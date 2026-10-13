"""Tenant-authoritative document operations. UI is never an authorization boundary."""
import base64
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.auth import require_structural_admin
from core.repository import require_actor, resolve_unit_scope, get_unit_active_jv_name
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import get_epi_effective_jv_name, is_epi_visible_for_unit
from modules.epis.service import fetch_epis
from .preview import MAX_FILE_BYTES, render_preview

CATEGORIES = {
    'epi_matrix': 'Matriz de Aplicação de EPIs', 'glove_matrix': 'Matriz de Seleção de Luvas',
    'care_guides': 'Guias de Higienização e Conservação', 'use_instructions': 'Instruções de Uso dos EPIs',
    'technical_manuals': 'Manuais e Fichas Técnicas', 'other_sst': 'Outros Documentos de SST',
}
PUBLIC_FIELDS = ('id','document_id','revision','version_label','title','category','effective_date','all_units','unit_ids','sectors','activities','epi_ids','state','created_at')
VERSION_READ_COLUMNS = (*PUBLIC_FIELDS, 'company_id', 'manifest')


def now():
    return datetime.now(timezone.utc).isoformat()


def audit(connection, context, action, *, decision='allow', document_id=None, version_id=None, details=None):
    connection.execute('''INSERT INTO safety_document_audit
        (company_id,actor_user_id,employee_id,unit_id,document_id,version_id,action,decision,details,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)''', (
        int(context['company_id']), context.get('actor_user_id'), context.get('employee_id'),
        context.get('unit_id'), document_id, version_id, action, decision,
        json.dumps(details or {}, ensure_ascii=False), now(),
    ))


def manager(connection, actor_id):
    actor = require_actor(connection, actor_id)
    require_structural_admin(actor)
    if not actor.get('company_id'):
        raise PermissionError('Administrador sem empresa efetiva.')
    actor['actor_user_id'] = actor['id']
    return actor


def _lock_company(connection, company_id):
    # New documents and idempotency serialize by tenant; no race allocating revisions.
    lock = '' if connection.__class__.__module__.startswith('sqlite3') else ' FOR UPDATE'
    connection.execute('SELECT id FROM companies WHERE id=?' + lock, (company_id,)).fetchone()


def _array(value, *, numeric=False):
    if not isinstance(value, list) or len(value) > 200:
        raise ValueError('Associações devem ser listas com no máximo 200 entradas.')
    if numeric:
        if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in value):
            raise ValueError('Identificador inválido.')
        return sorted(set(value))
    if any(not isinstance(v, str) or not v.strip() or len(v.strip()) > 180 for v in value):
        raise ValueError('Setor ou atividade inválido.')
    return sorted({v.strip() for v in value})


def validate_metadata(connection, actor, data):
    result = {}
    for key, limit in (('title',240),('version_label',80),('effective_date',10)):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            raise ValueError(f'Campo {key} inválido.')
        result[key] = value.strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['effective_date']):
        raise ValueError('Data de vigência deve usar AAAA-MM-DD.')
    date.fromisoformat(result['effective_date'])
    result['category'] = data.get('category')
    if result['category'] not in CATEGORIES:
        raise ValueError('Categoria inválida.')
    if type(data.get('all_units')) is not bool:
        raise ValueError('Defina explicitamente o alcance de unidades.')
    result['all_units'] = int(data['all_units'])
    for key in ('unit_ids','epi_ids','sectors','activities'):
        result[key] = _array(data.get(key, []), numeric=key in ('unit_ids','epi_ids'))
    if result['all_units'] and result['unit_ids']:
        raise ValueError('Escolha todas as unidades ou unidades específicas.')
    if not result['all_units'] and not result['unit_ids']:
        raise ValueError('Informe pelo menos uma unidade.')
    for unit_id in result['unit_ids']:
        resolve_unit_scope(connection, actor, unit_id)
    for epi_id in result['epi_ids']:
        row = connection.execute('SELECT company_id FROM epis WHERE id=?', (epi_id,)).fetchone()
        if not row or int(row['company_id']) != int(actor['company_id']):
            raise PermissionError('EPI fora do escopo da empresa.')
    return result


