"""R0.5B — gates da certificação de identidade da origem.

A R0.5 provou a FORMA da cadeia e nada além disso. Esta fatia mede as quatro
propriedades que faltam para `HOPS=3` sair de PARCIALMENTE PROVADO, e estes
gates travam as regressões que a própria certificação cria.

Cada gate existe para uma sabotagem nomeada em `docs/R05B_IDENTIDADE_DA_ORIGEM.md`:

    A  candidato passa a sair de `cadeia[0]`          R05B-3
    B  hops avaliado cai para 2                        R05B-4
    C  hops avaliado sobe para 4                       R05B-4
    D  o cliente controla o elemento selecionado       R05B-5
    E  P1 falso é tratado como aprovado                R05B-6a
    F  uma origem só é aceita como P2                  R05B-6b
    G  duas execuções da mesma origem passam por duas  R05B-6c
    H  sentinela de CF-Connecting-IP sobrevive         R05B-8
    I  sentinela de True-Client-IP sobrevive           R05B-8
    J  truncamento destrói o sufixo e P4 passa         R05B-9
    K  a sonda fica depois do fechamento               R05B-7
    L  a chave continua lida depois do fechamento      R05-6 (arquivo vizinho)
    M  Corporate e SaaS divergem no contrato           R05B-1
"""

import hashlib
import json
import importlib.util
import re
from pathlib import Path


# O script é TEMPORÁRIO e `R05B-7` exige que ele suma quando o contrato fechar.
# Um import de módulo incondicional rebentaria a coleta ANTES de o gate rodar —
# e não existiria estado fechado com a suíte verde. Mesma lição do módulo da
# sonda, logo abaixo; achado de revisão.
if importlib.util.find_spec('scripts.certificar_identidade_da_origem') is None:
    CERT = None
else:
    import scripts.certificar_identidade_da_origem as CERT

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / 'docs' / 'R05B_IDENTIDADE_DA_ORIGEM.md'
CONTRATO_R05 = RAIZ / 'docs' / 'R05_CADEIA_DE_PROXY.md'
SONDA_MODULO = RAIZ / 'epi_backend' / 'proxy_identity_probe.py'
SCRIPT = RAIZ / 'scripts' / 'certificar_identidade_da_origem.py'
ROTAS_AUTH = RAIZ / 'modules' / 'auth' / 'routes.py'
LIMITADOR = RAIZ / 'core' / 'rate_limit.py'

INICIO = '<!-- CONTRATO-R05B-INICIO -->'
FIM = '<!-- CONTRATO-R05B-FIM -->'
ROTA_DA_SONDA = 'origin-identity-diagnostics'

# Digesto do bloco de contrato, carregado igual nos dois repositórios: editar
# de um lado só deixa aquele lado vermelho (sabotagem M).
DIGESTO_CONTRATO_R05B = '0630ad453fced15de54578d302aa0a6c00b9dec8d38bda33d41b9dd44e433612'

#: Vocabulário fechado de cada campo do contrato. `HOSTNAMES-COBERTOS` é o
#: único aberto: quando medido, carrega a lista de hostnames.
_MEDIDA = ('nao-medida', 'provada', 'reprovada')
_CLASSE = ('nao-medida', 'sentinela-sobrevive', 'substituida', 'ausente')
#: As duas entradas públicas onde `HOPS` será aplicado. Fechar o contrato sem
#: cobrir as duas é fechar sem cobertura.
HOSTNAMES_OBRIGATORIOS = (
    'epi-controle-app-gupy.onrender.com',
    'epi-controle-app-livamobile-api.onrender.com',
)

VOCABULARIO_DO_CONTRATO = {
    'P1-IDENTIDADE': _MEDIDA,
    'P2-DUAS-ORIGENS': _MEDIDA,
    'P3-CF-CONNECTING-IP': _CLASSE,
    'P3-TRUE-CLIENT-IP': _CLASSE,
    'P4-SUFIXO-PRESERVADO': _MEDIDA,
}

# A sonda é temporária. Enquanto a identidade estiver INDETERMINADA ela pode
# existir; depois, a presença dela reprova.
if importlib.util.find_spec('epi_backend.proxy_identity_probe') is None:
    SONDA = None
else:
    from epi_backend import proxy_identity_probe as SONDA


def _bloco() -> str:
    texto = CONTRATO.read_text(encoding='utf-8')
    assert INICIO in texto and FIM in texto, 'marcadores do contrato R0.5B sumiram'
    return texto.split(INICIO, 1)[1].split(FIM, 1)[0].strip()


def _campos() -> dict:
    campos = {}
    for linha in _bloco().splitlines():
        if ':' in linha:
            chave, valor = linha.split(':', 1)
            campos[chave.strip()] = valor.strip()
    return campos


def _em_aberto() -> bool:
    return _campos().get('ESTADO-DA-IDENTIDADE') == 'INDETERMINADO'


def _saltos_do_contrato_r05() -> int:
    texto = CONTRATO_R05.read_text(encoding='utf-8')
    bloco = texto.split('<!-- CONTRATO-R05-INICIO -->', 1)[1]
    bloco = bloco.split('<!-- CONTRATO-R05-FIM -->', 1)[0]
    for linha in bloco.splitlines():
        if linha.strip().startswith('SALTOS-CONFIAVEIS:'):
            valor = linha.split(':', 1)[1].strip()
            return int(valor) if valor.isdigit() else 0
    return 0


def _cadeia(prefixo_do_cliente: int, hops: int, cliente: str) -> list:
    """Monta a cadeia como a borda a entrega: prefixo do cliente à esquerda,
    contribuição da borda à direita, começando pelo endereço do cliente."""
    prefixo = [f'192.0.2.{20 + i}' for i in range(prefixo_do_cliente)]
    borda = [cliente] + [f'198.51.100.{200 + i}' for i in range(hops - 1)]
    return prefixo + borda


# ── R05B-1: contrato legível e idêntico nos dois repositórios ───────────────

def test_r05b_1_contrato_legivel_e_com_digesto_de_paridade():
    campos = _campos()
    for obrigatorio in ('ESTADO-DA-IDENTIDADE', 'P1-IDENTIDADE', 'P2-DUAS-ORIGENS',
                        'P3-CF-CONNECTING-IP', 'P3-TRUE-CLIENT-IP',
                        'P4-SUFIXO-PRESERVADO', 'HOSTNAMES-COBERTOS'):
        assert obrigatorio in campos, f'contrato R0.5B sem o campo {obrigatorio}'
    assert campos['ESTADO-DA-IDENTIDADE'] in ('INDETERMINADO', 'DETERMINADA'), \
        'ESTADO-DA-IDENTIDADE só admite INDETERMINADO ou DETERMINADA'

    # Fechar o contrato exige EVIDÊNCIA, não só trocar uma palavra.
    #
    # Antes, este gate conferia apenas que o estado era uma das duas strings.
    # Dava para pôr `DETERMINADA`, recalcular o digesto, deixar P1..P4 e os
    # hostnames em `nao-medida`, e — depois que a sonda e o script saíssem —
    # nada mais reprovava esse fechamento sem medição nenhuma. Achado de
    # revisão, e era o buraco mais sério do conjunto: o instrumento inteiro
    # existe para impedir certificação vazia.
    for campo, permitido in VOCABULARIO_DO_CONTRATO.items():
        assert campos[campo] in permitido, (
            f'{campo} = {campos[campo]!r} está fora do vocabulário fechado '
            f'{sorted(permitido)}'
        )

    if campos['ESTADO-DA-IDENTIDADE'] == 'DETERMINADA':
        for campo in ('P1-IDENTIDADE', 'P2-DUAS-ORIGENS', 'P4-SUFIXO-PRESERVADO'):
            assert campos[campo] == 'provada', (
                f'contrato DETERMINADA com {campo} = {campos[campo]!r}: '
                'fechamento sem evidência'
            )
        for campo in ('P3-CF-CONNECTING-IP', 'P3-TRUE-CLIENT-IP'):
            assert campos[campo] != 'nao-medida', (
                f'contrato DETERMINADA com {campo} ainda não medido'
            )
        cobertos = campos['HOSTNAMES-COBERTOS']
        # `!= 'nao-medidos'` sozinho aceitava vazio, ou `qualquer-coisa`, e
        # liberava a remoção da sonda sem provar cobertura nenhuma. Achado de
        # revisão: o campo tem de nomear as duas entradas onde HOPS será
        # aplicado.
        for hostname in HOSTNAMES_OBRIGATORIOS:
            assert hostname in cobertos, (
                f'contrato DETERMINADA sem cobrir {hostname}: '
                f'HOSTNAMES-COBERTOS = {cobertos!r}'
            )

    atual = hashlib.sha256(_bloco().encode('utf-8')).hexdigest()
    # O que este digesto prova, e o que NÃO prova.
    #
    # Ele é auto-referente: compara o documento com uma constante ao lado dele,
    # no MESMO repositório. Editar o contrato e a constante juntos passa —
    # então ele NÃO observa o outro repositório e NÃO prova paridade.
    #
    # O que ele pega é a edição unilateral que esquece a constante, que é o
    # acidente comum, e obriga qualquer mudança legítima a tocar os dois lados
    # (a constante é a mesma nos dois). É quebra-molas com dente, não prova.
    # Provar paridade exigiria um passo de CI comparando os dois repositórios —
    # fora do escopo desta fatia, e registrado como tal.
    assert atual == DIGESTO_CONTRATO_R05B, (
        'o contrato R0.5B mudou sem o digesto ser recalculado. A constante é a '
        'mesma nos dois repositórios, então recalcule nos DOIS. '
        f'Atual: {atual}'
    )


