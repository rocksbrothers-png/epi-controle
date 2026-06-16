"""Serviços comerciais: configurações, marca, contratos e métricas."""
import base64
import json
import textwrap
from datetime import date, datetime, timezone

from core.auth import ensure_company_access
from core.meta import get_meta, set_meta
from core.roles import BILLABLE_ROLES
from epi_backend.db import row_to_dict
from core.pdf import build_pdf_document, extract_pdf_logo_image

UTC = timezone.utc

COMMERCIAL_CONTRACT_STATUS = {
    'draft', 'generated', 'sent', 'pending_signature', 'signed', 'active', 'closed', 'archived'
}

DEFAULT_SAAS_CONTRACT_CLAUSES = """1. OBJETO
A CONTRATADA disponibiliza à CONTRATANTE licença de uso do sistema EPI Controle, no modelo SaaS.

2. LICENÇA DE USO, PLANOS E LIMITES
O uso observará o plano contratado, limite de usuários e regras de aditivo comercial configuradas.

3. DISPONIBILIDADE E SUPORTE
A CONTRATADA manterá o serviço e canais de suporte em padrões compatíveis com operação corporativa.

4. OBRIGAÇÕES DA CONTRATANTE
Manter dados cadastrais atualizados, cumprir políticas de uso e preservar credenciais de acesso.

5. OBRIGAÇÕES DA CONTRATADA
Manter a plataforma em funcionamento, promover melhorias contínuas e zelar pela segurança da informação.

6. CONFIDENCIALIDADE E PROTEÇÃO DE DADOS
As partes observam confidencialidade mútua e legislação aplicável de proteção de dados pessoais.

7. PREÇO, PAGAMENTO E REAJUSTE
Os valores vigentes, periodicidade e critérios de reajuste seguem os dados comerciais aprovados no sistema.

8. VIGÊNCIA, RENOVAÇÃO E RESCISÃO
A vigência inicia na data contratual registrada e encerra conforme prazo definido, admitindo renovação/aditivo.

9. ADITIVOS CONTRATUAIS
Alterações de escopo, limite de usuários, preço e condições devem ser formalizadas por aditivo.

10. RESPONSABILIDADE, FORO E DISPOSIÇÕES GERAIS
As partes elegem o foro contratual acordado e reconhecem a validade de assinatura digital."""

DEFAULT_COMMERCIAL_SETTINGS = {
    'unit_price': 42.0,
    'plans': {
        'individual': {'label': 'Individual', 'min_users': 1, 'max_users': 1},
        'start': {'label': 'Start', 'min_users': 1, 'max_users': 10},
        'business': {'label': 'Business', 'min_users': 11, 'max_users': 25},
        'corporate': {'label': 'Corporate', 'min_users': 26, 'max_users': 100},
        'enterprise': {'label': 'Enterprise', 'min_users': 101, 'max_users': None},
    },
}

DEFAULT_PLATFORM_BRAND = {'display_name': 'Sua Empresa', 'legal_name': '', 'cnpj': '', 'logo_type': '', 'login_logo_type': ''}


