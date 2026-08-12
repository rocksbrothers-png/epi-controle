"""Menor Aprendiz / Praticante / Estagiário no Tipo de Vínculo do colaborador.

`index.html` é **gerado** a partir de `static/views/*.html` — estes testes olham
o arquivo gerado de propósito: é ele que o navegador carrega.

O campo "Empresa de Origem" é condicional ao vínculo ser de MÃO DE OBRA
CONTRATADA. Em 2026-08-11 a regra foi corrigida: Menor Aprendiz, Praticante e
Estagiário são vínculo DIRETO com a empresa — mesmo sendo aprendiz ou
estagiário, quem responde pelo EPI é a própria empresa, e não existe empresa de
origem a informar.

Até então `syncEmpresaOrigemVisibility` comparava só com `'CLT'`, e o backend
exigia empresa de origem para tudo que não fosse CLT. Resultado: as três opções
existiam no seletor e o cadastro era RECUSADO — só dava para salvar inventando
uma empresa terceirizada, gravando uma afirmação falsa sobre a responsabilidade.

A generalidade que estes testes fixam continua a mesma: a decisão sai de uma
LISTA compartilhada com o backend, nunca de comparações hard-coded por opção.
"""

import json
import os
import re

import pytest

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

def test_empresa_origem_visibility_has_no_per_option_special_case():
    """Nenhuma opção nova pode virar um caso especial na visibilidade.

    A versão anterior deste teste exigia `comparisons == ['CLT']` — e com isso
    travava o BUG em vez da regra: enquanto CLT era o único vínculo próprio,
    "comparar só com CLT" e "esconder para mão de obra própria" davam no mesmo.
    Deixaram de dar quando Menor Aprendiz, Praticante e Estagiário entraram no
    seletor: os três são vínculo DIRETO com a empresa (a responsabilidade pelo
    EPI é dela), mas o campo aparecia para eles e o backend recusava o cadastro
    pedindo uma empresa de origem inexistente.

    O que continua valendo — e é o que este teste guarda — é a intenção
    original: a decisão sai de uma LISTA, nunca de comparações encadeadas por
    opção.
    """
    app_js = _read('static', 'app.js')
    fn_match = re.search(
        r'function syncEmpresaOrigemVisibility\(\) \{(.*?)\n\}', app_js, re.S
    )
    assert fn_match, 'syncEmpresaOrigemVisibility não encontrada'
    body = fn_match.group(1)
    assert not re.findall(r"===\s*'([^']*)'", body), (
        'Comparação literal por opção dentro de syncEmpresaOrigemVisibility — '
        'use a lista de mão de obra própria.'
    )
    assert 'isOwnWorkforceVinculo' in body


def test_frontend_and_backend_agree_on_who_is_own_workforce():
    """A lista do `app.js` e a do backend precisam ser a MESMA.

    Divergir aqui é o pior dos dois mundos: o formulário esconde "Empresa de
    Origem" e o backend a exige (cadastro impossível), ou o formulário a pede e
    o backend a descarta (o operador digita e o dado some).
    """
    from modules.employees.service import OWN_WORKFORCE_VINCULOS
    app_js = _read('static', 'app.js')
    match = re.search(r'const OWN_WORKFORCE_VINCULOS = \[(.*?)\];', app_js, re.S)
    assert match, 'OWN_WORKFORCE_VINCULOS não encontrada em app.js'
    frontend = tuple(re.findall(r"'([^']+)'", match.group(1)))
    assert frontend == tuple(OWN_WORKFORCE_VINCULOS), (
        f'app.js={frontend} vs backend={tuple(OWN_WORKFORCE_VINCULOS)}'
    )


def test_every_own_workforce_vinculo_can_actually_be_registered():
    """O defeito concreto: as três opções do seletor eram RECUSADAS.

    `normalize_employee_domain_fields` exigia empresa de origem para tudo que
    não fosse CLT — então Menor Aprendiz, Praticante e Estagiário existiam na
    tela e não podiam ser salvos. Cadastrá-los só seria possível inventando
    uma empresa terceirizada, o que gravaria uma afirmação falsa sobre quem
    responde pelo EPI.
    """
    from modules.employees.service import (
        OWN_WORKFORCE_VINCULOS,
        normalize_employee_domain_fields,
    )
    for vinculo in OWN_WORKFORCE_VINCULOS:
        normalized = normalize_employee_domain_fields(
            {'cpf': '11144477735', 'tipo_vinculo': vinculo},
        )
        assert normalized['tipo_vinculo'] == vinculo
        assert normalized['empresa_origem'] == '', (
            f'{vinculo} é mão de obra própria — não pode carregar empresa de origem.'
        )


def test_contracted_vinculos_still_require_the_contractor():
    """A regra não pode ter sido afrouxada de lado: terceirizado e prestador
    continuam exigindo a identificação de quem os contratou."""
    from modules.employees.service import normalize_employee_domain_fields
    for vinculo in ('Terceirizado', 'Prestador de Serviço'):
        with pytest.raises(ValueError, match='Empresa de origem'):
            normalize_employee_domain_fields(
                {'cpf': '11144477735', 'tipo_vinculo': vinculo},
            )


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


def test_the_new_values_hide_the_field_because_they_are_own_workforce():
    """Este teste dizia o CONTRÁRIO até 2026-08-11.

    Chamava-se `..._so_they_show_the_field_by_construction` e afirmava que os
    três valores novos, por não serem `'CLT'`, exibiam "Empresa de Origem".
    Isso descrevia fielmente o que o código fazia — e o que o código fazia
    estava errado: aprendiz, praticante e estagiário têm vínculo direto com a
    empresa e não têm empresa de origem nenhuma.
    """
    from modules.employees.service import is_own_workforce
    for value in NEW_VALUES:
        assert is_own_workforce(value), value


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