# ── R05B-2: a sonda não devolve endereço nenhum ─────────────────────────────

_ADVERSARIAIS = [
    # (cadeia, reivindicação, alternativa)
    (['203.0.113.7', '198.51.100.9', '192.0.2.10'], '203.0.113.7', '198.51.100.9'),
    (['2001:db8::1', '203.0.113.250'], '2001:db8::1', ''),
    ([], '203.0.113.7', '203.0.113.8'),
    (['  203.0.113.7  ', 'nao-e-ip'], 'nao-e-ip', ''),
]


def test_r05b_2_a_sonda_nunca_devolve_endereco():
    """Varredura adversarial: nenhum valor da entrada pode aparecer na saída.

    A sonda compara endereços internamente — é o que P1 exige. O que ela não
    pode é deixar um deles escapar para a resposta.
    """
    if SONDA is None:
        return
    import ipaddress
    import json as _json

    for cadeia, reivindicacao, alternativa in _ADVERSARIAIS:
        saida = SONDA.analisar(cadeia, 3, reivindicacao, alternativa,
                               {'CF-Connecting-Ip': 'substituida',
                                'True-Client-Ip': 'ausente'},
                               ['X-Forwarded-For'])
        texto = _json.dumps(saida, ensure_ascii=False)
        for suspeito in list(cadeia) + [reivindicacao, alternativa]:
            limpo = suspeito.strip()
            if not limpo:
                continue
            try:
                ipaddress.ip_address(limpo)
            except ValueError:
                continue
            assert limpo not in texto, (
                f'a sonda devolveu o endereço {limpo!r} na resposta: {texto}'
            )


def test_r05b_2b_a_saida_so_tem_tipos_permitidos():
    """Booleanos, inteiros, e strings de vocabulário fechado. Nada mais."""
    if SONDA is None:
        return
    saida = SONDA.analisar(_cadeia(2, 3, '203.0.113.9'), 3, '203.0.113.9', '',
                           {'CF-Connecting-Ip': 'substituida',
                            'True-Client-Ip': 'sentinela_sobrevive'},
                           ['X-Forwarded-For'])
    permitidas = set(SONDA.CLASSES_DE_CABECALHO) | {'R05B'} | set(SONDA.CABECALHOS_OBSERVADOS)
    for chave, valor in saida.items():
        if isinstance(valor, (bool, int)) or valor is None:
            continue
        if isinstance(valor, list):
            assert all(v in permitidas for v in valor), f'{chave} traz valor livre: {valor}'
            continue
        assert isinstance(valor, str) and valor in permitidas, \
            f'{chave} devolveu string fora do vocabulário: {valor!r}'


# ── R05B-3: o candidato sai de cadeia[-N], nunca de cadeia[0] ───────────────

def test_r05b_3_o_candidato_e_a_janela_da_direita_e_nao_o_primeiro():
    """Sabotagem A. Com prefixo do cliente presente, `cadeia[0]` é dele —
    selecionar dali é o defeito que a R0 fechou."""
    if SONDA is None:
        return
    cliente = '203.0.113.9'
    cadeia = _cadeia(2, 3, cliente)
    assert cadeia[0] != cliente, 'o cenário precisa ter prefixo do cliente à esquerda'

    saida = SONDA.analisar(cadeia, 3, cliente, '', {}, [])
    assert saida['candidato_bate_com_origem_declarada'] is True, \
        'o candidato deixou de ser o elemento em cadeia[-N]'

    # E o primeiro elemento, que é do cliente, NÃO pode ser o candidato.
    saida_primeiro = SONDA.analisar(cadeia, 3, cadeia[0], '', {}, [])
    assert saida_primeiro['candidato_bate_com_origem_declarada'] is False, \
        'o candidato passou a casar com cadeia[0] — território do cliente'


# ── R05B-4: o hops avaliado é o do contrato da R0.5 ─────────────────────────

def test_r05b_4_o_hops_avaliado_acompanha_o_contrato_da_r05():
    """Sabotagens B e C. Certificar identidade num N diferente do que será
    aplicado não certifica nada: a janela medida seria outra."""
    esperado = _saltos_do_contrato_r05()
    if esperado < 1:
        return
    if not SCRIPT.exists():
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    fonte = SCRIPT.read_text(encoding='utf-8')
    casou = re.search(r"EPI_IDENT_HOPS', '(\d+)'", fonte)
    assert casou, 'o script deixou de declarar o hops default'
    assert int(casou.group(1)) == esperado, (
        f'o script avalia hops={casou.group(1)} e o contrato da R0.5 diz '
        f'{esperado} — a identidade seria certificada para outra janela'
    )


def test_r05b_4b_hops_diferente_seleciona_outro_elemento():
    """O contrapeso comportamental: mudar N muda o elemento, então avaliar o N
    errado mede outra coisa."""
    if SONDA is None:
        return
    cliente = '203.0.113.9'
    cadeia = _cadeia(1, 3, cliente)
    assert SONDA.analisar(cadeia, 3, cliente, '', {}, [])['candidato_bate_com_origem_declarada'] is True
    for outro in (2, 4):
        saida = SONDA.analisar(cadeia, outro, cliente, '', {}, [])
        assert saida['candidato_bate_com_origem_declarada'] is not True, \
            f'hops={outro} continuou casando com o cliente — a janela não mudou'


# ── R05B-5: elemento controlado pelo cliente é denunciado ───────────────────

def test_r05b_5_candidato_vindo_do_cliente_e_denunciado():
    """Sabotagem D. Se a janela cair dentro do que o cliente escreveu, a sonda
    precisa dizer isso — é o sinal que impede certificar."""
    if SONDA is None:
        return
    # Cadeia com 4 sentinelas e nada da borda: `cadeia[-3]` é do cliente.
    cadeia = [f'192.0.2.{20 + i}' for i in range(4)]
    saida = SONDA.analisar(cadeia, 3, '', '', {}, [])
    assert saida['candidato_e_do_cliente'] is True, \
        'a sonda deixou de denunciar candidato vindo do cliente'
    assert saida['sufixo_confiavel_preservado'] is False


def test_r05b_5b_contaminacao_de_p1_e_denunciada():
    """Os três guardas que tornam P1 evidência em vez de suposição."""
    if CERT is None:
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    if SONDA is None:
        return
    cliente = '203.0.113.9'

    limpo = SONDA.analisar(_cadeia(0, 3, cliente), 3, cliente, '', {}, [])
    assert limpo['prefixo_do_cliente_presente'] is False
    assert limpo['cadeia_maior_que_hops'] is False
    assert limpo['reivindicacao_fora_do_candidato'] is False

    com_prefixo = SONDA.analisar(_cadeia(2, 3, cliente), 3, cliente, '', {}, [])
    assert com_prefixo['prefixo_do_cliente_presente'] is True
    assert com_prefixo['cadeia_maior_que_hops'] is True

    # O chamador injetou o próprio valor declarado noutra posição da cadeia.
    injetada = [cliente] + _cadeia(0, 3, cliente)
    assert SONDA.analisar(injetada, 3, cliente, '', {}, [])['reivindicacao_fora_do_candidato'] is True


# ── R05B-6: o veredito do script não aceita evidência insuficiente ──────────

def _alvo(**kwargs):
    a = CERT.Alvo('teste', 'https://exemplo.invalid', 'k')
    a.alcancado = True
    a.p1 = kwargs.get('p1', True)
    a.p1_contaminado = kwargs.get('contaminado', False)
    a.p2_alt = kwargs.get('p2_alt', False)
    a.anterior_ligado = kwargs.get('ligado', True)
    a.p4 = kwargs.get('p4', True)
    a.candidato_do_cliente = kwargs.get('do_cliente', False)
    return a


def test_r05b_6a_p1_falso_nao_passa():
    """Sabotagem E."""
    if CERT is None:
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    ok, pendente, _ = CERT._veredito(_alvo(p1=False), True)
    assert not ok and not pendente

    ok, _, _ = CERT._veredito(_alvo(contaminado=True), True)
    assert not ok, 'P1 contaminado foi tratado como aprovado'

    ok, _, _ = CERT._veredito(_alvo(do_cliente=True), True)
    assert not ok, 'candidato vindo do cliente foi tratado como aprovado'


def test_r05b_6b_uma_origem_so_nao_certifica():
    """Sabotagem F. Sem a segunda origem o resultado é PENDENTE, nunca OK."""
    if CERT is None:
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    ok, pendente, _ = CERT._veredito(_alvo(), False)
    assert not ok and pendente, 'uma origem só passou por certificação completa'

    ok, pendente, _ = CERT._veredito(_alvo(), True)
    assert ok and not pendente, 'com as duas origens o gate precisa deixar fechar'


def test_r05b_6c_mesma_origem_duas_vezes_nao_conta_como_duas():
    """Sabotagem G. Se o candidato desta origem é o endereço declarado da
    anterior, as duas execuções vieram do mesmo caminho."""
    if CERT is None:
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    ok, _, motivo = CERT._veredito(_alvo(p2_alt=True), True)
    assert not ok, 'duas execuções da mesma origem passaram por duas origens'
    assert 'origens distintas' in motivo


# ── R05B-7: a sonda é temporária ────────────────────────────────────────────