def only_digits(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def format_cnpj(value):
    digits = only_digits(value)
    if len(digits) != 14:
        return str(value or '').strip()
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def is_valid_cnpj(value):
    digits = only_digits(value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    numbers = [int(item) for item in digits]
    weights_one = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(number * weight for number, weight in zip(numbers[:12], weights_one))
    remainder = total % 11
    digit_one = 0 if remainder < 2 else 11 - remainder
    weights_two = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(number * weight for number, weight in zip(numbers[:12] + [digit_one], weights_two))
    remainder = total % 11
    digit_two = 0 if remainder < 2 else 11 - remainder
    return numbers[12] == digit_one and numbers[13] == digit_two


def validate_cnpj(value):
    if not is_valid_cnpj(value):
        raise ValueError('CNPJ inválido.')
    return format_cnpj(value)


def validate_logo_payload(value):
    logo = str(value or '').strip()
    if not logo:
        return ''
    if logo.startswith('data:image/'):
        allowed = ('data:image/png', 'data:image/jpeg', 'data:image/jpg', 'data:image/svg+xml')
        if not logo.startswith(allowed):
            raise ValueError('Logotipo inválido. Envie PNG, JPG ou SVG.')
    return logo


def validate_login_logo_payload(value):
    logo = str(value or '').strip()
    if not logo:
        return ''
    if not logo.startswith(('data:image/png', 'data:image/svg+xml')):
        raise ValueError('Logotipo da tela de login inválido. Envie PNG ou SVG.')
    return logo


def company_license_label(status):
    return {
        'active': 'Ativo',
        'trial': 'Trial',
        'suspended': 'Suspenso',
        'expired': 'Expirado',
    }.get(status, status)


def count_company_users(connection, company_id):
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    return connection.execute(
        f"SELECT COUNT(*) FROM users WHERE company_id = ? AND active = 1 AND role IN ({placeholders})",
        (company_id, *BILLABLE_ROLES)
    ).fetchone()[0]


def default_commercial_settings():
    return json.loads(json.dumps(DEFAULT_COMMERCIAL_SETTINGS))


def normalize_plan_key(value):
    normalized = str(value or '').strip().lower()
    aliases = {
        'individual': 'individual',
        'indivudual': 'individual',
        'start': 'start',
        'business': 'business',
        'corporate': 'corporate',
        'enterprise': 'enterprise',
    }
    return aliases.get(normalized, normalized)


def ensure_commercial_settings(connection):
    if not get_meta(connection, 'commercial_settings'):
        set_meta(connection, 'commercial_settings', json.dumps(default_commercial_settings(), ensure_ascii=False))


def get_commercial_settings(connection):
    settings = default_commercial_settings()
    raw = get_meta(connection, 'commercial_settings')
    if not raw:
        return settings
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return settings
    settings['unit_price'] = float(parsed.get('unit_price', settings['unit_price']) or settings['unit_price'])
    for key, plan in settings['plans'].items():
        source = (parsed.get('plans') or {}).get(key, {})
        plan['label'] = str(source.get('label', plan['label'])).strip() or plan['label']
        plan['min_users'] = max(1, int(source.get('min_users', plan['min_users']) or plan['min_users']))
        raw_max = source.get('max_users', plan['max_users'])
        plan['max_users'] = None if raw_max in (None, '', 'null') else max(plan['min_users'], int(raw_max))
    return settings


def save_commercial_settings(connection, payload, *, require_master_actor_fn=None):
    if require_master_actor_fn is not None:
        actor = require_master_actor_fn(connection, int(payload.get('actor_user_id') or 0))
    else:
        actor = None
    current = get_commercial_settings(connection)
    unit_price = float(str(payload.get('unit_price', current['unit_price'])).replace(',', '.'))
    if unit_price <= 0:
        raise ValueError('O valor unitario precisa ser maior que zero.')
    plans_payload = payload.get('plans') or {}
    settings = default_commercial_settings()
    settings['unit_price'] = unit_price
    details = [{'field': 'Valor unitario', 'before': str(current['unit_price']), 'after': str(unit_price)}]
    for key, default_plan in settings['plans'].items():
        current_plan = current['plans'][key]
        source = plans_payload.get(key) or current_plan
        label = str(source.get('label', default_plan['label'])).strip() or default_plan['label']
        min_users = max(1, int(source.get('min_users', default_plan['min_users']) or default_plan['min_users']))
        raw_max = source.get('max_users', default_plan['max_users'])
        max_users = None if raw_max in (None, '', 'null') else max(min_users, int(raw_max))
        settings['plans'][key] = {'label': label, 'min_users': min_users, 'max_users': max_users}
        details.append({
            'field': f'Plano {label}',
            'before': f"min {current_plan['min_users']} / max {current_plan['max_users'] if current_plan['max_users'] is not None else 'livre'}",
            'after': f"min {min_users} / max {max_users if max_users is not None else 'livre'}"
        })
    if settings['plans']['individual']['max_users'] < 1:
        raise ValueError('O plano Individual precisa permitir pelo menos 1 usuario.')
    if settings['plans']['start']['max_users'] < settings['plans']['individual']['max_users']:
        raise ValueError('O limite do plano Start nao pode ser menor que o Individual.')
    if settings['plans']['business']['min_users'] > settings['plans']['business']['max_users']:
        raise ValueError('O plano Business esta com faixa invalida.')
    if settings['plans']['corporate']['min_users'] > settings['plans']['corporate']['max_users']:
        raise ValueError('O plano Corporate esta com faixa invalida.')
    if settings['plans']['enterprise']['min_users'] <= settings['plans']['corporate']['max_users']:
        raise ValueError('O plano Enterprise precisa comecar acima do limite do Corporate.')
    set_meta(connection, 'commercial_settings', json.dumps(settings, ensure_ascii=False))
    return actor, settings, details


def commercial_plan_for_company(company, settings):
    return settings['plans'].get(normalize_plan_key(company.get('plan_name')))


def compute_company_contract_metrics(company, settings):
    active_users = int(company.get('user_count') or 0)
    user_limit = int(company.get('user_limit') or 0)
    unit_price = float(settings['unit_price'])
    addendum_enabled = int(company.get('addendum_enabled') or 0)
    plan = commercial_plan_for_company(company, settings)
    min_users = plan['min_users'] if plan else 1
    max_users = plan['max_users'] if plan else None
    return {
        'unit_price': unit_price,
        'calculated_monthly_value': round(active_users * unit_price, 2),
        'projected_monthly_value': round(user_limit * unit_price, 2),
        'plan_min_users': min_users,
        'plan_max_users': max_users,
        'requires_addendum': bool(plan and max_users is not None and user_limit > max_users),
        'within_plan_limit': bool(plan and user_limit >= min_users and (max_users is None or user_limit <= max_users)),
        'addendum_enabled': addendum_enabled,
    }


def get_platform_brand(connection):
    raw = get_meta(connection, 'platform_brand')
    if not raw:
        return dict(DEFAULT_PLATFORM_BRAND)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_PLATFORM_BRAND)
    return {**DEFAULT_PLATFORM_BRAND, **parsed}


def validate_platform_brand_payload(payload):
    brand = {
        'display_name': str(payload.get('display_name', '')).strip() or DEFAULT_PLATFORM_BRAND['display_name'],
        'legal_name': str(payload.get('legal_name', '')).strip(),
        'cnpj': str(payload.get('cnpj', '')).strip(),
        'logo_type': validate_logo_payload(payload.get('logo_type', '')),
        'login_logo_type': validate_login_logo_payload(payload.get('login_logo_type', '')),
    }
    if brand['cnpj']:
        brand['cnpj'] = validate_cnpj(brand['cnpj'])
    return brand


def save_platform_brand(connection, payload):
    brand = validate_platform_brand_payload(payload)
    set_meta(connection, 'platform_brand', json.dumps(brand, ensure_ascii=False))
    return brand


def ensure_commercial_contract_tables(connection):
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS commercial_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,
            contract_number TEXT NOT NULL DEFAULT '',
            issue_date TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            contractor_name TEXT NOT NULL DEFAULT '',
            contractor_legal_name TEXT NOT NULL DEFAULT '',
            contractor_trade_name TEXT NOT NULL DEFAULT '',
            contractor_cnpj TEXT NOT NULL DEFAULT '',
            contractor_address TEXT NOT NULL DEFAULT '',
            contractor_representative TEXT NOT NULL DEFAULT '',
            contractor_representative_role TEXT NOT NULL DEFAULT '',
            contractor_email TEXT NOT NULL DEFAULT '',
            contractor_phone TEXT NOT NULL DEFAULT '',
            contractor_witness_1 TEXT NOT NULL DEFAULT '',
            contractor_witness_2 TEXT NOT NULL DEFAULT '',
            provider_name TEXT NOT NULL DEFAULT '',
            provider_legal_name TEXT NOT NULL DEFAULT '',
            provider_cnpj TEXT NOT NULL DEFAULT '',
            provider_address TEXT NOT NULL DEFAULT '',
            provider_representative TEXT NOT NULL DEFAULT '',
            provider_representative_role TEXT NOT NULL DEFAULT '',
            provider_email TEXT NOT NULL DEFAULT '',
            provider_phone TEXT NOT NULL DEFAULT '',
            provider_witnesses TEXT NOT NULL DEFAULT '',
            clauses_text TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            generated_pdf_base64 TEXT NOT NULL DEFAULT '',
            signed_pdf_base64 TEXT NOT NULL DEFAULT '',
            signed_file_name TEXT NOT NULL DEFAULT '',
            signed_file_mime TEXT NOT NULL DEFAULT '',
            signed_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL DEFAULT '',
            retention_until TEXT NOT NULL DEFAULT '',
            last_email_to TEXT NOT NULL DEFAULT '',
            last_email_subject TEXT NOT NULL DEFAULT '',
            last_email_body TEXT NOT NULL DEFAULT '',
            last_email_sent_at TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            signature_data TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            addendum_history_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS commercial_contract_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            contract_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            actor_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (contract_id) REFERENCES commercial_contracts(id) ON DELETE CASCADE
        );
        '''
    )


def _next_retention_date(end_date_value):
    end_date_value = str(end_date_value or '').strip()
    if not end_date_value:
        return ''
    try:
        dt = datetime.strptime(end_date_value, '%Y-%m-%d').date()
    except ValueError:
        return ''
    return dt.replace(year=dt.year + 5).isoformat()


def _default_contract_payload(company, settings, brand):
    metrics = compute_company_contract_metrics(company, settings)
    today_iso = date.today().isoformat()
    return {
        'company_id': int(company['id']),
        'contract_number': f"CTR-{int(company['id']):05d}-{today_iso.replace('-', '')}",
        'issue_date': today_iso,
        'start_date': str(company.get('contract_start') or ''),
        'end_date': str(company.get('contract_end') or ''),
        'status': 'draft',
        'contractor_name': str(company.get('name') or ''),
        'contractor_legal_name': str(company.get('legal_name') or ''),
        'contractor_trade_name': str(company.get('name') or ''),
        'contractor_cnpj': str(company.get('cnpj') or ''),
        'contractor_address': '',
        'contractor_representative': '',
        'contractor_representative_role': '',
        'contractor_email': '',
        'contractor_phone': '',
        'contractor_witness_1': '',
        'contractor_witness_2': '',
        'provider_name': str(brand.get('display_name') or ''),
        'provider_legal_name': str(brand.get('legal_name') or ''),
        'provider_cnpj': str(brand.get('cnpj') or ''),
        'provider_address': '',
        'provider_representative': '',
        'provider_representative_role': '',
        'provider_email': '',
        'provider_phone': '',
        'provider_witnesses': '',
        'clauses_text': DEFAULT_SAAS_CONTRACT_CLAUSES,
        'notes': str(company.get('commercial_notes') or ''),
        'generated_pdf_base64': '',
        'signed_pdf_base64': '',
        'signed_file_name': '',
        'signed_file_mime': '',
        'signed_at': '',
        'archived_at': '',
        'retention_until': _next_retention_date(company.get('contract_end')),
        'last_email_to': '',
        'last_email_subject': '',
        'last_email_body': '',
        'last_email_sent_at': '',
        'signature_name': '',
        'signature_data': '',
        'signature_at': '',
        'addendum_history_json': '[]',
        'metrics': metrics,
    }


def get_or_create_commercial_contract(connection, actor, company_id):
    ensure_company_access(actor, company_id)
    company_row = connection.execute('SELECT * FROM companies WHERE id = ?', (int(company_id),)).fetchone()
    if not company_row:
        raise ValueError('Empresa nao encontrada.')
    company = row_to_dict(company_row)
    settings = get_commercial_settings(connection)
    brand = get_platform_brand(connection)
    row = connection.execute('SELECT * FROM commercial_contracts WHERE company_id = ?', (int(company_id),)).fetchone()
    now = datetime.now(UTC).isoformat()
    if not row:
        payload = _default_contract_payload(company, settings, brand)
        connection.execute(
            '''
            INSERT INTO commercial_contracts (
                company_id, contract_number, issue_date, start_date, end_date, status,
                contractor_name, contractor_legal_name, contractor_trade_name, contractor_cnpj, contractor_address,
                contractor_representative, contractor_representative_role, contractor_email, contractor_phone,
                contractor_witness_1, contractor_witness_2,
                provider_name, provider_legal_name, provider_cnpj, provider_address, provider_representative,
                provider_representative_role, provider_email, provider_phone, provider_witnesses,
                clauses_text, notes, generated_pdf_base64, signed_pdf_base64, signed_file_name, signed_file_mime,
                signed_at, archived_at, retention_until, last_email_to, last_email_subject, last_email_body,
                last_email_sent_at, signature_name, signature_data, signature_at, addendum_history_json,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (
                payload['company_id'], payload['contract_number'], payload['issue_date'], payload['start_date'], payload['end_date'], payload['status'],
                payload['contractor_name'], payload['contractor_legal_name'], payload['contractor_trade_name'], payload['contractor_cnpj'], payload['contractor_address'],
                payload['contractor_representative'], payload['contractor_representative_role'], payload['contractor_email'], payload['contractor_phone'],
                payload['contractor_witness_1'], payload['contractor_witness_2'],
                payload['provider_name'], payload['provider_legal_name'], payload['provider_cnpj'], payload['provider_address'], payload['provider_representative'],
                payload['provider_representative_role'], payload['provider_email'], payload['provider_phone'], payload['provider_witnesses'],
                payload['clauses_text'], payload['notes'], payload['generated_pdf_base64'], payload['signed_pdf_base64'], payload['signed_file_name'], payload['signed_file_mime'],
                payload['signed_at'], payload['archived_at'], payload['retention_until'], payload['last_email_to'], payload['last_email_subject'], payload['last_email_body'],
                payload['last_email_sent_at'], payload['signature_name'], payload['signature_data'], payload['signature_at'], payload['addendum_history_json'],
                now, now
            )
        )
        row = connection.execute('SELECT * FROM commercial_contracts WHERE company_id = ?', (int(company_id),)).fetchone()
    contract = row_to_dict(row)
    contract['metrics'] = compute_company_contract_metrics(company, settings)
    contract['company'] = company
    contract['provider_brand'] = brand
    events = connection.execute(
        '''
        SELECT id, event_type, details_json, actor_name, created_at
        FROM commercial_contract_events
        WHERE company_id = ?
        ORDER BY id DESC
        LIMIT 20
        ''',
        (int(company_id),)
    ).fetchall()
    contract['events'] = [row_to_dict(item) for item in events]
    return contract


