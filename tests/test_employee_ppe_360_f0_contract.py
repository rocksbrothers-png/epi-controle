"""F0 — contratos de backend da Ficha 360° de EPI.

Fixa o que toda seção futura (F1–F6) herda: autorização pela permissão e pelo
escopo de leitura OFICIAIS, 404 indistinto para inexistente/fora do escopo,
paginação no servidor com limite rígido e envelope sem vazamento. Também
prova que o pacote é somente leitura e que nenhuma rota foi exposta antes da
hora.
"""

import ast
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import schema
from core.permissions import PERM_EMPLOYEES_VIEW, PERMISSIONS
from modules.employee_ppe_360 import contract
from modules.employee_ppe_360.contract import (
    PAGE_DEFAULT,
    PAGE_MAX,
    ContractError,
    decode_cursor,
    encode_cursor,
    error_envelope,
    parse_employee_id,
    parse_page_params,
    resolve_authorized_employee,
    success_envelope,
)
from modules.employees import service as employees_service

PACKAGE = ROOT / 'modules' / 'employee_ppe_360'


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT 'whatsapp',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', empresa_origem TEXT DEFAULT '',
            tipo_vinculo TEXT DEFAULT 'CLT'
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, company_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER, movement_type TEXT,
            start_date TEXT, end_date TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name) VALUES (1, 'Tenant A'), (2, 'Tenant B');
        INSERT INTO units (id, name, company_id) VALUES (10, 'A1', 1), (11, 'A2', 1), (20, 'B1', 2);
        INSERT INTO employees (id, company_id, unit_id, name) VALUES
            (100, 1, 10, 'Colaborador A1'),
            (101, 1, 11, 'Colaborador A2'),
            (200, 2, 20, 'Colaborador B1');
    """)
    connection.commit()
    schema.ensure_employee_unit_links(connection)
    return connection


@pytest.fixture()
def conn():
    connection = _conn()
    yield connection
    connection.close()


def _unit(monkeypatch, unit_id):
    monkeypatch.setattr(employees_service, 'actor_operational_unit_id', lambda *a, **k: unit_id)


# ── Autorização e isolamento ─────────────────────────────────────────────────

def test_admin_geral_consulta_colaborador_da_propria_empresa(conn, monkeypatch):
    _unit(monkeypatch, None)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    assert resolve_authorized_employee(conn, actor, 100)['id'] == 100
    assert resolve_authorized_employee(conn, actor, '101')['id'] == 101


def test_outra_empresa_responde_404_indistinto_de_inexistente(conn, monkeypatch):
    _unit(monkeypatch, None)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    with pytest.raises(ContractError) as other_tenant:
        resolve_authorized_employee(conn, actor, 200)
    with pytest.raises(ContractError) as missing:
        resolve_authorized_employee(conn, actor, 999)
    assert other_tenant.value.code == missing.value.code == 'EMPLOYEE_NOT_FOUND'
    assert other_tenant.value.status == missing.value.status == 404
    assert str(other_tenant.value) == str(missing.value)


def test_perfil_de_unidade_so_ve_a_propria_unidade(conn, monkeypatch):
    _unit(monkeypatch, 10)
    actor = {'id': 5, 'role': 'user', 'company_id': 1, 'linked_employee_id': 100}
    assert resolve_authorized_employee(conn, actor, 100)['id'] == 100
    with pytest.raises(ContractError) as exc:
        resolve_authorized_employee(conn, actor, 101)
    assert exc.value.code == 'EMPLOYEE_NOT_FOUND'


def test_troca_de_unidade_do_ator_muda_o_resultado_na_proxima_consulta(conn, monkeypatch):
    actor = {'id': 5, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 100}
    _unit(monkeypatch, 10)
    assert resolve_authorized_employee(conn, actor, 100)['id'] == 100
    _unit(monkeypatch, 11)
    with pytest.raises(ContractError):
        resolve_authorized_employee(conn, actor, 100)
    assert resolve_authorized_employee(conn, actor, 101)['id'] == 101


def test_vinculo_local_ativo_amplia_somente_a_leitura(conn, monkeypatch):
    _unit(monkeypatch, 11)
    actor = {'id': 5, 'role': 'user', 'company_id': 1, 'linked_employee_id': 101}
    conn.execute(
        "INSERT INTO employee_unit_links (company_id, employee_id, unit_id, local_status) VALUES (1, 100, 11, 'active')"
    )
    assert resolve_authorized_employee(conn, actor, 100)['id'] == 100


def test_perfil_de_unidade_sem_unidade_operacional_nao_ve_ninguem(conn, monkeypatch):
    _unit(monkeypatch, None)
    actor = {'id': 5, 'role': 'user', 'company_id': 1}
    with pytest.raises(ContractError) as exc:
        resolve_authorized_employee(conn, actor, 100)
    assert exc.value.code == 'EMPLOYEE_NOT_FOUND'


@pytest.mark.parametrize('role', sorted(r for r, perms in PERMISSIONS.items() if PERM_EMPLOYEES_VIEW not in perms))
def test_perfis_sem_employees_view_sao_recusados_antes_de_qualquer_leitura(conn, monkeypatch, role):
    _unit(monkeypatch, None)
    calls = []

    def spy_get(connection, employee_id):
        calls.append(employee_id)
        return {'id': employee_id, 'company_id': 1}

    actor = {'id': 9, 'role': role, 'company_id': 1}
    with pytest.raises(ContractError) as exc:
        resolve_authorized_employee(conn, actor, 100, get_employee_fn=spy_get,
                                    visibility_scope_fn=lambda *a: None)
    assert exc.value.code == 'FORBIDDEN'
    assert calls == [], 'o banco não pode ser consultado sem a permissão funcional'


def test_ator_ausente_ou_sem_papel_e_recusado(conn):
    for actor in (None, {}, {'id': 1}):
        with pytest.raises(ContractError) as exc:
            resolve_authorized_employee(conn, actor, 100)
        assert exc.value.code == 'FORBIDDEN'


def test_nenhuma_permissao_nova_foi_introduzida_pela_f0():
    source = (PACKAGE / 'contract.py').read_text(encoding='utf-8')
    assert 'PERM_EMPLOYEES_VIEW' in source
    assert not re.search(r"['\"][a-z_]+:[a-z_]+['\"]", source), 'F0 não declara permissões'


# ── Parâmetros ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('raw', [0, -1, '0', '-3', 'abc', '1.5', '1e3', '', None, True, ' ', '9' * 13])
def test_id_de_colaborador_invalido(raw):
    with pytest.raises(ContractError) as exc:
        parse_employee_id(raw)
    assert exc.value.code == 'INVALID_EMPLOYEE_ID'
    assert exc.value.status == 400


def test_id_de_colaborador_valido():
    assert parse_employee_id(' 42 ') == 42
    assert parse_employee_id(7) == 7


def test_paginacao_padrao_e_limites():
    assert parse_page_params({}) == {'limit': PAGE_DEFAULT, 'cursor': None}
    assert parse_page_params({'limit': ['1']})['limit'] == 1
    assert parse_page_params({'limit': [str(PAGE_MAX)]})['limit'] == PAGE_MAX


@pytest.mark.parametrize('query', [
    {'limit': ['0']}, {'limit': [str(PAGE_MAX + 1)]}, {'limit': ['-1']}, {'limit': ['10.5']},
    {'limit': ['abc']}, {'limit': ['10', '20']}, {'cursor': ['%%%']}, {'cursor': ['a' * 300]},
    {'cursor': ['eyJ4IjoxfQ']},  # JSON válido, chaves erradas
])
def test_paginacao_invalida_nao_e_corrigida_silenciosamente(query):
    with pytest.raises(ContractError) as exc:
        parse_page_params(query)
    assert exc.value.code == 'INVALID_PAGINATION'


def test_cursor_ida_e_volta():
    cursor = encode_cursor('2026-11-09', 77)
    assert decode_cursor(cursor) == ('2026-11-09', 77)
    assert parse_page_params({'cursor': [cursor]})['cursor'] == ('2026-11-09', 77)


@pytest.mark.parametrize('sort_value,row_id', [('ontem', 1), ('2026-01-01', 0), ('2026-01-01', True)])
def test_cursor_recusa_valores_invalidos(sort_value, row_id):
    with pytest.raises(ValueError):
        encode_cursor(sort_value, row_id)


# ── Envelope ─────────────────────────────────────────────────────────────────

def test_envelope_de_sucesso():
    assert success_envelope({'x': 1}) == {'ok': True, 'data': {'x': 1}}
    assert success_envelope([], limit=20, next_cursor=None) == {
        'ok': True, 'data': [], 'page': {'limit': 20, 'next_cursor': None},
    }


@pytest.mark.parametrize('code', sorted(contract.ERRORS))
def test_envelope_de_erro_so_tem_codigo_e_mensagem_generica(code):
    status, body = error_envelope(ContractError(code))
    assert status == contract.ERRORS[code][0]
    assert body == {'ok': False, 'error': {'code': code, 'message': contract.ERRORS[code][1]}}


def test_codigo_de_erro_desconhecido_e_bug_de_programacao():
    # O construtor recusa o código antes do raise (CodeQL: exceção sempre lançada).
    with pytest.raises(ValueError, match='código de erro desconhecido'):
        raise ContractError('QUALQUER')


# ── Limites arquiteturais ────────────────────────────────────────────────────

_SQL_WRITE = re.compile(r'\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|ALTER\s+TABLE|CREATE\s+TABLE|DROP\s+TABLE)\b', re.IGNORECASE)


def _package_sources():
    return sorted(PACKAGE.rglob('*.py'))


def test_pacote_e_somente_leitura():
    for path in _package_sources():
        text = path.read_text(encoding='utf-8')
        assert not _SQL_WRITE.search(text), f'{path.name} escreve no banco'
        assert '.commit(' not in text, f'{path.name} faz commit'


def test_pacote_nao_depende_de_compras():
    """Acoplamento: a Ficha só poderá LER Compras por uma API de leitura
    dedicada (F5); até lá, nenhuma importação do domínio de Compras."""
    for path in _package_sources():
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            for name in names:
                assert not name.startswith('modules.purchases'), f'{path.name} importa {name}'


def test_f0_nao_expoe_rota():
    assert not (PACKAGE / 'routes.py').exists(), 'rotas da Ficha entram a partir da F1'
    app_source = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert 'employee_ppe_360' not in app_source
    assert 'ppe-360' not in app_source


def test_contrato_documentado():
    doc = ROOT / 'docs' / 'FICHA_360_F0_CONTRATOS.md'
    assert doc.exists()
    text = doc.read_text(encoding='utf-8')
    for code in contract.ERRORS:
        assert code in text, f'{code} não documentado'
    assert os.path.basename(__file__) in text


def test_mensagens_do_contrato_estao_nos_5_catalogos():
    """As mensagens que chegam ao cliente são traduzidas pelo mecanismo oficial
    (describeApiError casa o texto pt-BR com apiErrors.messages)."""
    import importlib.util
    import json

    spec = importlib.util.spec_from_file_location('inv', ROOT / 'scripts/i18n/inventory_backend_errors.py')
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    cats = {loc: json.loads((ROOT / 'static/i18n' / f'{loc}.json').read_text(encoding='utf-8'))
            for loc in ('pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO')}
    for _status, message in contract.ERRORS.values():
        leaf = inv.key_for(message).split('.')[-1]
        assert cats['pt-BR']['apiErrors']['messages'][leaf] == message
        for loc in ('en-GB', 'es-ES', 'fr-FR', 'nb-NO'):
            translated = cats[loc]['apiErrors']['messages'][leaf]
            assert translated and translated != message, f'{loc}: {message}'