def test_r05b_7_a_sonda_sai_quando_a_identidade_for_determinada():
    """Sabotagem K."""
    if _em_aberto():
        assert SONDA_MODULO.exists(), \
            'a identidade está INDETERMINADA e a sonda já sumiu'
        return

    assert not SONDA_MODULO.exists(), \
        'identidade DETERMINADA e a sonda de identidade continua no repositório'
    assert not SCRIPT.exists(), \
        'o script de certificação continua, mas só fala com a rota removida'
    rotas = ROTAS_AUTH.read_text(encoding='utf-8')
    assert ROTA_DA_SONDA not in rotas, 'a rota da sonda continua registrada'
    assert 'proxy_identity_probe' not in rotas, 'o handler da sonda continua registrado'


def test_r05b_7b_nenhum_arquivo_mantem_a_rota_viva_depois():
    if _em_aberto():
        return
    sobreviventes = []
    for caminho in RAIZ.rglob('*'):
        if not caminho.is_file() or caminho.suffix not in ('.py', '.yaml', '.yml', '.js'):
            continue
        if '__pycache__' in caminho.parts or '.git' in caminho.parts:
            continue
        if caminho == Path(__file__):
            continue
        if ROTA_DA_SONDA in caminho.read_text(encoding='utf-8', errors='replace'):
            sobreviventes.append(str(caminho.relative_to(RAIZ)))
    assert not sobreviventes, f'a rota da sonda ainda aparece em: {sobreviventes}'


# ── R05B-8: cabeçalho controlável pelo cliente não vira fonte de identidade ─

def test_r05b_8_cabecalho_com_sentinela_sobrevivente_nao_e_adotavel():
    """Sabotagens H e I. A classificação tem de distinguir, e o documento tem
    de dizer que `sentinela_sobrevive` reprova o cabeçalho."""
    if SONDA is not None:
        assert set(SONDA.CLASSES_DE_CABECALHO) == {
            'ausente', 'sentinela_sobrevive', 'substituida'}

    texto = CONTRATO.read_text(encoding='utf-8')
    corrido = ' '.join(texto.split())
    assert 'sentinela_sobrevive' in corrido and 'não adotável' in corrido, (
        'o documento deixou de registrar que sentinela sobrevivente reprova o '
        'cabeçalho como fonte de identidade'
    )


class _HandlerFalso:
    def __init__(self, **cabecalhos):
        self.client_address = ('192.0.2.55', 1)
        self.headers = dict(cabecalhos)


def test_r05b_8c_sentinela_sobrevivente_e_classificado_como_tal():
    """Sabotagens H e I, no comportamento e não só no vocabulário.

    Se `_classe_do_cabecalho` mentir — reportando `substituida` para um valor
    que o cliente mandou —, o operador concluiria que a borda reescreve o
    cabeçalho quando na verdade ele é controlável. Este gate mede a função.
    """
    if SONDA is None:
        return
    for nome, campo in (('CF-Connecting-IP', 'cf_connecting_ip'),
                        ('True-Client-IP', 'true_client_ip')):
        sobrevive = SONDA.medir(_HandlerFalso(**{nome: '192.0.2.10'}))
        assert sobrevive[campo] == 'sentinela_sobrevive', (
            f'{nome} com sentinela do cliente foi classificado como '
            f'{sobrevive[campo]!r} — o operador leria isso como adotável'
        )

        substituida = SONDA.medir(_HandlerFalso(**{nome: '198.51.100.7'}))
        assert substituida[campo] == 'substituida'

        ausente = SONDA.medir(_HandlerFalso())
        assert ausente[campo] == 'ausente'


def test_r05b_8b_o_limitador_nao_le_cabecalho_de_identidade_nao_certificado():
    """O mecanismo que importa: ninguém pode ligar esses cabeçalhos em
    `get_client_ip` enquanto P3 não os certificar."""
    campos = _campos()
    certificados = {campos.get('P3-CF-CONNECTING-IP'), campos.get('P3-TRUE-CLIENT-IP')}
    if certificados == {'substituida'}:
        return
    fonte = LIMITADOR.read_text(encoding='utf-8')
    for cabecalho in ('CF-Connecting', 'True-Client', 'CF_CONNECTING', 'TRUE_CLIENT'):
        assert cabecalho not in fonte, (
            f'core/rate_limit.py passou a ler {cabecalho} sem P3 tê-lo '
            f'certificado como substituído pela borda (contrato: {certificados})'
        )


# ── R05B-9: truncamento que destrói a janela reprova ────────────────────────

def test_r05b_9_truncamento_da_janela_reprova_p4():
    """Sabotagem J. "Preservado" é definido como: nenhum dos N elementos mais
    à direita é sentinela. É essa janela que a seleção consome."""
    if SONDA is None:
        return
    cliente = '203.0.113.9'

    intacto = SONDA.analisar(_cadeia(30, 3, cliente), 3, '', '', {}, [])
    assert intacto['sufixo_confiavel_preservado'] is True, \
        'cadeia longa com sufixo intacto deixou de ser considerada preservada'

    # Truncamento pela direita: a borda perdeu elementos e sobrou sentinela na
    # janela. É o caso perigoso, e tem de reprovar.
    truncado = [f'192.0.2.{20 + i}' for i in range(30)] + ['198.51.100.200']
    saida = SONDA.analisar(truncado, 3, '', '', {}, [])
    assert saida['sufixo_confiavel_preservado'] is False, \
        'sufixo truncado pela direita passou por preservado'
    assert saida['candidato_e_do_cliente'] is True

    # Truncamento pela ESQUERDA não quebra nada: descarta prefixo do cliente.
    esquerda = SONDA.analisar(_cadeia(2, 3, cliente), 3, '', '', {}, [])
    assert esquerda['sufixo_confiavel_preservado'] is True


def test_r05b_9b_o_script_reprova_p4_falso():
    if CERT is None:
        return  # contrato fechado: o script saiu, e `R05B-7` cobre isso
    ok, pendente, motivo = CERT._veredito(_alvo(p4=False), True)
    assert not ok and not pendente
    assert 'P4' in motivo


# ── R05B-10: nenhum endereço real na fatia ──────────────────────────────────

FAIXAS_SEGURAS = (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
    '100.64.0.0/10', '127.0.0.0/8', '0.0.0.0/8',
    # não-roteáveis, necessários para exercitar `_origem_plausivel`: nenhum
    # deles é endereço público de alguém, que é o que este gate protege
    '169.254.0.0/16', '224.0.0.0/4', '240.0.0.0/4',
)


def test_r05b_10_nenhum_endereco_real_na_fatia():
    # Este gate NÃO depende do script: ele varre o que existir. Com o contrato
    # fechado, `SCRIPT` e `SONDA_MODULO` somem da lista e o contrato e este
    # arquivo continuam sendo varridos — que é o certo. Uma guarda `CERT is
    # None` aqui o transformaria em no-op justamente no estado fechado.
    import ipaddress

    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    padrao = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
    alvos = [CONTRATO, Path(__file__)]
    alvos += [caminho for caminho in (SCRIPT, SONDA_MODULO) if caminho.exists()]
    for caminho in alvos:
        for literal in set(padrao.findall(caminho.read_text(encoding='utf-8'))):
            try:
                endereco = ipaddress.ip_address(literal)
            except ValueError:
                continue
            assert any(endereco in faixa for faixa in faixas), (
                f'{caminho.name} contém {literal}, que não é de faixa reservada'
            )


# ── Achados da revisão do Codex em 699983ed ─────────────────────────────────
#
# Nove defeitos reais no INSTRUMENTO — e três deles deixavam o instrumento
# certificar o que ele existe para impedir. Cada correção ganhou gate próprio,
# porque correção sem gate volta.

_VARIAVEIS = ('EPI_IDENT_CORP_URL', 'EPI_IDENT_CORP_KEY', 'EPI_IDENT_SAAS_URL',
              'EPI_IDENT_SAAS_KEY', 'EPI_IDENT_ALT_URL', 'EPI_IDENT_ALT_KEY',
              'EPI_IDENT_ORIGEM', 'EPI_IDENT_MEU_IP', 'EPI_IDENT_IP_ANTERIOR',
              'EPI_IDENT_HOPS', 'EPI_IDENT_ESTADO')

_IP_A = '203.0.113.11'
_IP_B = '203.0.113.22'


def _env(monkeypatch, **valores):
    for nome in _VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    for nome, valor in valores.items():
        monkeypatch.setenv(nome, str(valor))


def _resposta(hops=3, **sobrescreve):
    base = {
        'probe': 'R05B',
        'hops_avaliado': hops,
        'cadeia_tamanho': hops,
        'cadeia_suficiente_para_hops': True,
        'sentinelas_na_cadeia': 0,
        'prefixo_do_cliente_presente': False,
        'cadeia_maior_que_hops': False,
        'reivindicacao_fora_do_candidato': False,
        'candidato_e_do_cliente': False,
        'sufixo_confiavel_preservado': True,
        'candidato_bate_com_origem_declarada': None,
        'candidato_bate_com_origem_alternativa': None,
        'cf_connecting_ip': 'ausente',
        'true_client_ip': 'ausente',
        'cabecalhos_presentes': [],
    }
    base.update(sobrescreve)
    return base


