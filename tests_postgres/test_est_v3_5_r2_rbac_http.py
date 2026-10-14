"""EST-V3.5-R2 — RBAC-REGULARIZE no CONTRATO HTTP real (acesso direto à API).

Prova que a regularização da validade física é concedida/barrada pelo BACKEND,
independentemente da UI: a rota ``POST /api/stock/items/regularize-validity`` é
exercida com JWT real por perfil, sob ``JWT_ENFORCEMENT_MODE=enforce``. Só o
transporte (socket) é substituído por um sink em memória — JWT, RBAC e
isolamento empresa/unidade são nativos. A tela nunca é a autoridade.

Regra de negócio (RBAC-REGULARIZE): a ação é EXCLUSIVA dos perfis operacionais
de unidade — Administrador Local (role ``admin``) e Gestor de EPI (role
``user``). NEGADA ao Administrador Geral (``general_admin`` — mantém só
``stock:adjust``), ao Administrador Master (``master_admin``), ao Administrador
de Registro (``registry_admin``), ao Comprador (``buyer``), ao Aprovador
(``approver``) e ao Colaborador (``employee``). O escopo empresa/unidade é
reaplicado sobre a peça.
"""
import io
import json
import os
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from core.bootstrap import init_db
from core.database import get_connection
from core.security import create_jwt_token
from modules.stock.routes import handle_post_stock_item_regularize_validity
from modules.stock.service import create_stock_item, next_company_qr_sequence

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3.5-R2 RBAC HTTP exige PostgreSQL real.',
)

FUTURE = (date.today() + timedelta(days=365)).isoformat()


class ResponseSink:
    """Transporte em memória: substitui apenas o socket. JWT/RBAC/isolamento são nativos."""

    def __init__(self, path, token_actor, command='POST'):
        self.path, self.command, self.client_address = path, command, ('127.0.0.1', 0)
        self.headers = {'Authorization': 'Bearer ' + create_jwt_token(token_actor)}
        self.wfile = io.BytesIO()
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, *args):
        pass

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue()) if self.wfile.getvalue() else None


@pytest.fixture(scope='module')
def conn():
    init_db()
    c = get_connection()
    yield c
    c.close()


@pytest.fixture(autouse=True)
def _enforce_jwt(monkeypatch):
    # Sempre enviamos Bearer; enforce apenas reafirma o contrato do servidor.
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


@pytest.fixture
def env(conn):
    """Semeia empresa/unidades/EPI e commita (a rota abre a PRÓPRIA conexão do
    pool — só enxerga o que já foi commitado). Banco PostgreSQL é descartável e
    isolado; cada teste usa sufixo único, sem colisão."""
    c = conn
    sfx = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('RBAC ' + sfx, sfx, 'text')).lastrowid
    c.execute("UPDATE companies SET timezone='UTC' WHERE id=?", (company,))
    other_company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                              ('RBAC2 ' + sfx, sfx + 'b', 'text')).lastrowid
    unit_a = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                       (company, 'UA', 'base', 'T')).lastrowid
    unit_b = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                       (company, 'UB', 'base', 'T')).lastrowid
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit_a, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    seeder = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                       ('seed_' + sfx, 'x', 'Seeder', 'admin', company)).lastrowid

    def mkpiece(unit):
        seqv = next_company_qr_sequence(c, company)
        qr = 'QR-' + uuid4().hex
        iid = create_stock_item(c, company, unit, epi, 'N/A', 'M', 'N/A', seqv, qr,
                                None, '', '', 'unit', '', '', seeder, now)  # validade DESCONHECIDA
        c.commit()  # a rota abre OUTRA conexão do pool: só enxerga o que foi commitado
        return iid, qr

    def mkuser(role, unit=None, company_id=None):
        # Administrador Local/Gestor de EPI têm vínculo com UMA unidade via
        # linked_employee_id -> employees.unit_id (actor_operational_unit_id).
        cid = company_id or company
        linked = None
        if unit is not None:
            linked = c.execute('INSERT INTO employees(company_id,unit_id,employee_id_code,name,sector,'
                               'role_name,admission_date,schedule_type) VALUES (?,?,?,?,?,?,?,?)',
                               (cid, unit, role + '-' + uuid4().hex, 'E', 'S', 'R',
                                date.today().isoformat(), 'administrativo')).lastrowid
        uid = c.execute('INSERT INTO users(username,password,full_name,role,company_id,linked_employee_id) '
                        'VALUES (?,?,?,?,?,?)',
                        (role + '_' + uuid4().hex, 'x', role, role, cid, linked)).lastrowid
        c.commit()  # idem: visível à conexão da rota
        return dict(id=uid, role=role, company_id=cid, full_name=role)

    c.commit()
    return dict(c=c, company=company, other_company=other_company, unit_a=unit_a, unit_b=unit_b,
                epi=epi, mkpiece=mkpiece, mkuser=mkuser)


