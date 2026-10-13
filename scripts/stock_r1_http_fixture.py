"""Exercise actual application HTTP from Flutter with a private PostgreSQL DB.

The signing key, JWT and test context remain in process memory.
No credentials or context are written to logs or artifacts.
"""
import importlib.util
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse


def main():
    root = Path(__file__).resolve().parents[1]
    db = urlparse(os.environ['DATABASE_URL'])
    if (os.environ.get('APP_ENV') != 'test'
            or db.hostname not in ('localhost', '127.0.0.1')
            or not (db.path.lstrip('/').startswith('est35_independent_')
                    or db.path == '/stock_r1_integration')):
        raise RuntimeError('HTTP fixture requires a disposable loopback test database.')
    os.environ['JWT_SECRET'] = secrets.token_hex(32)
    os.environ['JWT_ENFORCEMENT_MODE'] = 'enforce'
    sys.path.insert(0, str(root))
    from core.bootstrap import init_db
    from core.database import get_connection
    from core.security import create_jwt_token

    init_db()
    spec = importlib.util.spec_from_file_location(
        'native_fixture', root / 'tests_postgres/test_est_v3_5_r1_postgres.py')
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    connection = get_connection()
    seed = qa.seed(connection, ['valid', 'expired', 'unknown', 'blocked'], ca_expiry=qa.FUTURE)
    foreign = qa.seed(connection, ['valid'], ca_expiry=qa.FUTURE)
    import app
    # Same readiness transition as app.main, after real init_db succeeded.
    app._set_bootstrap_state(ready=True, completed_at=datetime.now(timezone.utc).isoformat(),
                             error_code='', error_kind='', error_message='')
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    context = {
        'base_url': 'http://127.0.0.1:' + str(server.server_port),
        'actor_id': seed['actor']['id'], 'company_id': seed['company'],
        'unit_id': seed['unit'], 'employee_id': seed['employee'], 'epi_id': seed['epi'],
        'valid_item': seed['items']['valid'], 'unknown_item': seed['items']['unknown'],
        'foreign_qr': foreign['items']['valid']['qr'], 'today': qa.TODAY, 'future': qa.FUTURE,
    }
    client_env = dict(os.environ, EST35_HTTP_CONTEXT_JSON=json.dumps(context),
                      EST35_HTTP_TOKEN=create_jwt_token(seed['actor']))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return subprocess.run(
            ['flutter', 'test', '--reporter', 'expanded', 'test/stock_http_integration_test.dart'],
            cwd=root / 'flutter/apps/epi_admin', env=client_env,
        ).returncode
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        connection.close()


if __name__ == '__main__':
    sys.exit(main())
