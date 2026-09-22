"""R0.5 — gates da determinação da cadeia de proxy.

A R0 deixou `RATE_LIMIT_TRUSTED_PROXY_HOPS` com padrão `0` porque não havia
como comprovar outro número: o egresso do ambiente onde o código é escrito nega
`render.com`, `docs.render.com` e `*.onrender.com` com 403 no CONNECT, enquanto
`pypi.org` responde 200. Não é rede quebrada — é política.

Esta fatia não configura o valor. Ela constrói o instrumento de medição e trava
quatro regressões, mais uma quinta que a própria fatia cria:

- `R05-6`  valor ausente no deployment DEPOIS que o contrato for fechado
- `R05-2`  divergência do contrato entre Corporate e SaaS
- `R05-7`  regressão para confiança irrestrita no primeiro elemento do XFF
- `R05-8`  configuração incompatível com o modelo documentado
- `R05-9`  a sonda temporária virar API permanente

Os gates `R05-6`, `R05-8` e `R05-9` são condicionais ao estado do contrato: eles
mudam de exigência sozinhos quando `ESTADO-DA-CADEIA` passar de `INDETERMINADO`
a `DETERMINADO`. Isso é deliberado — um gate que precisa que alguém lembre de
ativá-lo não é um gate.
"""

import hashlib
import importlib.util
import inspect
import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import core.rate_limit as RL
import scripts.certificar_cadeia_de_proxy as CERT

# A sonda é TEMPORÁRIA: quando a cadeia for determinada ela sai do repositório.
# Um import incondicional interrompia a coleta do arquivo inteiro nesse momento
# — e então `R05-9`, que existe justamente para exigir a ausência, nunca
# chegava a rodar. Não havia estado verde em que o contrato estivesse fechado E
# a sonda removida: o gate era inalcançável.
#
# Mas `try/except ImportError` em volta do import engolia demais: uma sonda que
# EXISTE e quebra ao importar deixava todos os gates `@com_sonda` pulados e a
# suíte verde, enquanto a rota de produção estouraria ao carregar o mesmo
# módulo. E estreitar para `ModuleNotFoundError` não resolve — medido: com o
# arquivo ausente, `from epi_backend import proxy_chain_probe` levanta
# `ImportError` puro ("cannot import name"), não `ModuleNotFoundError`. Aquela
# guarda tornava o estado terminal inalcançável de novo.
#
# `find_spec` separa as duas perguntas sem executar nada: ausente é ausente;
# presente importa de verdade, e o que estourar lá dentro derruba a coleta.
if importlib.util.find_spec('epi_backend.proxy_chain_probe') is None:
    SONDA = None
else:
    from epi_backend import proxy_chain_probe as SONDA

#: Vocabulário do modelo de borda. Declarado AQUI, e não lido da sonda, para
#: que `R05-8` continue valendo depois que ela for removida. Um gate abaixo
#: confere que os dois não divergem enquanto a sonda existe.
VEREDITOS_CONHECIDOS = (
    'ANEXA', 'SOBRESCREVE', 'HIGIENIZA', 'PASSA_DIRETO', 'INDETERMINADO',
)

com_sonda = pytest.mark.skipif(
    SONDA is None,
    reason='a sonda já foi removida do repositório; `R05-9` cobre a ausência',
)

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / 'docs' / 'R05_CADEIA_DE_PROXY.md'
ENV_EXEMPLO = RAIZ / 'env.example'
RENDER = RAIZ / 'render.yaml'
SONDA_MODULO = RAIZ / 'epi_backend' / 'proxy_chain_probe.py'
ROTAS_AUTH = RAIZ / 'modules' / 'auth' / 'routes.py'
SCRIPT = RAIZ / 'scripts' / 'certificar_cadeia_de_proxy.py'

INICIO = '<!-- CONTRATO-R05-INICIO -->'
FIM = '<!-- CONTRATO-R05-FIM -->'

# Digesto do bloco de contrato. Os dois repositórios carregam a MESMA constante,
# então editar o contrato de um lado só deixa aquele lado vermelho. É a mesma
# mecânica dos digestos de paridade que o projeto já usa — e tem a mesma
# limitação honesta: pega edição unilateral, não pega os dois editando igual e
# errado ao mesmo tempo.
DIGESTO_CONTRATO_R05 = 'a27ac5e2f6204262b2b3841938d7639bc10a68eba82e6c5623fd7609a924e312'

VARIAVEL = 'RATE_LIMIT_TRUSTED_PROXY_HOPS'


def _bloco_do_contrato() -> str:
    texto = CONTRATO.read_text(encoding='utf-8')
    assert INICIO in texto and FIM in texto, 'marcadores do contrato sumiram'
    miolo = texto.split(INICIO, 1)[1].split(FIM, 1)[0]
    return miolo.strip()


def _campos_do_contrato() -> dict:
    campos = {}
    for linha in _bloco_do_contrato().splitlines():
        if ':' in linha:
            chave, valor = linha.split(':', 1)
            campos[chave.strip()] = valor.strip()
    return campos


def _determinado() -> bool:
    return _campos_do_contrato().get('ESTADO-DA-CADEIA') == 'DETERMINADO'


# ── R05-1: o contrato existe e é legível por máquina ────────────────────────

def test_r05_1_o_contrato_e_legivel_por_maquina():
    campos = _campos_do_contrato()
    for obrigatorio in ('ESTADO-DA-CADEIA', 'SALTOS-CONFIAVEIS',
                        'MODELO-DA-BORDA', 'ORIGENS-CORROBORADAS', 'EVIDENCIA'):
        assert obrigatorio in campos, f'contrato sem o campo {obrigatorio}'
    assert campos['ESTADO-DA-CADEIA'] in ('INDETERMINADO', 'DETERMINADO'), \
        'ESTADO-DA-CADEIA só admite INDETERMINADO ou DETERMINADO'


