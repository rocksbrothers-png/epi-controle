"""Rotas de autenticação."""
import hmac
import os
import threading as _threading
import traceback
from contextlib import closing

from core.database import get_connection
from core.rate_limit import get_client_ip, login_limiter, recovery_limiter
from core.repository import authorize_action
from core.security import (
    AuthenticationError,
    hash_password,
    is_bcrypt_hash,
    parse_bearer_token,
    resolve_actor_user_id,
    validate_password_strength,
    verify_password,
)
from epi_backend.config import APP_ENV, PASSWORD_RECOVERY_KEY
from epi_backend.http_utils import (
    redact_sensitive_query,
    require_fields,
    send_api_response,
    send_json,
    structured_log,
)
from core.repository import get_user_by_id
from core.permissions import PERMISSIONS
from modules.auth.service import (
    _hash_ficticio,
    authenticate_login,
    disable_user_totp,
    enable_user_totp,
    get_user_totp_state,
    setup_user_totp,
    generate_user_recovery_token,
    get_user_by_username,
    refresh_access_token,
    require_actor,
    send_recovery_email_smtp,
    update_user_password,
    validate_and_clear_recovery_token,
)


# ── Não enumeração na recuperação de senha ───────────────────────────────────
#
# Dois endpoints, dois contratos. `MSG_RECUPERACAO_SOLICITADA` responde ao
# PEDIDO de instruções; `MSG_RECUPERACAO_RECUSADA` responde à TENTATIVA de
# redefinir com chave. A segunda não pode ser a primeira: quem chama
# `/api/recover-password` está enviando uma senha nova, não pedindo instruções.
#
# Nos dois casos a resposta é única para todo o espaço de falha de formato
# válido, e a distinção que a operação precisa fica no log.
MSG_RECUPERACAO_SOLICITADA = (
    'Se os dados informados estiverem cadastrados, você receberá as instruções '
    'para recuperação.'
)
MSG_RECUPERACAO_RECUSADA = (
    'Não foi possível concluir a recuperação. Verifique os dados informados e '
    'tente novamente.'
)
CODIGO_RECUPERACAO_RECUSADA = 'RECOVERY_FAILED'


def _recusa_de_recuperacao(handler, username, motivo):
    """A ÚNICA resposta pública para falha na redefinição com chave.

    Antes eram quatro respostas distinguíveis, e duas delas se separavam só
    pelo STATUS: `sem token + chave global errada` devolvia 403 e `com token +
    chave errada` devolvia 400, com a mesma mensagem. O status sozinho já dizia
    se a conta tinha token próprio.
    """
    structured_log('warning', 'auth.recovery_failed', username=username, reason=motivo)
    return send_json(handler, 400, {
        'ok': False,
        'error': {'code': CODIGO_RECUPERACAO_RECUSADA, 'message': MSG_RECUPERACAO_RECUSADA},
    })


def handle_post_login(handler, parsed, payload, match):
    structured_log(
        'info', 'auth.login.entry',
        path=parsed.path,
        raw_path=redact_sensitive_query(getattr(handler, 'path', '')),
    )
    client_ip = get_client_ip(handler)
    if not login_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.login.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {
                'code': 'AUTH_RATE_LIMITED',
                'message': 'Muitas tentativas de login. Aguarde 1 minuto e tente novamente.',
            }
        })
    _bootstrap_state_fn = None
    try:
        from epi_backend.bootstrap import _get_bootstrap_state
        _bootstrap_state_fn = _get_bootstrap_state
    except Exception:
        pass

    if _bootstrap_state_fn is not None:
        try:
            _bs = _bootstrap_state_fn()
            structured_log(
                'info',
                'auth.login.bootstrap_state',
                ready=bool(_bs.get('ready')),
                error_code=str(_bs.get('error_code') or ''),
                error_kind=str(_bs.get('error_kind') or ''),
                error_message=str(_bs.get('error_message') or ''),
            )
        except Exception:
            pass

    _login_response = {'status': None, 'code': ''}

    def _login_send_json(h, status, response_payload):
        _login_response['status'] = int(status)
        parsed_payload = response_payload if isinstance(response_payload, dict) else {}
        if isinstance(parsed_payload.get('error'), dict):
            _login_response['code'] = str(parsed_payload.get('error', {}).get('code') or '')
        else:
            _login_response['code'] = str(parsed_payload.get('code') or '')
        structured_log(
            'info',
            'auth.login.response',
            status=_login_response['status'],
            code=_login_response['code'],
        )
        return send_json(h, status, response_payload)

    require_fields(payload, ['username', 'password'])
    try:
        with closing(get_connection()) as connection:
            response_payload, status_code, error_payload = authenticate_login(
                connection,
                payload.get('username', ''),
                payload.get('password', ''),
                totp_code=payload.get('totp_code'),
            )
        if error_payload:
            return _login_send_json(handler, status_code, error_payload)
        return _login_send_json(handler, status_code, response_payload)
    except Exception as exc:
        structured_log(
            'error',
            'auth.login.exception',
            error_type=type(exc).__name__,
            error=str(exc),
            path=parsed.path,
            stacktrace=traceback.format_exc(),
        )
        structured_log(
            'info',
            'auth.login.response',
            status=500,
            code='AUTH_LOGIN_RUNTIME_ERROR',
        )
        return send_json(
            handler,
            500,
            {
                'ok': False,
                'error': {
                    'code': 'AUTH_LOGIN_RUNTIME_ERROR',
                    'message': 'Falha interna ao processar login.',
                    'details': {'error_type': type(exc).__name__},
                },
            },
        )


