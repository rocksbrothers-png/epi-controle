'use strict';

// Configuração de estoque por Unidade + EPI no Web Legado/SaaS (#271-B3).
//
// Paridade com a tela `/stock/config` do Flutter (#271-B2-a): os TRÊS
// parâmetros, cada um com valor efetivo, origem, salvar e restaurar herança.
// Enquanto o legado estiver operacional ele segue o mesmo contrato — deixar
// faixa e alerta exclusivos do app criaria duas experiências com capacidades
// diferentes sobre a mesma regra de negócio.
//
// O que este módulo NÃO faz, e por quê:
//
//   • **não recalcula classificação.** `attention_limit`, `stock_status` e
//     `underlying_status` vêm prontos de `/api/stock/epis` e são exibidos como
//     vieram. O gate `tests/stock_rule_scan.py` varre este arquivo.
//   • **não reconstrói permissão.** Quem decide é `stock:adjust`, o mesmo piso
//     que o backend cobra. Nenhuma lista de papéis vive aqui — a antiga
//     `canManageMinimumStock()` (`['admin','user']`) escondia a tela do
//     Administrador Geral, que o servidor autoriza.
//   • **não escolhe Unidade.** A lista vem de `GET /api/units/selectable`, e o
//     estado (`locked`, `allows_all_units`, `blocks_everything`) é desenhado,
//     nunca deduzido.
(function () {
  if (globalThis.__EPI_MODULE_ESTOQUE_CONFIG_LOADED__) { return; }
  globalThis.__EPI_MODULE_ESTOQUE_CONFIG_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function tr(key, fallback) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  }

  // ── Origens do contrato (#271) ────────────────────────────────────────────
  //
  // Mesmas constantes do Dart (`unit_epi_stock_config.dart`). O mínimo e o
  // percentual herdam da EMPRESA; o alerta pula esse degrau e herda do
  // SISTEMA. São hierarquias de altura diferente e rotulá-las igual mostraria
  // uma origem que não existe.
  const SOURCE_UNIT = 'unit_configured';
  const SOURCE_COMPANY = 'company_default';
  const SOURCE_SYSTEM = 'system_default';

  function sourceLabel(source) {
    switch (String(source || '')) {
      case SOURCE_UNIT:
        return tr('stock.originUnit', 'Configurado por esta Unidade');
      case SOURCE_COMPANY:
        return tr('stock.originCompany', 'Herdado do padrão da empresa');
      case SOURCE_SYSTEM:
        return tr('stock.originSystem', 'Padrão do sistema');
      default:
        return tr('stock.originUnknown', 'Não informada');
    }
  }

  /** Há decisão local para apagar? Só então restaurar faz sentido. */
  function canRestore(source) { return String(source || '') === SOURCE_UNIT; }

  // ── Leitura dos três parâmetros a partir da linha de /api/stock/epis ──────
  //
  // A linha traz o mínimo em DOIS campos com significados diferentes:
  // `minimum_stock` é o padrão CORPORATIVO e `unit_minimum_stock` é o efetivo
  // daquela Unidade. O editor antigo lia o primeiro — e o operador editava um
  // campo que mostrava o número de outra coisa. Aqui só o segundo governa.
  function readParameters(item) {
    if (!item) { return null; }
    const hasUnit = item.unit_scope_id !== null && item.unit_scope_id !== undefined;
    if (!hasUnit) { return null; }
    return {
      unitId: Number(item.unit_scope_id),
      epiId: Number(item.id),
      minimum: {
        value: Number(item.unit_minimum_stock ?? 0),
        source: String(item.minimum_stock_source || '')
      },
      attention: {
        value: Number(item.effective_attention_percentage ?? 0),
        source: String(item.attention_percentage_source || '')
      },
      alert: {
        enabled: item.stock_alert_enabled === true,
        source: String(item.alert_source || '')
      },
      // Derivados: EXIBIDOS, nunca recalculados.
      attentionLimit: item.attention_limit ?? null,
      stockStatus: item.stock_status ?? null,
      underlyingStatus: item.underlying_status ?? null,
      unitStock: item.unit_stock_quantity ?? null
    };
  }

  // ── Escopo de Unidade ─────────────────────────────────────────────────────

  /**
   * Traduz `GET /api/units/selectable` no que a tela precisa desenhar.
   *
   * Espelha `UnitSelectorCubit` do Flutter, inclusive nos casos de borda:
   * perfil travado não escolhe; "Todas" nunca aparece em escrita; carteira
   * vazia é diferente de empresa sem Unidades.
   */
  function readSelectableUnits(payload) {
    const data = payload || {};
    const units = Array.isArray(data.units) ? data.units : [];
    return {
      units: units.map((u) => ({ id: Number(u.id), name: String(u.name || '') })),
      locked: data.locked === true,
      unitId: data.unit_id === null || data.unit_id === undefined ? null : Number(data.unit_id),
      allowsAllUnits: data.allows_all_units === true,
      blocksEverything: data.blocks_everything === true
    };
  }

  /**
   * Pré-seleção obrigatória, não conveniência.
   *
   * - perfil travado → a Unidade do ator, sempre;
   * - uma opção só → pré-seleciona, porque escolher entre uma coisa não é
   *   escolha e deixar `null` bloquearia quem não tem alternativa;
   * - várias opções → `null`, e a tela fica fail-closed até o usuário decidir.
   *
   * **"Todas" não entra em escrita**, mesmo quando o backend a autoriza: não
   * existe gravar configuração em todas as Unidades, e um Salvar com "Todas"
   * selecionado deixaria dúvida entre gravar em todas, herdar, ou escolher
   * alguma em silêncio.
   */
  function initialUnitSelection(scope) {
    if (!scope) { return null; }
    if (scope.locked) { return scope.unitId; }
    if (scope.units.length === 1) { return scope.units[0].id; }
    return null;
  }

  /** A tela pode gravar com este escopo? Só com Unidade REAL escolhida. */
  function canWrite(scope, selectedUnitId) {
    if (!scope || scope.blocksEverything) { return false; }
    if (selectedUnitId === null || selectedUnitId === undefined) { return false; }
    return scope.units.some((u) => u.id === Number(selectedUnitId));
  }

  /**
   * Uma Unidade vinda de fora (querystring, estado antigo) só vale se o
   * servidor a tiver oferecido. Mesma guarda do `select` no Flutter: aceitar
   * aqui exibiria um escopo que o backend recusaria.
   */
  function acceptUnit(scope, requestedUnitId) {
    if (!scope || scope.locked) { return scope ? scope.unitId : null; }
    const pedida = Number(requestedUnitId);
    if (!Number.isFinite(pedida)) { return null; }
    return scope.units.some((u) => u.id === pedida) ? pedida : null;
  }

  // ── Autorização ───────────────────────────────────────────────────────────

  /**
   * Quem pode configurar. **Permissão, não papel.**
   *
   * Substitui `canManageMinimumStock()`, que testava `['admin','user']` e por
   * isso escondia o editor do Administrador Geral — a quem o backend concede
   * `stock:adjust`. Reconstruir autorização por lista de papéis no cliente é
   * exatamente o antipadrão que a #271 vem removendo.
   */
  function canConfigureStock() {
    const state = getState();
    const perms = (state.user && state.user.permissions) || state.permissions || [];
    return Array.isArray(perms) && perms.includes('stock:adjust');
  }

  // ── Rótulos de status (CHAVE é o contrato, texto sai do i18n) ─────────────

  function statusLabel(key) {
    switch (String(key || '')) {
      case 'critical': return tr('stock.statusCritical', 'Crítico');
      case 'near_minimum': return tr('stock.statusNearMinimum', 'Próximo do mínimo');
      case 'normal': return tr('stock.statusNormal', 'Normal');
      case 'disabled': return tr('stock.statusDisabled', 'Alerta desabilitado');
      // Chave desconhecida de um backend mais novo não vira "normal": some.
      default: return '';
    }
  }

  // ── Validação local: só o que o backend publica ───────────────────────────

  /**
   * O backend aplica `max(0, int(...))` ao mínimo e **não publica teto**.
   * Validar negatividade evita gravar 0 quando o usuário quis outra coisa;
   * inventar um limite superior criaria uma régua que o servidor desconhece.
   */
  function validateMinimum(raw) {
    const n = Number(raw);
    if (!Number.isFinite(n) || Math.floor(n) !== n || n < 0) {
      return { ok: false, error: 'negative' };
    }
    return { ok: true, value: n };
  }

  /** 0–100 é contrato PUBLICADO (`MAX_ATTENTION_PERCENTAGE`), não invenção. */
  function validateAttention(raw) {
    const n = Number(raw);
    if (!Number.isFinite(n) || Math.floor(n) !== n || n < 0 || n > 100) {
      return { ok: false, error: 'range' };
    }
    return { ok: true, value: n };
  }

  // ── Payloads das seis rotas ───────────────────────────────────────────────
  //
  // `unit_id` viaja em todas. É TRANSPORTE, não decisão: `resolve_unit_scope`
  // descarta o valor para perfil travado e valida contra o tenant para perfil
  // livre. Mandá-lo é o que faz o Administrador Geral funcionar aqui — o
  // editor antigo não mandava, e por isso ele tomava 400.

  function minimumPayload(actorUserId, unitId, epiId, minimumStock) {
    return {
      actor_user_id: Number(actorUserId),
      unit_id: Number(unitId),
      epi_id: Number(epiId),
      minimum_stock: Number(minimumStock)
    };
  }

  function attentionPayload(actorUserId, unitId, epiId, percentage) {
    return {
      actor_user_id: Number(actorUserId),
      unit_id: Number(unitId),
      epi_id: Number(epiId),
      attention_percentage: Number(percentage)
    };
  }

  function alertPayload(actorUserId, unitId, epiId, enabled) {
    return {
      actor_user_id: Number(actorUserId),
      unit_id: Number(unitId),
      epi_id: Number(epiId),
      alert_enabled: enabled === true
    };
  }

  function restorePayload(actorUserId, unitId, epiId) {
    return {
      actor_user_id: Number(actorUserId),
      unit_id: Number(unitId),
      epi_id: Number(epiId)
    };
  }

  const ROUTES = Object.freeze({
    minimum: '/api/stock/minimum',
    minimumRestore: '/api/stock/minimum/restore-default',
    attention: '/api/stock/attention-percentage',
    attentionRestore: '/api/stock/attention-percentage/restore-default',
    alert: '/api/stock/alert-enabled',
    alertRestore: '/api/stock/alert-enabled/restore-default',
    selectableUnits: '/api/units/selectable',
    epis: '/api/stock/epis'
  });

  // ── Desfecho: salvar ≠ restaurar ──────────────────────────────────────────
  //
  // As duas ações podem terminar com o MESMO valor e significam coisas
  // opostas. Seis mensagens, nunca um "pronto" genérico — é a distinção que a
  // hierarquia inteira existe para preservar.
  function outcomeMessage(block, outcome) {
    const saved = outcome === 'saved';
    switch (block) {
      case 'minimum':
        return saved
          ? tr('stock.minimumSaved', 'Estoque mínimo salvo para esta Unidade.')
          : tr('stock.minimumRestored', 'Estoque mínimo restaurado. A Unidade voltou a herdar o padrão da empresa.');
      case 'attention':
        return saved
          ? tr('stock.attentionSaved', 'Faixa de atenção salva para esta Unidade.')
          : tr('stock.attentionRestored', 'Faixa de atenção restaurada. A Unidade voltou a herdar o padrão da empresa.');
      case 'alert':
        return saved
          ? tr('stock.alertSaved', 'Monitoramento de alerta salvo para esta Unidade.')
          : tr('stock.alertRestored', 'Monitoramento restaurado. A Unidade voltou ao padrão do sistema.');
      default:
        return '';
    }
  }

  /**
   * Desligar o alerta pede confirmação; ligar não.
   *
   * Silenciar o monitoramento de um EPI é decisão operacional relevante —
   * interrompe alerta de estoque baixo e reposição automática naquela Unidade.
   * Mesma regra do Flutter (`alertRequiresConfirmation`).
   */
  function alertNeedsConfirmation(currentEnabled, draftEnabled) {
    return currentEnabled === true && draftEnabled === false;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const configExports = {
    sourceLabel,
    canRestore,
    readParameters,
    readSelectableUnits,
    initialUnitSelection,
    canWrite,
    acceptUnit,
    canConfigureStock,
    statusLabel,
    validateMinimum,
    validateAttention,
    minimumPayload,
    attentionPayload,
    alertPayload,
    restorePayload,
    outcomeMessage,
    alertNeedsConfirmation,
    STOCK_CONFIG_ROUTES: ROUTES,
    STOCK_CONFIG_SOURCES: Object.freeze({
      unit: SOURCE_UNIT,
      company: SOURCE_COMPANY,
      system: SOURCE_SYSTEM
    })
  };

  for (const [name, fn] of Object.entries(configExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_ESTOQUE_CONFIG__ = Object.freeze({ ...configExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, configExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
