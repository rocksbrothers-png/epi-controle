"""O preflight de readiness da B4-B — #271.

## Primeira evidência (02/09/2026): cold start escondendo defeitos

Quatro execuções da certificação reprovaram com `The read operation timed out`
nos dois deployments de API. A primeira resposta levava **46 s no corporativo e
35 s no SaaS**, contra `TIMEOUT = 20`. O timeout escondia dois defeitos que só
apareceram depois de aquecer os serviços — e o segundo era do próprio
certificador:

1. os dois tokens estavam expirados (401 no SaaS, 403 no corporativo);
2. **um HTTP 503 era reportado como `autenticação: token aceito`**, porque a
   checagem só reprovava em 401/403. O mesmo token saiu "aceito" numa leitura
   (503) e "recusado" na seguinte (403).

## Segunda evidência (03/09/2026): amostrar rápido demais

A primeira versão do preflight fazia duas tentativas de 60 s. Em produção:

    preflight 1/2: HTTP 503 em 32.5s → nao_pronta
    preflight 2/2: HTTP 503 em  0.2s → nao_pronta

Os 0,2 s denunciam o erro. O 503 vem do PRÓPRIO backend — enquanto
`state['ready']` é falso, `_require_bootstrap_ready` responde
`DB_BOOTSTRAP_NOT_READY` a toda rota `/api/` não isenta —, e uma resposta
imediata não consome timeout nenhum. "2 × 60 s" era orçamento de timeout, não de
relógio: gastou 32,6 s de espera real contra um bootstrap de ~80 s a ~120 s.

Daí o contrato atual: **amostragem periódica com deadline absoluto de relógio**.

Estes gates medem comportamento, não texto. O laço é exercitado contra um
relógio falso — `sleep` avança o tempo em vez de esperar —, então uma sabotagem
que transforme o deadline em soma de durações aparece como laço infinito, e não
como teste lento. Todo teste que pode não terminar roda com teto de requisições.
"""

import ast
import importlib.util
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / 'scripts' / 'certificar_deployment.py'

#: Teto de segurança: qualquer laço que passe daqui é laço infinito, não
#: lentidão. Muito acima do máximo legítimo (deadline / intervalo + 1).
TETO_DE_SEGURANCA = 500


class _LacoInfinito(RuntimeError):
    """O preflight não parou. Erro de projeto, não falha de rede."""


