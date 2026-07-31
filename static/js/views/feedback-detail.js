'use strict';

(function () {
  if (globalThis.__EPI_MODULE_FEEDBACK_DETAIL_LOADED__) { return; }
  globalThis.__EPI_MODULE_FEEDBACK_DETAIL_LOADED__ = true;

  // ── Local wrappers ─────────────────────────────────────────────────────────
  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function showToast(msg, type) { if (typeof globalThis.showToast === 'function') { globalThis.showToast(msg, type); } }
  function esc(value) { return globalThis.escapeHtml?.(value) ?? String(value ?? ''); }
  function tr(key, fallback) { return typeof globalThis.tr === 'function' ? globalThis.tr(key, fallback) : (fallback ?? key); }
  function hasPermission(perm) { return globalThis.currentUserHasPermission?.(perm) ?? false; }
  function openFeedbackTriageModal(fb) { globalThis.openFeedbackTriageModal?.(fb); }
  function forwardFeedbackToAdmin(id) { return globalThis.forwardFeedbackToAdmin?.(id); }
  function openFeedbackHseqModal(fb) { globalThis.openFeedbackHseqModal?.(fb); }
  function openFeedbackAdminDecisionModal(fb) { globalThis.openFeedbackAdminDecisionModal?.(fb); }
  function closeFeedback(id) { return globalThis.closeFeedback?.(id); }

  // ── Constants ──────────────────────────────────────────────────────────────
  const EPI_FEEDBACK_STATUS_LABELS = {
    enviado_gestor: tr('evaluation.statusManagerReview', 'Em Análise (Gestor)'),
    enviado_admin: tr('evaluation.awaitingAdmin', 'Aguardando Admin'),
    avaliacao_previa: tr('evaluation.previousCompleted', 'Prévia Concluída'),
    aceito: tr('portal.statusAccepted', 'Aceito'),
    recusado: tr('portal.statusRefused', 'Recusado'),
    bem_avaliado: tr('portal.statusWellRatedPlain', 'Bem Avaliado'),
    mal_avaliado: tr('portal.statusPoorlyRatedPlain', 'Mal Avaliado'),
    em_reavaliacao_3m: tr('portal.statusReevaluation3mFull', 'Reavaliação em 3m'),
    em_reavaliacao_6m: tr('portal.statusReevaluation6mFull', 'Reavaliação em 6m'),
    encerrado: tr('evaluation.closed', 'Encerrado'),
    pendente: tr('delivery.pending', 'Pendente'),
    recebido: tr('portal.statusReceived', 'Recebido'),
    aprovado: tr('portal.statusApproved', 'Aprovado'),
    reprovado: tr('portal.statusRejected', 'Reprovado'),
  };

  const EPI_FEEDBACK_TYPE_LABELS = {
    avaliacao: tr('evaluation.single', 'Avaliação'),
    sugestao: tr('evaluation.suggestionSingle', 'Sugestão'),
    reclamacao: tr('evaluation.complaintSingle', 'Reclamação'),
    elogio: tr('evaluation.praiseSingle', 'Elogio'),
  };

  const EPI_FEEDBACK_PRIORITY_COLORS = {
    baixa: 'var(--color-text-muted)',
    normal: '',
    alta: 'orange',
    urgente: 'var(--color-danger)',
  };

  const PORTAL_STATUS_DISPLAY = {
    '': { label: tr('portal.statusSent', 'Enviada'), tok: 'muted' },
    enviado_gestor: { label: tr('portal.statusInReview', 'Em Análise'), tok: 'info' },
    enviado_admin: { label: tr('portal.statusForwardedAdmin', 'Encaminh. Admin'), tok: 'accent' },
    avaliacao_previa: { label: tr('evaluation.previousCompletedIcon', '📋 Prévia Concluída'), tok: 'warning' },
    aceito: { label: tr('portal.statusAccepted', 'Aceito ✓'), tok: 'success' },
    recusado: { label: tr('portal.statusRefused', 'Recusado'), tok: 'danger' },
    bem_avaliado: { label: tr('portal.statusWellRated', '⭐ Bem Avaliado'), tok: 'success' },
    mal_avaliado: { label: tr('portal.statusPoorlyRated', '⚠ Mal Avaliado'), tok: 'danger' },
    em_reavaliacao_3m: { label: tr('portal.statusReevaluation3mFull', 'Reavaliação em 3m'), tok: 'warning' },
    em_reavaliacao_6m: { label: tr('portal.statusReevaluation6mFull', 'Reavaliação em 6m'), tok: 'warning' },
  };

  // ── Module state ───────────────────────────────────────────────────────────
  let _currentFeedbackList = [];
  let _currentFeedbackDetail = null;

  // ── Implementations ────────────────────────────────────────────────────────

  function portalStatusChip(status) {
    const cfg = PORTAL_STATUS_DISPLAY[status] || { label: status || tr('portal.statusSent', 'Enviada'), tok: 'muted' };
    return `<span style="display:inline-block;padding:2px 8px;border-radius:99px;background:var(--${cfg.tok}-soft);color:var(--${cfg.tok});font-size:11px;font-weight:600;">${esc(cfg.label)}</span>`;
  }

  async function loadEpiFeedbacks() {
    const state = getState();
    const tbody = document.getElementById('feedbacks-tbody');
    const table = document.getElementById('feedbacks-table');
    const empty = document.getElementById('feedbacks-empty');
    const detailPanel = document.getElementById('feedbacks-detail-panel');
    if (!tbody) { return; }
    if (detailPanel) { detailPanel.style.display = 'none'; }
    const statusFilter = document.getElementById('feedbacks-filter-status')?.value || '';
    const typeFilter = document.getElementById('feedbacks-filter-type')?.value || '';
    const params = new URLSearchParams({ actor_user_id: state.user?.id || '' });
    if (statusFilter) { params.set('status', statusFilter); }
    if (typeFilter) { params.set('type', typeFilter); }
    try {
      const res = await globalThis.apiFetch(`/api/feedbacks?${params.toString()}`);
      _currentFeedbackList = res?.items || [];
      if (!_currentFeedbackList.length) {
        if (table) { table.style.display = 'none'; }
        if (empty) { empty.style.display = ''; }
        return;
      }
      if (table) { table.style.display = ''; }
      if (empty) { empty.style.display = 'none'; }
      tbody.innerHTML = _currentFeedbackList.map((fb) => {
        const typeLabel = EPI_FEEDBACK_TYPE_LABELS[fb.type] || fb.type || tr('evaluation.single', 'Avaliação');
        const prioColor = EPI_FEEDBACK_PRIORITY_COLORS[fb.priority] || '';
        const portalSt = fb.employee_portal_status || '';
        const psCfgT = PORTAL_STATUS_DISPLAY[portalSt] || { label: EPI_FEEDBACK_STATUS_LABELS[portalSt] || portalSt || 'Enviada', tok: 'muted' };
        const statusChip = `<span style="display:inline-block;padding:2px 8px;border-radius:99px;background:var(--${psCfgT.tok}-soft);color:var(--${psCfgT.tok});font-size:11px;font-weight:600;">${esc(psCfgT.label)}</span>`;
        return `<tr>
        <td>${esc(String(fb.id))}</td>
        <td>${esc(typeLabel)}</td>
        <td>${esc(fb.epi_name || '—')}</td>
        <td>${esc(fb.employee_name || '—')}</td>
        <td>${esc(fb.unit_name || '—')}</td>
        <td style="color:${prioColor}">${esc(fb.priority || 'normal')}</td>
        <td>${statusChip}</td>
        <td>${esc((fb.created_at || '').slice(0, 10))}</td>
        <td><button class="btn ghost" style="font-size:12px;" data-feedback-open="${esc(String(fb.id))}">${tr('seeAll', 'Ver')}</button></td>
      </tr>`;
      }).join('');
      tbody.querySelectorAll('[data-feedback-open]').forEach((btn) => {
        btn.addEventListener('click', () => openFeedbackDetail(Number(btn.dataset.feedbackOpen)));
      });
    } catch (e) {
      showToast(e.message || 'Erro ao carregar feedbacks.', 'error');
    }
  }

  async function openFeedbackDetail(fbId) {
    const state = getState();
    try {
      const res = await globalThis.apiFetch(`/api/feedbacks/${fbId}?actor_user_id=${encodeURIComponent(state.user?.id || '')}`);
      _currentFeedbackDetail = res?.item ?? res;
      renderFeedbackDetail(_currentFeedbackDetail);
      const detailPanel = document.getElementById('feedbacks-detail-panel');
      if (detailPanel) { detailPanel.style.display = ''; detailPanel.scrollIntoView({ behavior: 'smooth' }); }
    } catch (e) {
      showToast(e.message || 'Erro ao carregar detalhe.', 'error');
    }
  }

  function renderFeedbackDetail(fb) {
    const title = document.getElementById('feedbacks-detail-title');
    if (title) { title.textContent = `Feedback #${fb.id} — ${EPI_FEEDBACK_TYPE_LABELS[fb.type] || fb.type || tr('evaluation.single', 'Avaliação')}`; }
    const info = document.getElementById('feedbacks-detail-info');
    if (info) {
      info.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;">
        <div><strong>${tr('employee.singleTitle', 'Colaborador')}:</strong> ${esc(fb.employee_name || '—')}</div>
        <div><strong>${tr('unit.title', 'Unidade')}:</strong> ${esc(fb.unit_name || '—')}</div>
        <div><strong>${tr('epi.title', 'EPI')}:</strong> ${esc(fb.epi_name || '—')}</div>
        <div><strong>${tr('portal.type', 'Tipo')}:</strong> ${esc(EPI_FEEDBACK_TYPE_LABELS[fb.type] || fb.type || '—')}</div>
        <div><strong>${tr('evaluation.priority', 'Prioridade')}:</strong> ${esc(fb.priority || 'normal')}</div>
        <div><strong>${tr('delivery.status', 'Status')}:</strong> ${portalStatusChip(fb.employee_portal_status || '')}</div>
        <div><strong>${tr('portal.date', 'Data')}:</strong> ${esc((fb.created_at || '').slice(0, 16).replace('T', ' '))}</div>
      </div>
      ${fb.comments ? `<div style="margin-top:8px;"><strong>${tr('signature.comments', 'Comentários')}:</strong> ${esc(fb.comments)}</div>` : ''}
      ${fb.improvement_suggestion ? `<div style="margin-top:4px;"><strong>${tr('portal.improvementSuggestionForPpe', 'Sugestão de melhoria para este EPI')}:</strong> ${esc(fb.improvement_suggestion)}</div>` : ''}
      ${fb.suggested_new_epi_name ? `<div style="margin-top:4px;"><strong>${tr('portal.suggestedPpeName', 'EPI sugerido')}:</strong> ${esc(fb.suggested_new_epi_name)}${fb.suggested_new_epi_notes ? ` — ${esc(fb.suggested_new_epi_notes)}` : ''}${fb.suggested_new_epi_link ? ` — <a href="${esc(fb.suggested_new_epi_link)}" target="_blank" rel="noopener noreferrer">${tr('portal.viewLink', 'Ver link')}</a>` : ''}</div>` : ''}
      ${fb.hseq_opinion ? `<div style="margin-top:8px;padding:8px;background:var(--color-bg-alt);border-radius:4px;"><strong>Parecer HSEQ:</strong> ${esc(fb.hseq_opinion)}</div>` : ''}
      ${fb.admin_decision ? `<div style="margin-top:8px;padding:8px;background:var(--color-bg-alt);border-radius:4px;"><strong>${tr('evaluation.adminDecision', 'Decisão Administrativa')}:</strong> ${esc(fb.admin_decision)}${fb.final_justification ? ` — ${esc(fb.final_justification)}` : ''}</div>` : ''}
    `;
    }
    const actionsEl = document.getElementById('feedbacks-detail-actions');
    if (actionsEl) { renderFeedbackActions(fb, actionsEl); }
    const historyEl = document.getElementById('feedbacks-detail-history');
    if (historyEl) {
      const history = fb.history || [];
      historyEl.innerHTML = history.length
        ? history.map((h) => `<div style="padding:6px 0;border-bottom:1px solid var(--color-border);font-size:12px;">
          [${esc((h.created_at || '').slice(0, 16).replace('T', ' '))}] <strong>${esc(h.actor_name || 'Sistema')}</strong>
          ${h.actor_role ? `<small>(${esc(h.actor_role)})</small>` : ''}
          — ${esc(h.action || h.status || '')}
          ${h.previous_status ? `<em> ${esc(EPI_FEEDBACK_STATUS_LABELS[h.previous_status] || h.previous_status)} → ${esc(EPI_FEEDBACK_STATUS_LABELS[h.status] || h.status)}</em>` : ''}
          ${h.reason ? `<small> Motivo: ${esc(h.reason)}</small>` : ''}
          ${h.notes ? `<br><span>${esc(h.notes)}</span>` : ''}
        </div>`).join('')
        : `<em>${tr('portal.noHistory', 'Sem histórico.')}</em>`;
    }
  }

  function renderFeedbackActions(fb, container) {
    container.innerHTML = '';
    const canTriage = hasPermission('epi_feedback:triage');
    const canHseq = hasPermission('epi_feedback:hseq_review');
    const canAdminApprove = hasPermission('epi_feedback:admin_approve');
    const canClose = hasPermission('epi_feedback:close');
    const status = fb.status || 'pendente';
    const addBtn = (label, ghost, danger, handler) => {
      const btn = document.createElement('button');
      btn.className = ghost ? 'btn ghost' : 'btn';
      if (danger) { btn.style.cssText += ';border-color:var(--color-danger);color:var(--color-danger);'; }
      btn.style.fontSize = '13px';
      btn.textContent = label;
      btn.addEventListener('click', handler);
      container.appendChild(btn);
    };
    if (canTriage && ['pendente', 'recebido', 'em_analise_gestor', 'analise_hseq_concluida'].includes(status)) {
      addBtn(tr('evaluation.doTriageClassify', 'Fazer Triagem / Classificar'), false, false, () => openFeedbackTriageModal(fb));
    }
    if (canTriage && ['em_analise_gestor', 'analise_hseq_concluida'].includes(status)) {
      addBtn(tr('evaluation.forwardToAdmin', 'Encaminhar para Administração'), true, false, () => forwardFeedbackToAdmin(fb.id));
    }
    if (canHseq && status === 'aguardando_hseq') {
      addBtn(tr('evaluation.registerHseqOpinion', 'Registrar Parecer HSEQ'), false, false, () => openFeedbackHseqModal(fb));
    }
    if (canAdminApprove && ['aguardando_aprovacao_admin', 'encaminhado_administracao'].includes(status)) {
      addBtn('Registrar Decisão Administrativa', false, false, () => openFeedbackAdminDecisionModal(fb));
    }
    if (canClose && !['encerrado', 'reprovado'].includes(status)) {
      addBtn(tr('evaluation.closeFeedback', 'Encerrar'), true, true, () => closeFeedback(fb.id));
    }
  }

  // ── Init: bind panel buttons ───────────────────────────────────────────────
  document.getElementById('feedbacks-refresh')?.addEventListener('click', loadEpiFeedbacks);
  document.getElementById('feedbacks-filter-apply')?.addEventListener('click', loadEpiFeedbacks);
  document.getElementById('feedbacks-detail-back')?.addEventListener('click', () => {
    const detailPanel = document.getElementById('feedbacks-detail-panel');
    if (detailPanel) { detailPanel.style.display = 'none'; }
  });

  // ── Exports ────────────────────────────────────────────────────────────────
  const moduleExports = {
    portalStatusChip,
    loadEpiFeedbacks,
    openFeedbackDetail,
    renderFeedbackDetail,
    renderFeedbackActions,
    EPI_FEEDBACK_STATUS_LABELS,
    EPI_FEEDBACK_TYPE_LABELS,
    EPI_FEEDBACK_PRIORITY_COLORS,
    PORTAL_STATUS_DISPLAY
  };

  for (const [name, fn] of Object.entries(moduleExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_FEEDBACK_DETAIL__ = Object.freeze({ ...moduleExports });
})();