# ── R05-2: paridade Corporate × SaaS do contrato ────────────────────────────

def test_r05_2_o_contrato_e_identico_nos_dois_repositorios():
    """Gate (b). Não compara com o outro repo — nenhum dos dois enxerga o
    outro. Compara com o digesto que os dois carregam igual, o que reprova
    quem editar de um lado só."""
    atual = hashlib.sha256(_bloco_do_contrato().encode('utf-8')).hexdigest()
    assert atual == DIGESTO_CONTRATO_R05, (
        'o bloco de contrato mudou sem o digesto ser recalculado nos DOIS '
        f'repositórios. Atual: {atual}'
    )


# ── R05-3: a sonda não vaza endereço nenhum ─────────────────────────────────

_ADVERSARIAIS = [
    ('203.0.113.7, 198.51.100.9, 192.0.2.10', '203.0.113.7'),
    ('', '198.51.100.200'),
    ('192.0.2.10', '10.1.2.3'),
    ('nao-e-ip, 192.0.2.11, 203.0.113.250', '::1'),
    ('  192.0.2.12  ,  203.0.113.1  ', ''),
]


def _cada_texto(objeto):
    if isinstance(objeto, str):
        yield objeto
    elif isinstance(objeto, dict):
        for chave, valor in objeto.items():
            yield str(chave)
            yield from _cada_texto(valor)
    elif isinstance(objeto, (list, tuple)):
        for item in objeto:
            yield from _cada_texto(item)


@com_sonda
def test_r05_3_a_saida_da_sonda_nao_contem_endereco():
    """Gate de redação. Varre a saída inteira procurando qualquer coisa que o
    `ipaddress` aceite como endereço. Não basta "não devolvemos o peer": o teste
    tem de valer para a estrutura toda, inclusive campos futuros."""
    for cadeia, peer in _ADVERSARIAIS:
        saida = SONDA.analisar(cadeia, peer, SONDA.CABECALHOS_DE_FORWARDING)
        for texto in _cada_texto(saida):
            for pedaco in re.split(r'[\s,;]+', texto):
                if not pedaco:
                    continue
                try:
                    ipaddress.ip_address(pedaco.strip('[]'))
                except ValueError:
                    continue
                raise AssertionError(
                    f'a sonda devolveu algo que é endereço: {pedaco!r} '
                    f'(entrada cadeia={cadeia!r})'
                )


@com_sonda
def test_r05_3b_os_nomes_de_cabecalho_saem_de_lista_fixa():
    """Nome de cabeçalho também é dado. Se a sonda ecoasse os nomes recebidos,
    um cliente poderia escrever o que quisesse dentro da resposta."""
    fonte = SONDA_MODULO.read_text(encoding='utf-8')
    assert 'CABECALHOS_DE_FORWARDING = (' in fonte, \
        'a lista fixa de cabeçalhos sumiu'
    saida = SONDA.analisar('192.0.2.10', '', ['X-Forwarded-For'])
    assert saida['cabecalhos_de_forwarding'] == ['X-Forwarded-For']


# ── R05-4: a sonda falha fechada ────────────────────────────────────────────

class _HandlerFalso:
    def __init__(self, chave='', xff=None, peer='192.0.2.10'):
        self.headers = {}
        if chave:
            self.headers['X-Diagnostics-Key'] = chave
        if xff is not None:
            self.headers['X-Forwarded-For'] = xff
        self.client_address = (peer, 54321)


@com_sonda
def test_r05_4_sem_chave_no_ambiente_a_sonda_nao_responde(monkeypatch):
    monkeypatch.delenv('PROXY_CHAIN_PROBE_KEY', raising=False)
    assert SONDA.autorizado(_HandlerFalso(chave='qualquer-coisa')) is False, \
        'a sonda respondeu sem chave configurada no ambiente'


@com_sonda
def test_r05_4b_chave_errada_nao_autoriza(monkeypatch):
    monkeypatch.setenv('PROXY_CHAIN_PROBE_KEY', 'a-chave-certa')
    assert SONDA.autorizado(_HandlerFalso(chave='a-chave-errada')) is False
    assert SONDA.autorizado(_HandlerFalso(chave='')) is False
    assert SONDA.autorizado(_HandlerFalso(chave='a-chave-certa')) is True


def _sem_comentarios(texto):
    """Os comentários citam justamente o que o gate proíbe, para explicar por
    que aquilo está proibido. Convenção já usada em
    `tests/test_343_f2_teardown_logout.py`."""
    return '\n'.join(
        linha for linha in texto.splitlines() if not linha.lstrip().startswith('#')
    )


@com_sonda
def test_r05_4c_a_rota_devolve_404_e_nao_403():
    """403 confirmaria a existência da sonda para quem sondasse."""
    fonte = ROTAS_AUTH.read_text(encoding='utf-8')
    trecho = fonte.split('SONDA TEMPORÁRIA DA CADEIA DE PROXY — INÍCIO', 1)[1]
    trecho = _sem_comentarios(
        trecho.split('SONDA TEMPORÁRIA DA CADEIA DE PROXY — FIM', 1)[0])
    assert 'send_json(handler, 404' in trecho, \
        'a sonda desligada precisa devolver 404'
    assert '403' not in trecho, 'a sonda não pode devolver 403'


# ── R05-5: a tabela de decisão da borda ─────────────────────────────────────

