"""Domínios por tenant (tenant_domains) — registro, verificação CNAME/SSL e ativação.

Tipos permitidos:
  - platform_subdomain: rótulo sob o domínio da plataforma (empresa.epicontrole.com.br),
    verificado automaticamente (o DNS é nosso).
  - custom_subdomain / custom_domain: FQDN do cliente (epi.empresa.com.br),
    ativado somente após validação de CNAME apontando para a plataforma e,
    como prova de propriedade, um registro TXT com o token de verificação.

A verificação DNS usa um resolvedor mínimo em stdlib (UDP) e a checagem de
SSL é best-effort (handshake TLS com SNI). Testes e ambientes offline podem
monkeypatchar ``dns_lookup``/``check_ssl_active``.
"""

from __future__ import annotations

import os
import re
import secrets
import socket
import ssl
import struct
from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log

UTC = timezone.utc

DOMAIN_TYPES = ('platform_subdomain', 'custom_subdomain', 'custom_domain')

_SUBDOMAIN_RE = re.compile(r'^(?!-)[a-z0-9-]{1,63}(?<!-)$')
_FQDN_RE = re.compile(r'^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$')

_TYPE_LABELS = {
    'platform_subdomain': 'Subdomínio da plataforma',
    'custom_subdomain': 'Subdomínio personalizado',
    'custom_domain': 'Domínio personalizado',
}


def platform_base_domain() -> str:
    return os.environ.get('TENANT_BASE_DOMAIN', 'epicontrole.com').strip().lower() or 'epicontrole.com'


def cname_target() -> str:
    """Host que os CNAMEs dos clientes devem apontar."""
    return os.environ.get('TENANT_CNAME_TARGET', f'app.{platform_base_domain()}').strip().lower()


# ── DNS mínimo em stdlib (UDP) ────────────────────────────────────────────────

_QTYPE = {'CNAME': 5, 'TXT': 16, 'A': 1}


def _encode_qname(name: str) -> bytes:
    out = b''
    for part in name.strip('.').split('.'):
        raw = part.encode('idna') if any(ord(c) > 127 for c in part) else part.encode('ascii')
        out += bytes([len(raw)]) + raw
    return out + b'\x00'


def _skip_name(data: bytes, offset: int) -> int:
    while True:
        length = data[offset]
        if length == 0:
            return offset + 1
        if length & 0xC0 == 0xC0:  # ponteiro de compressão
            return offset + 2
        offset += length + 1


def _decode_name(data: bytes, offset: int, depth: int = 0) -> str:
    if depth > 10:
        return ''
    labels = []
    while True:
        length = data[offset]
        if length == 0:
            break
        if length & 0xC0 == 0xC0:
            pointer = struct.unpack('>H', data[offset:offset + 2])[0] & 0x3FFF
            suffix = _decode_name(data, pointer, depth + 1)
            if suffix:
                labels.append(suffix)
            break
        offset += 1
        labels.append(data[offset:offset + length].decode('ascii', 'replace'))
        offset += length
    return '.'.join(labels)


def dns_lookup(name: str, record_type: str = 'CNAME', timeout: float = 3.0) -> list[str]:
    """Consulta DNS mínima via UDP. Retorna lista de valores (CNAME alvo / strings TXT).

    Best-effort: qualquer falha (rede bloqueada, timeout, resposta malformada)
    retorna lista vazia — o chamador trata como "não verificado ainda".
    """
    resolver = os.environ.get('DNS_RESOLVER', '8.8.8.8').strip() or '8.8.8.8'
    qtype = _QTYPE.get(record_type.upper())
    if not qtype or not name:
        return []
    query_id = secrets.randbelow(65536)
    header = struct.pack('>HHHHHH', query_id, 0x0100, 1, 0, 0, 0)
    question = _encode_qname(name) + struct.pack('>HH', qtype, 1)
    packet = header + question
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (resolver, 53))
            data, _addr = sock.recvfrom(4096)
    except Exception as exc:
        structured_log('warning', 'tenant_domains.dns_lookup_failed', name=name, type=record_type, error=str(exc))
        return []
    try:
        if len(data) < 12 or struct.unpack('>H', data[:2])[0] != query_id:
            return []
        answer_count = struct.unpack('>H', data[6:8])[0]
        offset = _skip_name(data, 12) + 4  # pergunta: nome + tipo/classe
        values: list[str] = []
        for _ in range(answer_count):
            offset = _skip_name(data, offset)
            rtype, _rclass, _ttl, rdlength = struct.unpack('>HHIH', data[offset:offset + 10])
            offset += 10
            rdata = data[offset:offset + rdlength]
            if rtype == _QTYPE['CNAME']:
                values.append(_decode_name(data, offset).lower().rstrip('.'))
            elif rtype == _QTYPE['TXT']:
                pos = 0
                chunks = []
                while pos < len(rdata):
                    ln = rdata[pos]
                    chunks.append(rdata[pos + 1:pos + 1 + ln].decode('utf-8', 'replace'))
                    pos += 1 + ln
                values.append(''.join(chunks))
            offset += rdlength
        return values
    except Exception as exc:
        structured_log('warning', 'tenant_domains.dns_parse_failed', name=name, type=record_type, error=str(exc))
        return []