class _Relogio:
    """Relógio monotônico falso: `sleep` avança o tempo em vez de esperar.

    Existe para que "esperar 180 s" seja uma afirmação verificável em
    milissegundos. Um gate que dormisse de verdade seria lento demais para
    rodar em CI e, por isso, acabaria não rodando.
    """

    def __init__(self) -> None:
        self.agora = 0.0
        self.dormidas: list[float] = []

    def monotonic(self) -> float:
        return self.agora

    def sleep(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.agora += segundos


def _modulo():
    spec = importlib.util.spec_from_file_location('certificar_deployment', SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _modulo_mutado(velho: str, novo: str):
    """Carrega o script com uma mutação — e PROVA que ela pegou."""
    fonte = SCRIPT.read_text(encoding='utf-8')
    assert velho in fonte, f'MUTACAO NAO APLICOU: {velho!r} não está no script'
    mutada = fonte.replace(velho, novo, 1)
    assert mutada != fonte, 'MUTACAO NAO APLICOU: texto idêntico após a troca'
    espaco = {'__name__': 'certificar_deployment_mutado', '__file__': str(SCRIPT)}
    exec(compile(mutada, str(SCRIPT), 'exec'), espaco)  # noqa: S102
    return espaco


def _por(alvo, nome, valor) -> None:
    """Injeta em módulo real ou em namespace de módulo mutado."""
    if isinstance(alvo, dict):
        alvo[nome] = valor
    else:
        setattr(alvo, nome, valor)


def _de(alvo, nome):
    return alvo[nome] if isinstance(alvo, dict) else getattr(alvo, nome)


def _relogiar(alvo) -> _Relogio:
    relogio = _Relogio()
    _por(alvo, 'time', relogio)
    return relogio


def _stub(alvo, *statuses, relogio=None, custo=0.0, teto=TETO_DE_SEGURANCA):
    """Troca `_get` por um duplo que registra (url, timeout, status).

    `custo` é quanto de relógio cada requisição consome — é assim que o gate
    distingue "deadline de relógio" de "soma de durações". O default de
    `timeout` espelha o da função real, então uma chamada que não passa nada
    registra `TIMEOUT`: é assim que o gate separa as duas fases sem ler código.
    """
    chamadas = []
    fila = list(statuses)
    padrao = _de(alvo, 'TIMEOUT')

    def falso(url, token, origin='', timeout=padrao):
        if len(chamadas) >= teto:
            raise _LacoInfinito(
                f'{len(chamadas)} requisições sem parar: o preflight virou '
                f'laço infinito')
        status = fila.pop(0) if len(fila) > 1 else fila[0]
        chamadas.append((url, timeout, status))
        if relogio is not None:
            relogio.agora += custo
        return status, {}, {}

    _por(alvo, '_get', falso)
    return chamadas


def _sondagens_ate_o_deadline(alvo) -> int:
    """Quantas sondagens cabem no deadline quando a requisição é instantânea."""
    return int(_de(alvo, 'PREFLIGHT_DEADLINE') // _de(alvo, 'PREFLIGHT_INTERVALO')) + 1


def _funcao(nome: str) -> ast.FunctionDef:
    arvore = ast.parse(SCRIPT.read_text(encoding='utf-8'))
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    raise AssertionError(f'função {nome!r} não existe mais em {SCRIPT.name}')


def _chamadas_de_get(alvo: ast.FunctionDef) -> list[ast.Call]:
    return [no for no in ast.walk(alvo)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name) and no.func.id == '_get']


# ═══════════════════════════════════════════════════════════════════════════
# Classificação — a tabela inteira, um status por vez
# ═══════════════════════════════════════════════════════════════════════════

def test_a_classificacao_do_preflight_cobre_a_tabela():
    """Cada status tem um veredito, e nenhum cai em falso verde."""
    m = _modulo()
    classificar = m._classificar_preflight

    for status in (200, 201, 204):
        assert classificar(status) == m.PRONTA, f'{status} deixou de ser pronta'

    for status in (401, 403):
        assert classificar(status) == m.PRONTA_AUTH_RECUSADA, \
            (f'{status} deixou de contar como aplicação de pé: a requisição '
             f'atravessou o portão de readiness e chegou à autenticação')

    assert classificar(404) == m.CONTRATO_INVALIDO, \
        '404 virou sucesso ou indisponibilidade — é contrato/deployment errado'

    for status in (500, 502, 503, 504):
        assert classificar(status) == m.NAO_PRONTA, \
            (f'{status} contou como aplicação pronta: é o 503 do portão de '
             f'readiness, e foi assim que um 503 virou "token aceito"')

    assert classificar(0) == m.NAO_PRONTA, 'timeout/socket deixou de ser não-pronta'

    # Demais 4xx: resposta deliberada da aplicação, portanto de pé. Não é falso
    # verde — o smoke funcional roda em seguida e julga o status.
    for status in (400, 429):
        assert classificar(status) == m.PRONTA, \
            f'{status} deixou de ser classificado explicitamente'


def test_so_2xx_prova_autenticacao():
    """O defeito medido, virado teste."""
    m = _modulo()
    for status in (200, 204, 299):
        assert m._autenticou(status) is True
    for status in (401, 403):
        assert m._autenticou(status) is False
    for status in (500, 502, 503, 504):
        assert m._autenticou(status) is False, \
            (f'HTTP {status} produziu "token aceito" — o certificador voltou a '
             f'afirmar autenticação sobre resposta de gateway')
    assert m._autenticou(0) is False


def test_o_gate_da_classificacao_pega_o_5xx_reclassificado():
    espaco = _modulo_mutado(
        '    if status == 0 or status >= 500:\n        return NAO_PRONTA',
        '    if status == 0:\n        return NAO_PRONTA')
    assert espaco['_classificar_preflight'](503) == espaco['PRONTA'], \
        'MUTACAO NAO APLICOU: 503 continua NAO_PRONTA com o ramo removido'
    assert _modulo()._classificar_preflight(503) == _modulo().NAO_PRONTA, \
        ('o classificador ÍNTEGRO já devolvia PRONTA para 503 — mutação e '
         'original são indistinguíveis e o gate não prova nada')


def test_o_gate_da_autenticacao_pega_o_autenticou_permissivo():
    espaco = _modulo_mutado(
        '    return 200 <= status < 300',
        '    return status not in (401, 403)')
    assert espaco['_autenticou'](503) is True, \
        'MUTACAO NAO APLICOU: 503 continua reprovando com a versão permissiva'
    assert _modulo()._autenticou(503) is False, \
        ('o `_autenticou` ÍNTEGRO aceitou 503 — é exatamente o defeito que '
         'este gate existe para impedir')


# ═══════════════════════════════════════════════════════════════════════════
# O laço: espera por relógio, não por contagem de tentativas
# ═══════════════════════════════════════════════════════════════════════════

def test_os_parametros_do_contrato():
    m = _modulo()
    assert m.TIMEOUT == 20, 'o TIMEOUT funcional foi alterado'
    assert m.PREFLIGHT_TIMEOUT == 60
    assert m.PREFLIGHT_DEADLINE == 180
    assert m.PREFLIGHT_INTERVALO == 5
    assert m.PREFLIGHT_DEADLINE > m.PREFLIGHT_TIMEOUT > m.TIMEOUT


def test_varios_503_seguidos_de_2xx_passam():
    """O caso que a versão anterior não conseguia atender.

    Cinco 503 do portão de readiness e o 200 quando o bootstrap termina: é
    exatamente o boot observado em produção, e tem de passar.
    """
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, 503, 503, 503, 503, 200, relogio=relogio, custo=1.0)

    veredito, tentativas, time_to_ready = m._preflight('https://exemplo', 'tok')

    assert veredito == m.PRONTA, \
        'uma aplicação que ficou pronta na 6ª sondagem foi dada como não-pronta'
    assert len(chamadas) == 6, f'{len(chamadas)} sondagens, esperado 6'
    assert [t[3] for t in tentativas] == [m.NAO_PRONTA] * 5 + [m.PRONTA]
    assert time_to_ready == pytest.approx(6 * 1.0 + 5 * m.PREFLIGHT_INTERVALO), \
        'o time_to_ready não corresponde ao relógio decorrido'


def test_503_ate_o_deadline_reprova():
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio)

    veredito, tentativas, time_to_ready = m._preflight('https://exemplo', 'tok')

    assert veredito == m.NAO_PRONTA
    assert len(chamadas) == _sondagens_ate_o_deadline(m), \
        (f'{len(chamadas)} sondagens em {m.PREFLIGHT_DEADLINE}s de deadline a '
         f'cada {m.PREFLIGHT_INTERVALO}s — o laço não usou o orçamento inteiro '
         f'ou passou dele')
    assert time_to_ready >= m.PREFLIGHT_DEADLINE, \
        (f'esperou só {time_to_ready}s de um deadline de '
         f'{m.PREFLIGHT_DEADLINE}s: é a regressão de 32,6 s de volta')
    assert all(t[3] == m.NAO_PRONTA for t in tentativas)


