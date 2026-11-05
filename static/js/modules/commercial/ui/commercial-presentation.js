'use strict';

// Apresentação comercial (UBX Comercial, fatia C1 — extraída de static/app.js).
//
// Doze funções que só DEVOLVEM texto ou markup para o painel Comercial: planos
// (rótulo, opções e dica), risco e ações por empresa, cartões de resumo, alerta
// e vencimento, e o histórico de auditoria. Não escrevem no DOM, não fazem HTTP
// e não alteram estado. Corpos idênticos aos do app.js, inclusive as chaves de
// tradução, os textos de fallback e os escapes da SECURITY-OUTPUT-XSS-V1.
//
// Dependências lidas pelo nome global na hora da chamada, como antes: tr,
// escapeHtml, formatCurrency, formatDate, companyLogoMarkup, hasPermission,
// getCommercialSettings (app.js), commercialAlertTone (../business/
// commercial-rules.js) e globalThis.EpiI18n. No app.js eram declarações de
// função no bloco de carga (Annex B: viravam globais); aqui são publicadas em
// globalThis com os mesmos nomes e em __EPI_COMMERCIAL_PRESENTATION__
// (congelado). Carga idempotente.
//
// Achado de segurança registrado à parte (docs/UBX_APPJS_AUDITORIA.md §18.5):
// planOptionMarkup insere a chave e o rótulo do plano no <select> sem escape.
// A extração preserva o comportamento exato; a correção vai em PR separado.
(function () {
  if (globalThis.__EPI_MODULE_COMMERCIAL_PRESENTATION_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMMERCIAL_PRESENTATION_LOADED__ = true;

  function planEntries() {
    return Object.entries(getCommercialSettings().plans || {});
  }

  function planLabel(planKey) {
    return getCommercialSettings().plans?.[planKey]?.label || planKey;
  }

  function planOptionMarkup(selectedPlan = '') {
    return planEntries().map(([key, plan]) => `<option value="${key}" ${key === selectedPlan ? 'selected' : ''}>${plan.label}</option>`).join('');
  }

  function planHintText(planKey, addendumEnabled = false) {
    const plan = getCommercialSettings().plans?.[planKey];
    if (!plan) return '';
    const maxText = plan.max_users === null
      ? tr('commercial.panel.planUnlimited', 'sem teto')
      : tr('commercial.panel.planUpTo', 'até {max}', { max: plan.max_users });
    return addendumEnabled
      ? tr('commercial.panel.planHintAddendum', '{plan}: Usuário(s), {limit} com aditivo contratual.', { plan: plan.label, limit: maxText })
      : tr('commercial.panel.planHint', '{plan}: Usuário(s), {limit}.', { plan: plan.label, limit: maxText });
  }

  function commercialRiskMeta(company) {
    if (Number(company.active) !== 1) return { label: tr('commercial.risk.inactiveCompany', 'Empresa inativa'), tone: 'inactive' };
    if (company.license_status === 'expired') return { label: tr('commercial.risk.contractExpired', 'Contrato expirado'), tone: 'inactive' };
    if (company.license_status === 'suspended') return { label: tr('commercial.risk.contractSuspended', 'Contrato suspenso'), tone: 'inactive' };
    if (Number(company.limit_reached) === 1) return { label: tr('commercial.risk.atLimit', 'No limite'), tone: 'inactive' };
    if (company.near_limit) return { label: tr('commercial.risk.nearLimit', 'Próxima do limite'), tone: 'warning' };
    return { label: tr('commercial.risk.healthy', 'Saudável'), tone: 'active' };
  }

  function commercialActions(company) {
    if (!hasPermission('companies:update')) return '';
    const canReactivate = company.license_status === 'suspended' || company.license_status === 'expired' || Number(company.active) !== 1;
    const actionMode = canReactivate ? 'reactivate' : 'suspend';
    const toggleLabel = canReactivate ? tr('commercial.panel.reactivate', 'Reativar') : tr('commercial.panel.suspend', 'Suspender');
    return `<div class="action-group commercial-actions"><button class="ghost" data-company-commercial="${escapeHtml(company.id)}">${escapeHtml(tr('commercial.panel.openContract', 'Abrir contrato'))}</button><button class="ghost" data-commercial-toggle="${escapeHtml(company.id)}" data-commercial-mode="${actionMode}">${escapeHtml(toggleLabel)}</button></div>`;
  }

  // SECURITY-OUTPUT-XSS-V1: cards do Comercial — nome da empresa, plano e motivos entram escapados
  // (o nome vem do cadastro e é exibido ao Administrador Master).
  function renderCommercialSummaryCard(item) {
    const usage = `${item.user_count}/${item.user_limit}`;
    const monthly = formatCurrency(item.monthly_value || 0, globalThis.EpiI18n?.lang);
    const projected = formatCurrency(item.projected_monthly_value || 0, globalThis.EpiI18n?.lang);
    const risk = commercialRiskMeta(item);
    return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${escapeHtml(item.name)}</strong><span>${tr('commercial.usersCount', '{count} Usuários').replace('{count}', escapeHtml(usage))}</span><span>${monthly} ${tr('commercial.currentLabel', 'atual')} | ${projected} ${tr('commercial.projectedLabel', 'projetado')}</span><span>${escapeHtml(planLabel(item.plan_name))}</span></div><span class="badge badge-status-${risk.tone}">${risk.label}</span></div>${commercialActions(item)}</div>`;
  }

  function renderCommercialAlertCard(item) {
    const reasons = [];
    if (Number(item.limit_reached) === 1) reasons.push(tr('commercial.limitReachedAlert', 'limite contratado atingido'));
    else if (item.near_limit) reasons.push(tr('commercial.nearLimitAlert', 'próxima do limite contratado'));
    if (['suspended', 'expired'].includes(item.license_status)) reasons.push(tr(`license.${item.license_status}`, item.license_status_label || item.license_status));
    if (Number(item.active) !== 1) reasons.push(tr('commercial.inactiveAlert', 'empresa inativa'));
    const tone = commercialAlertTone(item);
    return `<div class="commercial-card"><div class="alert-item ${tone}"><strong>${escapeHtml(item.name)}</strong><div>${reasons.map(escapeHtml).join(' | ')}</div></div>${commercialActions(item)}</div>`;
  }

  function renderCommercialExpiringCard(entry) {
    const { item, days } = entry;
    const badgeTone = days <= 7 ? 'inactive' : 'warning';
    const badgeLabel = days <= 7 ? tr('commercial.urgentBadge', 'Urgente') : tr('commercial.monitorBadge', 'Acompanhar');
    const expiresText = tr('commercial.expiresOn', 'Vence em {date}').replace('{date}', formatDate(item.contract_end));
    const remainingText = tr('commercial.daysRemaining', '{days} dia(s) restantes').replace('{days}', days);
    return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${escapeHtml(item.name)}</strong><span>${expiresText}</span><span>${remainingText}</span></div><span class="badge badge-status-${badgeTone}">${badgeLabel}</span></div>${commercialActions(item)}</div>`;
  }

  function formatCommercialAuditDetails(details) {
    const detailsHtml = (details || []).map((detail) => `<div class="audit-detail-row"><strong>${escapeHtml(detail.field)}</strong><span>${escapeHtml(detail.before || '-')} -> ${escapeHtml(detail.after || '-')}</span></div>`).join('');
    return detailsHtml ? `<div class="audit-details">${detailsHtml}</div>` : '';
  }

  function renderCommercialHistoryItem(item) {
    const createdAt = new Intl.DateTimeFormat(globalThis.EpiI18n?.lang || 'pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
    return `<div class="commercial-card"><div class="commercial-row"><div class="company-logo company-logo-sm"></div><div><strong>${escapeHtml(item.company_name)}</strong><span>${escapeHtml(tr('commercial.panel.historyBy', '{action} por {actor}', { action: item.action_label, actor: item.actor_name }))}</span><span>${createdAt}</span></div><span class="badge badge-status-active">${escapeHtml(item.action_label)}</span></div><div class="summary-item">${escapeHtml(item.summary)}</div>${formatCommercialAuditDetails(item.details)}</div>`;
  }

  function formatCommercialDetails(details, separator = '<br>') {
    return (details || []).map((detail) => `${escapeHtml(detail.field)}: ${escapeHtml(detail.before || '-')} -> ${escapeHtml(detail.after || '-')}`).join(separator);
  }

  const commercialPresentationExports = {
    planEntries,
    planLabel,
    planOptionMarkup,
    planHintText,
    commercialRiskMeta,
    commercialActions,
    renderCommercialSummaryCard,
    renderCommercialAlertCard,
    renderCommercialExpiringCard,
    formatCommercialAuditDetails,
    renderCommercialHistoryItem,
    formatCommercialDetails
  };

  for (const [name, fn] of Object.entries(commercialPresentationExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_COMMERCIAL_PRESENTATION__ = Object.freeze({ ...commercialPresentationExports });
})();
