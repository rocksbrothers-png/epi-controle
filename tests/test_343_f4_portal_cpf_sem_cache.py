"""#343 — F4: o portal do colaborador não persiste os 3 dígitos do CPF.

A auditoria da F4 achou três coisas distintas, e esta fatia corrige as três:

  F4-A  o portal cacheava `employee_portal_cpf_last3_<token>` em
        `sessionStorage`. O portal tem dois fatores — POSSE do link
        (`?employee_token=`) e CONHECIMENTO dos 3 dígitos. O cache era
        indexado pelo token, então quem chegasse àquela aba com o link de
        outra pessoa entrava sem o segundo fator: via a ficha inteira e podia
        ASSINAR em nome dela. O cache economizava três dígitos digitados.
  F4-B  `handle_get_employee_access` registrava `cpf_last3_received` na MESMA
        linha de log que `employee_id` e `link_id` — o fator de validação
        correlacionado a uma pessoa identificada.
  F4-C  o sanitizador da F1 redigia `token` e `employee_token`, mas deixava
        `cpf_last3` passar no path cru.

O que estes gates protegem é a AUSÊNCIA de um mecanismo. Ausência é fácil de
desfazer sem querer: basta alguém reintroduzir "uma conveniênciazinha" de UX.
Por isso os gates são específicos sobre a forma do que não pode voltar —
inclusive sobre os substitutos (marcador opaco, TTL, cookie), que apenas
encurtariam a janela do mesmo bypass em vez de fechá-la.
"""

import ast
import pathlib
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

APP_JS = RAIZ / 'static' / 'app.js'
PORTAL_JS = RAIZ / 'static' / 'js' / 'views' / 'employee-portal.js'
PORTAL_ROUTES = RAIZ / 'modules' / 'portal' / 'routes.py'
PORTAL_SERVICE = RAIZ / 'modules' / 'portal' / 'service.py'

from epi_backend.http_utils import (  # noqa: E402
    SENSITIVE_QUERY_PARAMS,
    redact_sensitive_query,
)


def _sem_comentarios(texto):
    """Remove linhas que são só comentário.

    Os comentários desta fatia EXPLICAM a remoção citando o nome do que foi
    removido — `sessionStorage`, `employee_portal_cpf_last3`. Um gate que
    procurasse a palavra crua proibiria o próprio texto que documenta a
    correção, e a saída seria apagar a explicação: o gate estaria piorando o
    código que deveria proteger.

    Só linhas cujo primeiro caractere não-branco é `//` saem. Nada de tirar
    comentário no fim da linha: `/` aparece dentro de literais de regex
    (`/^\\d{3}$/`) e recortar por ali quebraria código válido.
    """
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('//')
    )


def _corpo_de(js, nome_da_funcao):
    """Corpo de uma função JS, por contagem de chaves."""
    inicio = js.index(nome_da_funcao)
    abre = js.index('{', inicio)
    profundidade = 0
    for pos in range(abre, len(js)):
        if js[pos] == '{':
            profundidade += 1
        elif js[pos] == '}':
            profundidade -= 1
            if profundidade == 0:
                return js[abre:pos + 1]
    raise AssertionError(f'função {nome_da_funcao} sem fechamento — âncora errada')


@pytest.fixture(scope='module')
def portal_js():
    return PORTAL_JS.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def app_js():
    return APP_JS.read_text(encoding='utf-8')


# ── G1: nenhuma persistência dos 3 dígitos em browser storage ────────────────

def test_g1_o_portal_nao_toca_em_browser_storage(portal_js):
    """O módulo do portal não escreve NEM LÊ storage do navegador.

    Não basta parar de gravar: uma leitura sobrevivente indicaria que alguém
    ainda pretende consumir um valor persistido.
    """
    codigo = _sem_comentarios(portal_js)
    for proibido in ('sessionStorage', 'localStorage', 'document.cookie',
                     'indexedDB', 'openDatabase'):
        assert proibido not in codigo, (
            f'{proibido} voltou ao portal: os 3 dígitos do CPF não podem ser '
            f'persistidos em storage nenhum'
        )


