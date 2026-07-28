"""Evidências da entrega — o que prova que o EPI chegou a quem devia.

Antes disto a prova morava em colunas soltas da entrega (`signature_*`). Aquilo
comporta **uma** assinatura e nada mais: não havia onde registrar biometria,
foto, aceite no portal ou a conferência pelo QR — nem como ter duas evidências
da mesma entrega, que é o caso comum (assinatura no ato, conferência depois).
"""

import sqlite3

import pytest

from core.schema import ensure_delivery_evidence
from modules.deliveries.evidence import (
    BIOMETRICS,
    QR_HANDOVER,
    SIGNATURE_HANDWRITTEN,
    content_hash,
    fetch_delivery_evidence,
    record_evidence,
)

EMPRESA, ENTREGA = 1, 42
ASSINATURA = 'data:image/png;base64,iVBORw0KGgoAAAA'


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE deliveries (id INTEGER PRIMARY KEY, company_id INTEGER);
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO deliveries (id, company_id) VALUES (42, 1);
        """
    )
    ensure_delivery_evidence(conn)
    conn.commit()
    return conn


# ── o que a tabela existe para permitir ──────────────────────────────────────

def test_uma_entrega_pode_ter_varias_evidencias():
    """Assinatura no ato e conferência depois coexistem.

    É a razão de existir uma tabela em vez de mais colunas: nas colunas, a
    segunda evidência sobrescreveria a primeira.
    """
    conn = _conn()
    record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA,
        kind=SIGNATURE_HANDWRITTEN, content=ASSINATURA, collected_at='2026-07-28T10:00:00Z',
    )
    record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA,
        kind=QR_HANDOVER, content='token-abc', collected_at='2026-07-28T15:00:00Z',
    )
    evidencias = fetch_delivery_evidence(conn, ENTREGA)
    assert [e['kind'] for e in evidencias] == [SIGNATURE_HANDWRITTEN, QR_HANDOVER]


def test_evidencias_saem_em_ordem_cronologica():
    """Quem audita precisa da sequência dos fatos, não da ordem de inserção."""
    conn = _conn()
    record_evidence(conn, company_id=EMPRESA, delivery_id=ENTREGA, kind=QR_HANDOVER,
                    collected_at='2026-07-28T15:00:00Z')
    record_evidence(conn, company_id=EMPRESA, delivery_id=ENTREGA, kind=SIGNATURE_HANDWRITTEN,
                    collected_at='2026-07-28T10:00:00Z')
    momentos = [e['collected_at'] for e in fetch_delivery_evidence(conn, ENTREGA)]
    assert momentos == sorted(momentos)


def test_tipo_desconhecido_e_aceito():
    """Recusar o rótulo faria uma evidência **real** ser descartada.

    Perder prova é pior do que guardar um tipo fora da lista canônica — e um
    provedor biométrico novo não deve exigir migração para ser registrado.
    """
    conn = _conn()
    registro = record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA,
        kind='reconhecimento_facial_provedor_x', provider='provedor-x',
    )
    assert registro['kind'] == 'reconhecimento_facial_provedor_x'


def test_tipo_vazio_e_recusado():
    """Evidência sem tipo não é evidência — é linha órfã."""
    conn = _conn()
    with pytest.raises(ValueError):
        record_evidence(conn, company_id=EMPRESA, delivery_id=ENTREGA, kind='   ')


# ── conteúdo: hash, não segunda cópia ────────────────────────────────────────

def test_guarda_o_hash_e_nao_o_conteudo():
    """Duplicar a imagem da assinatura dobraria a exposição de dado pessoal."""
    conn = _conn()
    registro = record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA,
        kind=SIGNATURE_HANDWRITTEN, content=ASSINATURA,
        content_ref='deliveries.signature_data',
    )
    assert registro['content_hash'] == content_hash(ASSINATURA)
    assert ASSINATURA not in str(dict(registro).values())
    assert registro['content_ref'] == 'deliveries.signature_data'


def test_hash_muda_quando_o_conteudo_muda():
    """É o que torna o hash uma prova de integridade."""
    assert content_hash('assinatura-a') != content_hash('assinatura-b')
    assert content_hash(ASSINATURA) == content_hash(ASSINATURA)


def test_sem_conteudo_o_hash_fica_vazio():
    """Biometria pode não devolver conteúdo — só o veredito do provedor."""
    conn = _conn()
    registro = record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA, kind=BIOMETRICS,
        provider='aparelho', notes='digital conferida no aparelho',
    )
    assert registro['content_hash'] == ''
    assert registro['provider'] == 'aparelho'


# ── compatibilidade com o histórico ──────────────────────────────────────────

def test_entrega_antiga_sem_registro_le_das_colunas_de_assinatura():
    """Leitura uniforme sem reescrever histórico.

    Uma migração em massa reescreveria registros antigos para dizer algo que
    eles nunca disseram. Melhor projetar a coluna na leitura e marcar que é isso
    que está acontecendo.
    """
    conn = _conn()
    antiga = {
        'id': ENTREGA, 'company_id': EMPRESA,
        'signature_data': ASSINATURA, 'signature_name': 'Ana Souza',
        'signature_ip': '10.0.0.9', 'signature_at': '2025-03-01T12:00:00Z',
        'signature_comment': 'recebido em mãos',
    }
    evidencias = fetch_delivery_evidence(conn, ENTREGA, delivery=antiga)
    assert len(evidencias) == 1
    assert evidencias[0]['kind'] == SIGNATURE_HANDWRITTEN
    assert evidencias[0]['subject_name'] == 'Ana Souza'
    assert evidencias[0]['content_hash'] == content_hash(ASSINATURA)
    assert evidencias[0]['synthesized_from_legacy_columns'] is True
    assert evidencias[0]['id'] is None, 'projeção não pode se passar por registro'


def test_registro_real_tem_precedencia_sobre_as_colunas_antigas():
    conn = _conn()
    record_evidence(conn, company_id=EMPRESA, delivery_id=ENTREGA, kind=BIOMETRICS)
    antiga = {'id': ENTREGA, 'company_id': EMPRESA, 'signature_data': ASSINATURA,
              'signature_at': '2025-03-01T12:00:00Z'}
    evidencias = fetch_delivery_evidence(conn, ENTREGA, delivery=antiga)
    assert [e['kind'] for e in evidencias] == [BIOMETRICS]


def test_entrega_sem_assinatura_nenhuma_nao_inventa_evidencia():
    conn = _conn()
    vazia = {'id': ENTREGA, 'company_id': EMPRESA, 'signature_data': '', 'signature_at': ''}
    assert fetch_delivery_evidence(conn, ENTREGA, delivery=vazia) == []


def test_schema_sem_a_tabela_nao_quebra():
    """Janela de migração: registrar vira no-op, ler cai nas colunas antigas."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    assert record_evidence(conn, company_id=EMPRESA, delivery_id=ENTREGA,
                           kind=SIGNATURE_HANDWRITTEN) is None
    antiga = {'id': ENTREGA, 'company_id': EMPRESA, 'signature_data': ASSINATURA,
              'signature_at': '2025-03-01T12:00:00Z'}
    assert len(fetch_delivery_evidence(conn, ENTREGA, delivery=antiga)) == 1


