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


@pytest.mark.parametrize('path', [
    ('static', 'js', 'views', 'outsourced-employees-view.js'),
    ('static', 'app.js'),
])
def test_no_code_decides_who_is_outsourced_by_comparing_against_clt(path):
    """`tipo !== 'CLT'` como proxy de "é terceirizado" foi eliminado pelo PR
    #214 no backend e sobreviveu neste módulo até o PR C2.

    Enquanto CLT era o único vínculo próprio os dois davam no mesmo; com
    aprendiz, praticante e estagiário deixaram de dar. A decisão sai de uma
    lista, nunca de uma comparação contra uma única opção.
    """
    body = _strip_js_comments(_read(*path))
    offenders = re.findall(r"tipo_vinculo[^\n]*!==?\s*'CLT'|tipo\s*!==?\s*'CLT'", body)
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