def test_g1_os_helpers_de_cache_nao_existem_mais(portal_js, app_js):
    """As três funções e a chave saíram dos dois arquivos."""
    for nome in ('portalCpfStorageKey', 'cachePortalCpfLast3',
                 'getCachedPortalCpfLast3'):
        assert nome not in _sem_comentarios(portal_js), f'{nome} reapareceu no portal'
        assert nome not in _sem_comentarios(app_js), f'{nome} reapareceu no app.js'
    assert 'employee_portal_cpf_last3' not in _sem_comentarios(portal_js)
    assert 'employee_portal_cpf_last3' not in _sem_comentarios(app_js)


def test_g1_nao_ha_substituto_com_outro_nome(portal_js):
    """Marcador opaco, TTL ou cookie encurtariam a janela do MESMO bypass.

    A correção escolhida foi a ausência de estado, não um estado mais curto.
    Este gate procura a FORMA do substituto: qualquer escrita de storage no
    módulo, com qualquer nome de chave.
    """
    codigo = _sem_comentarios(portal_js)
    for forma in ('.setItem(', '.getItem(', '.removeItem('):
        assert forma not in codigo, (
            f'escrita/leitura de storage ({forma}) voltou ao portal — '
            f'substituir o cache por outro formato não fecha o bypass'
        )


# ── G2: o bootstrap não entra no portal com CPF vindo de storage ─────────────

def test_g2_o_bootstrap_do_portal_tem_um_caminho_so(app_js):
    """O bloco de `employee_token` em `init()` chama a tela de validação e sai.

    O defeito era um SEGUNDO ramo: se houvesse valor em cache, ele chamava
    `renderEmployeeExternalAccess` direto e dava `return` antes da tela.
    """
    inicio = app_js.index("get('employee_token')")
    bloco = app_js[inicio:inicio + 1200]
    fim = bloco.index('\n  }')
    bloco = _sem_comentarios(bloco[:fim])

    assert 'renderEmployeeCpfValidationScreen(' in bloco, \
        'o bootstrap do portal precisa continuar exigindo a tela de validação'
    assert 'renderEmployeeExternalAccess(' not in bloco, (
        'o bootstrap voltou a abrir o portal direto: posse do link não pode '
        'valer sozinha, sem o conhecimento dos 3 dígitos'
    )
    for proibido in ('sessionStorage', 'localStorage', 'getItem'):
        assert proibido not in bloco, f'{proibido} voltou ao bootstrap do portal'


# ── G3: o campo de CPF não é pré-preenchido ──────────────────────────────────

def test_g3_o_input_de_cpf_nasce_vazio(portal_js):
    """Pré-preencher a partir de storage é o mesmo bypass por outro caminho.

    A única atribuição a `input.value` que sobrevive é a normalização do que o
    usuário digita (só dígitos, no máximo 3) — ela LÊ do próprio input.
    """
    corpo = _sem_comentarios(_corpo_de(portal_js, 'function renderEmployeeCpfValidationScreen'))
    atribuicoes = [
        linha.strip() for linha in corpo.splitlines()
        if 'input.value =' in linha
    ]
    assert atribuicoes, 'âncora perdida: a normalização do input sumiu'
    for linha in atribuicoes:
        assert 'input.value || ' in linha, (
            f'atribuição a input.value vinda de outra fonte: {linha}'
        )


# ── G4: os 3 dígitos não vão para log ────────────────────────────────────────

def test_g4_nenhum_structured_log_do_portal_recebe_cpf():
    """AST, não texto: procura os `structured_log(...)` do módulo do portal e
    reprova qualquer argumento nomeado que cite CPF.

    Mascarar, truncar ou hashear não resolve — a mesma linha carrega
    `employee_id` e `link_id`, então qualquer representação correlacionável
    liga o fator de validação a uma pessoa identificada.
    """
    total_de_chamadas = 0
    for arquivo in (PORTAL_ROUTES, PORTAL_SERVICE):
        arvore = ast.parse(arquivo.read_text(encoding='utf-8'))
        chamadas = [
            no for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == 'structured_log'
        ]
        total_de_chamadas += len(chamadas)
        for chamada in chamadas:
            for argumento in chamada.keywords:
                assert 'cpf' not in str(argumento.arg or '').lower(), (
                    f'{arquivo.name}:{chamada.lineno} registra '
                    f'`{argumento.arg}` — o fator de validação do portal não '
                    f'pode ir para log'
                )

    # A âncora é o TOTAL, não cada arquivo: `service.py` não registra nada hoje
    # (0 chamadas) e `routes.py` registra 10. Exigir chamadas em cada arquivo
    # reprovaria por um fato que não é defeito. Exigir o total protege contra o
    # caso que importa: alguém renomear o logger e o gate passar varrendo nada.
    assert total_de_chamadas >= 8, (
        'âncora perdida: quase nenhum structured_log encontrado nos módulos do '
        'portal — o gate estaria varrendo vazio e passando por isso'
    )


