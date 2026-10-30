'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, confirmDestructive, formatDate,
   filterByUserCompany, loadBootstrap, runExclusiveMutation, refreshAfterMutation, coalesceLoad --
   globais do app.js, de shared/ui e de views/*, resolvidos na chamada; reportNonCriticalError é global do runtime */

// UI: Arquivamento de Unidades — soft delete com retenção mínima de 5 anos
// (Refatoração UBX-V5, Etapa 1 — extraído de static/app.js).
//
// Arquivar, desarquivar, excluir definitivamente em duas etapas e a lista de
// Unidades arquivadas. Regras puras (filtros, papéis, rótulos do resumo) em
// ../business/archival-rules.js; HTTP em ../integrations/archival-api.js;
// células comuns da linha em ./archival-view.js. Eram funções do app.js; agora
// são globais (showView, VIEW_FILTER_RESET e os listeners do init as chamam).
(function () {
  if (globalThis.__EPI_MODULE_UNIT_ARCHIVAL_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_UNIT_ARCHIVAL_UI_LOADED__ = true;

  // SECURITY-OUTPUT-XSS-V1/V2: escape local de texto de cadastro (não depende do helper global).
  function escapeText(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }
  function rules() { return globalThis.__EPI_ARCHIVAL_RULES__; }
  function archivalApi() { return globalThis.__EPI_ARCHIVAL_API__; }
  function archivalUi() { return globalThis.__EPI_ARCHIVAL_UI__; }

  function refreshUnits() {
    return refreshAfterMutation(async () => {
      await loadBootstrap({ preserveView: true });
      await loadArchivedUnits();
    });
  }

  async function archiveUnit(unitId) {
    return runExclusiveMutation(`archive:unit:${unitId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      if (!requirePermission('units:delete')) {return;}
      const unit = state.units.find((item) => String(item.id) === String(unitId));
      const unitName = unit ? unit.name : `#${unitId}`;
      const message = `${tr('unit.title', 'Unidade')}: "${unitName}"\n\n${tr('unit.archiveConfirm',
        'Esta Unidade será arquivada e deixará de receber novas operações (colaboradores, EPIs, entregas, estoque e compras).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos) para consultas, relatórios e auditorias.\n\nNenhum dado será excluído.')}`;
      if (!(await confirmDestructive({ title: tr('unit.archiveTitle', 'Arquivar Unidade'), message, confirmLabel: tr('unit.archive', 'Arquivar'), variant: 'danger' }))) {return;}
      const reason = globalThis.prompt(tr('unit.archiveReasonPrompt', 'Motivo do arquivamento (registrado na auditoria):'), '') ?? '';
      try {
        await archivalApi().archiveRecord('units', unitId, { actor_user_id: state.user.id, reason });
      } catch (error) {
        alert(error.message);
        return;
      }
      await refreshUnits();
    });
  }

  async function loadArchivedUnits() {
    if (!hasPermission('units:view')) {return;}
    return coalesceLoad('archived:units', async () => {
      const state = globalThis.__EPI_APP_STATE__;
      try {
        const data = await archivalApi().listArchived('units', actorQuery());
        state.archivedUnits = data.units || [];
      } catch (error) {
        state.archivedUnits = [];
        reportNonCriticalError('[unidades] falha ao carregar unidades arquivadas', error);
      }
      renderArchivedUnits();
    });
  }

  function formatArchivedUnitRow(item, canManage, canPurge) {
    const { retentionLabel, statusBadge, holdBadge } = archivalUi().archivedRowParts(item);
    const actions = [];
    if (canManage) {actions.push(`<button class="ghost" data-unit-restore="${item.id}">${tr('unit.restore', 'Desarquivar')}</button>`);}
    if (canPurge && rules().isPurgeable(item)) {
      actions.push(`<button class="ghost" data-unit-purge="${item.id}">${tr('unit.purge', 'Excluir definitivamente')}</button>`);
    }
    return `<tr><td>${escapeText(`${item.company_name}`)}</td><td>${escapeText(`${item.name}`)}${statusBadge}${holdBadge}</td><td>${formatDate(item.archived_at)}</td><td>${escapeText(item.archive_reason || '-')}</td><td>${escapeText(item.archived_by_name || '-')}</td><td>${retentionLabel}</td><td>${actions.length ? `<div class="action-group">${actions.join('')}</div>` : '-'}</td></tr>`;
  }

  function renderArchivedUnits() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.archivedUnitsTable) {return;}
    const canManage = rules().canManageArchivedUnits(state.user?.role);
    const canPurge = rules().canPurgeArchived(state.user?.role);
    const items = rules().filterArchivedItems(filterByUserCompany(state.archivedUnits), state.archivedUnitsFilters);
    refs.archivedUnitsTable.innerHTML = items.map((item) => formatArchivedUnitRow(item, canManage, canPurge)).join('')
      || globalThis.dsTableState({ colspan: 7, message: tr('unit.archivedEmpty', 'Nenhuma unidade arquivada.') });
  }

  function syncArchivedUnitsFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    Object.assign(state.archivedUnitsFilters, rules().normalizeArchivedFilters({
      company: refs.archivedUnitsFilterCompany?.value,
      date: refs.archivedUnitsFilterDate?.value,
      reason: refs.archivedUnitsFilterReason?.value,
      user: refs.archivedUnitsFilterUser?.value,
    }));
    renderArchivedUnits();
  }

  async function restoreArchivedUnit(unitId) {
    return runExclusiveMutation(`restore:unit:${unitId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      if (!requirePermission('units:update')) {return;}
      if (!(await confirmDestructive({ title: tr('unit.restoreTitle', 'Desarquivar Unidade'), message: tr('unit.restoreConfirm', 'A unidade será desarquivada e voltará a ficar ativa, podendo receber novas operações. Todo o histórico preservado permanece intacto. Continuar?'), confirmLabel: tr('unit.restore', 'Desarquivar'), variant: 'primary' }))) {return;}
      try {
        await archivalApi().restoreRecord('units', unitId, { actor_user_id: state.user.id });
      } catch (error) {
        alert(error.message);
        return;
      }
      await refreshUnits();
    });
  }

  // Exclusão definitiva em duas etapas: resumo do histórico + confirmação com
  // justificativa obrigatória e digitação do nome exato da unidade.
  async function purgeArchivedUnit(unitId) {
    return runExclusiveMutation(`purge:unit:${unitId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      if (!requirePermission('units:delete')) {return;}
      const unit = state.archivedUnits.find((item) => String(item.id) === String(unitId));
      if (!unit) {return;}
      try {
        const step1 = await archivalApi().requestPurge('units', unitId, { actor_user_id: state.user.id });
        const lines = rules().purgeSummaryLines(rules().UNIT_PURGE_RECORD_LABELS, step1.records || {});
        const message = `${tr('unit.purgeSummaryIntro', 'ATENÇÃO: exclusão definitiva e irreversível. Os seguintes registros históricos serão removidos:')}\n\n${lines}\n\n${tr('unit.purgeSummaryOutro', 'O registro de auditoria desta operação será preservado permanentemente.')}`;
        if (!(await confirmDestructive({ title: tr('unit.purgeTitle', 'Excluir definitivamente'), message, confirmLabel: tr('continue', 'Continuar'), variant: 'danger' }))) {
          await archivalApi().cancelPurge('units', unitId, { actor_user_id: state.user.id });
          await loadArchivedUnits();
          return;
        }
        const justification = globalThis.prompt(tr('unit.purgeJustification', 'Justificativa obrigatória da exclusão definitiva (mínimo 10 caracteres):'), '') ?? '';
        const confirmName = globalThis.prompt(`${tr('unit.purgeConfirmName', 'Digite o nome exato da unidade para confirmar:')}\n"${unit.name}"`, '') ?? '';
        if (!justification.trim() || !confirmName.trim()) {
          await archivalApi().cancelPurge('units', unitId, { actor_user_id: state.user.id });
          await loadArchivedUnits();
          return;
        }
        await archivalApi().confirmPurge('units', unitId,
          { actor_user_id: state.user.id, justification, confirm_name: confirmName });
      } catch (error) {
        alert(error.message);
        await loadArchivedUnits();
        return;
      }
      alert(tr('unit.purgeDone', 'Unidade excluída definitivamente. O registro da operação foi gravado na auditoria.'));
      await refreshUnits();
    });
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    archiveUnit,
    loadArchivedUnits,
    renderArchivedUnits,
    syncArchivedUnitsFilters,
    restoreArchivedUnit,
    purgeArchivedUnit
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_UNIT_ARCHIVAL_UI__ = Object.freeze({ ...exportsMap, formatArchivedUnitRow });
})();