def _sonda_falsa(cf='substituida', tc='substituida', alt_contradiz=False):
    """Uma borda ideal: P1 sempre bate, P4 sempre preserva, nada contaminado.

    Serve para provar que o veredito reprova pelos motivos ESTRUTURAIS — vínculo
    ausente, backend faltando, hostname contraditório — e não por acaso.
    """
    contador = {'n': 0}

    def falso(base_url, chave, hops, *, xff=None, cf_=None, tc_=None,
              reivindicacao='', alternativa='', **resto):
        contador['n'] += 1
        cabecalho_cf = resto.get('cf', cf_)
        cabecalho_tc = resto.get('tc', tc_)
        if alt_contradiz and 'alternativo' in base_url:
            return _resposta(hops=hops, cadeia_tamanho=3 + contador['n'] % 2)
        if cabecalho_cf is not None:
            return _resposta(hops=hops, cf_connecting_ip=cf)
        if cabecalho_tc is not None:
            return _resposta(hops=hops, true_client_ip=tc)
        if xff is not None:
            # Borda que ANEXA: com 30 sentinelas do cliente mais N da borda,
            # `cadeia[-N]` continua sendo o endereço que a borda escreveu para
            # este chamador — então a reivindicação bate aqui também. É isso
            # que o controle P4 passou a exigir, para separar "sufixo intacto"
            # de "sufixo intacto apontando para um proxy compartilhado".
            return _resposta(hops=hops, cadeia_tamanho=hops + 30,
                             cadeia_maior_que_hops=True,
                             prefixo_do_cliente_presente=True,
                             sentinelas_na_cadeia=30,
                             candidato_bate_com_origem_declarada=(
                                 True if reivindicacao else None))
        bate_alt = None
        if alternativa:
            bate_alt = CERT._canonico(alternativa) == CERT._canonico(reivindicacao)
        return _resposta(hops=hops,
                         candidato_bate_com_origem_declarada=True,
                         candidato_bate_com_origem_alternativa=bate_alt)

    return falso


def _rodar(monkeypatch, sonda=None, **env):
    monkeypatch.setattr(CERT, '_sondar', sonda or _sonda_falsa())
    _env(monkeypatch, **env)
    return CERT.main()


def _base(estado, **extra):
    valores = {
        'EPI_IDENT_CORP_URL': 'https://corporativo.invalid',
        'EPI_IDENT_CORP_KEY': 'k1',
        'EPI_IDENT_SAAS_URL': 'https://saas.invalid',
        'EPI_IDENT_SAAS_KEY': 'k2',
        'EPI_IDENT_ESTADO': str(estado),
        'EPI_IDENT_HOPS': '3',
    }
    valores.update(extra)
    return valores


# ── R05B-11: P2 precisa de LASTRO na primeira origem ────────────────────────

def test_r05b_11_p2_sem_lastro_nao_certifica(monkeypatch, tmp_path, capsys):
    """Achado P1 do Codex, e o mais grave dos três.

    `EPI_IDENT_IP_ANTERIOR` com QUALQUER endereço válido diferente do candidato
    fazia `candidato_bate_com_origem_alternativa` dar `False`, e o veredito
    lia isso como prova de duas origens. Um erro de digitação — ou um endereço
    inventado — certificava `ORIGEM_A != ORIGEM_B` de uma máquina só, sem a
    origem A ter existido.
    """
    if CERT is None:
        return

    # (a) o veredito rejeita o alvo sem vínculo
    ok, pendente, motivo = CERT._veredito(_alvo(ligado=False), True)
    assert not ok and not pendente, 'P2 sem lastro passou pelo veredito'
    assert 'lastro' in motivo

    # (b) ponta a ponta: origem única + endereço anterior inventado
    estado = tmp_path / 'estado.json'
    codigo = _rodar(monkeypatch, **_base(estado, EPI_IDENT_ORIGEM='B',
                                         EPI_IDENT_MEU_IP=_IP_B,
                                         EPI_IDENT_IP_ANTERIOR=_IP_A))
    assert codigo != 0, 'uma máquina só certificou duas origens'
    assert 'ORIGEM_A != ORIGEM_B' not in capsys.readouterr().out

    # (c) A e depois B, de verdade: aí sim fecha
    assert _rodar(monkeypatch, **_base(estado, EPI_IDENT_ORIGEM='A',
                                       EPI_IDENT_MEU_IP=_IP_A)) == 3
    assert estado.exists(), 'a origem A não gravou o compromisso'
    assert _IP_A not in estado.read_text(encoding='utf-8'), \
        'o compromisso guardou o endereço em claro'

    assert _rodar(monkeypatch, **_base(estado, EPI_IDENT_ORIGEM='B',
                                       EPI_IDENT_MEU_IP=_IP_B,
                                       EPI_IDENT_IP_ANTERIOR=_IP_A)) == 0


def test_r05b_11b_o_vinculo_recusa_cada_atalho(tmp_path):
    """Cada caminho que transformaria declaração em medição."""
    if CERT is None:
        return

    sal = 'ab' * 32
    bom = {'versao': CERT.VERSAO_DO_ESTADO, 'origem': 'A', 'hops': 3, 'sal': sal,
           'compromisso': CERT._compromisso(sal, _IP_A),
           'backends_com_p1': ['corporativo', 'saas']}
    nomes = ['corporativo', 'saas']

    ok, _ = CERT._validar_anterior(bom, _IP_A, 'B', 3, nomes)
    assert ok, 'o caminho legítimo foi recusado'

    for descricao, estado, ip, origem, hops in (
        ('sem estado nenhum', None, _IP_A, 'B', 3),
        ('endereço inventado', bom, '203.0.113.99', 'B', 3),
        ('mesmo rótulo de origem', bom, _IP_A, 'A', 3),
        ('hops diferente', bom, _IP_A, 'B', 4),
        ('backend sem P1 na origem A', {**bom, 'backends_com_p1': ['saas']},
         _IP_A, 'B', 3),
        ('versão desconhecida', {**bom, 'versao': 999}, _IP_A, 'B', 3),
    ):
        ok, _ = CERT._validar_anterior(estado, ip, origem, hops, nomes)
        assert not ok, f'o vínculo aceitou: {descricao}'


# ── R05B-12: os DOIS backends, ou nenhum ────────────────────────────────────

def test_r05b_12_um_backend_so_nao_certifica(monkeypatch, tmp_path, capsys):
    """Achado P1 do Codex. Faltando URL/chave de um lado, `obrigatorios` ficava
    com um alvo só, tudo passava, e o script anunciava "nos dois backends"."""
    if CERT is None:
        return

    env = _base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A', EPI_IDENT_MEU_IP=_IP_A)
    del env['EPI_IDENT_SAAS_URL']
    del env['EPI_IDENT_SAAS_KEY']

    assert _rodar(monkeypatch, **env) == 2, \
        'um backend só produziu resultado diferente de "não executado"'
    saida = capsys.readouterr().out
    assert 'saas' in saida, 'o relatório não disse qual backend faltou'
    assert 'nos dois backends' not in saida


# ── R05B-13: entrada pública contraditória reprova ──────────────────────────

def test_r05b_13_hostname_alternativo_contraditorio_reprova(monkeypatch, tmp_path, capsys):
    """Achado P1 do Codex. Repetições divergentes num hostname público são
    evidência de MAIS DE UM caminho de borda — ataca a premissa de rota do
    critério. Antes isso era reportado como "responde" e ignorado."""
    if CERT is None:
        return

    codigo = _rodar(
        monkeypatch, sonda=_sonda_falsa(alt_contradiz=True),
        **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A', EPI_IDENT_MEU_IP=_IP_A,
                EPI_IDENT_ALT_URL='https://alternativo.invalid',
                EPI_IDENT_ALT_KEY='k3'))

    assert codigo == 1, 'hostname público contraditório não reprovou'
    assert 'cobertura de rota REPROVADA' in capsys.readouterr().out


# ── R05B-14: os guardas de contaminação entram na comparação ────────────────

def test_r05b_14_guardas_de_contaminacao_sao_campos_decisivos():
    """Achado P2 do Codex. São eles que decidem `p1_contaminado`. Fora de
    `CAMPOS_DECISIVOS`, repetições contaminadas passavam por idênticas e o
    script devolvia a primeira amostra — a que parecia limpa."""
    if CERT is None:
        return
    for campo in ('prefixo_do_cliente_presente', 'cadeia_maior_que_hops',
                  'reivindicacao_fora_do_candidato'):
        assert campo in CERT.CAMPOS_DECISIVOS, (
            f'{campo} decide contaminação mas não invalida repetições divergentes'
        )


# ── R05B-15: erro de operador e resposta malformada viram resultado ─────────

