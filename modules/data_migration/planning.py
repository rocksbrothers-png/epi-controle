"""One tenant-scoped identity/action plan shared by preview and execution."""
from __future__ import annotations

import hashlib
import json
import re

from modules.data_migration.preview import build_preview


def identity_fields(descriptor):
    if descriptor.key == 'epis':
        return ('purchase_code', 'ca')  # name is descriptive, NOT UNIQUE in PostgreSQL.
    return descriptor.natural_keys


def identity_key(field, value):
    value = str(value if value is not None else '').strip()
    if field in ('cpf', 'cnpj', 'ca'):
        value = re.sub(r'\D', '', value)
    return f'{field}:{value}' if value else ''


def _composite_key(descriptor, record):
    """Chave ÚNICA combinando todas as `natural_keys` — para o caso em que elas
    formam uma chave COMPOSTA (estoque: unidade+EPI), não identificadores
    alternativos. Vazia se faltar qualquer componente."""
    parts = [identity_key(field, record.get(field)) for field in identity_fields(descriptor)]
    return '&'.join(parts) if all(parts) else ''


def add_identity(index, descriptor, record):
    if getattr(descriptor, 'composite_natural_key', False):
        key = _composite_key(descriptor, record)
        if key:
            rows = index.setdefault(key, [])
            rows[:] = [r for r in rows if r['id'] != record['id']]
            rows.append(record)
        return
    for field in identity_fields(descriptor):
        key = identity_key(field, record.get(field))
        if key:
            rows = index.setdefault(key, [])
            rows[:] = [r for r in rows if r['id'] != record['id']]
            rows.append(record)


def identify(index, descriptor, record):
    if getattr(descriptor, 'composite_natural_key', False):
        key = _composite_key(descriptor, record)
        if not key:
            # Falta um componente da chave composta: tratado como novo. Os
            # campos obrigatórios da chave são exigidos pelo preview antes de
            # qualquer gravação.
            return None, ''
        matches = index.get(key, [])
        if len(matches) > 1:
            return None, 'Os identificadores correspondem a registros distintos ou ambíguos.'
        return next(iter(matches), None), ''
    candidates = {}
    for field in identity_fields(descriptor):
        for candidate in index.get(identity_key(field, record.get(field)), []):
            candidates[candidate['id']] = candidate
    if len(candidates) > 1:
        return None, 'Os identificadores correspondem a registros distintos ou ambíguos.'
    current = next(iter(candidates.values()), None)
    if current:
        for field in identity_fields(descriptor):
            supplied = identity_key(field, record.get(field))
            stored = identity_key(field, current.get(field))
            if supplied and stored and supplied != stored:
                return None, 'Identificadores conflitantes; corrija o cadastro pela operação de domínio.'
    return current, ''


def action_for(strategy, current):
    if current:
        return 'skip' if strategy in ('insert_only', 'skip_duplicates') else 'update'
    return 'skip' if strategy == 'update_only' else 'insert'


def make_plan(descriptor, records, existing, strategy):
    preview = build_preview(descriptor, records, existing_keys=existing.keys())
    virtual = {key: list(value) for key, value in existing.items()}
    invalid = {d['row'] for d in preview['diagnostics'] if d['level'] == 'error'}
    classifications = []
    seen = set()
    for number, record in enumerate(records, 1):
        current, conflict = identify(virtual, descriptor, record)
        if conflict:
            preview['diagnostics'].append({'code': 'identity_conflict', 'row': number,
                'field': ','.join(identity_fields(descriptor)), 'message': conflict,
                'entity': descriptor.key, 'severity': 'error', 'level': 'error'})
            invalid.add(number)
        keys = [identity_key(field, record.get(field)) for field in identity_fields(descriptor)]
        duplicate = any(key and key in seen for key in keys)
        known = current is not None or record.get('__already_imported__', False)
        action = 'reject' if number in invalid else (
            'skip' if record.get('__already_imported__') else action_for(strategy, current))
        classifications.append({'row': number, 'source_line': record.get('__source_line__', number),
            'classification': 'invalid' if action == 'reject' else ('duplicate' if duplicate else ('existing' if known else 'new')),
            'action': action, 'target_id': current['id'] if current and current['id'] > 0 else None,
            'reason': 'identity_conflict' if conflict else ('validation_error' if action == 'reject' else
                      ('already_imported' if record.get('__already_imported__') else action)),
            'version': current.get('__version__') if current else None})
        if action != 'reject':
            seen.update(key for key in keys if key)
            if action in ('insert', 'update'):
                add_identity(virtual, descriptor, {**(current or {}), **record,
                             'id': current['id'] if current else -number})
    preview.update(total_rows=len(records), valid_rows=len(records)-len(invalid), invalid_rows=len(invalid),
        will_insert=sum(r['action']=='insert' for r in classifications),
        will_update=sum(r['action']=='update' for r in classifications),
        will_skip=sum(r['action']=='skip' for r in classifications), will_reject=len(invalid),
        new_rows=sum(r['classification']=='new' for r in classifications),
        existing_rows=sum(r['classification']=='existing' for r in classifications),
        duplicate_rows=sum(r['classification']=='duplicate' for r in classifications),
        row_classifications=classifications, blocking=bool(invalid), strategy=strategy,
        sample=[{k:v for k,v in r.items() if not k.startswith('__')} for r in records[:10]])
    return preview


def plan_token(company_id, entity, raw_hash, mapping, strategy, records, preview):
    content = [int(company_id), entity, raw_hash, mapping, strategy, records, preview['row_classifications']]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
