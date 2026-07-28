"""Evidências da entrega — o que prova que o EPI chegou às mãos de quem devia.

Antes disto a prova morava em colunas soltas da própria entrega
(``signature_*``). Aquilo comporta **uma** assinatura e nada mais: não havia
onde registrar biometria, foto do recebimento, aceite no portal ou a
conferência pelo QR — nem como ter duas evidências da mesma entrega, que é o
caso comum (assinatura no ato, conferência depois).

O registro é **append-only**. Evidência que pode ser editada não prova nada;
correção é uma linha nova, e a anterior continua lá.
"""

import hashlib
from datetime import datetime, timezone

from epi_backend.db import row_to_dict, table_exists

UTC = timezone.utc

# Tipos conhecidos. A coluna é texto de propósito — um provedor novo não deve
# exigir migração —, mas os nomes canônicos vivem aqui para que as telas não
# inventem variações do mesmo conceito.
SIGNATURE_HANDWRITTEN = 'assinatura_manuscrita'
SIGNATURE_DIGITAL = 'assinatura_digital'
BIOMETRICS = 'biometria'
PHOTO = 'foto'
QR_HANDOVER = 'conferencia_qr'
PORTAL_ACCEPT = 'aceite_portal'

EVIDENCE_KINDS = (
    SIGNATURE_HANDWRITTEN,
    SIGNATURE_DIGITAL,
    BIOMETRICS,
    PHOTO,
    QR_HANDOVER,
    PORTAL_ACCEPT,
)


def evidence_ready(connection) -> bool:
    """A tabela existe? Permite degradação graciosa na janela de migração."""
    return table_exists(connection, 'delivery_evidence')


def content_hash(content) -> str:
    """SHA-256 do conteúdo da evidência.

    Guardamos o **hash**, não uma segunda cópia: a imagem da assinatura já está
    na entrega, e duplicá-la aqui dobraria a exposição de dado pessoal sem
    ganho nenhum. O hash prova que o conteúdo não mudou depois.
    """
    raw = content if isinstance(content, bytes) else str(content or '').encode('utf-8')
    if not raw:
        return ''
    return f'sha256:{hashlib.sha256(raw).hexdigest()}'


def record_evidence(
    connection,
    *,
    company_id,
    delivery_id,
    kind,
    content=None,
    content_ref='',
    provider='',
    actor_user_id=None,
    actor_name='',
    subject_name='',
    client_ip='',
    notes='',
    collected_at=None,
):
    """Registra uma evidência da entrega. Devolve a linha criada.

    Não valida ``kind`` contra :data:`EVIDENCE_KINDS` de propósito: recusar um
    tipo desconhecido faria uma evidência real ser **descartada** por causa de
    um rótulo. Perder prova é pior do que guardar um rótulo fora da lista.
    """
    if not evidence_ready(connection):
        return None
    normalized_kind = str(kind or '').strip()
    if not normalized_kind:
        raise ValueError('Tipo da evidência é obrigatório.')

    now = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO delivery_evidence ('
        'company_id, delivery_id, kind, provider, collected_at, actor_user_id, '
        'actor_name, subject_name, client_ip, content_hash, content_ref, notes, created_at'
        ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(company_id), int(delivery_id), normalized_kind, str(provider or ''),
            str(collected_at or now), int(actor_user_id) if actor_user_id else None,
            str(actor_name or ''), str(subject_name or ''), str(client_ip or ''),
            content_hash(content), str(content_ref or ''), str(notes or ''), now,
        ),
    )
    return get_evidence(connection, int(cursor.lastrowid))


def get_evidence(connection, evidence_id):
    row = connection.execute(
        'SELECT * FROM delivery_evidence WHERE id = ?', (int(evidence_id),)
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_delivery_evidence(connection, delivery_id, delivery=None) -> list:
    """Evidências da entrega, em ordem cronológica.

    Quando a entrega é anterior a esta tabela e não tem nenhuma linha, sintetiza
    uma evidência a partir das colunas ``signature_*``. Assim a leitura é
    uniforme para quem consome, sem precisar de uma migração em massa que
    reescreveria histórico — e o histórico continua sendo o que sempre foi.
    """
    rows = []
    if evidence_ready(connection):
        rows = [
            row_to_dict(row)
            for row in connection.execute(
                'SELECT * FROM delivery_evidence WHERE delivery_id = ? '
                'ORDER BY collected_at, id',
                (int(delivery_id),),
            ).fetchall()
        ]
    if rows or not delivery:
        return rows
    legacy = _legacy_signature_evidence(delivery)
    return [legacy] if legacy else []


def _legacy_signature_evidence(delivery):
    """Projeção somente-leitura das colunas antigas de assinatura."""
    signature = str(delivery.get('signature_data') or '').strip()
    signed_at = str(delivery.get('signature_at') or '').strip()
    if not signature and not signed_at:
        return None
    return {
        'id': None,
        'company_id': delivery.get('company_id'),
        'delivery_id': delivery.get('id'),
        'kind': SIGNATURE_HANDWRITTEN,
        'provider': 'legado',
        'collected_at': signed_at,
        'actor_user_id': None,
        'actor_name': str(delivery.get('signature_name') or ''),
        'subject_name': str(delivery.get('signature_name') or ''),
        'client_ip': str(delivery.get('signature_ip') or ''),
        'content_hash': content_hash(signature),
        'content_ref': 'deliveries.signature_data',
        'notes': str(delivery.get('signature_comment') or ''),
        'created_at': signed_at,
        # Sinaliza que a linha não existe na tabela: quem for auditar precisa
        # saber que isto é uma leitura das colunas antigas, não um registro.
        'synthesized_from_legacy_columns': True,
    }