def test_404_reprova_de_imediato():
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 404, relogio=relogio)

    veredito, tentativas, _ = m._preflight('https://exemplo', 'tok')

    assert veredito == m.CONTRATO_INVALIDO
    assert len(chamadas) == 1, \
        f'404 gastou {len(chamadas)} sondagens: repetir não conserta rota ausente'
    assert relogio.dormidas == [], '404 dormiu antes de desistir'
    assert len(tentativas) == 1


def test_2xx_e_auth_recusada_encerram_na_primeira_sondagem():
    m = _modulo()
    for status in (200, 401, 403):
        relogio = _relogiar(m)
        chamadas = _stub(m, status, relogio=relogio)
        m._preflight('https://exemplo', 'tok')
        assert len(chamadas) == 1, \
            f'HTTP {status} gastou {len(chamadas)} sondagens; devia parar em 1'
        assert relogio.dormidas == [], f'HTTP {status} dormiu sem precisar'


def test_o_deadline_e_de_relogio_e_nao_soma_de_duracoes():
    """Requisições instantâneas: só o relógio pode parar o laço.

    Com 503 respondido em 0 s, a soma das durações fica sempre em zero. Se o
    deadline fosse medido por ela — como o "2 × 60 s" era —, este laço não
    terminaria nunca. Ele termina porque o tempo dormido também conta.
    """
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio, custo=0.0)

    _, tentativas, time_to_ready = m._preflight('https://exemplo', 'tok')

    assert all(t[2] == 0.0 for t in tentativas), \
        'as requisições deixaram de ser instantâneas; o teste perdeu o sentido'
    assert time_to_ready == pytest.approx(m.PREFLIGHT_DEADLINE)
    assert len(chamadas) == _sondagens_ate_o_deadline(m)


