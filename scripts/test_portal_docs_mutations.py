#!/usr/bin/env python3
"""Reproduce real red tests in disposable source copies and local databases only.

Never edits the implementation checkout. Every mutant has its own fresh DB.
Uses the same HTTP/renderer tests; failure must be an assertion, not a syntax error.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse, urlunparse
import uuid

import psycopg2
from psycopg2 import sql

MUTANTS = [
    ('manager_role', 'modules/safety_library/service.py', '    require_structural_admin(actor)\n', '    pass  # mutation: remove privileged role gate\n', 'test_direct_http_rbac[master_admin]'),
    ('tenant', 'modules/safety_library/service.py', "    if int(version['company_id']) != int(context['company_id']):\n        return False\n", "    context['company_id'] = version['company_id']  # mutation: trust resource tenant\n", 'test_all_units_does_not_mean_other_companies'),
    ('unit', 'modules/safety_library/service.py', "    if not int(version['all_units']) and int(context['unit_id']) not in json.loads(version['unit_ids']):\n        return False\n", '', 'test_preview_scope_publication_and_every_page_access'),
    ('original_role', 'modules/safety_library/service.py', "return actor.get('role') in ('general_admin','registry_admin') and bool(policy)", 'return bool(policy)', 'test_employee_never_original_and_backend_policy'),
    ('active_pdf', 'modules/safety_library/render_worker.py', "if re.search(r'/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|XFA)\\b', obj):", 'if False:  # mutation: accept active PDF', 'test_malicious_uploads_mime_size_and_cross_scope'),
    ('migration', 'epi_backend/migrations/034_safety_library.py', None, None, 'test_direct_http_rbac[general_admin]'),
]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dsn',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    target=urlparse(args.dsn)
    if target.hostname not in ('localhost','127.0.0.1') or not target.path.startswith('/portal_docs_'):
        raise SystemExit('Only explicitly local portal_docs_* databases permitted')
    root=Path(__file__).resolve().parents[1]
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    records=[]
    for name,relative,before,after,test in MUTANTS:
        with tempfile.TemporaryDirectory(prefix='portal-docs-mutant-') as temp:
            copy=Path(temp)/'repo'
            shutil.copytree(root,copy,ignore=shutil.ignore_patterns('.git','node_modules','.dart_tool','build','__pycache__','.pytest_cache','.ruff_cache','.env','.env.*','app'))
            changed=copy/relative
            if before is None:changed.unlink()
            else:
                source=changed.read_text()
                assert before in source,(name,'mutation anchor missing')
                changed.write_text(source.replace(before,after,1))
            database='portal_docs_mut_'+uuid.uuid4().hex[:16]
            admin=psycopg2.connect(urlunparse(target._replace(path='/postgres')));admin.autocommit=True
            with admin.cursor() as cursor:cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            dsn=urlunparse(target._replace(path='/'+database))
            env=dict(os.environ,DATABASE_URL=dsn,PORTAL_DOCS_TEST_DSN=dsn)
            result=subprocess.run([sys.executable,'-m','pytest','tests/test_portal_docs_postgres.py::'+test,'-q','--tb=short'],cwd=copy,env=env,text=True,capture_output=True,timeout=180)
            log=result.stdout+result.stderr
            (output/(name+'.log')).write_text(log)
            detected=result.returncode==1 and ('AssertionError' in log or 'E   assert ' in log) and 'SyntaxError' not in log
            records.append({'mutation':name,'test':test,'exit_code':result.returncode,'detected':detected})
            with admin.cursor() as cursor:
                cursor.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s',(database,))
                cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
            admin.close()
    (output/'results.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(records))
    if not all(record['detected'] for record in records):raise SystemExit(1)


if __name__=='__main__':main()