def test_r05b_15_entradas_invalidas_nao_viram_traceback(monkeypatch, tmp_path, capsys):
    """Achados P2 do Codex. Os dois produziam exceção fora dos caminhos
    controlados: o operador via traceback, e o shell via status 1 — o MESMO de
    uma propriedade reprovada. Erro de digitação não pode virar evidência."""
    if CERT is None:
        return

    # (a) campo decisivo não escalar
    try:
        CERT._forma('teste', _resposta(cf_connecting_ip=[]))
    except CERT.NaoAlcancado:
        pass
    except Exception as e:  # noqa: BLE001 — é exatamente o que o gate proíbe
        raise AssertionError(f'resposta malformada virou {type(e).__name__}') from e
    else:
        raise AssertionError('resposta malformada passou por válida')

    # (b) hops inválido — erro de digitação vira "não executado", nunca 1
    for ruim in ('abc', '3.5', '0', '-2'):
        codigo = _rodar(monkeypatch, **_base(tmp_path / 'e.json',
                                             EPI_IDENT_ORIGEM='A',
                                             EPI_IDENT_MEU_IP=_IP_A,
                                             EPI_IDENT_HOPS=ruim))
        assert codigo == 2, f'EPI_IDENT_HOPS={ruim!r} não deu "não executado"'

    # (c) vazio ou só espaço é indistinguível de "não definida" no shell, e cair
    # no padrão DOCUMENTADO é o certo. A primeira versão deste gate exigia `2`
    # aqui; quem estava errado era o gate, e enfraquecer o código para satisfazê-lo
    # teria trocado um padrão previsível por uma recusa surpresa.
    for vazio in ('', '   '):
        codigo = _rodar(monkeypatch, **_base(tmp_path / 'e.json',
                                             EPI_IDENT_ORIGEM='A',
                                             EPI_IDENT_MEU_IP=_IP_A,
                                             EPI_IDENT_HOPS=vazio))
        assert codigo == 3, f'EPI_IDENT_HOPS={vazio!r} não caiu no padrão'
    capsys.readouterr()


# ── R05B-16: P3 não some dentro de um "tudo certo" ──────────────────────────

def test_r05b_16_p3_controlado_pelo_cliente_e_denunciado(monkeypatch, tmp_path, capsys):
    """Achado P2 do Codex. `sentinela_sobrevive` significa que o CLIENTE
    controla o cabeçalho de identidade. Não reprova HOPS — P3 não está no
    critério —, mas não pode sair diluído: o relatório tem de gritar."""
    if CERT is None:
        return

    _rodar(monkeypatch, sonda=_sonda_falsa(cf='sentinela_sobrevive'),
           **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A', EPI_IDENT_MEU_IP=_IP_A))
    saida = capsys.readouterr().out
    assert 'ALERTA P3' in saida and 'CF-Connecting-IP' in saida
    assert 'todas as propriedades' not in saida

    _rodar(monkeypatch, sonda=_sonda_falsa(),
           **_base(tmp_path / 'e2.json', EPI_IDENT_ORIGEM='A', EPI_IDENT_MEU_IP=_IP_A))
    assert 'ALERTA P3' not in capsys.readouterr().out, 'alerta falso-positivo'


# ── Segunda rodada da revisão do Codex, sobre a versão já corrigida ─────────
#
# Nove achados novos. O padrão deles é instrutivo: quase todos são "a correção
# anterior fechou metade do caso". Só reprovar a contradição do hostname
# alternativo, e não o negativo estável. Só exigir os dois backends, e não que
# sejam distintos. Só amarrar o IP anterior, e não o endpoint. Só rejeitar
# container, e não campo ausente.

def test_r05b_17_alternativo_com_negativo_estavel_reprova(monkeypatch, tmp_path, capsys):
    """Responder de forma consistente e REPROVAR é pior que se contradizer: é
    uma entrada pública onde a janela `N` não vale. Antes só a contradição
    reprovava, e o negativo estável era anunciado como "entra na matriz"."""
    if CERT is None:
        return

    def sonda(base_url, chave, hops, *, xff=None, reivindicacao='',
              alternativa='', **resto):
        # o alternativo é uma borda mais curta: o candidato vem do cliente
        if 'alternativo' in base_url and resto.get('cf') is None \
                and resto.get('tc') is None and xff is None:
            return _resposta(hops=hops, candidato_bate_com_origem_declarada=False,
                             candidato_e_do_cliente=True)
        return _sonda_falsa()(base_url, chave, hops, xff=xff,
                              reivindicacao=reivindicacao,
                              alternativa=alternativa, **resto)

    codigo = _rodar(monkeypatch, sonda=sonda,
                    **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A',
                            EPI_IDENT_MEU_IP=_IP_A,
                            EPI_IDENT_ALT_URL='https://alternativo.invalid',
                            EPI_IDENT_ALT_KEY='k3'))
    assert codigo == 1, 'entrada pública reprovando não derrubou a certificação'
    assert 'cobertura de rota REPROVADA' in capsys.readouterr().out


def test_r05b_18_os_dois_backends_precisam_ser_distintos(monkeypatch, tmp_path, capsys):
    """Exigir as duas variáveis não basta: apontadas para o MESMO endpoint, um
    deployment se compara consigo mesmo e passa por dois."""
    if CERT is None:
        return

    mesma = 'https://corporativo.invalid'
    codigo = _rodar(monkeypatch, **_base(tmp_path / 'e.json',
                                         EPI_IDENT_ORIGEM='A',
                                         EPI_IDENT_MEU_IP=_IP_A,
                                         EPI_IDENT_SAAS_URL=mesma))
    assert codigo == 2, 'o mesmo endpoint certificou os dois backends'
    assert 'MESMO endpoint' in capsys.readouterr().out


def test_r05b_19_o_vinculo_amarra_tambem_o_endpoint(tmp_path):
    """Os rótulos são estáticos. Sem as URLs, trocar um endpoint entre a origem
    A e a B deixaria combinar P1 de um serviço com P2 de outro."""
    if CERT is None:
        return

    sal = 'cd' * 32
    urls = {'corporativo': 'https://corp.invalid', 'saas': 'https://saas.invalid'}
    estado = {'versao': CERT.VERSAO_DO_ESTADO, 'origem': 'A', 'hops': 3, 'sal': sal,
              'compromisso': CERT._compromisso(sal, _IP_A),
              'backends_com_p1': ['corporativo', 'saas'],
              'urls': dict(urls)}
    nomes = ['corporativo', 'saas']

    ok, _ = CERT._validar_anterior(estado, _IP_A, 'B', 3, nomes, urls)
    assert ok, 'o caminho legítimo foi recusado'

    trocada = dict(urls, saas='https://outro.invalid')
    ok, motivo = CERT._validar_anterior(estado, _IP_A, 'B', 3, nomes, trocada)
    assert not ok, 'endpoint trocado entre as origens passou'
    assert 'outro endpoint' in motivo

    sem_urls = {k: v for k, v in estado.items() if k != 'urls'}
    ok, _ = CERT._validar_anterior(sem_urls, _IP_A, 'B', 3, nomes, urls)
    assert not ok, 'estado sem as URLs foi aceito'


def test_r05b_20_campo_ausente_nao_vira_guarda_falsa():
    """`None` é escalar. Uma sonda que OMITA um guarda de contaminação fazia
    `.get()` devolver `None`, o campo passava, e `p1_contaminado` virava False —
    um P1 sem guarda nenhuma certificaria."""
    if CERT is None:
        return

    for guarda in ('prefixo_do_cliente_presente', 'cadeia_maior_que_hops',
                   'reivindicacao_fora_do_candidato'):
        amostra = _resposta()
        del amostra[guarda]
        try:
            CERT._forma('teste', amostra)
        except CERT.NaoAlcancado as e:
            assert guarda in str(e)
        else:
            raise AssertionError(f'{guarda} ausente passou por válido')

    for campo, ruim in (('cadeia_tamanho', True),
                        ('candidato_e_do_cliente', 'sim'),
                        ('cf_connecting_ip', 'inventada')):
        try:
            CERT._forma('teste', _resposta(**{campo: ruim}))
        except CERT.NaoAlcancado:
            pass
        else:
            raise AssertionError(f'{campo}={ruim!r} passou por válido')


def test_r05b_21_hops_avaliado_tem_de_bater_com_o_pedido(monkeypatch, tmp_path, capsys):
    """`_hops_pedido` satura em HOPS_MAXIMO, e uma sonda de outra versão pode
    interpretar o cabeçalho de outro jeito. Certificar a janela errada é
    certificar nada."""
    if CERT is None:
        return

    def sonda_que_avalia_outro(base_url, chave, hops, **resto):
        resposta = _sonda_falsa()(base_url, chave, hops, **resto)
        resposta['hops_avaliado'] = hops - 1
        return resposta

    codigo = _rodar(monkeypatch, sonda=sonda_que_avalia_outro,
                    **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A',
                            EPI_IDENT_MEU_IP=_IP_A))
    assert codigo != 0, 'janela diferente da pedida foi certificada'
    assert 'janela diferente' in capsys.readouterr().out


def test_r05b_22_o_compromisso_nao_e_enumeravel_em_segundos():
    """O sal impede tabela precomputada e NÃO impede enumeração: IPv4 tem 2^32
    valores. Quem tivesse o arquivo — que o roteiro manda levar entre máquinas —
    recuperaria o endereço em segundos com SHA-256."""
    if CERT is None:
        return

    sal = 'ef' * 32
    obtido = CERT._compromisso(sal, _IP_A)
    ingenuo = hashlib.sha256(bytes.fromhex(sal) + _IP_A.encode()).hexdigest()
    assert obtido != ingenuo, 'o compromisso voltou a ser sha256 de custo zero'

    fonte = SCRIPT.read_text(encoding='utf-8')
    assert 'hashlib.scrypt' in fonte, 'o compromisso deixou de usar KDF de custo'

    # e continua determinístico, senão o vínculo nunca bateria
    assert CERT._compromisso(sal, _IP_A) == obtido
    assert CERT._compromisso(sal, _IP_B) != obtido


