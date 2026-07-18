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
    const opts = { headers: { 'Content-Type': 'application/json', ...(globalThis.authHeaders?.() || {}) }, ...options };
    return fetch(path, opts).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {throw new Error(data?.error?.message || data?.error || `Erro ${res.status}`);}
      return data;
    });
  }

  function withActor(body) {
    return JSON.stringify({ actor_user_id: getState().user?.id, ...(body || {}) });
  }

  function fmtBrl(v) {
    return (globalThis.fmtBrl ?? ((x) => `R$ ${Number(x || 0).toFixed(2)}`))(v);
  }

  function toast(message, type) {
    if (typeof globalThis.showToast === 'function') {globalThis.showToast(message, type);}
    else {alert(message);}
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
    draft: 'Rascunho', sent: 'Enviada', answered: 'Respondida',
    selected: 'Vencedora', discarded: 'Descartada', expired: 'Expirada', declined: 'Recusada',
  };
  const CHANNEL_LABELS = { email: 'E-mail', portal: 'Portal', api: 'API', manual: 'Manual' };

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
      select.innerHTML = '<option value="">Selecione a requisição…</option>' + requests
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
      toast(err.message || 'Erro ao carregar requisições.', 'error');
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
      toast(err.message || 'Erro ao carregar cotações.', 'error');
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
      if (emptyEl) { emptyEl.style.display = ''; emptyEl.textContent = _quotesPrId ? 'Nenhuma cotação para esta requisição.' : 'Selecione uma requisição para ver as cotações.'; }
      renderComparison({});
      return;
    }
    if (emptyEl) {emptyEl.style.display = 'none';}
    tbody.innerHTML = quotes.map((q) => {
      const isOpen = q.status === 'draft' || q.status === 'sent';
      const actions = [];
      if (canManage && isOpen) {
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'email')">✉ E-mail</button>`);
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'portal')">🔗 Portal</button>`);
        if (String(q.supplier_integration_level || '') === 'api') {
          actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="procurementSendQuote(${q.id}, 'api')">⚡ Cotar via API</button>`);
        }
        actions.push(`<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openAnswerQuoteModal(${q.id})">Registrar resposta</button>`);
      }
      if (canManage && q.status === 'answered') {
        actions.push(`<button class="btn" style="font-size:12px;padding:3px 8px;" onclick="selectQuoteWinner(${q.id})">★ Selecionar vencedora</button>`);
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
          o.best_price ? '<span style="color:var(--color-success,green);font-weight:600;font-size:11px;">Melhor preço</span>' : '',
          o.best_lead_time ? '<span style="color:var(--color-info,#06c);font-weight:600;font-size:11px;">Melhor prazo</span>' : '',
        ].filter(Boolean).join(' ');
        return `<tr>
          <td style="padding-left:24px;">${esc(o.supplier_name || '')}</td>
          <td>${o.declined ? 'Recusado' : fmtBrl(o.unit_price)}</td>
          <td>${o.declined ? '—' : `${o.lead_time_days || 0} dias`}</td>
          <td>${badges || '—'}</td>
        </tr>`;
      }).join('');
      return `<tr style="background:var(--color-bg-alt);"><td colspan="4" style="font-weight:600;">${esc(item.epi_name || '')} (x${item.quantity_requested || 0})</td></tr>${offers}`;
    }).join('');
    container.innerHTML = `
      <h4 style="margin:16px 0 8px;">Comparação por fornecedor</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">Fornecedor</th><th scope="col">Status</th><th scope="col">Itens</th><th scope="col">Frete</th><th scope="col">Total</th><th scope="col">Pagamento</th></tr></thead>
        <tbody>${totalsHtml}</tbody>
      </table></div>
      <h4 style="margin:16px 0 8px;">Comparação por item</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">Fornecedor</th><th scope="col">Preço unit.</th><th scope="col">Prazo</th><th scope="col"></th></tr></thead>
        <tbody>${itemsHtml}</tbody>
      </table></div>`;
  }

  async function openCreateRfqModal() {
    if (!_quotesPrId) { toast('Selecione uma requisição primeiro.', 'error'); return; }
    let suppliers = [];
    try {
      const res = await api('/api/authorized-suppliers');
      suppliers = (res.items || []).filter((s) => s.active);
    } catch (err) {
      toast(err.message || 'Erro ao carregar fornecedores.', 'error');
      return;
    }
    if (!suppliers.length) { toast('Cadastre fornecedores ativos antes de cotar.', 'error'); return; }
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">Nova cotação — Requisição #${_quotesPrId}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 10px;">Selecione os fornecedores que receberão a solicitação de cotação.</p>
      <div style="max-height:260px;overflow:auto;border:1px solid var(--color-border);border-radius:6px;padding:8px;margin-bottom:12px;">
        ${suppliers.map((s) => `<label style="display:block;margin:4px 0;"><input type="checkbox" value="${s.id}" data-rfq-supplier> ${esc(s.name)} <span style="color:var(--color-text-muted);font-size:12px;">(${esc(CHANNEL_LABELS[s.integration_level] || s.integration_level || 'E-mail')})</span></label>`).join('')}
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-rfq-create>Criar cotações</button>
        <button class="btn ghost" data-rfq-cancel>Cancelar</button>
      </div>
      <div data-rfq-feedback style="font-size:13px;margin-top:8px;color:var(--color-danger,#c00);"></div>`);
    overlay.querySelector('[data-rfq-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-rfq-create]').addEventListener('click', async () => {
      const ids = [...overlay.querySelectorAll('[data-rfq-supplier]:checked')].map((el) => parseInt(el.value, 10));
      const feedback = overlay.querySelector('[data-rfq-feedback]');
      if (!ids.length) { feedback.textContent = 'Selecione ao menos um fornecedor.'; return; }
      try {
        await api(`/api/purchase-requests/${_quotesPrId}/quotes`, { method: 'POST', body: withActor({ supplier_ids: ids }) });
        overlay.remove();
        toast('Cotações criadas.', 'success');
        loadQuotesForSelectedPr();
      } catch (err) {
        feedback.textContent = err.message || 'Erro ao criar cotações.';
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
      toast(channel === 'api' ? 'Cotação respondida via API.' : 'Enviado ao fornecedor.', 'success');
      loadQuotesForSelectedPr();
    } catch (err) {
      toast(err.message || 'Erro ao enviar cotação.', 'error');
    }
  }

  function openAnswerQuoteModal(quoteId) {
    const quote = _quotesCache.find((q) => q.id === quoteId);
    if (!quote) {return;}
    const items = quote.items || [];
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">Registrar resposta — ${esc(quote.supplier_name || '')}</h3>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">Item</th><th scope="col">Qtd</th><th scope="col">Preço unit. (R$)</th><th scope="col">Prazo (dias)</th><th scope="col">Recusar</th></tr></thead>
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
        <label>Frete (R$)<input type="number" min="0" step="0.01" data-answer-freight value="${Number(quote.freight_value) || ''}"></label>
        <label>Condições de pagamento<input type="text" data-answer-payment value="${esc(quote.payment_terms || '')}"></label>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-answer-save>Salvar resposta</button>
        <button class="btn ghost" data-answer-cancel>Cancelar</button>
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
        toast('Resposta registrada.', 'success');
        loadQuotesForSelectedPr();
      } catch (err) {
        overlay.querySelector('[data-answer-feedback]').textContent = err.message || 'Erro ao salvar.';
      }
    });
  }

  async function selectQuoteWinner(quoteId) {
    if (!confirm('Selecionar esta cotação como vencedora? As demais cotações abertas serão descartadas.')) {return;}
    try {
      const res = await api(`/api/quotes/${quoteId}/select`, { method: 'POST', body: withActor({}) });
      const draft = res.po_draft || {};
      loadQuotesForSelectedPr();
      if (draft.items?.length && confirm(`Gerar a PO pré-preenchida (${draft.items.length} itens, fornecedor ${draft.supplier || '—'})? Ela seguirá o fluxo normal de aprovação.`)) {
        const created = await api('/api/purchase-orders', { method: 'POST', body: withActor(draft) });
        toast(`PO #${created.id || ''} criada a partir da cotação.`, 'success');
        globalThis.loadPurchaseOrders?.();
      }
    } catch (err) {
      toast(err.message || 'Erro ao selecionar a cotação.', 'error');
    }
  }

  // ── Catálogo do fornecedor ──────────────────────────────────────────────────

  async function openSupplierCatalogModal(supplierId, supplierName) {
    const canManage = hasPermission('suppliers:manage');
    const overlay = openOverlay(`
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <h3 style="margin:0;flex:1;">Catálogo — ${esc(supplierName || '')}</h3>
        ${canManage ? '<button class="btn ghost" data-catalog-sync style="font-size:12px;">⟳ Sincronizar via API</button>' : ''}
        <button class="btn ghost" data-catalog-close>Fechar</button>
      </div>
      ${canManage ? `<div class="form-grid" style="margin-bottom:10px;">
        <label>SKU<input type="text" data-catalog-sku></label>
        <label>Descrição<input type="text" data-catalog-description></label>
        <label>CA<input type="text" data-catalog-ca></label>
        <label>Último preço (R$)<input type="number" min="0" step="0.01" data-catalog-price></label>
        <label>Prazo (dias)<input type="number" min="0" step="1" data-catalog-lead></label>
        <label style="align-self:end;"><button class="btn" data-catalog-save>Salvar produto</button></label>
      </div>` : ''}
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">SKU</th><th scope="col">Descrição</th><th scope="col">CA</th><th scope="col">Últ. preço</th><th scope="col">Prazo</th><th scope="col"></th></tr></thead>
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
            <td>${canManage ? `<button class="btn ghost" style="font-size:12px;padding:2px 8px;" data-catalog-remove="${p.id}">Desativar</button>` : ''}</td>
          </tr>`).join('') : '<tr><td colspan="6" style="text-align:center;color:var(--color-text-muted);">Nenhum produto no catálogo.</td></tr>';
        tbody.querySelectorAll('[data-catalog-remove]').forEach((btn) => btn.addEventListener('click', async () => {
          await api(`/api/supplier-products/${btn.getAttribute('data-catalog-remove')}?actor_user_id=${getState().user?.id}`, { method: 'DELETE' });
          refresh();
        }));
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="color:var(--color-danger,#c00);">${esc(err.message || 'Erro ao carregar catálogo.')}</td></tr>`;
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
        feedback.textContent = err.message || 'Erro ao salvar produto.';
      }
    });
    overlay.querySelector('[data-catalog-sync]')?.addEventListener('click', async () => {
      const feedback = overlay.querySelector('[data-catalog-feedback]');
      try {
        const res = await api(`/api/authorized-suppliers/${supplierId}/catalog-sync`, { method: 'POST', body: withActor({}) });
        feedback.textContent = `Catálogo sincronizado: ${res.imported} produtos importados da loja.`;
        refresh();
      } catch (err) {
        feedback.textContent = err.message || 'Erro ao sincronizar (o fornecedor tem integração de API ativa?).';
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
      <h3 style="margin:0 0 12px;">Integração de API — ${esc(supplierName || '')}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 10px;">Nível 3: o sistema cota e envia pedidos direto na loja. As credenciais são gravadas cifradas.</p>
      <div class="form-grid" style="margin-bottom:10px;">
        <label>Conector<select data-integration-key>${connectors.map((c) => `<option value="${esc(c.key)}" ${integration?.connector_key === c.key ? 'selected' : ''}>${esc(c.label)}</option>`).join('')}</select></label>
        <label>Ativa<select data-integration-active><option value="1" ${integration?.active ? 'selected' : ''}>Sim</option><option value="0" ${integration && !integration.active ? 'selected' : ''}>Não</option></select></label>
      </div>
      <label style="display:block;margin-bottom:10px;">Configuração (JSON${integration?.has_config ? ' — já existe; deixe em branco para manter' : ''})
        <textarea data-integration-config rows="5" style="width:100%;font-family:monospace;font-size:12px;" placeholder='{"base_url": "https://api.loja.com.br", "api_key": "..."}'></textarea>
      </label>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-integration-save>Salvar</button>
        <button class="btn ghost" data-integration-test>Testar conexão</button>
        <button class="btn ghost" data-integration-cancel>Fechar</button>
      </div>
      <div data-integration-feedback style="font-size:13px;margin-top:8px;"></div>`);
    const feedback = overlay.querySelector('[data-integration-feedback]');
    overlay.querySelector('[data-integration-cancel]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('[data-integration-save]').addEventListener('click', async () => {
      const rawConfig = overlay.querySelector('[data-integration-config]').value.trim();
      let config;
      if (rawConfig) {
        try { config = JSON.parse(rawConfig); } catch { feedback.textContent = 'Configuração não é um JSON válido.'; return; }
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
        feedback.textContent = 'Integração salva.';
        globalThis.loadAuthorizedSuppliers?.();
      } catch (err) {
        feedback.textContent = err.message || 'Erro ao salvar integração.';
      }
    });
    overlay.querySelector('[data-integration-test]').addEventListener('click', async () => {
      try {
        const res = await api(`/api/authorized-suppliers/${supplierId}/integration/test`, { method: 'POST', body: withActor({}) });
        feedback.textContent = `Conexão OK (${res.connector_key}).`;
      } catch (err) {
        feedback.textContent = err.message || 'Teste falhou.';
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
      toast(err.message || 'Erro ao carregar acompanhamento.', 'error');
      return;
    }
    const canSend = hasPermission('purchase_orders:create');
    const confirmations = tracking.confirmations || [];
    const historyHtml = confirmations.length ? confirmations.map((c) => `<tr>
        <td>${(c.created_at || '').slice(0, 10)}</td>
        <td>${esc(c.status || '')}</td>
        <td>${esc(c.source || '')}</td>
        <td style="font-size:12px;">${[c.delivery_forecast, c.carrier, c.tracking_code, c.comment].filter(Boolean).map(esc).join(' — ') || '—'}</td>
      </tr>`).join('') : '<tr><td colspan="4" style="text-align:center;color:var(--color-text-muted);">Sem registros de acompanhamento.</td></tr>';
    const overlay = openOverlay(`
      <h3 style="margin:0 0 6px;">Fornecedor e entrega — PO #${poId}</h3>
      <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 12px;">
        Envio: ${tracking.sent_channel ? `${esc(CHANNEL_LABELS[tracking.sent_channel] || tracking.sent_channel)} em ${(tracking.sent_to_supplier_at || '').slice(0, 10)}` : 'ainda não enviada'}
        ${tracking.supplier_confirmation_status ? ` · Confirmação: <strong>${esc(tracking.supplier_confirmation_status)}</strong>` : ''}
      </p>
      ${canSend ? `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
        <button class="btn" data-po-send="send">✉ Enviar por e-mail</button>
        <button class="btn ghost" data-po-send="portal-link">🔗 Enviar link do portal</button>
        <button class="btn ghost" data-po-send="send-api">⚡ Enviar via API</button>
        <button class="btn ghost" data-po-send="refresh-status">⟳ Atualizar status (API)</button>
        <button class="btn ghost" data-po-confirm>Registrar confirmação manual</button>
      </div>` : ''}
      <h4 style="margin:8px 0;">Linha do tempo</h4>
      <div style="overflow-x:auto;"><table>
        <thead><tr><th scope="col">Data</th><th scope="col">Status</th><th scope="col">Origem</th><th scope="col">Detalhes</th></tr></thead>
        <tbody>${historyHtml}</tbody>
      </table></div>
      <div style="display:flex;gap:8px;margin-top:12px;"><button class="btn ghost" data-po-close>Fechar</button></div>
      <div data-po-feedback style="font-size:13px;margin-top:8px;"></div>`, { width: '760px' });
    const feedback = overlay.querySelector('[data-po-feedback]');
    overlay.querySelector('[data-po-close]').addEventListener('click', () => overlay.remove());
    overlay.querySelectorAll('[data-po-send]').forEach((btn) => btn.addEventListener('click', async () => {
      try {
        await api(`/api/purchase-orders/${poId}/${btn.getAttribute('data-po-send')}`, { method: 'POST', body: withActor({}) });
        overlay.remove();
        toast('Ação executada.', 'success');
        openPoSupplierActionsModal(poId);
      } catch (err) {
        feedback.textContent = err.message || 'Erro ao executar a ação.';
      }
    }));
    overlay.querySelector('[data-po-confirm]')?.addEventListener('click', () => {
      overlay.remove();
      openPoConfirmationModal(poId);
    });
  }

  function openPoConfirmationModal(poId) {
    const overlay = openOverlay(`
      <h3 style="margin:0 0 12px;">Registrar confirmação — PO #${poId}</h3>
      <div class="form-grid" style="margin-bottom:10px;">
        <label>Retorno do fornecedor<select data-confirm-status>
          <option value="confirmed">Pedido confirmado</option>
          <option value="delivery_update">Atualização de entrega</option>
          <option value="rejected">Pedido recusado</option>
        </select></label>
        <label>Previsão de entrega<input type="date" data-confirm-forecast></label>
        <label>Transportadora<input type="text" data-confirm-carrier></label>
        <label>Código de rastreio<input type="text" data-confirm-tracking></label>
      </div>
      <label style="display:block;margin-bottom:10px;">Comentário<input type="text" data-confirm-comment></label>
      <div style="display:flex;gap:8px;">
        <button class="btn" data-confirm-save>Registrar</button>
        <button class="btn ghost" data-confirm-cancel>Cancelar</button>
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
        toast('Confirmação registrada.', 'success');
        openPoSupplierActionsModal(poId);
      } catch (err) {
        overlay.querySelector('[data-confirm-feedback]').textContent = err.message || 'Erro ao registrar.';
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
