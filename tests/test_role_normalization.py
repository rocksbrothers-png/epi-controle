import server_postgres


def test_normalize_role_name_aliases():
    assert server_postgres.normalize_role_name('local_admin') == 'admin'
    assert server_postgres.normalize_role_name('gestor de epi') == 'user'
    assert server_postgres.normalize_role_name('funcionario') == 'employee'
    assert server_postgres.normalize_role_name('MASTER-ADMIN') == 'master_admin'


def test_resolve_target_company_id_accepts_alias_roles():
    actor = {'role': 'master_admin', 'company_id': None}
    company_id = server_postgres.resolve_target_company_id(actor, 7, 'local_admin')
    assert company_id == 7


def test_purchase_profiles_require_company_when_created_by_master():
    actor = {'role': 'master_admin', 'company_id': None}

    for role in ('buyer', 'approver'):
        try:
            server_postgres.resolve_target_company_id(actor, '', role)
        except ValueError as exc:
            assert 'empresa vinculada' in str(exc)
        else:
            raise AssertionError(f'{role} sem empresa deveria ser recusado')


def test_purchase_profiles_accept_selected_company_when_created_by_master():
    actor = {'role': 'master_admin', 'company_id': None}

    assert server_postgres.resolve_target_company_id(actor, '42', 'buyer') == 42
    assert server_postgres.resolve_target_company_id(actor, '43', 'approver') == 43