def test_r05b_23_nenhum_gate_depende_do_que_some_no_fechamento():
    """Meta-gate. `R05B-7` exige que o script suma quando o contrato fechar;
    qualquer teste que o leia sem guarda torna o estado fechado inalcançável
    com a suíte verde — e aí a promessa de remoção não é executável."""
    import ast

    # Fronteira de função por `ast`, não por "próxima linha que começa com
    # `def test_`". A primeira versão deste gate usava a heurística de texto, e
    # engolia os helpers de módulo que ficam ENTRE os testes — acusou o
    # `R05B-10`, que não usa CERT. Gate que erra a fronteira acusa o inocente e
    # deixa passar o culpado.
    fonte = Path(__file__).read_text(encoding='utf-8')
    arvore = ast.parse(fonte)

    for no in arvore.body:
        if not isinstance(no, ast.FunctionDef) or not no.name.startswith('test_'):
            continue
        corpo = ast.get_source_segment(fonte, no) or ''
        nome = no.name
        if 'CERT.' in corpo:
            assert 'if CERT is None' in corpo, (
                f'{nome} usa CERT sem guarda: com o contrato fechado a suíte '
                'quebraria em vez de provar a remoção'
            )
        for alvo in ('SCRIPT.read_text', 'SONDA_MODULO.read_text'):
            if alvo in corpo:
                assert ('.exists()' in corpo) or ('if CERT is None' in corpo), (
                    f'{nome} lê {alvo} sem conferir que o arquivo existe'
                )


# ── Terceira rodada da revisão ──────────────────────────────────────────────
#
# O padrão das duas rodadas anteriores se repetiu: cada correção minha abriu a
# lacuna vizinha. Reprovei o alternativo contraditório e depois o negativo
# estável — e deixei o alternativo EMPRESTAR o vínculo dos obrigatórios.

def test_r05b_24_o_veredito_do_alternativo_nao_depende_de_p2(monkeypatch, tmp_path, capsys):
    """O estado da primeira origem não guarda evidência para o alternativo,
    então `p2_alt` não significa nada ali. Emprestar o vínculo dos obrigatórios
    fazia o veredito do alternativo depender de um dado que ele não tem.

    A primeira versão deste gate não pegava a regressão: no cenário que montei,
    emprestar ou não dava o MESMO resultado observável. A propriedade que
    separa as duas versões é esta — mesma medição, `p2_alt` trocado, veredito
    tem de ser igual.
    """
    if CERT is None:
        return

    # sem lastro próprio, mesmo com tudo verdadeiro, nunca é OK
    ok, pendente, _ = CERT._veredito(_alvo(), False)
    assert not ok and pendente, 'o alternativo certificou sem lastro próprio'

    def roda_alt(p2_alt):
        def sonda(base_url, chave, hops, *, xff=None, reivindicacao='',
                  alternativa='', **resto):
            resposta = _sonda_falsa()(base_url, chave, hops, xff=xff,
                                      reivindicacao=reivindicacao,
                                      alternativa=alternativa, **resto)
            if 'alternativo' in base_url and alternativa:
                resposta['candidato_bate_com_origem_alternativa'] = p2_alt
            return resposta
        return sonda

    resultados = []
    for p2_alt in (False, True):
        estado = tmp_path / f'e{int(p2_alt)}.json'
        comum = dict(EPI_IDENT_ALT_URL='https://alternativo.invalid',
                     EPI_IDENT_ALT_KEY='k3')
        assert _rodar(monkeypatch, sonda=roda_alt(p2_alt),
                      **_base(estado, EPI_IDENT_ORIGEM='A',
                              EPI_IDENT_MEU_IP=_IP_A, **comum)) == 3
        resultados.append(_rodar(monkeypatch, sonda=roda_alt(p2_alt),
                                 **_base(estado, EPI_IDENT_ORIGEM='B',
                                         EPI_IDENT_MEU_IP=_IP_B,
                                         EPI_IDENT_IP_ANTERIOR=_IP_A, **comum)))
        capsys.readouterr()

    assert resultados[0] == resultados[1], (
        f'o veredito do alternativo mudou com p2_alt: {resultados} — ele está '
        'usando um vínculo que não é dele'
    )
    assert resultados[0] == 0


def test_r05b_25_estado_malformado_nao_vira_traceback(tmp_path, monkeypatch):
    """JSON válido não é esquema válido. `backends_com_p1` como inteiro fazia
    `set(...)` levantar TypeError fora de todo caminho controlado."""
    if CERT is None:
        return

    sal = 'ab' * 32
    bom = {'versao': CERT.VERSAO_DO_ESTADO, 'origem': 'A', 'hops': 3, 'sal': sal,
           'compromisso': CERT._compromisso(sal, _IP_A),
           'backends_com_p1': ['corporativo', 'saas'],
           'urls': {'corporativo': 'https://c.invalid', 'saas': 'https://s.invalid'}}

    caminho = tmp_path / 'estado.json'
    monkeypatch.setenv('EPI_IDENT_ESTADO', str(caminho))

    caminho.write_text(json.dumps(bom), encoding='utf-8')
    assert CERT._ler_estado() is not None, 'o estado legítimo foi recusado'

    for descricao, mudanca in (
        ('backends como inteiro', {'backends_com_p1': 7}),
        ('backends com item não-string', {'backends_com_p1': [1, 2]}),
        ('urls como lista', {'urls': ['a', 'b']}),
        ('urls com valor não-string', {'urls': {'corporativo': 9}}),
        ('hops como texto', {'hops': 'tres'}),
        ('sal não-hexadecimal', {'sal': 'zz'}),
        ('campo faltando', {'compromisso': None}),
    ):
        caminho.write_text(json.dumps({**bom, **mudanca}), encoding='utf-8')
        assert CERT._ler_estado() is None, f'estado aceito com {descricao}'


def test_r05b_26_o_sentinela_e_procurado_em_todo_o_cabecalho():
    """Uma borda que ANTEPÕE o próprio endereço e preserva o do cliente à
    direita — `real, 192.0.2.10` — fazia a leitura do primeiro elemento dizer
    `substituida` com o sentinela vivo na mesma linha. Falso `substituida` é o
    erro caro: leva a ADOTAR um cabeçalho que o cliente controla."""
    if SONDA is None:
        return

    for nome, campo in (('CF-Connecting-Ip', 'cf_connecting_ip'),
                        ('True-Client-Ip', 'true_client_ip')):
        for valor in ('192.0.2.10',
                      '198.51.100.7, 192.0.2.10',
                      '198.51.100.7,192.0.2.10,198.51.100.8'):
            saida = SONDA.medir(_HandlerFalso(**{nome: valor}))
            assert saida[campo] == 'sentinela_sobrevive', (
                f'{nome} = {valor!r} foi classificado {saida[campo]!r}'
            )

        saida = SONDA.medir(_HandlerFalso(**{nome: '198.51.100.7, 198.51.100.8'}))
        assert saida[campo] == 'substituida', 'classificou sentinela onde não há'


def test_r05b_27_p4_confere_identidade_e_nao_so_o_sufixo(monkeypatch, tmp_path, capsys):
    """Sufixo intacto não basta. Com cadeia longa, `cadeia[-N]` pode virar um
    proxy compartilhado SEM sentinela nenhum: P1 passa na rota sem cabeçalho,
    P4 passa com outro candidato, e as requisições de cadeia longa colapsam
    num balde só. É a distinção B/C dentro do controle."""
    if CERT is None:
        return

    def colapso_na_cadeia_longa(base_url, chave, hops, *, xff=None,
                                reivindicacao='', alternativa='', **resto):
        resposta = _sonda_falsa()(base_url, chave, hops, xff=xff,
                                  reivindicacao=reivindicacao,
                                  alternativa=alternativa, **resto)
        if xff is not None:
            # sufixo sem sentinela, candidato não é do cliente — e mesmo assim
            # não é o chamador: é o proxy compartilhado
            resposta['candidato_bate_com_origem_declarada'] = False
        return resposta

    codigo = _rodar(monkeypatch, sonda=colapso_na_cadeia_longa,
                    **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A',
                            EPI_IDENT_MEU_IP=_IP_A))
    assert codigo != 0, 'colapso na rota de cadeia longa passou por P4'
    assert 'P4 falso' in capsys.readouterr().out


def test_r05b_28_alternativo_pela_metade_e_configuracao_incompleta(monkeypatch, tmp_path, capsys):
    """URL sem chave não é "não investigado": é o operador pedindo para
    investigar e o alvo sendo pulado em silêncio."""
    if CERT is None:
        return

    for parcial in ({'EPI_IDENT_ALT_URL': 'https://alternativo.invalid'},
                    {'EPI_IDENT_ALT_KEY': 'k3'}):
        codigo = _rodar(monkeypatch, **_base(tmp_path / 'e.json',
                                             EPI_IDENT_ORIGEM='A',
                                             EPI_IDENT_MEU_IP=_IP_A, **parcial))
        assert codigo == 2, f'alternativo pela metade ({parcial}) foi ignorado'
        assert 'pela metade' in capsys.readouterr().out


def test_r05b_29_urls_equivalentes_contam_como_o_mesmo_endpoint(monkeypatch, tmp_path, capsys):
    """`https://host` e `https://host:443` vão para o mesmo lugar. Comparar
    texto cru deixava um deployment passar por dois."""
    if CERT is None:
        return

    assert CERT._normalizar_url('https://h.invalid') == \
           CERT._normalizar_url('https://H.invalid:443/')
    assert CERT._normalizar_url('http://h.invalid:80') == \
           CERT._normalizar_url('http://h.invalid')
    assert CERT._normalizar_url('https://h.invalid') != \
           CERT._normalizar_url('https://h.invalid:8443')

    codigo = _rodar(monkeypatch, **_base(tmp_path / 'e.json',
                                         EPI_IDENT_ORIGEM='A',
                                         EPI_IDENT_MEU_IP=_IP_A,
                                         EPI_IDENT_SAAS_URL='https://corporativo.invalid:443/'))
    assert codigo == 2, 'o mesmo endpoint com outra grafia passou por dois'
    assert 'MESMO endpoint' in capsys.readouterr().out


