'use strict';

// Navegação de leitura para o painel existente. Ações e autorização continuam
// pertencendo ao fluxo de regularização e aos endpoints atuais.
(function () {
  let intent = null;
  let ports = {};
  function configure(dependencies) { ports = dependencies; clear(); }
  const state = () => ports.getState?.() || {};
  const text = (key, fallback) => typeof ports.translate === 'function' ? ports.translate(key, fallback) : fallback;
  const id = (value) => /^[1-9]\d*$/.test(String(value ?? '')) ? String(value) : '';
  const selectors = () => ({
    companyId: String(document.getElementById('stock-company')?.value || state().user?.company_id || ''),
    unitId: String(document.getElementById('stock-unit')?.value || state().user?.operational_unit_id || ''),
  });

  function clear() {
    intent = null;
    const banner = document.getElementById('pending-reg-alert-context');
    if (banner) { banner.hidden = true; }
  }

  function current() {
    if (!intent) { return null; }
    const context = selectors();
    if (String(state().user?.id) !== intent.actorId || context.companyId !== intent.anchor.companyId
        || context.unitId !== intent.anchor.unitId) {
      clear();
    }
    return intent;
  }

  function renderContext() {
    const banner = document.getElementById('pending-reg-alert-context');
    const label = document.getElementById('pending-reg-alert-label');
    if (!banner || !label || !intent) { return; }
    const company = (state().companies || []).find((item) => String(item.id) === intent.companyId);
    const unit = (state().units || []).find((item) => String(item.id) === intent.unitId);
    label.textContent = text('stock.pendingReg.alertContext', 'Pendentes do alerta: {epi} · {company} · {unit}')
      .replace('{epi}', intent.epiName || text('stock.pendingReg.allEpis', 'Todos os EPIs'))
      .replace('{company}', company?.name || intent.companyId)
      .replace('{unit}', unit?.name || text('epi.allUnits', 'Todas as Unidades'));
    banner.hidden = false;
  }

  function requestContext(fallback) {
    const active = current();
    return active ? { companyId: active.companyId, unitId: active.unitId } : fallback;
  }

  function filterResponse(payload) {
    const active = current();
    if (!active) { return payload; }
    const items = (Array.isArray(payload.items) ? payload.items : []).filter((item) => (
      (!active.epiId || String(item.epi_id) === active.epiId)
      && (!active.unitId || String(item.unit_id) === active.unitId)
    ));
    renderContext();
    return { ...payload, items, count: items.length };
  }

  function open(alert) {
    if (!ports.hasPermission?.('stock:view')) { return false; }
    if (['company_id', 'unit_id', 'epi_id'].some((key) => alert[key] && !id(alert[key]))) { return false; }
    const user = state().user || {};
    const companyId = id(alert.company_id) || id(user.company_id);
    const epiId = id(alert.epi_id);
    const unitId = id(alert.unit_id);
    const locked = ['admin', 'user'].includes(user.role);
    const effectiveUnit = locked ? id(user.operational_unit_id) : unitId;
    if (!companyId || (user.role !== 'master_admin' && companyId !== id(user.company_id))
        || (locked && (!effectiveUnit || (unitId && unitId !== effectiveUnit)))) { return false; }
    if (effectiveUnit && !(state().units || []).some((unit) => String(unit.id) === effectiveUnit
        && String(unit.company_id) === companyId)) { return false; }
    const menu = document.querySelector('.menu-link[data-view="estoque"]');
    const company = document.getElementById('stock-company');
    const unit = document.getElementById('stock-unit');
    if (!menu || !company || !unit || typeof ports.syncOptions !== 'function') { return false; }
    menu.click(); // showView executa os resets normais antes de aplicar o recorte.
    if (!document.getElementById('estoque-view')?.classList.contains('active')) { return false; }
    company.value = companyId;
    if (company.value !== companyId) { return false; }
    ports.syncOptions();
    if (effectiveUnit) {
      unit.value = effectiveUnit;
      if (unit.value !== effectiveUnit) { return false; }
    }
    intent = { companyId, unitId: effectiveUnit, epiId, epiName: String(alert.epi_name || ''),
      actorId: String(user.id), anchor: selectors() };
    // Alerta corporativo sem unidade consulta TODAS as unidades no painel de
    // pendências. Não herda a primeira unidade do formulário de movimentação.
    const group = document.getElementById('pending-reg-filter');
    if (group) { group.value = ''; }
    renderContext();
    document.querySelector('[data-vtabs="estoque"] [data-vtab="validade"]')?.click();
    const heading = document.getElementById('pending-reg-title');
    heading?.focus({ preventScroll: true });
    // O título focado deve ficar visível abaixo do cabeçalho sticky.
    const horizontalPosition = globalThis.scrollX || 0;
    heading?.scrollIntoView({ block: 'center', inline: 'nearest' });
    globalThis.scrollTo?.({ left: horizontalPosition, top: globalThis.scrollY });
    void ports.refresh?.();
    return true;
  }

  document.addEventListener?.('epi:viewchange', (event) => {
    if (event.detail?.view !== 'estoque') { clear(); }
  });
  document.addEventListener?.('change', (event) => {
    if (['stock-company', 'stock-unit'].includes(event.target?.id)) { current(); }
  });
  document.addEventListener?.('click', (event) => {
    if (!event.target?.closest?.('#pending-reg-alert-clear')) { return; }
    clear();
    void ports.refresh?.();
  });
  globalThis.__EPI_PENDING_VALIDITY_NAVIGATION__ = Object.freeze({ configure, open, requestContext, filterResponse, clear });
}());
