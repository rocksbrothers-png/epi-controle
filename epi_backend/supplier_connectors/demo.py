"""Conector piloto de demonstração (Fase F4).

Simula uma loja de EPI com respostas determinísticas, servindo como
implementação de referência e permitindo exercitar o fluxo do Nível 3 de
ponta a ponta antes de existir parceria com uma loja real.

Config aceita (tudo opcional):
  - ``catalog``: lista de produtos (mesmo formato de get_catalog);
  - ``price_table``: dict CA→preço unitário;
  - ``default_price``: preço para itens fora da price_table (default 25.0);
  - ``default_lead_time_days``: prazo padrão (default 7);
  - ``reject_order``: se truthy, create_order recusa o pedido (para testes).
"""

import hashlib

from epi_backend.supplier_connectors.base import SupplierConnector


class DemoConnector(SupplierConnector):
    key = 'demo'
    label = 'Loja de demonstração (piloto)'

    def get_catalog(self):
        catalog = self.config.get('catalog')
        if catalog:
            return [dict(item) for item in catalog]
        return [
            {
                'supplier_sku': 'DEMO-LUVA-01',
                'description': 'Luva nitrílica (demo)',
                'ca': '12345',
                'manufacturer': 'Demo Ltda',
                'unit_measure': 'par',
                'last_price': 12.5,
                'lead_time_days': 5,
                'min_order_qty': 10,
            },
            {
                'supplier_sku': 'DEMO-CAPACETE-01',
                'description': 'Capacete classe B (demo)',
                'ca': '67890',
                'manufacturer': 'Demo Ltda',
                'unit_measure': 'un',
                'last_price': 39.9,
                'lead_time_days': 10,
                'min_order_qty': 1,
            },
        ]

    def get_price_and_stock(self, items):
        price_table = {str(k): float(v) for k, v in (self.config.get('price_table') or {}).items()}
        default_price = float(self.config.get('default_price') or 25.0)
        lead_time = int(self.config.get('default_lead_time_days') or 7)
        answers = []
        for item in items:
            ca = str(item.get('ca') or '')
            answers.append({
                'purchase_request_item_id': int(item['purchase_request_item_id']),
                'unit_price': price_table.get(ca, default_price),
                'quantity_available': int(item.get('quantity_requested') or 0),
                'lead_time_days': lead_time,
                'declined': False,
            })
        return answers

    def create_order(self, po, items):
        if self.config.get('reject_order'):
            return {
                'confirmed': False,
                'supplier_order_ref': '',
                'delivery_forecast': '',
                'comment': 'Pedido recusado pela loja (demo).',
            }
        seed = f"demo-{po.get('id')}-{po.get('po_number')}"
        ref = 'DEMO-' + hashlib.sha256(seed.encode('utf-8')).hexdigest()[:10].upper()
        return {
            'confirmed': True,
            'supplier_order_ref': ref,
            'delivery_forecast': str(self.config.get('delivery_forecast') or ''),
            'comment': f'Pedido aceito pela loja demo ({len(items)} itens).',
        }

    def get_order_status(self, supplier_order_ref):
        return {
            'status': 'delivery_update',
            'delivery_forecast': str(self.config.get('delivery_forecast') or ''),
            'carrier': 'Demo Express',
            'tracking_code': f'{supplier_order_ref}-TRK',
            'comment': 'Pedido em transporte (demo).',
        }

    def ping(self):
        return True
