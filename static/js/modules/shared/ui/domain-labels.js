'use strict';

// Módulo de UI compartilhado: rótulos de domínio traduzidos com `tr`
// (Refatoração UBX-V3, Etapa 2 — extraído de static/app.js).
//
// Rótulos de texto puro (sem HTML, permissão ou estado): tipo de unidade,
// vagas da empresa, vínculo e alocação do colaborador, vínculo do terceirizado
// com a unidade, proteção e unidade de medida do EPI.
//
// i18n sem dependência circular: este módulo não importa nada. O `tr` local
// delega, no momento da CHAMADA, para `globalThis.tr` — a mesma `var` global
// que o app.js define no topo (resolveLegacyTranslator/trEpi) e que os rótulos
// usavam antes —, inclusive se o tradutor for trocado depois do boot. Antes de
// o app.js carregar (só acontece em testes isolados) devolve o texto padrão,
// como os `tr` locais das views. Chaves, fallbacks e a interpolação `{count}`
// são os originais. Corpos idênticos às funções do app.js (só chaves).
(function () {
  if (globalThis.__EPI_MODULE_SHARED_DOMAIN_LABELS_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_DOMAIN_LABELS_LOADED__ = true;

  function tr(key, fallback) {
    return typeof globalThis.tr === 'function' ? globalThis.tr(key, fallback) : fallback;
  }

  // ── Unidades e empresas ───────────────────────────────────────────────────

  function unitTypeLabel(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'navio' || normalized === 'embarcacao') {return tr('unit.typeVessel', 'Embarcação');}
    if (normalized === 'plataforma') {return tr('unit.typePlatform', 'Plataforma');}
    return tr('unit.typeBase', 'Base');
  }

  function formatCompanyAvailabilityText(company) {
    return Number(company.limit_reached) === 1
      ? tr('company.limitReached', 'Limite atingido')
      : tr('company.availableSlotsText', '{count} vaga(s) disponíveis').replace('{count}', company.available_slots || 0);
  }

  // ── Colaboradores ─────────────────────────────────────────────────────────

  function employmentTypeLabel(value) {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized === 'clt') {return tr('employee.vincClt', 'CLT');}
    if (normalized === 'terceirizado') {return tr('employee.vincOutsourced', 'Terceirizado');}
    if (normalized === 'temporário' || normalized === 'temporario') {return tr('employee.vincTemporary', 'Temporário');}
    if (normalized === 'prestador de serviço' || normalized === 'prestador de servico') {return tr('employee.vincServiceProvider', 'Prestador de Serviço');}
    if (normalized === 'menor aprendiz') {return tr('employee.vincApprentice', 'Menor Aprendiz');}
    if (normalized === 'praticante') {return tr('employee.vincTrainee', 'Praticante');}
    if (normalized === 'estagiário' || normalized === 'estagiario') {return tr('employee.vincIntern', 'Estagiário');}
    return value || 'CLT';
  }

  function allocationTypeLabel(value) {
    return value === 'temporary' ? tr('employee.allocationTemporary', 'Temporário') : tr('employee.allocationPrimary', 'Principal');
  }

  function outsourcedEmployeeLinkLabel(status) {
    if (!status) {return '-';}
    if (status === 'active') {return tr('employee.unitLinkActive', 'Vinculado');}
    if (status === 'inactive') {return tr('employee.unitLinkArchived', 'Arquivado nesta Unidade');}
    return tr('employee.unitLinkAbsent', 'Não vinculado');
  }

  // ── EPIs ──────────────────────────────────────────────────────────────────

  function epiProtectionLabel(value) {
    const labels = {
      'Proteção-Membros Superiores': tr('epi.protectionUpperLimbs', 'Proteção-Membros Superiores'),
      'Proteção-Membros Inferiores': tr('epi.protectionLowerLimbs', 'Proteção-Membros Inferiores'),
      'Proteção-Auditiva': tr('epi.protectionHearing', 'Proteção-Auditiva'),
      'Proteção-Olhos e Face': tr('epi.protectionEyesFace', 'Proteção-Olhos e Face'),
      'Proteção-Respiratória': tr('epi.protectionRespiratory', 'Proteção-Respiratória'),
      'Proteção-Mãos e Braços': tr('epi.protectionHandsArms', 'Proteção-Mãos e Braços'),
      'Proteção-Cabeça': tr('epi.protectionHead', 'Proteção-Cabeça'),
      'Proteção-Combate a Incêndio': tr('epi.protectionFirefighting', 'Proteção-Combate a Incêndio'),
      'Proteção-Contra Queda': tr('epi.protectionFallProtection', 'Proteção-Contra Queda'),
      'Proteção-Eletricidade': tr('epi.protectionElectricity', 'Proteção-Eletricidade')
    };
    return labels[value] || value || '-';
  }

  function epiMeasureLabel(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'unidade') {return tr('epi.measureUnit', 'Unidade');}
    if (normalized === 'par') {return tr('epi.measurePair', 'Par');}
    return value || '-';
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  // Mesmos nomes globais de antes; lidos pelo app.js e por views/estoque.js
  // (via globalThis, com fallback próprio).

  const domainLabelExports = {
    unitTypeLabel,
    formatCompanyAvailabilityText,
    employmentTypeLabel,
    allocationTypeLabel,
    outsourcedEmployeeLinkLabel,
    epiProtectionLabel,
    epiMeasureLabel
  };

  for (const [name, fn] of Object.entries(domainLabelExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_DOMAIN_LABELS__ = Object.freeze({ ...domainLabelExports });
})();