def test_a_duracao_das_requisicoes_conta_no_deadline():
    """O outro lado da mesma moeda: requisição lenta gasta o orçamento."""
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio, custo=25.0)

    _, _, time_to_ready = m._preflight('https://exemplo', 'tok')

    assert len(chamadas) < _sondagens_ate_o_deadline(m), \
        ('sondagens de 25 s couberam tantas quanto as instantâneas: o tempo '
         'gasto na requisição não está sendo descontado do deadline')
    assert time_to_ready >= m.PREFLIGHT_DEADLINE


def test_o_polling_respeita_o_intervalo():
    m = _modulo()
    relogio = _relogiar(m)
    _stub(m, 503, relogio=relogio)

    m._preflight('https://exemplo', 'tok')

    assert relogio.dormidas, 'o preflight sondou em rajada, sem intervalo nenhum'
    assert all(0 < d <= m.PREFLIGHT_INTERVALO for d in relogio.dormidas), \
        f'alguma espera saiu do intervalo contratado: {relogio.dormidas}'
    assert all(d == m.PREFLIGHT_INTERVALO for d in relogio.dormidas[:-1]), \
        'só a última espera pode ser encurtada, para não passar do deadline'


def test_o_laco_nao_e_infinito():
    """Sem relógio falso: 503 eterno e teto baixo. Tem de parar sozinho."""
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio, teto=TETO_DE_SEGURANCA)

    m._preflight('https://exemplo', 'tok')

    assert len(chamadas) < TETO_DE_SEGURANCA, 'o teto de segurança foi atingido'


def test_o_time_to_ready_e_cada_sondagem_ficam_registrados():
    """Requisito de relatório: tentativa, status, duração, total."""
    m = _modulo()
    relogio = _relogiar(m)
    _stub(m, 503, 503, 200, relogio=relogio, custo=2.0)

    _, tentativas, time_to_ready = m._preflight('https://exemplo', 'tok')

    assert [t[0] for t in tentativas] == [1, 2, 3], 'a numeração se perdeu'
    assert [t[1] for t in tentativas] == [503, 503, 200], 'os status se perderam'
    for _, _, segundos, _ in tentativas:
        assert isinstance(segundos, float) and segundos >= 0.0, \
            'a duração deixou de ser registrada por sondagem'
    assert time_to_ready > sum(t[2] for t in tentativas), \
        'o time_to_ready ignorou o tempo de espera entre sondagens'


# ═══════════════════════════════════════════════════════════════════════════
# Sabotagens do laço — os gates acima estão cegos?
# ═══════════════════════════════════════════════════════════════════════════

def test_o_gate_pega_o_deadline_virado_soma_de_duracoes():
    """A regressão exata do contrato anterior."""
    espaco = _modulo_mutado(
        '        restante = PREFLIGHT_DEADLINE - (time.monotonic() - inicio_total)',
        '        restante = PREFLIGHT_DEADLINE - sum(t[2] for t in tentativas)')
    relogio = _relogiar(espaco)
    _stub(espaco, 503, relogio=relogio, custo=0.0)

    with pytest.raises(_LacoInfinito):
        espaco['_preflight']('https://exemplo', 'tok')

    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio, custo=0.0)
    m._preflight('https://exemplo', 'tok')
    assert len(chamadas) == _sondagens_ate_o_deadline(m), \
        'o preflight ÍNTEGRO também não para pelo relógio — o gate não prova nada'


