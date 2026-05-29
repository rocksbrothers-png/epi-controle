"""Serviços de devoluções de EPIs."""


def register_epi_devolution(connection, payload, actor):
    """Registra devolução de EPI e atualiza estoque.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('register_epi_devolution não foi extraída ainda do monolito.')


def fetch_devolutions(connection, actor, filters=None):
    """Lista devoluções com filtros opcionais.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('fetch_devolutions não foi extraída ainda do monolito.')


def fetch_open_deliveries_for_devolution(connection, actor, employee_id, epi_id, unit_id=None):
    """Retorna entregas abertas elegíveis para devolução.
    Stub — implementação extraída do monolito em fase futura.
    """
    raise NotImplementedError('fetch_open_deliveries_for_devolution não foi extraída ainda do monolito.')
