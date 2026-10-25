'use strict';

// Módulo de negócio compartilhado: formatação e leitura de valores simples
// (Refatoração UBX-V2 — camada Business, extraída de static/app.js).
//
// Transformações puras de valor usadas por vários domínios: dígitos, CNPJ,
// moeda, texto de busca, listas CSV, inteiros positivos, JSON opcional, cor
// hexadecimal e datas ISO (AAAA-MM-DD).
//
// Sem DOM, sem HTTP, sem storage, sem estado global: toda entrada vem por
// parâmetro. Os corpos são os das funções originais do app.js (só chaves
// acrescentadas para o lint; equivalência provada por teste diferencial) —
// inclusive as duplicatas e peculiaridades registradas abaixo. Qualquer
// mudança de resultado é mudança de comportamento, não de estrutura.
//
// Peculiaridades preservadas de propósito (docs/UBX_APPJS_AUDITORIA.md §10):
//  - formatCnpj e formatCNPJ NÃO são equivalentes: para entrada inválida a
//    primeira devolve '' e a segunda '—'.
//  - formatCurrency e fmtBrl são idênticas; ambas continuam publicadas
//    porque são contratos distintos (fmtBrl é lido por views/purchases.js e
//    views/procurement.js via globalThis).
//  - addDaysFromBaseDate e daysUntil usam o horário LOCAL do navegador;
//    addDaysFromBaseDate converte com toISOString (UTC), o que pode deslocar
//    um dia em fusos a leste de UTC. Defeito preexistente, não corrigido aqui.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_VALUE_FORMAT_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_VALUE_FORMAT_LOADED__ = true;

  // ── Números e moeda ───────────────────────────────────────────────────────

  function formatCurrency(value) {
    return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function fmtBrl(v) {
    return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function parseMonthsValue(rawValue) {
    const digits = String(rawValue ?? '').replaceAll(/[^\d-]/g, '').trim();
    const parsed = Number.parseInt(digits || '0', 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  function parsePositiveInteger(value) {
    const parsed = Number.parseInt(String(value ?? '').trim(), 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  }

  // ── Documentos ────────────────────────────────────────────────────────────

  function digitsOnly(value) {
    return String(value || '').replaceAll(/\D/g, '');
  }

  function formatCnpj(value) {
    const digits = digitsOnly(value);
    if (digits.length !== 14) {return value || '';}
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
  }

  function formatCNPJ(raw) {
    const d = String(raw || '').replace(/\D/g, '');
    if (d.length !== 14) {return raw || '—';}
    return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
  }

  // ── Texto e listas ────────────────────────────────────────────────────────

  function normalizeSearchText(value) {
    return String(value || '')
      .normalize('NFD')
      .replaceAll(/[̀-ͯ]/g, '')
      .toLowerCase()
      .trim();
  }

  function parseCsvList(value) {
    return String(value || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseCsvNumberList(value) {
    return parseCsvList(value).map((item) => Number(item)).filter((item) => Number.isFinite(item) && item > 0);
  }

  function parseOptionalJson(rawValue, fallbackValue) {
    const trimmed = String(rawValue || '').trim();
    if (!trimmed) {return fallbackValue;}
    try {
      return JSON.parse(trimmed);
    } catch (error) {
      throw new Error('JSON inválido na configuração avançada: ' + error.message);
    }
  }

  function normalizeHexColor(value, fallback) {
    const v = String(value || '').trim();
    if (/^#[0-9a-fA-F]{6}$/.test(v)) {return v;}
    if (/^#[0-9a-fA-F]{3}$/.test(v)) {return '#' + v.slice(1).split('').map((c) => c + c).join('');}
    return fallback;
  }

  // ── Datas ISO (AAAA-MM-DD) ────────────────────────────────────────────────

  function daysUntil(dateValue) {
    if (!dateValue) {return null;}
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(`${dateValue}T00:00:00`);
    return Math.round((target - today) / 86400000);
  }

  function addDaysFromBaseDate(baseDateIso, days) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(baseDateIso || ''))) {return '';}
    const baseDate = new Date(`${baseDateIso}T00:00:00`);
    if (Number.isNaN(baseDate.getTime())) {return '';}
    baseDate.setDate(baseDate.getDate() + Number(days));
    return baseDate.toISOString().slice(0, 10);
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  // Os nomes globais são o contrato legado: antes vinham das declarações de
  // bloco do app.js (globais pelo Annex B) e continuam sendo chamados pelo
  // app.js e pelas views. Atribuição direta: este módulo é a única definição.

  const valueFormatExports = {
    formatCurrency,
    fmtBrl,
    parseMonthsValue,
    parsePositiveInteger,
    digitsOnly,
    formatCnpj,
    formatCNPJ,
    normalizeSearchText,
    parseCsvList,
    parseCsvNumberList,
    parseOptionalJson,
    normalizeHexColor,
    daysUntil,
    addDaysFromBaseDate
  };

  for (const [name, fn] of Object.entries(valueFormatExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_VALUE_FORMAT__ = Object.freeze({ ...valueFormatExports });
})();
