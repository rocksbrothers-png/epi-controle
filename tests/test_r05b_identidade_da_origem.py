"""R0.5B — gates que protegem PRODUÇÃO.

Esta suíte não certifica nada. Ela garante oito propriedades que precisam valer
independentemente do resultado da medição:

  R05B-1  o contrato dirige a existência da sonda, e inverte sozinho
  R05B-2  a sonda nunca devolve endereço
  R05B-3  sem chave, a rota é indistinguível de rota inexistente
  R05B-4  o `hops` avaliado é o pedido, e um `hops` errado é detectável
  R05B-5  nenhum endereço real fica versionado nesta fatia
  R05B-6  nenhuma configuração de proxy é aplicada antes da evidência
  R05B-7  o limitador não lê cabeçalho de identidade não certificado
  R05B-8  o que a sonda mede é o que `core/rate_limit.py` vai usar

O certificador de ~1.550 linhas e os 62 gates que só o protegiam foram
removidos na simplificação de 24/09 — ver o histórico em
`docs/R05B_IDENTIDADE_DA_ORIGEM.md`.
"""
from __future__ import annotations

import hashlib
import importlib
import ipaddress
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / 'docs' / 'R05B_IDENTIDADE_DA_ORIGEM.md'
SONDA_MODULO = RAIZ / 'epi_backend' / 'proxy_identity_probe.py'
ROTAS = RAIZ / 'modules' / 'auth' / 'routes.py'
LIMITADOR = RAIZ / 'core' / 'rate_limit.py'
EXEMPLO_ENV = RAIZ / 'env.example'

#: Digesto do bloco de contrato. Fechar a identidade exige recalcular — o que
#: obriga a passar por aqui de propósito, e não por acidente de edição.
DIGESTO_CONTRATO = '0b9901d5bb2cc1d62a65568ce2e435152e23dc0c517047b9a652d5cd1bce8bbf'

ESTADOS_VALIDOS = ('INDETERMINADO', 'DETERMINADA')

try:
    SONDA = importlib.import_module('epi_backend.proxy_identity_probe')
except ImportError:                                   # contrato fechado
    SONDA = None

#: O nome da variável vem da SONDA, nunca como literal aqui. Assim ele sai do
#: repositório junto com ela, e o gate `R05-6` — que no fechamento proíbe
#: qualquer leitura da chave — continua verdadeiro sem exceção para os testes.
NOME_DA_CHAVE = SONDA.NOME_DA_VARIAVEL if SONDA else None


def _bloco_do_contrato() -> str:
    texto = CONTRATO.read_text(encoding='utf-8')
    achado = re.search(
        r'<!-- CONTRATO-R05B-INICIO -->\n(.*?)<!-- CONTRATO-R05B-FIM -->',
        texto, re.DOTALL)
    assert achado, 'o bloco de contrato sumiu do documento'
    return achado.group(1)


def _leitores_da_chave() -> list:
    """Arquivos de RUNTIME que mencionam o nome da variável.

    Testes ficam de fora de propósito: um gate que nomeia a chave para proibir
    sua leitura não é uma superfície que a lê.
    """
    if not NOME_DA_CHAVE:
        return []
    return [p for p in RAIZ.rglob('*.py')
            if 'tests' not in p.parts
            and NOME_DA_CHAVE in p.read_text(encoding='utf-8', errors='ignore')]


def _estado() -> str:
    achado = re.search(r'ESTADO-DA-IDENTIDADE:\s*(\S+)', _bloco_do_contrato())
    assert achado, 'o contrato não declara ESTADO-DA-IDENTIDADE'
    return achado.group(1)


class _Req:
    """Requisição falsa. `get` devolve a PRIMEIRA instância, como HTTPMessage."""

    def __init__(self, **cabecalhos):
        self._c = {k.replace('_', '-'): (v if isinstance(v, list) else [v])
                   for k, v in cabecalhos.items()}

    def get(self, nome, default=''):
        return self._c.get(nome, [default])[0]

    def get_all(self, nome):
        return self._c.get(nome)

    @property
    def headers(self):
        return self