# ── POST /api/recover-password ────────────────────────────────────────────────

def handle_post_recover_password(handler, parsed, payload, match):
    client_ip = get_client_ip(handler)
    if not recovery_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.recovery.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {
                'code': 'RECOVERY_RATE_LIMITED',
                'message': 'Muitas tentativas de recuperação. Aguarde 5 minutos e tente novamente.',
            }
        })
    require_fields(payload, ['username', 'new_password', 'recovery_key'])
    username = str(payload.get('username', '')).strip()
    new_password = validate_password_strength(payload.get('new_password', ''))
    provided_key = str(payload.get('recovery_key', '')).strip()
    with closing(get_connection()) as connection:
        user_ref = get_user_by_username(connection, username)
        token_hash_row = connection.execute(
            'SELECT recovery_token_hash FROM users WHERE id = ?', (user_ref['id'],)
        ).fetchone() if user_ref else None
        has_per_user_token = bool(token_hash_row and token_hash_row['recovery_token_hash'])
        try:
            if has_per_user_token:
                validate_and_clear_recovery_token(connection, username, provided_key)
            else:
                # Trabalho equivalente. O ramo do token por usuário paga um
                # `bcrypt`; sem isto, `usuário inexistente` e `conta sem token`
                # voltavam em ~0,03 ms contra ~268 ms, e a recusa uniforme seria
                # desfeita pelo relógio.
                verify_password(_hash_ficticio(), provided_key)
                if not user_ref:
                    raise ValueError('recovery_user_not_found')
                if not PASSWORD_RECOVERY_KEY:
                    raise ValueError('recovery_no_global_key')
                if not hmac.compare_digest(provided_key, PASSWORD_RECOVERY_KEY):
                    raise ValueError('recovery_global_key_mismatch')
        except (ValueError, PermissionError) as sinal:
            return _recusa_de_recuperacao(handler, username, str(sinal))
        update_user_password(connection, user_ref['id'], hash_password(new_password))
        connection.commit()
        structured_log('info', 'auth.password_recovered', username=username, user_id=user_ref['id'])
        return send_json(handler, 200, {'ok': True})


# ── POST /api/users/<id>/recovery-token ───────────────────────────────────────

def handle_post_user_recovery_token(handler, parsed, payload, match):
    user_id = int(match.group(1))
    actor_user_id = resolve_actor_user_id(handler, parsed, payload)
    with closing(get_connection()) as connection:
        from core.repository import authorize_action as _auth_action
        from core.auth import ensure_company_access as _ensure_company
        from core.roles import normalize_role_name as _norm_role
        actor = _auth_action(connection, actor_user_id, 'users:update')
        target = get_user_by_id(connection, user_id)
        if not target:
            raise ValueError('Usuário não encontrado.')
        actor_role = actor['role']
        target_role = _norm_role(target.get('role', ''))
        if actor_role == 'master_admin':
            if target_role == 'master_admin' and target['id'] != actor['id']:
                raise PermissionError('Administrador Master não pode gerar chave para outro Administrador Master.')
        elif actor_role == 'general_admin':
            allowed = ('registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee')
            if target_role not in allowed:
                raise PermissionError('Administrador Geral pode gerar chaves apenas para perfis inferiores da própria empresa.')
            _ensure_company(actor, target.get('company_id'))
        else:
            raise PermissionError('Somente Administrador Geral ou Master podem gerar chaves de recuperação.')
        token = generate_user_recovery_token(connection, user_id)
        connection.commit()
        structured_log('info', 'auth.recovery_token_generated', actor_id=actor['id'], target_user_id=user_id)
        return send_json(handler, 200, {'ok': True, 'token': token})


