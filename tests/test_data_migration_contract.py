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
