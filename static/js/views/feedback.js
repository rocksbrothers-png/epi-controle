'use strict';

// Módulo de feedback de EPI (refatoração JS — Fase 6).
//
// Extrai de app.js as funções: openFeedbackTriageModal,
// openFeedbackHseqModal, forwardFeedbackToAdmin,
// openFeedbackAdminDecisionModal, closeFeedback.
// Segue o padrão aditivo-paralelo: coexiste com app.js durante a transição.
(function () {
  if (globalThis.__EPI_MODULE_FEEDBACK_LOADED__) { return; }
  globalThis.__EPI_MODULE_FEEDBACK_LOADED__ = true;

  // ── Local helpers ─────────────────────────────────────────────────────────

  function safeOn(el, ev, fn, opts) {
    if (el && typeof el.addEventListener === 'function') {
      el.addEventListener(ev, fn, opts);
    }
  }

  function bindAppListener(el, ev, fn, opts) {
    if (typeof globalThis.bindAppListener === 'function') {
      globalThis.bindAppListener(el, ev, fn, opts);
    } else {
      safeOn(el, ev, fn, opts);
    }
  }

  function esc(value) {
    if (typeof globalThis.escapeHtml === 'function') { return globalThis.escapeHtml(value); }
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }

  async function api(path, opts) {
    if (typeof globalThis.api === 'function') { return globalThis.api(path, opts); }
    const res = await fetch(path, opts);
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const j = await res.json(); msg = j.error || j.message || msg; } catch (_) { /* ignore */ }
      throw new Error(msg);
    }
    return res.json();
  }

  function showToast(msg, type) {
    if (typeof globalThis.showToast === 'function') { globalThis.showToast(msg, type); }
  }

  // ── openFeedbackTriageModal ───────────────────────────────────────────────

  function openFeedbackTriageModal(fb) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
    modal.innerHTML = `
    <div class="card" style="max-width:520px;width:min(520px,96vw);margin:auto;padding:24px;">
      <h3 style="margin:0 0 12px;">Triagem do Feedback #${esc(String(fb.id))}</h3>
      <p style="font-size:12px;color:var(--color-text-muted);margin:0 0 12px;">Classifique o feedback e defina prioridade. Se necessário, solicite avaliação HSEQ.</p>
      <label style="display:block;margin-bottom:8px;">Tipo <select id="ftriage-type" style="width:100%;margin-top:4px;">
        <option value="avaliacao"${fb.type === 'avaliacao' ? ' selected' : ''}>Avaliação</option>
        <option value="sugestao"${fb.type === 'sugestao' ? ' selected' : ''}>Sugestão</option>
        <option value="reclamacao"${fb.type === 'reclamacao' ? ' selected' : ''}>Reclamação</option>
        <option value="elogio"${fb.type === 'elogio' ? ' selected' : ''}>Elogio</option>
      </select></label>
      <label style="display:block;margin-bottom:8px;">Categoria <input id="ftriage-category" type="text" style="width:100%;margin-top:4px;" placeholder="Ex: Qualidade, Conforto..." value="${esc(fb.category || '')}"></label>
      <label style="display:block;margin-bottom:8px;">Prioridade <select id="ftriage-priority" style="width:100%;margin-top:4px;">
        <option value="baixa"${fb.priority === 'baixa' ? ' selected' : ''}>Baixa</option>
        <option value="normal"${(!fb.priority || fb.priority === 'normal') ? ' selected' : ''}>Normal</option>
        <option value="alta"${fb.priority === 'alta' ? ' selected' : ''}>Alta</option>
        <option value="urgente"${fb.priority === 'urgente' ? ' selected' : ''}>Urgente</option>
      </select></label>
      <label style="display:block;margin-bottom:8px;"><input type="checkbox" id="ftriage-hseq"${fb.hseq_required ? ' checked' : ''}> Solicitar avaliação HSEQ</label>
      <label style="display:block;margin-bottom:12px;">Observações <textarea id="ftriage-notes" rows="2" style="width:100%;margin-top:4px;" placeholder="Observações da triagem..."></textarea></label>
      <div id="ftriage-error" style="display:none;color:var(--color-danger);font-size:13px;margin-bottom:8px;"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn ghost" id="ftriage-cancel">Cancelar</button>
        <button class="btn" id="ftriage-confirm">Salvar Triagem</button>
      </div>
    </div>`;
    document.body.appendChild(modal);
    bindAppListener(modal.querySelector('#ftriage-cancel'), 'click', () => modal.remove());
    bindAppListener(modal, 'click', (e) => { if (e.target === modal) { modal.remove(); } });
    bindAppListener(modal.querySelector('#ftriage-confirm'), 'click', async () => {
      const errorEl = modal.querySelector('#ftriage-error');
      try {
        await api('/api/feedbacks/triage', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: getState().user?.id,
            feedback_id: fb.id,
            type: modal.querySelector('#ftriage-type').value,
            category: modal.querySelector('#ftriage-category').value.trim(),
            priority: modal.querySelector('#ftriage-priority').value,
            hseq_required: modal.querySelector('#ftriage-hseq').checked,
            notes: modal.querySelector('#ftriage-notes').value.trim(),
          }),
        });
        modal.remove();
        showToast('Triagem salva com sucesso.');
        globalThis.openFeedbackDetail?.(fb.id);
      } catch (e) {
        if (errorEl) { errorEl.style.display = ''; errorEl.textContent = e.message || 'Erro ao salvar triagem.'; }
      }
    });
  }

  // ── openFeedbackHseqModal ─────────────────────────────────────────────────

  function openFeedbackHseqModal(fb) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
    modal.innerHTML = `
    <div class="card" style="max-width:520px;width:min(520px,96vw);margin:auto;padding:24px;">
      <h3 style="margin:0 0 12px;">Parecer HSEQ — Feedback #${esc(String(fb.id))}</h3>
      <label style="display:block;margin-bottom:12px;">Parecer técnico HSEQ <span style="color:var(--color-danger)">*</span>
        <textarea id="fhseq-opinion" rows="4" style="width:100%;margin-top:4px;" placeholder="Descreva o parecer técnico HSEQ..."></textarea>
      </label>
      <label style="display:block;margin-bottom:12px;">Observações adicionais
        <textarea id="fhseq-notes" rows="2" style="width:100%;margin-top:4px;"></textarea>
      </label>
      <div id="fhseq-error" style="display:none;color:var(--color-danger);font-size:13px;margin-bottom:8px;"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn ghost" id="fhseq-cancel">Cancelar</button>
        <button class="btn" id="fhseq-confirm">Registrar Parecer</button>
      </div>
    </div>`;
    document.body.appendChild(modal);
    bindAppListener(modal.querySelector('#fhseq-cancel'), 'click', () => modal.remove());
    bindAppListener(modal, 'click', (e) => { if (e.target === modal) { modal.remove(); } });
    bindAppListener(modal.querySelector('#fhseq-confirm'), 'click', async () => {
      const errorEl = modal.querySelector('#fhseq-error');
      const opinion = modal.querySelector('#fhseq-opinion').value.trim();
      if (!opinion) { errorEl.style.display = ''; errorEl.textContent = 'Parecer HSEQ é obrigatório.'; return; }
      try {
        await api('/api/feedbacks/hseq-review', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: getState().user?.id,
            feedback_id: fb.id,
            hseq_opinion: opinion,
            notes: modal.querySelector('#fhseq-notes').value.trim(),
          }),
        });
        modal.remove();
        showToast('Parecer HSEQ registrado.');
        globalThis.openFeedbackDetail?.(fb.id);
      } catch (e) {
        if (errorEl) { errorEl.style.display = ''; errorEl.textContent = e.message || 'Erro ao registrar parecer.'; }
      }
    });
  }

  // ── forwardFeedbackToAdmin ────────────────────────────────────────────────

  async function forwardFeedbackToAdmin(fbId) {
    if (!confirm('Encaminhar este feedback para aprovação administrativa?')) { return; }
    try {
      await api('/api/feedbacks/forward-admin', {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: getState().user?.id, feedback_id: fbId }),
      });
      showToast('Feedback encaminhado para administração.');
      globalThis.openFeedbackDetail?.(fbId);
    } catch (e) {
      showToast(e.message || 'Erro ao encaminhar.', 'error');
    }
  }

  // ── openFeedbackAdminDecisionModal ────────────────────────────────────────

  function openFeedbackAdminDecisionModal(fb) {
    const isSugestao = (fb.type || '') === 'sugestao';
    const optionsSugestao = [
      ['aprovar_sugestao', 'Aprovar sugestão'],
      ['reprovar_sugestao', 'Reprovar sugestão'],
      ['solicitar_mais_informacoes', 'Solicitar mais informações'],
      ['solicitar_analise_hseq', 'Solicitar análise HSEQ'],
      ['transformar_em_cadastro', 'Transformar em pré-cadastro de EPI'],
      ['encerrar', 'Encerrar sem ação'],
    ];
    const optionsAvaliacao = [
      ['registrar_acao', 'Registrar ação tomada'],
      ['abrir_acao_corretiva', 'Abrir ação corretiva'],
      ['encerrar_como_informacao', 'Encerrar como informação'],
      ['encaminhar_fornecedor', 'Encaminhar para fornecedor'],
      ['registrar_elogio', 'Registrar elogio'],
      ['solicitar_substituicao_epi', 'Solicitar substituição do EPI'],
      ['encerrar', 'Encerrar'],
    ];
    const options = isSugestao ? optionsSugestao : optionsAvaliacao;
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
    modal.innerHTML = `
    <div class="card" style="max-width:520px;width:min(520px,96vw);margin:auto;padding:24px;">
      <h3 style="margin:0 0 12px;">Decisão Administrativa — Feedback #${esc(String(fb.id))}</h3>
      <label style="display:block;margin-bottom:8px;">Decisão <span style="color:var(--color-danger)">*</span>
        <select id="fadmin-decision" style="width:100%;margin-top:4px;">
          <option value="">Selecione...</option>
          ${options.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}
        </select>
      </label>
      <label style="display:block;margin-bottom:8px;">Justificativa <span style="color:var(--color-danger)">*</span>
        <textarea id="fadmin-justification" rows="3" style="width:100%;margin-top:4px;" placeholder="Justificativa obrigatória para a decisão..."></textarea>
      </label>
      <label style="display:block;margin-bottom:12px;">Observações adicionais
        <textarea id="fadmin-notes" rows="2" style="width:100%;margin-top:4px;"></textarea>
      </label>
      <div id="fadmin-error" style="display:none;color:var(--color-danger);font-size:13px;margin-bottom:8px;"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn ghost" id="fadmin-cancel">Cancelar</button>
        <button class="btn" id="fadmin-confirm">Registrar Decisão</button>
      </div>
    </div>`;
    document.body.appendChild(modal);
    bindAppListener(modal.querySelector('#fadmin-cancel'), 'click', () => modal.remove());
    bindAppListener(modal, 'click', (e) => { if (e.target === modal) { modal.remove(); } });
    bindAppListener(modal.querySelector('#fadmin-confirm'), 'click', async () => {
      const errorEl = modal.querySelector('#fadmin-error');
      const decision = modal.querySelector('#fadmin-decision').value;
      const justification = modal.querySelector('#fadmin-justification').value.trim();
      if (!decision) { errorEl.style.display = ''; errorEl.textContent = 'Selecione a decisão.'; return; }
      if (!justification) { errorEl.style.display = ''; errorEl.textContent = 'Justificativa é obrigatória.'; return; }
      try {
        await api('/api/feedbacks/admin-decision', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: getState().user?.id,
            feedback_id: fb.id,
            decision,
            justification,
            notes: modal.querySelector('#fadmin-notes').value.trim(),
          }),
        });
        modal.remove();
        showToast('Decisão registrada com sucesso.');
        globalThis.openFeedbackDetail?.(fb.id);
        globalThis.loadEpiFeedbacks?.();
      } catch (e) {
        if (errorEl) { errorEl.style.display = ''; errorEl.textContent = e.message || 'Erro ao registrar decisão.'; }
      }
    });
  }

  // ── closeFeedback ─────────────────────────────────────────────────────────

  async function closeFeedback(fbId) {
    const notes = prompt('Observação para encerramento (opcional):') ?? '';
    if (notes === null) { return; }
    try {
      await api('/api/feedbacks/close', {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: getState().user?.id, feedback_id: fbId, notes }),
      });
      showToast('Feedback encerrado.');
      globalThis.openFeedbackDetail?.(fbId);
      globalThis.loadEpiFeedbacks?.();
    } catch (e) {
      showToast(e.message || 'Erro ao encerrar.', 'error');
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const feedbackExports = {
    openFeedbackTriageModal,
    openFeedbackHseqModal,
    forwardFeedbackToAdmin,
    openFeedbackAdminDecisionModal,
    closeFeedback,
  };

  for (const [name, fn] of Object.entries(feedbackExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_FEEDBACK__ = Object.freeze({ ...feedbackExports });
})();
