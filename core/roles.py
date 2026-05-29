"""Constantes de roles e mapeamento de pesos do sistema EPI Controle."""

ROLE_WEIGHT: dict[str, int] = {
    'employee': 0,
    'user': 1,
    'buyer': 1,
    'approver': 2,
    'admin': 2,
    'registry_admin': 3,
    'general_admin': 4,
    'master_admin': 5,
}

ROLE_ALIASES: dict[str, str] = {
    'master_admin': 'master_admin',
    'masteradmin': 'master_admin',
    'general_admin': 'general_admin',
    'generaladmin': 'general_admin',
    'registry_admin': 'registry_admin',
    'registryadmin': 'registry_admin',
    'local_admin': 'admin',
    'admin_local': 'admin',
    'admin': 'admin',
    'epi_manager': 'user',
    'gestor_epi': 'user',
    'gestor_de_epi': 'user',
    'gestor': 'user',
    'manager': 'user',
    'user': 'user',
    'employee': 'employee',
    'funcionario': 'employee',
    'buyer': 'buyer',
    'comprador': 'buyer',
    'approver': 'approver',
    'aprovador': 'approver',
}

BILLABLE_ROLES: tuple[str, ...] = (
    'general_admin',
    'registry_admin',
    'admin',
    'user',
    'buyer',
    'approver',
    'employee',
)


def normalize_role_name(role: str) -> str:
    normalized = str(role or '').strip().lower().replace('-', '_').replace(' ', '_')
    return ROLE_ALIASES.get(normalized, normalized)
