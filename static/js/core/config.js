'use strict';

(function () {
  if (globalThis.__EPI_CORE_CONFIG_LOADED__) return;
  globalThis.__EPI_CORE_CONFIG_LOADED__ = true;

  const DEFAULT_CONFIGURATION_FRAMEWORK = Object.freeze({
    version: 1,
    feature_flags: {
      enable_new_rules_engine: false,
      execution_mode: 'off',
      allow_new_engine_response: false,
      enabled_profiles: [],
      enabled_user_ids: [],
      enabled_company_ids: [],
      enabled_endpoints: [],
      enabled_environments: [],
      rollout_percentage: 0
    },
    hierarchy: {
      role_priority: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'employee'],
      who_can_view_what: {}
    },
    visibility_rules: [],
    report_scopes: {
      stock_by_unit: {
        enabled: true,
        enforce_unit_scope: true,
        enforce_visibility_rules: false,
        allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user']
      },
      delivery_by_employee: {
        enabled: true,
        enforce_unit_scope: true,
        enforce_visibility_rules: false,
        allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user']
      },
      movement: {
        enabled: true,
        enforce_unit_scope: true,
        enforce_visibility_rules: false,
        allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user']
      },
      epi_ficha: {
        enabled: true,
        enforce_unit_scope: true,
        enforce_visibility_rules: false,
        allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user']
      },
      alerts: {
        enabled: true,
        enforce_unit_scope: true,
        enforce_visibility_rules: false,
        allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user']
      }
    },
    observability: {
      audit_decisions: false,
      debug_visibility: false
    }
  });

  const DEFAULT_COMMERCIAL_SETTINGS = Object.freeze({
    unit_price: 42,
    plans: Object.freeze({
      individual: Object.freeze({ label: 'Individual', min_users: 1, max_users: 1 }),
      start: Object.freeze({ label: 'Start', min_users: 1, max_users: 10 }),
      business: Object.freeze({ label: 'Business', min_users: 11, max_users: 25 }),
      corporate: Object.freeze({ label: 'Corporate', min_users: 26, max_users: 100 }),
      enterprise: Object.freeze({ label: 'Enterprise', min_users: 101, max_users: null })
    })
  });

  globalThis.DEFAULT_CONFIGURATION_FRAMEWORK = DEFAULT_CONFIGURATION_FRAMEWORK;
  globalThis.DEFAULT_COMMERCIAL_SETTINGS = DEFAULT_COMMERCIAL_SETTINGS;
})();