# ── Quarta rodada da revisão ────────────────────────────────────────────────

def test_r05b_30_sentinela_mapeado_em_ipv6_nao_fica_invisivel():
    """`_e_sentinela` alimenta SEIS campos, não só P3. Uma borda que preserve o
    sentinela e o escreva como `::ffff:192.0.2.10` deixaria todas as guardas de
    contaminação cegas ao mesmo tempo — e um cabeçalho controlado pelo cliente
    passaria por `substituida`, que é o erro que leva a ADOTÁ-LO."""
    if SONDA is None:
        return

    for grafia in ('192.0.2.10', '::ffff:192.0.2.10', '::FFFF:192.0.2.10'):
        assert SONDA._e_sentinela(grafia), f'{grafia} não foi reconhecido'
        assert SONDA.medir(
            _HandlerFalso(**{'CF-Connecting-Ip': grafia})
        )['cf_connecting_ip'] == 'sentinela_sobrevive'

    cliente = '203.0.113.9'
    cadeia = ['::ffff:192.0.2.21', '::ffff:192.0.2.22', cliente,
              '198.51.100.200', '198.51.100.201']
    saida = SONDA.analisar(cadeia, 3, cliente, '', {}, [])
    assert saida['prefixo_do_cliente_presente'] is True
    assert saida['sentinelas_na_cadeia'] == 2

    # e o sentinela mapeado DENTRO da janela derruba P4
    dentro = [cliente, '::ffff:192.0.2.30', '198.51.100.200']
    assert SONDA.analisar(dentro, 3, '', '', {}, [])['sufixo_confiavel_preservado'] is False


def test_r05b_31_a_origem_declarada_tem_de_ser_publica(monkeypatch, tmp_path, capsys):
    """Dois candidatos PRIVADOS podem satisfazer as duas execuções sem que haja
    duas origens públicas — e endereços privados se repetem entre redes não
    relacionadas, então não são identidade de rate limit."""
    if CERT is None:
        return

    for privado in ('10.0.0.1', '192.168.1.1', '172.16.0.1', '127.0.0.1',
                    '100.64.0.1', '169.254.1.1', '224.0.0.1', '::1'):
        assert not CERT._origem_plausivel(privado), f'{privado} passou por público'

    # as faixas de documentação existem para os gates, e são aceitas de propósito
    for doc in (_IP_A, _IP_B, '192.0.2.10', '2001:db8::1'):
        assert CERT._origem_plausivel(doc), f'{doc} foi recusado'

    assert _rodar(monkeypatch, **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A',
                                       EPI_IDENT_MEU_IP='10.0.0.1')) == 2
    assert 'não é um endereço público' in capsys.readouterr().out

    assert _rodar(monkeypatch, **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='B',
                                       EPI_IDENT_MEU_IP=_IP_B,
                                       EPI_IDENT_IP_ANTERIOR='192.168.0.7')) == 2
    assert 'IP_ANTERIOR não é um endereço público' in capsys.readouterr().out


def test_r05b_32_p3_divergente_entre_backends_nao_reprova(monkeypatch, tmp_path, capsys):
    """P3 é classificação, não critério de HOPS — o próprio roteiro diz isso.
    Duas bordas podem classificar um cabeçalho de formas legítimas e diferentes,
    e reprovar por causa disso contradizia o contrato documentado."""
    if CERT is None:
        return

    def classes_diferentes(base_url, chave, hops, **resto):
        resposta = _sonda_falsa()(base_url, chave, hops, **resto)
        if 'saas' in base_url and resposta['cf_connecting_ip'] != 'ausente':
            resposta['cf_connecting_ip'] = 'ausente'
        return resposta

    estado = tmp_path / 'e.json'
    assert _rodar(monkeypatch, sonda=classes_diferentes,
                  **_base(estado, EPI_IDENT_ORIGEM='A', EPI_IDENT_MEU_IP=_IP_A)) == 3
    capsys.readouterr()
    codigo = _rodar(monkeypatch, sonda=classes_diferentes,
                    **_base(estado, EPI_IDENT_ORIGEM='B', EPI_IDENT_MEU_IP=_IP_B,
                            EPI_IDENT_IP_ANTERIOR=_IP_A))
    saida = capsys.readouterr().out
    assert codigo == 0, 'divergência de P3 reprovou uma certificação válida'
    assert 'NOTA' in saida and 'Não reprova HOPS' in saida


def test_r05b_33_backend_inalcancavel_e_nao_executado(monkeypatch, tmp_path, capsys):
    """Ausência de medição não é medição que reprovou. Devolver 1 nos dois casos
    impedia automação de distinguir "a sonda não respondeu" de "a produção
    rejeitou a propriedade"."""
    if CERT is None:
        return

    def saas_fora_do_ar(base_url, chave, hops, **resto):
        if 'saas' in base_url:
            raise CERT.NaoAlcancado('sonda desligada ou ausente (404)')
        return _sonda_falsa()(base_url, chave, hops, **resto)

    codigo = _rodar(monkeypatch, sonda=saas_fora_do_ar,
                    **_base(tmp_path / 'e.json', EPI_IDENT_ORIGEM='A',
                            EPI_IDENT_MEU_IP=_IP_A))
    saida = capsys.readouterr().out
    assert codigo == 2, f'backend inalcançável devolveu {codigo}, não "não executado"'
    assert 'backend inalcançável' in saida
    assert 'NÃO é evidência' in saida

    # mas CONTRADIÇÃO é outra coisa: foi medido, e as medições brigam → 1
    def saas_contraditorio(base_url, chave, hops, **resto):
        resposta = _sonda_falsa()(base_url, chave, hops, **resto)
        if 'saas' in base_url:
            resposta['cadeia_tamanho'] = resposta['cadeia_tamanho'] + (id(resposta) % 2)
        return resposta

    codigo = _rodar(monkeypatch, sonda=saas_contraditorio,
                    **_base(tmp_path / 'e2.json', EPI_IDENT_ORIGEM='A',
                            EPI_IDENT_MEU_IP=_IP_A))
    assert codigo in (1, 3), f'contradição devolveu {codigo}'
    capsys.readouterr()


# ── Quinta rodada da revisão ────────────────────────────────────────────────

def test_r05b_34_instancias_repetidas_do_cabecalho_sao_todas_lidas():
    """`HTTPMessage.get()` devolve só a PRIMEIRA instância. Uma borda que emita
    o próprio endereço numa e preserve o sentinela do cliente noutra fazia a
    classificação dizer `substituida` com o sentinela vivo na requisição — o
    mesmo erro caro do achado da vírgula, pela porta ao lado."""
    if SONDA is None:
        return

    from email.message import Message

    class _Repetido:
        def __init__(self, pares):
            self.headers = Message()
            for chave, valor in pares:
                self.headers[chave] = valor

    for nome, campo in (('CF-Connecting-Ip', 'cf_connecting_ip'),
                        ('True-Client-Ip', 'true_client_ip')):
        sobrevive = SONDA.medir(_Repetido([(nome, '198.51.100.7'),
                                           (nome, '192.0.2.10')]))
        assert sobrevive[campo] == 'sentinela_sobrevive', (
            f'{nome} repetido com sentinela na 2ª instância deu '
            f'{sobrevive[campo]!r}'
        )
        limpo = SONDA.medir(_Repetido([(nome, '198.51.100.7'),
                                       (nome, '198.51.100.8')]))
        assert limpo[campo] == 'substituida', 'classificou sentinela onde não há'

    # e a cadeia repetida vira uma cadeia só, que é a semântica de HTTP
    cadeia = SONDA.medir(_Repetido([('X-Forwarded-For', '192.0.2.21'),
                                    ('X-Forwarded-For', '203.0.113.9, 198.51.100.200')]))
    assert cadeia['cadeia_tamanho'] == 3
    assert cadeia['prefixo_do_cliente_presente'] is True


def test_r05b_35_o_compromisso_nao_sobrevive_a_certificacao(monkeypatch, tmp_path, capsys):
    """O arquivo guarda o sal e o compromisso do endereço público. Mantê-lo
    depois do fechamento o deixa reutilizável como evidência de primeira origem
    em execuções posteriores, quando a topologia já pode ter mudado."""
    if CERT is None:
        return

    estado = tmp_path / 'e.json'
    assert _rodar(monkeypatch, **_base(estado, EPI_IDENT_ORIGEM='A',
                                       EPI_IDENT_MEU_IP=_IP_A)) == 3
    assert estado.exists(), 'a origem A não gravou o compromisso'
    capsys.readouterr()

    assert _rodar(monkeypatch, **_base(estado, EPI_IDENT_ORIGEM='B',
                                       EPI_IDENT_MEU_IP=_IP_B,
                                       EPI_IDENT_IP_ANTERIOR=_IP_A)) == 0
    assert not estado.exists(), 'o compromisso sobreviveu à certificação'
    assert 'apagado' in capsys.readouterr().out


# ── O 403 da medição real: o instrumento jogava fora a evidência ────────────

