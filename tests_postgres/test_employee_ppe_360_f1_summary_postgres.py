"""Ficha 360° (F1) — resumo do colaborador em PostgreSQL real, via HTTP/JWT.

Prova, no dialeto de produção e pela API (não pelo serviço direto):

* identificação, responsáveis (DF-1) e indicadores com números conferidos;
* autorização: Admin Master bloqueado (DF-3), perfis sem ``employees:view``
  recusados, sem sessão → 401, identidade divergente → 403;
* isolamento: outra empresa e outra unidade → 404 idêntico ao inexistente;
* auditoria (DF-7) de abertura concedida e negada, sem conteúdo sensível;
* carga: 10 Fichas abertas ao mesmo tempo, sem esgotar o pool de conexões.
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from uuid import uuid4

import pytest
from test_est_v3_5_postmerge_receipt import server as _server_fixture
from test_est_v3_5_r3_lot_receipt_http import _fresh
from test_stock_lot_evidence_http import call

server = _server_fixture

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Ficha 360° (F1) via HTTP exige PostgreSQL isolado.',
)

TODAY = date.today()  # noqa: DTZ011 - mesma referência local do servidor
PAST = (TODAY - timedelta(days=10)).isoformat()
SOON = (TODAY + timedelta(days=5)).isoformat()
LATER = (TODAY + timedelta(days=90)).isoformat()
SENSITIVE_KEYS = {'cpf', 'email', 'whatsapp', 'signature_data', 'epi_photo_data', 'password', 'totp_secret'}


@pytest.fixture(autouse=True)
def enforce(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


def _company(c, label):
    sfx = uuid4().hex
    return c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                     (f'{label} {sfx[:6]}', sfx[:14], 'text')).lastrowid


def _unit(c, company, name):
    return c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, name, 'base', 'T')).lastrowid


def _employee(c, company, unit, name, **extra):
    cols = {'company_id': company, 'unit_id': unit, 'employee_id_code': 'M-' + uuid4().hex[:6], 'name': name,
            'sector': 'Manutenção', 'role_name': 'Eletricista', 'admission_date': '2020-01-01',
            'schedule_type': '8h', 'cpf': '123.456.789-00', 'email': 'pessoa@exemplo.com',
            'whatsapp': '+5511999999999', **extra}
    names = ', '.join(cols)
    marks = ', '.join('?' for _ in cols)
    return c.execute(f'INSERT INTO employees ({names}) VALUES ({marks})', tuple(cols.values())).lastrowid


def _user(c, company, role, name, *, linked=None, active=1):
    uid = c.execute('INSERT INTO users(username,password,full_name,role,company_id,linked_employee_id,active) '
                    'VALUES (?,?,?,?,?,?,?)',
                    ('f1_' + uuid4().hex, 'x', name, role, company, linked, active)).lastrowid
    return {'id': uid, 'role': role, 'company_id': company, 'full_name': name}


def _epi(c, company, unit, name, section):
    return c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,ca_expiry,'
                     'epi_validity_date,manufacture_date,validity_days,epi_section) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                     (company, unit, name, uuid4().hex, uuid4().hex[:8], 'S', 'un', '2030-01-01', '2030-01-01',
                      '2020-01-01', 0, section)).lastrowid


def _delivery(c, company, unit, employee, epi, *, qty=1, next_date='', returned='', reverted=''):
    return c.execute(
        'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, '
        'delivery_date, next_replacement_date, signature_name, unit_id, returned_date, migration_reverted_at, '
        'signature_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (company, employee, epi, qty, 'un', 'S', 'R', '2026-01-10', next_date, 'Assinou', unit, returned,
         reverted, 'data:image/png;base64,SECRETO'),
    ).lastrowid


def _request(c, company, unit, employee, epi, status):
    return c.execute(
        'INSERT INTO epi_requests (company_id, unit_id, employee_id, epi_id, quantity, request_token, status, '
        'requested_at, last_updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
        (company, unit, employee, epi, 1, uuid4().hex, status, '2026-01-01', '2026-01-01'),
    ).lastrowid


@pytest.fixture(scope='module')
def world(server):
    with _fresh() as c:
        a = _company(c, 'Tenant A')
        b = _company(c, 'Tenant B')
        u1, u2 = _unit(c, a, 'Unidade Norte'), _unit(c, a, 'Unidade Sul')
        ub = _unit(c, b, 'Unidade B')
        le = c.execute('INSERT INTO legal_entities (company_id, cnpj, legal_name, trade_name) VALUES (?,?,?,?)',
                       (a, '11.222.333/0001-81', 'Tenant A Indústria SA', 'Tenant A')).lastrowid
        oc = c.execute('INSERT INTO outsourced_companies (company_id, legal_name, trade_name, cnpj) VALUES (?,?,?,?)',
                       (a, 'Terceira Serviços LTDA', 'Terceira', '44.555.666/0001-77')).lastrowid
        sc = c.execute('INSERT INTO service_contracts (company_id, outsourced_company_id, contract_ref, start_date, '
                       "end_date, status) VALUES (?,?,?,?,?,'active')", (a, oc, 'CT-2026-07', '2026-01-01', '2026-12-31')).lastrowid

        e1 = _employee(c, a, u1, 'Ana Souza', legal_entity_id=le)
        e2 = _employee(c, a, u2, 'Bruno Lima')
        e3 = _employee(c, a, u1, 'Carla Terceira', tipo_vinculo='Terceirizado', outsourced_company_id=oc,
                       service_contract_id=sc)
        e_arch = _employee(c, a, u1, 'Arquivado', archived_at='2026-05-01', status='archived')
        e_del = _employee(c, a, u1, 'Excluído', deleted_at='2026-05-01')
        eb = _employee(c, b, ub, 'Pessoa B')
        # contas de Administrador Local/Gestor de EPI resolvem a unidade pelo colaborador vinculado
        la1_emp, ge1_emp, la2_emp = (_employee(c, a, u1, 'Base LA1'), _employee(c, a, u1, 'Base GE1'),
                                     _employee(c, a, u2, 'Base LA2'))
        tmp_emp = _employee(c, a, u2, 'Base temporária')
        users = {
            'ga': _user(c, a, 'general_admin', 'Gabriela Geral'),
            'ra': _user(c, a, 'registry_admin', 'Rafael Registro'),
            'la1': _user(c, a, 'admin', 'Lucas Local', linked=la1_emp),
            'ge1': _user(c, a, 'user', 'Gisele Gestora', linked=ge1_emp),
            'la2': _user(c, a, 'admin', 'Laura Local Sul', linked=la2_emp),
            'tmp': _user(c, a, 'gestor_epi', 'Tiago Temporário', linked=tmp_emp),
            'inactive': _user(c, a, 'admin', 'Inativo Local', linked=la1_emp, active=0),
            'master': _user(c, None, 'master_admin', 'Mestre'),
            'buyer': _user(c, a, 'buyer', 'Comprador'),
            'approver': _user(c, a, 'approver', 'Aprovador'),
            'portal': _user(c, a, 'employee', 'Portal', linked=e1),
            'ga_b': _user(c, b, 'general_admin', 'Geral B'),
        }
        c.execute('INSERT INTO employee_unit_movements (employee_id, company_id, source_unit_id, target_unit_id, '
                  "movement_type, start_date, end_date, actor_user_id, actor_name, created_at) "
                  "VALUES (?,?,?,?,'temporary',?,?,?,?,?)",
                  (tmp_emp, a, u2, u1, (TODAY - timedelta(days=1)).isoformat(), (TODAY + timedelta(days=30)).isoformat(),
                   users['ga']['id'], 'seed', TODAY.isoformat()))
        luva = _epi(c, a, u1, 'Luva de vaqueta', 'Mãos')
        capacete = _epi(c, a, u1, 'Capacete classe B', 'Cabeça')
        sem_secao = _epi(c, a, u1, 'Protetor auricular', '')
        _delivery(c, a, u1, e1, luva, qty=2, next_date=PAST)
        _delivery(c, a, u1, e1, capacete, next_date=SOON)
        _delivery(c, a, u1, e1, sem_secao, next_date='')
        _delivery(c, a, u1, e1, capacete, next_date=PAST, returned='2026-02-01')       # devolvida
        _delivery(c, a, u1, e1, luva, qty=5, next_date=PAST, reverted='2026-03-01')    # revertida
        _delivery(c, a, u2, e2, luva, next_date=LATER)
        for status in ('solicitado', 'solicitado', 'em análise', 'aprovado', 'aguardando estoque', 'prorrogado',
                       'entrega recusada', '', 'entregue', 'assinado', 'rejeitado', 'cancelado', 'valor-estranho'):
            _request(c, a, u1, e1, luva, status)
        c.commit()
    return {'a': a, 'b': b, 'u1': u1, 'u2': u2, 'e1': e1, 'e2': e2, 'e3': e3, 'e_arch': e_arch,
            'e_del': e_del, 'eb': eb, 'users': users, 'luva': luva}


def _get(server, w, who, employee_id, *, query=''):
    actor = w['users'][who]
    return call(server, {'actor': actor}, f'/api/employees/{employee_id}/ppe-360/summary{query}')


def _audit_rows(actor_id):
    with _fresh() as c:
        rows = c.execute('SELECT * FROM ficha_epi_audit_log WHERE actor_user_id = ? ORDER BY id', (actor_id,)).fetchall()
        return [dict(r) for r in rows]


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


# ── Conteúdo ─────────────────────────────────────────────────────────────────


def test_resumo_traz_identificacao_e_indicadores_reais(server, world):
    status, body = _get(server, world, 'ga', world['e1'])
    assert status == 200, body
    assert body['ok'] is True
    data = body['data']
    emp = data['employee']
    assert emp['name'] == 'Ana Souza' and emp['job_title'] == 'Eletricista'
    assert emp['registration'].startswith('M-')
    assert emp['company']['id'] == world['a']
    assert emp['unit'] == {'id': world['u1'], 'name': 'Unidade Norte', 'temporary_allocation': False, 'base_unit_name': ''}
    assert emp['legal_entity']['cnpj'] == '11.222.333/0001-81'
    assert emp['employment_type'] == 'CLT' and emp['contracted_workforce'] is None
    assert emp['lifecycle'] == 'active'

    ind = data['indicators']
    # em uso: luva(2) + capacete(1) + protetor(1); devolvida e revertida fora
    assert ind['in_use'] == {'units': 4, 'products': 3, 'categories': 2, 'uncategorized_products': 1}
    # próxima troca: a menor data gravada entre as em uso (a da luva, vencida)
    assert ind['next_replacement'] == {'date': PAST, 'epi_name': 'Luva de vaqueta', 'overdue_count': 1}
    pending = ind['pending_requests']
    codes = {item['code']: item['count'] for item in pending['by_status']}
    assert codes == {'SUBMITTED': 3, 'UNDER_REVIEW': 1, 'APPROVED': 1, 'WAITING_STOCK': 1,
                     'DELIVERY_REFUSED': 1, 'POSTPONED': 1, 'UNKNOWN': 1}
    assert pending['total'] == sum(codes.values()) == 9
    # ordem = ordem da máquina de estados; desconhecido por último
    assert pending['by_status'][0]['code'] == 'SUBMITTED'
    assert pending['by_status'][-1]['code'] == 'UNKNOWN'


def test_resumo_nao_expoe_dado_sensivel(server, world):
    status, body = _get(server, world, 'ga', world['e1'])
    assert status == 200
    assert not SENSITIVE_KEYS & set(_keys(body)), SENSITIVE_KEYS & set(_keys(body))
    text = repr(body)
    for value in ('123.456.789-00', 'pessoa@exemplo.com', '+5511999999999', 'SECRETO'):
        assert value not in text


def test_responsaveis_derivados_da_unidade_e_da_empresa(server, world):
    _status, body = _get(server, world, 'ga', world['e1'])
    resp = body['data']['responsibles']
    assert resp['unit'] == [
        {'role': 'admin', 'name': 'Lucas Local'},
        {'role': 'user', 'name': 'Gisele Gestora'},
        {'role': 'user', 'name': 'Tiago Temporário'},   # alocação temporária vigente na unidade
    ]
    assert resp['company'] == [
        {'role': 'general_admin', 'name': 'Gabriela Geral'},
        {'role': 'registry_admin', 'name': 'Rafael Registro'},
    ]
    names = {e['name'] for group in resp.values() for e in group}
    assert not names & {'Laura Local Sul', 'Inativo Local', 'Geral B', 'Comprador', 'Aprovador', 'Portal', 'Mestre'}


def test_terceirizado_traz_empresa_e_contrato(server, world):
    status, body = _get(server, world, 'ga', world['e3'])
    assert status == 200, body
    cw = body['data']['employee']['contracted_workforce']
    assert cw['outsourced_company'] == {'name': 'Terceira', 'legal_name': 'Terceira Serviços LTDA',
                                        'cnpj': '44.555.666/0001-77'}
    assert cw['contract'] == {'ref': 'CT-2026-07', 'start_date': '2026-01-01', 'end_date': '2026-12-31',
                              'status': 'active'}


def test_colaborador_sem_registros_mostra_vazio_sem_inventar(server, world):
    _status, body = _get(server, world, 'ga', world['e3'])
    ind = body['data']['indicators']
    assert ind['pending_requests'] == {'total': 0, 'by_status': []}
    assert ind['next_replacement'] is None
    assert ind['in_use'] == {'units': 0, 'products': 0, 'categories': 0, 'uncategorized_products': 0}


def test_arquivado_abre_com_situacao_e_excluido_nao(server, world):
    status, body = _get(server, world, 'ga', world['e_arch'])
    assert status == 200 and body['data']['employee']['lifecycle'] == 'archived'
    status, body = _get(server, world, 'ga', world['e_del'])
    assert status == 404 and body['error']['code'] == 'EMPLOYEE_NOT_FOUND'


# ── Autorização e isolamento ─────────────────────────────────────────────────


def test_admin_master_e_bloqueado(server, world):
    status, body = _get(server, world, 'master', world['e1'])
    assert status == 403 and body == {'ok': False, 'error': {'code': 'FORBIDDEN',
                                                             'message': 'Perfil sem permissão para esta consulta.'}}


@pytest.mark.parametrize('who', ['buyer', 'approver', 'portal'])
def test_perfis_sem_employees_view_sao_recusados(server, world, who):
    status, body = _get(server, world, who, world['e1'])
    assert status == 403 and body['error']['code'] == 'FORBIDDEN'


@pytest.mark.parametrize('who', ['ga', 'ra', 'la1', 'ge1'])
def test_perfis_legitimos_abrem(server, world, who):
    status, body = _get(server, world, who, world['e1'])
    assert status == 200, (who, body)


def test_outra_empresa_responde_igual_a_inexistente(server, world):
    other = _get(server, world, 'ga_b', world['e1'])
    missing = _get(server, world, 'ga_b', 987654321)
    assert other == missing == (404, {'ok': False, 'error': {'code': 'EMPLOYEE_NOT_FOUND',
                                                             'message': 'Colaborador indisponível no seu escopo.'}})


def test_outra_unidade_responde_404(server, world):
    assert _get(server, world, 'la2', world['e1'])[0] == 404
    assert _get(server, world, 'la2', world['e2'])[0] == 200
    assert _get(server, world, 'la1', world['e2'])[0] == 404


def test_sem_sessao_e_401(server, world):
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    with pytest.raises(HTTPError) as exc:
        urlopen(Request(f"{server}/api/employees/{world['e1']}/ppe-360/summary"), timeout=10)
    assert exc.value.code == 401


def test_identidade_divergente_na_query_e_recusada(server, world):
    other = world['users']['la2']['id']
    status, _ = _get(server, world, 'ga', world['e1'], query=f'?actor_user_id={other}')
    assert status == 403


def test_id_invalido_e_recusado(server, world):
    status, body = _get(server, world, 'ga', 0)
    assert status == 400 and body['error']['code'] == 'INVALID_EMPLOYEE_ID'


# ── Auditoria (DF-7) ─────────────────────────────────────────────────────────


def test_abertura_concedida_e_auditada(server, world):
    actor = world['users']['ra']
    before = len(_audit_rows(actor['id']))
    assert _get(server, world, 'ra', world['e1'])[0] == 200
    rows = _audit_rows(actor['id'])
    assert len(rows) == before + 1
    row = rows[-1]
    assert row['action'] == 'view_360'
    assert row['actor_role'] == 'registry_admin' and row['actor_name'] == 'Rafael Registro'
    assert row['employee_id'] == world['e1'] and row['employee_name'] == 'Ana Souza'
    assert row['company_id'] == world['a'] and row['unit_id'] == world['u1']
    assert row['accessed_at']


def _company_audit(actor_id):
    with _fresh() as c:
        rows = c.execute("SELECT * FROM company_audit_logs WHERE actor_user_id = ? AND action_type = 'ppe360_view_denied' "
                         'ORDER BY id', (actor_id,)).fetchall()
        return [dict(r) for r in rows]


def test_negativa_e_auditada_na_empresa_do_ator_sem_revelar_o_colaborador(server, world):
    import json as _json
    actor = world['users']['ga_b']
    before_ficha = len(_audit_rows(actor['id']))
    before = len(_company_audit(actor['id']))
    assert _get(server, world, 'ga_b', world['e1'])[0] == 404
    rows = _company_audit(actor['id'])
    assert len(rows) == before + 1
    row = rows[-1]
    assert row['company_id'] == world['b'] and row['actor_name'] == 'Geral B'
    details = _json.loads(row['details_json'])[0]
    assert details == {'requested_employee_id': world['e1'], 'result': 'EMPLOYEE_NOT_FOUND',
                       'actor_role': 'general_admin', 'ip_address': '127.0.0.1'}
    assert 'Ana Souza' not in row['summary'] + row['details_json']
    # a trilha da Ficha (com nome do colaborador) não recebe a negativa
    assert len(_audit_rows(actor['id'])) == before_ficha


@pytest.mark.parametrize('who,code', [('buyer', 'FORBIDDEN'), ('la2', 'EMPLOYEE_NOT_FOUND')])
def test_cada_negativa_registra_o_codigo_do_resultado(server, world, who, code):
    import json as _json
    actor = world['users'][who]
    before = len(_company_audit(actor['id']))
    _get(server, world, who, world['e1'])
    rows = _company_audit(actor['id'])
    assert len(rows) == before + 1 and _json.loads(rows[-1]['details_json'])[0]['result'] == code


def test_bloqueio_do_master_nao_grava_dado_de_tenant(server, world):
    actor = world['users']['master']
    assert _get(server, world, 'master', world['e1'])[0] == 403
    # sem empresa, o Admin Master só aparece no log estruturado da aplicação
    assert _audit_rows(actor['id']) == [] and _company_audit(actor['id']) == []


# ── Desempenho e pool ────────────────────────────────────────────────────────


def test_dez_fichas_simultaneas_sem_esgotar_o_pool(server, world):
    """Cada Ficha aberta faz UMA requisição (resumo) e segura UMA conexão do pool
    só durante a resposta. Dez aberturas simultâneas cabem no pool padrão (10),
    e nenhuma conexão fica retida depois."""
    from core.database import db_pool_status

    who = ['ga', 'ra', 'la1', 'ge1', 'la2', 'ga', 'ra', 'la1', 'ge1', 'ga']
    target = [world['e1'], world['e1'], world['e1'], world['e3'], world['e2'],
              world['e3'], world['e3'], world['e3'], world['e1'], world['e2']]
    barrier = threading.Barrier(10)
    peak = {'in_use': 0}
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            peak['in_use'] = max(peak['in_use'], int(db_pool_status().get('in_use') or 0))
            time.sleep(0.002)

    def open_ficha(i):
        barrier.wait()
        started = time.perf_counter()
        status, body = _get(server, world, who[i], target[i])
        return status, time.perf_counter() - started, body

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(open_ficha, range(10)))
    finally:
        stop.set()
        sampler.join(timeout=5)
    assert [r[0] for r in results] == [200] * 10, [(r[0], r[2]) for r in results if r[0] != 200]
    # A resposta HTTP sai antes de o handler devolver a conexão: espera a devolução
    # (com prazo) em vez de ler o pool no mesmo instante. Conexão retida ainda reprova.
    settle = time.monotonic() + 5
    status_after = db_pool_status()
    while int(status_after.get('in_use') or 0) and time.monotonic() < settle:
        time.sleep(0.02)
        status_after = db_pool_status()
    assert status_after['maxconn'] >= 10
    assert peak['in_use'] <= status_after['maxconn']
    assert int(status_after.get('in_use') or 0) == 0, status_after   # nada retido
    latencies = sorted(r[1] for r in results)
    print(f'\nF1 carga: 10 Fichas simultâneas; p50={latencies[4]*1000:.0f} ms '
          f'p95/máx={latencies[9]*1000:.0f} ms; pico de conexões em uso={peak["in_use"]}; pool={status_after}')
    assert latencies[9] < 5.0
