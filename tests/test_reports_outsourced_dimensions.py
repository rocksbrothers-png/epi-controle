"""Dimensões de terceirizado no relatório de entregas — PR 6 (ADR-0002).

Cobre a extensão de ``build_reports`` com ``by_outsourced_company``,
``by_epi_responsibility`` e ``by_delivering_company``, lidas do snapshot
histórico gravado na entrega (não do cadastro vivo — ver PR 4), e os
filtros ``outsourced_company_name``/``epi_responsibility``.
"""

import modules.reports.service as reports_svc


def _delivery(quantity=1, **overrides):
    base = {
        'unit_name': 'Base Santos', 'sector': 'Operações', 'epi_name': 'Luva',
        'tipo_vinculo': 'CLT', 'quantity': quantity,
        'snapshot_outsourced_company_name': '', 'snapshot_epi_responsibility': '',
        'company_name': 'ACME',
    }
    base.update(overrides)
    return base


def _patch_common(monkeypatch, deliveries):
    monkeypatch.setattr(reports_svc, 'actor_operational_unit_id', lambda connection, actor: None)

    def fake_fetch_deliveries(connection, actor, where_clause='', params=()):
        return deliveries

    import modules.deliveries.service as deliveries_svc
    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', fake_fetch_deliveries)


def test_by_outsourced_company_groups_clt_under_fixed_label(monkeypatch):
    deliveries = [_delivery(quantity=2), _delivery(quantity=3)]
    _patch_common(monkeypatch, deliveries)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    report = reports_svc.build_reports(connection=None, actor=actor, filters={})
    assert report['by_outsourced_company'] == {'CLT / Sem Terceirizada': 5}


def test_by_outsourced_company_groups_by_snapshot_name():
    deliveries = [
        _delivery(quantity=2, snapshot_outsourced_company_name='Terceirizada X'),
        _delivery(quantity=1, snapshot_outsourced_company_name='Terceirizada X'),
        _delivery(quantity=4),  # CLT
    ]
    import modules.deliveries.service as deliveries_svc

    def fake_fetch_deliveries(connection, actor, where_clause='', params=()):
        return deliveries

    original = deliveries_svc.fetch_deliveries
    deliveries_svc.fetch_deliveries = fake_fetch_deliveries
    try:
        actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
        report = reports_svc.build_reports(connection=None, actor=actor, filters={})
    finally:
        deliveries_svc.fetch_deliveries = original
    assert report['by_outsourced_company'] == {'Terceirizada X': 3, 'CLT / Sem Terceirizada': 4}


def test_by_epi_responsibility_defaults_to_nao_aplicavel(monkeypatch):
    deliveries = [_delivery(quantity=1), _delivery(quantity=1, snapshot_epi_responsibility='Empresa Terceirizada')]
    _patch_common(monkeypatch, deliveries)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    report = reports_svc.build_reports(connection=None, actor=actor, filters={})
    assert report['by_epi_responsibility'] == {'Não Aplicável': 1, 'Empresa Terceirizada': 1}


def test_by_delivering_company_only_counts_rows_with_company_name(monkeypatch):
    deliveries = [_delivery(quantity=2, company_name='ACME'), _delivery(quantity=1, company_name='')]
    _patch_common(monkeypatch, deliveries)
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    report = reports_svc.build_reports(connection=None, actor=actor, filters={})
    assert report['by_delivering_company'] == {'ACME': 2}


def test_outsourced_company_name_filter_is_applied_when_schema_ready(monkeypatch):
    import modules.deliveries.service as deliveries_svc
    captured = {}

    def fake_fetch_deliveries(connection, actor, where_clause='', params=()):
        captured['where_clause'] = where_clause
        captured['params'] = params
        return []

    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', fake_fetch_deliveries)
    monkeypatch.setattr(reports_svc, 'actor_operational_unit_id', lambda connection, actor: None)
    from epi_backend import db as db_module
    monkeypatch.setattr(db_module, 'table_columns', lambda connection, table: {'snapshot_outsourced_company_name'})

    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    filters = {'outsourced_company_name': 'Terceirizada X', 'epi_responsibility': 'Empresa Terceirizada'}
    reports_svc.build_reports(connection=object(), actor=actor, filters=filters)
    assert 'deliveries.snapshot_outsourced_company_name = ?' in captured['where_clause']
    assert 'deliveries.snapshot_epi_responsibility = ?' in captured['where_clause']
    assert 'Terceirizada X' in captured['params']
    assert 'Empresa Terceirizada' in captured['params']


def test_outsourced_company_name_filter_ignored_when_schema_not_ready(monkeypatch):
    import modules.deliveries.service as deliveries_svc
    captured = {}

    def fake_fetch_deliveries(connection, actor, where_clause='', params=()):
        captured['where_clause'] = where_clause
        return []

    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', fake_fetch_deliveries)
    monkeypatch.setattr(reports_svc, 'actor_operational_unit_id', lambda connection, actor: None)
    from epi_backend import db as db_module
    monkeypatch.setattr(db_module, 'table_columns', lambda connection, table: set())

    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    filters = {'outsourced_company_name': 'Terceirizada X'}
    reports_svc.build_reports(connection=object(), actor=actor, filters=filters)
    assert 'snapshot_outsourced_company_name' not in captured['where_clause']


def test_pdf_export_includes_new_groups_without_crashing():
    report = {
        'deliveries': [], 'total_quantity': 0,
        'by_unit': {}, 'by_sector': {}, 'by_epi': {}, 'by_tipo_vinculo': {},
        'by_outsourced_company': {'Terceirizada X': 3}, 'by_epi_responsibility': {'Empresa Terceirizada': 3},
    }
    pdf_bytes = reports_svc.build_report_pdf(report, meta={'generated_at': '2026-07-29'})
    assert pdf_bytes.startswith(b'%PDF')
