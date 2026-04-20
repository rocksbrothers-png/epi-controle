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
