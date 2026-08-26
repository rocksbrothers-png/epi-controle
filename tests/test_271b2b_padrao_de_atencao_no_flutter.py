"""#271-B2-b — o Flutter passa a EDITAR o padrão corporativo da faixa de atenção.

Não há toolchain Dart neste ambiente: `flutter analyze` e `flutter test` só
rodam no CI. O que estes testes protegem é a fronteira arquitetural, que uma
edição bem-intencionada reabre em uma linha.

O defeito que dá nome a esta fatia não é visual. `company_stock_attention_config`
existia desde a #271 e era somente-leitura no código inteiro; a B1b criou as
três rotas e, até aqui, nenhuma tela as chamava. Ao ligar a UI, a armadilha é
tratar "restaurar o padrão do sistema" como "gravar 20%": mesmo número, e a
empresa fica marcada como tendo tomado uma decisão que ela justamente desfez.

São verificações estruturais sobre o texto dos arquivos. Elas não provam que a
tela compila; provam que a regra não voltou para dentro dela.
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FLUTTER = RAIZ / 'flutter'
APP = FLUTTER / 'apps' / 'epi_admin' / 'lib'

MODELO = (FLUTTER / 'packages' / 'epi_api' / 'lib' / 'models' /
          'company_attention_setting.dart')
STOCK_API = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'stock_api.dart'
EXPORTS = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'epi_api.dart'
CUBIT = APP / 'core' / 'bloc' / 'company_attention_cubit.dart'
CARD = APP / 'features' / 'settings' / 'widgets' / 'company_attention_card.dart'
SETTINGS_DIR = APP / 'features' / 'settings'
TESTE_DART = (FLUTTER / 'apps' / 'epi_admin' / 'test' /
              'company_attention_cubit_test.dart')

LOCALES = ('app_pt_BR', 'app_en_US', 'app_es_ES', 'app_fr_FR', 'app_no_NO')
L10N = FLUTTER / 'packages' / 'epi_i18n' / 'lib' / 'l10n'

CHAVES = (
    'stockAttentionSectionTitle',
    'stockAttentionCompanyTitle',
    'stockAttentionCompanyHelp',
    'stockAttentionPercentageLabel',
    'stockAttentionOriginLabel',
    'stockAttentionOriginCompany',
    'stockAttentionOriginSystem',
    'stockAttentionSave',
    'stockAttentionRestore',
    'stockAttentionSaved',
    'stockAttentionRestored',
    'stockAttentionSystemDefaultHint',
    'stockAttentionRangeError',
    'stockAttentionLoadError',
)


def _sem_comentario_ao_final(linha: str) -> str:
    """Corta o `//` que abre comentário, ignorando o que está entre aspas.

    `'https://...'` não é comentário: recortar ali quebraria as asserções sobre
    rotas. O estado de aspas é seguido caractere a caractere, com escape.
    """
    aspas = None
    i = 0
    while i < len(linha):
        c = linha[i]
        if aspas is not None:
            if c == '\\':
                i += 2
                continue
            if c == aspas:
                aspas = None
        elif c in '\'"':
            aspas = c
        elif c == '/' and linha[i + 1:i + 2] == '/':
            return linha[:i]
        i += 1
    return linha


def _sem_comentarios(texto: str) -> str:
    """Remove `//` e `///` para que a prosa não satisfaça asserção nenhuma.

    Um teste que passa por causa de um comentário é um falso verde — foi o que
    aconteceu com a âncora da própria #271.

    Recortar só a linha inteira deixava passar o caso mais provável de todos:
    desligar o controle e deixar o nome dele no fim da linha — `return true; //
    hasPermission('settings:update')`. O gate continuava verde sobre um gate
    que não existe mais. Foi um teste de mutação desta fatia que revelou.
    """
    return '\n'.join(
        _sem_comentario_ao_final(linha) for linha in texto.split('\n')
        if not linha.lstrip().startswith('//')
    )


def _codigo(caminho: Path) -> str:
    return _sem_comentarios(caminho.read_text(encoding='utf-8'))


def _arquivos_que_montam_o_cartao() -> list:
    """Onde quer que o cartão esteja montado — a subtela pode mudar de nome.

    A B2-b nasceu com o cartão dentro de `settings_screen.dart`. A divisão das
    Configurações em hub + subtelas o moveu para `stock_defaults_screen.dart`,
    e o teste, que fixava o caminho, reprovou uma refatoração correta. Pior do
    que o falso vermelho seria o falso verde simétrico: se o cartão mudasse de
    casa de novo, o teste seguiria olhando para um arquivo que não o monta mais
    e aprovaria a B1b sem consumidor nenhum.

    O contrato não é o caminho do arquivo. É que o cartão esteja montado em
    algum lugar e que TODO ponto de montagem carregue o gate.
    """
    return sorted(
        caminho for caminho in SETTINGS_DIR.rglob('*.dart')
        if caminho != CARD and 'CompanyAttentionCard(' in _codigo(caminho)
    )


# ── Os arquivos existem e estão ligados ─────────────────────────────────────

def test_os_arquivos_da_fatia_existem():
    for caminho in (MODELO, STOCK_API, CUBIT, CARD, TESTE_DART):
        assert caminho.exists(), f'{caminho.name} sumiu'


def test_o_modelo_esta_exportado_no_pacote():
    assert "export 'models/company_attention_setting.dart';" in \
        EXPORTS.read_text(encoding='utf-8'), \
        'o modelo não sai do pacote e nenhuma tela conseguiria importá-lo'


def test_a_tela_de_configuracoes_monta_o_cartao():
    assert _arquivos_que_montam_o_cartao(), \
        'o cartão existe mas não está montado — a B1b continuaria sem consumidor'


# ── As três rotas, com os nomes certos ──────────────────────────────────────

def test_as_tres_rotas_da_b1b_sao_consumidas():
    fonte = _codigo(STOCK_API)
    assert "'/api/stock/company-attention-percentage'" in fonte
    assert "'/api/stock/company-attention-percentage/restore-default'" in fonte


def test_restaurar_usa_rota_propria_e_nao_um_set_com_valor_padrao():
    """Restaurar APAGA a linha; gravar 20 cria outra. São rotas diferentes."""
    fonte = _codigo(STOCK_API)
    trecho = fonte.split('restoreCompanyAttentionPercentage')[1]
    assert 'restore-default' in trecho.split('}')[0] or \
        'restore-default' in trecho[:600], \
        'restaurar deixou de chamar a rota de restauração'
    assert 'attention_percentage' not in trecho[:400], \
        'restaurar voltou a mandar um percentual — isso é gravar, não restaurar'


# ── A distinção que a fatia existe para preservar ───────────────────────────

def test_o_cubit_nao_implementa_restaurar_como_gravar():
    fonte = _codigo(CUBIT)
    corpo = fonte.split('restoreSystemDefault')[1].split('Future<void> _run')[0]
    assert 'setCompanyAttentionPercentage' not in corpo, \
        ('restaurar virou save(padrão): a empresa ficaria company_configured '
         'com o valor do sistema — a decisão que ela acabou de desfazer')
    assert 'restoreCompanyAttentionPercentage' in corpo


def test_salvar_e_restaurar_produzem_desfechos_distintos():
    fonte = _codigo(CUBIT)
    assert 'CompanyAttentionOutcome.saved' in fonte
    assert 'CompanyAttentionOutcome.restored' in fonte, \
        ('sem desfechos distintos a tela daria a mesma mensagem para as duas '
         'ações, que terminam com o mesmo número e significam o oposto')


def test_a_origem_exibida_vem_do_modelo_e_nao_da_acao():
    fonte = _codigo(CARD)
    assert 'setting.isCompanyConfigured' in fonte, \
        'o rótulo de origem deixou de ler o que o servidor devolveu'
    for pista in ('savedFeedback == CompanyAttentionOutcome.saved ? l10n.stockAttentionOriginCompany',
                  'outcome ==', 'acaoExecutada'):
        assert pista not in fonte, \
            f'a origem passou a ser deduzida da ação ({pista})'


# ── Uma régua só, e ela é do servidor ───────────────────────────────────────

def test_o_teto_e_o_padrao_nao_viram_constante_no_cliente():
    """Fixar 20 e 100 em Dart criaria a segunda régua que a B1b eliminou."""
    for caminho in (MODELO, CUBIT, CARD):
        fonte = _codigo(caminho)
        assert not re.search(r'=\s*100\b', fonte), \
            f'{caminho.name} fixou o teto de 100 no cliente'
        assert not re.search(r'=\s*20\b', fonte), \
            f'{caminho.name} fixou o padrão de 20 no cliente'


def test_a_validacao_local_usa_o_teto_do_servidor():
    fonte = _codigo(CUBIT)
    assert 'maxPercentage' in fonte, \
        'a validação deixou de consultar o teto que veio do backend'


def test_zero_nao_e_tratado_como_ausencia():
    """`0` é configuração válida: "sem faixa laranja, só crítico"."""
    for caminho in (MODELO, CUBIT, CARD):
        fonte = _codigo(caminho)
        assert 'attentionPercentage ?? 0' not in fonte
        assert 'attentionPercentage > 0' not in fonte
        assert not re.search(r'if\s*\(\s*\w*[Pp]ercentage\s*\)', fonte), \
            f'{caminho.name} testou a truthiness de um percentual'


def test_a_existencia_da_configuracao_vem_de_has_company_config():
    fonte = _codigo(MODELO)
    assert 'hasCompanyConfig' in fonte
    assert 'source == sourceCompanyConfigured' in fonte, \
        'a derivação de has_company_config para respostas de POST sumiu'


# ── Permissão e fail-closed ─────────────────────────────────────────────────

def test_o_cartao_e_gated_por_settings_update():
    montagens = _arquivos_que_montam_o_cartao()
    assert montagens, 'o cartão não está montado em lugar nenhum'
    for caminho in montagens:
        assert "hasPermission('settings:update')" in _codigo(caminho), \
            (f'{caminho.name} monta o cartão sem gate: `admin`/`user` veriam '
             'um controle que sempre terminaria em 403 — e o padrão que '
             'alterariam é herdado por todas as Unidades')


def test_o_cubit_nao_grava_sem_ter_lido_antes():
    fonte = _codigo(CUBIT)
    corpo = fonte.split('Future<void> save(')[1].split('Future<void> restore')[0]
    assert 'if (atual == null) return;' in corpo, \
        'sem os limites do servidor não há régua — gravar aqui seria chute'


def test_a_empresa_nunca_e_inventada():
    """`company_id` só é transportado; a tela não escolhe empresa nenhuma."""
    fonte = _codigo(CUBIT)
    assert 'companyId: _companyId' in fonte
    assert not re.search(r'companyId\s*\?\?\s*\d', fonte), \
        'a tela passou a chutar um company_id'


# ── i18n ────────────────────────────────────────────────────────────────────

def test_as_chaves_existem_nos_cinco_idiomas():
    for locale in LOCALES:
        dados = json.loads((L10N / f'{locale}.arb').read_text(encoding='utf-8'))
        faltando = [c for c in CHAVES if c not in dados]
        assert not faltando, f'{locale}: faltam {faltando}'


def test_as_chaves_com_placeholder_tem_metadado():
    dados = json.loads((L10N / 'app_pt_BR.arb').read_text(encoding='utf-8'))
    for chave, placeholder in (('stockAttentionSystemDefaultHint', 'value'),
                               ('stockAttentionRangeError', 'max')):
        meta = dados.get('@' + chave)
        assert meta, f'{chave} sem metadado — gen-l10n não geraria o parâmetro'
        assert placeholder in meta['placeholders']


def test_a_frase_sobre_propagacao_existe_e_nega_a_escrita():
    """Sem ela o administrador acredita que salvar reescreve as Unidades."""
    dados = json.loads((L10N / 'app_pt_BR.arb').read_text(encoding='utf-8'))
    texto = dados['stockAttentionCompanyHelp'].lower()
    assert 'não altera' in texto, \
        'a frase deixou de dizer que Unidades configuradas ficam intactas'


def test_o_cartao_nao_tem_string_literal_de_interface():
    """Texto de interface sai do ARB, senão o app fala português nos outros
    quatro idiomas.

    Interpolação de chave do ARB não conta: `'${l10n.x}: '` é composição, não
    literal. O que o detector procura é PALAVRA sobrando depois de remover as
    interpolações — `': '` passa, `'Origem: '` não.
    """
    fonte = _codigo(CARD)
    literais = []
    for bruto in re.findall(r"Text\(\s*'([^']*)'", fonte):
        sem_interpolacao = re.sub(r'\$\{[^}]*\}|\$\w+', '', bruto)
        if re.search(r'[A-Za-zÀ-ÿ]{3,}', sem_interpolacao):
            literais.append(bruto)
    assert not literais, f'strings fora do ARB no cartão: {literais}'
