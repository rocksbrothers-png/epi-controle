'use strict';

// Purchases view module (refatoração JS — Fase 6).
// Extrai funções do módulo de compras de app.js.
// Segue o padrão aditivo paralelo: exporta para globalThis com sobrescrita.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASES_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASES_LOADED__ = true;

  // ── Utilitários locais ─────────────────────────────────────────────────────

  function safeOn(target, eventName, handler, options) {
    if (!target || typeof target.addEventListener !== 'function' || typeof handler !== 'function') {return false;}
    target.addEventListener(eventName, handler, options);
    return true;
  }

  function bindAppListener(target, eventName, handler, options) {
    return globalThis.bindAppListener
      ? globalThis.bindAppListener(target, eventName, handler, options)
      : safeOn(target, eventName, handler, options);
  }

  function esc(value) {
    return (globalThis.escapeHtml ?? ((v) => String(v ?? '')))(value);
  }

  function hasPermission(perm) {
    return (globalThis.currentUserHasPermission?.(perm) ?? false);
  }

  function getState() {
    return globalThis.__EPI_APP_STATE__ || {};
  }

  function api(path, options) {
    if (typeof globalThis.api === 'function') {return globalThis.api(path, options);}
    const opts = options || {};
    if (!opts.headers) {opts.headers = {};}
    return fetch(path, opts).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {throw new Error(data?.error || data?.message || `HTTP ${res.status}`);}
      return data;
    });
  }

  function showToast(msg, type) {
    globalThis.showToast?.(msg, type);
  }

  function fmtBrl(v) {
    return typeof globalThis.fmtBrl === 'function'
      ? globalThis.fmtBrl(v)
      : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v) || 0);
  }

  function tr(key, fallback) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  }

  function filterByUserCompany(items) {
    return typeof globalThis.filterByUserCompany === 'function'
      ? globalThis.filterByUserCompany(items)
      : items;
  }

  // ── canSeePosTab ────────────────────────────────────────────────────────────

  function canSeePosTab() {
    return hasPermission('purchase_orders:view');
  }

  // ── switchComprasTab ────────────────────────────────────────────────────────

  function switchComprasTab(tab) {
    if (tab === 'pos' && !canSeePosTab()) {tab = 'requisicoes';}
    ['aprovacoes','demanda-revisao','demandas','requisicoes','pos','fornecedores','feedbacks'].forEach(t => {
      const panel = document.getElementById(`compras-${t}-panel`);
      const btn = document.getElementById(`compras-tab-${t}`);
      if (!panel || !btn) {return;}
      const active = t === tab;
      panel.style.display = active ? '' : 'none';
      btn.className = active ? 'btn' : 'btn ghost';
    });
    if (tab === 'aprovacoes') {globalThis.loadAprovacoesSolicitacoes?.();}
    else if (tab === 'demanda-revisao') { globalThis.populatePurchaseUnitSelects?.(); globalThis.loadPurchaseRequests?.(); }
    else if (tab === 'demandas') {globalThis.loadPurchaseDemands?.();}
    else if (tab === 'requisicoes') {globalThis.loadPurchaseRequests?.();}
    else if (tab === 'pos') {globalThis.loadPurchaseOrders?.();}
    else if (tab === 'fornecedores') { globalThis.loadAuthorizedSuppliers?.(); globalThis.loadFornecedoresPurchaseFunctions?.(); }
    else if (tab === 'feedbacks') {globalThis.loadEpiFeedbacks?.();}
  }

  // ── openPurchaseWorkflowModal ───────────────────────────────────────────────

  function openPurchaseWorkflowModal(config) {
    const PURCHASE_REVIEW_REASONS = globalThis.PURCHASE_REVIEW_REASONS || {
      buyer: ['Valor acima do esperado', 'Fornecedor incorreto', 'Item com preço divergente', 'Cotação incompleta', 'Necessário novo fornecedor', 'Quantidade divergente', 'Outro'],
      requester: ['Acrescentar novos itens', 'Corrigir item existente', 'Revisar quantidade', 'Reavaliar item inicialmente reprovado', 'Justificar necessidade', 'Anexar informação complementar', 'Outro'],
      reject: ['Valor acima do esperado', 'Fornecedor incorreto', 'Item com preço divergente', 'Cotação incompleta', 'Quantidade divergente', 'Outro'],
    };
    const PURCHASE_APPROVAL_REJECTION_REASONS = globalThis.PURCHASE_APPROVAL_REJECTION_REASONS || ['Item não necessário', 'Valor acima do esperado', 'Quantidade incorreta', 'Fornecedor inadequado', 'EPI incompatível', 'Fora do escopo da solicitação', 'Outro'];

    function workflowReasonOptions(group) {
      return (PURCHASE_REVIEW_REASONS[group] || []).map(reason => `<option value="${esc(reason)}">${esc(reason)}</option>`).join('');
    }

    return new Promise((resolve) => {
      const existing = document.getElementById('purchase-workflow-modal');
      if (existing) {existing.remove();}
      const overlay = document.createElement('div');
      overlay.id = 'purchase-workflow-modal';
      overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
      const needsReason = !!config.requiresReason;
      const needsComment = !!config.requiresComment;
      const needsChanges = !!config.showRequesterChecklist;
      const selectableItems = Array.isArray(config.items) ? config.items : [];
      const itemSelectionHtml = config.showItemSelection ? `<div style="margin-bottom:10px;max-height:180px;overflow:auto;border:1px solid var(--color-border);padding:8px;border-radius:6px;"><strong>Itens para recotar</strong>${selectableItems.map(item => `<label style="display:block;margin-top:6px;"><input type="checkbox" value="${esc(item.id)}" data-purchase-workflow-item> ${esc(item.epi_name || item.epi_display_name || 'Item')} — Qtd ${esc(item.quantity_requested || item.quantity || 1)}</label>`).join('')}</div>` : '';
      const approvalReasonOptions = PURCHASE_APPROVAL_REJECTION_REASONS.map(reason => `<option value="${esc(reason)}">${esc(reason)}</option>`).join('');
      const approvalItemsHtml = config.showApprovalItems ? `<div style="margin-bottom:10px;max-height:50vh;overflow:auto;border:1px solid var(--color-border);padding:8px;border-radius:6px;">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:8px;">
        <div><strong>Aprovação item a item</strong><p style="font-size:12px;color:var(--color-text-muted);margin:4px 0;">Itens marcados serão aprovados; itens desmarcados exigem motivo e justificativa individual.</p></div>
        <div style="display:flex;gap:6px;"><button type="button" class="ghost" data-purchase-approval-select-all>Selecionar todos</button><button type="button" class="ghost" data-purchase-approval-clear>Limpar seleção</button></div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr><th>Aprovar</th><th>Item</th><th>Qtd</th><th>Fornecedor</th><th>Colaborador</th><th>Unidade</th><th>Vlr Unit.</th><th>Total</th><th>Justificativa dos reprovados</th></tr></thead><tbody>
        ${selectableItems.map(item => {
          const total = Number(item.total_price || 0);
          const unitPrice = Number(item.unit_price || 0);
          return `<tr data-purchase-approval-row="${esc(item.id)}">
            <td><input type="checkbox" value="${esc(item.id)}" data-purchase-approval-item checked></td>
            <td><strong>${esc(item.epi_name || item.epi_display_name || 'Item')}</strong><br><small>${tr('epi.caShort', 'CA')}: ${esc(item.ca || item.epi_ca || '—')}</small></td>
            <td>${esc(item.quantity_requested || item.quantity || 1)}</td>
            <td>${esc(item.supplier || '—')}</td>
            <td>${esc(item.employee_name || '—')}</td>
            <td>${esc(item.unit_name || '—')}</td>
            <td>${unitPrice ? esc(fmtBrl(unitPrice)) : '—'}</td>
            <td>${total ? esc(fmtBrl(total)) : '—'}</td>
            <td><select data-purchase-rejection-reason="${esc(item.id)}" disabled><option value="">Motivo...</option>${approvalReasonOptions}</select><textarea data-purchase-rejection-comment="${esc(item.id)}" rows="2" placeholder="Observação" disabled style="width:100%;margin-top:4px;"></textarea></td>
          </tr>`;
        }).join('')}
      </tbody></table>
    </div>` : '';
      overlay.innerHTML = `
      <div class="card" style="max-width:${config.showApprovalItems ? '1120px' : '520px'};width:min(${config.showApprovalItems ? '1120px' : '520px'},96vw);margin:auto;padding:24px;">
        <h3 style="margin:0 0 8px;">${esc(config.title || 'Confirmar ação')}</h3>
        <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 12px;">${esc(config.description || '')}</p>
        ${needsReason ? `<label style="display:block;margin-bottom:10px;">Motivo <span style="color:var(--color-danger)">*</span><select id="purchase-workflow-reason" style="width:100%;margin-top:4px;"><option value="">Selecione...</option>${workflowReasonOptions(config.reasonGroup)}</select></label>` : ''}
        ${itemSelectionHtml}${approvalItemsHtml}
        ${needsChanges ? `<div style="margin-bottom:10px;"><strong>O que precisa ser revisado?</strong><div style="display:grid;grid-template-columns:1fr;gap:4px;margin-top:6px;font-size:13px;">${PURCHASE_REVIEW_REASONS.requester.map(reason => `<label><input type="checkbox" value="${esc(reason)}" data-purchase-review-change> ${esc(reason)}</label>`).join('')}</div></div>` : ''}
        <label style="display:block;">Observação ${needsComment ? '<span style="color:var(--color-danger)">*</span>' : ''}<textarea id="purchase-workflow-comment" rows="3" style="width:100%;margin-top:4px;" placeholder="Descreva a decisão ou correção necessária..."></textarea></label>
        <div id="purchase-workflow-error" style="display:none;color:var(--color-danger);font-size:13px;margin-top:8px;"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
          <button class="btn ghost" id="purchase-workflow-cancel">Cancelar</button>
          <button class="btn" id="purchase-workflow-confirm">Confirmar</button>
        </div>
      </div>`;
      document.body.appendChild(overlay);
      const finish = (value) => { overlay.remove(); resolve(value); };
      const errorEl = overlay.querySelector('#purchase-workflow-error');
      const syncApprovalRows = () => {
        overlay.querySelectorAll('[data-purchase-approval-row]').forEach(row => {
          const checkbox = row.querySelector('[data-purchase-approval-item]');
          const approved = !!checkbox?.checked;
          row.style.background = approved ? '' : 'var(--color-danger-bg)';
          row.querySelectorAll('[data-purchase-rejection-reason], [data-purchase-rejection-comment]').forEach(field => { field.disabled = approved; });
        });
      };
      overlay.querySelectorAll('[data-purchase-approval-item]').forEach(input => bindAppListener(input, 'change', syncApprovalRows));
      overlay.querySelectorAll('[data-purchase-rejection-reason]').forEach(select => bindAppListener(select, 'change', () => {
        const row = select.closest('[data-purchase-approval-row]');
        const comment = row?.querySelector('[data-purchase-rejection-comment]');
        if (comment) {comment.placeholder = select.value === 'Outro' ? 'Obrigatório para Outro' : 'Observação';}
      }));
      bindAppListener(overlay.querySelector('[data-purchase-approval-select-all]'), 'click', () => { overlay.querySelectorAll('[data-purchase-approval-item]').forEach(input => { input.checked = true; }); syncApprovalRows(); });
      bindAppListener(overlay.querySelector('[data-purchase-approval-clear]'), 'click', () => { overlay.querySelectorAll('[data-purchase-approval-item]').forEach(input => { input.checked = false; }); syncApprovalRows(); });
      syncApprovalRows();
      bindAppListener(overlay.querySelector('#purchase-workflow-cancel'), 'click', () => finish(null));
      bindAppListener(overlay, 'click', (event) => { if (event.target === overlay) {finish(null);} });
      bindAppListener(overlay.querySelector('#purchase-workflow-confirm'), 'click', () => {
        const reason = overlay.querySelector('#purchase-workflow-reason')?.value || '';
        const comment = overlay.querySelector('#purchase-workflow-comment')?.value?.trim() || '';
        const requestedChanges = Array.from(overlay.querySelectorAll('[data-purchase-review-change]:checked')).map(input => input.value);
        const itemIds = Array.from(overlay.querySelectorAll('[data-purchase-workflow-item]:checked')).map(input => Number(input.value));
        const decisions = Array.from(overlay.querySelectorAll('[data-purchase-approval-row]')).map(row => {
          const input = row.querySelector('[data-purchase-approval-item]');
          const itemId = Number(input?.value || 0);
          const approved = !!input?.checked;
          return {
            item_id: itemId,
            approved,
            rejection_reason: approved ? '' : (row.querySelector('[data-purchase-rejection-reason]')?.value || ''),
            rejection_comment: approved ? '' : (row.querySelector('[data-purchase-rejection-comment]')?.value?.trim() || '')
          };
        });
        const approvedItemIds = decisions.filter(item => item.approved).map(item => item.item_id);
        const rejectedItemIds = decisions.filter(item => !item.approved).map(item => item.item_id);
        const invalidRejected = decisions.find(item => !item.approved && !item.rejection_reason);
        const missingOther = decisions.find(item => !item.approved && item.rejection_reason === 'Outro' && !item.rejection_comment);
        if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }
        if (needsReason && !reason) { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = 'Selecione o motivo.'; } return; }
        if (config.showItemSelection && !itemIds.length) { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = 'Selecione ao menos um item.'; } return; }
        if (invalidRejected) { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = `Selecione o motivo do item #${invalidRejected.item_id}.`; } return; }
        if (missingOther) { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = `Informe observação para o motivo Outro no item #${missingOther.item_id}.`; } return; }
        if (needsComment && !comment) { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = 'Informe a observação obrigatória.'; } return; }
        finish({ reason, comment, requested_changes: requestedChanges, item_ids: itemIds, approved_item_ids: approvedItemIds, rejected_item_ids: rejectedItemIds, decisions });
      });
    });
  }

  // ── openRequesterReviewModal ────────────────────────────────────────────────

  function openRequesterReviewModal(pr, items) {
    const state = getState();
    const ITEM_STATUS_LABELS = globalThis.ITEM_STATUS_LABELS || {};

    return new Promise((resolve) => {
      const existing = document.getElementById('requester-review-modal');
      if (existing) {existing.remove();}
      const overlay = document.createElement('div');
      overlay.id = 'requester-review-modal';
      overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
      const lockedStatuses = ['approved','ordered','received','closed'];
      const editableItems = items.filter(i => !lockedStatuses.includes(String(i.status || '')));
      const lockedItems = items.filter(i => lockedStatuses.includes(String(i.status || '')));
      const availableEpis = filterByUserCompany(state.epis || []).filter(e => !pr.company_id || String(e.company_id) === String(pr.company_id));
      const epiOptions = availableEpis.map(e => `<option value="${esc(e.id)}">${esc(e.name)}${e.ca ? ` — ${tr('epi.caShort', 'CA')}:${esc(e.ca)}` : ''}</option>`).join('');
      overlay.innerHTML = `
      <div class="card" style="max-width:680px;width:min(680px,96vw);margin:auto;padding:24px;max-height:90vh;overflow-y:auto;">
        <h3 style="margin:0 0 8px;">Editar Itens da Requisição</h3>
        <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 14px;">Corrija quantidades, remova ou acrescente itens antes de reenviar.</p>
        <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:14px;">
          <thead><tr style="border-bottom:2px solid var(--color-border);">
            <th style="text-align:left;padding:6px 4px;">EPI</th>
            <th style="text-align:center;padding:6px 4px;width:80px;">Qtd</th>
            <th style="text-align:center;padding:6px 4px;width:70px;">Remover</th>
          </tr></thead>
          <tbody>
            ${editableItems.map(item => `<tr data-rr-row="${esc(item.id)}" style="border-bottom:1px solid var(--color-border);">
              <td style="padding:6px 4px;">${esc(item.epi_name || item.epi_display_name || '—')}</td>
              <td style="padding:6px 4px;text-align:center;"><input type="number" min="1" value="${esc(item.quantity_requested || 1)}" data-rr-qty="${esc(item.id)}" style="width:64px;text-align:center;padding:4px;"></td>
              <td style="padding:6px 4px;text-align:center;"><input type="checkbox" data-rr-remove="${esc(item.id)}"></td>
            </tr>`).join('')}
            ${lockedItems.map(item => `<tr style="opacity:0.5;border-bottom:1px solid var(--color-border);">
              <td style="padding:6px 4px;">${esc(item.epi_name || item.epi_display_name || '—')} <small style="color:var(--color-text-muted);">(${esc(ITEM_STATUS_LABELS[item.status] || item.status)})</small></td>
              <td style="padding:6px 4px;text-align:center;">${esc(item.quantity_requested || 1)}</td>
              <td style="padding:6px 4px;text-align:center;">—</td>
            </tr>`).join('')}
          </tbody>
        </table>
        <div style="margin-bottom:14px;border:1px dashed var(--color-border);border-radius:6px;padding:12px;">
          <strong style="font-size:13px;">Acrescentar EPI</strong>
          <div style="display:flex;gap:8px;margin-top:8px;align-items:flex-end;flex-wrap:wrap;">
            <label style="flex:1;min-width:200px;">EPI<select id="rr-add-epi" style="width:100%;margin-top:4px;"><option value="">Selecione...</option>${epiOptions}</select></label>
            <label style="width:72px;">Qtd<input type="number" id="rr-add-qty" min="1" value="1" style="width:100%;margin-top:4px;padding:4px;"></label>
            <button type="button" class="btn ghost" id="rr-add-btn" style="margin-bottom:1px;">+ Adicionar</button>
          </div>
          <table id="rr-new-table" style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;display:none;">
            <thead><tr><th style="text-align:left;">EPI</th><th style="text-align:center;">Qtd</th><th></th></tr></thead>
            <tbody id="rr-new-tbody"></tbody>
          </table>
        </div>
        <label style="display:block;margin-bottom:14px;">Observações / Justificativa
          <textarea id="rr-notes" rows="3" style="width:100%;margin-top:4px;" placeholder="Descreva as correções realizadas...">${esc(pr.notes || '')}</textarea>
        </label>
        <div id="rr-error" style="display:none;color:var(--color-danger);font-size:13px;margin-bottom:8px;"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn ghost" id="rr-cancel">Cancelar</button>
          <button class="btn" id="rr-confirm">Salvar Correções</button>
        </div>
      </div>`;
      document.body.appendChild(overlay);
      const newItems = [];
      const newTbody = overlay.querySelector('#rr-new-tbody');
      const newTable = overlay.querySelector('#rr-new-table');
      const errorEl = overlay.querySelector('#rr-error');
      const finish = (value) => { overlay.remove(); resolve(value); };
      bindAppListener(overlay.querySelector('#rr-add-btn'), 'click', () => {
        const epiSelect = overlay.querySelector('#rr-add-epi');
        const qtyInput = overlay.querySelector('#rr-add-qty');
        const epiId = Number(epiSelect?.value || 0);
        if (!epiId) {return;}
        const epi = availableEpis.find(e => Number(e.id) === epiId);
        if (!epi) {return;}
        const qty = Math.max(1, Number(qtyInput?.value || 1));
        newItems.push({ epi_id: epiId, quantity_requested: qty, origin: 'manual' });
        const trEl = document.createElement('tr');
        trEl.style.borderBottom = '1px solid var(--color-border)';
        trEl.innerHTML = `<td style="padding:4px;">${esc(epi.name)}</td><td style="text-align:center;padding:4px;">${esc(qty)}</td><td style="text-align:center;"><button type="button" style="background:none;border:none;cursor:pointer;color:var(--color-danger);" data-rr-new-idx="${newItems.length - 1}">✕</button></td>`;
        newTbody.appendChild(trEl);
        if (newTable) {newTable.style.display = '';}
        if (epiSelect) {epiSelect.value = '';}
        if (qtyInput) {qtyInput.value = '1';}
      });
      bindAppListener(newTbody, 'click', (e) => {
        const btn = e.target.closest('[data-rr-new-idx]');
        if (!btn) {return;}
        const idx = Number(btn.dataset.rrNewIdx);
        newItems.splice(idx, 1);
        btn.closest('tr').remove();
        newTbody.querySelectorAll('[data-rr-new-idx]').forEach((b, i) => { b.dataset.rrNewIdx = i; });
        if (!newTbody.children.length && newTable) {newTable.style.display = 'none';}
      });
      bindAppListener(overlay.querySelector('#rr-cancel'), 'click', () => finish(null));
      bindAppListener(overlay, 'click', (e) => { if (e.target === overlay) {finish(null);} });
      bindAppListener(overlay.querySelector('#rr-confirm'), 'click', async () => {
        const updates = editableItems
          .filter(item => !overlay.querySelector(`[data-rr-remove="${item.id}"]`)?.checked)
          .map(item => ({ id: item.id, quantity_requested: Number(overlay.querySelector(`[data-rr-qty="${item.id}"]`)?.value || item.quantity_requested || 1), notes: item.notes || '' }));
        const removeItemIds = editableItems.filter(item => overlay.querySelector(`[data-rr-remove="${item.id}"]`)?.checked).map(item => item.id);
        const notes = overlay.querySelector('#rr-notes')?.value?.trim() || '';
        if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }
        try {
          const state2 = getState();
          await api(`/api/purchase-requests/${pr.id}/review-items`, { method: 'POST', body: JSON.stringify({ actor_user_id: state2.user?.id, updates, add_items: newItems, remove_item_ids: removeItemIds, notes }) });
          finish(true);
          showToast('Correções da requisição salvas.');
          globalThis.openPrDetail?.(pr.id);
        } catch (error) {
          if (errorEl) { errorEl.style.display = ''; errorEl.textContent = error.message || 'Erro ao salvar correções.'; }
        }
      });
    });
  }

  // ── _getBuyerApproverEmployees ──────────────────────────────────────────────

  function _getBuyerApproverEmployees() {
    const state = getState();
    const buyerApproverRoles = new Set(['buyer', 'approver']);
    const linkedEmployeeIds = new Set(
      (state.users || [])
        .filter(u => buyerApproverRoles.has(u.role) && u.active && u.linked_employee_id)
        .map(u => String(u.linked_employee_id))
    );
    return filterByUserCompany(state.employees || []).filter(e => linkedEmployeeIds.has(String(e.id)));
  }

  // ── initAprovacoes ──────────────────────────────────────────────────────────

  function initAprovacoes() {
    const selectAll = document.getElementById('aprovacoes-select-all');
    if (selectAll) {
      safeOn(selectAll, 'change', () => {
        globalThis._selectedAprovacoes?.clear();
        document.querySelectorAll('.aprovacao-check').forEach((cb, i) => {
          cb.checked = selectAll.checked;
          if (selectAll.checked) {globalThis._selectedAprovacoes?.add(i);}
        });
        globalThis._syncAprovacoesBtnVisibility?.();
      });
    }
    safeOn(document.getElementById('aprovacoes-refresh'), 'click', () => globalThis.loadAprovacoesSolicitacoes?.());
    safeOn(document.getElementById('aprovacoes-aprovar-btn'), 'click', async () => {
      if (!globalThis._selectedAprovacoes?.size) {return;}
      if (!confirm(`Aprovar ${globalThis._selectedAprovacoes.size} solicitação(ões)?`)) {return;}
      globalThis._executarAprovacaoEmLote?.(globalThis._buildBulkUpdates?.('aprovado'));
    });
    safeOn(document.getElementById('aprovacoes-reprovar-btn'), 'click', () => {
      if (!globalThis._selectedAprovacoes?.size) {return;}
      const modal = document.getElementById('aprovacoes-reprovar-modal');
      if (modal) {modal.style.display = 'flex';}
    });
    safeOn(document.getElementById('aprovacoes-prorrogar-btn'), 'click', () => {
      if (!globalThis._selectedAprovacoes?.size) {return;}
      const modal = document.getElementById('aprovacoes-prorrogar-modal');
      if (modal) {modal.style.display = 'flex';}
    });

    const motivoSel = document.getElementById('aprovacoes-reprovar-motivo');
    const outroWrap = document.getElementById('aprovacoes-reprovar-outro-wrap');
    if (motivoSel) {
      safeOn(motivoSel, 'change', () => {
        if (outroWrap) {outroWrap.style.display = motivoSel.value === 'Outro' ? '' : 'none';}
      });
    }
    safeOn(document.getElementById('aprovacoes-reprovar-cancel'), 'click', () => {
      document.getElementById('aprovacoes-reprovar-modal').style.display = 'none';
    });
    safeOn(document.getElementById('aprovacoes-reprovar-confirm'), 'click', async () => {
      const motivo = document.getElementById('aprovacoes-reprovar-motivo')?.value;
      const outro = document.getElementById('aprovacoes-reprovar-outro')?.value?.trim();
      const reason = motivo === 'Outro' ? (outro || 'Outro') : motivo;
      if (!reason) { alert('Selecione o motivo da reprovação.'); return; }
      document.getElementById('aprovacoes-reprovar-modal').style.display = 'none';
      globalThis._executarAprovacaoEmLote?.(globalThis._buildBulkUpdates?.('rejeitado', { rejection_reason: reason }));
    });

    safeOn(document.getElementById('aprovacoes-prorrogar-cancel'), 'click', () => {
      document.getElementById('aprovacoes-prorrogar-modal').style.display = 'none';
    });
    safeOn(document.getElementById('aprovacoes-prorrogar-confirm'), 'click', async () => {
      const date = document.getElementById('aprovacoes-prorrogar-data')?.value;
      if (!date) { alert('Informe a data de prorrogação.'); return; }
      document.getElementById('aprovacoes-prorrogar-modal').style.display = 'none';
      globalThis._executarAprovacaoEmLote?.(globalThis._buildBulkUpdates?.('prorrogado', { postponed_until: date }));
    });

    safeOn(document.getElementById('aprovacoes-export-btn'), 'click', () => globalThis.exportAprovacoesCsv?.());
  }

  // ── initPoCsvImport ─────────────────────────────────────────────────────────

  function initPoCsvImport(pr) {
    globalThis._poCsvParsed = [];
    const preview = document.getElementById('req-po-csv-preview');
    const feedback = document.getElementById('req-po-csv-feedback');
    const fileInput = document.getElementById('req-po-csv-file');
    if (preview) {preview.style.display = 'none';}
    if (feedback) { feedback.textContent = ''; feedback.style.color = ''; }
    if (fileInput) {fileInput.value = '';}

    const previewBtn = document.getElementById('req-po-csv-preview-btn');
    const cancelBtn = document.getElementById('req-po-csv-cancel-btn');
    const submitBtn = document.getElementById('req-po-csv-submit-btn');

    if (previewBtn) {previewBtn.onclick = async () => {
      const file = document.getElementById('req-po-csv-file')?.files?.[0];
      if (!file) { if (feedback) {feedback.textContent = 'Selecione um arquivo CSV ou XLSX.';} return; }
      try {
        if (feedback) { feedback.textContent = 'Lendo arquivo...'; feedback.style.color = ''; }
        const result = await globalThis._parsePoImportFile?.(file) || [];
        if (!result.length) { if (feedback) {feedback.textContent = 'Nenhuma linha válida encontrada no arquivo.';} return; }
        globalThis._poCsvParsed = result;
        globalThis._renderPoCsvPreview?.(result);
        if (preview) {preview.style.display = '';}
        if (feedback) { feedback.textContent = ''; feedback.style.color = ''; }
      } catch (error) {
        if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = error.message || 'Erro ao ler arquivo de cotação.'; }
      }
    };}

    if (cancelBtn) {cancelBtn.onclick = () => {
      if (preview) {preview.style.display = 'none';}
      if (feedback) { feedback.textContent = ''; feedback.style.color = ''; }
      globalThis._poCsvParsed = [];
    };}

    const savePricesBtn = document.getElementById('req-po-save-prices-btn');
    if (savePricesBtn) {savePricesBtn.onclick = async () => {
      const poCsvParsed = globalThis._poCsvParsed || [];
      if (!poCsvParsed.length) { if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = 'Visualize o CSV antes de salvar.'; } return; }
      const currentPrDetail = globalThis._currentPrDetail;
      const prItems = (currentPrDetail?.items || []).filter(item => !['approved','partially_approved'].includes(String(pr.status || '')) || String(item.status || '') === 'approved');
      const matchedRows = globalThis._matchPurchaseImportRows?.(poCsvParsed, prItems) || [];
      const priceUpdates = poCsvParsed.map((row, idx) => {
        const matched = matchedRows[idx];
        if (!matched) {return null;}
        return { item_id: matched.id, unit_price: globalThis._parsePurchaseMoney?.(row.valor_unitario) ?? 0, quantity: globalThis._parsePurchaseQuantity?.(row.qtd, matched.quantity_requested || 1) ?? 1 };
      }).filter(Boolean);
      if (!priceUpdates.length) { if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = 'Nenhum item do CSV foi associado a um item da requisição. Verifique os CAs ou nomes.'; } return; }
      const state2 = getState();
      try {
        if (feedback) { feedback.textContent = 'Salvando preços...'; feedback.style.color = ''; }
        await api(`/api/purchase-requests/${pr.id}/save-prices`, { method: 'POST', body: JSON.stringify({ actor_user_id: state2.user?.id, items: priceUpdates }) });
        if (feedback) { feedback.style.color = 'var(--color-success)'; feedback.textContent = `Preços salvos (${priceUpdates.length} item(s)). Status atualizado.`; }
        globalThis._poCsvParsed = [];
        await globalThis.openPrDetail?.(pr.id);
        globalThis.loadPurchaseRequests?.();
      } catch(err) {
        if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = err.message || 'Erro ao salvar preços.'; }
      }
    };}

    if (submitBtn) {submitBtn.onclick = async () => {
      const poCsvParsed = globalThis._poCsvParsed || [];
      if (!poCsvParsed.length) { if (feedback) {feedback.textContent = 'Nenhum dado para importar.';} return; }
      const poNumber = document.getElementById('req-po-csv-number')?.value?.trim();
      const supplier = document.getElementById('req-po-csv-supplier')?.value?.trim();
      if (!supplier) { if (feedback) {feedback.textContent = 'Informe o fornecedor principal.';} return; }
      const currentPrDetail = globalThis._currentPrDetail;
      const prItems = (currentPrDetail?.items || []).filter(item => !['approved','partially_approved'].includes(String(pr.status || '')) || String(item.status || '') === 'approved');
      const matchedRows = globalThis._matchPurchaseImportRows?.(poCsvParsed, prItems) || [];
      const poItems = poCsvParsed.map((row, idx) => {
        const matched = matchedRows[idx];
        return {
          purchase_request_item_id: matched?.id || null,
          epi_id: matched?.epi_id || null,
          epi_name: row.epi || matched?.epi_name || matched?.epi_display_name || '',
          ca: row.ca || matched?.ca || matched?.epi_ca || '',
          manufacturer: row.fabricante || matched?.manufacturer || '',
          supplier: row.fornecedor || supplier,
          glove_size: row.tamanho_luva || matched?.glove_size || 'N/A',
          size: row.tamanho || matched?.size || 'N/A',
          uniform_size: row.tamanho_uniforme || matched?.uniform_size || 'N/A',
          quantity: globalThis._parsePurchaseQuantity?.(row.qtd, matched?.quantity_requested || 1) ?? 1,
          unit_price: globalThis._parsePurchaseMoney?.(row.valor_unitario) ?? 0,
          origin: matched?.origin || 'employee_request',
          employee_id: matched?.employee_id || null,
          employee_name: matched?.employee_name || '',
          employee_sector: matched?.employee_sector || '',
          employee_role: matched?.employee_role || '',
          epi_request_id: matched?.epi_request_id || null,
        };
      });
      const validItems = poItems.filter(i => i.epi_id);
      const skipped = poItems.length - validItems.length;
      if (!validItems.length) { if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = 'Nenhum item do CSV foi associado a um EPI cadastrado. Verifique os nomes ou CAs.'; } return; }
      if (skipped > 0 && !confirm(`${skipped} item(s) não foram associados a EPIs cadastrados e serão ignorados. Continuar com ${validItems.length} item(s)?`)) {return;}
      const state2 = getState();
      try {
        if (feedback) { feedback.textContent = 'Criando PO...'; feedback.style.color = ''; }
        await api('/api/purchase-orders', { method: 'POST', body: JSON.stringify({
          actor_user_id: state2.user?.id,
          unit_id: pr.unit_id,
          po_number: poNumber || '',
          supplier,
          notes: `Importado via CSV da Requisição #${pr.id}`,
          purchase_request_id: pr.id,
          items: validItems,
        }) });
        if (feedback) { feedback.style.color = 'var(--color-success)'; feedback.textContent = 'PO criada com sucesso!'; }
        if (preview) {preview.style.display = 'none';}
        globalThis._poCsvParsed = [];
        await globalThis.openPrDetail?.(pr.id);
        globalThis.loadPurchaseOrders?.();
      } catch(err) {
        if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = err.message || 'Erro ao criar PO.'; }
      }
    };}
  }

  // ── _parsePoCsv ─────────────────────────────────────────────────────────────

  function _parsePoCsv(text) {
    const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(l => l.trim());
    if (!lines.length) {return [];}
    const sep = lines[0].includes(';') ? ';' : ',';
    const rawHeaders = lines[0].split(sep).map(h => h.replace(/^["'\s]+|["'\s]+$/g, '').toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '_'));
    const COL_MAP = { item_id: ['item_id','id_item','purchase_request_item_id','id_item_requisicao'], requisicao: ['requisicao','requisicao_demanda','demanda','request_id','purchase_request_id'], unidade: ['unidade','unit','unit_name','nome_unidade'], epi: ['epi','nome_epi','descricao','item'], ca: ['ca','certificado','ca_numero'], fabricante: ['fabricante','manufacturer','marca'], fornecedor: ['fornecedor','supplier','empresa_fornecedora'], colaborador: ['colaborador','employee','employee_name','funcionario','nome_colaborador'], setor: ['setor','employee_sector','sector'], origem: ['origem','origin'], tamanho: ['tamanho','tam','size'], tamanho_luva: ['tamanho_luva','luva','glove_size'], tamanho_uniforme: ['tamanho_uniforme','uniforme','uniform_size'], qtd: ['qtd','quantidade','qty','quantity'], valor_unitario: ['valor_unitario','vlr_unit_r','vl_unit','preco_unitario','unit_price','valor','preco','price'], total: ['total','total_r','valor_total','total_price'] };
    const colIdx = {};
    Object.entries(COL_MAP).forEach(([key, aliases]) => {
      const found = aliases.find(a => rawHeaders.includes(a));
      if (found) {colIdx[key] = rawHeaders.indexOf(found);}
    });
    const getCol = (row, key) => colIdx[key] !== undefined ? (row[colIdx[key]] || '').replace(/^["'\s]+|["'\s]+$/g, '').trim() : '';
    return lines.slice(1).map(line => {
      const cols = line.split(sep);
      const row = { item_id: getCol(cols, 'item_id'), requisicao: getCol(cols, 'requisicao'), unidade: getCol(cols, 'unidade'), epi: getCol(cols, 'epi'), ca: getCol(cols, 'ca'), fabricante: getCol(cols, 'fabricante'), fornecedor: getCol(cols, 'fornecedor'), colaborador: getCol(cols, 'colaborador'), setor: getCol(cols, 'setor'), origem: getCol(cols, 'origem'), tamanho: getCol(cols, 'tamanho'), tamanho_luva: getCol(cols, 'tamanho_luva'), tamanho_uniforme: getCol(cols, 'tamanho_uniforme'), qtd: getCol(cols, 'qtd'), valor_unitario: getCol(cols, 'valor_unitario'), total: getCol(cols, 'total') };
      return (row.epi || row.ca) ? row : null;
    }).filter(Boolean);
  }

  // ── _renderPoCsvPreview ─────────────────────────────────────────────────────

  function _renderPoCsvPreview(rows) {
    const tbody = document.getElementById('req-po-csv-preview-tbody');
    const totalEl = document.getElementById('req-po-csv-total');
    if (!tbody) {return;}
    let grandTotal = 0;
    tbody.innerHTML = rows.map(r => {
      const qty = globalThis._parsePurchaseQuantity?.(r.qtd) ?? 1;
      const price = globalThis._parsePurchaseMoney?.(r.valor_unitario) ?? 0;
      const total = qty * price;
      grandTotal += total;
      return `<tr>
      <td>${esc(r.epi || '—')}</td><td>${esc(r.ca || '—')}</td><td>${esc(r.fabricante || '—')}</td>
      <td>${esc(r.fornecedor || '—')}</td><td>${esc([r.tamanho_luva ? `L:${r.tamanho_luva}`:null, r.tamanho ? `T:${r.tamanho}`:null, r.tamanho_uniforme ? `U:${r.tamanho_uniforme}`:null].filter(Boolean).join(' ') || '—')}</td>
      <td>${qty}</td><td>${fmtBrl(price)}</td><td>${fmtBrl(total)}</td>
    </tr>`;
    }).join('');
    if (totalEl) {totalEl.textContent = `Total geral: ${fmtBrl(grandTotal)}`;}
  }

  // ── initPurchaseModule ──────────────────────────────────────────────────────

  function initPurchaseModule() {
    if (hasPermission('purchase_requests:create')) {initAprovacoes();}
    // Esconde aba POs para perfis sem acesso (admin local vê apenas Demandas e Requisições)
    const posTabBtn = document.getElementById('compras-tab-pos');
    if (posTabBtn) {posTabBtn.style.display = canSeePosTab() ? '' : 'none';}
    // Aba Fornecedores: admins (suppliers:manage) + aprovadores (purchase_orders:approve)
    const fornTabBtn = document.getElementById('compras-tab-fornecedores');
    if (fornTabBtn) {fornTabBtn.style.display = (hasPermission('suppliers:manage') || hasPermission('purchase_orders:approve')) ? '' : 'none';}
    // Aba Demandas: buyer não cria requisições a partir de demandas — só Req + POs
    const manualTab = document.getElementById('compras-tab-demanda-revisao');
    if (manualTab) {manualTab.style.display = hasPermission('purchase_requests:create') ? '' : 'none';}
    const demTab = document.getElementById('compras-tab-demandas');
    if (demTab) {demTab.style.display = hasPermission('purchase_requests:create') ? '' : 'none';}
    // Aba Aprovações: apenas quem pode criar purchase_requests (admin local+)
    const aprovTab = document.getElementById('compras-tab-aprovacoes');
    if (aprovTab) {aprovTab.style.display = hasPermission('purchase_requests:create') ? '' : 'none';}

    // Aba Avaliações e Sugestões removida de Compras — fica apenas na aba principal de Avaliações
    const feedbacksTab = document.getElementById('compras-tab-feedbacks');
    if (feedbacksTab) {feedbacksTab.style.display = 'none';}

    // Tab switching
    bindAppListener(document.getElementById('compras-tab-aprovacoes'), 'click', () => switchComprasTab('aprovacoes'));
    bindAppListener(document.getElementById('compras-tab-demanda-revisao'), 'click', () => switchComprasTab('demanda-revisao'));
    bindAppListener(document.getElementById('compras-tab-demandas'), 'click', () => switchComprasTab('demandas'));
    bindAppListener(document.getElementById('compras-tab-requisicoes'), 'click', () => switchComprasTab('requisicoes'));
    bindAppListener(document.getElementById('compras-tab-pos'), 'click', () => switchComprasTab('pos'));
    bindAppListener(document.getElementById('compras-tab-fornecedores'), 'click', () => switchComprasTab('fornecedores'));

    bindAppListener(document.getElementById('compras-manual-request-btn'), 'click', () => {
      globalThis._manualRequestItems = [];
      globalThis.populatePurchaseUnitSelects?.();
      globalThis._renderManualRequestItems?.();
      globalThis._syncManualRequestItemsJson?.();
      const form = document.getElementById('compras-new-request-form');
      if (form) { form.style.display = ''; form.scrollIntoView({ behavior: 'smooth' }); }
    });
    bindAppListener(document.getElementById('compras-review-returned-btn'), 'click', () => {
      const filter = document.getElementById('compras-req-status-filter');
      if (filter) {filter.value = 'waiting_requester_correction';}
      switchComprasTab('requisicoes');
    });

    // Demandas
    bindAppListener(document.getElementById('compras-demands-company-filter'), 'change', () => globalThis.loadPurchaseDemands?.());
    bindAppListener(document.getElementById('compras-demands-refresh'), 'click', () => globalThis.loadPurchaseDemands?.());
    bindAppListener(document.getElementById('compras-demands-select-all'), 'change', (e) => {
      globalThis._selectedDemands?.clear();
      document.querySelectorAll('.demand-check').forEach((cb, i) => {
        cb.checked = e.target.checked;
        if (e.target.checked) {globalThis._selectedDemands?.add(i);}
      });
      globalThis.updateCreateRequestBtn?.();
    });
    bindAppListener(document.getElementById('compras-demands-tbody'), 'change', (e) => {
      if (!e.target.classList.contains('demand-check')) {return;}
      const idx = parseInt(e.target.dataset.demandIndex);
      if (e.target.checked) {globalThis._selectedDemands?.add(idx);}
      else {globalThis._selectedDemands?.delete(idx);}
      globalThis.updateCreateRequestBtn?.();
    });
    bindAppListener(document.getElementById('compras-create-request-btn'), 'click', () => {
      globalThis.populatePurchaseUnitSelects?.();
      const selectedItems = Array.from(globalThis._selectedDemands || []).map(i => (globalThis._purchaseDemands || [])[i]).filter(Boolean);
      globalThis._manualRequestItems = selectedItems.map(d => ({
        epi_id: d.epi_id, quantity_requested: d.quantity_requested || d.quantity || 1,
        origin: d.demand_type === 'employee_request' ? 'employee_request' : 'stock_minimum',
        employee_id: d.employee_id || null, employee_name: d.employee_name || '',
        employee_sector: d.employee_sector || '', employee_role: d.employee_role || '',
        epi_request_id: d.id && d.demand_type === 'employee_request' ? d.id : null,
        glove_size: d.glove_size || 'N/A', size: d.size || 'N/A', uniform_size: d.uniform_size || 'N/A',
      }));
      globalThis._renderManualRequestItems?.();
      globalThis._syncManualRequestItemsJson?.();
      const form = document.getElementById('compras-new-request-form');
      if (form) { form.style.display = ''; form.scrollIntoView({ behavior: 'smooth' }); }
    });
    bindAppListener(document.getElementById('compras-cancel-request'), 'click', () => {
      const form = document.getElementById('compras-new-request-form');
      if (form) {form.style.display = 'none';}
      globalThis._manualRequestItems = [];
      globalThis._renderManualRequestItems?.();
    });
    bindAppListener(document.getElementById('purchase-request-add-item-btn'), 'click', () => {
      const epiSel = document.getElementById('purchase-request-epi-select');
      const qtyInput = document.getElementById('purchase-request-item-qty');
      const gloveSizeSel = document.getElementById('purchase-request-glove-size');
      const sizeSel = document.getElementById('purchase-request-size');
      const uniformSizeSel = document.getElementById('purchase-request-uniform-size');
      const epiId = epiSel?.value;
      const qty = parseInt(qtyInput?.value || '1', 10);
      if (!epiId) { alert('Selecione um EPI para adicionar.'); return; }
      if (!qty || qty < 1) { alert('Informe uma quantidade válida.'); return; }
      if (!globalThis._manualRequestItems) {globalThis._manualRequestItems = [];}
      globalThis._manualRequestItems.push({
        epi_id: Number(epiId),
        quantity_requested: qty,
        origin: 'manual',
        glove_size: gloveSizeSel?.value || 'N/A',
        size: sizeSel?.value || 'N/A',
        uniform_size: uniformSizeSel?.value || 'N/A',
      });
      globalThis._renderManualRequestItems?.();
      globalThis._syncManualRequestItemsJson?.();
      if (epiSel) {epiSel.value = '';}
      if (qtyInput) {qtyInput.value = '1';}
      if (gloveSizeSel) {gloveSizeSel.value = 'N/A';}
      if (sizeSel) {sizeSel.value = 'N/A';}
      if (uniformSizeSel) {uniformSizeSel.value = 'N/A';}
    });
    bindAppListener(document.getElementById('purchase-request-items-preview'), 'click', (event) => {
      const btn = event.target.closest('[data-remove-manual-item]');
      if (!btn) {return;}
      if (!globalThis._manualRequestItems) {globalThis._manualRequestItems = [];}
      globalThis._manualRequestItems.splice(parseInt(btn.dataset.removeManualItem, 10), 1);
      globalThis._renderManualRequestItems?.();
      globalThis._syncManualRequestItemsJson?.();
    });
    bindAppListener(document.getElementById('purchase-request-form'), 'submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn?.disabled) {return;}
      const itemsJson = document.getElementById('purchase-request-items-json')?.value || '[]';
      let items;
      try { items = JSON.parse(itemsJson); } catch { items = []; }
      if (!items.length) {
        alert('Adicione ao menos um EPI à requisição usando o seletor acima.');
        return;
      }
      const state2 = getState();
      try {
        if (submitBtn) {submitBtn.disabled = true;}
        await api('/api/purchase-requests', { method: 'POST', body: JSON.stringify({
          actor_user_id: state2.user?.id,
          unit_id: form.elements.unit_id.value,
          title: form.elements.title.value,
          notes: form.elements.notes.value,
          items,
        }) });
        form.reset();
        globalThis._manualRequestItems = [];
        globalThis._renderManualRequestItems?.();
        document.getElementById('compras-new-request-form').style.display = 'none';
        globalThis._selectedDemands?.clear();
        globalThis.updateCreateRequestBtn?.();
        globalThis.loadPurchaseDemands?.();
        alert('Requisição criada com sucesso!');
      } catch(err) {
        alert(err.message || 'Erro ao criar requisição.');
      } finally {
        if (submitBtn) {submitBtn.disabled = false;}
      }
    });

    // Requisições
    bindAppListener(document.getElementById('compras-req-refresh'), 'click', () => globalThis.loadPurchaseRequests?.());
    bindAppListener(document.getElementById('compras-req-status-filter'), 'change', () => globalThis.loadPurchaseRequests?.());
    bindAppListener(document.getElementById('compras-req-tbody'), 'click', (e) => {
      const btn = e.target.closest('[data-pr-detail]');
      if (btn) {globalThis.openPrDetail?.(btn.dataset.prDetail);}
    });
    bindAppListener(document.getElementById('compras-req-detail-close'), 'click', () => {
      const el = document.getElementById('compras-req-detail');
      if (el) {el.style.display = 'none';}
    });

    // POs
    bindAppListener(document.getElementById('compras-po-refresh'), 'click', () => globalThis.loadPurchaseOrders?.());
    bindAppListener(document.getElementById('compras-po-status-filter'), 'change', () => globalThis.loadPurchaseOrders?.());
    bindAppListener(document.getElementById('compras-po-tbody'), 'click', (e) => {
      const btn = e.target.closest('[data-po-detail]');
      if (btn) {globalThis.openPoDetail?.(btn.dataset.poDetail);}
    });
    bindAppListener(document.getElementById('compras-po-detail-close'), 'click', () => {
      const el = document.getElementById('compras-po-detail');
      if (el) {el.style.display = 'none';}
    });
    // Aprovação
    bindAppListener(document.getElementById('po-approve-items-btn'), 'click', () => globalThis.submitPoApprovalWithItems?.());
    ['po-reject-btn','po-postpone-btn'].forEach(id => {
      bindAppListener(document.getElementById(id), 'click', (e) => {
        const decision = e.currentTarget.dataset.decision;
        const commentRequired = document.getElementById('po-approval-comment-required');
        const postponeRow = document.getElementById('po-postpone-date-row');
        if (commentRequired) {commentRequired.style.display = ['rejected','postponed'].includes(decision) ? '' : 'none';}
        if (postponeRow) {postponeRow.style.display = decision === 'postponed' ? '' : 'none';}
        globalThis.submitPoApproval?.(decision);
      });
    });
    // Reenvio de PO pelo comprador (após sugestões)
    bindAppListener(document.getElementById('po-resubmit-btn'), 'click', () => globalThis.submitPoResubmit?.());

    // Revisão operacional do admin
    ['po-review-approve-btn','po-review-return-btn'].forEach(id => {
      bindAppListener(document.getElementById(id), 'click', (e) => {
        const reviewDecision = e.currentTarget.dataset.review;
        const reqSpan = document.getElementById('po-review-comment-required');
        if (reqSpan) {reqSpan.style.display = reviewDecision === 'returned_with_suggestions' ? '' : 'none';}
        globalThis.submitPoAdminReview?.(reviewDecision);
      });
    });
    // Recebimento
    ['po-received-btn','po-checked-btn','po-closed-btn'].forEach(id => {
      bindAppListener(document.getElementById(id), 'click', (e) => globalThis.submitPoReceive?.(e.currentTarget.dataset.action));
    });
    // Nova PO
    const newPoBtn = document.getElementById('compras-new-po-btn');
    if (newPoBtn) {bindAppListener(newPoBtn, 'click', () => {
      globalThis.populatePurchaseUnitSelects?.();
      if ((globalThis._authorizedSuppliers || []).length) {
        globalThis.populatePoSupplierSelect?.();
      } else {
        globalThis.loadAuthorizedSuppliers?.();
      }
      const hint = document.getElementById('po-items-unit-hint');
      if (hint) {hint.style.display = document.getElementById('po-unit')?.value ? 'none' : '';}
      const form = document.getElementById('compras-new-po-form');
      if (form) { form.style.display = ''; form.scrollIntoView({ behavior: 'smooth' }); }
    });}
    bindAppListener(document.getElementById('compras-cancel-po'), 'click', () => {
      const form = document.getElementById('compras-new-po-form');
      if (form) {form.style.display = 'none';}
    });
    bindAppListener(document.getElementById('po-add-item-btn'), 'click', () => {
      const list = document.getElementById('po-items-list');
      if (!list) {return;}
      const idx = list.children.length;
      list.insertAdjacentHTML('beforeend', globalThis.buildPoItemRow?.(idx, null) || '');
      const row = list.querySelector(`[data-po-item="${idx}"]`);
      if (!row) {return;}
      bindAppListener(row.querySelector(`[data-po-remove-item="${idx}"]`), 'click', () => {
        list.querySelector(`[data-po-item="${idx}"]`)?.remove();
        globalThis.updatePoTotal?.();
      });
      bindAppListener(row.querySelector(`[data-poi-qty="${idx}"]`), 'input', () => globalThis.updatePoTotal?.());
      bindAppListener(row.querySelector(`[data-poi-price="${idx}"]`), 'input', () => globalThis.updatePoTotal?.());
      bindAppListener(row.querySelector(`[data-poi-epi="${idx}"]`), 'change', () => globalThis.onPoItemEpiChange?.(idx));
    });
    // Atualizar EPIs ao mudar de unidade no form de PO
    bindAppListener(document.getElementById('po-unit'), 'change', () => globalThis.refreshPoItemEpiSelects?.());
    // Preencher CNPJ ao selecionar fornecedor
    bindAppListener(document.getElementById('po-supplier-select'), 'change', (e) => {
      const opt = e.target.options[e.target.selectedIndex];
      const cnpj = opt?.dataset?.cnpj || '';
      const cnpjInput = document.getElementById('po-supplier-cnpj');
      const statusEl = document.getElementById('po-supplier-status');
      if (cnpjInput) {cnpjInput.value = cnpj ? (globalThis.formatCNPJ?.(cnpj) || cnpj) : '';}
      if (statusEl) {statusEl.textContent = e.target.value ? '✓ Fornecedor autorizado' : '';}
    });

    // Fornecedores autorizados tab
    bindAppListener(document.getElementById('compras-suppliers-refresh'), 'click', () => globalThis.loadAuthorizedSuppliers?.());
    // Vínculos de unidade — somente leitura na aba Fornecedores
    bindAppListener(document.getElementById('compras-links-refresh'), 'click', () => globalThis.loadFornecedoresPurchaseFunctions?.());
    // Popula selects de unidade para criação de PO/Requisição
    if (hasPermission('unit_links:manage')) {
      globalThis.populatePurchaseUnitSelects?.();
    }
    const SUPPLIERS_MANAGE_PERM = globalThis.SUPPLIERS_MANAGE_PERM || 'suppliers:manage';
    const _suppliersAddBtn = document.getElementById('compras-suppliers-add-btn');
    const _suppliersUploadBtn = document.getElementById('compras-suppliers-upload-btn');
    if (_suppliersAddBtn) {_suppliersAddBtn.style.display = hasPermission(SUPPLIERS_MANAGE_PERM) ? '' : 'none';}
    if (_suppliersUploadBtn) {_suppliersUploadBtn.style.display = hasPermission(SUPPLIERS_MANAGE_PERM) ? '' : 'none';}
    bindAppListener(document.getElementById('compras-suppliers-add-btn'), 'click', () => {
      const form = document.getElementById('compras-suppliers-add-form');
      const upload = document.getElementById('compras-suppliers-upload-form');
      if (upload) {upload.style.display = 'none';}
      if (form) {form.style.display = form.style.display === 'none' ? '' : 'none';}
    });
    bindAppListener(document.getElementById('compras-suppliers-add-cancel'), 'click', () => {
      const form = document.getElementById('compras-suppliers-add-form');
      if (form) {form.style.display = 'none';}
    });
    bindAppListener(document.getElementById('compras-suppliers-add-submit'), 'click', async () => {
      const feedback = document.getElementById('compras-suppliers-add-feedback');
      const name = document.getElementById('compras-supplier-name')?.value?.trim();
      if (!name) { if (feedback) {feedback.textContent = 'Nome é obrigatório.';} return; }
      const state2 = getState();
      try {
        if (feedback) {feedback.textContent = '';}
        await api('/api/authorized-suppliers', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: state2.user?.id,
            name,
            cnpj: document.getElementById('compras-supplier-cnpj')?.value?.trim() || '',
            contact_email: document.getElementById('compras-supplier-email')?.value?.trim() || '',
            notes: document.getElementById('compras-supplier-notes')?.value?.trim() || '',
          })
        });
        if (feedback) {feedback.textContent = 'Fornecedor salvo com sucesso.';}
        ['compras-supplier-name','compras-supplier-cnpj','compras-supplier-email','compras-supplier-notes'].forEach(id => {
          const el = document.getElementById(id); if (el) {el.value = '';}
        });
        globalThis.loadAuthorizedSuppliers?.();
      } catch(e) {
        if (feedback) {feedback.textContent = e.message || 'Erro ao salvar fornecedor.';}
      }
    });
    bindAppListener(document.getElementById('compras-suppliers-upload-btn'), 'click', () => {
      const form = document.getElementById('compras-suppliers-upload-form');
      const add = document.getElementById('compras-suppliers-add-form');
      if (add) {add.style.display = 'none';}
      if (form) {form.style.display = form.style.display === 'none' ? '' : 'none';}
    });
    bindAppListener(document.getElementById('compras-suppliers-csv-cancel'), 'click', () => {
      const form = document.getElementById('compras-suppliers-upload-form');
      if (form) {form.style.display = 'none';}
    });
    bindAppListener(document.getElementById('compras-suppliers-csv-submit'), 'click', () => globalThis.importSuppliersCSV?.());

    // Modal de edição de fornecedor
    bindAppListener(document.getElementById('edit-supplier-save'), 'click', () => globalThis.saveEditSupplier?.());
    bindAppListener(document.getElementById('edit-supplier-cancel'), 'click', () => {
      const modal = document.getElementById('modal-edit-supplier');
      if (modal) {modal.style.display = 'none';}
    });

    // Modal de POs do fornecedor
    bindAppListener(document.getElementById('modal-supplier-pos-close'), 'click', () => {
      const modal = document.getElementById('modal-supplier-pos');
      if (modal) {modal.style.display = 'none';}
    });

    bindAppListener(document.getElementById('purchase-order-form'), 'submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      if (!form.elements.unit_id.value) { alert('Selecione a unidade.'); return; }
      if (!form.elements.supplier.value) { alert('Selecione o fornecedor.'); return; }
      const items = globalThis.collectPoItems?.() || [];
      if (!items.length) { alert('Adicione ao menos um item.'); return; }
      if (items.some(i => !i.epi_id)) { alert('Selecione o EPI em todos os itens.'); return; }
      const state2 = getState();
      try {
        await api('/api/purchase-orders', { method: 'POST', body: JSON.stringify({
          actor_user_id: state2.user?.id,
          unit_id: form.elements.unit_id.value,
          supplier: form.elements.supplier.value,
          supplier_cnpj: form.elements.supplier_cnpj.value,
          expected_delivery_date: form.elements.expected_delivery_date.value,
          notes: form.elements.notes.value,
          purchase_request_id: form.elements.purchase_request_id.value || null,
          items,
        }) });
        form.reset();
        const supplierCnpjEl = document.getElementById('po-supplier-cnpj');
        if (supplierCnpjEl) {supplierCnpjEl.value = '';}
        const supplierStatusEl = document.getElementById('po-supplier-status');
        if (supplierStatusEl) {supplierStatusEl.textContent = '';}
        const newPoForm = document.getElementById('compras-new-po-form');
        if (newPoForm) {newPoForm.style.display = 'none';}
        const poItemsList = document.getElementById('po-items-list');
        if (poItemsList) {poItemsList.innerHTML = '';}
        const hint = document.getElementById('po-items-unit-hint');
        if (hint) {hint.style.display = '';}
        globalThis.loadPurchaseOrders?.();
        alert('PO criada com sucesso!');
      } catch(err) {
        alert(err.message || 'Erro ao criar PO.');
      }
    });
  }

  // ── Exports ────────────────────────────────────────────────────────────────

  globalThis.canSeePosTab = canSeePosTab;
  globalThis.switchComprasTab = switchComprasTab;
  globalThis.openPurchaseWorkflowModal = openPurchaseWorkflowModal;
  globalThis.openRequesterReviewModal = openRequesterReviewModal;
  globalThis._getBuyerApproverEmployees = _getBuyerApproverEmployees;
  globalThis.initAprovacoes = initAprovacoes;
  globalThis.initPoCsvImport = initPoCsvImport;
  globalThis._parsePoCsv = _parsePoCsv;
  globalThis._renderPoCsvPreview = _renderPoCsvPreview;
  globalThis.initPurchaseModule = initPurchaseModule;

  globalThis.__EPI_PURCHASES__ = Object.freeze({
    canSeePosTab,
    switchComprasTab,
    openPurchaseWorkflowModal,
    openRequesterReviewModal,
    _getBuyerApproverEmployees,
    initAprovacoes,
    initPoCsvImport,
    _parsePoCsv,
    _renderPoCsvPreview,
    initPurchaseModule,
  });
})();
