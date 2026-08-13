"""Paridade frontend/backend do vínculo local (ADR-0002 §13, PR C2).

Duas coisas travadas aqui:

1. A lista de vínculos contratados do frontend é a MESMA do backend. Divergir
   é o pior dos dois mundos — a tela some com quem o backend aceita, ou
   oferece "Vincular" para quem o backend recusa.

2. O frontend NÃO deduz o estado do vínculo. Ele lê `local_unit_link_status`
   do backend. Se alguém reintroduzir uma comparação local de `unit_id` para
   adivinhar "está vinculado?", passa a existir uma segunda verdade sobre o
   mesmo fato — que foi exatamente a razão de o PR C ter sido dividido em C1
   (backend) e C2 (consumo).
"""

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(*parts):
    return (REPO_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def _strip_js_comments(body):
    """Remove comentários antes de procurar o anti-padrão.

    Sem isto o teste falha nos comentários que EXPLICAM o anti-padrão — foi o
    que aconteceu ao escrevê-lo. Um teste que proíbe descrever o problema
    empurra a explicação para fora do código, que é o oposto do desejado.
    """
    body = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
    return re.sub(r'^\s*(//|\*).*$', '', body, flags=re.MULTILINE)


def test_frontend_and_backend_agree_on_contracted_vinculos():
    from modules.employees.service import CONTRACTED_VINCULOS

    view_js = _read('static', 'js', 'views', 'outsourced-employees-view.js')
    match = re.search(r'var CONTRACTED_VINCULOS = \[(.*?)\];', view_js, re.DOTALL)
    assert match, 'CONTRACTED_VINCULOS não encontrada em outsourced-employees-view.js'
    frontend = tuple(re.findall(r"'([^']+)'", match.group(1)))
    assert frontend == tuple(CONTRACTED_VINCULOS), (
        f'view.js={frontend} vs backend={tuple(CONTRACTED_VINCULOS)}'
    )


def test_the_app_js_fallback_matches_too():
    """O `app.js` guarda um último recurso para o caso de o módulo de regras
    não carregar. Se ele divergir, a tela passa a filtrar diferente conforme
    um script carregou ou não — o pior tipo de bug para reproduzir."""
    from modules.employees.service import CONTRACTED_VINCULOS

    app_js = _read('static', 'app.js')
    match = re.search(r'const CONTRACTED_VINCULOS_FALLBACK = \[(.*?)\];', app_js, re.DOTALL)
    assert match, 'CONTRACTED_VINCULOS_FALLBACK não encontrada em app.js'
    fallback = tuple(re.findall(r"'([^']+)'", match.group(1)))
    assert fallback == tuple(CONTRACTED_VINCULOS), (
        f'app.js fallback={fallback} vs backend={tuple(CONTRACTED_VINCULOS)}'
    )


# ── Flutter (Web, Android e iOS) ────────────────────────────────────────────
#
# O app Flutter é o TERCEIRO consumidor da mesma regra, e por muito tempo o
# único não coberto aqui. As duas divergências que a auditoria da #226 achou
# viveram meses justamente porque nada confrontava o Dart com o Python.


def test_flutter_and_backend_agree_on_contracted_vinculos():
    """`kContractedVinculos` (Dart) == `CONTRACTED_VINCULOS` (Python).

    A lista do Flutter tinha só dois valores e omitia `Temporário`, que o
    backend sempre aceitou: um vínculo válido que o app não deixava cadastrar.
    """
    from modules.employees.service import CONTRACTED_VINCULOS

    dart = _read('flutter', 'packages', 'epi_api', 'lib', 'models', 'employee.dart')
    match = re.search(
        r'const List<String> kContractedVinculos = <String>\[(.*?)\];', dart, re.DOTALL
    )
    assert match, 'kContractedVinculos não encontrada em employee.dart'
    flutter = tuple(re.findall(r"'([^']+)'", match.group(1)))
    assert flutter == tuple(CONTRACTED_VINCULOS), (
        f'employee.dart={flutter} vs backend={tuple(CONTRACTED_VINCULOS)}'
    )


def test_the_flutter_form_offers_exactly_the_contracted_vinculos():
    """O formulário simplificado não pode redigitar a lista.

    Ele referencia `kContractedVinculos`; um literal Dart aqui recriaria a
    divergência que este PR fecha, e ela voltaria a passar despercebida
    porque o teste acima continuaria verde.
    """
    tab = _read(
        'flutter', 'apps', 'epi_admin', 'lib', 'features', 'outsourced_companies',
        'outsourced_employees_tab.dart',
    )
    match = re.search(r'const _kOutsourcedEmploymentTypes = ([^;]+);', tab)
    assert match, '_kOutsourcedEmploymentTypes não encontrada'
    assert match.group(1).strip() == 'kContractedVinculos', (
        f'o formulário deve referenciar kContractedVinculos, achei: {match.group(1).strip()}'
    )


def test_the_flutter_status_literals_match_the_backend():
    """Os literais que o Dart publica são os que o backend emite."""
    from modules.employees.service import (
        UNIT_LINK_STATUS_ACTIVE,
        UNIT_LINK_STATUS_INACTIVE,
        UNIT_LINK_STATUS_NONE,
    )

    dart = _read('flutter', 'packages', 'epi_api', 'lib', 'models', 'employee.dart')
    for name, expected in (
        ('kUnitLinkStatusActive', UNIT_LINK_STATUS_ACTIVE),
        ('kUnitLinkStatusInactive', UNIT_LINK_STATUS_INACTIVE),
        ('kUnitLinkStatusNone', UNIT_LINK_STATUS_NONE),
    ):
        match = re.search(rf"const String {name} = '([^']+)';", dart)
        assert match, f'{name} não encontrada em employee.dart'
        assert match.group(1) == expected, f'{name}={match.group(1)} vs backend={expected}'


def test_the_flutter_list_comes_from_the_route_that_carries_the_link_state():
    """A aba não pode voltar a se alimentar do bootstrap.

    `modules/auth/service.py` chama `fetch_employees` SEM `unit_context_id`,
    então o payload de bootstrap traz `local_unit_link_status` nulo para
    todos. Uma tela alimentada por ele não quebra — apenas nunca oferece as
    ações de vínculo, silenciosamente. É a pior forma de a paridade falhar:
    sem erro, sem log, com a aparência de estar implementada.
    """
    cubit = _read(
        'flutter', 'apps', 'epi_admin', 'lib', 'core', 'bloc',
        'outsourced_employees_cubit.dart',
    )
    body = _strip_js_comments(cubit)
    assert 'getEmployees(' in body, 'o cubit precisa consumir GET /api/employees'
    assert '.bootstrap()' not in body, (
        'o bootstrap não carrega o estado do vínculo local — a aba ficaria sem ações'
    )


def test_the_flutter_screen_does_not_deduce_the_link_state():
    """Mesma proibição do Web Legado, do lado Dart: nada de reconstruir o
    estado comparando `unitId` com a Unidade do ator."""
    for parts in (
        ('flutter', 'apps', 'epi_admin', 'lib', 'core', 'bloc',
         'outsourced_employees_cubit.dart'),
        ('flutter', 'apps', 'epi_admin', 'lib', 'features', 'outsourced_companies',
         'outsourced_employees_tab.dart'),
    ):
        body = _strip_js_comments(_read(*parts))
        offenders = re.findall(r'unitId\s*==\s*\w*[Uu]nit\w*', body)
        assert not offenders, f'{parts[-1]}: dedução local do vínculo: {offenders}'


@pytest.mark.parametrize('path', [
    ('static', 'js', 'views', 'outsourced-employees-view.js'),
    ('static', 'app.js'),
    ('flutter', 'apps', 'epi_admin', 'lib', 'core', 'bloc',
     'outsourced_employees_cubit.dart'),
    ('flutter', 'apps', 'epi_admin', 'lib', 'features', 'employees',
     'employee_detail_screen.dart'),
])
def test_no_code_decides_who_is_outsourced_by_comparing_against_clt(path):
    """`tipo !== 'CLT'` como proxy de "é terceirizado" foi eliminado pelo PR
    #214 no backend, sobreviveu no Web Legado até o PR C2 e no Flutter até o
    F2 da #226.

    Enquanto CLT era o único vínculo próprio os dois davam no mesmo; com
    aprendiz, praticante e estagiário deixaram de dar. A decisão sai de uma
    lista, nunca de uma comparação contra uma única opção.

    O padrão cobre os três nomes que a mesma propriedade recebe nas duas
    linguagens: `tipo_vinculo` e `tipo` no JS, `employmentType` no Dart. Sem
    o terceiro, este teste teria passado durante toda a vida das duas
    ocorrências Dart que o F2 corrigiu.
    """
    body = _strip_js_comments(_read(*path))
    offenders = re.findall(
        r"(?:tipo_vinculo|tipo|employmentType)!?[^\n]{0,40}?!==?\s*'CLT'", body
    )
    assert not offenders, f'comparação contra CLT reintroduzida em {path[-1]}: {offenders}'


def test_the_frontend_reads_the_link_state_instead_of_deducing_it():
    """A tela consome `local_unit_link_status`; não reconstrói o estado."""
    app_js = _read('static', 'app.js')
    assert 'local_unit_link_status' in app_js, (
        'app.js precisa consumir local_unit_link_status — o estado do vínculo '
        'é decidido pelo backend (PR C1), não pela tela.'
    )


def test_the_three_link_paths_are_literal_not_interpolated():
    """`test_frontend_api_contract.py` confronta cada chamada com as rotas
    registradas e não resolve enum-em-path. Interpolar a ação na URL faria a
    verificação de contrato deixar de enxergar estas três chamadas."""
    app_js = _read('static', 'app.js')
    for path in (
        '/api/employees/${entityId}/link',
        '/api/employees/${entityId}/unit-link/activate',
        '/api/employees/${entityId}/unit-link/deactivate',
    ):
        assert path in app_js, f'caminho literal ausente em app.js: {path}'


def test_index_html_was_rebuilt_with_the_new_column():
    """O `index.html` é gerado; esquecer o rebuild deixa a tela sem a coluna
    enquanto o `app.js` já escreve sete células — desalinhando a tabela."""
    index_html = _read('static', 'index.html')
    assert 'employee.unitLinkColumn' in index_html, (
        'index.html desatualizado — rode `python3 scripts/build_index.py build`.'
    )


def test_the_status_values_used_by_the_screen_match_the_backend():
    """Os literais que a tela compara têm de ser os que o backend emite."""
    from modules.employees.service import (
        UNIT_LINK_STATUS_ACTIVE,
        UNIT_LINK_STATUS_INACTIVE,
    )

    app_js = _read('static', 'app.js')
    assert f"linkStatus === '{UNIT_LINK_STATUS_ACTIVE}'" in app_js
    assert f"linkStatus === '{UNIT_LINK_STATUS_INACTIVE}'" in app_js


def test_own_workforce_never_gets_a_unit_link_button():
    """Defesa em profundidade: mesmo que o backend mandasse um status para mão
    de obra própria, a tela só oferece ação quando `local_unit_link_status` é
    verdadeiro — e o backend manda `null` para ela (PR C1)."""
    app_js = _read('static', 'app.js')
    assert 'if (permissions.canUpdate && linkStatus) {' in app_js, (
        'o botão de vínculo precisa depender de linkStatus ser verdadeiro'
    )


# ── i18n ────────────────────────────────────────────────────────────────────

_LOCALES = ('pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO')
_UNIT_LINK_KEYS = (
    'unitLinkColumn', 'unitLink', 'unitLinkActivate', 'unitLinkDeactivate',
    'unitLinkDeactivateReason', 'unitLinkActive', 'unitLinkArchived',
    'unitLinkAbsent',
)


@pytest.mark.parametrize('locale', _LOCALES)
def test_unit_link_keys_are_nested_under_employee(locale):
    """As chaves precisam viver DENTRO do objeto `employee`, não planas no topo.

    `static/i18n.js` resolve `employee.unitLinkColumn` navegando o dicionário
    aninhado (split em '.'), então uma chave plana chamada
    "employee.unitLinkColumn" nunca é encontrada — a tela cai no fallback do
    código e o idioma escolhido é ignorado em silêncio. Foi o que a primeira
    versão deste PR fez nos cinco arquivos.
    """
    import json

    data = json.loads(_read('static', 'i18n', f'{locale}.json'))
    assert isinstance(data.get('employee'), dict), f'{locale}: `employee` não é objeto'
    for key in _UNIT_LINK_KEYS:
        assert key in data['employee'], f'{locale}: falta employee.{key}'
        assert f'employee.{key}' not in data, (
            f'{locale}: employee.{key} está plana no topo — não resolve'
        )