@com_sonda
def test_r05_5_os_quatro_modelos_de_borda_sao_distinguidos():
    """A pergunta obrigatória: anexa, sobrescreve ou higieniza. Se dois modelos
    colapsassem no mesmo veredito, o número sairia de um empate."""
    casos = [
        # (cadeia recebida, veredito, elementos da borda à direita do sentinela)
        ('192.0.2.10, 203.0.113.9',            'ANEXA',        1),
        ('192.0.2.10, 203.0.113.9, 10.0.0.1',  'ANEXA',        2),
        ('203.0.113.9',                        'SOBRESCREVE',  None),
        ('',                                   'HIGIENIZA',    None),
        ('192.0.2.10',                         'PASSA_DIRETO', 0),
        ('203.0.113.9, 192.0.2.10',            'INDETERMINADO', 0),
    ]
    for cadeia, esperado, a_direita in casos:
        saida = SONDA.analisar(cadeia, '198.51.100.1', [])
        assert saida['veredito'] == esperado, \
            f'{cadeia!r} deveria ser {esperado}, veio {saida["veredito"]}'
        if a_direita is not None:
            assert saida['elementos_a_direita_do_sentinela'] == a_direita


@com_sonda
def test_r05_5b_a_cadeia_de_sentinelas_mede_a_borda_e_nao_o_cliente():
    """Controle C manda três sentinelas. O que interessa é o que a borda pôs
    DEPOIS do último — se o número mudasse com o tamanho do que o cliente
    escreve, ele seria escolhido pelo cliente."""
    um = SONDA.analisar('192.0.2.10, 203.0.113.9', '203.0.113.9', [])
    tres = SONDA.analisar('192.0.2.10, 192.0.2.11, 192.0.2.12, 203.0.113.9',
                          '203.0.113.9', [])
    assert um['elementos_a_direita_do_sentinela'] == 1
    assert tres['elementos_a_direita_do_sentinela'] == 1, \
        'a contribuição medida da borda mudou com o tamanho do envio do cliente'


# ── R05-6: gate (a) — valor no deployment depois do contrato fechado ────────

def _valores_declarados(texto: str) -> list:
    """Extrai os valores de `RATE_LIMIT_TRUSTED_PROXY_HOPS` nas DUAS formas.

    `env.example` usa `VARIAVEL=1`. O `render.yaml` usa a estrutura de lista
    que o blueprint da Render consome:

        - key: RATE_LIMIT_TRUSTED_PROXY_HOPS
          value: "1"

    A primeira versão deste gate procurava `VARIAVEL` seguida de `:` ou `=` e
    um número na MESMA linha. Isso reprovava a declaração correta do
    `render.yaml` — e empurraria quem tentasse satisfazê-lo a escrever um
    mapeamento inline que a Render não lê.
    """
    valores = []
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        # Forma de arquivo .env
        casou = re.match(rf'\s*{VARIAVEL}\s*=\s*"?(\d+)"?\s*$', linha)
        if casou:
            valores.append(casou.group(1))
            continue
        # Forma de blueprint: `- key: VARIAVEL` e, logo abaixo, `value: N`
        if not re.search(rf'key:\s*{VARIAVEL}\s*$', linha):
            continue
        for seguinte in linhas[i + 1:]:
            if re.match(r'\s*-\s', seguinte):
                break  # começou outra entrada de envVars sem declarar valor
            casou = re.match(r'\s*value:\s*"?(\d+)"?\s*$', seguinte)
            if casou:
                valores.append(casou.group(1))
                break
    return valores


def _declara_variavel(caminho: Path) -> bool:
    if not caminho.exists():
        return False
    return VARIAVEL in caminho.read_text(encoding='utf-8')


def test_r05_6_o_valor_so_existe_depois_de_comprovado():
    """Gate (a), nos dois sentidos.

    INDETERMINADO → declarar um número é proibido. Um valor não comprovado numa
    superfície de deployment é pior que nenhum: parece configuração.

    DETERMINADO → declarar é obrigatório, em `env.example` E em `render.yaml`,
    com o mesmo número do contrato."""
    campos = _campos_do_contrato()
    if not _determinado():
        assert not _declara_variavel(ENV_EXEMPLO), (
            f'{VARIAVEL} declarada em env.example com a cadeia ainda '
            'INDETERMINADA — isso é um palpite com cara de configuração'
        )
        assert not _declara_variavel(RENDER), (
            f'{VARIAVEL} declarada em render.yaml com a cadeia ainda INDETERMINADA'
        )
        return

    esperado = campos['SALTOS-CONFIAVEIS']
    for caminho in (ENV_EXEMPLO, RENDER):
        assert _declara_variavel(caminho), (
            f'contrato DETERMINADO e {VARIAVEL} ausente em {caminho.name}'
        )
        encontrados = _valores_declarados(caminho.read_text(encoding='utf-8'))
        assert encontrados, f'{caminho.name} cita {VARIAVEL} sem valor numérico'
        assert all(v == esperado for v in encontrados), (
            f'{caminho.name} declara {encontrados}, contrato diz {esperado}'
        )


def test_r05_6b_o_gate_entende_as_duas_formas_de_declaracao():
    """O gate de deployment precisa aceitar o que a Render realmente consome."""
    blueprint = (
        'services:\n'
        '  - type: web\n'
        '    envVars:\n'
        '      - key: OCR_REQUIRED\n'
        '        value: "1"\n'
        f'      - key: {VARIAVEL}\n'
        '        value: "2"\n'
    )
    assert _valores_declarados(blueprint) == ['2'], \
        'a forma de lista do blueprint precisa ser reconhecida'
    assert _valores_declarados(f'{VARIAVEL}=3\n') == ['3'], \
        'a forma de arquivo .env precisa ser reconhecida'
    # Chave declarada sem valor logo abaixo não conta como declaração.
    sem_valor = f'      - key: {VARIAVEL}\n      - key: OUTRA\n        value: "9"\n'
    assert _valores_declarados(sem_valor) == [], \
        'chave sem valor não pode ser lida como configurada'