def check_ssl_active(host: str, timeout: float = 4.0) -> bool:
    """Handshake TLS com SNI para confirmar certificado válido. Best-effort."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                return bool(tls.getpeercert())
    except Exception:
        return False


# ── CRUD / regras de negócio ──────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def normalize_domain_value(domain: str, domain_type: str) -> str:
    value = str(domain or '').strip().lower().rstrip('.')
    if domain_type == 'platform_subdomain':
        # aceita "empresa" ou "empresa.epicontrole.com.br" (guarda só o rótulo)
        base = '.' + platform_base_domain()
        if value.endswith(base):
            value = value[: -len(base)]
        if not _SUBDOMAIN_RE.match(value):
            raise ValueError(f"Subdomínio inválido: '{value}'. Use apenas letras minúsculas, números e hífens.")
        return value
    if domain_type not in DOMAIN_TYPES:
        raise ValueError(f"Tipo de domínio inválido: '{domain_type}'.")
    if not _FQDN_RE.match(value):
        raise ValueError(f"Domínio inválido: '{value}'.")
    if value == platform_base_domain() or value.endswith('.' + platform_base_domain()):
        raise ValueError('Para subdomínios da plataforma use o tipo platform_subdomain.')
    return value


def ensure_domain_available(connection, domain: str, domain_type: str, company_id: int) -> None:
    """Associação única: um domínio pertence a no máximo uma tenant."""
    row = connection.execute(
        'SELECT company_id FROM tenant_domains WHERE domain = ? AND domain_type = ?',
        (domain, domain_type),
    ).fetchone()
    if row and int(row_to_dict(row)['company_id']) != int(company_id):
        raise ValueError(f"O domínio '{domain}' já está registrado para outra tenant.")
    # colunas legadas ainda usadas no roteamento (empresas sem linha em tenant_domains)
    if domain_type == 'platform_subdomain':
        legacy = connection.execute(
            'SELECT id FROM companies WHERE (subdomain = ? OR slug = ?) AND id != ?',
            (domain, domain, int(company_id)),
        ).fetchone()
    else:
        legacy = connection.execute(
            'SELECT id FROM companies WHERE custom_domain = ? AND id != ?',
            (domain, int(company_id)),
        ).fetchone()
    if legacy:
        raise ValueError(f"O domínio '{domain}' já está em uso por outra empresa.")


def list_company_domains(connection, company_id: int) -> list[dict]:
    rows = connection.execute(
        'SELECT id, company_id, domain, domain_type, verification_token, verification_status, '
        'ssl_status, is_primary, created_at, verified_at '
        'FROM tenant_domains WHERE company_id = ? ORDER BY is_primary DESC, id ASC',
        (int(company_id),),
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        item['type_label'] = _TYPE_LABELS.get(item.get('domain_type'), item.get('domain_type'))
        if item.get('domain_type') == 'platform_subdomain':
            item['full_host'] = f"{item['domain']}.{platform_base_domain()}"
        else:
            item['full_host'] = item['domain']
        item['cname_target'] = cname_target()
        item['txt_record'] = f"_epicontrole-verify.{item['full_host']}"
        items.append(item)
    return items


def register_company_domain(connection, company_id: int, domain: str, domain_type: str) -> dict:
    domain_type = str(domain_type or '').strip().lower()
    if domain_type not in DOMAIN_TYPES:
        raise ValueError(f"Tipo de domínio inválido: '{domain_type}'. Use {', '.join(DOMAIN_TYPES)}.")
    value = normalize_domain_value(domain, domain_type)

    existing_own = connection.execute(
        'SELECT id FROM tenant_domains WHERE domain = ? AND domain_type = ? AND company_id = ?',
        (value, domain_type, int(company_id)),
    ).fetchone()
    if existing_own:
        raise ValueError(f"O domínio '{value}' já está registrado para a sua empresa.")
    ensure_domain_available(connection, value, domain_type, int(company_id))

    now = _now()
    if domain_type == 'platform_subdomain':
        # DNS da plataforma: verificado imediatamente e sincronizado no roteamento
        cursor = connection.execute(
            'INSERT INTO tenant_domains (company_id, domain, domain_type, verification_token, '
            "verification_status, ssl_status, is_primary, created_at, verified_at) "
            "VALUES (?, ?, ?, '', 'verified', 'active', 0, ?, ?)",
            (int(company_id), value, domain_type, now, now),
        )
        connection.execute(
            'UPDATE companies SET subdomain = ? WHERE id = ?', (value, int(company_id))
        )
    else:
        token = f'epi-verify-{secrets.token_urlsafe(16)}'
        cursor = connection.execute(
            'INSERT INTO tenant_domains (company_id, domain, domain_type, verification_token, '
            "verification_status, ssl_status, is_primary, created_at, verified_at) "
            "VALUES (?, ?, ?, ?, 'pending', 'pending', 0, ?, '')",
            (int(company_id), value, domain_type, token, now),
        )
    domain_id = int(cursor.lastrowid)
    structured_log('info', 'tenant_domains.registered',
                   company_id=int(company_id), domain=value, domain_type=domain_type)
    return get_company_domain(connection, int(company_id), domain_id)


def get_company_domain(connection, company_id: int, domain_id: int) -> dict | None:
    for item in list_company_domains(connection, company_id):
        if int(item['id']) == int(domain_id):
            return item
    return None


def verify_company_domain(connection, company_id: int, domain_id: int) -> dict:
    """Valida CNAME + propriedade (TXT) e ativa o domínio. Exige assinatura ativa."""
    record = get_company_domain(connection, company_id, domain_id)
    if not record:
        raise ValueError('Domínio não encontrado para a sua empresa.')

    company = connection.execute(
        'SELECT active, license_status FROM companies WHERE id = ?', (int(company_id),)
    ).fetchone()
    company = row_to_dict(company) if company else {}
    if int(company.get('active') or 0) != 1 or str(company.get('license_status') or '') in ('suspended', 'expired'):
        raise PermissionError('Domínio só pode ser ativado com a assinatura ativa.')

    if record['domain_type'] == 'platform_subdomain':
        return record  # já nasce verificado

    host = record['full_host']
    checks = {'cname': False, 'txt': False, 'ssl': False}

    cname_values = dns_lookup(host, 'CNAME')
    expected = cname_target()
    checks['cname'] = any(v == expected or v.endswith('.' + expected) for v in cname_values)

    txt_values = dns_lookup(f'_epicontrole-verify.{host}', 'TXT')
    checks['txt'] = any(record['verification_token'] and record['verification_token'] in v for v in txt_values)

    if not checks['cname']:
        connection.execute(
            "UPDATE tenant_domains SET verification_status = 'failed' WHERE id = ?", (int(domain_id),)
        )
        structured_log('warning', 'tenant_domains.verify_failed',
                       company_id=int(company_id), domain=host, checks=checks)
        raise ValueError(
            f'CNAME não encontrado. Configure {host} → {expected} e o TXT '
            f'_epicontrole-verify.{host} = "{record["verification_token"]}", então verifique novamente.'
        )
    if not checks['txt']:
        connection.execute(
            "UPDATE tenant_domains SET verification_status = 'failed' WHERE id = ?", (int(domain_id),)
        )
        structured_log('warning', 'tenant_domains.verify_failed',
                       company_id=int(company_id), domain=host, checks=checks)
        raise ValueError(
            f'Prova de propriedade ausente. Crie o registro TXT _epicontrole-verify.{host} '
            f'com o valor "{record["verification_token"]}" e verifique novamente.'
        )

    checks['ssl'] = check_ssl_active(host)
    ssl_status = 'active' if checks['ssl'] else 'pending'
    now = _now()
    connection.execute(
        "UPDATE tenant_domains SET verification_status = 'verified', ssl_status = ?, verified_at = ? WHERE id = ?",
        (ssl_status, now, int(domain_id)),
    )
    # sincroniza o roteamento legado (resolve_tenant_by_host usa companies.custom_domain)
    connection.execute(
        'UPDATE companies SET custom_domain = ? WHERE id = ?', (host, int(company_id))
    )
    structured_log('info', 'tenant_domains.verified',
                   company_id=int(company_id), domain=host, ssl_status=ssl_status)
    return get_company_domain(connection, company_id, domain_id)


def set_primary_company_domain(connection, company_id: int, domain_id: int) -> dict:
    record = get_company_domain(connection, company_id, domain_id)
    if not record:
        raise ValueError('Domínio não encontrado para a sua empresa.')
    if record['verification_status'] != 'verified':
        raise ValueError('Somente domínios verificados podem ser definidos como principal.')
    connection.execute(
        'UPDATE tenant_domains SET is_primary = 0 WHERE company_id = ?', (int(company_id),)
    )
    connection.execute(
        'UPDATE tenant_domains SET is_primary = 1 WHERE id = ?', (int(domain_id),)
    )
    return get_company_domain(connection, company_id, domain_id)


def delete_company_domain(connection, company_id: int, domain_id: int) -> dict:
    record = get_company_domain(connection, company_id, domain_id)
    if not record:
        raise ValueError('Domínio não encontrado para a sua empresa.')
    connection.execute('DELETE FROM tenant_domains WHERE id = ?', (int(domain_id),))
    # limpa o roteamento legado se apontava para este domínio
    if record['domain_type'] == 'platform_subdomain':
        connection.execute(
            'UPDATE companies SET subdomain = NULL WHERE id = ? AND subdomain = ?',
            (int(company_id), record['domain']),
        )
    else:
        connection.execute(
            'UPDATE companies SET custom_domain = NULL WHERE id = ? AND custom_domain = ?',
            (int(company_id), record['domain']),
        )
    structured_log('info', 'tenant_domains.deleted',
                   company_id=int(company_id), domain=record['domain'], domain_type=record['domain_type'])
    return record


# ── Resolução de tenant via tenant_domains ────────────────────────────────────

def find_company_id_by_host(connection, host: str, base_domain: str | None = None) -> int | None:
    """Resolve a tenant pelo host consultando tenant_domains (apenas verificados)."""
    normalized = str(host or '').strip().lower().split(':')[0]
    if normalized.startswith('www.'):
        normalized = normalized[4:]
    if not normalized:
        return None
    try:
        row = connection.execute(
            "SELECT company_id FROM tenant_domains "
            "WHERE domain = ? AND domain_type IN ('custom_subdomain', 'custom_domain') "
            "AND verification_status = 'verified' LIMIT 1",
            (normalized,),
        ).fetchone()
        if row:
            return int(row_to_dict(row)['company_id'])
        base = (base_domain or platform_base_domain()).lower()
        if normalized.endswith('.' + base):
            label = normalized[: -(len(base) + 1)]
            row = connection.execute(
                "SELECT company_id FROM tenant_domains "
                "WHERE domain = ? AND domain_type = 'platform_subdomain' "
                "AND verification_status = 'verified' LIMIT 1",
                (label,),
            ).fetchone()
            if row:
                return int(row_to_dict(row)['company_id'])
    except Exception:
        # tabela ainda não migrada — o chamador usa o fallback legado
        try:
            connection.rollback()
        except Exception:
            pass
    return None
