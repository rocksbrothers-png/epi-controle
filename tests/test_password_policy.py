"""Política de senha temporária (#909).

Um admin provisiona um usuário com senha temporária. A UI diz que é
temporária. Sem estes testes — e sem o backend que eles cobrem — ela é
**permanente**: o campo nunca chega ao cliente, e o guard de troca obrigatória
nunca dispara.

Este repositório tinha a UI e o cliente Flutter, mas nenhuma linha de backend.
A cobertura aqui é do porte: as funções da política e, principalmente, o
**cabeamento** — provisionar marca, trocar limpa, login informa. Testar só os
helpers deixaria passar exatamente o defeito que a #909 descreve, que é de
integração, não de lógica.

**Limitação conhecida, registrada de propósito:** estes testes usam conexão
falsa. Eles provam que as peças estão ligadas, não que o fluxo ponta a ponta
funciona contra um banco real — e não cobrem o bypass de quem já tem um token
válido com `must_change_password = 1`, porque esse bloqueio ainda não existe
(nem aqui, nem no repositório principal). Ver o PR de endurecimento.
"""

from datetime import datetime, timedelta

import modules.auth.service as auth_svc
import modules.users.service as users_svc
from epi_backend.config import UTC


# ── Fakes de conexão ─────────────────────────────────────────────────────────

class _FakeConn:
    """Conexão mínima: guarda linhas de users por id para as políticas."""

    def __init__(self, rows):
        self._rows = rows  # {user_id: {col: value}}
        self.updates = []

    def execute(self, sql, params=()):
        low = sql.lower().strip()
        if low.startswith('select must_change_password'):
            uid = int(params[0])
            row = self._rows.get(uid)
            return _Cur([row] if row else [])
        if low.startswith('update users set must_change_password = 1'):
            self.updates.append(('mark', params))
            return _Cur([])
        if low.startswith("update users set must_change_password = 0"):
            self.updates.append(('clear', params))
            return _Cur([])
        if low.startswith('update users set password'):
            self.updates.append(('password', params))
            return _Cur([])
        raise AssertionError(f'SQL inesperado: {sql}')

    def rollback(self):
        pass


class _Cur:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


# ── Leitura da política ──────────────────────────────────────────────────────

def test_policy_active_and_not_expired():
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    conn = _FakeConn({5: {'must_change_password': 1, 'password_expires_at': future}})
    policy = auth_svc.get_user_password_policy(conn, 5)
    assert policy == {'must_change': True, 'expired': False}


def test_policy_expired():
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    conn = _FakeConn({5: {'must_change_password': 1, 'password_expires_at': past}})
    policy = auth_svc.get_user_password_policy(conn, 5)
    assert policy['must_change'] is True
    assert policy['expired'] is True


def test_existing_user_without_flag_is_never_blocked():
    # A migração não pode trancar quem já usa o sistema: default 0 = fora da
    # exigência.
    conn = _FakeConn({9: {'must_change_password': 0, 'password_expires_at': ''}})
    policy = auth_svc.get_user_password_policy(conn, 9)
    assert policy == {'must_change': False, 'expired': False}


def test_policy_tolerates_missing_columns():
    # Base pré-migração: a política fica inativa em vez de derrubar o login.
    class _Broken:
        def execute(self, *a, **k):
            raise Exception('column "must_change_password" does not exist')

        def rollback(self):
            pass

    policy = auth_svc.get_user_password_policy(_Broken(), 1)
    assert policy == {'must_change': False, 'expired': False}


def test_sem_data_de_expiracao_a_troca_segue_obrigatoria():
    # `must_change` e `expired` são independentes: sem prazo, a senha não
    # expira, mas a troca continua exigida.
    conn = _FakeConn({3: {'must_change_password': 1, 'password_expires_at': ''}})
    assert auth_svc.get_user_password_policy(conn, 3) == {
        'must_change': True, 'expired': False,
    }


def test_data_de_expiracao_ilegivel_nao_bloqueia_o_login():
    # Prazo corrompido não pode virar bloqueio: o usuário ficaria sem entrar e
    # sem meio de resolver.
    conn = _FakeConn({3: {'must_change_password': 1, 'password_expires_at': 'nao-e-data'}})
    assert auth_svc.get_user_password_policy(conn, 3)['expired'] is False


# ── Limpeza após a troca ─────────────────────────────────────────────────────

def test_update_password_clears_policy():
    conn = _FakeConn({7: {'must_change_password': 1, 'password_expires_at': 'x'}})
    auth_svc.update_user_password(conn, 7, 'newhash')
    kinds = [u[0] for u in conn.updates]
    assert 'password' in kinds and 'clear' in kinds


def test_a_limpeza_acontece_junto_com_a_troca_e_nao_antes():
    # Se a flag fosse zerada antes de gravar a senha e a gravação falhasse, o
    # usuário ficaria sem a exigência E com a senha temporária.
    conn = _FakeConn({7: {'must_change_password': 1, 'password_expires_at': 'x'}})
    auth_svc.update_user_password(conn, 7, 'newhash')
    kinds = [u[0] for u in conn.updates]
    assert kinds.index('password') < kinds.index('clear')


# ── Marcação ao provisionar ──────────────────────────────────────────────────

def test_o_prazo_padrao_e_a_janela_configurada():
    assert users_svc.TEMP_PASSWORD_TTL_DAYS == 7
    agora = datetime.now(UTC)
    prazo = datetime.fromisoformat(users_svc.temp_password_expiry_iso(now=agora))
    assert (prazo - agora).days == 7


