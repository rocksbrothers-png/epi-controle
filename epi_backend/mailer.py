"""Serviço genérico de envio de e-mail via SMTP (stdlib smtplib).

Extraído do fluxo de recuperação de senha (modules/auth/service.py) para ser
reutilizado pelo módulo de Compras (envio de cotações/POs — Nível 1) e pelo
Portal do Fornecedor (links tokenizados — Nível 2), conforme a Fase F0 do
docs/PLANO_TECNICO_MODULO_COMPRAS.md. Comportamento e configuração idênticos
ao envio original: STARTTLS + login, variáveis SMTP_HOST/SMTP_PORT/SMTP_USER/
SMTP_PASSWORD/SMTP_FROM.
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from epi_backend.http_utils import structured_log


def smtp_configured() -> bool:
    from epi_backend.config import SMTP_HOST, SMTP_USER
    return bool(SMTP_HOST and SMTP_USER)


def send_email(to_email, subject, body, html_body=None, attachments=None, reply_to=''):
    """Envia um e-mail via SMTP configurado.

    - ``to_email``: destinatário único (str) ou lista de destinatários.
    - ``body``: corpo em texto puro (sempre presente, fallback dos clientes).
    - ``html_body``: corpo HTML opcional (multipart/alternative).
    - ``attachments``: lista opcional de tuplas ``(file_name, content_bytes)``.
    - ``reply_to``: endereço opcional de resposta.

    Levanta ``ValueError`` se o SMTP não estiver configurado (mesma mensagem do
    fluxo de recuperação de senha, já tratada pelos frontends).
    """
    from epi_backend.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    if not SMTP_HOST or not SMTP_USER:
        raise ValueError('Servidor de e-mail não configurado. Configure SMTP_HOST e SMTP_USER.')
    recipients = [to_email] if isinstance(to_email, str) else [str(addr) for addr in (to_email or [])]
    recipients = [addr.strip() for addr in recipients if addr and str(addr).strip()]
    if not recipients:
        raise ValueError('Destinatário de e-mail não informado.')
    from_addr = SMTP_FROM or SMTP_USER

    if html_body or attachments:
        msg = MIMEMultipart('mixed')
        alternative = MIMEMultipart('alternative')
        alternative.attach(MIMEText(body, 'plain', 'utf-8'))
        if html_body:
            alternative.attach(MIMEText(html_body, 'html', 'utf-8'))
        msg.attach(alternative)
        for file_name, content in (attachments or []):
            part = MIMEApplication(content, Name=str(file_name))
            part['Content-Disposition'] = f'attachment; filename="{file_name}"'
            msg.attach(part)
    else:
        msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(recipients)
    if reply_to:
        msg['Reply-To'] = reply_to

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(from_addr, recipients, msg.as_string())
    structured_log('info', 'mailer.email_sent', to_count=len(recipients), subject=str(subject)[:80])