# ── R05B-1 ──────────────────────────────────────────────────────────────────
def test_r05b_1_o_contrato_dirige_a_existencia_da_sonda():
    """O contrato é a chave: o gate inverte junto com ele, sem edição.

    INDETERMINADO → a sonda pode existir, e só ela lê a chave.
    DETERMINADA   → sonda, rota e qualquer leitura da chave são proibidas.
    """
    bloco = _bloco_do_contrato()
    estado = _estado()
    assert estado in ESTADOS_VALIDOS, f'estado fora do vocabulário: {estado}'

    atual = hashlib.sha256(bloco.encode('utf-8')).hexdigest()
    assert atual == DIGESTO_CONTRATO, (
        'o bloco de contrato mudou sem que o digesto fosse recalculado — '
        'fechar a identidade tem de ser deliberado'
    )

    rotas = ROTAS.read_text(encoding='utf-8')
    if estado == 'DETERMINADA':
        assert not SONDA_MODULO.exists(), 'a sonda ficou depois do fechamento'
        assert 'origin-identity-diagnostics' not in rotas, 'a rota ficou'
        assert 'proxy_identity_probe' not in rotas, 'o import ficou'
        # A ausência de leitores da chave no estado fechado é do `R05-6`, que
        # varre o repositório inteiro. Aqui o nome nem existe mais: ele veio da
        # sonda, e a sonda acabou de ser removida.
    else:
        assert SONDA_MODULO.exists(), 'contrato aberto e sonda ausente'
        assert 'origin-identity-diagnostics' in rotas, 'contrato aberto e rota ausente'
        # A chave só pode ser lida pela sonda. Qualquer outro leitor amplia a
        # superfície do segredo para além do que o contrato autoriza.
        outros = [p for p in _leitores_da_chave() if p != SONDA_MODULO]
        assert not outros, f'a chave é lida fora da sonda: {outros}'


# ── R05B-2 ──────────────────────────────────────────────────────────────────
def test_r05b_2_a_sonda_nunca_devolve_endereco():
    """Varre a resposta com entradas adversariais.

    Se qualquer valor da resposta contiver um endereço analisável, a sonda
    deixou de ser redigida — e a rota vira vazamento em vez de oráculo.
    """
    if SONDA is None:
        return

    v6 = str(ipaddress.ip_address((0x2001 << 112) | 0xdb8))
    entradas = [
        _Req(X_Forwarded_For='192.0.2.1, 192.0.2.2, 198.51.100.7',
             X_Probe_Hops='3', X_Origin_Claim='198.51.100.7'),
        _Req(X_Forwarded_For=f'{v6}, 203.0.113.9', X_Probe_Hops='2',
             X_Origin_Claim=v6),
        _Req(X_Forwarded_For=['192.0.2.1', '198.51.100.7'], X_Probe_Hops='1',
             X_Origin_Claim='198.51.100.7'),
        _Req(X_Probe_Hops='0', X_Origin_Claim='198.51.100.7'),
    ]
    for req in entradas:
        resposta = SONDA.medir(req)
        for chave, valor in resposta.items():
            if not isinstance(valor, str):
                continue
            for pedaco in re.split(r'[\s,]+', valor):
                try:
                    ipaddress.ip_address(pedaco.strip())
                except ValueError:
                    continue
                raise AssertionError(f'campo {chave!r} devolveu um endereço')


# ── R05B-3 ──────────────────────────────────────────────────────────────────
def test_r05b_3_sem_chave_a_rota_nao_existe(monkeypatch):
    """Falha FECHADA: sem a variável, e com chave errada, não autoriza."""
    if SONDA is None:
        return

    monkeypatch.delenv(SONDA.NOME_DA_VARIAVEL, raising=False)
    assert SONDA.autorizado(_Req(X_Diagnostics_Key='qualquer')) is False, (
        'sem a variável no ambiente a sonda autorizou — a rota deixaria de ser '
        'indistinguível de uma rota inexistente'
    )

    monkeypatch.setenv(SONDA.NOME_DA_VARIAVEL, 'segredo-de-teste')
    assert SONDA.autorizado(_Req(X_Diagnostics_Key='errada')) is False
    assert SONDA.autorizado(_Req()) is False
    assert SONDA.autorizado(_Req(X_Diagnostics_Key='segredo-de-teste')) is True

    # Caractere fora de ASCII não pode virar 500: a exceção distinguiria rota
    # protegida de rota ausente.
    assert SONDA.autorizado(_Req(X_Diagnostics_Key='✓')) is False

    # E a rota responde o 404 do fallthrough, não JSON.
    assert "send_error(404, 'File not found')" in ROTAS.read_text(encoding='utf-8')


