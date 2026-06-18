'use strict';

(function () {
  if (globalThis.__EPI_MODULE_DEVOLUTION_LOADED__) { return; }
  globalThis.__EPI_MODULE_DEVOLUTION_LOADED__ = true;

  // ── Local wrappers ─────────────────────────────────────────────────────────
  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function safeOn(el, evt, fn) { if (typeof globalThis.safeOn === 'function') { globalThis.safeOn(el, evt, fn); } }
  function api(path, opts) { return globalThis.api?.(path, opts); }
  function openModal(el) { if (typeof globalThis.openModal === 'function') { globalThis.openModal(el); } }
  function closeModal(el) { if (typeof globalThis.closeModal === 'function') { globalThis.closeModal(el); } }
  function bindModalKeyboard(el, fn) { if (typeof globalThis.bindModalKeyboard === 'function') { globalThis.bindModalKeyboard(el, fn); } }
  function openSignatureModal(opts) { if (typeof globalThis.openSignatureModal === 'function') { globalThis.openSignatureModal(opts); } }
  function showToast(msg, type) { if (typeof globalThis.showToast === 'function') { globalThis.showToast(msg, type); } }
  function loadBootstrap() { return globalThis.loadBootstrap?.(); }
  function hasPermission(perm) { return globalThis.currentUserHasPermission?.(perm) ?? false; }
  function formatDate(d) { return globalThis.formatDate?.(d) ?? (d ?? ''); }
  function formatDateTime(d) { return globalThis.formatDateTime?.(d) ?? (d ?? ''); }
  function formatItemSizeDisplay(item) { return globalThis.formatItemSizeDisplay?.(item) ?? ''; }
  function tr(key, fallback) { return typeof globalThis.tr === 'function' ? globalThis.tr(key, fallback) : (fallback ?? key); }
  function msg(key, fallback, values = {}) {
    return String(tr(key, fallback)).replace(/\{(\w+)\}/g, (_, name) => values[name] ?? '');
  }

  async function apiWithBootstrapRetry(path, opts) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        return await api(path, opts);
      } catch (err) {
        const status = Number(err?.status || 0);
        if ((status === 502 || status === 503) && attempt < 4) {
          await new Promise((r) => setTimeout(r, 1200 * Math.pow(2, attempt - 1)));
          continue;
        }
        throw err;
      }
    }
  }

  // ── Implementations ────────────────────────────────────────────────────────

  function selectedOpenDeliveryForDevolution() {
    const state = getState();
    const refs = getRefs();
    const selectedId = String(refs.deliveryReturnDeliveryId?.value || '').trim();
    if (!selectedId) { return null; }
    return (state.deliveryReturnCandidates || []).find((item) => String(item.id) === selectedId) || null;
  }

  function renderDeliveryReturnCandidates(candidates = []) {
    const refs = getRefs();
    const field = refs.deliveryReturnDeliveryId;
    const hint = refs.deliveryReturnDeliveryHint;
    if (!field) { return; }
    const list = Array.isArray(candidates) ? candidates : [];
    const needsExplicitPick = list.length > 1;
    const options = list.map((item) => {
      const signatureLabel = item.signature_at ? msg('devolution.signedAt', 'assinado em {date}', { date: formatDateTime(item.signature_at) }) : tr('devolution.signaturePending', 'assinatura pendente');
      const detail = `${formatDate(item.delivery_date)} | ${item.quantity} ${item.quantity_label || 'unidade'} | ${item.unit_name || tr('unit.undefined', 'Unidade não informada')} | ${signatureLabel}`;
      return `<option value="${item.id}">#${item.id} — ${detail}</option>`;
    }).join('');
    field.innerHTML = options || `<option value="">${tr('devolution.noOpenDelivery', 'Sem entrega aberta para este colaborador + EPI')}</option>`;
    if (needsExplicitPick) {
      field.innerHTML = `<option value="">${tr('devolution.selectOriginDelivery', 'Selecione a entrega de origem da devolução')}</option>${field.innerHTML}`;
      field.value = '';
    } else if (list.length === 1) {
      field.value = String(list[0].id);
    }
    if (hint) {
      if (!list.length) { hint.textContent = tr('devolution.noOpenDeliveryHint', 'Nenhuma entrega aberta para este colaborador e este EPI.'); }
      else if (list.length === 1) { hint.textContent = tr('devolution.autoOriginHint', 'Entrega aberta identificada automaticamente.'); }
      else { hint.textContent = tr('devolution.multipleOriginHint', 'Foram encontradas múltiplas entregas abertas. Selecione explicitamente a entrega de origem da devolução.'); }
    }
  }

  async function loadOpenDeliveriesForCurrentPair() {
    const state = getState();
    const actorUserId = String(state.user?.id || '').trim();
    const employeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
    const epiId = String(document.getElementById('delivery-epi')?.value || '').trim();
    const unitId = String(document.getElementById('delivery-unit-filter')?.value || state.user?.operational_unit_id || '').trim();
    const scopeKey = `${employeeId}|${epiId}|${unitId}`;
    if (!actorUserId || !employeeId || !epiId) {
      state.deliveryReturnCandidates = [];
      state.deliveryReturnScopeKey = '';
      state.deliveryReturnPendingScopeKey = '';
      renderDeliveryReturnCandidates([]);
      return;
    }
    if (state.deliveryReturnScopeKey === scopeKey && state.deliveryReturnCandidates.length) { return; }
    if (state.deliveryReturnPendingScopeKey === scopeKey) { return; }
    try {
      state.deliveryReturnPendingScopeKey = scopeKey;
      const payload = await apiWithBootstrapRetry(`/api/devolutions/open-deliveries?${new URLSearchParams({ employee_id: employeeId, epi_id: epiId, unit_id: unitId, actor_user_id: actorUserId }).toString()}`);
      state.deliveryReturnCandidates = payload.items || [];
      state.deliveryReturnScopeKey = scopeKey;
      renderDeliveryReturnCandidates(state.deliveryReturnCandidates);
    } catch (error) {
      console.error('[devolution-open-deliveries] Falha ao consultar entregas abertas:', error);
      state.deliveryReturnCandidates = [];
      state.deliveryReturnScopeKey = scopeKey;
      renderDeliveryReturnCandidates([]);
    } finally {
      if (state.deliveryReturnPendingScopeKey === scopeKey) { state.deliveryReturnPendingScopeKey = ''; }
    }
  }

  function syncDeliveryDevolutionOptions() {
    const state = getState();
    const refs = getRefs();
    const selectedEpiId = String(document.getElementById('delivery-epi')?.value || '').trim();
    const employeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
    const optionWrap = refs.deliveryDevolutionOptions;
    const checkField = refs.deliveryIsDevolution;
    const fieldsWrap = refs.deliveryDevolutionFields;
    const submitButton = document.querySelector('#delivery-form button[type="submit"]');
    if (!optionWrap || !checkField || !fieldsWrap) { return; }
    const hasSelection = Boolean(selectedEpiId && employeeId);
    optionWrap.style.display = hasSelection ? 'block' : 'none';
    if (!hasSelection) {
      state.deliveryReturnCandidates = [];
      state.deliveryReturnScopeKey = '';
      renderDeliveryReturnCandidates([]);
      checkField.checked = false;
      fieldsWrap.style.display = 'none';
      if (submitButton) { submitButton.textContent = tr('delivery.registerDelivery', 'Registrar entrega'); }
      return;
    }
    const canReturnSelectedPair = Boolean((state.deliveryReturnCandidates || []).length);
    checkField.disabled = !canReturnSelectedPair;
    if (!canReturnSelectedPair) {
      checkField.checked = false;
      fieldsWrap.style.display = 'none';
    }
    if (submitButton) {
      submitButton.textContent = checkField.checked ? tr('delivery.registerReturn', 'Registrar devolução') : tr('delivery.registerDelivery', 'Registrar entrega');
    }
  }

  function openDevolutionModal(deliveryId, epiName, employeeName) {
    const state = getState();
    const today = new Date().toISOString().split('T')[0];
    let devolutionSignature = null;
    document.getElementById('devolution-modal')?.remove();
    const modal = document.createElement('div');
    modal.id = 'devolution-modal';
    modal.className = 'signature-modal';
    modal.tabIndex = -1;
    modal.innerHTML = [
      '<div class="signature-modal__dialog" role="dialog" aria-modal="true" style="max-width:540px">',
      '<header class="signature-modal__header">',
      `<h3 style="margin:0">${tr('devolution.title', 'Registrar Devolução de EPI')}</h3>`,
      '</header>',
      '<div class="signature-modal__body" style="display:flex;flex-direction:column;gap:12px">',
      '<div class="card" style="background:#f8f9fa;padding:12px;border-radius:6px;margin:0">',
      `<strong>${tr('epi.title', 'EPI')}:</strong> ${epiName}<br>`,
      `<strong>${tr('employee.singleTitle', 'Colaborador')}:</strong> ${employeeName}`,
      '</div>',
      '<label style="display:flex;flex-direction:column;gap:4px">',
      `<span>${tr('devolution.returnDate', 'Data da devolução')} <span style="color:red">*</span></span>`,
      '<input id="dev-date" type="date" value="'+today+'" required style="padding:8px;border:1px solid #ccc;border-radius:4px">',
      '</label>',
      '<label style="display:flex;flex-direction:column;gap:4px">',
      `<span>${tr('devolution.returnedEpiCondition', 'Condição do EPI devolvido')} <span style="color:red">*</span></span>`,
      '<select id="dev-condition" style="padding:8px;border:1px solid #ccc;border-radius:4px">',
      `<option value="usable">✅ ${tr('devolution.conditionReusableLong', 'Reutilizável — pode voltar ao estoque')}</option>`,
      `<option value="damaged">⚠️ ${tr('devolution.conditionDamagedLong', 'Danificado — encaminhar para avaliação')}</option>`,
      `<option value="discarded">🗑️ ${tr('devolution.conditionDiscardedLong', 'Descartado — sem condições de uso')}</option>`,
      `<option value="maintenance">🔧 ${tr('devolution.conditionMaintenance', 'Em manutenção')}</option>`,
      `<option value="hygiene">🧼 ${tr('devolution.conditionHygiene', 'Para higienização')}</option>`,
      `<option value="quarantine">🔒 ${tr('devolution.conditionQuarantine', 'Em quarentena')}</option>`,
      '</select>',
      '</label>',
      '<label style="display:flex;flex-direction:column;gap:4px">',
      `<span>${tr('devolution.itemDestination', 'Destino do item')} <span style="color:red">*</span></span>`,
      '<select id="dev-dest" style="padding:8px;border:1px solid #ccc;border-radius:4px">',
      `<option value="stock">📦 ${tr('devolution.destinationStock', 'Retornar ao estoque (atualiza saldo)')}</option>`,
      `<option value="discard">🗑️ ${tr('devolution.destinationDiscard', 'Descartar')}</option>`,
      `<option value="maintenance">🔧 ${tr('devolution.destinationMaintenance', 'Encaminhar para manutenção')}</option>`,
      `<option value="hygiene">🧼 ${tr('devolution.destinationHygiene', 'Encaminhar para higienização')}</option>`,
      `<option value="quarantine">🔒 ${tr('devolution.destinationQuarantine', 'Colocar em quarentena')}</option>`,
      '</select>',
      '</label>',
      '<label style="display:flex;flex-direction:column;gap:4px">',
      `<span>${tr('devolution.reason', 'Motivo / Justificativa')}</span>`,
      `<input id="dev-reason" type="text" placeholder="${tr('devolution.reasonPlaceholder', 'Ex.: rescisão de contrato, EPI vencido, troca por uso...')}" style="padding:8px;border:1px solid #ccc;border-radius:4px">`,
      '</label>',
      '<label style="display:flex;flex-direction:column;gap:4px">',
      `<span>${tr('devolution.additionalNotes', 'Observações adicionais')}</span>`,
      `<textarea id="dev-notes" rows="2" placeholder="${tr('devolution.additionalNotesPlaceholder', 'Informações adicionais sobre a devolução...')}" style="padding:8px;border:1px solid #ccc;border-radius:4px;resize:vertical"></textarea>`,
      '</label>',
      `<label>${tr('devolution.returnDigitalSignature', 'Assinatura digital da devolução')} <span style="color:red">*</span> ${tr('devolution.required', '(obrigatória)')}`,
      `<button id="dev-signature-open" class="ghost" type="button">${tr('delivery.clickToSign', 'Clique para assinar')}</button>`,
      '</label>',
      `<small id="dev-signature-status" class="hint" style="color:#dc3545">${tr('devolution.signatureRequired', 'Assinatura obrigatória para registrar a devolução.')}</small>`,
      '<div style="background:#e8f4fd;border:1px solid #b8daff;border-radius:4px;padding:10px;font-size:13px">',
      `<strong>${tr('devolution.whatHappensTitle', 'ℹ️ O que acontece ao confirmar:')}</strong><br>`,
      `${tr('devolution.whatHappensLinked', '• A devolução será vinculada à entrega original')}<br>`,
      `${tr('devolution.whatHappensStock', '• A movimentação de estoque será registrada automaticamente')}<br>`,
      `${tr('devolution.whatHappensFicha', '• A Ficha de EPI do colaborador será atualizada')}<br>`,
      tr('devolution.whatHappensAudit', '• O histórico completo ficará disponível para auditoria'),
      '</div>',
      '</div>',
      '<footer class="signature-modal__footer">',
      `<button class="ghost" id="dev-cancel">${tr('cancel', 'Cancelar')}</button>`,
      `<button class="primary" id="dev-confirm" style="background:#dc3545">${tr('devolution.confirm', '↩ Confirmar devolução')}</button>`,
      '</footer>',
      '</div>'
    ].join('');
    document.body.appendChild(modal);
    openModal(modal);
    const closeDevolutionModal = () => { state.currentDevolutionContext = null; closeModal(modal); };
    bindModalKeyboard(modal, closeDevolutionModal);
    const devCancelBtn = document.getElementById('dev-cancel');
    if (devCancelBtn) { devCancelBtn.onclick = closeDevolutionModal; }
    modal.onclick = (e) => { if (e.target === modal) { closeDevolutionModal(); } };
    const devSignatureBtn = document.getElementById('dev-signature-open');
    const devSignatureStatus = document.getElementById('dev-signature-status');
    const buildDevolutionFormData = () => ({
      returned_date: String(document.getElementById('dev-date')?.value || ''),
      condition: String(document.getElementById('dev-condition')?.value || ''),
      destination: String(document.getElementById('dev-dest')?.value || ''),
      reason: String(document.getElementById('dev-reason')?.value || '').trim(),
      notes: String(document.getElementById('dev-notes')?.value || '').trim(),
    });
    const restoreDevolutionFocus = () => {
      if (!modal?.classList.contains('is-open')) { return; }
      const target = devSignatureBtn || document.getElementById('dev-confirm') || modal.querySelector('input,select,textarea,button');
      target?.focus?.();
    };
    safeOn(devSignatureBtn, 'click', () => {
      state.currentDevolutionContext = { itemId: Number(deliveryId) || 0, formData: buildDevolutionFormData() };
      openSignatureModal({
        signerName: employeeName || state.user?.full_name || tr('delivery.digitalSignature', 'Assinatura digital'),
        comment: devolutionSignature?.signature_comment || '',
        parentModal: modal,
        context: state.currentDevolutionContext,
        onConfirm: (payloadSignature) => {
          devolutionSignature = payloadSignature;
          if (devSignatureStatus) {
            devSignatureStatus.textContent = msg('devolution.signedCaptured', '✓ Assinatura capturada em {date}.', { date: formatDateTime(payloadSignature.signature_at) });
            devSignatureStatus.style.color = '#28a745';
          }
          if (devSignatureBtn) { devSignatureBtn.textContent = tr('devolution.changeSignature', 'Alterar assinatura'); }
        },
        onAfterConfirm: () => {
          restoreDevolutionFocus();
          state.currentDevolutionContext = null;
        }
      });
    });
    const devConfirmBtn = document.getElementById('dev-confirm');
    if (!devConfirmBtn) { return; }
    devConfirmBtn.onclick = async () => {
      const btn = devConfirmBtn;
      const returnedDate = document.getElementById('dev-date').value;
      if (!returnedDate) { alert(tr('devolution.dateRequiredAlert', 'Informe a data da devolução.')); return; }
      if (!devolutionSignature?.signature_data) {
        alert(tr('devolution.signatureRequiredAlert', 'Assinatura digital obrigatória. Clique em "Clique para assinar" antes de confirmar a devolução.'));
        document.getElementById('dev-signature-open')?.focus();
        return;
      }
      const condition = document.getElementById('dev-condition').value;
      const destination = document.getElementById('dev-dest').value;
      const reason = document.getElementById('dev-reason').value.trim();
      const notes = document.getElementById('dev-notes').value.trim();
      const originalText = btn.textContent;
      try {
        btn.disabled = true;
        btn.textContent = tr('devolution.registering', 'Registrando...');
        await api('/api/devolutions', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: state.user.id,
            delivery_id: deliveryId,
            returned_date: returnedDate,
            condition,
            destination,
            reason,
            notes,
            signature_name: devolutionSignature?.signature_name || '',
            signature_data: devolutionSignature?.signature_data || '',
            signature_at: devolutionSignature?.signature_at || '',
            signature_comment: devolutionSignature?.signature_comment || '',
          })
        });
        closeDevolutionModal();
        showToast(tr('devolution.success', 'Devolução registrada com sucesso! Movimentação e ficha atualizadas.'), 'success');
        state.deliveryEpisScopeKey = '';
        state.deliveryReturnScopeKey = '';
        state.deliveryReturnPendingScopeKey = '';
        await loadBootstrap();
      } catch (err) {
        alert('Erro: ' + (err instanceof Error ? err.message : String(err)));
        btn.disabled = false;
        btn.textContent = originalText;
      }
    };
  }

  function buildDeliveryRowWithDevolution(item) {
    const devolvido = String(item.returned_date || '').trim();
    let col8 = '';
    if (devolvido) {
      const condLabel = {
        usable: tr('devolution.conditionReusable', 'Reutilizável'), damaged: tr('devolution.conditionDamaged', 'Danificado'), discarded: tr('devolution.conditionDiscarded', 'Descartado'),
        maintenance: tr('devolution.conditionMaintenance', 'Em manutenção'), quarantine: tr('devolution.conditionQuarantine', 'Em quarentena'), hygiene: tr('devolution.conditionHygiene', 'Para higienização')
      }[item.returned_condition || ''] || item.returned_condition || '';
      col8 = '<span class="badge badge-status-inactive" title="'+msg('devolution.conditionTitle', 'Condição: {condition}', { condition: condLabel })+'">'
            +tr('devolution.returnedShort', '↩ Dev.')+' '+formatDate(item.returned_date)+'</span>';
    } else {
      col8 = formatDate(item.next_replacement_date) || '<span style="color:#aaa">—</span>';
    }
    let col9 = '';
    if (!devolvido && hasPermission('deliveries:create') && item.devolution_available !== 0) {
      col9 = '<button class="ghost" style="font-size:12px;padding:4px 10px;" '
            +'data-dev-delivery="'+item.id+'" '
            +'data-dev-epi="'+(item.epi_name||'').replace(/"/g,'&quot;')+'" '
            +'data-dev-emp="'+(item.employee_name||'').replace(/"/g,'&quot;')+'" '
            +'title="'+tr('devolution.registerReturnTitle', 'Registrar devolução deste EPI')+'">'+tr('devolution.returnButton', '↩ Devolver')+'</button>';
    } else if (devolvido) {
      col9 = '<span style="color:#6c757d;font-size:12px;">'+tr('devolution.returned', 'Devolvido')+'</span>';
    }
    return '<tr>'
      +'<td>'+(item.company_name||'')+'</td>'
      +'<td>'+(item.employee_id_code||'')+'</td>'
      +'<td>'+(item.employee_name||'')+'</td>'
      +'<td>'+(item.epi_name||'')+'</td>'
      +'<td>'+formatItemSizeDisplay(item)+'</td>'
      +'<td>'+(item.quantity||'')+'</td>'
      +'<td>'+(item.quantity_label||'')+'</td>'
      +'<td>'+formatDate(item.delivery_date)+'</td>'
      +'<td>'+col8+'</td>'
      +'<td><div class="action-group">'+col9+'</div></td>'
      +'</tr>';
  }

  // ── Exports ────────────────────────────────────────────────────────────────
  const moduleExports = {
    selectedOpenDeliveryForDevolution,
    renderDeliveryReturnCandidates,
    loadOpenDeliveriesForCurrentPair,
    syncDeliveryDevolutionOptions,
    openDevolutionModal,
    buildDeliveryRowWithDevolution
  };

  for (const [name, fn] of Object.entries(moduleExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_DEVOLUTION__ = Object.freeze({ ...moduleExports });
})();
