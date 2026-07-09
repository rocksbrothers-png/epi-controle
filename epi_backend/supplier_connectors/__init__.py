"""Registro dos conectores de API direta (Nível 3, Fase F4)."""

from epi_backend.supplier_connectors.base import ConnectorError, SupplierConnector
from epi_backend.supplier_connectors.demo import DemoConnector
from epi_backend.supplier_connectors.http_json import HttpJsonConnector

CONNECTORS = {
    DemoConnector.key: DemoConnector,
    HttpJsonConnector.key: HttpJsonConnector,
}


def available_connectors():
    """Lista (key, label) dos conectores registrados — para a UI de admin."""
    return [
        {'key': cls.key, 'label': cls.label}
        for cls in CONNECTORS.values()
    ]


def get_connector(key, config):
    """Instancia o conector pela key. Levanta ValueError para key desconhecida."""
    cls = CONNECTORS.get(str(key or '').strip())
    if cls is None:
        raise ValueError(f'Conector desconhecido: {key!r}.')
    return cls(config)


__all__ = [
    'CONNECTORS',
    'ConnectorError',
    'SupplierConnector',
    'available_connectors',
    'get_connector',
]
