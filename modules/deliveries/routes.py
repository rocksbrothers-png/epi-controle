"""Rotas de entregas."""


def handle_create_delivery_route(self, connection, payload, *, require_fields, send_json, create_delivery):
    require_fields(
        payload,
        [
            'actor_user_id',
            'company_id',
            'employee_id',
            'epi_id',
            'quantity',
            'sector',
            'role_name',
            'delivery_date',
            'next_replacement_date',
            'stock_item_id',
            'stock_qr_code',
        ],
    )
    delivery_id = create_delivery(connection, payload)
    return send_json(self, 201, {'ok': True, 'id': delivery_id})
