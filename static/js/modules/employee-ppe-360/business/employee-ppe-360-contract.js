'use strict';

// Ficha 360° de EPI — contrato de apresentação (F0, camada business).
//
// Regras PURAS que a interface da Ficha usa para decidir o que pode mostrar.
// Não toca DOM, HTTP, storage nem estado global: tudo entra por parâmetro
// (guarda UBX, regra 5). Não calcula valores financeiros — custos chegam
// prontos do backend, que é a única fonte (ver docs/FICHA_360_F0_CONTRATOS.md).
//
// O que fica fixado aqui:
//  - identidade do contexto (usuário + empresa + unidade + perfil + colaborador):
//    qualquer mudança invalida tudo o que foi carregado antes;
//  - validação do envelope de resposta do backend ({ok, data, page} / {ok:false,
//    error:{code}}), espelhando modules/employee_ppe_360/contract.py;
//  - paginação pedida pelo cliente, com os mesmos limites do servidor (o
//    servidor continua sendo quem decide);
//  - estados visuais de uma seção.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_BUSINESS_LOADED__ = true;

  const PAGE_DEFAULT = 20;
  const PAGE_MAX = 100;
  const CURSOR_MAX_LENGTH = 200;
  const CURSOR_RE = /^[A-Za-z0-9_-]+$/;

  const SECTION_STATES = Object.freeze({
    IDLE: 'idle',
    LOADING: 'loading',
    READY: 'ready',
    EMPTY: 'empty',
    ERROR: 'error',
    // Sem permissão: a seção some; nunca vira "0" ou "vazio".
    FORBIDDEN: 'forbidden'
  });

  // Códigos do backend (contract.py → ERRORS) e o estado visual de cada um.
  const ERROR_STATES = Object.freeze({
    INVALID_EMPLOYEE_ID: SECTION_STATES.ERROR,
    INVALID_PAGINATION: SECTION_STATES.ERROR,
    FORBIDDEN: SECTION_STATES.FORBIDDEN,
    EMPLOYEE_NOT_FOUND: SECTION_STATES.FORBIDDEN
  });

  function normalizeEmployeeId(raw) {
    if (typeof raw === 'boolean' || raw === null || raw === undefined) { return null; }
    const text = String(raw).trim();
    if (!/^\d{1,12}$/.test(text)) { return null; }
    const value = Number(text);
    return Number.isSafeInteger(value) && value > 0 ? value : null;
  }

  function normalizeScopeValue(raw) {
    if (raw === null || raw === undefined) { return ''; }
    return String(raw).trim();
  }

  // Chave do contexto. Sem usuário, empresa, perfil ou colaborador não há
  // contexto válido (null) — a Ficha não monta.
  function buildContextKey(ctx) {
    const source = ctx || {};
    const userId = normalizeScopeValue(source.userId);
    const role = normalizeScopeValue(source.role);
    const companyId = normalizeScopeValue(source.companyId);
    const employeeId = normalizeEmployeeId(source.employeeId);
    if (!userId || !role || !employeeId) { return null; }
    // master_admin não tem empresa própria; os demais precisam ter.
    if (!companyId && role !== 'master_admin') { return null; }
    const unitId = normalizeScopeValue(source.unitId);
    return JSON.stringify([userId, role, companyId, unitId, employeeId]);
  }

  function normalizePageRequest(input) {
    const source = input || {};
    let limit = PAGE_DEFAULT;
    if (source.limit !== undefined && source.limit !== null && String(source.limit).trim() !== '') {
      const text = String(source.limit).trim();
      if (!/^\d+$/.test(text)) { return null; }
      limit = Number(text);
      if (limit < 1 || limit > PAGE_MAX) { return null; }
    }
    let cursor = null;
    if (source.cursor !== undefined && source.cursor !== null && String(source.cursor) !== '') {
      cursor = String(source.cursor);
      if (cursor.length > CURSOR_MAX_LENGTH || !CURSOR_RE.test(cursor)) { return null; }
    }
    return { limit, cursor };
  }

  // Valida o envelope do backend. Devolve {ok, data, page} ou {ok:false, code,
  // state}. Envelope malformado é tratado como erro — nunca como "vazio".
  function readEnvelope(body) {
    if (!body || typeof body !== 'object') {
      return { ok: false, code: 'MALFORMED_RESPONSE', state: SECTION_STATES.ERROR };
    }
    if (body.ok === true && Object.prototype.hasOwnProperty.call(body, 'data')) {
      let page = null;
      if (body.page !== undefined) {
        const p = body.page;
        const validLimit = p && Number.isInteger(p.limit) && p.limit >= 1 && p.limit <= PAGE_MAX;
        const validCursor = p && (p.next_cursor === null
          || (typeof p.next_cursor === 'string' && p.next_cursor.length <= CURSOR_MAX_LENGTH && CURSOR_RE.test(p.next_cursor)));
        if (!validLimit || !validCursor) {
          return { ok: false, code: 'MALFORMED_RESPONSE', state: SECTION_STATES.ERROR };
        }
        page = { limit: p.limit, nextCursor: p.next_cursor };
      }
      return { ok: true, data: body.data, page };
    }
    if (body.ok === false && body.error && typeof body.error.code === 'string') {
      const code = body.error.code;
      return { ok: false, code, state: ERROR_STATES[code] || SECTION_STATES.ERROR };
    }
    return { ok: false, code: 'MALFORMED_RESPONSE', state: SECTION_STATES.ERROR };
  }

  // Estado visual a partir de dados já validados.
  function sectionStateFor(result) {
    if (!result) { return SECTION_STATES.IDLE; }
    if (!result.ok) { return result.state || SECTION_STATES.ERROR; }
    const data = result.data;
    if (data === null || data === undefined) { return SECTION_STATES.EMPTY; }
    if (Array.isArray(data) && data.length === 0) { return SECTION_STATES.EMPTY; }
    return SECTION_STATES.READY;
  }

  globalThis.__EPI_EMPLOYEE_PPE_360_BUSINESS__ = Object.freeze({
    PAGE_DEFAULT,
    PAGE_MAX,
    SECTION_STATES,
    ERROR_STATES,
    normalizeEmployeeId,
    buildContextKey,
    normalizePageRequest,
    readEnvelope,
    sectionStateFor
  });
})();