# ── R05-7: gate (c) — regressão para confiar no primeiro elemento ───────────

def test_r05_7_o_primeiro_elemento_do_xff_nunca_volta_a_ser_a_origem():
    fonte = inspect.getsource(RL.get_client_ip)
    assert 'cadeia[0]' not in fonte, \
        'get_client_ip voltou a ler o primeiro elemento da cadeia'
    assert "split(',')[0]" not in fonte, \
        'voltou o split(\',\')[0] que a R0 removeu'
    assert 'TRUSTED_PROXY_HOPS' in fonte, \
        'a origem deixou de consultar a confiança declarada'


def test_r05_7b_sem_salto_declarado_o_cabecalho_nao_muda_a_origem():
    """O comportamento, não só a forma do código."""
    anterior = RL.TRUSTED_PROXY_HOPS
    RL.TRUSTED_PROXY_HOPS = 0
    try:
        sem = RL.get_client_ip(_HandlerFalso(peer='198.51.100.7'))
        com = RL.get_client_ip(_HandlerFalso(peer='198.51.100.7',
                                             xff='192.0.2.10, 203.0.113.9'))
        assert sem == com == '198.51.100.7', \
            'o cabeçalho voltou a decidir origem sem proxy confiável declarado'
    finally:
        RL.TRUSTED_PROXY_HOPS = anterior


# ── R05-8: gate (d) — contrato coerente com o modelo documentado ────────────

def test_r05_8_o_contrato_e_internamente_coerente():
    campos = _campos_do_contrato()
    if not _determinado():
        assert campos['SALTOS-CONFIAVEIS'] == 'nao-determinado', (
            'a cadeia está INDETERMINADA mas o contrato já traz um número'
        )
        assert campos['ORIGENS-CORROBORADAS'] == 'nao-determinado', (
            'a cadeia está INDETERMINADA mas o contrato já conta origens'
        )
        return

    modelo = campos['MODELO-DA-BORDA']
    assert modelo in VEREDITOS_CONHECIDOS, f'modelo de borda desconhecido: {modelo}'
    # Só três modelos fecham contrato. `INDETERMINADO` nunca foi aceitável; e
    # `SOBRESCREVE` deixou de ser quando o script passou a recusar produzir
    # número para ele — forma constante não prova que o elemento restante seja
    # o cliente. Sem esta linha o gate abençoaria, escrito à mão, exatamente o
    # valor que o script se recusa a emitir.
    assert modelo in ('ANEXA', 'PASSA_DIRETO', 'HIGIENIZA'), (
        f'modelo {modelo} não fecha contrato: o script não consegue provar o '
        'número a partir dele'
    )
    evidencia = campos['EVIDENCIA']
    # `EVIDENCIA:` sozinho parseia para string vazia, que é != do marcador e
    # passava. O contrato podia fechar e liberar a configuração sem registrar
    # nada — o oposto do que este gate afirma garantir.
    assert evidencia and evidencia != 'nao-produzida', \
        'contrato DETERMINADO sem evidência registrada'

    # Uma origem mede UM caminho. `get_client_ip` lê `cadeia[-N]`, e num
    # caminho com menos proxies que N esse elemento é escrito pelo cliente —
    # o bypass que a R0 fechou. Por isso o número só vale corroborado, e o
    # script sai com `[MEDIDO]` (código 3) de uma origem só.
    origens = campos['ORIGENS-CORROBORADAS']
    assert origens.isdigit() and int(origens) >= 2, (
        f'contrato DETERMINADO com ORIGENS-CORROBORADAS={origens!r}: o número '
        'precisa de pelo menos duas origens independentes'
    )

    saltos = int(campos['SALTOS-CONFIAVEIS'])
    if modelo in ('PASSA_DIRETO', 'HIGIENIZA'):
        assert saltos == 0, (
            f'{modelo} significa que a borda não contribui nada confiável; '
            f'só 0 é compatível, o contrato diz {saltos}'
        )
    else:  # ANEXA é o único que sobra, pela asserção acima
        assert saltos >= 1, (
            f'{modelo} significa que a borda contribui; 0 é incompatível'
        )


# ── R05-9: a sonda é temporária, e isso é gateado ───────────────────────────

def test_r05_9_a_sonda_sai_do_repositorio_quando_a_cadeia_for_determinada():
    """Diagnóstico não vira API. Enquanto a cadeia está INDETERMINADA a sonda
    pode existir; depois que ela cumpre a função, ficar é dívida."""
    if not _determinado():
        assert SONDA_MODULO.exists(), \
            'a cadeia ainda está INDETERMINADA e a sonda já sumiu'
        return

    assert not SONDA_MODULO.exists(), (
        'cadeia DETERMINADA e a sonda continua no repositório — ela era '
        'temporária por contrato'
    )
    rotas = ROTAS_AUTH.read_text(encoding='utf-8')
    assert 'proxy-chain-diagnostics' not in rotas, \
        'a rota da sonda continua registrada'
    assert 'proxy_chain_probe' not in rotas, \
        'o handler da sonda continua em modules/auth/routes.py'


# ── R05-10: o script de operador ────────────────────────────────────────────