# ── POST /api/auth/request-email-recovery ─────────────────────────────────────

def _emitir_recuperacao_em_segundo_plano(user_id, email, username):
    """Gera o token e envia o e-mail FORA da linha da resposta.

    Duas razões, e as duas são de não enumeração:

    1. `generate_user_recovery_token` chama `hash_password`, que é `bcrypt`.
       Na linha da resposta isso custava ~268 ms para quem existe e ~0,09 ms
       para quem não existe — 5207×, medido. A mensagem já era genérica e o
       endpoint continuava respondendo a pergunta, pelo relógio.
    2. Uma falha de SMTP virava `400 'Falha ao enviar e-mail: <detalhe>'`, que
       só é alcançável para conta existente COM e-mail. Daqui ela não alcança
       o solicitante: é registrada e morre no log.

    Igualar os tempos pagando um `bcrypt` também no caminho de quem não existe
    resolveria o item 1 — e encareceria TODA requisição num endpoint que hoje
    não tem limitador. Tirar o trabalho da linha da resposta resolve sem esse
    custo: o solicitante paga um SELECT, exista ele ou não.

    Segue o precedente de thread daemon do `init_db` (`app.py`).
    """
    def _trabalho():
        # A decisão de enviar mora AQUI, não na linha da resposta. A thread sobe
        # dos dois jeitos: criar uma thread custa ~0,6 ms, e fazer isso só para
        # quem existe reabriria a diferença de tempo em escala menor — 11,8×,
        # medido depois da primeira versão desta correção.
        if not user_id or not email:
            structured_log('info', 'auth.recovery_email_skipped', username=username,
                           reason='user_not_found' if not user_id else 'user_without_email')
            return
        try:
            with closing(get_connection()) as conexao:
                token = generate_user_recovery_token(conexao, user_id)
                conexao.commit()
            send_recovery_email_smtp(email, username, token)
            structured_log('info', 'auth.recovery_email_sent', user_id=user_id, username=username)
        except Exception as exc:
            structured_log('error', 'auth.recovery_email_failed', username=username, error=str(exc))

    _threading.Thread(target=_trabalho, daemon=True,
                      name=f'recovery_email_{user_id or "none"}').start()


def handle_post_request_email_recovery(handler, parsed, payload, match):
    """Pede o token de recuperação por e-mail.

    A resposta é SEMPRE a mesma e sai SEMPRE pelo mesmo caminho: exista o
    usuário ou não, tenha ele e-mail ou não, funcione o SMTP ou não. O que
    varia é só o efeito interno — e o efeito interno não é observável daqui.
    """
    require_fields(payload, ['username'])
    username = str(payload.get('username', '')).strip()
    with closing(get_connection()) as connection:
        user_ref = get_user_by_username(connection, username)
        row = connection.execute(
            'SELECT id, username, email FROM users WHERE id = ?', (user_ref['id'],)
        ).fetchone() if user_ref else None
        # O e-mail sai para conta existente COM endereço, e só. O que muda
        # entre os casos é isso, e nada na resposta.
        _emitir_recuperacao_em_segundo_plano(
            row['id'] if row else None,
            row['email'] if row else None,
            row['username'] if row else username,
        )
    return send_json(handler, 200, {'ok': True, 'message': MSG_RECUPERACAO_SOLICITADA})


# ── POST /api/change-password ─────────────────────────────────────────────────

def handle_post_change_password(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'current_password', 'new_password'])
    with closing(get_connection()) as connection:
        actor_user_id = resolve_actor_user_id(handler, parsed, payload)
        user = get_user_by_id(connection, actor_user_id)
        if not user:
            raise ValueError('Usuário não encontrado.')
        current_password = str(payload.get('current_password', '')).strip()
        new_password_raw = str(payload.get('new_password', '')).strip()
        if not verify_password(user['password'], current_password):
            raise PermissionError('Senha atual incorreta.')
        new_hashed = hash_password(validate_password_strength(new_password_raw))
        update_user_password(connection, actor_user_id, new_hashed)
        connection.commit()
        structured_log('info', 'auth.password_changed', user_id=actor_user_id)
        return send_json(handler, 200, {'ok': True})