def register_commercial_contract_event(connection, actor, contract, event_type, details=None):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        INSERT INTO commercial_contract_events (
            company_id, contract_id, actor_user_id, actor_name, event_type, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(contract['company_id']),
            int(contract['id']),
            int(actor['id']),
            str(actor.get('full_name') or ''),
            str(event_type or '').strip(),
            json.dumps(details or {}, ensure_ascii=False),
            now
        )
    )


def save_commercial_contract(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    status = str(payload.get('status') or contract.get('status') or 'draft').strip().lower()
    if status not in COMMERCIAL_CONTRACT_STATUS:
        raise ValueError('Status de contrato inválido.')
    end_date = str(payload.get('end_date') or contract.get('end_date') or '').strip()
    update_data = {
        'contract_number': str(payload.get('contract_number') or contract.get('contract_number') or '').strip(),
        'issue_date': str(payload.get('issue_date') or contract.get('issue_date') or '').strip(),
        'start_date': str(payload.get('start_date') or contract.get('start_date') or '').strip(),
        'end_date': end_date,
        'status': status,
        'contractor_name': str(payload.get('contractor_name') or '').strip(),
        'contractor_legal_name': str(payload.get('contractor_legal_name') or '').strip(),
        'contractor_trade_name': str(payload.get('contractor_trade_name') or '').strip(),
        'contractor_cnpj': str(payload.get('contractor_cnpj') or '').strip(),
        'contractor_address': str(payload.get('contractor_address') or '').strip(),
        'contractor_representative': str(payload.get('contractor_representative') or '').strip(),
        'contractor_representative_role': str(payload.get('contractor_representative_role') or '').strip(),
        'contractor_email': str(payload.get('contractor_email') or '').strip().lower(),
        'contractor_phone': str(payload.get('contractor_phone') or '').strip(),
        'contractor_witness_1': str(payload.get('contractor_witness_1') or '').strip(),
        'contractor_witness_2': str(payload.get('contractor_witness_2') or '').strip(),
        'provider_name': str(payload.get('provider_name') or '').strip(),
        'provider_legal_name': str(payload.get('provider_legal_name') or '').strip(),
        'provider_cnpj': str(payload.get('provider_cnpj') or '').strip(),
        'provider_address': str(payload.get('provider_address') or '').strip(),
        'provider_representative': str(payload.get('provider_representative') or '').strip(),
        'provider_representative_role': str(payload.get('provider_representative_role') or '').strip(),
        'provider_email': str(payload.get('provider_email') or '').strip().lower(),
        'provider_phone': str(payload.get('provider_phone') or '').strip(),
        'provider_witnesses': str(payload.get('provider_witnesses') or '').strip(),
        'clauses_text': str(payload.get('clauses_text') or '').strip() or DEFAULT_SAAS_CONTRACT_CLAUSES,
        'notes': str(payload.get('notes') or '').strip(),
        'retention_until': _next_retention_date(end_date),
    }
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts SET
            contract_number = ?, issue_date = ?, start_date = ?, end_date = ?, status = ?,
            contractor_name = ?, contractor_legal_name = ?, contractor_trade_name = ?, contractor_cnpj = ?, contractor_address = ?,
            contractor_representative = ?, contractor_representative_role = ?, contractor_email = ?, contractor_phone = ?,
            contractor_witness_1 = ?, contractor_witness_2 = ?, provider_name = ?, provider_legal_name = ?, provider_cnpj = ?,
            provider_address = ?, provider_representative = ?, provider_representative_role = ?, provider_email = ?, provider_phone = ?,
            provider_witnesses = ?, clauses_text = ?, notes = ?, retention_until = ?, updated_at = ?
        WHERE id = ?
        ''',
        (
            update_data['contract_number'], update_data['issue_date'], update_data['start_date'], update_data['end_date'], update_data['status'],
            update_data['contractor_name'], update_data['contractor_legal_name'], update_data['contractor_trade_name'], update_data['contractor_cnpj'], update_data['contractor_address'],
            update_data['contractor_representative'], update_data['contractor_representative_role'], update_data['contractor_email'], update_data['contractor_phone'],
            update_data['contractor_witness_1'], update_data['contractor_witness_2'], update_data['provider_name'], update_data['provider_legal_name'], update_data['provider_cnpj'],
            update_data['provider_address'], update_data['provider_representative'], update_data['provider_representative_role'], update_data['provider_email'], update_data['provider_phone'],
            update_data['provider_witnesses'], update_data['clauses_text'], update_data['notes'], update_data['retention_until'], now,
            int(contract['id'])
        )
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'saved', {'status': updated.get('status')})
    return updated


def generate_commercial_contract_pdf(connection, actor, company_id):
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    pdf_bytes = build_commercial_contract_pdf(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE commercial_contracts SET generated_pdf_base64 = ?, status = ?, updated_at = ? WHERE id = ?',
        (base64.b64encode(pdf_bytes).decode('ascii'), 'generated', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'generated', {})
    return updated


def sign_commercial_contract(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_data = str(payload.get('signature_data') or '').strip()
    if not signature_name or not signature_data:
        raise ValueError('Informe nome e assinatura digital.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET signature_name = ?, signature_data = ?, signature_at = ?, signed_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (signature_name, signature_data, now, now, 'signed', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'signed', {'signature_name': signature_name})
    return updated


def upload_signed_contract_file(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    file_name = str(payload.get('file_name') or '').strip()
    file_mime = str(payload.get('file_mime') or 'application/pdf').strip()
    file_base64 = str(payload.get('file_base64') or '').strip()
    if not file_name or not file_base64:
        raise ValueError('Arquivo assinado inválido.')
    if file_mime not in ('application/pdf', 'application/octet-stream'):
        raise ValueError('Formato inválido. Utilize PDF.')
    raw = base64.b64decode(file_base64.encode('ascii'), validate=True)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('Arquivo excede 10MB.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET signed_pdf_base64 = ?, signed_file_name = ?, signed_file_mime = ?, signed_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (file_base64, file_name, file_mime, now, 'signed', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'uploaded_signed_file', {'file_name': file_name})
    return updated


def send_commercial_contract_email(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    email_to = str(payload.get('email_to') or '').strip().lower()
    subject = str(payload.get('subject') or '').strip() or 'Contrato comercial EPI Controle'
    body = str(payload.get('body') or '').strip() or 'Segue contrato comercial para análise e assinatura.'
    if not email_to:
        raise ValueError('E-mail do destinatário é obrigatório.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET last_email_to = ?, last_email_subject = ?, last_email_body = ?, last_email_sent_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (email_to, subject, body, now, 'sent', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'email_sent', {'email_to': email_to, 'subject': subject})
    return updated


def build_commercial_contract_pdf(connection, actor, company_id):
    ensure_company_access(actor, company_id)
    company = connection.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
    if not company:
        raise ValueError('Empresa nao encontrada.')
    company = row_to_dict(company)
    company['user_count'] = count_company_users(connection, company_id)
    settings = get_commercial_settings(connection)
    metrics = compute_company_contract_metrics(company, settings)
    brand = get_platform_brand(connection)
    logo_image = extract_pdf_logo_image(brand.get('logo_type'))
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    today = datetime.now()
    monthly_value = f"R$ {float(metrics['calculated_monthly_value'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    projected_value = f"R$ {float(metrics['projected_monthly_value'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    unit_price = f"R$ {float(metrics['unit_price'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    pages = []
    page_lines = []
    y = 792

    def add_line(text_value, size=12, bold=False, x=52, gap=18):
        nonlocal y, page_lines
        if y < 70:
            pages.append(page_lines)
            page_lines = []
            y = 792
        page_lines.append({'text': text_value, 'size': size, 'bold': bold, 'x': x, 'y': y})
        y -= gap

    add_line(brand.get('display_name') or 'Sua Empresa', size=22, bold=True, x=52, gap=28)
    if brand.get('legal_name'):
        add_line(brand['legal_name'], size=11, x=52, gap=16)
    if brand.get('cnpj'):
        add_line(f"CNPJ: {brand['cnpj']}", size=11, x=52, gap=20)
    add_line('Contrato Comercial de Licenca do Sistema', size=18, bold=True, x=52, gap=24)
    add_line(f"Gerado em {today.strftime('%d/%m/%Y %H:%M')}", size=10, x=52, gap=22)
    add_line(f"Numero do contrato: {contract.get('contract_number') or '-'}", size=11, x=52, gap=16)
    add_line(f"Data de emissao: {contract.get('issue_date') or today.strftime('%Y-%m-%d')}", size=11, x=52, gap=20)
    add_line('Empresa contratante', size=14, bold=True, x=52, gap=20)
    add_line(contract.get('contractor_name') or company['name'], size=12, bold=True, x=52, gap=18)
    add_line(f"Razao social: {contract.get('contractor_legal_name') or company.get('legal_name') or '-'}")
    add_line(f"CNPJ: {contract.get('contractor_cnpj') or company.get('cnpj') or '-'}")
    add_line(f"Endereco: {contract.get('contractor_address') or '-'}")
    add_line(f"Representante: {contract.get('contractor_representative') or '-'}")
    add_line(f"Cargo: {contract.get('contractor_representative_role') or '-'}")
    add_line(f"E-mail: {contract.get('contractor_email') or '-'}")
    add_line(f"Telefone: {contract.get('contractor_phone') or '-'}")
    add_line(f"Testemunha 1: {contract.get('contractor_witness_1') or '-'}")
    add_line(f"Testemunha 2: {contract.get('contractor_witness_2') or '-'}")
    add_line('Empresa contratada', size=14, bold=True, x=52, gap=20)
    add_line(contract.get('provider_name') or brand.get('display_name') or 'Sua Empresa', size=12, bold=True, x=52, gap=18)
    add_line(f"Razao social: {contract.get('provider_legal_name') or brand.get('legal_name') or '-'}")
    add_line(f"CNPJ: {contract.get('provider_cnpj') or brand.get('cnpj') or '-'}")
    add_line(f"Endereco: {contract.get('provider_address') or '-'}")
    add_line(f"Representante: {contract.get('provider_representative') or '-'}")
    add_line(f"Cargo: {contract.get('provider_representative_role') or '-'}")
    add_line(f"E-mail: {contract.get('provider_email') or '-'}")
    add_line(f"Telefone: {contract.get('provider_phone') or '-'}")
    add_line(f"Testemunhas: {contract.get('provider_witnesses') or '-'}")
    add_line('Dados comerciais', size=14, bold=True, x=52, gap=20)
    add_line(f"Plano contratado: {company.get('plan_name') or '-'}")
    add_line(f"Usuarios ativos: {company.get('user_count') or 0}")
    add_line(f"Limite de usuarios ativos: {company.get('user_limit') or 0}")
    add_line(f"Valor unitario: {unit_price}")
    add_line(f"Valor mensal atual: {monthly_value}")
    add_line(f"Valor projetado pelo limite contratado: {projected_value}")
    add_line(f"Status da licenca: {company_license_label(company.get('license_status'))}")
    add_line(f"Status da empresa: {'Ativa' if int(company.get('active') or 0) == 1 else 'Inativa'}")
    add_line(f"Aditivo contratual: {'Sim' if int(company.get('addendum_enabled') or 0) == 1 else 'Nao'}")
    add_line(f"Inicio do contrato: {contract.get('start_date') or company.get('contract_start') or '-'}")
    add_line(f"Fim do contrato: {contract.get('end_date') or company.get('contract_end') or '-'}")
    add_line('Observacoes comerciais', size=14, bold=True, x=52, gap=20)
    notes = contract.get('notes') or company.get('commercial_notes') or 'Sem observacoes comerciais registradas.'
    for wrapped in textwrap.wrap(notes, width=82):
        add_line(wrapped, size=11, x=52, gap=16)
    add_line('Clausulas editaveis do contrato', size=14, bold=True, x=52, gap=20)
    clauses_text = str(contract.get('clauses_text') or '').strip() or DEFAULT_SAAS_CONTRACT_CLAUSES
    clauses = [line.strip() for line in clauses_text.splitlines() if line.strip()]
    for clause in clauses:
        for wrapped in textwrap.wrap(clause, width=82):
            add_line(wrapped, size=11, x=52, gap=16)
    add_line('Assinatura digital', size=14, bold=True, x=52, gap=20)
    add_line(f"Nome: {contract.get('signature_name') or '-'}")
    add_line(f"Hash/codigo: {contract.get('signature_data') or '-'}")
    add_line(f"Data assinatura: {contract.get('signature_at') or contract.get('signed_at') or '-'}")
    add_line('Envio por e-mail', size=14, bold=True, x=52, gap=20)
    add_line(f"Destinatario: {contract.get('last_email_to') or '-'}")
    add_line(f"Assunto: {contract.get('last_email_subject') or '-'}")
    email_body = str(contract.get('last_email_body') or '-')
    for wrapped in textwrap.wrap(email_body, width=82):
        add_line(wrapped, size=11, x=52, gap=16)
    add_line('Assinaturas', size=14, bold=True, x=52, gap=22)
    add_line(f"Contratada: {contract.get('provider_name') or brand.get('display_name') or 'Sua Empresa'}", size=11, x=52, gap=40)
    add_line(f"Contratante: {contract.get('contractor_name') or company['name']}", size=11, x=52, gap=40)
    pages.append(page_lines)
    return build_pdf_document(pages, logo_image)
