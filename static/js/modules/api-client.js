'use strict';

// Módulo de cliente HTTP (refatoração JS — Fase 4).
//
// Reimplementação canônica da camada de comunicação HTTP de app.js, seguindo
// o padrão aditivo: app.js mantém suas cópias locais; este módulo expõe as
// versões testáveis em globalThis/__EPI_API_CLIENT__ para o app modular
// futuro e scripts externos.
//
// Dependência de estado: buildApiHeaders lê o token via __EPI_APP_STATE__.token
// (o mesmo objeto de estado publicado por app.js), sem acesso a refs ou DOM.
(function () {
  if (globalThis.__EPI_MODULE_API_CLIENT_LOADED__) {return;}
  globalThis.__EPI_MODULE_API_CLIENT_LOADED__ = true;

  function _reportError(msg, error) {
    if (typeof globalThis.reportNonCriticalError === 'function') {
      globalThis.reportNonCriticalError(msg, error);
    } else {
      console.warn('[api-client]', msg, error);
    }
  }

  // ── Helpers puros ─────────────────────────────────────────────────────────

  function createApiError(message, response, payload, code = '') {
    const error = new Error(message);
    error.status = response.status;
    error.code = code || payload?.code || '';
    error.payload = payload;
    return error;
  }

  function isBootstrapApiPath(path = '') {
    return String(path || '').startsWith('/api/bootstrap');
  }

  function waitMs(ms) {
    return new Promise((resolve) => setTimeout(resolve, Math.max(0, Number(ms || 0))));
  }

  function ensureExpectedApiResponse(path, response, payload, contentType) {
    const expectsJson = String(path || '').startsWith('/api/');
    if (response.ok && expectsJson && !contentType.includes('application/json')) {
      throw createApiError(
        'Resposta inválida do servidor. Tente novamente em instantes.',
        response, payload, 'INVALID_API_RESPONSE'
      );
    }
  }

  function throwIfApiRequestFailed(path, response, payload) {
    if (response.ok) {return;}
    const serverError = payload?.error;
    const serverMessage = typeof serverError === 'string' ? serverError : serverError?.message;
    const normalizedCode = payload?.code || serverError?.code || '';
    const isGatewayError = [502, 503, 504].includes(response.status);

    let fallbackMessage;
    if (response.status === 401) {
      fallbackMessage = 'Usuário ou senha inválidos.';
    } else if (response.status === 403) {
      fallbackMessage = 'Acesso negado. Faça login novamente.';
    } else if (response.status === 404) {
      fallbackMessage = 'Rota da API não encontrada. Verifique versão do frontend/backend.';
    } else if (isGatewayError) {
      fallbackMessage = 'Servidor temporariamente indisponível. Tente novamente em instantes.';
    } else {
      fallbackMessage = `Falha na requisição (${response.status}).`;
    }

    const message = isGatewayError ? fallbackMessage : (serverMessage || fallbackMessage);
    const apiError = createApiError(message, response, payload, normalizedCode);
    if (isBootstrapApiPath(path) || isGatewayError) {apiError.nonFatal = true;}
    throw apiError;
  }

  // ── Estado: lê token do objeto compartilhado __EPI_APP_STATE__ ───────────

  function buildApiHeaders(options = {}) {
    const token = (globalThis.__EPI_APP_STATE__ || {}).token || '';
    const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
    return {
      'Content-Type': 'application/json',
      ...authHeader,
      ...options.headers
    };
  }

  // ── Pipeline de fetch ─────────────────────────────────────────────────────

  async function parseApiPayload(response) {
    const contentType = String(response.headers.get('content-type') || '').toLowerCase();
    if (response.status >= 400) {
      const raw = await response.text();
      const compact = String(raw || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      if (!raw) {
        return {
          contentType,
          payload: {
            ok: false,
            error: {
              code: 'EMPTY_ERROR_RESPONSE',
              message: `Falha na requisição (${response.status}).`,
              details: { raw: '' }
            }
          }
        };
      }
      try {
        return { contentType, payload: JSON.parse(raw) };
      } catch (error) {
        _reportError('api json parse failed', error);
        const isGateway = [502, 503, 504].includes(response.status);
        if (isGateway) {
          console.warn('[api] gateway error (non-JSON body)', { status: response.status });
        } else {
          console.error('[api] error body parse failed', { status: response.status, raw });
        }
        return {
          contentType,
          payload: {
            ok: false,
            error: {
              code: 'INVALID_ERROR_RESPONSE',
              message: compact || `Falha na requisição (${response.status}).`,
              details: { raw }
            }
          }
        };
      }
    }
    if (contentType.includes('application/json')) {
      try {
        return { contentType, payload: await response.json() };
      } catch (error) {
        _reportError('api json parse failed', error);
        return {
          contentType,
          payload: {
            ok: false,
            error: {
              code: 'INVALID_SUCCESS_RESPONSE',
              message: 'Resposta inválida do servidor.',
              details: { raw: '' }
            }
          }
        };
      }
    }
    const raw = await response.text();
    const compact = String(raw || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return { contentType, payload: raw ? { error: compact || 'Resposta não-JSON do servidor.', raw } : {} };
  }

  async function requestApiResponse(path, options = {}) {
    try {
      return await fetch(path, { headers: buildApiHeaders(options), ...options });
    } catch (error) {
      if (error instanceof Error) {
        throw new Error('Falha de conexão com o servidor. Verifique sua internet e tente novamente.', { cause: error });
      }
      throw new Error('Falha de conexão com o servidor. Verifique sua internet e tente novamente.');
    }
  }

  async function apiFetch(path, options = {}) {
    const response = await requestApiResponse(path, options);
    const { contentType, payload } = await parseApiPayload(response);
    ensureExpectedApiResponse(path, response, payload, contentType);
    throwIfApiRequestFailed(path, response, payload);
    if (payload && typeof payload === 'object' && Object.hasOwn(payload, 'ok')) {
      if (payload.ok === false) {
        const err = payload.error || {};
        throw createApiError(err.message || 'Falha na API.', response, payload, err.code || '');
      }
      if (payload.data !== undefined) {return payload.data;}
      return payload;
    }
    return payload || {};
  }

  async function apiFetchOptional(path, options = {}) {
    try {
      const payload = await apiFetch(path, options);
      return { ok: true, payload };
    } catch (error) {
      _reportError(`[api-optional] ${path}`, error);
      return { ok: false, error };
    }
  }

  async function apiFetchWithRetry(path, options = {}, config = {}) {
    const maxAttempts = Math.max(1, Number(config.maxAttempts || 4));
    const retryDelayMs = Math.max(250, Number(config.retryDelayMs || 1200));
    let lastError = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        return await apiFetch(path, options);
      } catch (error) {
        lastError = error;
        const errStatus = Number(error?.status || 0);
        const bootstrapUnavailable = errStatus === 503 || errStatus === 502;
        if (!bootstrapUnavailable || attempt >= maxAttempts) {break;}
        // Exponential backoff with jitter: base * 2^(attempt-1) + random(0-1s), capped at 30s
        const backoff = Math.min(retryDelayMs * Math.pow(2, attempt - 1), 30000);
        await waitMs(backoff + Math.random() * 1000);
      }
    }
    throw lastError || new Error('Falha ao carregar dados da API.');
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exports = {
    createApiError,
    isBootstrapApiPath,
    waitMs,
    ensureExpectedApiResponse,
    throwIfApiRequestFailed,
    buildApiHeaders,
    parseApiPayload,
    requestApiResponse,
    apiFetch,
    apiFetchOptional,
    apiFetchWithRetry
  };

  for (const [name, fn] of Object.entries(exports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_API_CLIENT__ = Object.freeze({ ...exports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, exports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