def handle_get_auth_diagnostics(handler, parsed, payload, match):
    from modules.auth.service import auth_diagnostics

    diagnostics_key = os.environ.get('AUTH_DIAGNOSTICS_KEY', '').strip()
    provided_key = str(handler.headers.get('X-Diagnostics-Key', '')).strip()
    has_diagnostics_key = bool(diagnostics_key and hmac.compare_digest(provided_key, diagnostics_key))
    is_production = APP_ENV in ('prod', 'production')
    if has_diagnostics_key or not is_production:
        return send_json(handler, 200, auth_diagnostics(public=False))

    try:
        with closing(get_connection()) as connection:
            authorize_action(connection, resolve_actor_user_id(handler, parsed), 'dashboard:view')
        return send_json(handler, 200, auth_diagnostics(public=False))
    except Exception:
        return send_json(handler, 200, auth_diagnostics(public=True))


# ── R0.5B SONDA TEMPORÁRIA DE IDENTIDADE DA ORIGEM — INÍCIO ─────────────────
#
# Responde P1–P4 da certificação de identidade (docs/R05B_IDENTIDADE_DA_ORIGEM.md).
# Sai do repositório quando a certificação fechar; o gate `R05B-7` reprova a
# suíte enquanto ela ficar depois disso.
def handle_get_origin_identity_diagnostics(handler, parsed, payload, match):
    from epi_backend.proxy_identity_probe import autorizado, medir

    # `send_json` não devolve nada, e `core/router.py` documenta que handler
    # retornando None é o caso normal — ele converte em HANDLED. Devolver o
    # resultado de `send_json` propagaria um valor sem significado.
    if not autorizado(handler):
        # 404 com o MESMO corpo de `app.not_found()`: um 403, ou um corpo
        # próprio, confirmaria a existência da sonda para quem sondasse.
        send_json(handler, 404, {'error': 'Rota não encontrada.'})
        return
    send_json(handler, 200, medir(handler))
# ── R0.5B SONDA TEMPORÁRIA DE IDENTIDADE DA ORIGEM — FIM ────────────────────


def handle_get_db_pool_status(handler, parsed, payload, match):
    from core.database import db_pool_status
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'dashboard:view')
        if actor.get('role') != 'master_admin':
            raise PermissionError('Somente Administrador Master pode consultar o status do pool.')
        return send_json(handler, 200, {'pool': db_pool_status()})


def handle_get_bootstrap(handler, parsed, payload, match):
    from epi_backend.http_utils import structured_log
    from modules.auth.service import build_bootstrap
    actor_user_id = None
    actor = None
    try:
        actor_user_id = resolve_actor_user_id(handler, parsed)
        with closing(get_connection()) as connection:
            actor = authorize_action(connection, actor_user_id, 'dashboard:view')
            structured_log('info', 'bootstrap.started', actor_user_id=actor_user_id, user_role=actor.get('role'), company_id=actor.get('company_id'), path=parsed.path)
            payload_data = build_bootstrap(connection, actor)
            structured_log('info', 'bootstrap.completed', actor_user_id=actor_user_id, user_role=actor.get('role'), company_id=actor.get('company_id'), path=parsed.path, degraded=bool(payload_data.get('degraded')), failed_sections=[item.get('section') for item in payload_data.get('bootstrap_warnings', [])])
            return send_json(handler, 200, {'ok': True, 'data': payload_data})
    except AuthenticationError as exc:
        # Token ausente/inválido/expirado → 401 (dispara o refresh no cliente).
        from epi_backend.http_utils import structured_log
        structured_log('warning', 'bootstrap.auth_failed', actor_user_id=actor_user_id, user_role=actor.get('role') if actor else '', company_id=actor.get('company_id') if actor else '', path=parsed.path, error=str(exc))
        send_json(handler, 401, {'error': str(exc)})
    except PermissionError as exc:
        # Usuário autenticado, mas sem permissão (dashboard:view) → 403.
        from epi_backend.http_utils import structured_log
        structured_log('warning', 'bootstrap.permission_denied', actor_user_id=actor_user_id, user_role=actor.get('role') if actor else '', company_id=actor.get('company_id') if actor else '', path=parsed.path, error=str(exc))
        send_json(handler, 403, {'error': str(exc)})


