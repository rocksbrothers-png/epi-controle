"""Snapshot PDF de relatórios (#6) + regressão dos campos de assinatura do
contrato comercial (#8 bug A)."""

import inspect

from modules.reports.service import build_report_pdf
import modules.commercial.service as commercial_service


def _report(n=0):
    deliveries = [
        {'delivery_date': '2026-01-0%d' % ((i % 9) + 1), 'employee_name': f'Colab {i}',
         'epi_name': 'Luva Nitrilica', 'quantity': i + 1, 'unit_name': 'Base Santos', 'sector': 'Operacao'}
        for i in range(n)
    ]
    return {
        'deliveries': deliveries,
        'by_unit': {'Base Santos': sum(d['quantity'] for d in deliveries)},
        'by_sector': {'Operacao': sum(d['quantity'] for d in deliveries)},
        'by_epi': {'Luva Nitrilica': sum(d['quantity'] for d in deliveries)},
        'by_tipo_vinculo': {'CLT': sum(d['quantity'] for d in deliveries)},
        'total_quantity': sum(d['quantity'] for d in deliveries),
    }


# ── #6 build_report_pdf ───────────────────────────────────────────────────────

def test_report_pdf_is_valid_document():
    pdf = build_report_pdf(_report(3), {'generated_at': '2026-01-01T10:00:00',
                                        'filters': {'start_date': '2026-01-01', 'sector': 'Operacao'}})
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b'%PDF-1.4')
    assert pdf.rstrip().endswith(b'%%EOF')


def test_report_pdf_contains_data_and_filters():
    pdf = build_report_pdf(_report(2), {'generated_at': '2026-01-01', 'filters': {'sector': 'Operacao'}})
    assert b'Relatorio de Entregas de EPI' in pdf
    assert b'Luva Nitrilica' in pdf      # agregacao por EPI
    assert b'Setor: Operacao' in pdf     # filtro aplicado renderizado


def test_report_pdf_empty_is_still_valid():
    pdf = build_report_pdf({}, {})
    assert pdf.startswith(b'%PDF')
    assert b'Nenhuma entrega' in pdf


def test_report_pdf_paginates_many_rows():
    pdf = build_report_pdf(_report(220), {})
    # cada página é um objeto "<< /Type /Page /Parent ..."
    assert pdf.count(b'/Type /Page /Parent') >= 2


# ── #8 bug A: campos de assinatura do contrato comercial ──────────────────────

def test_commercial_pdf_uses_correct_signature_fields():
    src = inspect.getsource(commercial_service.build_commercial_contract_pdf)
    # colunas reais no banco
    assert "contract.get('signature_name')" in src
    assert "contract.get('signature_data')" in src
    # nomes inexistentes que causavam assinatura em branco no PDF
    assert "contract.get('signed_name')" not in src
    assert "contract.get('signed_signature')" not in src