def test_o_gate_pega_o_deadline_removido():
    """Sem a parada, 503 eterno vira laço eterno. O teto de segurança prova."""
    espaco = _modulo_mutado(
        '        if restante <= 0:\n            break\n',
        '        if False:\n            break\n')
    relogio = _relogiar(espaco)
    _stub(espaco, 503, relogio=relogio)

    with pytest.raises(_LacoInfinito):
        espaco['_preflight']('https://exemplo', 'tok')

    m = _modulo()
    relogio_ok = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio_ok)
    m._preflight('https://exemplo', 'tok')
    assert len(chamadas) < TETO_DE_SEGURANCA, \
        ('o preflight ÍNTEGRO também não para — mutação e original são '
         'indistinguíveis e o gate não prova nada')


def test_o_gate_pega_o_polling_sem_intervalo():
    espaco = _modulo_mutado(
        '        time.sleep(min(PREFLIGHT_INTERVALO, restante))',
        '        pass')
    relogio = _relogiar(espaco)
    _stub(espaco, 503, relogio=relogio, custo=1.0)
    espaco['_preflight']('https://exemplo', 'tok')
    assert relogio.dormidas == [], \
        'MUTACAO NAO APLICOU: o preflight mutado continua dormindo'

    m = _modulo()
    relogio_ok = _relogiar(m)
    _stub(m, 503, relogio=relogio_ok, custo=1.0)
    m._preflight('https://exemplo', 'tok')
    assert relogio_ok.dormidas, \
        'o preflight ÍNTEGRO também não dorme — o intervalo não está sendo exercido'


def test_o_gate_pega_a_sonda_trocada_por_health():
    """`/health` responde 200 antes de `ready`. Trocar a sonda é falso verde.

    `runtime_probe_response` devolve 200 incondicionalmente para a sonda de
    liveness, e é assim que o health check da plataforma mantém o serviço
    roteável durante o boot. Sondar `/health` diria "pronta" no meio do
    bootstrap e jogaria o smoke funcional contra os 503 do portão.
    """
    espaco = _modulo_mutado(
        "        status, _, _ = _get(raiz + SONDAS[0][0], token,",
        "        status, _, _ = _get(raiz + '/health', token,")
    relogio = _relogiar(espaco)
    chamadas = _stub(espaco, 200, relogio=relogio)
    espaco['_preflight']('https://exemplo', 'tok')
    assert chamadas[0][0].endswith('/health'), \
        'MUTACAO NAO APLICOU: a sonda mutada não foi para /health'

    m = _modulo()
    _relogiar(m)
    chamadas_ok = _stub(m, 200)
    m._preflight('https://exemplo', 'tok')
    assert chamadas_ok[0][0].endswith('/api/units/selectable'), \
        ('o preflight ÍNTEGRO não sonda a superfície real da #271 — /health '
         'não prova readiness funcional')


def test_a_sonda_e_a_superficie_real_e_nao_o_health():
    m = _modulo()
    assert m.SONDAS[0][0] == '/api/units/selectable'
    fonte_do_preflight = ast.get_source_segment(
        SCRIPT.read_text(encoding='utf-8'), _funcao('_preflight'))
    assert '/health' not in fonte_do_preflight, \
        '`/health` apareceu no preflight: ele responde 200 antes de `ready`'


# ═══════════════════════════════════════════════════════════════════════════
# Fail-closed e separação das duas fases
# ═══════════════════════════════════════════════════════════════════════════

def test_sem_ready_nenhuma_requisicao_funcional():
    """Fail-closed com prova: zero GETs funcionais depois do preflight ruim."""
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, relogio=relogio)

    r = m.certificar_api('teste', 'https://exemplo', 'tok')

    assert r.nao_pronta is True
    assert r.certificado is False, 'preflight reprovado produziu ambiente certificado'
    assert len(chamadas) == _sondagens_ate_o_deadline(m), \
        (f'{len(chamadas)} requisições com o preflight reprovando: alguma '
         f'checagem funcional rodou assim mesmo, que é o fail-open que esta '
         f'fase existe para impedir')
    assert all(timeout == m.PREFLIGHT_TIMEOUT for _, timeout, _ in chamadas), \
        'alguma requisição do preflight usou o timeout funcional'
    assert r.time_to_ready >= m.PREFLIGHT_DEADLINE, \
        'o READY TIMEOUT não registrou o tempo esperado'


