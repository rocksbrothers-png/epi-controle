/**
 * Módulo de Compras — Fases F1–F4 no web legado (§6.1 do plano técnico).
 *
 * Aba "Cotações" (RFQ multi-fornecedor, envio por e-mail/portal/API, resposta
 * manual, comparação e seleção da vencedora → PO pelo fluxo existente) e
 * modais de Catálogo do fornecedor, Integração de API (Nível 3) e ações de
 * Fornecedor/entrega na PO. Sem regra de negócio local: tudo via API.
 */
(function () {
  'use strict';

  function esc(value) {
    return (globalThis.escapeHtml ?? ((v) => String(v ?? '')))(value);
  }

  function getState() {
    return globalThis.__EPI_APP_STATE__ || globalThis.state || {};
  }

  function hasPermission(perm) {
    return typeof globalThis.hasPermission === 'function' ? globalThis.hasPermission(perm) : false;
  }

  function api(path, options) {
    const opts = { headers: { 'Content-Type': 'application/json', 'Accept-Language':globalThis.EpiI18n?.lang || 'pt-BR', ...(globalThis.authHeaders?.() || {}) }, ...options };
    return fetch(path, opts).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const fallback = globalThis.trEpi?.('ui.procurement.erro_p0_6b5d33','Erro {p0}',{p0:res.status}) || ('Erro '+res.status);
        const detail = globalThis.EpiI18n?.describeApiError?.(data, fallback);
        const error = new Error(detail?.text || data?.error?.message || data?.error || fallback);
        if (detail?.key) {error.i18n=detail;}
        error.status=res.status;error.code=data?.code || data?.error?.code || data?.validation?.code || '';error.payload=data;
        throw error;
      }
      return data;
    });
  }

  function withActor(body) {
    return JSON.stringify({ actor_user_id: getState().user?.id, ...(body || {}) });
  }

  function fmtBrl(v) {
    return (globalThis.fmtBrl ?? ((x, locale) => new Intl.NumberFormat(locale, {style:'currency', currency:'BRL'}).format(Number(x || 0))))(v, globalThis.EpiI18n?.lang || 'pt-BR');
  }

  function errorText(node, error, fallback) {
    const detail=error?.i18n;
    if (detail?.key && globalThis.EpiI18n?.textFor) {return globalThis.EpiI18n.textFor(node,detail.key,detail.text,detail.vars,detail.refs);}
    if (error?.message) {globalThis.EpiI18n?.clearBinding?.(node);return error.message;}
    return fallback();
  }

  function errorMarkup(error, fallback) {
    const detail=error?.i18n;
    return detail?.key && globalThis.EpiI18n?.bindText ? globalThis.EpiI18n.bindText(detail.key,detail.vars,detail.text,detail.refs) : esc(error?.message || fallback());
  }

  function toast(message, type) {
    if (typeof globalThis.showToast === 'function') {globalThis.showToast(message, type);}
    else {alert(message?.message || message);}
  }

  // ── Overlay/modal genérico (mesmo padrão de openPurchaseWorkflowModal) ─────

  function openOverlay(innerHtml, { width = '640px' } = {}) {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `<div class="card" style="width:min(${width},96vw);max-height:92vh;overflow-y:auto;padding:20px;">${innerHtml}</div>`;
    overlay.addEventListener('click', (e) => { if (e.target === overlay) {overlay.remove();} });
    document.body.appendChild(overlay);
    return overlay;
  }

  const QUOTE_STATUS_LABELS = {
    get ['draft']() { return (globalThis.trEpi?.('purchase.poStatus.draft','Rascunho',{}) ?? 'Rascunho'); }, get ['sent']() { return (globalThis.trEpi?.('portal.statusSent','Enviada',{}) ?? 'Enviada'); }, get ['answered']() { return (globalThis.trEpi?.('ui.procurement.respondida_0c7dac','Respondida',{}) ?? 'Respondida'); },
    get ['selected']() { return (globalThis.trEpi?.('ui.procurement.vencedora_364619','Vencedora',{}) ?? 'Vencedora'); }, get ['discarded']() { return (globalThis.trEpi?.('ui.procurement.descartada_ba5a36','Descartada',{}) ?? 'Descartada'); }, get ['expired']() { return (globalThis.trEpi?.('license.expired','Expirada',{}) ?? 'Expirada'); }, get ['declined']() { return (globalThis.trEpi?.('ui.procurement.recusada_e42aa2','Recusada',{}) ?? 'Recusada'); },
  };
  const CHANNEL_LABELS = { email: 'E-mail', get ['portal']() { return (globalThis.trEpi?.('nav.portal','Portal',{}) ?? 'Portal'); }, api: 'API', get ['manual']() { return (globalThis.trEpi?.('dataMigration.mapStrategy.manual','Manual',{}) ?? 'Manual'); } };

  let _quotesPrId = 0;
  let _quotesCache = [];

  // ── Aba Cotações ────────────────────────────────────────────────────────────

  async function loadCotacoes() {
    const select = document.getElementById('cotacoes-pr-select');
    if (!select) {return;}
    try {
      const res = await api(`/api/purchase-requests?actor_user_id=${getState().user?.id}`);
      const requests = (res.items || []).filter((r) => !['closed', 'cancelled', 'rejected'].includes(String(r.status || '')));
      const current = _quotesPrId || parseInt(select.value || '0', 10);
      select.innerHTML = '<option value="" data-i18n="ui.procurement.selecione_a_requisicao_6f457f">Selecione a requisi\u00e7\u00e3o\u2026</option>' + requests
        .map((r) => `<option value="${r.id}" ${r.id === current ? 'selected' : ''}>#${r.id} — ${esc(r.title || '')} (${esc(r.unit_name || '')})</option>`)
        .join('');
      if (current && requests.some((r) => r.id === current)) {
        select.value = String(current);
        await loadQuotesForSelectedPr();
      } else {
        _quotesPrId = 0;
        renderQuotes([], {});
      }
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_carregar_requisicoes_ec390a','Erro ao carregar requisi\u00e7\u00f5es.',{}) ?? 'Erro ao carregar requisi\u00e7\u00f5es.')), 'error');
    }
  }

  async function loadQuotesForSelectedPr() {
    const select = document.getElementById('cotacoes-pr-select');
    _quotesPrId = parseInt(select?.value || '0', 10);
    if (!_quotesPrId) { renderQuotes([], {}); return; }
    try {
      const res = await api(`/api/purchase-requests/${_quotesPrId}/quotes?actor_user_id=${getState().user?.id}`);
      _quotesCache = res.items || [];
      renderQuotes(_quotesCache, res.comparison || {});
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_carregar_cotacoes_a31470','Erro ao carregar cota\u00e7\u00f5es.',{}) ?? 'Erro ao carregar cota\u00e7\u00f5es.')), 'error');
    }
  }

  function renderQuotes(quotes, comparison) {
    const tbody = document.getElementById('cotacoes-tbody');
    const emptyEl = document.getElementById('cotacoes-empty');
    const newBtn = document.getElementById('cotacoes-new-btn');
    if (newBtn) {newBtn.style.display = _quotesPrId && hasPermission('quotes:manage') ? '' : 'none';}
    if (!tbody) {return;}
    const canManage = hasPermission('quotes:manage');
    if (!quotes.length) {
      tbody.innerHTML = '';
      if (emptyEl) { emptyEl.style.display = ''; emptyEl.textContent = _quotesPrId ? ((globalThis.EpiI18n?.textFor?.(emptyEl,'ui.procurement.nenhuma_cotacao_para_esta_requisicao_d40027','Nenhuma cota\u00e7\u00e3o para esta requisi\u00e7\u00e3o.',{}) ?? globalThis.trEpi?.('ui.procurement.nenhuma_cotacao_para_esta_requisicao_d40027','Nenhuma cota\u00e7\u00e3o para esta requisi\u00e7\u00e3o.',{})) ?? 'Nenhuma cota\u00e7\u00e3o para esta requisi\u00e7\u00e3o.') : ((globalThis.EpiI18n?.textFor?.(emptyEl,'ui.compras.selecione_uma_requisicao_para_ver_as_cotacoes_5fbe6c','Selecione uma requisi\u00e7\u00e3o para ver as cota\u00e7\u00f5es.',{}) ?? globalThis.trEpi?.('ui.compras.selecione_uma_requisicao_para_ver_as_cotacoes_5fbe6c','Selecione uma requisi\u00e7\u00e3o para ver as cota\u00e7\u00f5es.',{})) ?? 'Selecione uma requisi\u00e7\u00e3o para ver as cota\u00e7\u00f5es.'); }
      renderComparison({});
      return;
    }
    if (emptyEl) {emptyEl.style.display = 'none';}
    tbody.innerHTML = quotes.map((q) => {
      const isOpen = q.status === 'draft' || q.status === 'sent';
      const actions = [];
      if (canManage && isOpen) {
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'email')" data-i18n="ui.procurement.e_mail_1cc537">✉ E-mail</button>`);
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'portal')" data-i18n="ui.procurement.portal_8a0f71">🔗 Portal</button>`);
        if (String(q.supplier_integration_level || '') === 'api') {
          actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'api')" data-i18n="ui.procurement.cotar_via_api_f65c25">⚡ Cotar via API</button>`);
        }
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openAnswerQuoteModal(${q.id})" data-i18n="ui.procurement.registrar_resposta_100366">Registrar resposta</button>`);
      }
      if (canManage && q.status === 'answered') {
        actions.push(`<button class="btn" style="font-size:12px;padding:3px 8px;" onclick="selectQuoteWinner(${q.id})" data-i18n="ui.procurement.selecionar_vencedora_ba6811">★ Selecionar vencedora</button>`);
      }
      return `<tr>
        <td>#${q.id}</td>
        <td>${esc(q.supplier_name || '')}</td>
        <td>${esc(QUOTE_STATUS_LABELS[q.status] || q.status)}</td>
        <td>${esc(CHANNEL_LABELS[q.channel] || q.channel || '—')}</td>
        <td>${(q.answered_at || q.sent_at || '').slice(0, 10) || '—'}</td>
        <td>${q.freight_value ? fmtBrl(q.freight_value) : '—'}</td>
        <td style="white-space:nowrap;">${actions.join(' ') || '—'}</td>
      </tr>`;
    }).join('');
    renderComparison(comparison);
  }

  function renderComparison(comparison) {
    const container = document.getElementById('cotacoes-comparison');
    if (!container) {return;}
    const suppliers = comparison.suppliers || [];
    const items = comparison.items || [];
    if (!suppliers.length) { container.innerHTML = ''; return; }
    const totalsHtml = suppliers.map((s) => `<tr>
        <td>${esc(s.supplier_name || '')}</td>
        <td>${esc(QUOTE_STATUS_LABELS[s.status] || s.status)}</td>
        <td>${fmtBrl(s.items_total)}</td>
        <td>${fmtBrl(s.freight_value)}</td>
        <td style="font-weight:700;">${fmtBrl(s.total_with_freight)}</td>
        <td>${esc(s.payment_terms || '—')}</td>
      </tr>`).join('');
    const itemsHtml = items.map((item) => {
      const offers = (item.offers || []).map((o) => {
        const badges = [
          o.best_price ? '<span style="color:var(--color-success,green);font-weight:600;font-size:11px;" data-i18n="ui.procurement.melhor_preco_f90e4f">Melhor pre\u00e7o</span>' : '',
          o.best_lead_time ? '<span style="color:var(--color-info,#06c);font-weight:600;font-size:11px;" data-i18n="ui.procurement.melhor_prazo_da32c9">Melhor prazo</span>' : '',
        ].filter(Boolean).join(' ');
        return `<tr>
          <td style="padding-left:24px;">${esc(o.supplier_name || '')}</td>
          <td>${o.declined ? (globalThis.trEpi?.('portal.statusRefused','Recusado',{}) ?? 'Recusado') : fmtBrl(o.unit_price)}</td>
          <td>${o.declined ? '—' : `${o.lead_time_days || 0} dias`}</td>
          <td>${badges || '—'}</td>
        </tr>`;
      }).join('');
      return `<tr style="background:var(--color-bg-alt);"><td colspan="4" style="font-weight:600;">${esc(item.epi_name || '')} (x${item.quantity_requested || 0})</td></tr>${offers}`;
    }).join('');
    container.innerHTML = `
      <h4 style="margin:16px 0 8px;" data-i18n="ui.procurement.comparacao_por_fornecedor_aaed37">Comparação por fornecedor</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col" data-i18n="epi.supplierShort">Fornecedor</th><th scope="col" data-i18n="user.status">Status</th><th scope="col" data-i18n="validity.count">Itens</th><th scope="col" data-i18n="ui.compras.frete_7ae391">Frete</th><th scope="col" data-i18n="evaluation.total">Total</th><th scope="col" data-i18n="ui.procurement.pagamento_de58da">Pagamento</th></tr></thead>
        <tbody>${totalsHtml}</tbody>
      </table></div>
      <h4 style="margin:16px 0 8px;" data-i18n="ui.procurement.comparacao_por_item_607b24">Comparação por item</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col" data-i18n="epi.supplierShort">Fornecedor</th><th scope="col" data-i18n="ui.procurement.preco_unit_8b1e4c">Preço unit.</th><th scope="col" data-i18n="ui.procurement.prazo_f36758">Prazo</th><th scope="col"></th></tr></thead>
        <tbody>${itemsHtml}</tbody>
      </table></div>`;
  }

  async function openCreateRfqModal() {
    if (!_quotesPrId) { toast((globalThis.trEpi?.('ui.procurement.selecione_uma_requisicao_primeiro_f464a4','Selecione uma requisi\u00e7\u00e3o primeiro.',{}) ?? 'Selecione uma requisi\u00e7\u00e3o primeiro.'), 'error'); return; }
    let suppliers = [];
    try {
      const res = await api('/api/authorized-suppliers');
      suppliers = (res.items || []).filter((s) => s.active);
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_carregar_fornecedores_db079f','Erro ao carregar fornecedores.',{}) ?? 'Erro ao carregar fornecedores.')), 'error');
      return;
    }
    if (!suppliers.length) { toast((globalThis.trEpi?.('ui.procurement.cadastre_fornecedores_ativos_antes_de_cotar_3daa28','Cadastre fornecedores ativos antes de cotar.',{}) ?? 'Cadastre fornecedores ativos antes de cotar.'), 'error'); return; }
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.nova_cotacao_requisicao_p0_91ec0c',{p0:(_quotesPrId)},'Nova cota\u00e7\u00e3o \u2014 Requisi\u00e7\u00e3o #{p0}') ?? `Nova cotação — Requisição #${_quotesPrId}`)}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 10px;" data-i18n="ui.procurement.selecione_os_fornecedores_que_receberao_a_solicitacao_de_cotacao_c52d56">Selecione os fornecedores que receberão a solicitação de cotação.</p>
      <div style="max-height:260px;overflow:auto;border:1px solid var(--color-border);border-radius:6px;padding:8px;margin-bottom:12px;">
        ${suppliers.map((s) => `<label style="display:block;margin:4px 0;"><input type="checkbox" value="${s.id}" data-rfq-supplier> ${esc(s.name)} <span style="color:var(--color-text-muted);font-size:12px;">(${esc(CHANNEL_LABELS[s.integration_level] || s.integration_level || 'E-mail')})</span></label>`).join('')}
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-rfq-create data-i18n="ui.procurement.criar_cotacoes_ebb4e8">Criar cotações</button>
        <button class="btn ghost" data-rfq-cancel data-i18n="stock.physical.cancel">Cancelar</button>
      </div>
      <div data-rfq-feedback style="font-size:13px;margin-top:8px;color:var(--color-danger,#c00);"></div>`);
    overlay.querySelector('[data-rfq-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-rfq-create]').addEventListener('click', async () => {
      const ids = [...overlay.querySelectorAll('[data-rfq-supplier]:checked')].map((el) => parseInt(el.value, 10));
      const feedback = overlay.querySelector('[data-rfq-feedback]');
      if (!ids.length) { feedback.textContent = ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.selecione_ao_menos_um_fornecedor_d9c838','Selecione ao menos um fornecedor.',{}) ?? globalThis.trEpi?.('ui.procurement.selecione_ao_menos_um_fornecedor_d9c838','Selecione ao menos um fornecedor.',{})) ?? 'Selecione ao menos um fornecedor.'); return; }
      try {
        await api(`/api/purchase-requests/${_quotesPrId}/quotes`, { method: 'POST', body: withActor({ supplier_ids: ids }) });
        overlay.remove();
        toast((globalThis.trEpi?.('ui.procurement.cotacoes_criadas_a39c5b','Cota\u00e7\u00f5es criadas.',{}) ?? 'Cota\u00e7\u00f5es criadas.'), 'success');
        loadQuotesForSelectedPr();
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.erro_ao_criar_cotacoes_dd66e8','Erro ao criar cota\u00e7\u00f5es.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_criar_cotacoes_dd66e8','Erro ao criar cota\u00e7\u00f5es.',{})) ?? 'Erro ao criar cota\u00e7\u00f5es.'));
      }
    });
  }

  async function procurementSendQuote(quoteId, channel) {
    const paths = {
      email: `/api/quotes/${quoteId}/send`,
      portal: `/api/quotes/${quoteId}/portal-link`,
      api: `/api/quotes/${quoteId}/fetch-api`,
    };
    try {
      await api(paths[channel], { method: 'POST', body: withActor({}) });
      toast(channel === 'api' ? (globalThis.trEpi?.('ui.procurement.cotacao_respondida_via_api_b267f4','Cota\u00e7\u00e3o respondida via API.',{}) ?? 'Cota\u00e7\u00e3o respondida via API.') : (globalThis.trEpi?.('ui.procurement.enviado_ao_fornecedor_16f6bc','Enviado ao fornecedor.',{}) ?? 'Enviado ao fornecedor.'), 'success');
      loadQuotesForSelectedPr();
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_enviar_cotacao_58155a','Erro ao enviar cota\u00e7\u00e3o.',{}) ?? 'Erro ao enviar cota\u00e7\u00e3o.')), 'error');
    }
  }

  function openAnswerQuoteModal(quoteId) {
    const quote = _quotesCache.find((q) => q.id === quoteId);
    if (!quote) {return;}
    const items = quote.items || [];
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.registrar_resposta_p0_de9c0b',{p0:(quote.supplier_name || '')},'Registrar resposta \u2014 {p0}') ?? `Registrar resposta — ${esc(quote.supplier_name || '')}`)}</h3>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col" data-i18n="ui.purchases.item_652bcc">Item</th><th scope="col" data-i18n="stock.receipt.qty">Qtd</th><th scope="col" data-i18n="ui.procurement.preco_unit_r_6a0fde">Preço unit. (R$)</th><th scope="col" data-i18n="ui.procurement.prazo_dias_2b5f20">Prazo (dias)</th><th scope="col" data-i18n="ui.procurement.recusar_ce4328">Recusar</th></tr></thead>
        <tbody>
          ${items.map((i, idx) => `<tr>
            <td>${esc(i.epi_name || '')}</td>
            <td>${i.quantity_requested || 0}</td>
            <td><input type="number" min="0" step="0.01" style="width:110px;" data-answer-price="${idx}" value="${Number(i.unit_price) || ''}"></td>
            <td><input type="number" min="0" step="1" style="width:90px;" data-answer-lead="${idx}" value="${Number(i.lead_time_days) || ''}"></td>
            <td style="text-align:center;"><input type="checkbox" data-answer-declined="${idx}" ${i.declined ? 'checked' : ''}></td>
          </tr>`).join('')}
        </tbody>
      </table></div>
      <div class="form-grid" style="margin:12px 0;">
        <label data-i18n="ui.procurement.frete_r_4da93f">Frete (R$)<input type="number" min="0" step="0.01" data-answer-freight value="${Number(quote.freight_value) || ''}"></label>
        <label data-i18n="ui.procurement.condicoes_de_pagamento_aaf010">Condições de pagamento<input type="text" data-answer-payment value="${esc(quote.payment_terms || '')}"></label>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-answer-save data-i18n="ui.procurement.salvar_resposta_e4f3b2">Salvar resposta</button>
        <button class="btn ghost" data-answer-cancel data-i18n="stock.physical.cancel">Cancelar</button>
      </div>
      <div data-answer-feedback style="font-size:13px;margin-top:8px;color:var(--color-danger,#c00);"></div>`, { width: '760px' });
    overlay.querySelector('[data-answer-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-answer-save]').addEventListener('click', async () => {
      const body = {
        freight_value: parseFloat(overlay.querySelector('[data-answer-freight]').value || '0') || 0,
        payment_terms: overlay.querySelector('[data-answer-payment]').value || '',
        items: items.map((i, idx) => ({
          quote_item_id: i.id,
          unit_price: parseFloat(overlay.querySelector(`[data-answer-price="${idx}"]`).value || '0') || 0,
          lead_time_days: parseInt(overlay.querySelector(`[data-answer-lead="${idx}"]`).value || '0', 10) || 0,
          declined: overlay.querySelector(`[data-answer-declined="${idx}"]`).checked,
        })),
      };
      try {
        await api(`/api/quotes/${quoteId}/answer`, { method: 'POST', body: withActor(body) });
        overlay.remove();
        toast((globalThis.trEpi?.('ui.procurement.resposta_registrada_038f54','Resposta registrada.',{}) ?? 'Resposta registrada.'), 'success');
        loadQuotesForSelectedPr();
      } catch (err) {
        overlay.querySelector('[data-answer-feedback]').textContent = errorText(overlay.querySelector('[data-answer-feedback]'), err, () => ((globalThis.EpiI18n?.textFor?.(overlay.querySelector('[data-answer-feedback]'),'ui.procurement.erro_ao_salvar_61374a','Erro ao salvar.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_salvar_61374a','Erro ao salvar.',{})) ?? 'Erro ao salvar.'));
      }
    });
  }

  async function selectQuoteWinner(quoteId) {
    if (!confirm((globalThis.trEpi?.('ui.procurement.selecionar_esta_cotacao_como_vencedora_as_demais_cotacoes_abertas_serao_des_d88c99','Selecionar esta cota\u00e7\u00e3o como vencedora? As demais cota\u00e7\u00f5es abertas ser\u00e3o descartadas.',{}) ?? 'Selecionar esta cota\u00e7\u00e3o como vencedora? As demais cota\u00e7\u00f5es abertas ser\u00e3o descartadas.'))) {return;}
    try {
      const res = await api(`/api/quotes/${quoteId}/select`, { method: 'POST', body: withActor({}) });
      const draft = res.po_draft || {};
      loadQuotesForSelectedPr();
      if (draft.items?.length && confirm((globalThis.trEpi?.('ui.procurement.gerar_a_po_pre_preenchida_p0_itens_fornecedor_p1_ela_seguira_o_fluxo_normal_53eb17','Gerar a PO pr\u00e9-preenchida ({p0} itens, fornecedor {p1})? Ela seguir\u00e1 o fluxo normal de aprova\u00e7\u00e3o.',{p0:(draft.items.length),p1:(draft.supplier || '—')}) ?? `Gerar a PO pré-preenchida (${draft.items.length} itens, fornecedor ${draft.supplier || '—'})? Ela seguirá o fluxo normal de aprovação.`))) {
        const created = await api('/api/purchase-orders', { method: 'POST', body: withActor(draft) });
        toast((globalThis.trEpi?.('ui.procurement.po_p0_criada_a_partir_da_cotacao_ce3fab','PO #{p0} criada a partir da cota\u00e7\u00e3o.',{p0:(created.id || '')}) ?? `PO #${created.id || ''} criada a partir da cotação.`), 'success');
        globalThis.loadPurchaseOrders?.();
      }
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_selecionar_a_cotacao_4f0281','Erro ao selecionar a cota\u00e7\u00e3o.',{}) ?? 'Erro ao selecionar a cota\u00e7\u00e3o.')), 'error');
    }
  }

  // ── Catálogo do fornecedor ──────────────────────────────────────────────────

  async function openSupplierCatalogModal(supplierId, supplierName) {
    const canManage = hasPermission('suppliers:manage');
    const overlay = openOverlay(`
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <h3 style="margin:0;flex:1;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.catalogo_p0_be6287',{p0:(supplierName || '')},'Cat\u00e1logo \u2014 {p0}') ?? `Catálogo — ${esc(supplierName || '')}`)}</h3>
        ${canManage ? '<button class="btn ghost" data-catalog-sync style="font-size:12px;" data-i18n="ui.procurement.sincronizar_via_api_2efc32">\u27f3 Sincronizar via API</button>' : ''}
        <button class="btn ghost" data-catalog-close data-i18n="close">Fechar</button>
      </div>
      ${canManage ? `<div class="form-grid" style="margin-bottom:10px;">
        <label>SKU<input type="text" data-catalog-sku></label>
        <label data-i18n="ui.procurement.descricao_46332f">Descrição<input type="text" data-catalog-description></label>
        <label>CA<input type="text" data-catalog-ca></label>
        <label data-i18n="ui.procurement.ultimo_preco_r_5a9fb7">Último preço (R$)<input type="number" min="0" step="0.01" data-catalog-price></label>
        <label data-i18n="ui.procurement.prazo_dias_2b5f20">Prazo (dias)<input type="number" min="0" step="1" data-catalog-lead></label>
        <label style="align-self:end;"><button class="btn" data-catalog-save data-i18n="ui.procurement.salvar_produto_d0aeee">Salvar produto</button></label>
      </div>` : ''}
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">SKU</th><th scope="col" data-i18n="ui.procurement.descricao_46332f">Descrição</th><th scope="col">CA</th><th scope="col" data-i18n="ui.procurement.ult_preco_553bfd">Últ. preço</th><th scope="col" data-i18n="ui.procurement.prazo_f36758">Prazo</th><th scope="col"></th></tr></thead>
        <tbody data-catalog-tbody></tbody>
      </table></div>
      <div data-catalog-feedback style="font-size:13px;margin-top:8px;"></div>`, { width: '820px' });
    overlay.querySelector('[data-catalog-close]').addEventListener('click', () => overlay.remove());

    async function refresh() {
      const tbody = overlay.querySelector('[data-catalog-tbody]');
      try {
        const res = await api(`/api/authorized-suppliers/${supplierId}/products?actor_user_id=${getState().user?.id}`);
        const items = res.items || [];
        tbody.innerHTML = items.length ? items.map((p) => `<tr>
            <td>${esc(p.supplier_sku || '—')}</td>
            <td>${esc(p.description || '—')}</td>
            <td>${esc(p.ca || '—')}</td>
            <td>${p.last_price ? fmtBrl(p.last_price) : '—'}</td>
            <td>${p.lead_time_days || '—'}</td>
            <td>${canManage ? `<button class="btn ghost" style="font-size:12px;padding:2px 8px;" data-catalog-remove="${p.id}" data-i18n="ui.procurement.desativar_67afbe">Desativar</button>` : ''}</td>
          </tr>`).join('') : '<tr><td colspan="6" style="text-align:center;color:var(--color-text-muted);" data-i18n="ui.procurement.nenhum_produto_no_catalogo_e3de92">Nenhum produto no cat\u00e1logo.</td></tr>';
        tbody.querySelectorAll('[data-catalog-remove]').forEach((btn) => btn.addEventListener('click', async () => {
          await api(`/api/supplier-products/${btn.getAttribute('data-catalog-remove')}?actor_user_id=${getState().user?.id}`, { method: 'DELETE' });
          refresh();
        }));
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="color:var(--color-danger,#c00);">${errorMarkup(err, () => (globalThis.trEpi?.('ui.procurement.erro_ao_carregar_catalogo_00941e','Erro ao carregar cat\u00e1logo.',{}) ?? 'Erro ao carregar cat\u00e1logo.'))}</td></tr>`;
      }
    }

    overlay.querySelector('[data-catalog-save]')?.addEventListener('click', async () => {
      const feedback = overlay.querySelector('[data-catalog-feedback]');
      try {
        await api(`/api/authorized-suppliers/${supplierId}/products`, {
          method: 'POST',
          body: withActor({
            supplier_sku: overlay.querySelector('[data-catalog-sku]').value.trim(),
            description: overlay.querySelector('[data-catalog-description]').value.trim(),
            ca: overlay.querySelector('[data-catalog-ca]').value.trim(),
            last_price: parseFloat(overlay.querySelector('[data-catalog-price]').value || '0') || 0,
            lead_time_days: parseInt(overlay.querySelector('[data-catalog-lead]').value || '0', 10) || 0,
          }),
        });
        feedback.textContent = '';
        refresh();
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.erro_ao_salvar_produto_2dc40c','Erro ao salvar produto.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_salvar_produto_2dc40c','Erro ao salvar produto.',{})) ?? 'Erro ao salvar produto.'));
      }
    });
    overlay.querySelector('[data-catalog-sync]')?.addEventListener('click', async () => {
      const feedback = overlay.querySelector('[data-catalog-feedback]');
      try {
        const res = await api(`/api/authorized-suppliers/${supplierId}/catalog-sync`, { method: 'POST', body: withActor({}) });
        feedback.textContent = ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.catalogo_sincronizado_p0_produtos_importados_da_loja_3f7094','Cat\u00e1logo sincronizado: {p0} produtos importados da loja.',{p0:(res.imported)}) ?? globalThis.trEpi?.('ui.procurement.catalogo_sincronizado_p0_produtos_importados_da_loja_3f7094','Cat\u00e1logo sincronizado: {p0} produtos importados da loja.',{p0:(res.imported)})) ?? `Catálogo sincronizado: ${res.imported} produtos importados da loja.`);
        refresh();
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.erro_ao_sincronizar_o_fornecedor_tem_integracao_de_api_ativa_e7a3e4','Erro ao sincronizar (o fornecedor tem integra\u00e7\u00e3o de API ativa?).',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_sincronizar_o_fornecedor_tem_integracao_de_api_ativa_e7a3e4','Erro ao sincronizar (o fornecedor tem integra\u00e7\u00e3o de API ativa?).',{})) ?? 'Erro ao sincronizar (o fornecedor tem integra\u00e7\u00e3o de API ativa?).'));
      }
    });
    refresh();
  }

  // ── Integração de API (Nível 3) ─────────────────────────────────────────────

  async function openSupplierIntegrationModal(supplierId, supplierName) {
    let connectors = [];
    let integration = null;
    try {
      const res = await api(`/api/supplier-connectors?actor_user_id=${getState().user?.id}`);
      connectors = res.items || [];
    } catch { /* segue com lista vazia */ }
    try {
      const res = await api(`/api/authorized-suppliers/${supplierId}/integration?actor_user_id=${getState().user?.id}`);
      integration = res.item || null;
    } catch { /* 404 = sem integração ainda */ }
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.integracao_de_api_p0_f7aa27',{p0:(supplierName || '')},'Integra\u00e7\u00e3o de API \u2014 {p0}') ?? `Integração de API — ${esc(supplierName || '')}`)}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 10px;" data-i18n="ui.procurement.nivel_3_o_sistema_cota_e_envia_pedidos_direto_na_loja_as_credenciais_sao_gr_380ade">Nível 3: o sistema cota e envia pedidos direto na loja. As credenciais são gravadas cifradas.</p>
      <div class="form-grid" style="margin-bottom:10px;">
        <label data-i18n="ui.procurement.conector_db5b06">Conector<select data-integration-key>${connectors.map((c) => `<option value="${esc(c.key)}" ${integration?.connector_key === c.key ? 'selected' : ''}>${esc(c.label)}</option>`).join('')}</select></label>
        <label data-i18n="license.active">Ativa<select data-integration-active><option value="1" ${integration?.active ? 'selected' : ''} data-i18n="common.yes">Sim</option><option value="0" ${integration && !integration.active ? 'selected' : ''} data-i18n="common.no">Não</option></select></label>
      </div>
      <label style="display:block;margin-bottom:10px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.configuracao_json_p4_e56e03',{p4:(integration?.has_config ? (globalThis.trEpi?.('ui.procurement.ja_existe_deixe_em_branco_para_manter_6bab2b',' \u2014 j\u00e1 existe; deixe em branco para manter',{}) ?? ' \u2014 j\u00e1 existe; deixe em branco para manter') : '')},'Configura\u00e7\u00e3o (JSON{p4})',integration?.has_config ? {p4:'ui.procurement.ja_existe_deixe_em_branco_para_manter_6bab2b'} : {}) ?? `Configuração (JSON${integration?.has_config ? (globalThis.trEpi?.('ui.procurement.ja_existe_deixe_em_branco_para_manter_6bab2b',' \u2014 j\u00e1 existe; deixe em branco para manter',{}) ?? ' \u2014 j\u00e1 existe; deixe em branco para manter') : ''})`)}
        <textarea data-integration-config rows="5" style="width:100%;font-family:monospace;font-size:12px;" placeholder='{"base_url": "https://api.loja.com.br", "api_key": "..."}'></textarea>
      </label>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-integration-save data-i18n="commercial.save">Salvar</button>
        <button class="btn ghost" data-integration-test data-i18n="ui.procurement.testar_conexao_e5f454">Testar conexão</button>
        <button class="btn ghost" data-integration-cancel data-i18n="close">Fechar</button>
      </div>
      <div data-integration-feedback style="font-size:13px;margin-top:8px;"></div>`);
    const feedback = overlay.querySelector('[data-integration-feedback]');
    overlay.querySelector('[data-integration-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-integration-save]').addEventListener('click', async () => {
      const rawConfig = overlay.querySelector('[data-integration-config]').value.trim();
      let config;
      if (rawConfig) {
        try { config = JSON.parse(rawConfig); } catch { feedback.textContent = ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.configuracao_nao_e_um_json_valido_d6850b','Configura\u00e7\u00e3o n\u00e3o \u00e9 um JSON v\u00e1lido.',{}) ?? globalThis.trEpi?.('ui.procurement.configuracao_nao_e_um_json_valido_d6850b','Configura\u00e7\u00e3o n\u00e3o \u00e9 um JSON v\u00e1lido.',{})) ?? 'Configura\u00e7\u00e3o n\u00e3o \u00e9 um JSON v\u00e1lido.'); return; }
      }
      try {
        await api(`/api/authorized-suppliers/${supplierId}/integration`, {
          method: 'POST',
          body: withActor({
            connector_key: overlay.querySelector('[data-integration-key]').value,
            active: overlay.querySelector('[data-integration-active]').value === '1',
            ...(config !== undefined ? { config } : {}),
          }),
        });
        feedback.textContent = ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.integracao_salva_f8e88a','Integra\u00e7\u00e3o salva.',{}) ?? globalThis.trEpi?.('ui.procurement.integracao_salva_f8e88a','Integra\u00e7\u00e3o salva.',{})) ?? 'Integra\u00e7\u00e3o salva.');
        globalThis.loadAuthorizedSuppliers?.();
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.erro_ao_salvar_integracao_7c9c38','Erro ao salvar integra\u00e7\u00e3o.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_salvar_integracao_7c9c38','Erro ao salvar integra\u00e7\u00e3o.',{})) ?? 'Erro ao salvar integra\u00e7\u00e3o.'));
      }
    });
    overlay.querySelector('[data-integration-test]').addEventListener('click', async () => {
      try {
        const res = await api(`/api/authorized-suppliers/${supplierId}/integration/test`, { method: 'POST', body: withActor({}) });
        feedback.textContent = ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.conexao_ok_p0_c8552e','Conex\u00e3o OK ({p0}).',{p0:(res.connector_key)}) ?? globalThis.trEpi?.('ui.procurement.conexao_ok_p0_c8552e','Conex\u00e3o OK ({p0}).',{p0:(res.connector_key)})) ?? `Conexão OK (${res.connector_key}).`);
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.teste_falhou_a64e41','Teste falhou.',{}) ?? globalThis.trEpi?.('ui.procurement.teste_falhou_a64e41','Teste falhou.',{})) ?? 'Teste falhou.'));
      }
    });
  }

  // ── Fornecedor e entrega na PO ──────────────────────────────────────────────

  async function openPoSupplierActionsModal(poId) {
    let tracking = {};
    try {
      const res = await api(`/api/purchase-orders/${poId}/tracking?actor_user_id=${getState().user?.id}`);
      tracking = res.item || {};
    } catch (err) {
      toast((err.i18n ? err : err.message || (globalThis.trEpi?.('ui.procurement.erro_ao_carregar_acompanhamento_2142fc','Erro ao carregar acompanhamento.',{}) ?? 'Erro ao carregar acompanhamento.')), 'error');
      return;
    }
    const canSend = hasPermission('purchase_orders:create');
    const confirmations = tracking.confirmations || [];
    const historyHtml = confirmations.length ? confirmations.map((c) => `<tr>
        <td>${(c.created_at || '').slice(0, 10)}</td>
        <td>${esc(c.status || '')}</td>
        <td>${esc(c.source || '')}</td>
        <td style="font-size:12px;">${[c.delivery_forecast, c.carrier, c.tracking_code, c.comment].filter(Boolean).map(esc).join(' — ') || '—'}</td>
      </tr>`).join('') : '<tr><td colspan="4" style="text-align:center;color:var(--color-text-muted);" data-i18n="ui.procurement.sem_registros_de_acompanhamento_273b54">Sem registros de acompanhamento.</td></tr>';
    const overlay = openOverlay(`
      <h3 style="margin:0 0 6px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.fornecedor_e_entrega_po_p0_54889c',{p0:(poId)},'Fornecedor e entrega \u2014 PO #{p0}') ?? `Fornecedor e entrega — PO #${poId}`)}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 12px;">
        <span data-i18n="ui.procurement.envio_182b19">Envio:</span> ${tracking.sent_channel ? `${esc(CHANNEL_LABELS[tracking.sent_channel] || tracking.sent_channel)} em ${(tracking.sent_to_supplier_at || '').slice(0, 10)}` : (globalThis.trEpi?.('ui.procurement.ainda_nao_enviada_485986','ainda n\u00e3o enviada',{}) ?? 'ainda n\u00e3o enviada')}
        ${tracking.supplier_confirmation_status ? ` · Confirmação: <strong>${esc(tracking.supplier_confirmation_status)}</strong>` : ''}
      </p>
      ${canSend ? `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
        <button class="btn" data-po-send="send" data-i18n="ui.procurement.enviar_por_e_mail_ad24a6">✉ Enviar por e-mail</button>
        <button class="btn ghost" data-po-send="portal-link" data-i18n="ui.procurement.enviar_link_do_portal_43fff2">🔗 Enviar link do portal</button>
        <button class="btn ghost" data-po-send="send-api" data-i18n="ui.procurement.enviar_via_api_aca832">⚡ Enviar via API</button>
        <button class="btn ghost" data-po-send="refresh-status" data-i18n="ui.procurement.atualizar_status_api_769b8a">⟳ Atualizar status (API)</button>
        <button class="btn ghost" data-po-confirm data-i18n="ui.procurement.registrar_confirmacao_manual_e6e72c">Registrar confirmação manual</button>
      </div>` : ''}
      <h4 style="margin:8px 0;" data-i18n="ui.procurement.linha_do_tempo_2bbefc">Linha do tempo</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col" data-i18n="outsourcedCompany.requestDate">Data</th><th scope="col" data-i18n="user.status">Status</th><th scope="col" data-i18n="dataMigration.jobSource">Origem</th><th scope="col" data-i18n="tabs.details">Detalhes</th></tr></thead>
        <tbody>${historyHtml}</tbody>
      </table></div>
      <div style="display:flex;gap:8px;margin-top:12px;"><button class="btn ghost" data-po-close data-i18n="close">Fechar</button></div>
      <div data-po-feedback style="font-size:13px;margin-top:8px;"></div>`, { width: '760px' });
    const feedback = overlay.querySelector('[data-po-feedback]');
    overlay.querySelector('[data-po-close]').addEventListener('click', () => overlay.remove());
    overlay.querySelectorAll('[data-po-send]').forEach((btn) => btn.addEventListener('click', async () => {
      try {
        await api(`/api/purchase-orders/${poId}/${btn.getAttribute('data-po-send')}`, { method: 'POST', body: withActor({}) });
        overlay.remove();
        toast((globalThis.trEpi?.('ui.procurement.acao_executada_789459','A\u00e7\u00e3o executada.',{}) ?? 'A\u00e7\u00e3o executada.'), 'success');
        openPoSupplierActionsModal(poId);
      } catch (err) {
        feedback.textContent = errorText(feedback, err, () => ((globalThis.EpiI18n?.textFor?.(feedback,'ui.procurement.erro_ao_executar_a_acao_f6d97b','Erro ao executar a a\u00e7\u00e3o.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_executar_a_acao_f6d97b','Erro ao executar a a\u00e7\u00e3o.',{})) ?? 'Erro ao executar a a\u00e7\u00e3o.'));
      }
    }));
    overlay.querySelector('[data-po-confirm]')?.addEventListener('click', () => {
      overlay.remove();
      openPoConfirmationModal(poId);
    });
  }

  function openPoConfirmationModal(poId) {
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">${(globalThis.EpiI18n?.bindText?.('ui.procurement.registrar_confirmacao_po_p0_55110a',{p0:(poId)},'Registrar confirma\u00e7\u00e3o \u2014 PO #{p0}') ?? `Registrar confirmação — PO #${poId}`)}</h3>
      <div class="form-grid" style="margin-bottom:10px;">
        <label data-i18n="ui.procurement.retorno_do_fornecedor_17993b">Retorno do fornecedor<select data-confirm-status>
          <option value="confirmed" data-i18n="ui.procurement.pedido_confirmado_7ef09b">Pedido confirmado</option>
          <option value="delivery_update" data-i18n="ui.procurement.atualizacao_de_entrega_aa0722">Atualização de entrega</option>
          <option value="rejected" data-i18n="ui.procurement.pedido_recusado_5aa140">Pedido recusado</option>
        </select></label>
        <label data-i18n="ui.procurement.previsao_de_entrega_2b8745">Previsão de entrega<input type="date" data-confirm-forecast></label>
        <label data-i18n="ui.procurement.transportadora_efbe6a">Transportadora<input type="text" data-confirm-carrier></label>
        <label data-i18n="ui.procurement.codigo_de_rastreio_265785">Código de rastreio<input type="text" data-confirm-tracking></label>
      </div>
      <label style="display:block;margin-bottom:10px;" data-i18n="evaluation.comment">Comentário<input type="text" data-confirm-comment></label>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-confirm-save data-i18n="deliveryTabs.register">Registrar</button>
        <button class="btn ghost" data-confirm-cancel data-i18n="stock.physical.cancel">Cancelar</button>
      </div>
      <div data-confirm-feedback style="font-size:13px;margin-top:8px;color:var(--color-danger,#c00);"></div>`);
    overlay.querySelector('[data-confirm-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-confirm-save]').addEventListener('click', async () => {
      try {
        await api(`/api/purchase-orders/${poId}/confirmation`, {
          method: 'POST',
          body: withActor({
            status: overlay.querySelector('[data-confirm-status]').value,
            delivery_forecast: overlay.querySelector('[data-confirm-forecast]').value,
            carrier: overlay.querySelector('[data-confirm-carrier]').value.trim(),
            tracking_code: overlay.querySelector('[data-confirm-tracking]').value.trim(),
            comment: overlay.querySelector('[data-confirm-comment]').value.trim(),
          }),
        });
        overlay.remove();
        toast((globalThis.trEpi?.('ui.procurement.confirmacao_registrada_0036b0','Confirma\u00e7\u00e3o registrada.',{}) ?? 'Confirma\u00e7\u00e3o registrada.'), 'success');
        openPoSupplierActionsModal(poId);
      } catch (err) {
        overlay.querySelector('[data-confirm-feedback]').textContent = errorText(overlay.querySelector('[data-confirm-feedback]'), err, () => ((globalThis.EpiI18n?.textFor?.(overlay.querySelector('[data-confirm-feedback]'),'ui.procurement.erro_ao_registrar_ce0cc7','Erro ao registrar.',{}) ?? globalThis.trEpi?.('ui.procurement.erro_ao_registrar_ce0cc7','Erro ao registrar.',{})) ?? 'Erro ao registrar.'));
      }
    });
  }

  // ── Init ────────────────────────────────────────────────────────────────────

  function initProcurement() {
    const select = document.getElementById('cotacoes-pr-select');
    if (select) {select.addEventListener('change', loadQuotesForSelectedPr);}
    const newBtn = document.getElementById('cotacoes-new-btn');
    if (newBtn) {newBtn.addEventListener('click', openCreateRfqModal);}
    const refreshBtn = document.getElementById('cotacoes-refresh');
    if (refreshBtn) {refreshBtn.addEventListener('click', loadCotacoes);}
  }

  // ── Exports ────────────────────────────────────────────────────────────────

  globalThis.loadCotacoes = loadCotacoes;
  globalThis.procurementSendQuote = procurementSendQuote;
  globalThis.openAnswerQuoteModal = openAnswerQuoteModal;
  globalThis.selectQuoteWinner = selectQuoteWinner;
  globalThis.openSupplierCatalogModal = openSupplierCatalogModal;
  globalThis.openSupplierIntegrationModal = openSupplierIntegrationModal;
  globalThis.openPoSupplierActionsModal = openPoSupplierActionsModal;
  globalThis.initProcurement = initProcurement;

  globalThis.__EPI_PROCUREMENT__ = Object.freeze({
    loadCotacoes,
    procurementSendQuote,
    openAnswerQuoteModal,
    selectQuoteWinner,
    openSupplierCatalogModal,
    openSupplierIntegrationModal,
    openPoSupplierActionsModal,
    initProcurement,
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProcurement);
  } else {
    initProcurement();
  }
})();
