"""Conector REST/JSON genérico (Fase F4).

Modelo para lojas de EPI que exponham uma API JSON simples. A loja define a
``base_url`` e autentica por header (``Authorization: Bearer <api_key>`` ou
header customizado). Contrato esperado (todos os corpos em JSON):

  GET  {base_url}/catalog                     → {"items": [...]}
  POST {base_url}/price-and-stock  {items}    → {"items": [...]}
  POST {base_url}/orders           {order}    → {"confirmed", "order_ref", ...}
  GET  {base_url}/orders/{ref}/status         → {"status", "carrier", ...}

Usa stdlib urllib (sem dependência nova) com timeout curto. Qualquer falha
de rede/HTTP/contrato vira ConnectorError — nunca vaza para o fluxo interno.
"""

import json
import urllib.error
import urllib.request

from epi_backend.supplier_connectors.base import ConnectorError, SupplierConnector

_TIMEOUT_SECONDS = 15


class HttpJsonConnector(SupplierConnector):
    key = 'http_json_v1'
    label = 'API REST/JSON genérica (v1)'

    def _base_url(self):
        base = str(self.config.get('base_url') or '').strip().rstrip('/')
        if not base.startswith('https://'):
            raise ConnectorError('Integração exige base_url HTTPS.')
        return base

    def _headers(self):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        api_key = str(self.config.get('api_key') or '').strip()
        header_name = str(self.config.get('auth_header') or 'Authorization').strip()
        if api_key:
            prefix = str(self.config.get('auth_prefix') or 'Bearer ').rstrip() + ' ' \
                if header_name == 'Authorization' else ''
            headers[header_name] = f'{prefix}{api_key}'.strip()
        return headers

    def _request(self, method, path, payload=None):
        url = f'{self._base_url()}{path}'
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                body = response.read().decode('utf-8')
        except urllib.error.HTTPError as exc:
            raise ConnectorError(f'Loja respondeu HTTP {exc.code} em {path}.') from exc
        except Exception as exc:
            raise ConnectorError(f'Falha de comunicação com a loja em {path}: {exc}') from exc
        try:
            return json.loads(body or '{}')
        except ValueError as exc:
            raise ConnectorError(f'Resposta inválida (não-JSON) da loja em {path}.') from exc

    def get_catalog(self):
        data = self._request('GET', '/catalog')
        items = data.get('items')
        if not isinstance(items, list):
            raise ConnectorError('Catálogo da loja sem a chave "items".')
        return [dict(item) for item in items]

    def get_price_and_stock(self, items):
        payload = {
            'items': [
                {
                    'purchase_request_item_id': int(item['purchase_request_item_id']),
                    'epi_name': str(item.get('epi_name') or ''),
                    'ca': str(item.get('ca') or ''),
                    'quantity_requested': int(item.get('quantity_requested') or 0),
                }
                for item in items
            ]
        }
        data = self._request('POST', '/price-and-stock', payload)
        answers = data.get('items')
        if not isinstance(answers, list):
            raise ConnectorError('Cotação da loja sem a chave "items".')
        normalized = []
        for answer in answers:
            normalized.append({
                'purchase_request_item_id': int(answer.get('purchase_request_item_id') or 0),
                'unit_price': float(answer.get('unit_price') or 0),
                'quantity_available': int(answer.get('quantity_available') or 0),
                'lead_time_days': int(answer.get('lead_time_days') or 0),
                'declined': bool(answer.get('declined')),
            })
        return normalized

    def create_order(self, po, items):
        payload = {
            'po_number': str(po.get('po_number') or po.get('id') or ''),
            'expected_delivery_date': str(po.get('expected_delivery_date') or ''),
            'items': [
                {
                    'epi_name': str(item.get('epi_name') or ''),
                    'ca': str(item.get('ca') or ''),
                    'quantity': int(item.get('quantity_approved') or item.get('quantity') or 0),
                    'unit_price': float(item.get('unit_price') or 0),
                }
                for item in items
            ],
        }
        data = self._request('POST', '/orders', payload)
        return {
            'confirmed': bool(data.get('confirmed')),
            'supplier_order_ref': str(data.get('order_ref') or data.get('supplier_order_ref') or ''),
            'delivery_forecast': str(data.get('delivery_forecast') or ''),
            'comment': str(data.get('comment') or ''),
        }

    def get_order_status(self, supplier_order_ref):
        ref = str(supplier_order_ref or '').strip()
        if not ref:
            raise ConnectorError('PO sem referência de pedido na loja.')
        data = self._request('GET', f'/orders/{ref}/status')
        status = str(data.get('status') or 'delivery_update')
        if status not in ('confirmed', 'rejected', 'delivery_update'):
            status = 'delivery_update'
        return {
            'status': status,
            'delivery_forecast': str(data.get('delivery_forecast') or ''),
            'carrier': str(data.get('carrier') or ''),
            'tracking_code': str(data.get('tracking_code') or ''),
            'comment': str(data.get('comment') or ''),
        }