# ── quem, quando, de onde ────────────────────────────────────────────────────

def test_registra_responsavel_momento_e_origem():
    """Sem isso é um carimbo anônimo — não serve de prova."""
    conn = _conn()
    registro = record_evidence(
        conn, company_id=EMPRESA, delivery_id=ENTREGA, kind=SIGNATURE_HANDWRITTEN,
        content=ASSINATURA, actor_user_id=7, actor_name='Carlos (almoxarife)',
        subject_name='Ana Souza', client_ip='192.168.1.10',
        collected_at='2026-07-28T10:00:00Z',
    )
    assert registro['actor_user_id'] == 7
    assert registro['actor_name'] == 'Carlos (almoxarife)'
    assert registro['subject_name'] == 'Ana Souza'
    assert registro['client_ip'] == '192.168.1.10'
    assert registro['collected_at'] == '2026-07-28T10:00:00Z'
    # `created_at` é quando o sistema gravou; `collected_at` é quando o fato
    # aconteceu. Confundir os dois apaga a diferença entre colher e registrar.
    assert registro['created_at'] != registro['collected_at']


def test_evidencia_de_outra_entrega_nao_aparece():
    conn = _conn()
    conn.execute('INSERT INTO deliveries (id, company_id) VALUES (43, 1)')
    record_evidence(conn, company_id=EMPRESA, delivery_id=43, kind=BIOMETRICS)
    assert fetch_delivery_evidence(conn, ENTREGA) == []