def handle_post_auth_refresh(handler, parsed, payload, match):
    """Reemite o access token a partir de um refresh token válido (stateless)."""
    client_ip = get_client_ip(handler)
    if not login_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.refresh.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {'code': 'AUTH_RATE_LIMITED', 'message': 'Muitas tentativas. Aguarde e tente novamente.'},
        })
    payload = payload or {}
    refresh_token = str(payload.get('refresh_token') or '').strip()
    if not refresh_token:
        try:
            refresh_token = parse_bearer_token(handler)
        except PermissionError:
            refresh_token = ''
    if not refresh_token:
        return send_json(handler, 400, {'error': 'Token de atualização ausente.', 'code': 'MISSING_REFRESH_TOKEN'})
    try:
        with closing(get_connection()) as connection:
            response_payload, status_code, error_payload = refresh_access_token(connection, refresh_token)
        if error_payload:
            return send_json(handler, status_code, error_payload)
        return send_json(handler, status_code, response_payload)
    except PermissionError:
        return send_json(handler, 401, {'error': 'Token de atualização inválido ou expirado.', 'code': 'INVALID_REFRESH_TOKEN'})


def handle_get_auth_me(handler, parsed, payload, match):
    """Identidade enxuta do usuário autenticado (envelope {success,data,message}).

    ÚNICA rota que atravessa o bloqueio de senha temporária. É ela que informa
    ao cliente por que as demais estão negadas: sem isso, um app reaberto com
    token já emitido receberia 403 em tudo e não teria como descobrir que o
    caminho é a tela de troca de senha.
    """
    with closing(get_connection()) as connection:
        actor = require_actor(
            connection,
            resolve_actor_user_id(handler, parsed),
            allow_password_change_pending=True,
        )
        user = dict(actor)
        user.pop('password', None)
        # Preferências pessoais de interface (Isolamento PR C). Explicitamente
        # NORMALIZADAS aqui: a coluna guarda JSON cru, e entregar cru obrigaria
        # cada cliente a repetir a validação — três clientes, três chances de
        # divergir. Uma representação só, decidida pelo dono.
        from modules.auth.service import get_user_ui_preferences
        user['ui_preferences'] = get_user_ui_preferences(connection, actor['id'])
        from modules.auth.service import get_user_password_policy
        from modules.employees.service import actor_operational_unit_id
        from modules.settings.service import get_effective_module_visibility
        unit_id = actor_operational_unit_id(connection, actor)
        # Mesmas duas chaves do login, com o mesmo valor: o Flutter lê
        # `must_change_password` e o web legado `require_password_change`.
        # Repetir aqui é o que permite decidir o redirect após um restart, sem
        # exigir novo login.
        must_change = bool(get_user_password_policy(connection, int(actor['id']))['must_change'])
        user['must_change_password'] = must_change
        return send_api_response(handler, 200, data={
            'user': user,
            'permissions': sorted(PERMISSIONS.get(actor['role'], set())),
            'module_visibility': get_effective_module_visibility(connection, actor, unit_id=unit_id),
            'must_change_password': must_change,
            'require_password_change': must_change,
        })


# ── 2FA (TOTP) — segurança da conta ──────────────────────────────────────────

def _require_authenticated_actor(connection, handler, parsed, payload):
    from modules.auth.service import require_actor
    return require_actor(connection, resolve_actor_user_id(handler, parsed, payload))


def handle_get_2fa_status(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        state = get_user_totp_state(connection, actor['id'])
        return send_json(handler, 200, {'ok': True, 'enabled': state['enabled']})


def handle_post_2fa_setup(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        result = setup_user_totp(connection, actor['id'], actor.get('username') or str(actor['id']))
        connection.commit()
        structured_log('info', 'auth.totp_setup', user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, **result})


def handle_post_2fa_enable(handler, parsed, payload, match):
    require_fields(payload, ['totp_code'])
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        enable_user_totp(connection, actor['id'], payload.get('totp_code'))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'enabled': True})


def handle_post_2fa_disable(handler, parsed, payload, match):
    require_fields(payload, ['totp_code'])
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        disable_user_totp(connection, actor['id'], payload.get('totp_code'))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'enabled': False})


