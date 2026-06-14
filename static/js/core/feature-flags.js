'use strict';

(function () {
  if (globalThis.__EPI_CORE_FEATURE_FLAGS_LOADED__) {return;}
  globalThis.__EPI_CORE_FEATURE_FLAGS_LOADED__ = true;

  const UX_FRONTEND_FLAGS = Object.freeze({
    collaboratorHtmxEnabled: 'colaborador_htmx_enabled',
    collaboratorHtmxEnabledLegacy: 'ux_phase2_nav_interactivity_v1',
    collaboratorListHtmxEnabled: 'colaborador_list_htmx_enabled',
    gestaoColaboradorHtmxEnabled: 'gestao_colaborador_htmx_enabled',
    phase2NavInteractivity: 'ux_phase2_nav_interactivity_v1',
    epiHtmxEnabled: 'epi_htmx_enabled',
    estoqueHtmxEnabled: 'estoque_htmx_enabled',
    entregaEpiHtmxEnabled: 'entrega_epi_htmx_enabled',
    dashboardInterativoEnabled: 'dashboard_interativo_enabled',
    spaNavigationEnabled: 'spa_navigation_enabled',
    uxGlobalEnabled: 'ux_global_enabled',
    uxPerformanceHardeningEnabled: 'ux_performance_hardening_enabled',
    uxInteractiveAppEnabled: 'ux_interactive_app_enabled',
    uxToolsFunctionalEnabled: 'ux_tools_functional_enabled',
    uxPhase41Enabled: 'ux_phase41_enabled',
    uxPhase42Enabled: 'ux_phase42_enabled',
    uxPhase43Enabled: 'ux_phase43_enabled',
    uxPhase44Enabled: 'ux_phase44_enabled',
    uxHierarchicalNavigationEnabled: 'ux_hierarchical_navigation_enabled',
    uxMultitabNavigationEnabled: 'ux_multitab_navigation_enabled',
    uxAnalyticsEnabled: 'ux_analytics_enabled',
    uxMobileEnabled: 'ux_mobile_enabled',
    uxNavigationControlsEnabled: 'ux_navigation_controls_enabled',
    htmxAlpineProductionEnabled: 'htmx_alpine_production_enabled',
    uxGlobalKillSwitch: 'ux_global_kill_switch'
  });

  const UX_FORCE_CLASSIC_FLAGS = Object.freeze(new Set([
    'ux_phase41_enabled',
    'ux_phase42_enabled',
    'ux_phase43_enabled',
    'ux_phase44_enabled',
    'ux_hierarchical_navigation_enabled',
    'ux_multitab_navigation_enabled',
    'spa_navigation_enabled',
    'ux_global_enabled',
    'dashboard_interativo_enabled',
    'entrega_epi_htmx_enabled'
  ]));

  const FEATURE_FLAG_DEFINITIONS = Object.freeze({
    colaborador_htmx_enabled: {
      queryParam: 'ux_phase2_colaboradores',
      storageKeys: ['colaborador_htmx_enabled', 'ux_phase2_nav_interactivity_v1']
    },
    colaborador_list_htmx_enabled: {
      queryParam: 'ux_phase2_colab_list',
      storageKeys: ['colaborador_list_htmx_enabled']
    },
    gestao_colaborador_htmx_enabled: {
      queryParam: 'ux_phase2_gestao_colab',
      storageKeys: ['gestao_colaborador_htmx_enabled']
    },
    epi_htmx_enabled: {
      queryParam: 'ux_phase2_epis',
      storageKeys: ['epi_htmx_enabled']
    },
    estoque_htmx_enabled: {
      queryParam: 'ux_phase2_estoque',
      storageKeys: ['estoque_htmx_enabled']
    },
    entrega_epi_htmx_enabled: {
      queryParam: 'ux_entrega_epi',
      storageKeys: ['entrega_epi_htmx_enabled']
    },
    dashboard_interativo_enabled: {
      queryParam: 'ux_dashboard_interativo',
      storageKeys: ['dashboard_interativo_enabled']
    },
    spa_navigation_enabled: {
      queryParam: 'ux_spa_navigation',
      storageKeys: ['spa_navigation_enabled']
    },
    ux_global_enabled: {
      queryParam: 'ux_global',
      storageKeys: ['ux_global_enabled']
    },
    ux_performance_hardening_enabled: {
      queryParam: 'ux_perf_hardening',
      storageKeys: ['ux_performance_hardening_enabled']
    },
    ux_interactive_app_enabled: {
      queryParam: 'ux_interactive_app',
      storageKeys: ['ux_interactive_app_enabled']
    },
    ux_tools_functional_enabled: {
      queryParam: 'ux_tools_functional',
      storageKeys: ['ux_tools_functional_enabled']
    },
    ux_phase41_enabled: {
      queryParam: 'ux_phase41',
      storageKeys: ['ux_phase41_enabled']
    },
    ux_phase42_enabled: {
      queryParam: 'ux_phase42',
      storageKeys: ['ux_phase42_enabled']
    },
    ux_phase43_enabled: {
      queryParam: 'ux_phase43',
      storageKeys: ['ux_phase43_enabled']
    },
    ux_phase44_enabled: {
      queryParam: 'ux_phase44',
      storageKeys: ['ux_phase44_enabled']
    },
    ux_hierarchical_navigation_enabled: {
      queryParam: 'ux_hierarchy',
      storageKeys: ['ux_hierarchical_navigation_enabled']
    },
    ux_multitab_navigation_enabled: {
      queryParam: 'ux_multitab',
      storageKeys: ['ux_multitab_navigation_enabled']
    },
    ux_analytics_enabled: {
      queryParam: 'ux_analytics',
      storageKeys: ['ux_analytics_enabled']
    },
    ux_mobile_enabled: {
      queryParam: 'ux_mobile',
      storageKeys: ['ux_mobile_enabled']
    },
    ux_navigation_controls_enabled: {
      queryParam: 'ux_nav_controls',
      storageKeys: ['ux_navigation_controls_enabled']
    },
    htmx_alpine_production_enabled: {
      queryParam: 'ux_htmx_prod',
      storageKeys: ['htmx_alpine_production_enabled']
    },
    ux_global_kill_switch: {
      queryParam: 'ux_kill_switch',
      storageKeys: ['ux_global_kill_switch']
    }
  });

  const PHASE2_STORAGE_ROLLOUT_KEY = 'epi_phase2_rollout_storage_enabled';

  const PHASE2_FLAG_MATRIX = Object.freeze([
    { flag: 'colaborador_htmx_enabled', queryParam: 'ux_phase2_colaboradores', moduleName: 'Cadastro de Colaborador', defaultValue: false, status: 'pilot_stable' },
    { flag: 'colaborador_list_htmx_enabled', queryParam: 'ux_phase2_colab_list', moduleName: 'Listagem de Colaboradores', defaultValue: false, status: 'pilot_stable' },
    { flag: 'gestao_colaborador_htmx_enabled', queryParam: 'ux_phase2_gestao_colab', moduleName: 'Gestão de Colaborador', defaultValue: false, status: 'pilot_stable' },
    { flag: 'epi_htmx_enabled', queryParam: 'ux_phase2_epis', moduleName: 'Cadastro de EPI', defaultValue: false, status: 'pilot_stable' },
    { flag: 'estoque_htmx_enabled', queryParam: 'ux_phase2_estoque', moduleName: 'Controle de Estoque (read-only + filtros)', defaultValue: false, status: 'pilot_controlled' }
  ]);

  const PHASE3_FLAG_MATRIX = Object.freeze([
    {
      flag: 'spa_navigation_enabled',
      queryParam: 'ux_spa_navigation',
      moduleName: 'Navegação SPA-like',
      defaultValue: false,
      risk: 'Médio: risco de regressão de navegação/back-forward.',
      rollback: 'Desativar flag + limpar storage da sessão controlada.'
    },
    {
      flag: 'ux_global_enabled',
      queryParam: 'ux_global',
      moduleName: 'UX global unificada',
      defaultValue: false,
      risk: 'Baixo/Médio: risco visual em telas com maior densidade de cards/tabelas.',
      rollback: 'Desativar flag para retorno imediato ao layout clássico.'
    },
    {
      flag: 'dashboard_interativo_enabled',
      queryParam: 'ux_dashboard_interativo',
      moduleName: 'Dashboard interativo',
      defaultValue: false,
      risk: 'Médio: risco de fallback parcial em estados de carga/erro.',
      rollback: 'Desativar flag e manter dashboard clássico ativo.'
    },
    {
      flag: 'ux_performance_hardening_enabled',
      queryParam: 'ux_perf_hardening',
      moduleName: 'Hardening de listeners/eventos',
      defaultValue: false,
      risk: 'Baixo: impacto controlado no binding de eventos.',
      rollback: 'Desativar flag e restaurar comportamento padrão de listeners.'
    },
    {
      flag: 'ux_interactive_app_enabled',
      queryParam: 'ux_interactive_app',
      moduleName: 'Comportamento interativo avançado',
      defaultValue: false,
      risk: 'Baixo/Médio: eventos globais de teclado/dropdown e histórico de navegação.',
      rollback: 'Desativar flag para voltar ao comportamento padrão imediatamente.'
    },
    {
      flag: 'ux_tools_functional_enabled',
      queryParam: 'ux_tools_functional',
      moduleName: 'Ferramentas UX funcionais',
      defaultValue: false,
      risk: 'Médio: refresh/filtros com feedback real em módulos de operação.',
      rollback: 'Desativar flag para restaurar somente o fluxo clássico.'
    }
  ]);

  globalThis.UX_FRONTEND_FLAGS = UX_FRONTEND_FLAGS;
  globalThis.UX_FORCE_CLASSIC_FLAGS = UX_FORCE_CLASSIC_FLAGS;
  globalThis.FEATURE_FLAG_DEFINITIONS = FEATURE_FLAG_DEFINITIONS;
  globalThis.PHASE2_STORAGE_ROLLOUT_KEY = PHASE2_STORAGE_ROLLOUT_KEY;
  globalThis.PHASE2_FLAG_MATRIX = PHASE2_FLAG_MATRIX;
  globalThis.PHASE3_FLAG_MATRIX = PHASE3_FLAG_MATRIX;
})();
