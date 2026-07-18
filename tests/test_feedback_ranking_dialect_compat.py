"""Regressão: os rankings de avaliação precisam rodar em SQLite E PostgreSQL.

Dois bugs reais que só apareceram em produção (Postgres), mascarados enquanto
o boot falhava:

1. fetch_suggestion_ranking selecionava `f.epi_name` — coluna que NÃO existe em
   epi_feedbacks (o nome do EPI vem de epis via epi_id). Resultado: 500
   "no such column"/"column does not exist" em qualquer banco assim que a aba
   Ranking era aberta.
2. Ambas as queries agrupam por expressão/coluna e selecionam colunas nuas de
   tabelas juntadas. O SQLite tolera; o PostgreSQL exige que toda coluna do
   SELECT esteja no GROUP BY ou sob agregação, senão 500.

O schema deste teste reproduz o de produção: epi_feedbacks SEM coluna epi_name.
"""

import sqlite3

from modules.feedback.service import compute_epi_evaluation_status, fetch_suggestion_ranking

ACTOR = {'id': 10, 'role': 'general_admin', 'company_id': 1, 'full_name': 'Admin'}


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        '''
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, ca TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '', sector TEXT DEFAULT '', company_id INTEGER DEFAULT 1,
            evaluation_status TEXT DEFAULT 'normal', updated_at TEXT DEFAULT '');
        -- epi_feedbacks propositalmente SEM coluna epi_name (fiel à produção)
        CREATE TABLE epi_feedbacks (id INTEGER PRIMARY KEY, company_id INTEGER, epi_id INTEGER,
            suggested_new_epi_name TEXT DEFAULT '', epi_rank TEXT DEFAULT '',
            feedback_subtype TEXT DEFAULT '', type TEXT DEFAULT '',
            manager_eval_status TEXT DEFAULT '', status TEXT DEFAULT '',
            employee_portal_status TEXT DEFAULT '', employee_portal_message TEXT DEFAULT '',
            comfort_rating INT DEFAULT 0, quality_rating INT DEFAULT 0,
            adequacy_rating INT DEFAULT 0, performance_rating INT DEFAULT 0,
            created_at TEXT DEFAULT '2026-01-01');
        CREATE TABLE epi_evaluation_summary (id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INT, epi_id INT, epi_name TEXT, total_avaliacoes INT, total_reclamacoes INT,
            total_elogios INT, total_sugestoes INT, avg_comfort REAL, avg_quality REAL,
            avg_adequacy REAL, avg_performance REAL, score REAL, evaluation_status TEXT,
            rank_excelente INT DEFAULT 0, rank_otimo INT DEFAULT 0, rank_muito_bom INT DEFAULT 0,
            rank_ruim INT DEFAULT 0, rank_muito_ruim INT DEFAULT 0, rank_pessimo INT DEFAULT 0,
            rank_excelente_sug INT DEFAULT 0, rank_otima_sug INT DEFAULT 0,
            rank_muito_boa_sug INT DEFAULT 0, rank_pessima_sug INT DEFAULT 0,
            rank_muito_ruim_sug INT DEFAULT 0, rank_ruim_sug INT DEFAULT 0,
            last_computed_at TEXT, created_at TEXT, updated_at TEXT, UNIQUE(company_id, epi_id));
        INSERT INTO epis (id, name) VALUES (5, 'Luva Atual');
        INSERT INTO epi_feedbacks (id, company_id, epi_id, suggested_new_epi_name, epi_rank,
            feedback_subtype, type, manager_eval_status, created_at)
            VALUES (1, 1, 5, 'Luva Nova X', 'excelente_sug', 'sugestao_nova', 'sugestao', 'validado', '2026-01-01');
        INSERT INTO epi_feedbacks (id, company_id, epi_id, suggested_new_epi_name, epi_rank,
            feedback_subtype, type, manager_eval_status, comfort_rating, quality_rating,
            adequacy_rating, performance_rating, created_at)
            VALUES (2, 1, 5, 'Capacete Y', 'otima_sug', 'elogio', 'elogio', 'validado', 5, 5, 5, 5, '2026-01-02');
        '''
    )
    return connection


def test_suggestion_ranking_resolves_reference_epi_via_join():
    connection = _conn()
    rows = fetch_suggestion_ranking(connection, ACTOR)
    assert rows, 'ranking de sugestões não pode vir vazio quando há sugestão validada'
    row = rows[0]
    assert row['sugestao_nome'] == 'Luva Nova X'
    # epi_referencia vem de epis.name via JOIN (epi_feedbacks não tem epi_name)
    assert row['epi_referencia'] == 'Luva Atual'
    assert row['total_avaliacoes'] == 1


def test_compute_evaluation_status_runs_without_dialect_error():
    connection = _conn()
    result = compute_epi_evaluation_status(connection, ACTOR)
    assert result['ok'] is True
    assert len(result['items']) == 1
    assert result['items'][0]['epi_name'] == 'Luva Atual'