def handle_post_accept_terms(handler, parsed, payload, match):
    """Registra o aceite dos termos de uso e política de privacidade."""
    from datetime import datetime, timezone
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        accepted_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        try:
            connection.execute(
                'UPDATE users SET terms_accepted_at = ? WHERE id = ?', (accepted_at, actor['id'])
            )
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
            raise ValueError('Não foi possível registrar o aceite dos termos.')
        structured_log('info', 'auth.terms_accepted', user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'terms_accepted_at': accepted_at})


def handle_get_auth_me_preferences(handler, parsed, payload, match):
    """Preferências pessoais de interface do usuário autenticado.

    Já vêm no `/api/bootstrap` e no `/api/auth/me`; esta rota existe para quem
    precisa só delas, sem pagar um bootstrap inteiro.
    """
    from modules.auth.service import get_user_ui_preferences
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        return send_api_response(handler, 200, data={
            'ui_preferences': get_user_ui_preferences(connection, actor['id']),
        })


def handle_put_auth_me_preferences(handler, parsed, payload, match):
    """Grava as preferências pessoais de interface do usuário autenticado.

    Escopo USER (Isolamento PR C). O ator vem do mesmo caminho de sempre —
    nunca do corpo —, então um usuário não consegue escrever na linha de
    outro nem mandando `user_id`.

    Escrita parcial e tolerante: só as quatro chaves conhecidas entram, e um
    valor não reconhecido é ignorado em vez de virar 400. Aparência não pode
    ser motivo de erro na tela de quem só trocou o tema.
    """
    from modules.auth.service import save_user_ui_preferences
    with closing(get_connection()) as connection:
        actor = _require_authenticated_actor(connection, handler, parsed, payload)
        entrada = payload if isinstance(payload, dict) else {}
        # Aceita tanto `{tema: ...}` quanto `{ui_preferences: {tema: ...}}`.
        if isinstance(entrada.get('ui_preferences'), dict):
            entrada = entrada['ui_preferences']
        try:
            resultado = save_user_ui_preferences(connection, actor['id'], entrada)
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except Exception:
                # Rollback falhou depois de a escrita já ter falhado: não há
                # segunda chance a tentar, e engolir aqui preserva o erro
                # original, que é o que descreve o problema de verdade.
                pass
            raise ValueError('Não foi possível salvar as preferências.')
        return send_api_response(handler, 200, data={'ui_preferences': resultado})


def register_routes(router):
    router.register('GET',  '/api/auth-diagnostics',  handle_get_auth_diagnostics)
    # ── R0.5B SONDA TEMPORÁRIA — INÍCIO ─────────────────────────────────────
    router.register('GET',  '/api/origin-identity-diagnostics', handle_get_origin_identity_diagnostics)
    # ── R0.5B SONDA TEMPORÁRIA — FIM ────────────────────────────────────────
    router.register('GET',  '/api/db-pool/status',    handle_get_db_pool_status)
    router.register('GET',  '/api/bootstrap',          handle_get_bootstrap)
    router.register('GET',  '/api/auth/me',           handle_get_auth_me)
    router.register('POST', '/api/login',             handle_post_login)
    router.register('POST', '/api/auth/login',        handle_post_login)
    router.register('POST', '/api/auth/refresh',      handle_post_auth_refresh)
    router.register('POST', '/api/recover-password',  handle_post_recover_password)
    router.register('POST', '/api/change-password',   handle_post_change_password)
    router.register('POST', r'/api/users/(\d+)/recovery-token$', handle_post_user_recovery_token, regex=True)
    router.register('POST', '/api/auth/request-email-recovery', handle_post_request_email_recovery)
    router.register('GET',  '/api/auth/2fa/status',   handle_get_2fa_status)
    router.register('POST', '/api/auth/2fa/setup',    handle_post_2fa_setup)
    router.register('POST', '/api/auth/2fa/enable',   handle_post_2fa_enable)
    router.register('POST', '/api/auth/2fa/disable',  handle_post_2fa_disable)
    router.register('POST', '/api/auth/accept-terms', handle_post_accept_terms)
    router.register('GET',  '/api/auth/me/preferences', handle_get_auth_me_preferences)
    router.register('PUT',  '/api/auth/me/preferences', handle_put_auth_me_preferences)
    router.register('POST', '/api/auth/me/preferences', handle_put_auth_me_preferences)