# ── R05B-4 ──────────────────────────────────────────────────────────────────
def test_r05b_4_o_hops_avaliado_e_o_pedido():
    """`hops` errado tem de ser DETECTÁVEL, senão a medição não vale nada."""
    if SONDA is None:
        return

    # Cadeia: 3 sentinelas do cliente + 3 escritos pela borda.
    cadeia = ['192.0.2.1', '192.0.2.2', '192.0.2.3',
              '198.51.100.7', '203.0.113.1', '203.0.113.2']

    certo = SONDA.analisar(cadeia, 3, '198.51.100.7')
    assert certo['hops_avaliado'] == 3
    assert certo['candidato_bate_com_origem_declarada'] is True
    assert certo['candidato_e_do_cliente'] is False
    assert certo['prefixo_do_cliente_presente'] is True

    # `hops` grande demais: a janela entra no prefixo do CLIENTE, e isso tem de
    # aparecer — é o que impede certificar a posição errada.
    errado = SONDA.analisar(cadeia, 6, '198.51.100.7')
    assert errado['candidato_e_do_cliente'] is True, (
        'a janela caiu em dado do cliente e a sonda não acusou'
    )
    assert errado['candidato_bate_com_origem_declarada'] is False

    # Cadeia curta: nada a afirmar.
    curta = SONDA.analisar(['198.51.100.7'], 3, '198.51.100.7')
    assert curta['cadeia_suficiente_para_hops'] is False
    assert curta['candidato_bate_com_origem_declarada'] is None

    # `X-Probe-Hops` absurdo satura em vez de explodir.
    assert SONDA.medir(_Req(X_Probe_Hops='999999'))['hops_avaliado'] == SONDA.HOPS_MAXIMO
    assert SONDA.medir(_Req(X_Probe_Hops='nao-numero'))['hops_avaliado'] == 0


# ── R05B-5 ──────────────────────────────────────────────────────────────────
FAIXAS_SEGURAS = (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10',
    '127.0.0.0/8', '0.0.0.0/8', '169.254.0.0/16', '224.0.0.0/4', '240.0.0.0/4',
    '2001:db8::/32', 'fc00::/7', 'fe80::/10', 'ff00::/8', '100::/64',
)
_TOKEN = re.compile(r'[0-9A-Fa-f:][0-9A-Fa-f.:]*')


def _enderecos(texto: str) -> list:
    achados = []
    for bruto in _TOKEN.findall(texto):
        candidato = bruto
        while candidato:
            try:
                achados.append(ipaddress.ip_address(candidato))
                break
            except ValueError:
                candidato = candidato[:-1]
    return achados


def _seguro(endereco, faixas) -> bool:
    """Toda forma IPv6 que EMBUTE um IPv4 é julgada por esse IPv4."""
    if endereco.version == 6 and int(endereco) < 2 ** 32:
        endereco = ipaddress.ip_address(int(endereco))
    elif getattr(endereco, 'ipv4_mapped', None) is not None:
        endereco = endereco.ipv4_mapped
    return any(endereco in f for f in faixas if f.version == endereco.version)


def test_r05b_5_nenhum_endereco_real_na_fatia():
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    alvos = [CONTRATO, Path(__file__)] + [p for p in (SONDA_MODULO,) if p.exists()]
    for caminho in alvos:
        for endereco in _enderecos(caminho.read_text(encoding='utf-8')):
            # A mensagem NÃO ecoa o endereço: o gate existe para impedir que
            # endereço real seja gravado, e não pode publicá-lo no log do CI.
            assert _seguro(endereco, faixas), (
                f'{caminho.name} tem um endereço IPv{endereco.version} fora '
                'das faixas reservadas'
            )


def test_r05b_5b_a_varredura_enxerga_as_duas_familias():
    """Meta-gate: varredura IPv4-only deixaria o gate acima verde com um IPv6
    real dentro do arquivo. Os endereços de prova vêm de inteiros, senão o
    próprio `R05B-5` os pegaria."""
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    for real in (ipaddress.ip_address((0x2a01 << 112) | 1),
                 ipaddress.ip_address(0x60606060)):
        achados = _enderecos(f'a borda respondeu de {real}.')
        assert real in achados, f'a varredura não enxergou IPv{real.version}'
        assert not _seguro(real, faixas), 'endereço real passou por reservado'
    for reservado in ('192.0.2.1', '2001:db8::1', '::ffff:192.0.2.1'):
        assert _seguro(ipaddress.ip_address(reservado), faixas)