def test_contrato_invalido_tambem_nao_emite_requisicao_funcional():
    m = _modulo()
    _relogiar(m)
    chamadas = _stub(m, 404)
    r = m.certificar_api('teste', 'https://exemplo', 'tok')
    assert r.certificado is False
    assert r.nao_pronta is False, \
        '404 foi rotulado como indisponibilidade; é divergência de contrato'
    assert len(chamadas) == 1, \
        f'{len(chamadas)} requisições: o 404 não interrompeu o fluxo'


def test_depois_de_ready_o_smoke_roda_com_o_timeout_funcional():
    """READY encerra o preflight e a fase 2 começa com `TIMEOUT = 20`."""
    m = _modulo()
    relogio = _relogiar(m)
    chamadas = _stub(m, 503, 503, 200, relogio=relogio, custo=1.0)

    m.certificar_api('teste', 'https://exemplo', 'tok')

    do_preflight = [c for c in chamadas if c[1] == m.PREFLIGHT_TIMEOUT]
    funcionais = [c for c in chamadas if c[1] == m.TIMEOUT]
    assert len(do_preflight) == 3, \
        f'{len(do_preflight)} sondagens de preflight, esperado 3'
    assert funcionais, \
        'o smoke funcional não rodou depois de READY: a fase 2 ficou órfã'
    assert all(c[1] == m.TIMEOUT for c in funcionais), \
        'um GET funcional herdou o timeout do preflight'


# ═══════════════════════════════════════════════════════════════════════════
# Os dois timeouts e o método, verificados no PONTO DE CHAMADA
# ═══════════════════════════════════════════════════════════════════════════

def test_os_dois_timeouts_moram_em_fases_diferentes():
    """Existir a constante não prova nada; usá-la no lugar certo prova."""
    do_preflight = _chamadas_de_get(_funcao('_preflight'))
    assert len(do_preflight) == 1, \
        f'`_preflight` faz {len(do_preflight)} chamadas a `_get`, esperado 1'
    palavras = {k.arg: k.value for k in do_preflight[0].keywords}
    assert 'timeout' in palavras, '`_preflight` voltou a usar o timeout funcional'
    assert isinstance(palavras['timeout'], ast.Name)
    assert palavras['timeout'].id == 'PREFLIGHT_TIMEOUT'

    for chamada in _chamadas_de_get(_funcao('certificar_api')):
        assert 'timeout' not in {k.arg for k in chamada.keywords}, \
            ('um GET funcional passou `timeout` explícito: o smoke deve usar '
             'o default de 20s, não afrouxar junto com o preflight')


def test_o_deadline_e_o_intervalo_sao_usados_no_laco():
    """Constante definida e não usada passaria num gate que só lê o topo."""
    nomes = {no.id for no in ast.walk(_funcao('_preflight'))
             if isinstance(no, ast.Name)}
    for constante in ('PREFLIGHT_DEADLINE', 'PREFLIGHT_INTERVALO'):
        assert constante in nomes, \
            f'{constante} não é usada dentro de `_preflight`'


def test_somente_get_em_todo_o_certificador():
    """Nenhuma escrita em produção. O cabeçalho promete; isto verifica."""
    arvore = ast.parse(SCRIPT.read_text(encoding='utf-8'))
    requests = [no for no in ast.walk(arvore)
                if isinstance(no, ast.Call)
                and getattr(no.func, 'attr', '') == 'Request']
    assert requests, 'nenhuma `urllib.request.Request` encontrada'
    for chamada in requests:
        metodo = {k.arg: k.value for k in chamada.keywords}.get('method')
        assert isinstance(metodo, ast.Constant) and metodo.value == 'GET', \
            'uma requisição deixou de ser GET explícito'

    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            proibidas = {'data', 'json'} & {k.arg for k in no.keywords}
            assert not proibidas, \
                f'chamada com {sorted(proibidas)}: o certificador não escreve'
