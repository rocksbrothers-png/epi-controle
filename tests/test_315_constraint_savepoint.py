"""#315 — o `ADD CONSTRAINT` não pode mais envenenar a transação.

Aqui ficam os gates que NÃO precisam de PostgreSQL: dialeto SQLite e o gate
estático. As provas de comportamento transacional vivem em
`tests_postgres/test_315_constraint_savepoint_postgres.py`, porque dependem de
semântica de transação abortada que o SQLite não replica.

O defeito, medido em produção e reproduzido em PostgreSQL 16.13: em banco já
provisionado o `ALTER TABLE ... ADD CONSTRAINT` falha SEMPRE (o PostgreSQL não
tem `ADD CONSTRAINT IF NOT EXISTS`), o `except` engolia sem `rollback()`, a
transação ficava `INERROR`, o `CREATE INDEX` seguinte era recusado e o
`connection.commit()` do runner descartava a transação inteira **sem levantar
exceção** — ainda logando `db.ensure_fn_ok`.
"""
import ast
import pathlib

import pytest

from core import schema

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / 'core' / 'schema.py'


class _ConexaoSqliteFalsa:
    """Basta o módulo/classe conterem 'sqlite' — é o critério de `_is_sqlite_connection`."""

    __module__ = 'sqlite3.dbapi2'

    def __init__(self) -> None:
        self.sql = []

    def execute(self, query, params=None):
        self.sql.append(str(query))
        raise AssertionError('SQLite não deveria receber SQL de constraint')


class _Recorder:
    def __init__(self) -> None:
        self.eventos = []

    def __call__(self, nivel, evento, **campos):
        self.eventos.append((nivel, evento, campos))

    def nomes(self):
        return [e for _, e, _ in self.eventos]


@pytest.fixture
def logs(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(schema, 'structured_log', rec)
    return rec


# ═══════════════════════════════════════════════════════════════════════════
# Dialeto: SQLite não tem ADD CONSTRAINT — não se tenta e não se engole
# ═══════════════════════════════════════════════════════════════════════════

def test_sqlite_nao_emite_add_constraint(logs):
    conexao = _ConexaoSqliteFalsa()
    resultado = schema._add_constraint_protegido(
        conexao, 'deliveries', 'fk_deliveries_migration_job', 'ALTER TABLE ...')

    assert resultado is False
    assert conexao.sql == [], \
        ('SQLite recebeu SQL de constraint: o dialeto não suporta '
         '`ALTER TABLE ADD CONSTRAINT` e tentar-e-engolir foi justamente o '
         'formato que a #315 elimina')
    assert 'db.constraint_unsupported_dialect' in logs.nomes()


def test_nome_de_constraint_invalido_nao_vira_sql():
    """O nome entra numa f-string de SAVEPOINT. Só identificador passa."""
    for nome in ('fk; DROP TABLE deliveries', 'fk deliveries', '', '1fk'):
        with pytest.raises(schema.SchemaMigrationError):
            schema._add_constraint_protegido(
                object(), 'deliveries', nome, 'ALTER TABLE ...')


# ═══════════════════════════════════════════════════════════════════════════
# Gate estático — ESTREITO, casa só o formato comprovado
# ═══════════════════════════════════════════════════════════════════════════

def _blocos_perigosos(fonte: str) -> list:
    """`try` que executa `ADD CONSTRAINT`, engole tudo, e não usa SAVEPOINT.

    Estreito de propósito. NÃO casa `CREATE ... IF NOT EXISTS` nem DML: os
    demais candidatos do inventário da #315 seguem sendo candidatos a
    auditoria, e uma regra genérica os transformaria em defeitos por
    associação — exatamente o que o contrato proíbe.
    """
    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Try):
            continue
        literais = [n.value for n in ast.walk(no)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if not any('ADD CONSTRAINT' in s.upper() for s in literais):
            continue
        if any('SAVEPOINT' in s.upper() for s in literais):
            continue
        if any(isinstance(n, ast.Raise) for h in no.handlers for n in ast.walk(h)):
            continue
        achados.append(no.lineno)
    return achados


_FIXTURE_ANTIGA = '''
def ensure_algo(connection):
    try:
        connection.execute(
            'ALTER TABLE deliveries ADD CONSTRAINT fk_x '
            'FOREIGN KEY (a) REFERENCES b(id)'
        )
        connection.commit()
    except Exception as _e:
        structured_log('info', 'db.constraint_skip', error=str(_e))
    connection.execute('CREATE INDEX IF NOT EXISTS idx_y ON deliveries (a)')
'''


def test_o_matcher_nao_e_vacuo():
    """Regra estática que não casa nada é indistinguível de regra quebrada."""
    assert len(_blocos_perigosos(_FIXTURE_ANTIGA)) == 1, \
        'o matcher deixou de reconhecer o formato exato que a #315 corrigiu'


def test_nenhum_add_constraint_desprotegido_no_schema():
    perigosos = _blocos_perigosos(ARQUIVO.read_text(encoding='utf-8'))
    assert perigosos == [], (
        f'linhas {perigosos}: `ADD CONSTRAINT` dentro de try que engole e não '
        f'usa SAVEPOINT. Em banco provisionado isso falha sempre, aborta a '
        f'transação e faz o commit do runner descartar tudo em silêncio.')


def test_o_matcher_nao_acusa_os_demais_candidatos():
    """Guarda contra alargar a regra e transformar os 88 em defeitos."""
    guardados = '''
def ensure_x(connection):
    try:
        connection.execute('CREATE INDEX IF NOT EXISTS idx_a ON t (c)')
    except Exception as _e:
        structured_log('warning', 'db.index_skip', error=str(_e))
    try:
        connection.execute('INSERT INTO app_meta (key, value) VALUES (?, ?) '
                           'ON CONFLICT (key) DO NOTHING', ('k', 'v'))
    except Exception as _e:
        structured_log('warning', 'db.meta_skip', error=str(_e))
'''
    assert _blocos_perigosos(guardados) == [], \
        ('o matcher passou a acusar DDL guardado/DML: isso transformaria o '
         'inventário inteiro da #315 em defeito por associação')
