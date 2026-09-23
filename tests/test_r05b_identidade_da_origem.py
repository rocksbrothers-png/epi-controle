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
import importlib.util
import re
from pathlib import Path

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

    atual = hashlib.sha256(_bloco().encode('utf-8')).hexdigest()
    assert atual == DIGESTO_CONTRATO_R05B, (
        'o contrato R0.5B mudou sem o digesto ser recalculado nos DOIS '
        f'repositórios. Atual: {atual}'
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
    a.p4 = kwargs.get('p4', True)
    a.candidato_do_cliente = kwargs.get('do_cliente', False)
    return a


def test_r05b_6a_p1_falso_nao_passa():
    """Sabotagem E."""
    ok, pendente, _ = CERT._veredito(_alvo(p1=False), True)
    assert not ok and not pendente

    ok, _, _ = CERT._veredito(_alvo(contaminado=True), True)
    assert not ok, 'P1 contaminado foi tratado como aprovado'

    ok, _, _ = CERT._veredito(_alvo(do_cliente=True), True)
    assert not ok, 'candidato vindo do cliente foi tratado como aprovado'


def test_r05b_6b_uma_origem_so_nao_certifica():
    """Sabotagem F. Sem a segunda origem o resultado é PENDENTE, nunca OK."""
    ok, pendente, _ = CERT._veredito(_alvo(), False)
    assert not ok and pendente, 'uma origem só passou por certificação completa'

    ok, pendente, _ = CERT._veredito(_alvo(), True)
    assert ok and not pendente, 'com as duas origens o gate precisa deixar fechar'


def test_r05b_6c_mesma_origem_duas_vezes_nao_conta_como_duas():
    """Sabotagem G. Se o candidato desta origem é o endereço declarado da
    anterior, as duas execuções vieram do mesmo caminho."""
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
    ok, pendente, motivo = CERT._veredito(_alvo(p4=False), True)
    assert not ok and not pendente
    assert 'P4' in motivo


# ── R05B-10: nenhum endereço real na fatia ──────────────────────────────────

FAIXAS_SEGURAS = (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
    '100.64.0.0/10', '127.0.0.0/8', '0.0.0.0/8',
)


def test_r05b_10_nenhum_endereco_real_na_fatia():
    import ipaddress

    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    padrao = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
    alvos = [CONTRATO, Path(__file__), SCRIPT]
    if SONDA_MODULO.exists():
        alvos.append(SONDA_MODULO)
    for caminho in alvos:
        for literal in set(padrao.findall(caminho.read_text(encoding='utf-8'))):
            try:
                endereco = ipaddress.ip_address(literal)
            except ValueError:
                continue
            assert any(endereco in faixa for faixa in faixas), (
                f'{caminho.name} contém {literal}, que não é de faixa reservada'
            )
