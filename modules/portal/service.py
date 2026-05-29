"""Serviços do portal do funcionário."""


def get_employee_portal_context_by_token(connection, token):
    """Retorna contexto do portal pelo token de acesso.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('get_employee_portal_context_by_token não foi extraída ainda do monolito.')


def resolve_external_employee_context(connection, token, cpf_last3=None, *, ip_address='', user_agent=''):
    """Resolve contexto externo do funcionário por token e CPF.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('resolve_external_employee_context não foi extraída ainda do monolito.')


def build_employee_ficha_pdf(connection, employee_user):
    """Gera PDF da ficha EPI do funcionário para o portal.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('build_employee_ficha_pdf não foi extraída ainda do monolito.')
