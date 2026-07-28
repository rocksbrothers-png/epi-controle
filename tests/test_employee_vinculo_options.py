"""Menor Aprendiz / Praticante / Estagiário no Tipo de Vínculo do colaborador.

`index.html` é **gerado** a partir de `static/views/*.html` — estes testes olham
o arquivo gerado de propósito: é ele que o navegador carrega.

O campo "Empresa de Origem" é condicional a "Tipo de Vínculo" != CLT, e isso já
existia antes deste trabalho (`syncEmpresaOrigemVisibility` compara só com
`'CLT'`). As três opções novas herdam o comportamento sem exigir nenhum caso
especial — é justamente essa generalidade que estes testes fixam: uma
comparação nova hard-coded contra um valor específico (`=== 'Estagiário'`, por
exemplo) reintroduziria o acoplamento que a implementação original evitou.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEW_VALUES = ('Menor Aprendiz', 'Praticante', 'Estagiário')


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _options_of(html, select_id):
    match = re.search(
        rf'<select[^>]*id="{select_id}"[^>]*>(.*?)</select>', html, re.S
    )
    assert match, f'select#{select_id} não encontrado'
    return re.findall(r'<option value="([^"]*)"', match.group(1))


# ── cadastro de colaborador ──────────────────────────────────────────────────

def test_new_vinculo_options_are_in_the_registration_select():
    html = _read('static', 'index.html')
    options = _options_of(html, 'employee-tipo-vinculo')
    for value in NEW_VALUES:
        assert value in options, value


def test_registration_fragment_and_generated_index_agree():
    """Guarda contra editar só o gerado (que o build sobrescreve)."""
    fragment = _read('static', 'views', 'colaboradores.html')
    for value in NEW_VALUES:
        assert f'value="{value}"' in fragment, value


# ── filtro de relatório ───────────────────────────────────────────────────────

def test_new_vinculo_options_are_in_the_report_filter():
    html = _read('static', 'index.html')
    options = _options_of(html, 'report-tipo-vinculo')
    for value in NEW_VALUES:
        assert value in options, value


# ── rótulo exibido nas tabelas ────────────────────────────────────────────────

def test_employment_type_label_maps_the_new_values():
    app_js = _read('static', 'app.js')
    fn_match = re.search(
        r'function employmentTypeLabel\(value\) \{(.*?)\n\}', app_js, re.S
    )
    assert fn_match, 'employmentTypeLabel não encontrada'
    body = fn_match.group(1)
    for value, key in (
        ('menor aprendiz', 'employee.vincApprentice'),
        ('praticante', 'employee.vincTrainee'),
        ('estagiário', 'employee.vincIntern'),
    ):
        assert value in body, value
        assert key in body, key


# ── o campo condicional continua genérico ─────────────────────────────────────

def test_empresa_origem_visibility_only_compares_against_clt():
    """Nenhuma opção nova pode virar um caso especial na visibilidade.

    Se alguém adicionar `tv === 'Estagiário'` aqui, a próxima opção nova
    (e há razão para crer que virá mais uma) vai exigir outra edição neste
    trecho — o oposto do que a implementação original conquistou.
    """
    app_js = _read('static', 'app.js')
    fn_match = re.search(
        r'function syncEmpresaOrigemVisibility\(\) \{(.*?)\n\}', app_js, re.S
    )
    assert fn_match, 'syncEmpresaOrigemVisibility não encontrada'
    body = fn_match.group(1)
    comparisons = re.findall(r"===\s*'([^']*)'", body)
    assert comparisons == ['CLT'], comparisons


def test_empresa_origem_visibility_has_a_single_source_of_truth():
    """`row.hidden` só pode ser escrito dentro de `syncEmpresaOrigemVisibility`.

    As três chamadoras (setup inicial, edição, reset do formulário) devem
    delegar a essa função em vez de duplicar `row.hidden = ...` — foi
    exatamente essa duplicação que causou o campo ficar visível com CLT
    selecionado (o estado divergia entre os pontos que o escreviam).
    """
    app_js = _read('static', 'app.js')
    # Só a própria função pode buscar o elemento — as chamadoras delegam a ela.
    lookups = re.findall(r"getElementById\('employee-empresa-origem-row'\)", app_js)
    assert len(lookups) == 1, lookups
    calls = len(re.findall(r'syncEmpresaOrigemVisibility\(\)', app_js))
    # Definição + init() + startEditEmployee + handleFormReset.
    assert calls >= 4, calls


def test_new_values_are_not_clt_so_they_show_the_field_by_construction():
    """Não é o teste do DOM (isso é E2E) — é a garantia de que os valores
    escolhidos não colidem com o único caso que esconde o campo."""
    for value in NEW_VALUES:
        assert value != 'CLT'


# ── i18n ─────────────────────────────────────────────────────────────────────

def test_vinculo_labels_exist_in_all_locales():
    locales = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
    for locale in locales:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        for key in (
            'vincApprentice', 'vincTrainee', 'vincIntern',
            'employmentApprentice', 'employmentTrainee', 'employmentIntern',
        ):
            assert data['employee'][key], f'{locale}.employee.{key}'
