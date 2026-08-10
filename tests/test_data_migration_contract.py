"""Contrato de domínio da importação, sem depender de banco (ADR-0003 §12).

O contrato de **schema** (nullability, defaults, FKs) vive em
``tests_postgres/test_migration_contract_postgres.py``, contra o PostgreSQL
real. Ele não pode morar aqui: ``core/database.py`` não tem driver SQLite, e
o schema que a suíte padrão usa é um fixture escrito à mão — comparar o
catálogo contra uma cópia foi exatamente o que deixou passar
``employees.employee_id_code`` NOT NULL.

Aqui ficam só as invariantes que não dependem do banco: o catálogo usar o
mesmo normalizador do cadastro manual, e as regras de vínculo em si.
"""

import pytest

from modules.data_migration.catalog import ENTITIES, get_entity


def _enabled_entities():
    return [descriptor for descriptor in ENTITIES.values() if descriptor.enabled]


def test_every_enabled_entity_declares_a_target_table_and_natural_keys():
    for descriptor in _enabled_entities():
        assert descriptor.target_table, descriptor.key
        assert descriptor.natural_keys, (
            f'{descriptor.key}: sem chave natural não há como deduplicar nem '
            f'atualizar — só inserir cegamente.'
        )


def test_column_defaults_are_documented_as_empty_not_invented_business_values():
    """Não inventar valor de negócio para calar uma constraint.

    `sector` e `schedule_type` recebem string vazia porque é o que o próprio
    Cadastro Simplificado do sistema grava. Preencher "Integral" ou "CLT"
    seria afirmar algo falso sobre a jornada e o setor de cada pessoa.
    """
    colaboradores = get_entity('colaboradores')
    assert dict(colaboradores.column_defaults) == {'sector': '', 'schedule_type': ''}


def test_units_required_fields_have_no_invented_default():
    """`unit_type` e `city` são NOT NULL sem default honesto possível: viraram
    obrigatórios no assistente em vez de receberem um valor inventado."""
    unidades = get_entity('unidades')
    assert unidades.column_defaults == ()
    assert {'name', 'unit_type', 'city'} <= set(unidades.required_fields())


def test_every_enabled_entity_declares_a_normalizer():
    """Critério de aceite da issue #169: nenhuma entidade HABILITADA pode
    ficar sem `normalizer` — a importação gravaria sem passar pelas mesmas
    regras de domínio do cadastro manual. Este teste tem que falhar sozinho
    no dia em que uma entidade nova for habilitada sem declarar o dela;
    entidades de roadmap (`enabled=False`) não entram no critério."""
    for descriptor in _enabled_entities():
        assert descriptor.normalizer, (
            f'{descriptor.key}: entidade habilitada sem normalizer.'
        )


# ── Validação condicional da aplicação ──────────────────────────────────────

def test_import_uses_the_same_domain_normalizer_as_manual_registration():
    """Sem isto, importação e cadastro manual divergem — e já divergiram: o
    CPF era gravado formatado pela importação e só com dígitos pelo cadastro
    manual, de modo que o upsert nunca reconhecia quem já existia."""
    from modules.employees.service import normalize_employee_domain_fields
    descriptor = get_entity('colaboradores')
    assert descriptor.normalizer == (
        'modules.employees.service:normalize_employee_domain_fields'
    )
    module_name, _, function_name = descriptor.normalizer.partition(':')
    from importlib import import_module
    assert getattr(import_module(module_name), function_name) is normalize_employee_domain_fields


def test_domain_normalizer_stores_cpf_exactly_like_manual_registration():
    from modules.employees.service import create_employee  # noqa: F401 - documenta a origem da regra
    from modules.employees.service import normalize_cpf, normalize_employee_domain_fields
    normalized = normalize_employee_domain_fields({'cpf': '111.444.777-35'})
    assert normalized['cpf'] == normalize_cpf('111.444.777-35') == '11144477735'