# ── G5: o sanitizador cobre cpf_last3 ────────────────────────────────────────

def test_g5_cpf_last3_esta_entre_os_parametros_sensiveis():
    assert 'cpf_last3' in SENSITIVE_QUERY_PARAMS


def test_g5_a_redacao_apaga_o_valor_de_cpf_last3():
    """Comportamental: os DOIS fatores do portal somem da mesma linha."""
    saida = redact_sensitive_query(
        '/api/employee-access?employee_token=SEGREDO&cpf_last3=123&actor_user_id=42')
    assert saida == '/api/employee-access?employee_token=***&cpf_last3=***&actor_user_id=42'
    assert '123' not in saida.replace('actor_user_id=42', '')


@pytest.mark.parametrize('codificado', ['cpf%5Flast3', 'cpf_last%33', 'cpf%5flast%33'])
def test_g5_a_protecao_sobrevive_ao_nome_percent_encoded(codificado):
    """`parse_qs` aplica UMA passada de decodificação no nome, e é por ela que
    a rota lê a query: `cpf%5Flast3=123` chega como `cpf_last3`."""
    from urllib.parse import parse_qs
    assert 'cpf_last3' in {k.lower() for k in parse_qs(f'{codificado}=123')}, \
        'premissa do teste: o servidor precisa mesmo aceitar este nome'
    assert '123' not in redact_sensitive_query(f'/x?{codificado}=123')


# ── G6: o backend continua sendo a autoridade ────────────────────────────────

def test_g6_o_backend_continua_exigindo_cpf_last3():
    """Premissa da fatia, comportamental.

    Tirar o cache do cliente só é seguro porque o servidor revalida a cada
    requisição. Se alguém enfraquecer o backend para "compensar" a fricção do
    frontend, este gate fica vermelho antes de a fatia virar teatro.
    """
    from tests.test_ficha_renderer_and_portal_cpf import _base_conn
    from modules.portal.service import (
        get_employee_portal_context_by_token,
        validate_portal_cpf_with_attempts,
    )

    conn = _base_conn()
    conn.execute(
        "INSERT INTO employee_portal_links (id, company_id, employee_id, token, "
        "qr_code_value, active, expires_at, created_by_user_id, created_at, "
        "updated_at, cpf_attempts) VALUES "
        "(1, 1, 100, 'token-f4', 'qr', 1, '9999-12-31T00:00:00+00:00', 1, "
        "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 0)"
    )
    ctx = get_employee_portal_context_by_token(conn, 'token-f4')

    for ausente in ('', None, '12', 'abc'):
        with pytest.raises(Exception) as exc:
            validate_portal_cpf_with_attempts(conn, ctx, ausente)
        assert '3 últimos dígitos' in str(exc.value), (
            f'o backend aceitou cpf_last3={ausente!r} — a autoridade saiu do '
            f'servidor e a remoção do cache virou teatro'
        )


def test_g6_a_rota_continua_lendo_cpf_last3_da_query():
    """Se a rota parar de ler o parâmetro, o sanitizador da F4-C vira código
    morto e o gate G5 passaria protegendo nada."""
    fonte = PORTAL_ROUTES.read_text(encoding='utf-8')
    assert fonte.count("query.get('cpf_last3'") >= 2, (
        'as duas rotas do portal (acesso e PDF) precisam continuar lendo '
        '`cpf_last3` da query'
    )
