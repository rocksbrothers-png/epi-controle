"""Auditoria Dashboard §3/§10 — alertas acionáveis.

compute_alerts passa a expor `category` ('stock' | 'ca' | 'manufacturer') e
`epi_name` em cada alerta, para o frontend montar o botão de ação e o deep-link
filtrado (Ver Estoque / Ver EPIs) sem depender de parsear o título. Enriquecimento
aditivo: a lógica de quando um alerta é gerado permanece inalterada.
"""

from datetime import date, timedelta

from modules.alerts.service import compute_alerts

TODAY = date.today()


def _fake_low_stock(_conn, _actor):
    return [{
        'stock': 0, 'minimum_stock': 10, 'epi_name': 'Capacete', 'company_name': 'ACME',
        'unit_name': 'Base', 'unit_measure': 'un', 'company_id': 1, 'unit_id': 2,
        'epi_id': 5, 'size_balances': [],
    }]


def _fake_epis(_conn, _actor, _scope):
    return [{
        'active': 1, 'name': 'Luva', 'company_name': 'ACME', 'id': 7,
        'company_id': 1, 'unit_id': 2, 'stock': 3, 'unit_measure': 'par',
        'ca_expiry': (TODAY + timedelta(days=10)).isoformat(),
        'epi_validity_date': (TODAY - timedelta(days=3)).isoformat(),
    }]


def _alerts():
    return compute_alerts(
        None, {'id': 1},
        fetch_low_stock_items=_fake_low_stock,
        actor_operational_unit_id=lambda _c, _a: None,
        fetch_epis=_fake_epis,
    )


def test_every_alert_has_category_and_epi_name():
    alerts = _alerts()
    assert alerts, 'esperava alertas gerados'
    for a in alerts:
        assert a.get('category') in {'stock', 'ca', 'manufacturer'}, a
        assert str(a.get('epi_name') or '').strip(), a


def test_stock_alert_category_and_name():
    stock = [a for a in _alerts() if a['category'] == 'stock']
    assert len(stock) == 1
    assert stock[0]['epi_name'] == 'Capacete'
    assert stock[0]['epi_id'] == 5 and stock[0]['unit_id'] == 2


def test_ca_alert_category_and_name():
    ca = [a for a in _alerts() if a['category'] == 'ca']
    assert len(ca) == 1
    assert ca[0]['epi_name'] == 'Luva'


def test_manufacturer_alert_category_and_name():
    mf = [a for a in _alerts() if a['category'] == 'manufacturer']
    assert len(mf) == 1
    assert mf[0]['epi_name'] == 'Luva'
    assert 'não pode ser entregue' in mf[0]['description']
