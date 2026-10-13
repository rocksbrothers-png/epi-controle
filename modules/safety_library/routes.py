"""Authenticated per-access previews. No original endpoint on employee surface."""
from contextlib import closing
import json
import os
from urllib.parse import urlparse

from core.database import get_connection
from core.repository import require_actor
from core.security import require_bearer_actor
from epi_backend.db import row_to_dict
from epi_backend.http_utils import send_json, structured_log
from modules.portal.service import resolve_external_employee_context, EmployeePortalAccessDenied
from . import service


def secure_response(handler):
    # app.py sets these headers once, including errors. Reset at every response.
    handler.safety_library_response = True


def send_private_bytes(handler, content, mime, *, filename=None):
    handler.send_response(200)
    handler.send_header('Content-Type', mime)
    handler.send_header('Content-Length', str(len(content)))
    if filename:
        from urllib.parse import quote
        handler.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(filename, safe=''))
    else:
        handler.send_header('Content-Disposition', 'inline')
    handler.end_headers()
    handler.wfile.write(content)


def _origin(handler):
    origin = str(handler.headers.get('Origin') or '')
    if not origin:
        return  # Native clients still require credentials and context.
    allowed = {v.strip() for v in os.environ.get('CORS_ALLOW_ORIGIN','').split(',') if v.strip() and v.strip()!='*'}
    # Same origin works without additional configuration. Cross origin is explicit.
    if urlparse(origin).netloc == handler.headers.get('Host','') or origin in allowed:
        return
    raise PermissionError('Origem não autorizada para a biblioteca.')


def employee_context(connection, handler, payload):
    context = resolve_external_employee_context(connection,payload.get('token'),cpf_last3=payload.get('cpf_last3'),ip_address=str(handler.client_address[0]),user_agent=handler.headers.get('User-Agent',''))
    # Authoritative tenant and CURRENT operational unit, never caller overrides.
    employee = connection.execute('SELECT * FROM employees WHERE id=? AND company_id=?', (context['employee_id'],context['company_id'])).fetchone()
    if not employee or row_to_dict(employee).get('status') != 'active':
        raise PermissionError('Colaborador indisponível.')
    from datetime import date
    today = date.today().isoformat()
    movement = connection.execute("SELECT target_unit_id FROM employee_unit_movements WHERE employee_id=? AND movement_type='temporary' AND start_date<=? AND COALESCE(NULLIF(end_date,''),'9999-12-31')>=? ORDER BY start_date DESC,id DESC LIMIT 1", (context['employee_id'],today,today)).fetchone()
    context['unit_id'] = movement['target_unit_id'] if movement else employee['unit_id']
    unit = connection.execute("SELECT id,name FROM units WHERE id=? AND company_id=? AND status='active'", (context['unit_id'],context['company_id'])).fetchone()
    company = connection.execute('SELECT active FROM companies WHERE id=?', (context['company_id'],)).fetchone()
    if not unit or not company or not int(company['active']):
        raise PermissionError('Empresa ou unidade indisponível.')
    context['unit_name'] = unit['name']
    context['sector'],context['role_name'] = employee['sector'],employee['role_name']
    return context


