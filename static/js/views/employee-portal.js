'use strict';

// Employee Portal view module (refatoração JS — Fase 6).
// Extrai funções de acesso externo do colaborador de app.js.
// Segue o padrão aditivo paralelo: exporta para globalThis com sobrescrita.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PORTAL_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PORTAL_LOADED__ = true;

  // ── Utilitários locais ─────────────────────────────────────────────────────

  function safeOn(target, eventName, handler, options) {
    if (!target || typeof target.addEventListener !== 'function' || typeof handler !== 'function') {return false;}
    target.addEventListener(eventName, handler, options);
    return true;
  }

  function esc(value) {
    return (globalThis.escapeHtml ?? ((v) => String(v ?? '')))(value);
  }

  function formatDate(value) {
    return globalThis.formatDate?.(value) ?? String(value || '-');
  }

  function formatDateTime(value) {
    return globalThis.formatDateTime?.(value) ?? String(value || '-');
  }

  function api(path, options) {
    if (typeof globalThis.api === 'function') {return globalThis.api(path, options);}
    // Fallback minimal para uso fora do contexto de app.js
    const opts = options || {};
    if (!opts.headers) {opts.headers = {};}
    return fetch(path, opts).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {throw new Error(data?.error || data?.message || `HTTP ${res.status}`);}
      return data;
    });
  }

  function resolveItemSize(formValues) {
    if (typeof globalThis.resolveItemSize === 'function') {return globalThis.resolveItemSize(formValues);}
    // Fallback simples
    const glove_size = formValues.glove_size || 'N/A';
    const size = formValues.size || 'N/A';
    const uniform_size = formValues.uniform_size || 'N/A';
    const selectedSize = [glove_size, size, uniform_size].find((v) => v && v !== 'N/A') || 'N/A';
    return { glove_size, size, uniform_size, selectedSize };
  }

  function openSignatureModal(config) {
    if (typeof globalThis.openSignatureModal === 'function') {return globalThis.openSignatureModal(config);}
  }

  function closeSignatureModal() {
    if (typeof globalThis.closeSignatureModal === 'function') {return globalThis.closeSignatureModal();}
  }

  // ── Portal CPF helpers ─────────────────────────────────────────────────────

  function portalCpfStorageKey(token) {
    return `employee_portal_cpf_last3_${String(token || '').slice(0, 18)}`;
  }

  function cachePortalCpfLast3(token, cpfLast3) {
    if (!/^\d{3}$/.test(String(cpfLast3 || ''))) {return;}
    sessionStorage.setItem(portalCpfStorageKey(token), String(cpfLast3));
  }

  function getCachedPortalCpfLast3(token) {
    const cached = String(sessionStorage.getItem(portalCpfStorageKey(token)) || '').trim();
    return /^\d{3}$/.test(cached) ? cached : '';
  }

  // ── Tela de validação de CPF ───────────────────────────────────────────────

  function renderEmployeeCpfValidationScreen(token, message = '', locked = false) {
    const safeMessage = esc(String(message || ''));
    document.body.innerHTML = `
    <section class="screen active">
      <div class="login-panel employee-portal-shell" style="max-width:460px;">
        <h2>Validação de CPF</h2>
        <p>Digite os 3 últimos números do CPF para acessar o portal.</p>
        <label>Últimos 3 dígitos do CPF
          <input id="employee-cpf-last3" maxlength="3" inputmode="numeric" placeholder="000" ${locked ? 'disabled' : ''}>
        </label>
        <small id="employee-cpf-feedback" class="hint" style="${message ? 'color:#b42318;' : ''}">${safeMessage || 'Você tem até 3 tentativas por token.'}</small>
        <button id="employee-cpf-submit" class="primary" type="button" ${locked ? 'disabled' : ''}>Validar acesso</button>
      </div>
    </section>
  `;
    const input = document.getElementById('employee-cpf-last3');
    const submit = document.getElementById('employee-cpf-submit');
    const feedback = document.getElementById('employee-cpf-feedback');
    if (!input || !submit || !feedback) {return;}
    const cached = getCachedPortalCpfLast3(token);
    if (cached && !locked) {input.value = cached;}
    safeOn(input, 'input', () => { input.value = String(input.value || '').replace(/\D/g, '').slice(0, 3); });
    safeOn(input, 'keyup', (event) => {
      if (event.key === 'Enter' && !locked) {submit.click();}
    });
    safeOn(submit, 'click', async () => {
      const cpfLast3 = String(input.value || '').replace(/\D/g, '').slice(0, 3);
      if (!/^\d{3}$/.test(cpfLast3)) {
        feedback.textContent = 'Informe exatamente os 3 últimos dígitos do CPF.';
        feedback.style.color = '#b42318';
        return;
      }
      try {
        await renderEmployeeExternalAccess(token, cpfLast3);
        cachePortalCpfLast3(token, cpfLast3);
      } catch (error) {
        const msg = String(error?.message || 'Não foi possível validar o CPF.');
        feedback.textContent = msg;
        feedback.style.color = '#b42318';
        if (msg.toLowerCase().includes('bloqueado') || msg.toLowerCase().includes('novo link')) {
          submit.disabled = true;
          input.disabled = true;
        }
      }
    });
  }

  // ── Tela principal do portal do colaborador ────────────────────────────────

  async function renderEmployeeExternalAccess(token, cpfLast3 = '', preferredFichaPeriodId = '') {
    const payload = await api(`/api/employee-access?token=${encodeURIComponent(token)}&cpf_last3=${encodeURIComponent(cpfLast3)}`, { headers: {} });
    const employee = payload.employee || {};
    const deliveries = payload.deliveries || [];
    const fichas = payload.fichas || [];
    const requests = payload.requests || [];
    const feedbacks = payload.feedbacks || [];
    const availableEpis = payload.available_epis || [];
    const gloveSizeOptions = ['N/A', 'XP (6)', 'P (7)', 'M (8)', 'G (9)', 'XG (10)', 'XXG (11)'];
    const sizeOptions = ['N/A', 'N°34', 'N°35', 'N°36', 'N°37', 'N°38', 'N°39', 'N°40', 'N°41', 'N°42', 'N°43', 'N°44', 'N°45', 'N°46', 'N°47', 'N°48', 'N°49', 'N°50', 'N°51', 'N°52', 'N°53', 'N°54', 'N°55', 'N°56', 'N°57', 'N°58', 'N°59', 'N°60'];
    const uniformSizeOptions = ['N/A', 'XP', 'PP', 'P', 'M', 'G', 'GG', 'XGG', 'XXG'];
    const requestSizeLabel = (item) => [item.glove_size, item.size, item.uniform_size].filter((value) => value && value !== 'N/A').join(' / ') || 'N/A';
    const requestedPeriodId = String(preferredFichaPeriodId || '').trim();
    const initialFichaPeriodId = String(
      (requestedPeriodId && fichas.some((item) => String(item?.id || '').trim() === requestedPeriodId) ? requestedPeriodId : (fichas[0]?.id || ''))
    ).trim();
    const findFichaPeriod = (periodId) => (fichas || []).find((item) => String(item?.id || '').trim() === String(periodId || '').trim()) || null;
    const parsePortalDateValue = (value) => {
      const normalized = String(value || '').trim();
      if (!normalized) {return null;}
      const parsed = new Date(normalized.length <= 10 ? `${normalized}T00:00:00` : normalized);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    };
    const isDeliveryInsidePeriod = (delivery, fichaPeriod) => {
      if (!fichaPeriod) {return false;}
      const deliveryDate = parsePortalDateValue(delivery?.delivery_date || delivery?.delivered_at || delivery?.created_at || delivery?.date);
      const periodStart = parsePortalDateValue(fichaPeriod?.period_start);
      const periodEnd = parsePortalDateValue(fichaPeriod?.period_end);
      if (!deliveryDate || !periodStart || !periodEnd) {return false;}
      return deliveryDate >= periodStart && deliveryDate <= periodEnd;
    };
    const buildPortalDeliveryRows = (periodId) => {
      const selectedPeriodId = String(periodId || '').trim();
      const selectedFichaPeriod = findFichaPeriod(selectedPeriodId);
      let periodDeliveries = (deliveries || []).filter((item) => String(item?.ficha_period_id || '').trim() === selectedPeriodId);
      if (!periodDeliveries.length) {
        periodDeliveries = (deliveries || []).filter((item) => isDeliveryInsidePeriod(item, selectedFichaPeriod));
      }
      return periodDeliveries.length ? periodDeliveries.map((item) => {
        const deliveredAt = formatDate(item.delivery_date || item.delivered_at || item.created_at || item.date);
        const signed = String(item.item_signature_at || '').trim() !== '';
        return `<tr>
                <td>${esc(item.epi_name || item.name || '-')}</td>
                <td>${esc(deliveredAt)}</td>
                <td>${signed ? 'Assinado' : 'Pendente'}</td>
                <td>${signed ? 'Assinado' : 'Pendente (use assinatura em lote do período)'}</td>
              </tr>`;
      }).join('') : '<tr><td colspan="4">Nenhuma entrega registrada para o período selecionado.</td></tr>';
    };
    const initialDeliveryRows = buildPortalDeliveryRows(initialFichaPeriodId);
    document.body.innerHTML = `
    <section class="screen active">
      <div class="login-panel employee-portal-shell">
        <h2>Acesso do Colaborador</h2>
        <p><strong>${esc(employee.employee_name || '-')}</strong> ${esc(employee.company_name || '-')}</p>
        <p>ID: ${esc(employee.employee_id_code || '-')} | Setor: ${esc(employee.sector || '-')}</p>
        <label>Assinatura do colaborador
          <button id="employee-signature-open" class="ghost" type="button">Clique aqui para assinar</button>
        </label>
        <small id="employee-signature-status" class="hint">Assinatura pendente para o período.</small>
        <label>Período da ficha</label>
        <select id="employee-ficha-period">${fichas.map((item) => `<option value="${esc(item.id)}" data-total-items="${esc(item.total_items || 0)}" data-pending-items="${esc(item.pending_items || 0)}" data-has-batch-signature="${item.has_batch_signature ? '1' : '0'}">${esc(formatDate(item.period_start))} a ${esc(formatDate(item.period_end))} (${esc(item.status)} | pendentes: ${esc(item.pending_items || 0)})</option>`).join('')}</select>
        <small id="employee-period-status" class="hint"></small>
        <button id="employee-sign-batch" class="btn btn-primary" type="button">Fechar período selecionado</button>
        <button id="employee-download-pdf" class="btn btn-secondary" type="button">Baixar PDF da ficha</button>
        <div class="table-wrap users-table-wrap">
          <table>
            <thead>
              <tr>
                <th>EPI</th>
                <th>Data de Entrega</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              ${initialDeliveryRows}
            </tbody>
          </table>
        </div>
        <div class="portal-tabs">
          <button class="menu-link active" data-portal-tab="ficha">Ficha de EPI</button>
          <button class="menu-link" data-portal-tab="solicitacao">Solicitação de EPI</button>
          <button class="menu-link" data-portal-tab="avaliacao">Avaliação</button>
        </div>
        <div data-portal-pane="ficha">
          <h3>Ficha de EPI</h3>
          <div class="table-wrap users-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>EPI</th>
                  <th>Data de Entrega</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                ${initialDeliveryRows}
              </tbody>
            </table>
          </div>
        </div>
        <div data-portal-pane="solicitacao" style="display:none;">
          <h3>Solicitar EPI cadastrado</h3>
          <label>EPI disponível</label>
          <select id="employee-request-epi">${availableEpis.map((item) => `<option value="${esc(item.id)}">${esc(item.name)} (${esc(item.purchase_code || '-')})</option>`).join('')}</select>
          <fieldset class="size-group">
            <legend>Tamanhos do item</legend>
            <div class="size-grid">
              <label>Tamanho-luva
                <select id="employee-request-glove-size">${gloveSizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
              <label>Tamanho
                <select id="employee-request-size">${sizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
              <label>Tamanho-uniforme
                <select id="employee-request-uniform-size">${uniformSizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
            </div>
          </fieldset>
          <label>Quantidade</label>
          <input id="employee-request-quantity" type="number" min="1" value="1">
          <label>Justificativa</label>
          <textarea id="employee-request-justification" rows="3" placeholder="Motivo da solicitação"></textarea>
          <button id="employee-request-submit" class="btn btn-primary" type="button">Enviar solicitação</button>
          <div class="table-wrap users-table-wrap"><table><thead><tr><th>ID</th><th>EPI</th><th>Tamanho</th><th>Qtd</th><th>Status</th><th>Informação</th><th>Data</th></tr></thead><tbody>${requests.map((item) => {
            const STATUS_PT = { 'solicitado': 'Solicitado', 'em análise': 'Em Análise', 'aprovado': 'Aprovado', 'rejeitado': 'Reprovado', 'prorrogado': 'Prorrogado', 'separado': 'Separado', 'entregue': 'Entregue', 'assinado': 'Assinado', 'included_in_request': 'Em Requisição' };
            const statusLabel = STATUS_PT[item.status] || item.status;
            const statusColor = { 'aprovado': 'var(--color-success)', 'rejeitado': 'var(--color-danger)', 'prorrogado': 'var(--color-warning)', 'entregue': 'var(--color-success)', 'assinado': 'var(--color-success)' }[item.status] || 'inherit';
            const info = item.status === 'rejeitado' && item.rejection_reason ? `Motivo: ${esc(item.rejection_reason)}` : item.status === 'prorrogado' && item.postponed_until ? `Até: ${esc(formatDate(item.postponed_until))}` : '—';
            return `<tr><td>#${esc(item.id)}</td><td>${esc(item.epi_name)}</td><td>${esc(requestSizeLabel(item))}</td><td>${esc(item.quantity)}</td><td style="color:${statusColor};font-weight:600;">${esc(statusLabel)}</td><td style="font-size:12px;">${info}</td><td>${esc(formatDate(item.requested_at))}</td></tr>`;
          }).join('') || '<tr><td colspan="7">Sem solicitações.</td></tr>'}</tbody></table></div>
        </div>
        <div data-portal-pane="avaliacao" style="display:none;">
          <h3>Avaliações e Sugestões</h3>
          <div style="background:linear-gradient(135deg,#1e40af 0%,#7c3aed 100%);color:#fff;border-radius:12px;padding:16px 18px;margin-bottom:20px;">
            <div style="font-size:14px;font-weight:700;margin-bottom:5px;">⭐ Contribua para o Ranking de EPIs!</div>
            <p style="margin:0;font-size:12px;line-height:1.5;">Suas avaliações alimentam o <strong>Ranking de EPIs</strong> da empresa. EPIs bem avaliados são priorizados nas compras e o retorno que você recebe aqui reflete exatamente o rank do equipamento. Sugestões de novos EPIs são analisadas pelos gestores — a decisão final é do Administrador Geral.</p>
          </div>

          <div style="border:2px solid #2563eb;border-radius:12px;padding:16px;margin-bottom:20px;background:#f0f7ff;">
            <h4 style="margin:0 0 10px;color:#1e40af;font-size:15px;">📋 Avaliar EPI em Uso</h4>
            <p style="margin:0 0 12px;font-size:12px;color:#374151;">Avalie um EPI aprovado que você já recebeu ou está usando. Sua nota entra diretamente no ranking.</p>
            <label>EPI avaliado <span style="color:#dc2626">*</span>
              <select id="employee-eval-epi" style="width:100%;margin-top:4px;">
                <option value="">Selecione o EPI</option>
                ${availableEpis.map((item) => `<option value="${esc(item.id)}">${esc(item.name)} (${esc(item.purchase_code || '-')})</option>`).join('')}
              </select>
            </label>
            <label style="margin-top:10px;">Tipo de Avaliação
              <select id="employee-eval-type" style="width:100%;margin-top:4px;">
                <option value="elogio">👍 Elogio — EPI está bom</option>
                <option value="reclamacao">👎 Reclamação — EPI tem problema</option>
              </select>
            </label>
            <div class="grid cols-2" style="margin-top:10px;">
              <label>Conforto (0–5)<input id="employee-eval-comfort" type="number" min="0" max="5" value="0"></label>
              <label>Qualidade (0–5)<input id="employee-eval-quality" type="number" min="0" max="5" value="0"></label>
              <label>Adequação (0–5)<input id="employee-eval-adequacy" type="number" min="0" max="5" value="0"></label>
              <label>Desempenho (0–5)<input id="employee-eval-performance" type="number" min="0" max="5" value="0"></label>
            </div>
            <label style="margin-top:8px;">Observações
              <textarea id="employee-eval-comments" rows="2" placeholder="Descreva sua experiência com este EPI..."></textarea>
            </label>
            <label>Sugestão de melhoria para este EPI
              <textarea id="employee-eval-improvement" rows="2" placeholder="Como poderíamos melhorar este EPI?"></textarea>
            </label>
            <button id="employee-epi-eval-submit" class="btn btn-primary" type="button" style="margin-top:10px;">Enviar Avaliação</button>
          </div>

          <div style="border:2px solid #7c3aed;border-radius:12px;padding:16px;margin-bottom:20px;background:#faf5ff;">
            <h4 style="margin:0 0 10px;color:#7c3aed;font-size:15px;">💡 Sugerir Novo EPI</h4>
            <p style="margin:0 0 12px;font-size:12px;color:#374151;">Sugira um equipamento que deveria ser adquirido. A decisão final é do <strong>Administrador Geral</strong>.</p>
            <label>Nome do EPI sugerido <span style="color:#dc2626">*</span>
              <input id="employee-sug-name" type="text" placeholder="Ex: Luva de nitrilo tamanho M" style="width:100%;margin-top:4px;">
            </label>
            <label style="margin-top:10px;">Por que este EPI é necessário?
              <textarea id="employee-sug-notes" rows="2" placeholder="Qual problema ele resolve? Em que situação seria usado?"></textarea>
            </label>
            <label>Link de referência (opcional)
              <input id="employee-sug-link" type="url" placeholder="https://..." style="width:100%;margin-top:4px;">
            </label>
            <button id="employee-sug-submit" class="btn btn-primary" type="button" style="margin-top:10px;background:#7c3aed;border-color:#7c3aed;">Enviar Sugestão</button>
          </div>

          <h4 style="margin:20px 0 8px;font-size:14px;">Minhas Avaliações de EPI</h4>
          <div class="table-wrap users-table-wrap" style="margin-bottom:20px;">
            <table>
              <thead><tr><th>ID</th><th>EPI</th><th>Tipo</th><th>Status / Rank</th><th>Retorno</th></tr></thead>
              <tbody>
                ${(() => {
                    const epiEvals = feedbacks.filter((fb) => fb.type !== 'sugestao' && !fb.suggested_new_epi_name);
                    const psCfg = (ps) => ({ '': { label: 'Enviada', color: '#6b7280' }, enviado_gestor: { label: 'Em Análise', color: '#2563eb' }, enviado_admin: { label: 'Encaminh. Admin', color: '#7c3aed' }, aceito: { label: 'Aceito ✓', color: '#16a34a' }, recusado: { label: 'Recusado', color: '#dc2626' }, bem_avaliado: { label: '⭐ Bem Avaliado', color: '#16a34a' }, mal_avaliado: { label: '⚠ Mal Avaliado', color: '#dc2626' }, em_reavaliacao_3m: { label: 'Reavaliação 3m', color: '#d97706' }, em_reavaliacao_6m: { label: 'Reavaliação 6m', color: '#d97706' } }[ps] || { label: ps || '-', color: '#6b7280' });
                    const typeLabel = (t) => t === 'elogio' ? '👍 Elogio' : t === 'reclamacao' ? '👎 Reclamação' : '📋 Avaliação';
                    return epiEvals.length ? epiEvals.map((item) => {
                      const cfg = psCfg(item.employee_portal_status || '');
                      const chip = `<span style="display:inline-block;padding:2px 7px;border-radius:99px;background:${cfg.color};color:#fff;font-size:11px;font-weight:600;">${esc(cfg.label)}</span>`;
                      return `<tr><td>#${esc(item.id)}</td><td>${esc(item.epi_name || '-')}</td><td style="font-size:11px;">${esc(typeLabel(item.type))}</td><td>${chip}</td><td style="font-size:11px;max-width:200px;">${esc(item.employee_portal_message || '-')}</td></tr>`;
                    }).join('') : '<tr><td colspan="5" style="text-align:center;opacity:.6;">Sem avaliações registradas.</td></tr>';
                  })()}
              </tbody>
            </table>
          </div>

          <h4 style="margin:0 0 8px;font-size:14px;">Minhas Sugestões de EPI</h4>
          <div class="table-wrap users-table-wrap">
            <table>
              <thead><tr><th>ID</th><th>Sugestão</th><th>Status</th><th>Retorno do Administrador</th></tr></thead>
              <tbody>
                ${(() => {
                    const sugs = feedbacks.filter((fb) => fb.type === 'sugestao' || fb.suggested_new_epi_name);
                    const psCfg = (ps) => ({ '': { label: 'Enviada', color: '#6b7280' }, enviado_gestor: { label: 'Em Análise', color: '#2563eb' }, enviado_admin: { label: 'Encaminh. Admin', color: '#7c3aed' }, aceito: { label: 'Aceito ✓', color: '#16a34a' }, recusado: { label: 'Recusado', color: '#dc2626' } }[ps] || { label: ps || '-', color: '#6b7280' });
                    return sugs.length ? sugs.map((item) => {
                      const cfg = psCfg(item.employee_portal_status || '');
                      const chip = `<span style="display:inline-block;padding:2px 7px;border-radius:99px;background:${cfg.color};color:#fff;font-size:11px;font-weight:600;">${esc(cfg.label)}</span>`;
                      return `<tr><td>#${esc(item.id)}</td><td><strong>${esc(item.suggested_new_epi_name || '-')}</strong></td><td>${chip}</td><td style="font-size:11px;max-width:220px;">${esc(item.employee_portal_message || '—')}</td></tr>`;
                    }).join('') : '<tr><td colspan="4" style="text-align:center;opacity:.6;">Sem sugestões registradas.</td></tr>';
                  })()}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>`;
    (function bindPortalSignatureModal() {
      const modal = document.getElementById('signature-modal');
      const cancelBtn = document.getElementById('signature-modal-cancel');
      const confirmBtn = document.getElementById('signature-modal-confirm');
      const openBtn = document.getElementById('delivery-signature-open');
      if (!modal || !cancelBtn || !confirmBtn) {return;}
      if (openBtn) {
        safeOn(openBtn, 'click', () => {
          const employeeSelect = document.getElementById('delivery-employee');
          const signerName = employeeSelect?.options[employeeSelect.selectedIndex]?.text || '';
          openSignatureModal({
            signerName: signerName,
            comment: '',
            onConfirm: (data) => {
              const sigData = document.getElementById('delivery-signature-data');
              const sigName = document.getElementById('delivery-signature-name');
              const sigAt = document.getElementById('delivery-signature-at');
              const sigComment = document.getElementById('delivery-signature-comment');
              if (sigData) {sigData.value = data.signature_data;}
              if (sigName) {sigName.value = data.signature_name;}
              if (sigAt) {sigAt.value = data.signature_at;}
              if (sigComment) {sigComment.value = data.signature_comment;}
              const status = document.getElementById('delivery-signature-status');
              if (status) {status.textContent = 'Assinatura coletada. ✓';}
            }
          });
        });
      }
      safeOn(cancelBtn, 'click', closeSignatureModal);
      safeOn(modal, 'click', (event) => {
        if (event.target === modal) {closeSignatureModal();}
      });
      safeOn(confirmBtn, 'click', () => {
        const appState = globalThis.__EPI_APP_STATE__ || {};
        if (!appState.signatureDraft?.onConfirm) {return closeSignatureModal();}
        const signaturePadController = globalThis.signaturePadController || null;
        const signatureData = signaturePadController?.getData?.() || '';
        if (!signatureData) {
          alert('Assinatura digital obrigatória. Desenhe no campo de assinatura.');
          return;
        }
        appState.signatureDraft.onConfirm({
          signature_name: String(document.getElementById('signature-modal-name')?.value || '').trim() || 'Assinatura digital',
          signature_data: signatureData,
          signature_at: new Date().toISOString(),
          signature_comment: String(document.getElementById('signature-modal-comment')?.value || '').trim()
        });
        closeSignatureModal();
      });
    })();
    let portalSignature = null;
    const employeeSignatureStatus = document.getElementById('employee-signature-status');
    const employeeSignatureOpen = document.getElementById('employee-signature-open');
    safeOn(employeeSignatureOpen, 'click', () => {
      openSignatureModal({
        signerName: employee.employee_name || 'Assinatura digital',
        comment: portalSignature?.signature_comment || '',
        onConfirm: async (payloadSignature) => {
          const fichaPeriodId = String(document.getElementById('employee-ficha-period')?.value || '').trim();
          if (!fichaPeriodId) {
            alert('Nenhum período selecionado para assinatura.');
            return;
          }
          try {
            const signResponse = await api('/api/employee-sign-batch', {
              method: 'POST',
              body: JSON.stringify({
                token,
                cpf_last3: cpfLast3,
                ficha_period_id: fichaPeriodId,
                signature_name: payloadSignature.signature_name,
                signature_data: payloadSignature.signature_data,
                signature_comment: payloadSignature.signature_comment
              })
            });
            if (!signResponse?.ok || !signResponse?.signature_state?.has_batch_signature) {
              throw new Error('Falha ao persistir assinatura em lote no período selecionado.');
            }
            portalSignature = payloadSignature;
            if (employeeSignatureStatus) {
              employeeSignatureStatus.textContent = `Assinatura capturada em ${formatDateTime(payloadSignature.signature_at)}.`;
            }
            await renderEmployeeExternalAccess(token, cpfLast3, fichaPeriodId);
          } catch (error) {
            alert(error?.message || 'Falha ao salvar assinatura em lote.');
            if (employeeSignatureStatus) {
              employeeSignatureStatus.textContent = 'Assinatura pendente para o período.';
            }
          }
        }
      });
    });

    safeOn(document.getElementById('employee-download-pdf'), 'click', () => {
      globalThis.open(`/api/employee-access/pdf?token=${encodeURIComponent(token)}&cpf_last3=${encodeURIComponent(cpfLast3)}`, '_blank');
    });
    document.querySelectorAll('[data-portal-tab]').forEach((button) => {
      safeOn(button, 'click', () => {
        document.querySelectorAll('[data-portal-tab]').forEach((item) => item.classList.remove('active'));
        document.querySelectorAll('[data-portal-pane]').forEach((pane) => { pane.style.display = 'none'; });
        button.classList.add('active');
        const pane = document.querySelector(`[data-portal-pane="${button.dataset.portalTab}"]`);
        if (pane) {pane.style.display = 'block';}
      });
    });
    const syncEmployeePeriodStatus = () => {
      const periodField = document.getElementById('employee-ficha-period');
      const statusField = document.getElementById('employee-period-status');
      const closeButton = document.getElementById('employee-sign-batch');
      if (!periodField || !statusField || !closeButton) {return 0;}
      const selectedPeriodId = String(periodField.value || '').trim();
      document.querySelectorAll('[data-portal-pane="ficha"] tbody, .employee-portal-shell > .table-wrap tbody')
        .forEach((tbody) => { tbody.innerHTML = buildPortalDeliveryRows(selectedPeriodId); });
      const selectedOption = periodField.options?.[periodField.selectedIndex] || null;
      const totalItems = Number(selectedOption?.dataset?.totalItems || 0);
      const pendingItems = Number(selectedOption?.dataset?.pendingItems || 0);
      const hasBatchSignature = String(selectedOption?.dataset?.hasBatchSignature || '0') === '1';
      if (totalItems === 0) {
        statusField.textContent = 'Período inválido (sem itens).';
      } else if (pendingItems > 0) {
        statusField.textContent = `Este período ainda possui ${pendingItems} item(ns) sem assinatura. Assine para liberar o fechamento.`;
      } else if (!hasBatchSignature) {
        statusField.textContent = 'Todos os itens estão assinados, mas a assinatura em lote do período ainda está pendente.';
      } else {
        statusField.textContent = 'Todos os itens já estão assinados. Você já pode fechar o período selecionado.';
      }
      return pendingItems;
    };
    safeOn(document.getElementById('employee-ficha-period'), 'change', syncEmployeePeriodStatus);
    syncEmployeePeriodStatus();

    safeOn(document.getElementById('employee-sign-batch'), 'click', async () => {
      const fichaPeriodId = document.getElementById('employee-ficha-period')?.value;
      if (!fichaPeriodId) {return alert('Nenhum período de ficha selecionado para fechamento.');}
      const pendingItems = syncEmployeePeriodStatus();
      try {
        if (pendingItems > 0) {
          if (!portalSignature?.signature_data) {
            return alert('Ainda existem itens sem assinatura. Clique em "Clique aqui para assinar" para prosseguir.');
          }
          const signResponse = await api('/api/employee-sign-batch', {
            method: 'POST',
            body: JSON.stringify({
              token,
              cpf_last3: cpfLast3,
              ficha_period_id: fichaPeriodId,
              signature_name: portalSignature.signature_name,
              signature_data: portalSignature.signature_data,
              signature_comment: portalSignature.signature_comment
            })
          });
          const nextPendingItems = Number(signResponse?.signature_state?.pending_items ?? NaN);
          if (Number.isFinite(nextPendingItems) && nextPendingItems === 0) {
            alert('Assinatura aplicada com sucesso. Todos os itens foram assinados e o período já pode ser fechado.');
          } else if (Number.isFinite(nextPendingItems)) {
            alert(`Assinatura aplicada. Ainda restam ${nextPendingItems} item(ns) pendente(s) para fechar o período.`);
          } else {
            alert('Assinatura aplicada. Agora finalize o período.');
          }
        } else {
          await api('/api/employee-close-period', {
            method: 'POST',
            body: JSON.stringify({
              token,
              cpf_last3: cpfLast3,
              ficha_period_id: fichaPeriodId
            })
          });
          alert('Período fechado com sucesso.');
        }
        await renderEmployeeExternalAccess(token, cpfLast3, fichaPeriodId);
      } catch (error) {
        alert(error.message);
      }
    });
    safeOn(document.getElementById('employee-request-submit'), 'click', async () => {
      try {
        const resolvedSize = resolveItemSize({
          glove_size: document.getElementById('employee-request-glove-size')?.value,
          size: document.getElementById('employee-request-size')?.value,
          uniform_size: document.getElementById('employee-request-uniform-size')?.value
        });
        if (!resolvedSize.selectedSize || resolvedSize.selectedSize === 'N/A') {
          throw new Error('Selecione o tamanho para solicitar o EPI.');
        }
        await api('/api/requests', {
          method: 'POST',
          body: JSON.stringify({
            token,
            cpf_last3: cpfLast3,
            epi_id: Number(document.getElementById('employee-request-epi')?.value || 0),
            glove_size: resolvedSize.glove_size,
            size: resolvedSize.size,
            uniform_size: resolvedSize.uniform_size,
            quantity: Number(document.getElementById('employee-request-quantity')?.value || 1),
            justification: String(document.getElementById('employee-request-justification')?.value || '').trim()
          })
        });
        alert('Solicitação enviada com sucesso.');
        await renderEmployeeExternalAccess(token, cpfLast3);
      } catch (error) {
        alert(error.message);
      }
    });
    const employeeRequestEpi = document.getElementById('employee-request-epi');
    const syncEmployeeRequestSizes = () => {
      const selectedEpi = availableEpis.find((item) => String(item.id) === String(employeeRequestEpi?.value || ''));
      if (!selectedEpi) {return;}
      const gloveField = document.getElementById('employee-request-glove-size');
      const sizeField = document.getElementById('employee-request-size');
      const uniformField = document.getElementById('employee-request-uniform-size');
      if (gloveField) {gloveField.value = String(selectedEpi.glove_size || 'N/A');}
      if (sizeField) {sizeField.value = String(selectedEpi.size || 'N/A');}
      if (uniformField) {uniformField.value = String(selectedEpi.uniform_size || 'N/A');}
    };
    safeOn(employeeRequestEpi, 'change', syncEmployeeRequestSizes);
    syncEmployeeRequestSizes();
    safeOn(document.getElementById('employee-epi-eval-submit'), 'click', async () => {
      const epiId = document.getElementById('employee-eval-epi')?.value;
      if (!epiId) { alert('Selecione o EPI que está sendo avaliado.'); return; }
      try {
        await api('/api/employee-feedback', {
          method: 'POST',
          body: JSON.stringify({
            token, cpf_last3: cpfLast3,
            type: document.getElementById('employee-eval-type')?.value || 'elogio',
            epi_id: epiId,
            comfort_rating: Number(document.getElementById('employee-eval-comfort')?.value || 0),
            quality_rating: Number(document.getElementById('employee-eval-quality')?.value || 0),
            adequacy_rating: Number(document.getElementById('employee-eval-adequacy')?.value || 0),
            performance_rating: Number(document.getElementById('employee-eval-performance')?.value || 0),
            comments: String(document.getElementById('employee-eval-comments')?.value || '').trim(),
            improvement_suggestion: String(document.getElementById('employee-eval-improvement')?.value || '').trim(),
          })
        });
        alert('Avaliação enviada com sucesso!');
        await renderEmployeeExternalAccess(token, cpfLast3);
      } catch (error) { alert(error.message); }
    });
    safeOn(document.getElementById('employee-sug-submit'), 'click', async () => {
      const sugName = String(document.getElementById('employee-sug-name')?.value || '').trim();
      if (!sugName) { alert('Informe o nome do EPI sugerido.'); return; }
      try {
        await api('/api/employee-feedback', {
          method: 'POST',
          body: JSON.stringify({
            token, cpf_last3: cpfLast3,
            type: 'sugestao',
            suggested_new_epi_name: sugName,
            suggested_new_epi_notes: String(document.getElementById('employee-sug-notes')?.value || '').trim(),
            suggested_new_epi_link: String(document.getElementById('employee-sug-link')?.value || '').trim(),
          })
        });
        alert('Sugestão enviada com sucesso!');
        await renderEmployeeExternalAccess(token, cpfLast3);
      } catch (error) { alert(error.message); }
    });
  }

  // ── Exports ────────────────────────────────────────────────────────────────

  globalThis.portalCpfStorageKey = portalCpfStorageKey;
  globalThis.cachePortalCpfLast3 = cachePortalCpfLast3;
  globalThis.getCachedPortalCpfLast3 = getCachedPortalCpfLast3;
  globalThis.renderEmployeeCpfValidationScreen = renderEmployeeCpfValidationScreen;
  globalThis.renderEmployeeExternalAccess = renderEmployeeExternalAccess;

  globalThis.__EPI_EMPLOYEE_PORTAL__ = Object.freeze({
    portalCpfStorageKey,
    cachePortalCpfLast3,
    getCachedPortalCpfLast3,
    renderEmployeeCpfValidationScreen,
    renderEmployeeExternalAccess,
  });
})();