def test_r05_10_o_script_e_somente_leitura():
    fonte = SCRIPT.read_text(encoding='utf-8')
    for verbo in ("'POST'", "'PUT'", "'DELETE'", "'PATCH'"):
        assert verbo not in fonte, f'o script de determinação faz {verbo}'
    assert "method='GET'" in fonte, 'o script deixou de declarar o método'


def test_r05_10b_um_numero_nao_sai_de_uma_requisicao_so():
    """O ponto que separa medição de palpite: três controles, repetidos, e um
    veredito que só sai quando todos concordam."""
    fonte = SCRIPT.read_text(encoding='utf-8')
    assert re.search(r'REPETICOES\s*=\s*([3-9]|\d{2,})', fonte), \
        'o script precisa repetir cada sondagem ao menos 3 vezes'
    for controle in ('A (sem XFF)', 'B (um sentinela)', 'C (três sentinelas)'):
        assert controle in fonte, f'o controle {controle} sumiu do script'
    assert 'Inconsistente' in fonte, \
        'o script precisa recusar medições que se contradizem'


# Faixas que RFC 5737 e RFC 1918 reservam para documentação e uso interno.
# Nenhuma delas identifica uma pessoa.
FAIXAS_SEGURAS = tuple(ipaddress.ip_network(r) for r in (
    '192.0.2.0/24',     # TEST-NET-1
    '198.51.100.0/24',  # TEST-NET-2
    '203.0.113.0/24',   # TEST-NET-3
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
    '127.0.0.0/8',
    '100.64.0.0/10',    # CGNAT, RFC 6598 — reservado, não identifica ninguém
))


def test_r05_10c_nenhum_endereco_real_em_lugar_nenhum_da_fatia():
    """A instrução era explícita: nada de IP real em documentação, PR ou teste.
    Este gate varre a fatia inteira, não só o literal que eu lembrei de olhar."""
    arquivos = (SCRIPT, SONDA_MODULO, CONTRATO, Path(__file__))
    for caminho in arquivos:
        if not caminho.exists():
            continue
        for literal in re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
                                  caminho.read_text(encoding='utf-8')):
            try:
                endereco = ipaddress.ip_address(literal)
            except ValueError:
                continue  # não é endereço: número de versão, porta, o que for
            assert any(endereco in faixa for faixa in FAIXAS_SEGURAS), (
                f'{caminho.name} contém {literal}, que não é de faixa reservada'
            )


# ── R05-11..14: o que a revisão do Codex mostrou que faltava ────────────────

def _forma(veredito, tamanho, sentinela, indice, a_direita, peer_classe='publico'):
    return {
        'cadeia_tamanho': tamanho,
        'sentinela_presente': sentinela,
        'sentinela_indice': indice,
        'elementos_a_direita_do_sentinela': a_direita,
        'peer_na_cadeia': False,
        'peer_indice': None,
        'peer_classe': peer_classe,
        'cabecalhos_de_forwarding': ['X-Forwarded-For'],
        'veredito': veredito,
    }


@com_sonda
def test_r05_11_chave_nao_ascii_nao_autoriza_e_nao_explode(monkeypatch):
    """`compare_digest` sobre `str` levanta TypeError com caractere fora de
    ASCII. A exceção escapava de `autorizado` e o handler devolvia 500 — o que
    distingue rota protegida de rota ausente para quem sonda, destruindo a
    razão de ser do 404."""
    monkeypatch.setenv('PROXY_CHAIN_PROBE_KEY', 'chave-ascii-comum')
    assert SONDA.autorizado(_HandlerFalso(chave='chavé-com-acento')) is False
    assert SONDA.autorizado(_HandlerFalso(chave='ключ')) is False


@com_sonda
def test_r05_11b_o_vocabulario_de_veredito_nao_diverge_da_sonda():
    """`R05-8` passou a declarar os vereditos localmente para sobreviver à
    remoção da sonda. Enquanto ela existe, os dois têm de bater."""
    assert tuple(SONDA.VEREDITOS) == VEREDITOS_CONHECIDOS


def test_r05_12_sobrescreve_nao_vira_numero(monkeypatch):
    """Forma constante não prova que o elemento restante seja o cliente.

    Dois proxies, o interno sobrescrevendo o cabeçalho com o próprio peer,
    produzem esta medição de forma perfeitamente consistente — e certificar
    um número aqui colapsaria todos os usuários num bucket só, com aparência
    de medição."""
    sobrescreve = _forma('SOBRESCREVE', 1, False, None, None)
    monkeypatch.setattr(CERT, '_controle', lambda *a, **k: sobrescreve)
    r = CERT.determinar('teste', 'https://exemplo.invalido', 'chave')
    assert r.executado is True
    assert r.valor is None, 'SOBRESCREVE não pode produzir número'
    assert r.contradicao is False, 'não é contradição — é prova insuficiente'
    assert 'SOBRESCREVE' in r.motivo


def test_r05_12b_anexa_com_controles_coerentes_produz_o_numero(monkeypatch):
    """Controle positivo: o caminho que DEVE determinar continua determinando."""
    anexa = _forma('ANEXA', 2, True, 0, 1)
    monkeypatch.setattr(CERT, '_controle', lambda *a, **k: anexa)
    r = CERT.determinar('teste', 'https://exemplo.invalido', 'chave')
    assert r.valor == 1, f'esperava 1 salto, veio {r.valor}'
    assert r.veredito == 'ANEXA'


