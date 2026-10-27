'use strict';

(function () {
  if (globalThis.__EPI_CORE_CONSTANTS_LOADED__) {return;}
  globalThis.__EPI_CORE_CONSTANTS_LOADED__ = true;

  const STORAGE_KEYS = Object.freeze({
    session: 'epi-session-v4',
    permissions: 'epi-session-v4-permissions',
    token: 'epi-session-v4-token',
    changeRequired: 'epi-session-v4-password-change-required'
  });

  const ROLE_LABELS = Object.freeze({
    get ['master_admin']() { return (globalThis.trEpi?.('role.master_admin','Administrador Master',{}) ?? 'Administrador Master'); },
    get ['general_admin']() { return (globalThis.trEpi?.('role.general_admin','Administrador Geral',{}) ?? 'Administrador Geral'); },
    get ['registry_admin']() { return (globalThis.trEpi?.('role.registry_admin','Administrador de Registro',{}) ?? 'Administrador de Registro'); },
    get ['admin']() { return (globalThis.trEpi?.('role.admin','Administrador Local',{}) ?? 'Administrador Local'); },
    get ['user']() { return (globalThis.trEpi?.('role.user','Gestor de EPI',{}) ?? 'Gestor de EPI'); },
    get ['buyer']() { return (globalThis.trEpi?.('role.buyer','Comprador',{}) ?? 'Comprador'); },
    get ['approver']() { return (globalThis.trEpi?.('role.approver','Aprovador',{}) ?? 'Aprovador'); },
    get ['employee']() { return (globalThis.trEpi?.('role.employee','Funcion\u00e1rio',{}) ?? 'Funcion\u00e1rio'); },
    // Identidade técnica da certificação B4-B (#313). Presente só como
    // RÓTULO: a conta precisa ser identificável numa listagem ou auditoria em
    // vez de aparecer com o nome cru. Deliberadamente ausente de
    // USER_COMPANY_REQUIRED_ROLES, CONFIGURATION_ADMIN_ROLES e
    // EPI_ALL_UNITS_PROFILES, e de todo seletor de criação/edição: visibilidade
    // não é permissão para criar pela tela.
    get certification_readonly() { return globalThis.trEpi?.('role.certification_readonly', 'Certificação (somente leitura)') ?? 'Certificação (somente leitura)'; }
  });

  const ROLE_ALIASES = Object.freeze({
    master_admin: 'master_admin',
    masteradmin: 'master_admin',
    general_admin: 'general_admin',
    generaladmin: 'general_admin',
    registry_admin: 'registry_admin',
    registryadmin: 'registry_admin',
    admin: 'admin',
    buyer: 'buyer',
    comprador: 'buyer',
    approver: 'approver',
    aprovador: 'approver',
    user: 'user',
    employee: 'employee'
  });

  const USER_COMPANY_REQUIRED_ROLES = Object.freeze([
    'general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'
  ]);

  const CONFIGURATION_ADMIN_ROLES = Object.freeze([
    'master_admin', 'general_admin', 'registry_admin'
  ]);

  const EPI_ALL_UNITS_VALUE = '__ALL_UNITS__';
  const EPI_COMPANY_LEVEL_FILTER_VALUE = '__COMPANY_LEVEL_ALL_UNITS__';
  const EPI_ALL_UNITS_PROFILES = Object.freeze(['general_admin', 'registry_admin']);

  const DEFAULT_COMPANY_LOGO = `data:image/svg+xml;utf8,${encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">' +
    '<rect width="80" height="80" rx="20" fill="#f6d8c8"/>' +
    '<path d="M20 56h40M26 48V26h28v22" fill="none" stroke="#96401c" ' +
    'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  )}`;

  const DEFAULT_PLATFORM_BRAND = Object.freeze({
    display_name: 'Sua Empresa',
    legal_name: '',
    cnpj: '',
    logo_type: '',
    login_logo_type: ''
  });

  globalThis.STORAGE_KEYS = STORAGE_KEYS;
  globalThis.ROLE_LABELS = ROLE_LABELS;
  globalThis.ROLE_ALIASES = ROLE_ALIASES;
  globalThis.USER_COMPANY_REQUIRED_ROLES = USER_COMPANY_REQUIRED_ROLES;
  globalThis.CONFIGURATION_ADMIN_ROLES = CONFIGURATION_ADMIN_ROLES;
  globalThis.EPI_ALL_UNITS_VALUE = EPI_ALL_UNITS_VALUE;
  globalThis.EPI_COMPANY_LEVEL_FILTER_VALUE = EPI_COMPANY_LEVEL_FILTER_VALUE;
  globalThis.EPI_ALL_UNITS_PROFILES = EPI_ALL_UNITS_PROFILES;
  globalThis.DEFAULT_COMPANY_LOGO = DEFAULT_COMPANY_LOGO;
  globalThis.DEFAULT_PLATFORM_BRAND = DEFAULT_PLATFORM_BRAND;
})();