# ── R05B-6 ──────────────────────────────────────────────────────────────────
def test_r05b_6_nenhuma_configuracao_de_proxy_antes_da_evidencia():
    """`HOPS` fica em 0 enquanto a identidade não for determinada."""
    linhas = [l.strip() for l in EXEMPLO_ENV.read_text(encoding='utf-8').splitlines()
              if l.strip().startswith('RATE_LIMIT_TRUSTED_PROXY_HOPS')]
    assert linhas, 'o modelo de ambiente parou de declarar a variável'
    for linha in linhas:
        assert linha.split('=', 1)[1].strip().strip('"\'') == '0', (
            f'o modelo genérico carrega valor topológico: {linha!r}'
        )

    # E o padrão do próprio limitador é 0 — ausência de configuração não pode
    # significar confiar no cabeçalho.
    fonte = LIMITADOR.read_text(encoding='utf-8')
    assert "os.environ.get('RATE_LIMIT_TRUSTED_PROXY_HOPS', '0')" in fonte
    assert 'if TRUSTED_PROXY_HOPS <= 0:' in fonte, (
        'o limitador deixou de tratar 0 como "ignore o cabeçalho"'
    )

    if _estado() != 'DETERMINADA':
        assert 'HOPS=3' not in _bloco_do_contrato()


# ── R05B-7 ──────────────────────────────────────────────────────────────────
def test_r05b_7_o_limitador_nao_le_cabecalho_nao_certificado():
    """`CF-Connecting-IP`, `True-Client-IP` e `X-Real-IP` não foram medidos.

    Enquanto não forem, o limitador não pode lê-los: seriam identidade escolhida
    pelo cliente entrando na chave de balde por outra porta.
    """
    fonte = LIMITADOR.read_text(encoding='utf-8').lower()
    for nome in ('cf-connecting-ip', 'cf_connecting_ip', 'true-client-ip',
                 'true_client_ip', 'x-real-ip', 'x_real_ip', 'forwarded ='):
        assert nome not in fonte, f'o limitador passou a ler {nome!r}'


# ── R05B-8 ──────────────────────────────────────────────────────────────────
def test_r05b_8_a_sonda_mede_o_que_o_limitador_usa():
    """Sem isto, D e E seriam opinião em vez de medição.

    O limitador lê a PRIMEIRA instância de `X-Forwarded-For` e usa a string
    CRUA como chave de balde. A sonda precisa reportar os dois fatos, senão a
    medição descreveria uma função diferente da que roda em produção.
    """
    if SONDA is None:
        return

    fonte = LIMITADOR.read_text(encoding='utf-8')
    assert "handler.headers.get('X-Forwarded-For', '')" in fonte, (
        'o limitador mudou a forma de ler o cabeçalho; a sonda mede a antiga'
    )
    assert 'return cadeia[-TRUSTED_PROXY_HOPS]' in fonte, (
        'o limitador deixou de usar a string crua de cadeia[-N] como chave'
    )

    # Duas instâncias: a sonda acusa a divergência que o limitador ignoraria.
    repetido = SONDA.medir(_Req(
        X_Forwarded_For=['192.0.2.1,192.0.2.2,192.0.2.3', '198.51.100.7'],
        X_Probe_Hops='3', X_Origin_Claim='198.51.100.7'))
    assert repetido['xff_instancias_repetidas'] is True
    assert repetido['candidato_e_do_cliente'] is True, (
        'com duas instâncias o limitador selecionaria dado do cliente, e a '
        'sonda não acusou'
    )

    uma_so = SONDA.medir(_Req(X_Forwarded_For='192.0.2.1,192.0.2.2,198.51.100.7',
                              X_Probe_Hops='1', X_Origin_Claim='198.51.100.7'))
    assert uma_so['xff_instancias_repetidas'] is False

    # Grafia não canônica na posição do candidato.
    torto = SONDA.analisar(['::ffff:198.51.100.7', '203.0.113.1', '203.0.113.2'],
                           3, '198.51.100.7')
    assert torto['candidato_bate_com_origem_declarada'] is True
    assert torto['candidato_ja_canonico'] is False, (
        'a grafia não canônica passou por canônica: o balde do limitador '
        'dependeria da forma que a borda escolheu escrever'
    )
