"""Run the actual application HTTP handler against a private PostgreSQL DB."""
import importlib.util,json,os,sys
from pathlib import Path
from http.server import ThreadingHTTPServer

root=Path(__file__).resolve().parents[1]
from urllib.parse import urlparse
db=urlparse(os.environ['DATABASE_URL'])
assert os.environ.get('APP_ENV') == 'test'
assert db.hostname in ('localhost','127.0.0.1')
assert db.path.lstrip('/').startswith('est35_independent_') or db.path == '/stock_r1_integration'
out=Path(os.environ['EST35_HTTP_OUTPUT']);out.mkdir(parents=True,exist_ok=True)
short=json.loads((root/'ci/authorized_backend.json').read_text())['product']
sys.path.insert(0,str(root))
from core.bootstrap import init_db
from core.database import get_connection
from core.security import create_jwt_token
init_db()
spec=importlib.util.spec_from_file_location('native_fixture',root/'tests_postgres/test_est_v3_5_r1_postgres.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
c=get_connection();seed=qa.seed(c,['valid','expired','unknown','blocked'],ca_expiry=qa.FUTURE)
foreign=qa.seed(c,['valid'],ca_expiry=qa.FUTURE)
import app
from datetime import datetime, timezone
# Same readiness transition as app.main, only after real init_db succeeded.
app._set_bootstrap_state(ready=True, completed_at=datetime.now(timezone.utc).isoformat(), error_code='', error_kind='', error_message='')
server=ThreadingHTTPServer(('127.0.0.1',0),app.EpiHandler)
context={'server_pid':os.getpid(),'base_url':'http://127.0.0.1:'+str(server.server_port),'token':create_jwt_token(seed['actor']),
'actor_id':seed['actor']['id'],'company_id':seed['company'],'unit_id':seed['unit'],'employee_id':seed['employee'],
'epi_id':seed['epi'],'valid_item':seed['items']['valid'],'unknown_item':seed['items']['unknown'],
'foreign_qr':foreign['items']['valid']['qr'],'today':qa.TODAY,'future':qa.FUTURE}
# A fixture token, never a production credential. No token in stdout or logs.
(out/'stock-r1-http-context.json').write_text(json.dumps(context))
print(short,'actual app.EpiHandler fixture ready',flush=True)
try:server.serve_forever()
finally:server.server_close();c.close()
