"""Real HTTP + PostgreSQL + converter. Only explicitly isolated local DSNs.

Run with DATABASE_URL=PORTAL_DOCS_TEST_DSN=postgresql://.../portal_docs_* .
Never migrates a shared environment. Synthetic fixtures are generated locally.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse
import uuid
import zipfile

import pytest

DSN = os.environ.get('PORTAL_DOCS_TEST_DSN','')
pytestmark = pytest.mark.skipif(not DSN, reason='Requires explicitly isolated PORTAL_DOCS_TEST_DSN')


def png():
    from PIL import Image
    output=io.BytesIO()
    Image.new('RGB',(160,80),'navy').save(output,'PNG')
    return output.getvalue()


def pdf():
    import pymupdf
    doc=pymupdf.open()
    for text in ('Authorized safety document — page 1','Page 2 — preserve navigation'):
        page=doc.new_page();page.insert_text((72,72),text)
    result=doc.tobytes();doc.close();return result


def seed_tenant(connection, label):
    suffix=uuid.uuid4().hex
    def insert(table,**data):
        fields=','.join(data)
        return connection.execute(f'INSERT INTO {table}({fields}) VALUES({",".join("?" for _ in data)})',tuple(data.values())).lastrowid
    company=insert('companies',name=label+' '+suffix,cnpj=suffix,logo_type='DOF',contract_end='2099-12-31')
    units=[insert('units',company_id=company,name=label+f' unit {i}',unit_type='base',city='Test') for i in (1,2)]
    roles={}
    for role in ('general_admin','registry_admin','master_admin','admin','user','employee','buyer','approver','manager','safety_tech'):
        roles[role]=insert('users',company_id=company,username=suffix+'_'+role,password='isolated-fixture-only',full_name='Fixture '+role,role=role)
    employees=[];tokens=[]
    expires=(datetime.now(timezone.utc)+timedelta(days=5)).isoformat()
    from modules.portal.service import upsert_employee_portal_link
    for index,unit in enumerate(units):
        emp=insert('employees',company_id=company,unit_id=unit,employee_id_code=suffix+str(index),cpf='00000000123',name='Test employee '+str(index),sector='Deck',role_name='Technician',admission_date='2020-01-01',schedule_type='fixed')
        token=uuid.uuid4().hex+uuid.uuid4().hex
        upsert_employee_portal_link(connection,emp,company,token,token,expires,roles['general_admin'],datetime.now(timezone.utc).isoformat())
        employees.append(emp);tokens.append(token)
    epis=[]
    for index,unit in enumerate(units):
        epis.append(insert('epis',company_id=company,unit_id=unit,name='Approved helmet '+str(index),purchase_code=suffix+str(index),ca=suffix+str(index),sector='Head',epi_section='Deck',unit_measure='UN',ca_expiry='2028-01-09',epi_validity_date='2099-12-31',manufacture_date='',validity_days=0,manufacturer_validity_months=60,manufacturer='Fixture manufacturer',model_reference='Model',manufacturer_recommendations='Use correctly',epi_photo_data='data:image/png;base64,'+base64.b64encode(png()).decode(),scope_type='UNIT'))
    connection.commit()
    return {'company':company,'units':units,'users':roles,'employees':employees,'tokens':tokens,'epis':epis}


@pytest.fixture(scope='session')
def environment():
    target=urlparse(DSN)
    assert target.hostname in ('127.0.0.1','localhost')
    assert target.path.startswith('/portal_docs_') or target.path=='/epi_ci'
    assert os.environ.get('DATABASE_URL')==DSN, 'Test and application DSNs must match'
    from core.bootstrap import init_db
    init_db()
    import app
    from http.server import ThreadingHTTPServer
    app._set_bootstrap_state(ready=True,error_code='',error_message='')
    server=ThreadingHTTPServer(('127.0.0.1',0),app.EpiHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join(timeout=3)


@pytest.fixture
def tenants(environment):
    from core.database import get_connection
    with closing(get_connection()) as c:
        return seed_tenant(c,'A'),seed_tenant(c,'B')


def request(base,action,data=None,*,tenant=None,role='general_admin',employee=False,index=0,method='POST',origin=None):
    headers={'Content-Type':'application/json'}
    body=dict(data or {})
    if tenant is not None:
        if employee:
            body.update(token=tenant['tokens'][index],cpf_last3='123')
        else:
            from core.security import create_jwt_token
            headers['Authorization']='Bearer '+create_jwt_token({'id':tenant['users'][role],'company_id':tenant['company'],'role':role})
    if origin:headers['Origin']=origin
    path=action if action.startswith('/') else '/api/'+('employee' if employee else 'safety')+'-library/'+action
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if method=='POST' else None,headers=headers,method=method)
    try:res=urllib.request.urlopen(req,timeout=115)
    except urllib.error.HTTPError as exc:res=exc
    raw=res.read();mime=res.headers.get('Content-Type','')
    return res.status,json.loads(raw) if 'application/json' in mime else raw,dict(res.headers)


def upload_data(tenant,**overrides):
    result={'title':'Safety guidance','category':'care_guides','version_label':'1.0','effective_date':'2020-01-01','all_units':False,'unit_ids':[tenant['units'][0]],'epi_ids':[tenant['epis'][0]],'sectors':['Deck'],'activities':['Technician'],'filename':'guide.pdf','mime':'application/pdf','content_base64':base64.b64encode(pdf()).decode(),'idempotency_key':uuid.uuid4().hex}
    result.update(overrides);return result


def published(base,tenant,**overrides):
    status,result,_=request(base,'upload',upload_data(tenant,**overrides),tenant=tenant)
    assert status==200,result
    v=result['version']
    status,result,_=request(base,'publish',{'document_id':v['document_id'],'version_id':v['id'],'justification':'Approved isolated fixture'},tenant=tenant)
    assert status==200,result
    return v


@pytest.mark.parametrize('role',['general_admin','registry_admin','master_admin','admin','user','employee','buyer','approver','manager','safety_tech'])
def test_direct_http_rbac(environment,tenants,role):
    a,_=tenants
    code,data,_=request(environment,'upload',upload_data(a),tenant=a,role=role)
    assert code==(200 if role in ('general_admin','registry_admin') else 403),data
    for action in ('documents','options','history','publish','archive','policy'):
        code,_,_=request(environment,action,{},tenant=a,role=role)
        if role not in ('general_admin','registry_admin'):assert code==403


def test_preview_scope_publication_and_every_page_access(environment,tenants):
    a,b=tenants;v=published(environment,a)
    payload={'document_id':v['document_id'],'version_id':v['id']}
    status,result,headers=request(environment,'manifest',payload,tenant=a,employee=True)
    assert status==200 and len(result['preview']['parts'][0]['pages'])==2
    assert not any(key in json.dumps(result) for key in ('original_content','content_base64','original_filename','original_url','download_url'))
    status,body,headers=request(environment,'page',{**payload,'part_index':0,'page_index':0},tenant=a,employee=True)
    assert status==200 and body.startswith(b'\x89PNG') and body!=pdf()
    assert 'no-store' in headers['Cache-Control'] and headers['X-Frame-Options']=='DENY'
    assert headers['Content-Disposition']=='inline' and headers['Referrer-Policy']=='no-referrer'
    for other,index in ((b,0),(a,1)):
        for action in ('manifest','page'):
            status,_,_=request(environment,action,{**payload,'part_index':0,'page_index':0,'company_id':a['company'],'unit_id':a['units'][0]},tenant=other,employee=True,index=index)
            assert status==403
    status,_,_=request(environment,'page',{**payload,'part_index':0,'page_index':0},tenant=a,employee=True,origin='https://attacker.invalid')
    assert status==403
    status,_,_=request(environment,'archive',{'document_id':v['document_id'],'justification':'Retired'},tenant=a)
    assert status==200
    for action in ('manifest','page'):
        assert request(environment,action,{**payload,'part_index':0,'page_index':0},tenant=a,employee=True)[0]==403
    assert request(environment,'documents',tenant=a,employee=True)[1]['items']==[]


def test_drafts_future_scope_sector_activity_and_catalogue_not_stock(environment,tenants):
    a,b=tenants
    code,result,_=request(environment,'upload',upload_data(a),tenant=a);assert code==200
    assert request(environment,'documents',tenant=a,employee=True)[1]['items']==[]
    for overrides in ({'effective_date':'2099-01-01'},{'sectors':['Office']},{'activities':['Other']}):
        published(environment,a,**overrides)
    assert request(environment,'documents',tenant=a,employee=True)[1]['items']==[]
    code,result,_=request(environment,'approved-epis',tenant=a,employee=True)
    assert code==200
    assert [e['id'] for e in result['items']]==[a['epis'][0]]
    epi=result['items'][0]
    assert epi['ca_expiry']=='2028-01-09' and epi['manufacturer_validity_months']==60
    assert 'stock' not in epi and 'epi_validity_date' not in epi and 'physical_expiry_date' not in epi
    assert request(environment,'photo',{'epi_id':a['epis'][0]},tenant=a,employee=True)[1].startswith(b'\x89PNG')
    assert request(environment,'photo',{'epi_id':b['epis'][0]},tenant=a,employee=True)[0]==403


def test_employee_never_original_and_backend_policy(environment,tenants):
    a,b=tenants;v=published(environment,a)
    path=f"/api/safety-library/original/{v['id']}"
    assert request(environment,path,tenant=a,method='GET')[0]==403
    assert request(environment,'policy',{'allow_admin_original_download':True,'justification':'Administrative recovery'},tenant=a,role='registry_admin')[0]==200
    for role in ('employee','user','admin','master_admin','buyer','approver'):
        assert request(environment,path,tenant=a,role=role,method='GET')[0]==403
    for role in ('general_admin','registry_admin'):
        code,body,headers=request(environment,path,tenant=a,role=role,method='GET')
        assert code==200 and body.startswith(b'%PDF-') and headers['Content-Disposition'].startswith('attachment')
    assert request(environment,path,tenant=b,method='GET')[0]==403
    for action in ('upload','publish','archive','delete','export','original'):
        assert request(environment,action,{'document_id':v['document_id'],'version_id':v['id']},tenant=a,employee=True)[0]==403


def test_all_units_does_not_mean_other_companies(environment,tenants):
    a,b=tenants;v=published(environment,a,all_units=True,unit_ids=[])
    payload={'document_id':v['document_id'],'version_id':v['id']}
    assert request(environment,'manifest',payload,tenant=a,employee=True,index=1)[0]==200
    assert request(environment,'manifest',payload,tenant=b,employee=True)[0]==403
    assert request(environment,'page',{**payload,'part_index':0,'page_index':0},tenant=b,employee=True)[0]==403


def test_admin_scope_change_during_conversion_never_moves_upload_between_tenants(environment,tenants,monkeypatch):
    a,b=tenants
    from core.database import get_connection
    from modules.safety_library import service
    render=service.render_preview
    def move_scope_after_real_conversion(*args):
        result=render(*args)
        with closing(get_connection()) as c:
            c.execute('UPDATE users SET company_id=? WHERE id=?',(b['company'],a['users']['general_admin']));c.commit()
        return result
    monkeypatch.setattr(service,'render_preview',move_scope_after_real_conversion)
    code,_,_=request(environment,'upload',upload_data(a,all_units=True,unit_ids=[],epi_ids=[]),tenant=a)
    assert code==403
    with closing(get_connection()) as c:
        assert c.execute('SELECT COUNT(*) FROM safety_documents WHERE company_id IN (?,?)',(a['company'],b['company'])).fetchone()[0]==0


def test_replacement_idempotency_concurrency_and_history(environment,tenants):
    a,_=tenants;v=published(environment,a)
    payload=upload_data(a,document_id=v['document_id'],version_label='2.0')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:request(environment,'upload',payload,tenant=a),range(2)))
    assert all(r[0]==200 for r in results),results
    ids={r[1]['version']['id'] for r in results};assert len(ids)==1
    replacement=results[0][1]['version'];assert replacement['revision']==2
    assert request(environment,'manifest',{'document_id':v['document_id'],'version_id':v['id']},tenant=a,employee=True)[0]==200
    assert request(environment,'publish',{'document_id':v['document_id'],'version_id':replacement['id'],'justification':'Replace approved edition'},tenant=a)[0]==200
    assert request(environment,'manifest',{'document_id':v['document_id'],'version_id':v['id']},tenant=a,employee=True)[0]==403
    assert request(environment,'manifest',{'document_id':v['document_id'],'version_id':v['id']},tenant=a)[0]==200
    payload['title']='Changed request'
    assert request(environment,'upload',payload,tenant=a)[0]==400
    history=request(environment,'history',{'document_id':v['document_id']},tenant=a)[1]['items']
    assert sum(e['action']=='upload_version' for e in history)==2
    assert sum(e['action']=='publish' for e in history)==2


def test_malicious_uploads_mime_size_and_cross_scope(environment,tenants):
    a,b=tenants
    cases=[{'mime':'text/html'},{'filename':'../../escape.pdf'},{'content_base64':'@not-base64'},{'content_base64':base64.b64encode(b'<script>bad</script>').decode()}, {'unit_ids':[b['units'][0]]},{'epi_ids':[b['epis'][0]]},{'all_units':False,'unit_ids':[]}]
    for case in cases:assert request(environment,'upload',upload_data(a,**case),tenant=a)[0] in (400,403)
    import pymupdf
    active=pymupdf.open();page=active.new_page();page.insert_text((40,40),'Active PDF')
    xref=active.get_new_xref();active.update_object(xref,'<< /S /JavaScript /JS (app.alert(1)) >>')
    active.xref_set_key(active.pdf_catalog(),'OpenAction',f'{xref} 0 R');raw=active.tobytes();active.close()
    assert request(environment,'upload',upload_data(a,content_base64=base64.b64encode(raw).decode()),tenant=a)[0]==400
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>');z.writestr('word/document.xml','<doc/>');z.writestr('word/vbaProject.bin',b'hostile')
    assert request(environment,'upload',upload_data(a,filename='macro.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',content_base64=base64.b64encode(archive.getvalue()).decode()),tenant=a)[0]==400
    assert request(environment,'documents')[0]==401
    assert request(environment,'documents',{'actor_user_id':a['users']['registry_admin']},tenant=a)[0]==403


def test_migration_idempotency_private_rls_and_immutable_history(environment,tenants):
    a,_=tenants;v=published(environment,a)
    from core.database import get_connection
    from core.schema import run_pending_migrations
    migration=Path(__file__).resolve().parents[1]/'epi_backend/migrations/034_safety_library.py'
    spec=importlib.util.spec_from_file_location('library_migration',migration);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with closing(get_connection()) as c:
        before=bytes(c.execute('SELECT original_content FROM safety_document_versions WHERE id=?',(v['id'],)).fetchone()[0])
        module.run(c);module.run(c);run_pending_migrations(c)
        assert bytes(c.execute('SELECT original_content FROM safety_document_versions WHERE id=?',(v['id'],)).fetchone()[0])==before
        assert c.execute("SELECT COUNT(*) FROM app_migrations WHERE migration_id='034_safety_library' AND status='applied'").fetchone()[0]==1
        for statement in ('UPDATE safety_document_versions SET title=\'tampered\' WHERE id=?','DELETE FROM safety_document_versions WHERE id=?'):
            with pytest.raises(Exception):c.execute(statement,(v['id'],))
            c.rollback()

        for table in ('safety_preview_pages','safety_document_audit'):
            with pytest.raises(Exception):c.execute(f'DELETE FROM {table} WHERE company_id=?',(a['company'],))
            c.rollback()
        for role in ('anon','authenticated'):
            c.execute('SET LOCAL ROLE '+role)
            try:
                rows=c.execute('SELECT original_content FROM safety_document_versions').fetchall();assert not rows
            except __import__('psycopg2').errors.InsufficientPrivilege:c.rollback()
            c.rollback()


def test_current_unit_revocation_and_denial_audit(environment,tenants):
    a,b=tenants;v=published(environment,a)
    from core.database import get_connection
    with closing(get_connection()) as c:
        c.execute("INSERT INTO employee_unit_movements(company_id,employee_id,source_unit_id,target_unit_id,movement_type,start_date,end_date,actor_user_id,actor_name,created_at) VALUES(?,?,?,?,'temporary','2020-01-01','2099-01-01',?,'Fixture Admin',?)", (a['company'],a['employees'][0],a['units'][0],a['units'][1],a['users']['general_admin'],datetime.now(timezone.utc).isoformat()))
        c.commit()
    payload={'document_id':v['document_id'],'version_id':v['id']}
    assert request(environment,'manifest',payload,tenant=a,employee=True)[0]==403
    assert request(environment,'manifest',payload,tenant=b,employee=True)[0]==403
    with closing(get_connection()) as c:
        row=c.execute("SELECT company_id,employee_id,unit_id,details FROM safety_document_audit WHERE company_id=? AND decision='deny' ORDER BY id DESC LIMIT 1",(a['company'],)).fetchone()
        assert row['employee_id']==a['employees'][0] and row['unit_id']==a['units'][1]
        assert a['tokens'][0] not in row['details'] and 'cpf_last3' not in row['details']
        c.execute('UPDATE employee_portal_links SET active=0 WHERE employee_id=?',(a['employees'][0],));c.commit()
    assert request(environment,'documents',tenant=a,employee=True)[0]==403


@pytest.mark.parametrize('extension',['docx','xlsx','xls','png'])
def test_real_office_rendering_preserves_pages_sheets_merges_and_images(environment,tenants,extension):
    a,_=tenants
    from modules.safety_library.preview import MIMES
    output=io.BytesIO()
    if extension=='docx':
        from docx import Document
        doc=Document();doc.add_heading('Safety instructions',0);table=doc.add_table(rows=2,cols=2);table.style='Table Grid'
        table.cell(0,0).text='Merged title';table.cell(0,0).merge(table.cell(0,1));table.cell(1,0).text='Care';table.cell(1,1).text='Do not use solvents'
        doc.add_picture(io.BytesIO(png()));doc.add_page_break();doc.add_paragraph('Second page');doc.save(output)
    elif extension=='xlsx':
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image
        workbook=Workbook();workbook.active.title='POR';workbook.create_sheet('ENG')
        for sheet in workbook:
            sheet.merge_cells('A1:C1');sheet['A1']='Matrix heading';sheet['A2']='EPI';sheet['B2']='Activity';sheet['A3']='Gloves';sheet['B3']='Required';sheet.add_image(Image(io.BytesIO(png())),'A5');sheet.print_area='A1:D12'
        workbook.save(output)
    elif extension=='xls':
        import xlwt
        workbook=xlwt.Workbook();sheet=workbook.add_sheet('Glove matrix');sheet.write_merge(0,0,0,2,'Merged heading');sheet.write(1,0,'Gloves');sheet.write(1,1,'Mandatory');workbook.save(output)
    else:output.write(png())
    v=published(environment,a,filename='fixture.'+extension,mime=MIMES['.'+extension],content_base64=base64.b64encode(output.getvalue()).decode())
    code,data,_=request(environment,'manifest',{'document_id':v['document_id'],'version_id':v['id']},tenant=a,employee=True)
    assert code==200
    parts=data['preview']['parts']
    assert [p['name'] for p in parts]==({'docx':['Documento'],'xlsx':['POR','ENG'],'xls':['Glove matrix'],'png':['Imagem']}[extension])
    if extension=='docx':assert len(parts[0]['pages'])==2
    for part in parts:
        for page in part['pages']:
            code,body,_=request(environment,'page',{'document_id':v['document_id'],'version_id':v['id'],'part_index':part['index'],'page_index':page['index']},tenant=a,employee=True)
            assert code==200 and body.startswith(b'\x89PNG')
            from PIL import Image
            image=Image.open(io.BytesIO(body));assert image.width==page['width'] and image.height==page['height']