def _erro_http(codigo, cabecalhos, corpo):
    import email.message
    import io as _io
    import urllib.error
    msg = email.message.Message()
    for chave, valor in cabecalhos:
        msg[chave] = valor
    return urllib.error.HTTPError(
        'https://exemplo.invalid/api/origin-identity-diagnostics',
        codigo, 'Forbidden', msg, _io.BytesIO(corpo.encode('utf-8')))


def test_r05b_36_erro_http_identifica_a_camada_sem_vazar_nada():
    """A medição real devolveu `HTTP 403` nos dois backends e nada mais. Com
    isso não dá para saber se quem recusou foi a aplicação ou a borda — e a
    aplicação, exercitada no caminho HTTP real, só devolve 200 ou 404.

    O instrumento tinha a resposta na mão e a descartava: `_sondar` colapsava
    todo HTTPError não-404 em `HTTP {code}`, jogando fora cabeçalhos e corpo,
    que são justamente o que distingue as camadas.

    Nada do corpo pode sair no relatório: a página de bloqueio da Cloudflare
    EXIBE o endereço do visitante, e o relatório vai ser colado numa revisão.
    """
    if CERT is None:
        return

    cenarios = [
        ('borda',
         [('Server', 'cloudflare'), ('CF-Ray', '8f0a1b2c3d4e5f60-GRU'),
          ('Content-Type', 'text/html; charset=UTF-8')],
         '<!DOCTYPE html><html><body>Sorry, you have been blocked. '
         'Your IP: 203.0.113.77 · Cloudflare Ray ID: 8f0a</body></html>'),
        ('aplicacao',
         [('Content-Type', 'application/json')],
         '{"error": "Acesso negado."}'),
    ]

    for esperado, cabecalhos, corpo in cenarios:
        erro = _erro_http(403, cabecalhos, corpo)

        class _Abridor:
            def open(self, *a, **k):
                raise erro

        original = CERT._ABRIDOR
        CERT._ABRIDOR = _Abridor()
        try:
            CERT._sondar('https://exemplo.invalid', 'k', 3)
        except CERT.NaoAlcancado as e:
            texto = str(e)
        finally:
            CERT._ABRIDOR = original

        assert '403' in texto, f'o status sumiu: {texto!r}'
        assert esperado in texto, (
            f'não identificou a camada {esperado!r}: {texto!r}'
        )
        # e NADA do corpo, que numa página de bloqueio traz o IP do visitante
        assert '203.0.113.77' not in texto, f'vazou endereço do corpo: {texto!r}'
        assert 'Sorry, you have been blocked' not in texto, \
            f'ecoou o corpo da resposta: {texto!r}'


def test_r05b_37_a_aplicacao_nunca_devolve_403_nesta_rota():
    """Reprodução do caminho HTTP REAL, contra o `EpiHandler` de verdade.

    É esta a evidência que move o 403 da medição para fora da aplicação: com a
    chave certa a rota devolve 200, com chave errada ou ausente devolve 404, e
    o controle P4 de cadeia longa também passa. 403 não é uma resposta que este
    caminho saiba produzir.
    """
    if SONDA is None:
        return

    import http.client
    import os
    import threading
    from http.server import ThreadingHTTPServer

    import app as APP
    from epi_backend.bootstrap import DB_BOOTSTRAP_STATE, DB_BOOTSTRAP_STATE_LOCK

    chave = 'chave-do-gate-r05b-37'
    anterior = os.environ.get('PROXY_CHAIN_PROBE_KEY')
    os.environ['PROXY_CHAIN_PROBE_KEY'] = chave
    with DB_BOOTSTRAP_STATE_LOCK:
        pronto_antes = DB_BOOTSTRAP_STATE.get('ready')
        DB_BOOTSTRAP_STATE['ready'] = True

    servidor = ThreadingHTTPServer(('127.0.0.1', 0), APP.EpiHandler)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    def pedir(cabecalhos):
        conexao = http.client.HTTPConnection('127.0.0.1', porta, timeout=10)
        conexao.request('GET', '/api/origin-identity-diagnostics', headers=cabecalhos)
        resposta = conexao.getresponse()
        resposta.read()
        conexao.close()
        return resposta.status

    try:
        casos = {
            'chave correta': (
                {'X-Diagnostics-Key': chave, 'X-Probe-Hops': '3',
                 'X-Origin-Claim': '203.0.113.11'}, 200),
            'chave errada': ({'X-Diagnostics-Key': 'outra'}, 404),
            'sem chave': ({'X-Probe-Hops': '3'}, 404),
            'cadeia longa (P4)': (
                {'X-Diagnostics-Key': chave, 'X-Probe-Hops': '3',
                 'X-Forwarded-For': ', '.join(f'192.0.2.{n}' for n in range(20, 50))},
                200),
        }
        for rotulo, (cabecalhos, esperado) in casos.items():
            obtido = pedir(cabecalhos)
            assert obtido == esperado, (
                f'{rotulo}: esperado {esperado}, veio {obtido}'
            )
            assert obtido != 403, f'{rotulo}: a aplicação devolveu 403'
    finally:
        servidor.shutdown()
        servidor.server_close()
        with DB_BOOTSTRAP_STATE_LOCK:
            DB_BOOTSTRAP_STATE['ready'] = pronto_antes
        if anterior is None:
            os.environ.pop('PROXY_CHAIN_PROBE_KEY', None)
        else:
            os.environ['PROXY_CHAIN_PROBE_KEY'] = anterior


# ── O 503 da triagem: o portão de bootstrap intercepta a sonda ──────────────

def test_r05b_38_a_sonda_e_interceptada_pelo_portao_de_bootstrap():
    """A triagem sem chave devolveu 503 nos dois backends, com
    `content-type: application/json` e `x-render-origin-server:
    SimpleHTTP/0.6 Python/…` — isto é, a própria aplicação respondendo.

    Este gate reproduz essa interceptação e trava o formato: enquanto o
    bootstrap não estiver pronto, TODA rota `/api/` fora da lista de isenção —
    inclusive a sonda — responde 503 antes do handler. Não é a sonda recusando
    nada; ela nem é alcançada.
    """
    if SONDA is None:
        return

    import http.client
    import os
    import threading
    from http.server import ThreadingHTTPServer

    import app as APP
    from epi_backend.bootstrap import (BOOTSTRAP_READY_EXEMPT_PATHS,
                                       DB_BOOTSTRAP_STATE,
                                       DB_BOOTSTRAP_STATE_LOCK)

    # A rota da sonda NÃO é isenta, e isso é decisão registrada: isentá-la a
    # tornaria alcançável num estado em que o resto da API não está, e faria
    # medir topologia de um serviço que não está servindo.
    assert '/api/origin-identity-diagnostics' not in BOOTSTRAP_READY_EXEMPT_PATHS

    chave = 'chave-do-gate-r05b-38'
    anterior = os.environ.get('PROXY_CHAIN_PROBE_KEY')
    os.environ['PROXY_CHAIN_PROBE_KEY'] = chave
    with DB_BOOTSTRAP_STATE_LOCK:
        pronto_antes = DB_BOOTSTRAP_STATE.get('ready')
        DB_BOOTSTRAP_STATE['ready'] = False

    servidor = ThreadingHTTPServer(('127.0.0.1', 0), APP.EpiHandler)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    def pedir(rota, cabecalhos=None):
        conexao = http.client.HTTPConnection('127.0.0.1', porta, timeout=10)
        conexao.request('GET', rota, headers=cabecalhos or {})
        resposta = conexao.getresponse()
        corpo = resposta.read().decode('utf-8', 'replace')
        cabecalho = {
            'server': resposta.getheader('Server') or '',
            'content-type': resposta.getheader('Content-Type') or '',
        }
        conexao.close()
        return resposta.status, cabecalho, corpo

    try:
        # com a chave CERTA e o bootstrap pendente: 503, não 200 e não 404
        status, cabecalhos, corpo = pedir(
            '/api/origin-identity-diagnostics', {'X-Diagnostics-Key': chave})
        assert status == 503, f'esperado 503 do portão, veio {status}'
        assert cabecalhos['content-type'] == 'application/json; charset=utf-8'
        assert cabecalhos['server'].startswith('SimpleHTTP/'), cabecalhos['server']
        assert 'DB_BOOTSTRAP_NOT_READY' in corpo

        # e o diagnóstico keyless que diz POR QUE, fora de `/api/`
        status_saude, _, corpo_saude = pedir('/health/ready')
        assert status_saude == 503
        assert 'DB_BOOTSTRAP_NOT_READY' in corpo_saude
        assert 'phase' in corpo_saude, 'a saúde precisa dizer a fase do bootstrap'

        # com o bootstrap pronto, a mesma requisição volta a ser da sonda
        with DB_BOOTSTRAP_STATE_LOCK:
            DB_BOOTSTRAP_STATE['ready'] = True
        status, _, _ = pedir('/api/origin-identity-diagnostics',
                             {'X-Diagnostics-Key': chave})
        assert status == 200, f'com bootstrap pronto esperava 200, veio {status}'
    finally:
        servidor.shutdown()
        servidor.server_close()
        with DB_BOOTSTRAP_STATE_LOCK:
            DB_BOOTSTRAP_STATE['ready'] = pronto_antes
        if anterior is None:
            os.environ.pop('PROXY_CHAIN_PROBE_KEY', None)
        else:
            os.environ['PROXY_CHAIN_PROBE_KEY'] = anterior