def dto(version):
    result = {key: version[key] for key in PUBLIC_FIELDS}
    for key in ('unit_ids','epi_ids','sectors','activities'):
        result[key] = json.loads(result[key])
    result['all_units'] = bool(result['all_units'])
    result['category_label'] = CATEGORIES[result['category']]
    result['state_label'] = {'draft':'Rascunho','published':'Publicado','superseded':'Substituído','archived':'Arquivado'}[result['state']]
    return result


def upload(connection, actor_id, data):
    actor = manager(connection, actor_id)
    request_company_id = int(actor['company_id'])
    metadata = validate_metadata(connection, actor, data)
    key = str(data.get('idempotency_key') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
        raise ValueError('Chave de idempotência inválida.')
    filename = str(data.get('filename') or '')
    if len(filename) > 240 or not filename or filename != Path(filename).name or '\\' in filename or any(ord(c)<32 for c in filename):
        raise ValueError('Nome de arquivo inválido.')
    encoded = data.get('content_base64')
    if not isinstance(encoded, str) or len(encoded) > ((MAX_FILE_BYTES + 2)//3)*4:
        raise ValueError('Arquivo ausente ou maior que 20 MiB.')
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError('Conteúdo base64 inválido.') from None
    mime = str(data.get('mime') or '')
    document_id = data.get('document_id')
    if document_id is not None and (type(document_id) is not int or document_id<=0):
        raise ValueError('Documento inválido.')
    if document_id is not None:
        own_document(connection, actor, document_id)
    digest = hashlib.sha256(content).hexdigest()
    fingerprint = hashlib.sha256(json.dumps([metadata,digest,filename,mime,document_id], sort_keys=True).encode()).hexdigest()
    existing = connection.execute('SELECT * FROM safety_document_versions WHERE company_id=? AND idempotency_key=?', (actor['company_id'],key)).fetchone()
    if existing:
        if existing['request_fingerprint'] != fingerprint:
            raise ValueError('Chave de idempotência reutilizada com conteúdo diferente.')
        return dto(row_to_dict(existing))
    # Release any read transaction before slow conversion. Re-authorize afterwards.
    connection.commit()
    manifest, pages = render_preview(content, filename, mime)
    actor = manager(connection, actor_id)
    if int(actor['company_id']) != request_company_id:
        raise PermissionError('Escopo do administrador alterado durante o envio. Reinicie a operação.')
    metadata = validate_metadata(connection, actor, data)
    _lock_company(connection, actor['company_id'])
    existing = connection.execute('SELECT * FROM safety_document_versions WHERE company_id=? AND idempotency_key=?', (actor['company_id'],key)).fetchone()
    if existing:
        if existing['request_fingerprint'] != fingerprint:
            raise ValueError('Chave de idempotência reutilizada com conteúdo diferente.')
        return dto(row_to_dict(existing))
    created_at = now()
    if document_id is None:
        document_id = connection.execute('INSERT INTO safety_documents(company_id,created_at,created_by) VALUES(?,?,?)', (actor['company_id'],created_at,actor_id)).lastrowid
    else:
        doc = own_document(connection, actor, document_id)
        if doc['archived']:
            raise ValueError('Documento arquivado; crie um novo documento.')
    revision = connection.execute('SELECT COALESCE(MAX(revision),0)+1 AS n FROM safety_document_versions WHERE document_id=?', (document_id,)).fetchone()['n']
    fields = ['document_id','company_id','revision',*metadata.keys(),'original_filename','original_mime','original_size','original_sha256','original_content','manifest','idempotency_key','request_fingerprint','created_at','created_by']
    values = [document_id,actor['company_id'],revision,*[json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for v in metadata.values()],filename,mime,len(content),digest,content,json.dumps(manifest),key,fingerprint,created_at,actor_id]
    version_id = connection.execute('INSERT INTO safety_document_versions('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')', values).lastrowid
    for part,page,bytes_ in pages:
        connection.execute('INSERT INTO safety_preview_pages(version_id,company_id,part_index,page_index,content) VALUES(?,?,?,?,?)', (version_id,actor['company_id'],part,page,bytes_))
    audit(connection,actor,'upload_version',document_id=document_id,version_id=version_id,details={'sha256':digest,'revision':revision})
    return dto(row_to_dict(connection.execute('SELECT * FROM safety_document_versions WHERE id=?', (version_id,)).fetchone()))


def own_document(connection, context, document_id):
    row = connection.execute('SELECT * FROM safety_documents WHERE id=? AND company_id=?', (document_id,context['company_id'])).fetchone()
    if not row:
        raise PermissionError('Documento indisponível neste escopo.')
    return row_to_dict(row)


def change_state(connection, actor_id, document_id, version_id, action, justification):
    actor = manager(connection,actor_id)
    if not isinstance(justification,str) or not justification.strip() or len(justification)>2000:
        raise ValueError('Justificativa obrigatória (até 2000 caracteres).')
    _lock_company(connection,actor['company_id'])
    doc = own_document(connection,actor,document_id)
    if action == 'publish':
        version = connection.execute('SELECT * FROM safety_document_versions WHERE id=? AND document_id=? AND company_id=?', (version_id,document_id,actor['company_id'])).fetchone()
        if not version or doc['archived'] or version['state'] not in ('draft','published'):
            raise ValueError('Versão não pode ser publicada.')
        if doc['published_version_id'] == version_id:
            return
        if doc['published_version_id']:
            connection.execute("UPDATE safety_document_versions SET state='superseded' WHERE id=?", (doc['published_version_id'],))
        connection.execute("UPDATE safety_document_versions SET state='published' WHERE id=?", (version_id,))
        connection.execute('UPDATE safety_documents SET published_version_id=? WHERE id=?', (version_id,document_id))
    elif action == 'archive':
        if doc['archived']:
            return
        connection.execute("UPDATE safety_document_versions SET state='archived' WHERE document_id=? AND state<>'archived'", (document_id,))
        connection.execute('UPDATE safety_documents SET archived=1,published_version_id=NULL WHERE id=?', (document_id,))
    else:
        raise ValueError('Ação inválida.')
    audit(connection,actor,action,document_id=document_id,version_id=version_id if action=='publish' else None,details={'justification':justification.strip()})


def employee_can_view(connection, context, version):
    if int(version['company_id']) != int(context['company_id']):
        return False
    row = connection.execute('SELECT timezone FROM companies WHERE id=?', (context['company_id'],)).fetchone()
    try:
        today = datetime.now(ZoneInfo(str(row['timezone'] or 'America/Sao_Paulo'))).date().isoformat()
    except ZoneInfoNotFoundError:
        return False  # Invalid tenant calendar must not publish early.
    if version['state'] != 'published' or version['effective_date'] > today:
        return False
    if not int(version['all_units']) and int(context['unit_id']) not in json.loads(version['unit_ids']):
        return False
    for key,field in (('sectors','sector'),('activities','role_name')):
        allowed = json.loads(version[key])
        if allowed and str(context.get(field) or '').casefold() not in {v.casefold() for v in allowed}:
            return False
    return True


def visible_version(connection, context, document_id, version_id=None):
    columns = ','.join('v.'+key for key in VERSION_READ_COLUMNS)
    row = connection.execute(f'''SELECT {columns} FROM safety_documents d JOIN safety_document_versions v ON v.id=d.published_version_id
        WHERE d.id=? AND d.archived=0''', (document_id,)).fetchone()
    if not row or not employee_can_view(connection,context,row) or (version_id is not None and row['id'] != version_id):
        raise PermissionError('Documento indisponível neste escopo.')
    return row_to_dict(row)


def list_documents(connection, context, *, administrative=False):
    if administrative:
        require_structural_admin(context)
        rows = connection.execute('SELECT '+','.join(VERSION_READ_COLUMNS)+' FROM safety_document_versions WHERE company_id=? ORDER BY document_id,revision DESC', (context['company_id'],)).fetchall()
    else:
        rows = connection.execute('SELECT '+','.join('v.'+key for key in VERSION_READ_COLUMNS)+''' FROM safety_documents d JOIN safety_document_versions v ON v.id=d.published_version_id
            WHERE d.company_id=? AND d.archived=0 ORDER BY v.title''', (context['company_id'],)).fetchall()
        rows = [r for r in rows if employee_can_view(connection,context,r)]
    items = [dto(row_to_dict(r)) for r in rows]
    if not administrative:
        # Related catalogue IDs are metadata, not a bypass of catalogue unit visibility.
        ids = {e['id'] for e in approved_epis(connection,context)}
        for item in items:
            item['epi_ids'] = [i for i in item['epi_ids'] if i in ids]
    return items


def approved_epis(connection, context):
    fields = ('id','name','manufacturer','model_reference','ca','ca_expiry','manufacturer_validity_months','sector','epi_section','manufacturer_recommendations')
    unit = int(context['unit_id'])
    jv = get_unit_active_jv_name(connection,unit)
    items = []
    for epi in fetch_epis(connection,actor={'role':'employee','company_id':context['company_id']}):
        if int(epi.get('active') or 0) != 1 or not is_epi_visible_for_unit(
            epi_unit_id=epi.get('unit_id'), epi_joint_venture_name=get_epi_effective_jv_name(epi,lambda uid:get_unit_active_jv_name(connection,uid)),
            target_unit_id=unit,target_unit_joint_venture_name=jv,
        ):
            continue
        item = {key:epi.get(key) for key in fields}
        if not item['manufacturer_validity_months']:
            item['manufacturer_validity_months'] = None
        item['has_photo'] = bool(epi.get('epi_photo_data'))
        items.append(item)
    return items


def original_allowed(actor, policy):
    return actor.get('role') in ('general_admin','registry_admin') and bool(policy)


def get_policy(connection, company_id):
    row = connection.execute('SELECT allow_admin_original_download FROM safety_document_policy WHERE company_id=?', (company_id,)).fetchone()
    return bool(row and row[0])


def download_original(connection, actor_id, version_id):
    actor = require_actor(connection,actor_id)
    actor['actor_user_id'] = actor_id
    if not original_allowed(actor,get_policy(connection,actor.get('company_id'))):
        raise PermissionError('Download de original não autorizado.')
    version = connection.execute('SELECT * FROM safety_document_versions WHERE id=? AND company_id=?', (version_id,actor['company_id'])).fetchone()
    if not version:
        raise PermissionError('Documento indisponível neste escopo.')
    audit(connection,actor,'download_original',document_id=version['document_id'],version_id=version_id)
    return bytes(version['original_content']),version['original_mime'],version['original_filename']


def photo(connection, context, epi_id):
    if epi_id not in {e['id'] for e in approved_epis(connection,context)}:
        raise PermissionError('EPI indisponível neste escopo.')
    row = connection.execute('SELECT epi_photo_data FROM epis WHERE id=? AND company_id=?', (epi_id,context['company_id'])).fetchone()
    raw = str(row['epi_photo_data'] or '')
    if not re.match(r'^data:image/(png|jpeg|jpg);base64,',raw) or len(raw)>8*1024**2:
        raise ValueError('Foto indisponível em formato seguro.')
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 8_000_000
    with Image.open(io.BytesIO(base64.b64decode(raw.split(',',1)[1],validate=True))) as image:
        image.load()
        if image.width*image.height>8_000_000:
            raise ValueError('Foto excede limite de pixels.')
        output=io.BytesIO()
        oriented = ImageOps.exif_transpose(image)
        matte = Image.new('RGBA', oriented.size, 'white')
        matte.alpha_composite(oriented.convert('RGBA'))
        sanitized = matte.convert('RGB')
        sanitized.info.clear()
        sanitized.save(output,format='PNG')
        return output.getvalue()