def _post(token_actor, qr, unit_id=None, company_id=None):
    payload = dict(actor_user_id=token_actor['id'], qr_code=qr, physical_expiry_date=FUTURE,
                   evidence='Laudo do fabricante nº 123', justification='Captura de validade do lote')
    if unit_id is not None:
        payload['unit_id'] = unit_id
    if company_id is not None:
        payload['company_id'] = company_id
    handler = ResponseSink('/api/stock/items/regularize-validity', token_actor, 'POST')
    err = None
    try:
        handle_post_stock_item_regularize_validity(handler, urlparse(handler.path), payload, None)
    except (ValueError, PermissionError) as exc:
        err = (type(exc).__name__, str(exc))
    return handler, err


def _events(c, iid):
    c.rollback()  # snapshot fresco: enxerga o commit da conexão da rota (READ COMMITTED)
    return int(c.execute("SELECT COUNT(*) AS n FROM epi_stock_events WHERE stock_item_id=? "
                         "AND event_type='expiry_regularization'", (iid,)).fetchone()['n'])


# — AUTORIZAÇÃO: Administrador Local e Gestor de EPI regularizam via API (200) —
@pytest.mark.parametrize('role', ['admin', 'user'])
def test_authorized_roles_regularize_via_api(env, role):
    s = env
    iid, qr = s['mkpiece'](s['unit_a'])
    actor = s['mkuser'](role, unit=s['unit_a'])
    handler, err = _post(actor, qr)
    assert err is None, f'{role} (perfil autorizado) deveria conseguir: {err}'
    assert handler.status == 200 and handler.body['ok'] is True
    assert handler.body['validity_status'] == 'valid'
    assert _events(s['c'], iid) == 1


# — NEGAÇÃO (acesso DIRETO à API): perfis não autorizados são barrados pelo backend —
@pytest.mark.parametrize('role', ['general_admin', 'master_admin', 'registry_admin',
                                  'buyer', 'approver', 'employee'])
def test_denied_roles_rejected_via_api(env, role):
    s = env
    iid, qr = s['mkpiece'](s['unit_a'])
    actor = s['mkuser'](role)  # negação é por PERMISSÃO (authorize_action), antes de qualquer escopo
    handler, err = _post(actor, qr, unit_id=s['unit_a'], company_id=s['company'])
    assert err is not None and err[0] == 'PermissionError' and 'permiss' in err[1].lower(), \
        f'{role} deveria ser barrado por RBAC (ensure_permission), veio status={handler.status} err={err}'
    assert _events(s['c'], iid) == 0  # nada gravado


# — ISOLAMENTO POR UNIDADE: Administrador Local da Unidade A não alcança peça da Unidade B —
def test_unit_isolation_rejected_via_api(env):
    # Isolamento por unidade é FAIL-CLOSED já na BUSCA: lookup_stock_item_by_qr é
    # escopada à unidade operacional do ator, então a peça da Unidade B é
    # invisível ao ator da Unidade A ("não encontrado"). A checagem explícita de
    # unidade no handler é defesa secundária. Controle positivo abaixo prova que
    # o bloqueio é da UNIDADE (mesma peça/QR), não de um QR inexistente.
    s = env
    iid, qr = s['mkpiece'](s['unit_b'])                 # peça está na Unidade B
    actor_a = s['mkuser']('admin', unit=s['unit_a'])    # ator opera na Unidade A
    handler, err = _post(actor_a, qr)
    assert err is not None and err[0] == 'ValueError' and 'encontrado' in err[1].lower(), \
        f'esperado isolamento por unidade (peça invisível ao ator), veio status={handler.status} err={err}'
    assert _events(s['c'], iid) == 0
    # controle positivo: ator da MESMA Unidade B regulariza a mesma peça (200)
    actor_b = s['mkuser']('admin', unit=s['unit_b'])
    handler2, err2 = _post(actor_b, qr)
    assert err2 is None and handler2.status == 200, f'ator da Unidade B deveria conseguir: {err2}'
    assert _events(s['c'], iid) == 1


# — ISOLAMENTO POR EMPRESA: ator de OUTRA empresa não alcança a peça (item não encontrado) —
def test_company_isolation_rejected_via_api(env):
    s = env
    iid, qr = s['mkpiece'](s['unit_a'])
    other_unit = s['c'].execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                                (s['other_company'], 'UO', 'base', 'T')).lastrowid
    s['c'].commit()
    actor = s['mkuser']('admin', unit=other_unit, company_id=s['other_company'])
    s['c'].commit()
    handler, err = _post(actor, qr)   # QR real, mas empresa do ator é outra → lookup por empresa falha
    assert err is not None and err[0] == 'ValueError' and 'encontrado' in err[1].lower(), \
        f'ator de outra empresa não pode alcançar a peça, veio status={handler.status} err={err}'
    assert _events(s['c'], iid) == 0
