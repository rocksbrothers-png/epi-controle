"""Funções de autorização compartilhadas entre módulos."""

from core.permissions import PERMISSIONS


def ensure_permission(actor, action):
    if action not in PERMISSIONS.get(actor['role'], set()):
        raise PermissionError('Perfil sem permissão para esta ação.')


def ensure_company_access(actor, company_id):
    if actor['role'] == 'master_admin':
        return
    if str(actor.get('company_id') or '') != str(company_id or ''):
        raise PermissionError('Acesso permitido apenas para registros da própria empresa.')


def ensure_resource_company(actor, resource, label='Registro'):
    if not resource:
        raise ValueError(f'{label} não encontrado.')
    ensure_company_access(actor, resource.get('company_id'))


def require_structural_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError(
            'Apenas Administrador Geral e Administrador de Registro podem executar esta ação estrutural.'
        )


def require_configuration_admin(actor):
    if actor.get('role') not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError(
            'Apenas Administrador Master, Administrador Geral e Administrador de Registro '
            'podem acessar Configuração.'
        )


def require_master_admin(actor, message='Apenas Administrador Master pode executar esta ação.'):
    if actor.get('role') != 'master_admin':
        raise PermissionError(message)