def test_r05_13_medicoes_contraditorias_nao_derrubam_o_relatorio(monkeypatch, capsys):
    """A evidência vem vazia quando as repetições se contradizem. Indexá-la
    estourava IndexError exatamente no caso que o script existe para
    diagnosticar."""
    def contraditorio(ambiente, url, chave):
        r = CERT.Determinacao(ambiente)
        r.executado = True
        r.contradicao = True
        r.motivo = 'formas diferentes entre repetições'
        return r

    monkeypatch.setattr(CERT, 'determinar', contraditorio)
    codigo = CERT.main()
    saida = capsys.readouterr().out
    assert codigo == 1, 'contradição precisa sair com código 1'
    assert '[INCONSISTENT]' in saida
    assert 'NÃO configure' in saida


def test_r05_14_a_chave_nao_segue_redirecionamento():
    """O `urllib` copia cabeçalhos para o destino do redirect — só
    `content-length` e `content-type` ficam de fora. Um redirect entre origens
    entregaria a chave da sonda a outro host."""
    fonte = SCRIPT.read_text(encoding='utf-8')
    assert 'urllib.request.urlopen(' not in fonte, \
        'abrir direto pelo urlopen volta a seguir redirecionamento'
    manipulador = CERT._RecusaRedirecionamento()
    try:
        manipulador.redirect_request(None, None, 302, 'Found', {}, 'https://outro.invalido/')
    except CERT.NaoDeterminado as e:
        assert 'redirect' in str(e).lower()
    else:
        raise AssertionError('o redirecionamento não foi recusado')


# ── R05-15..18: segunda rodada da revisão automática ────────────────────────

def test_r05_15_so_tres_modelos_fecham_contrato():
    """O script recusa emitir número para `SOBRESCREVE`. Sem a restrição no
    `R05-8`, alguém podia escrever o mesmo valor à mão no contrato e passar —
    o gate abençoando justamente o que o instrumento se recusa a afirmar.

    Este teste é estrutural de propósito: ele guarda a lista. A prova de
    comportamento é a sabotagem que fecha o contrato com `SOBRESCREVE` e vê o
    `R05-8` reprovar — um teste que só reafirmasse a lista contra ela mesma
    não provaria nada.
    """
    fonte = _sem_comentarios(Path(__file__).read_text(encoding='utf-8'))
    assert "modelo in ('ANEXA', 'PASSA_DIRETO', 'HIGIENIZA')" in fonte, \
        'a lista de modelos que fecham contrato saiu do R05-8'
    # Os dois que ficaram de fora precisam continuar no vocabulário: sumir da
    # lista de vereditos conhecidos os deixaria passar por outro caminho.
    for excluido in ('SOBRESCREVE', 'INDETERMINADO'):
        assert excluido in VEREDITOS_CONHECIDOS


def test_r05_16_veredito_desconhecido_falha_fechado(monkeypatch):
    """Sonda com versão diferente pode devolver veredito que este script não
    conhece. Antes ele caía por exaustão no `valor = n_borda` e recomendava um
    número para um modelo que não entende."""
    estranho = _forma('MODELO_QUE_NAO_EXISTE', 2, True, 0, 1)
    monkeypatch.setattr(CERT, '_controle', lambda *a, **k: estranho)
    r = CERT.determinar('teste', 'https://exemplo.invalido', 'chave')
    assert r.valor is None, 'veredito desconhecido não pode virar número'
    assert 'MODELO_QUE_NAO_EXISTE' in r.motivo


def test_r05_17_a_chave_exige_https():
    """A recusa de redirecionamento cobre o segundo salto; esta checagem cobre
    o primeiro. Com `http://`, a chave iria em claro antes de existir redirect."""
    try:
        CERT._sondar('http://exemplo.invalido', 'chave-secreta', None)
    except CERT.NaoDeterminado as e:
        assert 'https' in str(e).lower()
    else:
        raise AssertionError('URL sem TLS foi aceita')


@com_sonda
def test_r05_18_cgnat_conta_como_privado():
    """`is_private` não cobre 100.64.0.0/10 neste Python, e o aviso de colapso
    só dispara para `privado` — uma borda em CGNAT passaria por cliente direto
    e o aviso sumiria em silêncio."""
    rede = SONDA._CGNAT
    assert SONDA._classe_do_endereco(str(rede.network_address)) == 'privado'
    assert SONDA._classe_do_endereco(str(rede.broadcast_address)) == 'privado'
    # As fronteiras de FORA são endereços roteáveis de verdade, então são
    # calculadas a partir da rede em vez de escritas como literal — o
    # `R05-10c` reprova, com razão, endereço real dentro desta fatia.
    assert SONDA._classe_do_endereco(str(rede.network_address - 1)) == 'publico'
    assert SONDA._classe_do_endereco(str(rede.broadcast_address + 1)) == 'publico'


@com_sonda
def test_r05_18b_o_404_da_sonda_usa_o_corpo_canonico_do_projeto():
    """Um literal próprio distinguia a sonda pelo texto da resposta."""
    trecho = _sem_comentarios(
        ROTAS_AUTH.read_text(encoding='utf-8')
        .split('SONDA TEMPORÁRIA DA CADEIA DE PROXY — INÍCIO', 1)[1]
        .split('SONDA TEMPORÁRIA DA CADEIA DE PROXY — FIM', 1)[0])
    assert "'Rota não encontrada.'" in trecho, \
        'o 404 da sonda precisa usar o mesmo corpo de app.not_found()'


# ── R05-19..23: terceira rodada da revisão automática ───────────────────────

