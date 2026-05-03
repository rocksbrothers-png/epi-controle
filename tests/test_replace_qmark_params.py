"""Testes unitários para PostgresConnectionWrapper._replace_qmark_params."""
from epi_backend.db import PostgresConnectionWrapper

replace = PostgresConnectionWrapper._replace_qmark_params


def test_question_mark_becomes_percent_s():
    assert replace("SELECT * FROM t WHERE id = ?") == "SELECT * FROM t WHERE id = %s"


def test_multiple_question_marks():
    assert replace("INSERT INTO t (a,b) VALUES (?,?)") == "INSERT INTO t (a,b) VALUES (%s,%s)"


def test_bare_percent_escaped_for_psycopg2():
    # %I e %L são especificadores do format() do PostgreSQL — devem virar %%
    sql = "EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl)"
    result = replace(sql)
    assert "%%I" in result
    assert "%I" not in result.replace("%%I", "")


def test_percent_in_like_pattern_escaped():
    sql = "WHERE name ILIKE 'foo%'"
    result = replace(sql)
    assert "%%'" in result


def test_percent_bind_param_via_qmark_not_double_escaped():
    # ? vira %s — não deve virar %%s
    sql = "WHERE name ILIKE ?"
    result = replace(sql)
    assert result == "WHERE name ILIKE %s"


def test_question_mark_inside_single_quotes_preserved():
    assert replace("WHERE val = '?'") == "WHERE val = '?'"


def test_percent_and_qmark_combined():
    sql = "WHERE pg_get_constraintdef(c.oid) ILIKE ? AND schema = 'public%'"
    result = replace(sql)
    assert "%s" in result
    assert "public%%" in result