def handle(handler, parsed, payload, match):
    secure_response(handler)
    administrative = parsed.path.startswith('/api/safety-library/')
    if not isinstance(payload,dict):
        return send_json(handler,400,{'error':'Corpo JSON inválido.'})
    context = None
    actor_id = None
    with closing(get_connection()) as connection:
        if administrative:
            actor_id = require_bearer_actor(handler,parsed,payload)
        try:
            _origin(handler)
            if administrative:
                context = require_actor(connection,actor_id)
                context['actor_user_id'] = actor_id
                context = service.manager(connection,actor_id)
            else:
                context = employee_context(connection,handler,payload)
            action = match.group('action')
            if action == 'approved-epis' and not administrative:
                result = {'items':service.approved_epis(connection,context)}
            elif action == 'documents':
                result = {'items':service.list_documents(connection,context,administrative=administrative),'categories':service.CATEGORIES}
            elif action == 'options' and administrative:
                units = connection.execute('SELECT id,name FROM units WHERE company_id=? ORDER BY name', (context['company_id'],)).fetchall()
                epis = service.fetch_epis(connection,actor=context)
                result = {'units':[row_to_dict(r) for r in units],'epis':[{'id':e['id'],'name':e['name']} for e in epis],'categories':service.CATEGORIES,'allow_admin_original_download':service.get_policy(connection,context['company_id'])}
            elif action == 'upload' and administrative:
                result = {'version':service.upload(connection,actor_id,payload)}
            elif action in ('publish','archive') and administrative:
                service.change_state(connection,actor_id,_id(payload,'document_id'),_id(payload,'version_id') if action=='publish' else None,action,payload.get('justification'))
                result = {'ok':True}
            elif action == 'policy' and administrative:
                if type(payload.get('allow_admin_original_download')) is not bool or not str(payload.get('justification') or '').strip():
                    raise ValueError('Política e justificativa obrigatórias.')
                service._lock_company(connection,context['company_id'])
                connection.execute('''INSERT INTO safety_document_policy(company_id,allow_admin_original_download) VALUES(?,?)
                    ON CONFLICT(company_id) DO UPDATE SET allow_admin_original_download=excluded.allow_admin_original_download''', (context['company_id'],int(payload['allow_admin_original_download'])))
                service.audit(connection,context,'policy_change',details={'allowed':payload['allow_admin_original_download'],'justification':str(payload['justification'])[:2000]})
                result = {'ok':True}
            elif action == 'history' and administrative:
                doc_id = _id(payload,'document_id')
                service.own_document(connection,context,doc_id)
                rows = connection.execute('SELECT id,action,decision,actor_user_id,employee_id,unit_id,version_id,details,created_at FROM safety_document_audit WHERE document_id=? AND company_id=? ORDER BY id', (doc_id,context['company_id'])).fetchall()
                result = {'items':[row_to_dict(r) for r in rows]}
            elif action in ('manifest','page'):
                doc_id = _id(payload,'document_id')
                if administrative:
                    service.own_document(connection,context,doc_id)
                    version = connection.execute('SELECT '+','.join(service.VERSION_READ_COLUMNS)+' FROM safety_document_versions WHERE id=? AND document_id=? AND company_id=?', (_id(payload,'version_id'),doc_id,context['company_id'])).fetchone()
                    if not version:
                        raise PermissionError('Documento indisponível neste escopo.')
                else:
                    version = service.visible_version(connection,context,doc_id,payload.get('version_id'))
                service.audit(connection,context,'view_'+action,document_id=doc_id,version_id=version['id'],details={'part':payload.get('part_index'),'page':payload.get('page_index')})
                if action == 'manifest':
                    document = service.dto(row_to_dict(version))
                    if not administrative:
                        allowed_epis = {e['id'] for e in service.approved_epis(connection,context)}
                        document['epi_ids'] = [i for i in document['epi_ids'] if i in allowed_epis]
                    result = {'document':document,'preview':json.loads(version['manifest'])}
                else:
                    part,page = _id(payload,'part_index',zero=True),_id(payload,'page_index',zero=True)
                    row = connection.execute('SELECT content FROM safety_preview_pages WHERE version_id=? AND company_id=? AND part_index=? AND page_index=?', (version['id'],context['company_id'],part,page)).fetchone()
                    if not row:
                        raise ValueError('Página indisponível.')
                    connection.commit()
                    return send_private_bytes(handler,bytes(row['content']),'image/png')
            elif action == 'photo' and not administrative:
                content = service.photo(connection,context,_id(payload,'epi_id'))
                service.audit(connection,context,'view_epi_photo',details={'epi_id':payload['epi_id']})
                connection.commit()
                return send_private_bytes(handler,content,'image/png')
            else:
                raise PermissionError('Operação não autorizada.')
            service.audit(connection,context,'library_'+action)
            if not administrative:
                result['context'] = {'unit_id':context['unit_id'],'unit_name':context['unit_name']}
            connection.commit()
            return send_json(handler,200,result)
        except (PermissionError,ValueError) as exc:
            # Preserve CPF attempts/blocking; resolver already audited denied factors.
            if isinstance(exc,EmployeePortalAccessDenied):
                context = exc.portal_context
            if context and context.get('company_id'):
                service.audit(connection,context,'request_denied',decision='deny',details={'path':parsed.path,'requested_document_id':payload.get('document_id'),'requested_version_id':payload.get('version_id'),'reason':exc.code if isinstance(exc,EmployeePortalAccessDenied) else type(exc).__name__})
            connection.commit()
            structured_log('warning','safety_library.denied',path=parsed.path,reason=type(exc).__name__,actor_user_id=actor_id,employee_id=(context or {}).get('employee_id'))
            return send_json(handler,403 if isinstance(exc,PermissionError) else 400,{'error':str(exc),'preview_available':False})


def _id(payload, key, zero=False):
    value = payload.get(key)
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError(f'{key} inválido.')
    return value


def original(handler,parsed,payload,match):
    secure_response(handler)
    with closing(get_connection()) as connection:
        actor_id = require_bearer_actor(handler,parsed,payload)
        try:
            _origin(handler)
            body,mime,filename = service.download_original(connection,actor_id,int(match.group('version')))
            connection.commit()
            return send_private_bytes(handler,body,mime,filename=filename)
        except PermissionError:
            actor = require_actor(connection,actor_id)
            if actor.get('company_id'):
                actor['actor_user_id']=actor_id
                service.audit(connection,actor,'original_denied',decision='deny',details={'requested_version_id':int(match.group('version'))})
                connection.commit()
            structured_log('warning','safety_library.original_denied',actor_user_id=actor_id,requested_version_id=int(match.group('version')))
            raise


def register_routes(router):
    router.register('POST',r'^/api/(?:safety-library|employee-library)/(?P<action>[a-z-]+)$',handle,regex=True)
    router.register('GET',r'^/api/safety-library/original/(?P<version>\d+)$',original,regex=True)
