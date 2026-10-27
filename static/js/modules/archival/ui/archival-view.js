'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, confirmDestructive, showToast, formatDate,
   filterByUserCompany, loadBootstrap, loadOutsourcedCompanies, runExclusiveMutation, refreshAfterMutation,
   coalesceLoad --
   globais do app.js, de shared/ui, de views/* e do módulo de Terceirizados, resolvidos na chamada;
   reportNonCriticalError é global do runtime */

// UI: Arquivamento genérico — Colaboradores, EPIs, Empresas terceirizadas e
// Colaboradores terceirizados (Refatoração UBX-V5, Etapa 1 — extraído de static/app.js).
//
// Arquivar (com o pré-voo do EPI), desarquivar, excluir definitivamente em
// duas etapas, carga/filtros/tabela das listas de arquivados. Configuração e
// regras puras em ../business/archival-rules.js; HTTP em
// ../integrations/archival-api.js. Fluxo gravar → atualizar a tela (clique
// único, recarga sem duplicata, aviso verdadeiro) em shared/ui/mutation-flow.js.
// Eram `async function` de bloco no app.js; agora são globais (o app.js as
// chama em showView, limparFiltrosArquivados e nos listeners do init).
(function () {
  if (globalThis.__EPI_MODULE_ARCHIVAL_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_ARCHIVAL_UI_LOADED__ = true;

  function rules() { return globalThis.__EPI_ARCHIVAL_RULES__; }
  function archivalApi() { return globalThis.__EPI_ARCHIVAL_API__; }

  // Células comuns às linhas de arquivados (genérico e Unidades): retenção,
  // selos de "em exclusão" e "bloqueio jurídico".
  function archivedRowParts(item) {
    const retentionOver = rules().isRetentionOver(item);
    const retentionLabel = retentionOver
      ? tr('unit.retentionExpired', 'Retenção cumprida')
      : `${item.retention_days_remaining} ${tr('unit.retentionDays', 'dia(s)')}`;
    const statusBadge = item.status === 'pending_deletion' ? ` <span class="badge">${tr('unit.pendingDeletion', 'Em processo de exclusão')}</span>` : '';
    const holdBadge = rules().hasLegalHold(item) ? ` <span class="badge">${tr('unit.legalHold', 'Bloqueio jurídico')}</span>` : '';
    return { retentionOver, retentionLabel, statusBadge, holdBadge };
  }

  // Item 1: EPI com saldo/vínculos vivos exige decisão autorizada. Consome
  // EXCLUSIVAMENTE a regra do backend (#735): GET archival-state para decidir e
  // POST /archive com block_and_archive. Nenhuma regra é duplicada no frontend.
  async function _epiArchivalPreflight(recordId) {
    try {
      const resp = await archivalApi().getEpiArchivalState(recordId, actorQuery());
      return resp.archival_state || null;
    } catch (error) {
      reportNonCriticalError('[epi] falha ao consultar estado de arquivamento', error);
      return null;
    }
  }

  function epiOpenLinksMessage(cfg, recordName, st) {
    return `${cfg.labelFallback}: "${recordName}"\n\n`
      + `${tr('epi.archiveHasStock', 'Este EPI possui saldo ou vínculos vivos:')}\n`
      + `• ${tr('epi.stockAvailable', 'Disponível')}: ${st.available}\n`
      + `• ${tr('epi.stockInTransit', 'Reservado/em trânsito')}: ${st.in_transit}\n`
      + `• ${tr('epi.stockInPossession', 'Em posse (colaborador)')}: ${st.in_possession}\n`
      + `• ${tr('epi.stockBlocked', 'Bloqueado')}: ${st.blocked}\n`
      + `• ${tr('epi.pendingRequests', 'Solicitações abertas')}: ${st.pending_requests}\n`
      + `• ${tr('epi.pendingPurchase', 'Pedidos abertos')}: ${st.pending_purchase}\n\n`
      + (st.blockable > 0
        ? tr('epi.archiveBlockExplain', 'Ao continuar, o saldo disponível será BLOQUEADO (movido para Estoque Bloqueado — rastreável, nada some) e o EPI será arquivado.')
        : tr('epi.archiveNoBlockable', 'Não há saldo físico livre para bloquear; itens em posse/pedidos permanecem em seus fluxos. O EPI será arquivado.'));
  }

  // Atualização da tela depois de uma gravação concluída (FIX-NAV-REFRESH-V1).
  function refreshArchivedKind(kind, cfg, { withOutsourcedCompanies }) {
    return refreshAfterMutation(async () => {
      await loadBootstrap({ preserveView: cfg.preserveView === true });
      if (withOutsourcedCompanies && kind === 'outsourcedCompany') { await loadOutsourcedCompanies(); }
      await loadArchivedRecords(kind);
    });
  }

  async function archiveEntityRecord(kind, recordId) {
    return runExclusiveMutation(`archive:${kind}:${recordId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      const cfg = rules().archivalConfig(kind);
      if (!cfg || !requirePermission(cfg.deletePermission)) {return;}
      const record = (state[cfg.stateList] || []).find((item) => String(item.id) === String(recordId));
      const recordName = record ? record.name : `#${recordId}`;

      let blockAndArchive = false;
      if (kind === 'epi') {
        const st = await _epiArchivalPreflight(recordId);
        if (st && st.has_open_links) {
          if (!(await confirmDestructive({
            title: tr('epi.blockAndArchive', 'Bloquear saldo e arquivar'),
            message: epiOpenLinksMessage(cfg, recordName, st),
            confirmLabel: tr('epi.blockAndArchive', 'Bloquear saldo e arquivar'),
            variant: 'danger',
          }))) {return;}
          blockAndArchive = true;
        }
      }

      if (!blockAndArchive) {
        const message = `${cfg.labelFallback}: "${recordName}"\n\n${tr(`${cfg.i18nPrefix}.archiveConfirm`, 'Este registro será arquivado e deixará de receber novas operações. Todo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos). Nenhum dado será excluído.')}`;
        if (!(await confirmDestructive({ title: tr(`${cfg.i18nPrefix}.archiveTitle`, `Arquivar ${cfg.labelFallback}`), message, confirmLabel: tr(`${cfg.i18nPrefix}.archive`, 'Arquivar'), variant: 'danger' }))) {return;}
      }

      const reason = globalThis.prompt(tr('unit.archiveReasonPrompt', 'Motivo do arquivamento (registrado na auditoria):'), '') ?? '';
      if (blockAndArchive && !String(reason).trim()) {
        showToast(tr('epi.archiveReasonRequired', 'Motivo é obrigatório para bloquear o saldo e arquivar.'), 'error');
        return;
      }
      let result;
      try {
        result = await archivalApi().archiveRecord(cfg.resource, recordId,
          { actor_user_id: state.user.id, reason, block_and_archive: blockAndArchive });
      } catch (error) {
        showToast(error.message || tr('epi.archiveFailed', 'Não foi possível arquivar.'), 'error');
        return;
      }
      if (blockAndArchive && Number(result?.blocked_stock_items) > 0) {
        showToast(`${result.blocked_stock_items} ${tr('epi.itemsBlockedArchived', 'item(ns) de estoque bloqueado(s) e EPI arquivado.')}`, 'success');
      } else {
        showToast(tr('epi.archivedOk', 'Registro arquivado.'), 'success');
      }
      await refreshArchivedKind(kind, cfg, { withOutsourcedCompanies: true });
      // Atualiza imediatamente as telas de estoque (itens recém-bloqueados aparecem em Estoque Bloqueado)
      if (kind === 'epi') { globalThis.loadBlockedStock?.(); }
    });
  }

  async function loadArchivedRecords(kind) {
    const cfg = rules().archivalConfig(kind);
    if (!cfg || !hasPermission(rules().archivedViewPermission(cfg))) {return;}
    return coalesceLoad(`archived:${kind}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      try {
        const data = await archivalApi().listArchived(cfg.resource, `${actorQuery()}${cfg.archivedQueryExtra || ''}`);
        state[cfg.archivedList] = data[cfg.responseKey] || [];
      } catch (error) {
        state[cfg.archivedList] = [];
        reportNonCriticalError(`[${kind}] falha ao carregar arquivados`, error);
      }
      renderArchivedRecords(kind);
    });
  }

  function formatArchivedRecordRow(kind, item, canManage, canPurge) {
    const cfg = rules().archivalConfig(kind);
    const { retentionOver, retentionLabel, statusBadge, holdBadge } = archivedRowParts(item);
    const actions = [];
    if (canManage) {actions.push(`<button class="ghost" data-archived-restore="${kind}:${item.id}">${tr('unit.restore', 'Desarquivar')}</button>`);}
    if (canPurge && cfg.supportsPurge !== false && retentionOver && !rules().hasLegalHold(item)) {
      actions.push(`<button class="ghost" data-archived-purge="${kind}:${item.id}">${tr('unit.purge', 'Excluir definitivamente')}</button>`);
    }
    const actionsCell = actions.length ? `<div class="action-group">${actions.join('')}</div>` : '-';
    const identityKind = cfg.identityKind || kind;
    const identity = identityKind === 'employee'
      ? `<td>${item.employee_id_code || '-'} · ${item.name}${statusBadge}${holdBadge}</td><td>${item.unit_name || '-'}</td>`
      : identityKind === 'outsourcedCompanyLike'
        ? `<td>${item.legal_name || item.trade_name || ''}${statusBadge}${holdBadge}</td><td>${item.cnpj || '-'}</td>`
        : `<td>${item.name}${statusBadge}${holdBadge}</td><td>${item.ca || '-'}</td>`;
    return `<tr><td>${item.company_name || '-'}</td>${identity}<td>${formatDate(item.archived_at)}</td><td>${item.archive_reason || '-'}</td><td>${item.archived_by_name || '-'}</td><td>${retentionLabel}</td><td>${actionsCell}</td></tr>`;
  }

  function renderArchivedRecords(kind) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const cfg = rules().archivalConfig(kind);
    const table = refs[cfg.tableRef];
    if (!table) {return;}
    // O backend (ensure_actor_outsourced_company_scope / _load_employee_for_lifecycle /
    // _require_deletion_admin) é quem decide; isto só evita mostrar um botão que
    // ele vai recusar.
    const canManage = rules().canManageArchived(kind, state.user?.role);
    const canPurge = rules().canPurgeArchived(state.user?.role);
    const items = rules().filterArchivedItems(filterByUserCompany(state[cfg.archivedList] || []), state[cfg.filters]);
    table.innerHTML = items.map((item) => formatArchivedRecordRow(kind, item, canManage, canPurge)).join('')
      || `<tr><td colspan="8">${tr(`${cfg.i18nPrefix}.archivedEmpty`, 'Nenhum registro arquivado.')}</td></tr>`;
  }

  function syncArchivedRecordsFilters(kind) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const cfg = rules().archivalConfig(kind);
    const prefix = cfg.tableRef.replace('Table', '');
    Object.assign(state[cfg.filters], rules().normalizeArchivedFilters({
      company: refs[`${prefix}FilterCompany`]?.value,
      date: refs[`${prefix}FilterDate`]?.value,
      reason: refs[`${prefix}FilterReason`]?.value,
      user: refs[`${prefix}FilterUser`]?.value,
    }));
    renderArchivedRecords(kind);
  }

  async function restoreArchivedRecord(kind, recordId) {
    return runExclusiveMutation(`restore:${kind}:${recordId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      const cfg = rules().archivalConfig(kind);
      if (!cfg || !requirePermission(cfg.updatePermission)) {return;}
      if (!(await confirmDestructive({ title: tr('unit.restoreTitle', 'Desarquivar'), message: tr(`${cfg.i18nPrefix}.restoreConfirm`, 'O registro será desarquivado e voltará a ficar ativo, podendo receber novas operações. Todo o histórico preservado permanece intacto. Continuar?'), confirmLabel: tr('unit.restore', 'Desarquivar'), variant: 'primary' }))) {return;}
      try {
        await archivalApi().restoreRecord(cfg.resource, recordId, { actor_user_id: state.user.id });
      } catch (error) {
        alert(error.message);
        return;
      }
      await refreshArchivedKind(kind, cfg, { withOutsourcedCompanies: true });
    });
  }

  // Exclusão definitiva em duas etapas (habilitada só após a retenção mínima):
  // resumo do histórico + justificativa obrigatória e o nome exato do registro.
  async function purgeArchivedRecord(kind, recordId) {
    return runExclusiveMutation(`purge:${kind}:${recordId}`, async () => {
      const state = globalThis.__EPI_APP_STATE__;
      const cfg = rules().archivalConfig(kind);
      if (!cfg || cfg.supportsPurge === false || !requirePermission(cfg.deletePermission)) {return;}
      const record = (state[cfg.archivedList] || []).find((item) => String(item.id) === String(recordId));
      if (!record) {return;}
      try {
        const step1 = await archivalApi().requestPurge(cfg.resource, recordId, { actor_user_id: state.user.id });
        const lines = rules().purgeSummaryLines(cfg.purgeLabels, step1.records || {});
        const message = `${tr('unit.purgeSummaryIntro', 'ATENÇÃO: exclusão definitiva e irreversível. Os seguintes registros históricos serão removidos:')}\n\n${lines}\n\n${tr('unit.purgeSummaryOutro', 'O registro de auditoria desta operação será preservado permanentemente.')}`;
        if (!(await confirmDestructive({ title: tr('unit.purgeTitle', 'Excluir definitivamente'), message, confirmLabel: tr('continue', 'Continuar'), variant: 'danger' }))) {
          await archivalApi().cancelPurge(cfg.resource, recordId, { actor_user_id: state.user.id });
          await loadArchivedRecords(kind);
          return;
        }
        const justification = globalThis.prompt(tr('unit.purgeJustification', 'Justificativa obrigatória da exclusão definitiva (mínimo 10 caracteres):'), '') ?? '';
        const confirmName = globalThis.prompt(`${tr('unit.purgeConfirmName', 'Digite o nome exato para confirmar:')}\n"${rules().purgeDisplayName(record)}"`, '') ?? '';
        if (!justification.trim() || !confirmName.trim()) {
          await archivalApi().cancelPurge(cfg.resource, recordId, { actor_user_id: state.user.id });
          await loadArchivedRecords(kind);
          return;
        }
        await archivalApi().confirmPurge(cfg.resource, recordId,
          { actor_user_id: state.user.id, justification, confirm_name: confirmName });
      } catch (error) {
        alert(error.message);
        await loadArchivedRecords(kind);
        return;
      }
      alert(tr('unit.purgeDone', 'Registro excluído definitivamente. A operação foi gravada na auditoria.'));
      await refreshArchivedKind(kind, cfg, { withOutsourcedCompanies: false });
    });
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    archiveEntityRecord,
    loadArchivedRecords,
    renderArchivedRecords,
    syncArchivedRecordsFilters,
    restoreArchivedRecord,
    purgeArchivedRecord
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_ARCHIVAL_UI__ = Object.freeze({ ...exportsMap, archivedRowParts, formatArchivedRecordRow });
})();