def test_domain_normalizer_applies_the_employment_relationship_rules():
    from modules.employees.service import normalize_employee_domain_fields
    # Mão de obra própria: empresa de origem não se aplica e é limpa.
    own = normalize_employee_domain_fields(
        {'cpf': '11144477735', 'tipo_vinculo': 'CLT', 'empresa_origem': 'Alguma Coisa'},
    )
    assert own['empresa_origem'] == ''
    # Terceirizado/prestador: identificação do contratado é exigida.
    for vinculo in ('Terceirizado', 'Prestador de Serviço'):
        contracted = normalize_employee_domain_fields(
            {'cpf': '11144477735', 'tipo_vinculo': vinculo, 'empresa_origem': 'Alfa Serviços'},
        )
        assert contracted['empresa_origem'] == 'Alfa Serviços'
        with pytest.raises(ValueError, match='Empresa de origem'):
            normalize_employee_domain_fields(
                {'cpf': '11144477735', 'tipo_vinculo': vinculo, 'empresa_origem': ''},
            )


def test_domain_normalizer_defaults_missing_relationship_to_own_workforce():
    from modules.employees.service import normalize_employee_domain_fields
    assert normalize_employee_domain_fields({'cpf': '11144477735'})['tipo_vinculo'] == 'CLT'


# ── fornecedores (issue #169) ────────────────────────────────────────────
#
# O normalizer de `fornecedores` já existe desde 2026-08-07 (commit
# 1127122), mas só era provado em tests_postgres/test_migration_contract_
# postgres.py (linhas 313-481) — a suíte rápida (a que roda a cada push)
# não tinha nenhuma cobertura dele. Os testes abaixo não duplicam aqueles
# (que provam contra PostgreSQL real: índice único parcial, detecção de
# duplicidade pelo cadastro manual) — só garantem a mesma paridade de
# identidade + transformação básica sem depender de banco.

def test_fornecedores_import_uses_the_same_domain_normalizer_as_manual_registration():
    from modules.outsourced_companies.service import normalize_outsourced_company_domain_fields
    descriptor = get_entity('fornecedores')
    assert descriptor.normalizer == (
        'modules.outsourced_companies.service:normalize_outsourced_company_domain_fields'
    )
    module_name, _, function_name = descriptor.normalizer.partition(':')
    from importlib import import_module
    assert getattr(import_module(module_name), function_name) is normalize_outsourced_company_domain_fields


def test_fornecedores_domain_normalizer_derives_the_canonical_cnpj_column():
    """O defeito original da issue #169: a importação gravava o CNPJ como
    veio da planilha e deixava `cnpj_normalized` vazia, tirando a linha do
    índice único parcial de deduplicação (prova contra banco real em
    tests_postgres/)."""
    from modules.outsourced_companies.service import normalize_outsourced_company_domain_fields
    normalized = normalize_outsourced_company_domain_fields({
        'legal_name': 'Alfa Servicos LTDA',
        'cnpj': '11.222.333/0001-81',
        'company_kind': 'Terceirizada',
    })
    assert normalized['cnpj'] == '11.222.333/0001-81'
    assert normalized['cnpj_normalized'] == '11222333000181'
    assert normalized['company_kind'] == 'outsourced'  # vocabulário controlado, não o texto cru


# ── unidades (issue #169) ────────────────────────────────────────────────

def test_unidades_import_uses_the_same_domain_normalizer_as_manual_registration():
    from modules.units.service import normalize_unit_domain_fields
    descriptor = get_entity('unidades')
    assert descriptor.normalizer == 'modules.units.service:normalize_unit_domain_fields'
    module_name, _, function_name = descriptor.normalizer.partition(':')
    from importlib import import_module
    assert getattr(import_module(module_name), function_name) is normalize_unit_domain_fields