def _determinacao_falsa(ambiente, veredito, valor, tamanho=2):
    """Uma `Determinacao` já concluída, para exercitar o rodapé do script sem
    rede. Os controles carregam os campos decisivos porque é deles que
    `_forma_da_determinacao` monta a forma salva."""
    r = CERT.Determinacao(ambiente)
    r.executado = True
    r.veredito = veredito
    r.valor = valor
    amostra = {
        'cadeia_tamanho': tamanho,
        'sentinela_presente': True,
        'sentinela_indice': 0,
        'elementos_a_direita_do_sentinela': valor,
        'veredito': veredito,
        'cabecalhos_de_forwarding': ['X-Forwarded-For'],
        'peer_classe': 'publico',
        'peer_na_cadeia': False,
        'peer_indice': None,
    }
    r.evidencia = [
        ('A · sem X-Forwarded-For', amostra),
        ('B · um sentinela', amostra),
        ('C · três sentinelas', amostra),
    ]
    return r


def _rodar_main(monkeypatch, resultados, **ambiente):
    """Executa `CERT.main()` com `determinar` dublado e o ambiente controlado."""
    for nome in ('EPI_PROXY_ORIGEM', 'EPI_PROXY_MEDICAO_ANTERIOR',
                 'EPI_PROXY_SALVAR_MEDICAO'):
        monkeypatch.delenv(nome, raising=False)
    for nome, valor in ambiente.items():
        monkeypatch.setenv(nome, valor)
    monkeypatch.setenv('EPI_PROXY_CORP_URL', 'https://exemplo.invalid')
    monkeypatch.setenv('EPI_PROXY_CORP_KEY', 'x')
    monkeypatch.setenv('EPI_PROXY_SAAS_URL', 'https://exemplo.invalid')
    monkeypatch.setenv('EPI_PROXY_SAAS_KEY', 'x')
    fila = list(resultados)
    monkeypatch.setattr(CERT, 'determinar', lambda *a, **k: fila.pop(0))
    return CERT.main()


def test_r05_19_uma_origem_so_nao_certifica(monkeypatch, capsys):
    """Achado P1. Três repetições saem todas da mesma máquina e enxergam o
    mesmo caminho. Se o roteamento da borda depender de origem, certificar N
    daqui faz `cadeia[-N]` apontar para um elemento do CLIENTE nos caminhos
    mais curtos — o bypass que a R0 fechou."""
    resultados = [_determinacao_falsa('corporativo', 'ANEXA', 1),
                  _determinacao_falsa('saas', 'ANEXA', 1)]
    codigo = _rodar_main(monkeypatch, resultados)
    saida = capsys.readouterr().out
    assert codigo == 3, f'uma origem só devolveu código {codigo}'
    assert '[MEDIDO]' in saida and '[DETERMINED]' not in saida
    assert 'NÃO configure nada' in saida


def test_r05_19b_duas_origens_que_concordam_certificam(monkeypatch, capsys, tmp_path):
    """O contrapeso: se o gate acima só soubesse recusar, a R0.5 não teria
    estado terminal e o número nunca poderia ser fechado."""
    arquivo = tmp_path / 'medicao-casa.json'
    CERT._salvar_medicao(str(arquivo), 'casa', [
        _determinacao_falsa('corporativo', 'ANEXA', 1),
        _determinacao_falsa('saas', 'ANEXA', 1),
    ])
    resultados = [_determinacao_falsa('corporativo', 'ANEXA', 1),
                  _determinacao_falsa('saas', 'ANEXA', 1)]
    codigo = _rodar_main(monkeypatch, resultados,
                         EPI_PROXY_ORIGEM='4g',
                         EPI_PROXY_MEDICAO_ANTERIOR=str(arquivo))
    saida = capsys.readouterr().out
    assert codigo == 0, f'duas origens concordes devolveram código {codigo}'
    assert 'corroborada por duas origens' in saida


def test_r05_19c_duas_origens_que_discordam_reprovam(monkeypatch, capsys, tmp_path):
    arquivo = tmp_path / 'medicao-casa.json'
    CERT._salvar_medicao(str(arquivo), 'casa', [
        _determinacao_falsa('corporativo', 'ANEXA', 2),
        _determinacao_falsa('saas', 'ANEXA', 2),
    ])
    resultados = [_determinacao_falsa('corporativo', 'ANEXA', 1),
                  _determinacao_falsa('saas', 'ANEXA', 1)]
    codigo = _rodar_main(monkeypatch, resultados,
                         EPI_PROXY_ORIGEM='4g',
                         EPI_PROXY_MEDICAO_ANTERIOR=str(arquivo))
    saida = capsys.readouterr().out
    assert codigo == 1, f'origens discordantes devolveram código {codigo}'
    assert 'NÃO corroborado' in saida


def test_r05_19d_a_mesma_origem_nao_corrobora_a_si_mesma(monkeypatch, capsys, tmp_path):
    """Rodar duas vezes da mesma rede mede o mesmo caminho duas vezes."""
    arquivo = tmp_path / 'medicao-casa.json'
    CERT._salvar_medicao(str(arquivo), 'casa', [
        _determinacao_falsa('corporativo', 'ANEXA', 1),
        _determinacao_falsa('saas', 'ANEXA', 1),
    ])
    codigo = _rodar_main(monkeypatch,
                         [_determinacao_falsa('corporativo', 'ANEXA', 1),
                          _determinacao_falsa('saas', 'ANEXA', 1)],
                         EPI_PROXY_ORIGEM='casa',
                         EPI_PROXY_MEDICAO_ANTERIOR=str(arquivo))
    assert codigo == 1
    assert 'MESMA origem' in capsys.readouterr().out


