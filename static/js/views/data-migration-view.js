'use strict';

// Centro de Migração de Dados do web legado (ADR-0003, fase 2) — regras puras.
//
// Segue o padrão de js/views/outsourced-employees-view.js: aqui ficam só
// funções sem DOM e sem estado global (testadas em js/test/run-tests.js);
// app.js lê o estado e escreve no documento.
//
// O backend continua sendo a autoridade: estas funções decidem o que
// *mostrar*, nunca o que é permitido. Toda importação passa de novo pelo
// catálogo declarativo e por ensure_module_enabled_for_unit no servidor.
(function () {
  if (globalThis.__EPI_MODULE_DATA_MIGRATION_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_DATA_MIGRATION_VIEW_LOADED__ = true;

  // Etapas do assistente, na ordem do pedido: escolher o que importar →
  // escolher a origem → conferir a leitura → revisar o mapeamento.
  var WIZARD_STEPS = ['entidade', 'origem', 'leitura', 'mapeamento'];

  // Estratégias que o usuário escolhe antes de confirmar. `dry_run` não é
  // oferecida como opção: ela é o preview, disparado automaticamente.
  var APPLY_STRATEGIES = [
    'insert_only',
    'update_only',
    'upsert',
    'skip_duplicates',
    'overwrite',
  ];

  /**
   * Rótulo da confiança do mapeamento automático. O número cru (0.82) não
   * diz nada ao usuário; o que ele precisa saber é se pode confiar ou se
   * vale conferir à mão.
   */
  function confidenceLevel(confidence) {
    const value = Number(confidence);
    if (!Number.isFinite(value) || value <= 0) return 'none';
    if (value >= 0.999) return 'exact';
    if (value >= 0.9) return 'high';
    if (value >= 0.82) return 'medium';
    return 'low';
  }

  /**
   * Uma coluna precisa de decisão humana quando o motor não escolheu
   * destino, ou escolheu por semelhança e não por igualdade. `duplicate_target`
   * é o caso em que o melhor destino já estava tomado (ADR-0003 §2.3): o
   * motor deliberadamente não degrada para o segundo melhor.
   */
  function needsReview(detail) {
    if (!detail || !detail.target_field) return true;
    const strategy = String(detail.strategy || '');
    return strategy === 'duplicate_target' || strategy === 'fuzzy' || strategy === 'contains';
  }

  /**
   * Resumo do mapeamento para o cabeçalho da etapa 4.
   */
  function mappingSummary(details, missingRequired) {
    const list = Array.isArray(details) ? details : [];
    let mapped = 0;
    let review = 0;
    list.forEach((detail) => {
      if (detail && detail.target_field) mapped += 1;
      if (needsReview(detail)) review += 1;
    });
    const missing = Array.isArray(missingRequired) ? missingRequired : [];
    return {
      total: list.length,
      mapped,
      unmapped: list.length - mapped,
      review,
      missingRequired: missing.slice(),
      ready: missing.length === 0,
    };
  }

  /**
   * Destinos ainda livres para o seletor manual de uma coluna. Um campo já
   * usado por outra coluna não pode ser reoferecido — é exatamente o que o
   * backend recusa em normalize_manual_mapping.
   */
  function availableTargets(fields, mapping, sourceColumn) {
    const all = Array.isArray(fields) ? fields : [];
    const current = mapping && typeof mapping === 'object' ? mapping : {};
    const taken = new Set();
    Object.keys(current).forEach((column) => {
      if (column === sourceColumn) return;
      const target = current[column];
      if (target) taken.add(String(target));
    });
    return all.filter((field) => !taken.has(String(field && field.name ? field.name : field)));
  }

  /**
   * Campos obrigatórios que ainda não têm coluna de origem. É o que trava o
   * botão de importar.
   */
  function missingRequiredFields(fields, mapping) {
    const all = Array.isArray(fields) ? fields : [];
    const current = mapping && typeof mapping === 'object' ? mapping : {};
    const assigned = new Set(Object.keys(current).map((column) => String(current[column] || '')));
    return all
      .filter((field) => field && field.required && !assigned.has(String(field.name)))
      .map((field) => field.name);
  }

  /**
   * O assistente só libera a etapa seguinte quando a atual está resolvida.
   */
  function canAdvance(step, draft) {
    const data = draft && typeof draft === 'object' ? draft : {};
    switch (step) {
      case 'entidade':
        return Boolean(data.entity);
      case 'origem':
        return Boolean(data.sourceKind) && Boolean(data.fileName);
      case 'leitura':
        return Number(data.totalRows) > 0;
      case 'mapeamento':
        return missingRequiredFields(data.fields, data.mapping).length === 0;
      default:
        return false;
    }
  }

  function nextStep(step) {
    const index = WIZARD_STEPS.indexOf(step);
    if (index < 0 || index >= WIZARD_STEPS.length - 1) return step;
    return WIZARD_STEPS[index + 1];
  }

  function previousStep(step) {
    const index = WIZARD_STEPS.indexOf(step);
    if (index <= 0) return WIZARD_STEPS[0];
    return WIZARD_STEPS[index - 1];
  }

  /**
   * Cards do painel. Entidades de roadmap continuam visíveis — o pedido pede
   * os 20 cards — mas marcadas, porque `require_enabled_entity()` as recusa
   * no servidor antes do writer.
   */
  function dashboardCards(entities) {
    return (Array.isArray(entities) ? entities : []).map((entity) => ({
      key: entity && entity.key ? entity.key : '',
      label: entity && entity.label ? entity.label : '',
      enabled: Boolean(entity && entity.enabled),
      phase: entity && entity.phase ? entity.phase : 0,
      fieldCount: Array.isArray(entity && entity.fields) ? entity.fields.length : 0,
    }));
  }

  /**
   * Só uma importação concluída e ainda não revertida pode ser desfeita —
   * mesma condição que revert_job aplica no backend.
   */
  function canRevert(job) {
    if (!job) return false;
    return String(job.status || '') === 'completed' && !job.reverted_at;
  }

  /**
   * Contadores de um job em texto curto para a tabela de histórico.
   */
  function jobCounters(job) {
    const source = job && typeof job === 'object' ? job : {};
    return {
      total: Number(source.total_rows || 0),
      inserted: Number(source.inserted_rows || 0),
      updated: Number(source.updated_rows || 0),
      skipped: Number(source.skipped_rows || 0),
      failed: Number(source.failed_rows || 0),
    };
  }

  /**
   * Diagnósticos do preview agrupados por tipo, para o usuário ver "12 CPFs
   * inválidos" em vez de 12 linhas soltas.
   */
  function groupDiagnostics(diagnostics) {
    const grouped = new Map();
    (Array.isArray(diagnostics) ? diagnostics : []).forEach((item) => {
      const kind = String((item && item.kind) || 'outro');
      if (!grouped.has(kind)) grouped.set(kind, { kind, count: 0, rows: [] });
      const bucket = grouped.get(kind);
      bucket.count += 1;
      if (bucket.rows.length < 20 && item && item.row_number) bucket.rows.push(item.row_number);
    });
    return Array.from(grouped.values()).sort((a, b) => b.count - a.count);
  }

  globalThis.__EPI_DATA_MIGRATION_VIEW__ = Object.freeze({
    WIZARD_STEPS: Object.freeze(WIZARD_STEPS.slice()),
    APPLY_STRATEGIES: Object.freeze(APPLY_STRATEGIES.slice()),
    confidenceLevel,
    needsReview,
    mappingSummary,
    availableTargets,
    missingRequiredFields,
    canAdvance,
    nextStep,
    previousStep,
    dashboardCards,
    canRevert,
    jobCounters,
    groupDiagnostics,
  });
})();
