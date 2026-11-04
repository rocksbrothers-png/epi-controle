"""Segurança: o 503 do bootstrap, /health e o 500 genérico não expõem detalhe interno.

O 503 e /health são respondidos ANTES da autenticação. Antes, `details.detail`
e `error_message` devolviam `str(exc)` da falha de banco/migração (host, usuário,
SQL e, com DATABASE_URL malformada, a própria URL de conexão). O contrato
público — status, `code`, `kind`, chaves do JSON — continua igual; só o texto
livre vira uma frase fixa. O erro bruto segue no estado interno e no log, com a
senha redigida.
"""
import io
import json
import sqlite3
from contextlib import redirect_stdout

import app
from epi_backend import bootstrap
from epi_backend.http_utils import (
    PUBLIC_INTERNAL_ERROR,
    public_error_message,
    redact_secrets,
    structured_log,
)

# Valores fictícios, só para provar a redação.
SEGREDO = 'SenhaFicticia123'
HOST = 'db-interno.exemplo.invalid'
BRUTO = (f'invalid dsn: missing "=" after "postgresql://usuario:{SEGREDO}@{HOST}:5432/base" '
         f'connection to server at "{HOST}" (10.0.0.9), port 5432 failed: '
         'FATAL: password authentication failed for user "usuario"')


class _Handler:
    command = 'GET'
    path = '/api/users'


def _falha():
    bootstrap._set_bootstrap_state(ready=False, error_code='DB_CONNECTION_FAILED', error_kind='driver_unexpected',
                                   error_message=BRUTO, started_at='2026-11-04T00:00:00+00:00',
                                   completed_at='2026-11-04T00:00:05+00:00')


def _limpa():
    bootstrap._set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                                   started_at='', completed_at='')


def _sem_interno(texto):
    for proibido in (SEGREDO, HOST, '10.0.0.9', 'postgresql://', 'usuario', 'FATAL'):
        assert proibido not in texto, proibido


def test_503_do_gate_nao_expoe_detalhe_e_preserva_contrato(monkeypatch):
    _falha()
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))
    try:
        assert app.EpiHandler._require_bootstrap_ready(_Handler(), '/api/users') is None
    finally:
        _limpa()
    assert capturado['status'] == 503
    erro = capturado['payload']['error']
    assert capturado['payload']['ok'] is False
    assert erro['code'] == 'DB_CONNECTION_FAILED'
    assert erro['message'] == 'Serviço indisponível: bootstrap do banco pendente ou com falha.'
    assert set(erro['details']) == {'kind', 'detail', 'ready', 'started_at', 'completed_at'}
    assert erro['details']['kind'] == 'driver_unexpected'
    assert erro['details']['detail'] == bootstrap.PUBLIC_BOOTSTRAP_FAILED
    _sem_interno(json.dumps(capturado['payload'], ensure_ascii=False))
    # O estado interno guarda o erro bruto para diagnóstico.


def test_503_pendente_mantem_texto_anterior(monkeypatch):
    _limpa()
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))
    app.EpiHandler._require_bootstrap_ready(_Handler(), '/api/users')
    assert capturado['payload']['error']['details']['detail'] == 'A migração/validação de schema ainda não concluiu.'


def test_health_e_ready_nao_expoem_detalhe():
    _falha()
    try:
        for probe in ('live', 'ready'):
            status, payload = bootstrap.runtime_probe_response(probe)
            assert status == (200 if probe == 'live' else 503)
            assert payload['error_code'] == 'DB_CONNECTION_FAILED'
            assert payload['error_kind'] == 'driver_unexpected'
            assert payload['error_message'] == bootstrap.PUBLIC_BOOTSTRAP_FAILED
            _sem_interno(json.dumps(payload, ensure_ascii=False))
        assert bootstrap._get_bootstrap_state()['error_message'] == BRUTO
    finally:
        _limpa()


def test_health_saudavel_continua_sem_mensagem():
    bootstrap._set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='')
    try:
        status, payload = bootstrap.runtime_probe_response('ready')
        assert status == 200 and payload['error_message'] == ''
    finally:
        _limpa()


def test_500_de_banco_vira_mensagem_fixa():
    assert public_error_message(sqlite3.OperationalError('no such table: users')) == PUBLIC_INTERNAL_ERROR
    assert public_error_message(sqlite3.IntegrityError('UNIQUE constraint failed: users.email')) == PUBLIC_INTERNAL_ERROR
    assert public_error_message(RuntimeError(BRUTO)) == PUBLIC_INTERNAL_ERROR

    class SchemaMigrationError(Exception):
        pass
    assert public_error_message(SchemaMigrationError('Falha em migração x: y')) == PUBLIC_INTERNAL_ERROR


def test_500_de_aplicacao_mantem_a_mensagem():
    texto = 'Falha no OCR para os idiomas configurados: tesseract ausente'
    assert public_error_message(RuntimeError(texto)) == texto


def test_todos_os_500_genericos_usam_a_mensagem_publica():
    with open(app.__file__, encoding='utf-8') as arquivo:
        fonte = arquivo.read()
    assert "send_json(self, 500, {'error': str(exc)})" not in fonte
    assert fonte.count("send_json(self, 500, {'error': public_error_message(exc)})") == 4


def test_log_mantem_diagnostico_e_redige_a_senha():
    saida = io.StringIO()
    with redirect_stdout(saida):
        structured_log('error', 'db.init_failed_gracefully', error=BRUTO)
    linha = saida.getvalue()
    assert SEGREDO not in linha
    assert HOST in linha  # diagnóstico preservado para o operador
    assert redact_secrets('host=x password=abc user=y') == 'host=x password=*** user=y'
    assert redact_secrets('postgres://u:p@h/db') == 'postgres://u:***@h/db'
