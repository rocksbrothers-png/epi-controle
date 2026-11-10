'use strict';

// Ficha 360° de EPI — regras de apresentação do resumo (F1, camada business).
//
// Funções PURAS (sem DOM, HTTP, storage ou estado global): recebem o que o
// backend devolveu em /api/employees/{id}/ppe-360/summary e decidem O QUE
// mostrar. Nada é calculado além de organizar o que chegou:
//  - "Pendentes" é sempre o detalhamento por estado; o total vem do backend e
//    só é exibido junto do detalhamento (nunca um número sem origem);
//  - a próxima troca é a data gravada; "vencida" é comparação de datas ISO;
//  - responsáveis são os que o backend derivou (DF-1) — lista vazia é vazia;
//  - blocos de fatias futuras são declarados aqui como INDISPONÍVEIS, sem
//    número nem conteúdo simulado.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_SUMMARY_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_SUMMARY_LOADED__ = true;

  const OPEN_PERMISSION = 'employees:view';
  const FINANCE_PERMISSION = 'finance:view';
  // DF-3: o backend bloqueia; esconder o botão é só conveniência.
  const BLOCKED_ROLES = Object.freeze(['master_admin']);

  // Ordem da máquina de estados (modules/epis/request_states.py → SPEC_CODE).
  const REQUEST_STATUS_ORDER = Object.freeze([
    'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'WAITING_STOCK', 'RESERVED', 'PICKING',
    'READY_FOR_DELIVERY', 'DELIVERY_COMPLETED', 'DELIVERY_REFUSED', 'REJECTED', 'POSTPONED',
    'CANCELLED', 'UNKNOWN'
  ]);
  const RESPONSIBLE_ROLES = Object.freeze(['admin', 'user', 'general_admin', 'registry_admin']);

  // Blocos das fatias seguintes: aparecem como indisponíveis (sem dado).
  const FUTURE_BLOCKS = Object.freeze({
    central: Object.freeze([
      Object.freeze({ id: 'active-epis', label: 'employee360.blocks.activeEpis', fallback: 'EPIs em uso', hintLabel: 'employee360.blocks.activeEpisHint', hint: 'Produto, CA, validade, entrega e troca' }),
      Object.freeze({ id: 'requests', label: 'employee360.blocks.requests', fallback: 'Solicitações', hintLabel: 'employee360.blocks.requestsHint', hint: 'Pendentes, aprovadas e atendidas' }),
      Object.freeze({ id: 'deliveries', label: 'employee360.blocks.deliveries', fallback: 'Entregas', hintLabel: 'employee360.blocks.deliveriesHint', hint: 'Histórico e comprovantes' })
    ]),
    complementary: Object.freeze([
      Object.freeze({ id: 'evaluations', label: 'employee360.blocks.evaluations', fallback: 'Avaliações de EPI' }),
      Object.freeze({ id: 'suggestions', label: 'employee360.blocks.suggestions', fallback: 'Sugestões de EPI' }),
      Object.freeze({ id: 'manuals', label: 'employee360.blocks.manuals', fallback: 'Manuais e visualizações' }),
      Object.freeze({ id: 'signatures', label: 'employee360.blocks.signatures', fallback: 'Assinaturas e evidências' }),
      Object.freeze({ id: 'returns', label: 'employee360.blocks.returns', fallback: 'Devoluções' }),
      Object.freeze({ id: 'consumption', label: 'employee360.blocks.consumption', fallback: 'Consumo e custos', finance: true })
    ])
  });

  // Cartões financeiros (F5): só com finance:view, e indisponíveis até lá.
  const FINANCE_CARDS = Object.freeze([
    Object.freeze({ id: 'total', label: 'employee360.finance.total', fallback: 'Custo total' }),
    Object.freeze({ id: 'monthly', label: 'employee360.finance.monthly', fallback: 'Custo mensal' }),
    Object.freeze({ id: 'forecast', label: 'employee360.finance.forecast', fallback: 'Custo previsto' })
  ]);

  function includesPermission(permissions, permission) {
    return Array.isArray(permissions) && permissions.includes(permission);
  }

  function canOpen(user, permissions) {
    if (!user || !user.role || BLOCKED_ROLES.includes(user.role)) { return false; }
    return includesPermission(permissions, OPEN_PERMISSION);
  }

  function canSeeFinance(permissions) {
    return includesPermission(permissions, FINANCE_PERMISSION);
  }

  function toCount(value) {
    const n = Number(value);
    return Number.isInteger(n) && n > 0 ? n : 0;
  }

  // [{code, count}] na ordem canônica; códigos fora da lista viram UNKNOWN.
  function pendingBreakdown(pending) {
    const source = pending && Array.isArray(pending.by_status) ? pending.by_status : [];
    const counts = new Map();
    for (const item of source) {
      const code = REQUEST_STATUS_ORDER.includes(item && item.code) ? item.code : 'UNKNOWN';
      const count = toCount(item && item.count);
      if (count) { counts.set(code, (counts.get(code) || 0) + count); }
    }
    return REQUEST_STATUS_ORDER.filter((code) => counts.has(code)).map((code) => ({ code, count: counts.get(code) }));
  }

  function pendingView(pending) {
    const items = pendingBreakdown(pending);
    const total = items.reduce((acc, item) => acc + item.count, 0);
    // O total exibido é o do backend; divergência com o detalhamento = dado
    // inconsistente, e a tela mostra o detalhamento (não um número sem origem).
    const backendTotal = toCount(pending && pending.total);
    return { items, total, consistent: backendTotal === total, empty: total === 0 };
  }

  function isIsoDate(text) {
    return typeof text === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(text);
  }

  function nextReplacementView(next, todayIso) {
    if (!next || !isIsoDate(next.date)) { return { empty: true }; }
    return {
      empty: false,
      date: next.date,
      epiName: String(next.epi_name || ''),
      overdueCount: toCount(next.overdue_count),
      isOverdue: isIsoDate(todayIso) ? next.date < todayIso : false
    };
  }

  function inUseView(inUse) {
    const source = inUse || {};
    const view = {
      units: toCount(source.units),
      products: toCount(source.products),
      categories: toCount(source.categories),
      uncategorized: toCount(source.uncategorized_products)
    };
    view.empty = view.units === 0 && view.products === 0;
    return view;
  }

  function responsibleGroups(responsibles) {
    const pick = (list) => (Array.isArray(list) ? list : [])
      .filter((item) => item && RESPONSIBLE_ROLES.includes(item.role) && String(item.name || '').trim())
      .map((item) => ({ role: item.role, name: String(item.name).trim() }));
    const source = responsibles || {};
    const unit = pick(source.unit);
    const company = pick(source.company);
    return { unit, company, empty: unit.length === 0 && company.length === 0 };
  }

  function contractedView(contracted) {
    if (!contracted) { return null; }
    const company = contracted.outsourced_company || null;
    const contract = contracted.contract || null;
    return {
      companyName: company ? String(company.name || company.legal_name || '') : '',
      companyCnpj: company ? String(company.cnpj || '') : '',
      originName: String(contracted.origin_name || ''),
      contractRef: contract ? String(contract.ref || '') : '',
      contractStart: contract && isIsoDate(String(contract.start_date || '').slice(0, 10)) ? String(contract.start_date).slice(0, 10) : '',
      contractEnd: contract && isIsoDate(String(contract.end_date || '').slice(0, 10)) ? String(contract.end_date).slice(0, 10) : '',
      hasContract: Boolean(contract)
    };
  }

  function futureBlocks(group, permissions) {
    const list = FUTURE_BLOCKS[group] || [];
    return list.filter((block) => !block.finance || canSeeFinance(permissions));
  }

  globalThis.__EPI_EMPLOYEE_PPE_360_SUMMARY__ = Object.freeze({
    REQUEST_STATUS_ORDER,
    FINANCE_CARDS,
    canOpen,
    canSeeFinance,
    pendingBreakdown,
    pendingView,
    nextReplacementView,
    inUseView,
    responsibleGroups,
    contractedView,
    futureBlocks
  });
})();