def test_unidades_domain_normalizer_applies_the_same_unit_type_aliases_as_manual_registration():
    """`normalize_unit_type` é a mesma função que `handle_post_units`/
    `handle_put_unit` (modules/units/routes.py) já chamam antes de
    create_unit/update_unit — aqui só confirmamos que o normalizador de
    importação a aplica igual."""
    from modules.units.service import normalize_unit_domain_fields
    assert normalize_unit_domain_fields({'unit_type': 'Navio'})['unit_type'] == 'embarcacao'
    assert normalize_unit_domain_fields({'unit_type': 'embarcação'})['unit_type'] == 'embarcacao'
    assert normalize_unit_domain_fields({'unit_type': ''})['unit_type'] == 'base'


def test_unidades_domain_normalizer_does_not_touch_city():
    """Não existe normalização de `city` em lugar nenhum do sistema hoje —
    não foi inventada aqui. O normalizador precisa ignorar o campo."""
    from modules.units.service import normalize_unit_domain_fields
    normalized = normalize_unit_domain_fields({'unit_type': 'base', 'city': '  São Paulo  '})
    assert normalized['city'] == '  São Paulo  '


# ── epis (issue #169) ────────────────────────────────────────────────────

def test_epis_import_uses_the_same_domain_normalizer_as_manual_registration():
    from modules.epis.service import normalize_epi_domain_fields
    descriptor = get_entity('epis')
    assert descriptor.normalizer == 'modules.epis.service:normalize_epi_domain_fields'
    module_name, _, function_name = descriptor.normalizer.partition(':')
    from importlib import import_module
    assert getattr(import_module(module_name), function_name) is normalize_epi_domain_fields


def test_epis_domain_normalizer_keeps_only_digits_in_ca():
    from modules.epis.service import normalize_epi_domain_fields
    assert normalize_epi_domain_fields({'ca': '12.345-A'})['ca'] == '12345'
    assert normalize_epi_domain_fields({'ca': ''})['ca'] == ''


def test_epis_domain_normalizer_canonicalizes_accepted_date_formats_to_iso():
    """Mesmos formatos que `preview.validate_date` já aceita no preview —
    fecha o buraco em que uma data `dd/mm/yyyy` passava como válida na
    prévia mas era gravada como texto literal (issue #169)."""
    from modules.epis.service import normalize_epi_domain_fields
    for raw in ('15/03/2024', '2024-03-15', '15-03-2024'):
        normalized = normalize_epi_domain_fields({'ca_expiry': raw})
        assert normalized['ca_expiry'] == '2024-03-15', f'{raw!r} -> {normalized["ca_expiry"]!r}'
    assert normalize_epi_domain_fields({'epi_validity_date': ''})['epi_validity_date'] == ''


def test_epis_domain_normalizer_uses_the_same_parser_preview_validates_against():
    """Uma só implementação de parsing: o mesmo `parse_date_flexible` que
    `preview.validate_date` usa para aceitar o formato no preview é o que
    grava o valor canônico aqui — não um segundo parser que poderia
    divergir sobre o que é uma data válida."""
    from modules.data_migration.preview import parse_date_flexible, validate_date
    from modules.epis.service import normalize_epi_domain_fields
    raw = '15/03/2024'
    assert validate_date(raw) is True
    assert parse_date_flexible(raw) is not None
    assert normalize_epi_domain_fields({'ca_expiry': raw})['ca_expiry'] == '2024-03-15'


def test_epis_domain_normalizer_rejects_an_unparseable_date_instead_of_storing_it_verbatim():
    """Antes desta issue esse texto seria gravado literal e
    `modules.epis.validity.parse_iso_date` o ignoraria em silêncio,
    quebrando o cálculo de vencimento sem erro visível em lugar nenhum.
    Agora vira `ValueError`, que o preview transforma num diagnóstico
    `domain_rule` — linha recusada, nunca mais dado corrompido em
    silêncio."""
    from modules.epis.service import normalize_epi_domain_fields
    with pytest.raises(ValueError, match='Validade do CA'):
        normalize_epi_domain_fields({'ca_expiry': 'não é uma data'})
    with pytest.raises(ValueError, match='Validade do EPI'):
        normalize_epi_domain_fields({'epi_validity_date': 'não é uma data'})
