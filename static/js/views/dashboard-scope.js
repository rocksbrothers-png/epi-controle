'use strict';

// Filtro em cascata do dashboard legado: Empresa → CNPJ → Unidade → Setor.
//
// Regras puras, sem DOM e sem estado global — a manipulação de tela fica em
// dashboard.js. A semântica é a MESMA do DashboardCubit do Flutter (mesmo
// repositório, mesma decisão de produto): o que muda é só o runtime.
//
// A convenção central, e a mais fácil de errar: `scopedUnitIds` devolve `null`
// para "sem restrição" e um Set VAZIO para "nenhuma unidade casa". Tratar os
// dois como a mesma coisa faria um CNPJ sem unidades mostrar o total da
// empresa, em vez de zero.
(function () {
  if (globalThis.__EPI_MODULE_DASHBOARD_SCOPE_LOADED__) { return; }
  globalThis.__EPI_MODULE_DASHBOARD_SCOPE_LOADED__ = true;

  function toId(value) {
    if (value === null || value === undefined || value === '') { return null; }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  /**
   * Unidades exibíveis: com um CNPJ selecionado, só as dele.
   *
   * É o elo da cascata — a unidade pertence a um CNPJ (`units.legal_entity_id`).
   * Unidade sem vínculo não aparece sob nenhum CNPJ: é o caso da janela de
   * migração, e mostrá-la em todos seria pior do que não mostrar.
   */
  function availableUnits(units, legalEntityId) {
    const list = Array.isArray(units) ? units : [];
    const wanted = toId(legalEntityId);
    if (wanted === null) { return list; }
    return list.filter((unit) => toId(unit?.legal_entity_id) === wanted);
  }

  /**
   * Ids das unidades no escopo atual.
   *
   * `null` = sem restrição; Set vazio = nada casa (zera os indicadores).
   */
  function scopedUnitIds(units, legalEntityId, unitId) {
    const unit = toId(unitId);
    if (unit !== null) { return new Set([unit]); }
    const entity = toId(legalEntityId);
    if (entity === null) { return null; }
    return new Set(
      availableUnits(units, entity)
        .map((item) => toId(item?.id))
        .filter((id) => id !== null)
    );
  }

  /** Um registro está no escopo? Registro sem unidade fica de fora quando há recorte. */
  function inScope(scopedUnits, rawUnitId) {
    if (scopedUnits === null) { return true; }
    const unit = toId(rawUnitId);
    return unit !== null && scopedUnits.has(unit);
  }

  /**
   * Aplica o recorte a uma lista de registros que carregam `unit_id`.
   *
   * `sectorKey` existe porque o setor mora em campos diferentes conforme a
   * entidade (colaborador tem `sector`, entrega também) — quem chama diz onde.
   */
  function applyScope(items, scopedUnits, sector, sectorKey) {
    const list = Array.isArray(items) ? items : [];
    const wantedSector = String(sector ?? '').trim();
    const key = sectorKey || 'sector';
    return list.filter((item) => {
      if (!inScope(scopedUnits, item?.unit_id)) { return false; }
      if (!wantedSector) { return true; }
      return String(item?.[key] ?? '').trim() === wantedSector;
    });
  }

  /**
   * Recorte para itens de nível empresa.
   *
   * EPI sem `unit_id` pertence à empresa, não a uma unidade: ele permanece
   * visível em qualquer recorte. Filtrá-lo junto esconderia catálogo inteiro
   * ao escolher um CNPJ.
   */
  function applyScopeKeepingCompanyWide(items, scopedUnits) {
    const list = Array.isArray(items) ? items : [];
    return list.filter((item) => {
      const unit = toId(item?.unit_id);
      if (unit === null) { return true; }
      return inScope(scopedUnits, unit);
    });
  }

  /** Setores distintos dos colaboradores no escopo, ordenados. */
  function sectorsOf(employees, scopedUnits) {
    const out = new Set();
    (Array.isArray(employees) ? employees : []).forEach((item) => {
      if (!inScope(scopedUnits, item?.unit_id)) { return; }
      const sector = String(item?.sector ?? '').trim();
      if (sector) { out.add(sector); }
    });
    return Array.from(out).sort();
  }

  function hasActiveFilter(selection) {
    return Boolean(
      toId(selection?.legalEntityId) !== null
      || toId(selection?.unitId) !== null
      || String(selection?.sector ?? '').trim()
    );
  }

  globalThis.__EPI_DASHBOARD_SCOPE__ = Object.freeze({
    availableUnits,
    scopedUnitIds,
    inScope,
    applyScope,
    applyScopeKeepingCompanyWide,
    sectorsOf,
    hasActiveFilter,
  });
})();
