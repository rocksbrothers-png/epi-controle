"""Interface dos conectores de API direta com lojas de EPI (Nível 3, Fase F4).

Um conector implementa as 4 operações do plano
(docs/PLANO_TECNICO_MODULO_COMPRAS.md §3.3). O fluxo interno NÃO muda:
quando o fornecedor tem integração ativa, o envio da RFQ/PO chama o conector
em vez do e-mail/portal, e a resposta preenche as MESMAS tabelas de
cotação/confirmação das fases F1/F2.
"""

from abc import ABC, abstractmethod


class ConnectorError(Exception):
    """Falha de comunicação/contrato com a loja parceira."""


class SupplierConnector(ABC):
    """Contrato único de integração com uma loja de EPI.

    ``config`` é o dicionário decifrado de ``supplier_integrations``
    (credenciais/URLs específicas do tenant — nunca logar).
    """

    #: identificador estável do conector (ex.: 'demo', 'http_json_v1')
    key = ''
    #: nome exibível para o administrador
    label = ''

    def __init__(self, config):
        self.config = dict(config or {})

    @abstractmethod
    def get_catalog(self):
        """Lista o catálogo da loja.

        Retorna lista de dicts: ``supplier_sku``, ``description``, ``ca``,
        ``manufacturer``, ``unit_measure``, ``last_price``, ``lead_time_days``,
        ``min_order_qty``.
        """

    @abstractmethod
    def get_price_and_stock(self, items):
        """Cota preço/estoque/prazo dos itens.

        ``items``: lista de dicts com ``purchase_request_item_id``,
        ``epi_name``, ``ca``, ``quantity_requested``.
        Retorna lista de dicts com ``purchase_request_item_id``,
        ``unit_price``, ``quantity_available``, ``lead_time_days`` e
        ``declined`` (bool) — mesmo formato aceito por ``answer_quote``.
        """

    @abstractmethod
    def create_order(self, po, items):
        """Cria o pedido na loja.

        Retorna dict: ``confirmed`` (bool), ``supplier_order_ref``,
        ``delivery_forecast`` (AAAA-MM-DD ou ''), ``comment``.
        """

    @abstractmethod
    def get_order_status(self, supplier_order_ref):
        """Consulta o status do pedido na loja.

        Retorna dict: ``status`` (confirmed|rejected|delivery_update),
        ``delivery_forecast``, ``carrier``, ``tracking_code``, ``comment``.
        """

    def ping(self):
        """Teste de conectividade barato; conectores podem sobrescrever."""
        self.get_catalog()
        return True
