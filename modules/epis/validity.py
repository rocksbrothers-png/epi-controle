"""Regras de validade de EPI e do Certificado de Aprovação (CA).

Base legal: Nota Técnica nº 146/2015/CGNOR/DSST/SIT, que distingue dois conceitos
de "validade":

- Validade do CA (Certificado de Aprovação): autoriza a fabricação e a
  *comercialização* do EPI. Na **aquisição/compra**, o CA não pode estar vencido
  (itens 14 a 16 da NT). O empregador, consumidor final, deve observar a validade
  do CA no momento da compra.
- Validade do produto informada pelo **fabricante**: rege o **uso/entrega** do EPI.
  Após a aquisição com CA válido, o uso do EPI não fica proibido mesmo com o CA
  posteriormente vencido — passa a valer a validade do produto informada pelo
  fabricante (itens 15 e 17 da NT). Logo, na entrega ao trabalhador o que bloqueia
  é a validade do fabricante vencida, e não o CA.

Os EPIs com validade do fabricante mais próxima do vencimento devem sair do
estoque primeiro (PEPS — Primeiro a Expirar, Primeiro a Sair).
"""

from datetime import date, datetime

# Antecedência (em dias) para alertar que a validade do fabricante está próxima.
MANUFACTURER_VALIDITY_WARNING_DAYS = 30


def parse_iso_date(value):
    """Converte 'YYYY-MM-DD' (ou ISO com hora) em date; retorna None se inválida/vazia."""
    raw = str(value or '').strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def days_until(value, today=None):
    """Dias até a data informada (negativo se já passou); None se data inválida/vazia."""
    parsed = parse_iso_date(value)
    if parsed is None:
        return None
    return (parsed - (today or date.today())).days


def is_expired(value, today=None):
    """True somente quando há data válida e ela já passou (vencida)."""
    days = days_until(value, today)
    return days is not None and days < 0


def is_expiring_soon(value, today=None, within_days=MANUFACTURER_VALIDITY_WARNING_DAYS):
    """True quando a data é válida e vence dentro de ``within_days`` (ainda não vencida)."""
    days = days_until(value, today)
    return days is not None and 0 <= days <= within_days
