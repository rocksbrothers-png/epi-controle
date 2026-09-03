"""O preflight de disponibilidade da B4-B — #271.

Quatro execuções da certificação reprovaram com `The read operation timed out`
nos dois deployments de API. A causa foi medida à mão em 02/09/2026: a primeira
resposta leva **46 s no corporativo e 35 s no SaaS**, contra `TIMEOUT = 20`.

O timeout escondia dois defeitos que só apareceram depois de aquecer os
serviços — e o segundo é do próprio certificador:

1. os dois tokens estavam expirados (401 no SaaS, 403 no corporativo);
2. **um HTTP 503 era reportado como `autenticação: token aceito`**, porque a
   checagem só reprovava em 401/403. O mesmo token saiu "aceito" numa leitura
   (503) e "recusado" na seguinte (403). O certificador afirmava ter verificado
   autenticação sem a requisição ter chegado à aplicação.

Estes gates travam as duas coisas. Como no resto da casa, eles medem
comportamento: a classificação é exercitada status a status, e cada uma tem
mutação provando que o gate a enxerga.
"""

import ast
import importlib.util
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / 'scripts' / 'certificar_deployment.py'


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


def _stub(modulo, *statuses):
    """Troca `_get` por um duplo que registra (url, timeout, status).

    O default de `timeout` espelha o da função real, então uma chamada que não
    passa nada registra `TIMEOUT` — é assim que o gate distingue as duas fases
    sem ler o código.
    """
    chamadas = []
    fila = list(statuses)

    def falso(url, token, origin='', timeout=modulo.TIMEOUT):
        status = fila.pop(0) if len(fila) > 1 else fila[0]
        chamadas.append((url, timeout, status))
        return status, {}, {}

    modulo._get = falso
    return chamadas


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
    """Cada status tem um veredito, e 404 não é sucesso.

    `/api/units/selectable` faz parte do contrato da #271. Um 404 diz "o
    servidor respondeu, mas este deployment não é o esperado" — situação
    diferente de "ainda subindo", e que repetir não conserta.
    """
    m = _modulo()
    classificar = m._classificar_preflight

    for status in (200, 201, 204):
        assert classificar(status) == m.PRONTA, f'{status} deixou de ser pronta'

    for status in (401, 403):
        assert classificar(status) == m.PRONTA_AUTH_RECUSADA, \
            (f'{status} deixou de contar como aplicação de pé: a requisição '
             f'chegou à camada de autenticação e recebeu recusa deliberada')

    assert classificar(404) == m.CONTRATO_INVALIDO, \
        '404 virou sucesso ou indisponibilidade — é contrato/deployment errado'

    for status in (500, 502, 503, 504):
        assert classificar(status) == m.NAO_PRONTA, \
            (f'{status} contou como aplicação pronta: 5xx é resposta do '
             f'GATEWAY, e foi assim que um 503 virou "token aceito"')

    assert classificar(0) == m.NAO_PRONTA, 'timeout/socket deixou de ser não-pronta'


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


# ═══════════════════════════════════════════════════════════════════════════
# Mutações — os dois gates acima estão cegos?
# ═══════════════════════════════════════════════════════════════════════════

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
# Teto de tentativas e fail-closed — por CONTAGEM, não por leitura do literal
# ═══════════════════════════════════════════════════════════════════════════

def test_o_preflight_para_no_teto_de_tentativas():
    m = _modulo()
    chamadas = _stub(m, 503)
    veredito, tentativas = m._preflight('https://exemplo', 'tok')
    assert veredito == m.NAO_PRONTA
    assert len(chamadas) == m.PREFLIGHT_TENTATIVAS == 2, \
        (f'o preflight emitiu {len(chamadas)} requisições: o teto virou laço, '
         f'e "no máximo uma repetição controlada" deixou de valer')
    assert len(tentativas) == 2


def test_a_segunda_tentativa_so_e_gasta_por_indisponibilidade():
    """404 e 401 param na primeira: repetir não conserta nenhum dos dois."""
    m = _modulo()
    for status in (404, 401, 200):
        chamadas = _stub(m, status)
        m._preflight('https://exemplo', 'tok')
        assert len(chamadas) == 1, \
            f'HTTP {status} gastou {len(chamadas)} tentativas; devia parar em 1'

    chamadas = _stub(m, 503, 200)
    veredito, tentativas = m._preflight('https://exemplo', 'tok')
    assert len(chamadas) == 2 and veredito == m.PRONTA, \
        'a segunda tentativa deixou de recuperar um deployment que acordou'


def test_preflight_reprovado_nao_emite_requisicao_funcional():
    """Fail-closed com prova: zero GETs funcionais depois do preflight ruim."""
    m = _modulo()
    chamadas = _stub(m, 503)
    r = m.certificar_api('teste', 'https://exemplo', 'tok')

    assert r.nao_pronta is True
    assert r.certificado is False, 'preflight reprovado produziu ambiente certificado'
    assert len(chamadas) == m.PREFLIGHT_TENTATIVAS, \
        (f'{len(chamadas)} requisições com o preflight reprovando: alguma '
         f'checagem funcional rodou assim mesmo, que é o fail-open que esta '
         f'fase existe para impedir')
    assert all(timeout == m.PREFLIGHT_TIMEOUT for _, timeout, _ in chamadas), \
        'alguma requisição do preflight usou o timeout funcional'


def test_contrato_invalido_tambem_nao_emite_requisicao_funcional():
    m = _modulo()
    chamadas = _stub(m, 404)
    r = m.certificar_api('teste', 'https://exemplo', 'tok')
    assert r.certificado is False
    assert r.nao_pronta is False, \
        '404 foi rotulado como indisponibilidade; é divergência de contrato'
    assert len(chamadas) == 1, \
        f'{len(chamadas)} requisições: o 404 não interrompeu o fluxo'


def test_o_tempo_de_cada_tentativa_e_registrado():
    m = _modulo()
    _stub(m, 503)
    _, tentativas = m._preflight('https://exemplo', 'tok')
    assert len(tentativas) == 2
    for numero, status, segundos, veredito in tentativas:
        assert isinstance(numero, int) and isinstance(status, int)
        assert isinstance(segundos, float) and segundos >= 0.0, \
            'o tempo de resposta deixou de ser registrado por tentativa'
        assert veredito == m.NAO_PRONTA


# ═══════════════════════════════════════════════════════════════════════════
# Os dois timeouts, verificados no PONTO DE CHAMADA
# ═══════════════════════════════════════════════════════════════════════════

def test_os_dois_timeouts_moram_em_fases_diferentes():
    """Existir a constante não prova nada; usá-la no lugar certo prova.

    Um gate que só confere `PREFLIGHT_TIMEOUT = 60` no topo do arquivo passaria
    com o preflight rodando a 20 s e o smoke funcional a 60 s.
    """
    m = _modulo()
    assert m.TIMEOUT == 20, 'o TIMEOUT funcional foi alterado'
    assert m.PREFLIGHT_TIMEOUT > m.TIMEOUT

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