def test_mark_temp_password_grava_flag_e_prazo():
    conn = _FakeConn({})
    users_svc.mark_temp_password(conn, 11, '2030-01-01T00:00:00+00:00')
    assert conn.updates == [('mark', ('2030-01-01T00:00:00+00:00', 11))]


def test_marcacao_tolera_base_pre_migracao():
    # Mesma tolerância da leitura: a criação do usuário não pode quebrar porque
    # a coluna ainda não existe.
    class _Broken:
        def execute(self, *a, **k):
            raise Exception('column "must_change_password" does not exist')

        def rollback(self):
            pass

    users_svc.mark_temp_password(_Broken(), 1, 'x')  # não levanta


# ── Cabeamento: é aqui que o defeito da #909 vivia ───────────────────────────

def test_criar_usuario_marca_a_senha_como_temporaria():
    # O teste que faltava. As funções da política podiam estar todas corretas e
    # o defeito persistiria, porque ninguém as chamava no provisionamento.
    import pathlib
    fonte = pathlib.Path(users_svc.__file__).read_text(encoding='utf-8')
    inicio = fonte.index('def create_user(')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    assert 'mark_temp_password(connection, new_user_id, temp_password_expiry_iso())' in corpo, \
        'create_user não marca a senha provisionada como temporária'
    assert 'cursor.lastrowid' in corpo, \
        'sem o id do usuário recém-criado não há como marcar a linha certa'


def test_reset_de_senha_por_admin_tambem_marca():
    import pathlib
    fonte = pathlib.Path(users_svc.__file__).read_text(encoding='utf-8')
    inicio = fonte.index('def update_user(')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    # Só quando há senha nova: editar nome ou papel não pode exigir troca.
    #
    # A asserção precisa ser sobre a SEQUÊNCIA guarda→chamada, não sobre a
    # presença de `if incoming_password:`. Essa linha aparece duas vezes em
    # `update_user` — a primeira decide o hash da senha —, então procurá-la
    # solta passa mesmo com a marcação incondicional. Foi o que a sabotagem
    # mostrou: removi o guarda da marcação e o teste continuou verde.
    assert (
        '    if incoming_password:\n'
        '        mark_temp_password(connection, user_id, temp_password_expiry_iso())'
    ) in corpo, 'a marcação precisa estar DENTRO do guarda de senha nova'


def test_o_login_informa_o_estado_ao_cliente():
    # O cliente Flutter lê `must_change_password`; o web legado já consumia
    # `require_password_change`. As duas chaves precisam sair do login, senão o
    # guard de troca obrigatória nunca dispara — que era exatamente o defeito.
    import pathlib
    fonte = pathlib.Path(auth_svc.__file__).read_text(encoding='utf-8')
    inicio = fonte.index('def authenticate_login(')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    assert "'must_change_password': bool(password_policy['must_change'])" in corpo
    assert "'require_password_change': bool(password_policy['must_change'])" in corpo
    assert "user_data['must_change_password']" in corpo


def test_o_login_bloqueia_senha_temporaria_expirada():
    import pathlib
    fonte = pathlib.Path(auth_svc.__file__).read_text(encoding='utf-8')
    inicio = fonte.index('def authenticate_login(')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    assert "password_policy['must_change'] and password_policy['expired']" in corpo
    assert 'TEMP_PASSWORD_EXPIRED' in corpo


def test_o_refresh_nao_devolve_as_chaves_da_politica():
    # `refresh_access_token` tem um `return` quase idêntico ao do login. Uma
    # substituição desatenta acrescentaria as chaves lá também, e o cliente
    # passaria a reavaliar a política a cada renovação de token, com um valor
    # que o refresh não apurou.
    import pathlib
    fonte = pathlib.Path(auth_svc.__file__).read_text(encoding='utf-8')
    inicio = fonte.index('def refresh_access_token(')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    assert 'must_change_password' not in corpo
    assert 'require_password_change' not in corpo


# ── Schema e migration ───────────────────────────────────────────────────────

def test_as_colunas_estao_declaradas_no_schema():
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent
    schema = (raiz / 'core/schema.py').read_text(encoding='utf-8')
    assert "('must_change_password', 'INTEGER NOT NULL DEFAULT 0')" in schema
    assert "('password_expires_at', 'TEXT')" in schema


def test_a_migration_existe_e_e_idempotente():
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent
    sql = (raiz / 'supabase/migrations/20260715000000_user_password_policy.sql').read_text(encoding='utf-8')
    # Contar sobre os ALTER, não sobre o arquivo: o cabeçalho do .sql explica
    # que a migration é idempotente e CITA `ADD COLUMN IF NOT EXISTS`. Contar
    # o arquivo inteiro somaria a prosa ao código.
    alteracoes = [
        linha for linha in sql.split('\n')
        if linha.strip().upper().startswith('ALTER TABLE')
    ]
    assert len(alteracoes) == 2, f'esperadas 2 alterações, achei {len(alteracoes)}'
    assert all('ADD COLUMN IF NOT EXISTS' in linha for linha in alteracoes), \
        'sem IF NOT EXISTS a migration falha ao rodar duas vezes'
    assert 'DEFAULT 0' in sql, \
        'sem default 0 a migração exigiria troca de senha de todo mundo'
    assert (raiz / 'epi_backend/migrations/014_user_password_policy.py').exists()
