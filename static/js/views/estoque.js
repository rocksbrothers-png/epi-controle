'use strict';

// Módulo de view: Estoque (refatoração JS — Fase 6).
//
// Reimplementação modular das funções de render de estoque de app.js:
// renderStockEpis, renderLowStock, renderRequests.
// Lê dados de globalThis.__EPI_APP_STATE__ e refs de globalThis.__EPI_REFS__.
(function () {
  if (globalThis.__EPI_MODULE_ESTOQUE_LOADED__) { return; }
  globalThis.__EPI_MODULE_ESTOQUE_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function tr(key, fallback) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  }
  function esc(v) {
    // Sanitização COMPLETA para atributos HTML (aspas incluídas), espelhando o
    // escapeHtml global — o fallback não pode deixar " ou ' sem escape (XSS).
    return typeof globalThis.escapeHtml === 'function'
      ? globalThis.escapeHtml(v)
      : String(v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
  }
  function epiProtectionLabel(value) {
    return typeof globalThis.epiProtectionLabel === 'function' ? globalThis.epiProtectionLabel(value) : (value || '-');
  }
  function epiMeasureLabel(value) {
    return typeof globalThis.epiMeasureLabel === 'function' ? globalThis.epiMeasureLabel(value) : (value || '-');
  }
  function fmtSizeBalances(sizeBalances) {
    return typeof globalThis.formatSizeBalancesDisplay === 'function'
      ? globalThis.formatSizeBalancesDisplay(sizeBalances)
      : '—';
  }
  function phase3Cards(container, items) {
    if (typeof globalThis.renderPhase3SummaryCards === 'function') {
      globalThis.renderPhase3SummaryCards(container, items);
    }
  }
  function phase3Status(view, tone, message) {
    if (typeof globalThis.updatePhase3ContextStatus === 'function') {
      globalThis.updatePhase3ContextStatus(view, tone, message);
    }
  }

  // ── Classificação de estoque: vem do BACKEND, inteira (1.1D-C3) ──────────
  //
  // Até esta fatia o Web Legado ignorava a classificação por Unidade e exibia
  // o saldo e o mínimo CORPORATIVOS como se fossem o número operacional da
  // Unidade. Uma varredura por `stock_status` em `static/` devolvia zero.
  //
  // Nada aqui recalcula regra: `stock_status`, `attention_limit`,
  // `unit_minimum_stock` e `minimum_stock_source` vêm prontos de
  // `/api/stock/epis` e `/api/stock/low`. Comparar saldo com mínimo no JS
  // criaria uma segunda régua — foi assim que a comparação errada se espalhou
  // por sete consumidores (#271).

  var STOCK_STATUS_LABELS = {
    normal: ['stock.statusNormal', 'Normal'],
    near_minimum: ['stock.statusNearMinimum', 'Próximo do mínimo'],
    critical: ['stock.statusCritical', 'Crítico'],
    disabled: ['stock.statusAlertDisabled', 'Alerta desabilitado']
  };

  // Descrições da condição FÍSICA. Informativas: explicam o número, não
  // classificam. A severidade é sempre `stock_status`.
  // Os cinco valores de `CONDITION_*` em modules/stock/service.py. A lista é
  // fechada de propósito: um valor novo no backend aparece como vazio aqui, e
  // não como um rótulo aproximado que mentiria sobre a condição.
  var STOCK_CONDITION_LABELS = {
    negative: ['stock.conditionNegative', 'saldo negativo'],
    zero: ['stock.conditionZero', 'sem saldo'],
    below_minimum: ['stock.conditionBelowMinimum', 'abaixo do mínimo'],
    at_minimum: ['stock.conditionAtMinimum', 'no mínimo'],
    above_minimum: ['stock.conditionAboveMinimum', 'acima do mínimo']
  };

  var MINIMUM_SOURCE_LABELS = {
    unit_configured: ['stock.minimumFromUnit', 'configurado pela Unidade'],
    company_default: ['stock.minimumFromCompany', 'herdado do padrão da empresa'],
    system_default: ['stock.minimumFromSystem', 'padrão do sistema']
  };

  function trPair(pair) { return pair ? tr(pair[0], pair[1]) : ''; }

  /** Chip do estado operacional, ou `''` quando NÃO há classificação.
   *
   * `stock_status` ausente significa que não existe Unidade resolvida naquele
   * contexto — é diferente de estoque normal. Devolver "Normal" aqui pintaria
   * de verde justamente o caso em que o sistema não sabe. */
  function stockStatusBadge(item) {
    var status = item && item.stock_status;
    if (!status || !STOCK_STATUS_LABELS[status]) { return ''; }
    return '<span class="badge badge-stock-' + esc(status) + '">'
      + esc(trPair(STOCK_STATUS_LABELS[status])) + '</span>';
  }

  /** Saldo a exibir e se ele é da Unidade.
   *
   * A escolha é por PRESENÇA de `unit_scope_id`, nunca por truthiness do
   * saldo: uma Unidade com zero mostra zero, e não o total da empresa. Sem
   * Unidade resolvida não existe saldo local para inventar — mostramos o
   * corporativo dizendo que ele é corporativo. */
  function stockReading(item) {
    var hasUnit = item && item.unit_scope_id !== null && item.unit_scope_id !== undefined;
    if (hasUnit) {
      return { value: Number(item.unit_stock_quantity ?? 0), fromUnit: true };
    }
    return { value: Number(item.company_stock_quantity ?? item.stock ?? 0), fromUnit: false };
  }

  /** Mínimo a exibir, com a origem. Mesma regra de presença. */
  function minimumReading(item) {
    var hasUnit = item && item.unit_scope_id !== null && item.unit_scope_id !== undefined;
    if (hasUnit && item.unit_minimum_stock !== null && item.unit_minimum_stock !== undefined) {
      return {
        value: Number(item.unit_minimum_stock),
        source: String(item.minimum_stock_source || ''),
        fromUnit: true
      };
    }
    return { value: Number(item.minimum_stock ?? 0), source: 'company_default', fromUnit: false };
  }

  function minimumSourceLabel(source) {
    return trPair(MINIMUM_SOURCE_LABELS[source]) || '';
  }

  /** Faixa de atenção EXPLICADA, nunca recalculada.
   *
   * `attention_limit` é `ceil(mínimo × (1 + pct/100))` calculado com Decimal no
   * servidor. Refazer essa conta em JS com ponto flutuante daria divergências
   * de uma unidade justamente na fronteira que decide a cor. */
  function attentionHint(item) {
    if (!item || item.attention_limit === null || item.attention_limit === undefined) { return ''; }
    var pct = item.effective_attention_percentage;
    var base = tr('stock.attentionLimit', 'faixa de atenção até {n}')
      .replace('{n}', String(item.attention_limit));
    if (pct === null || pct === undefined) { return base; }
    return base + ' (' + String(pct) + '%)';
  }

  // ── Helpers internos ─────────────────────────────────────────────────────

  function formatStockEpiRow(item) {
    const sizesFromBalances = fmtSizeBalances(item.size_balances);
    const sizesFromEpi = [
      item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
      item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
      item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : ''
    ].filter(Boolean).join(', ');
    const sizesDisplay = sizesFromBalances || sizesFromEpi || '—';
    const saldo = stockReading(item);
    const minimo = minimumReading(item);
    // Sem Unidade resolvida os números são da EMPRESA. Dizê-lo é o que impede
    // que o operador leia um total corporativo como disponibilidade local.
    const escopoSaldo = saldo.fromUnit
      ? ''
      : ` <small>(${esc(tr('stock.companyTotal', 'total da empresa'))})</small>`;
    const origemMinimo = minimumSourceLabel(minimo.source);
    const faixa = attentionHint(item);
    const detalheMinimo = [origemMinimo, faixa].filter(Boolean).join(' · ');
    return `<tr>
    <td>${item.name}</td>
    <td>${epiProtectionLabel(item.sector)}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${item.unit_name || '-'}</td>
    <td>${sizesDisplay}</td>
    <td>${saldo.value} ${epiMeasureLabel(item.unit_measure)}(s)${escopoSaldo}</td>
    <td>${minimo.value}${detalheMinimo ? `<br><small>${esc(detalheMinimo)}</small>` : ''}</td>
    <td>${stockStatusBadge(item) || '<span class="muted">—</span>'}</td>
  </tr>`;
  }

  // ── Funções de render ─────────────────────────────────────────────────────

  function renderStockEpis() {
    const state = getState();
    const refs = getRefs();
    if (!refs.stockEpisTable) { return; }
    const rows = state.stockEpis || [];
    refs.stockEpisTable.innerHTML = rows.map(formatStockEpiRow).join('')
      || `<tr><td colspan="10">${tr('stock.noEpiForFilters', 'Nenhum EPI encontrado para os filtros.')}</td></tr>`;
    phase3Cards(refs.phase3EstoqueSummary, [
      { label: tr('stock.filteredItems', 'Itens filtrados'), value: rows.length },
      { label: tr('stock.lowStock', 'Estoque baixo'), value: (state.lowStock || []).length },
      { label: tr('stock.requests', 'Solicitações'), value: (state.requests || []).length }
    ]);
    phase3Status('estoque', 'success', tr('stock.itemsListed', '{count} item(ns) listado(s)').replace('{count}', rows.length));
  }

  function renderLowStock() {
    const refs = getRefs();
    if (!refs.stockLowList) { return; }
    const items = getState().lowStock || [];
    refs.stockLowList.innerHTML = items.map((item) => {
      // `severity` (critical/danger/warning) era uma TERCEIRA régua: nascia no
      // backend de `stock <= 0` / `stock < minimum`, independente da
      // classificação. Duas escalas para o mesmo fato divergem no primeiro
      // ajuste feito num lado só. A severidade agora é `stock_status`, a
      // mesma de toda a aplicação.
      const badge = stockStatusBadge(item);
      // `stock_condition` descreve a condição física e explica o número. Não
      // é severidade: um EPI pode estar `disabled` e ainda assim abaixo do
      // mínimo, e é isso que o operador precisa ler.
      const condicao = trPair(STOCK_CONDITION_LABELS[String(item.stock_condition || '')]);
      const sizeTag = (() => {
        if (!Array.isArray(item.size_balances) || !item.size_balances.length) { return ''; }
        const parts = item.size_balances.map((s) => {
          const label = [
            s.glove_size !== 'N/A' ? s.glove_size : '',
            s.size !== 'N/A' ? s.size : '',
            s.uniform_size !== 'N/A' ? s.uniform_size : ''
          ].filter(Boolean).join('/');
          return label ? `${label}:${s.quantity}` : '';
        }).filter(Boolean).join(', ');
        return parts ? ` [${parts}]` : '';
      })();
      // `/api/stock/low` já devolve `stock` e `minimum_stock` recortados NA
      // Unidade (saldo dela contra o mínimo efetivo dela) — não são os
      // corporativos de `/api/stock/epis`.
      const origemMinimo = minimumSourceLabel(String(item.minimum_stock_source || ''));
      const faixa = attentionHint(item);
      const explicacao = [condicao, origemMinimo, faixa].filter(Boolean).join(' · ');
      // Alerta desligado nunca some nem vira normal: o chip é cinza e o
      // estado FÍSICO continua sendo dito, porque o saldo não deixou de ser
      // o que é só porque o monitoramento foi desativado.
      const subjacente = item.stock_status === 'disabled'
        ? trPair(STOCK_STATUS_LABELS[String(item.underlying_status || '')])
        : '';
      const rodape = [
        badge || esc(tr('stock.statusUnknown', 'Sem classificação por Unidade')),
        subjacente ? esc(tr('stock.underlyingIs', 'condição atual: {s}').replace('{s}', subjacente)) : '',
        explicacao ? esc(explicacao) : ''
      ].filter(Boolean).join(' — ');
      return `<div class="summary-item"><strong>${item.company_name} / ${item.unit_name}</strong><div>${item.epi_name}${sizeTag}: ${item.stock} ${epiMeasureLabel(item.unit_measure)}(s) (${tr('stock.minimum', 'mínimo')} ${item.minimum_stock})</div><small>${rodape}</small></div>`;
    }).join('') || `<div class="summary-item">${tr('stock.noLowStockItems', 'Sem itens com estoque baixo.')}</div>`;
  }

  function renderRequests() {
    const refs = getRefs();
    if (!refs.requestsList) { return; }
    const items = (getState().requests || []).filter((r) => r.status === 'solicitado');
    refs.requestsList.innerHTML = items.map((item) => {
      const sizeInfo = [
        item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
        item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
        item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : ''
      ].filter(Boolean).join(' ') || '—';
      return `<div class="summary-item">
      <strong>${esc(item.employee_name || '—')}</strong>
      <div>${esc(item.employee_sector || '—')} / ${esc(item.employee_role || '—')} — ${esc(item.unit_name || '—')}</div>
      <div>${esc(item.epi_name || '—')} ${tr('epi.caShort', 'CA')}:${esc(item.ca || '—')} ${sizeInfo} × ${item.quantity}</div>
    </div>`;
    }).join('') || `<div class="summary-item">${tr('stock.noCriticalRequests', 'Sem solicitações críticas pendentes.')}</div>`;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const estoqueExports = {
    formatStockEpiRow,
    renderStockEpis,
    renderLowStock,
    renderRequests,
    // Exportados para serem TESTÁVEIS. São a fronteira entre o contrato do
    // backend e a tela: é neles que uma regressão de "corporativo virou
    // local" ou "disabled virou normal" apareceria primeiro.
    stockStatusBadge,
    stockReading,
    minimumReading,
    attentionHint
  };

  for (const [name, fn] of Object.entries(estoqueExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_ESTOQUE__ = Object.freeze({ ...estoqueExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, estoqueExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