def test_r05_20_ambientes_com_modelos_diferentes_nao_passam_por_iguais(monkeypatch, capsys):
    """`HIGIENIZA` e `PASSA_DIRETO` dão os dois o valor 0. Comparar só o número
    dizia "cadeia determinada" com as bordas sendo de modelos diferentes — e o
    contrato, que é idêntico nos dois repositórios, registra o MODELO."""
    resultados = [_determinacao_falsa('corporativo', 'HIGIENIZA', 0),
                  _determinacao_falsa('saas', 'PASSA_DIRETO', 0)]
    codigo = _rodar_main(monkeypatch, resultados)
    saida = capsys.readouterr().out
    assert codigo == 1, f'modelos diferentes devolveram código {codigo}'
    assert 'DIFERENTES' in saida
    assert 'HIGIENIZA' in saida and 'PASSA_DIRETO' in saida


class _RespostaFalsa:
    """Resposta HTTP mínima, só o que `_sondar` consome."""

    def __init__(self, corpo, status=200):
        self._corpo = corpo.encode('utf-8')
        self.status = status

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _sondar_com_corpo(monkeypatch, corpo):
    monkeypatch.setattr(CERT._ABRIDOR, 'open',
                        lambda req, timeout=None: _RespostaFalsa(corpo))
    return CERT._sondar('https://exemplo.invalid', 'chave', None)


def test_r05_21_resposta_json_que_nao_e_objeto_vira_nao_determinado(monkeypatch):
    """`json.loads('[]')` devolve lista sem erro, e `_forma` chama `.get`. A
    versão anterior estourava AttributeError no meio do relatório, justamente
    no caso que o script existe para diagnosticar.

    A primeira versão deste gate procurava `isinstance(dados, dict)` no texto
    do script inteiro — e o script tem OUTRA ocorrência dessa mesma linha, em
    `_carregar_medicao`. A sabotagem que apagava a verificação de `_sondar`
    passava. Comportamento, não texto.
    """
    with pytest.raises(CERT.NaoDeterminado) as erro:
        _sondar_com_corpo(monkeypatch, '[]')
    assert 'não é um objeto' in str(erro.value)


def test_r05_21b_resposta_de_objeto_continua_passando(monkeypatch):
    """Contrapeso: um gate que só soubesse recusar quebraria o script."""
    assert _sondar_com_corpo(monkeypatch, '{"veredito": "ANEXA"}') == {'veredito': 'ANEXA'}


def test_r05_22_a_sonda_quebrada_nao_passa_por_sonda_removida():
    """Uma sonda que existe e quebra ao importar não pode passar por sonda
    removida: os gates `@com_sonda` ficariam pulados e a suíte verde, enquanto
    a rota de produção estouraria ao carregar o mesmo módulo.

    Duas versões anteriores deste gate falharam por motivos opostos, e as duas
    foram descobertas por sabotagem: a primeira procurava o nome da exceção no
    texto do próprio arquivo — e a asserção continha esse nome, então o teste
    satisfazia a si mesmo; a segunda exigia `except ModuleNotFoundError`, que
    não é o que o Python levanta quando o arquivo some (`from pacote import
    modulo` ausente dá `ImportError` puro), e com ela o estado terminal ficava
    inalcançável.
    """
    import ast

    arvore = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    importes_da_sonda = [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module == 'epi_backend'
        and any(alias.name == 'proxy_chain_probe' for alias in no.names)
    ]
    assert importes_da_sonda, 'o import da sonda sumiu do arquivo'

    # Nenhum `try` pode envolver o import: é isso que engole a sonda quebrada.
    protegidos = {
        id(no) for tentativa in ast.walk(arvore) if isinstance(tentativa, ast.Try)
        for no in ast.walk(tentativa)
    }
    for importe in importes_da_sonda:
        assert id(importe) not in protegidos, (
            'o import da sonda voltou para dentro de um try: uma sonda que '
            'existe e quebra passaria por sonda removida'
        )

    # E a ausência continua tolerada pela via que não executa o módulo.
    consultas = [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        and no.func.attr == 'find_spec'
        and any(isinstance(arg, ast.Constant)
                and arg.value == 'epi_backend.proxy_chain_probe' for arg in no.args)
    ]
    assert consultas, (
        'a guarda deixou de consultar `find_spec`: ou o import virou '
        'incondicional (e o estado terminal fica inalcançável), ou voltou '
        'para dentro de um try'
    )



def test_r05_23_o_padrao_sem_configuracao_e_zero():
    """`R05-7b` troca `TRUSTED_PROXY_HOPS` por 0 antes de exercitar o
    comportamento, então ele não enxerga o INICIALIZADOR. Trocar o default de
    `'0'` para `'1'` em `core/rate_limit.py` passaria por toda a suíte e faria
    implantações não configuradas confiarem no cabeçalho do cliente.

    Import limpo, em processo separado, com a variável ausente: recarregar o
    módulo aqui dentro criaria limitadores novos e `modules/auth/routes.py`
    continuaria apontando para os antigos.
    """
    ambiente = {k: v for k, v in os.environ.items()
                if k != 'RATE_LIMIT_TRUSTED_PROXY_HOPS'}
    ambiente['PYTHONPATH'] = str(RAIZ)
    saida = subprocess.run(
        [sys.executable, '-c',
         'import core.rate_limit as RL; print(RL.TRUSTED_PROXY_HOPS)'],
        capture_output=True, text=True, env=ambiente, cwd=str(RAIZ),
        timeout=60, check=False)
    assert saida.returncode == 0, f'import limpo falhou: {saida.stderr}'
    assert saida.stdout.strip() == '0', (
        'sem RATE_LIMIT_TRUSTED_PROXY_HOPS no ambiente, o padrão deixou de ser '
        f'0 e virou {saida.stdout.strip()!r} — implantação não configurada '
        'passaria a confiar no cabeçalho do cliente'
    )
