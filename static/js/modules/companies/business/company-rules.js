'use strict';

// Módulo de negócio: Empresas (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Puro: sem DOM, HTTP, storage nem leitura de globais. Contagens do resumo,
// tom do selo de licença e os corpos de gravação da empresa (cadastro, edição
// e ativar/inativar) — mesmas chaves, na mesma ordem e com os mesmos padrões
// que o app.js montava. Licença, limite de usuários e vigência são do
// Comercial: a gravação da empresa só repete os valores atuais. Quem decide
// (companies:*, Administrador Master, isolamento por empresa) é o backend.
(function () {
  if (globalThis.__EPI_MODULE_COMPANIES_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMPANIES_BUSINESS_LOADED__ = true;

  function isCompanyActive(company) {
    return Number(company.active) === 1;
  }

  // Resumo da lista (empresas já limitadas à do usuário pela UI).
  function companiesSummaryCounts(companies) {
    return {
      total: companies.length,
      active: companies.filter((item) => Number(item.active) === 1).length,
      nearLimit: companies.filter((item) => item.near_limit && Number(item.limit_reached) !== 1).length,
      blocked: companies.filter((item) => Number(item.active) !== 1 || ['suspended', 'expired'].includes(item.license_status)).length,
    };
  }

  function licenseTone(licenseStatus) {
    if (licenseStatus === 'active') {return 'active';}
    if (licenseStatus === 'trial') {return 'warning';}
    return 'inactive';
  }

  // Selo de uso: no limite tem precedência sobre "próxima do limite".
  function usageRisk(company) {
    if (Number(company.limit_reached) === 1) {return 'atLimit';}
    if (company.near_limit) {return 'nearLimit';}
    return null;
  }

  // Corpo do cadastro/edição. `fields` são os valores lidos do formulário (o
  // CNPJ já formatado); `current` é a empresa em edição ({} no cadastro).
  // O Administrador Geral inicial só vai no cadastro.
  function companySavePayload(actorUserId, fields, current, editing) {
    const values = {
      actor_user_id: actorUserId,
      name: fields.name,
      legal_name: fields.legal_name,
      cnpj: fields.cnpj,
      logo_type: current.logo_type || '',
      plan_name: current.plan_name || 'start',
      user_limit: current.user_limit || 10,
      addendum_enabled: current.addendum_enabled || 0,
      contract_start: current.contract_start || '',
      contract_end: current.contract_end || '',
      monthly_value: current.monthly_value || 0,
      license_status: current.license_status || 'active',
      active: fields.active,
      commercial_notes: current.commercial_notes || ''
    };
    if (!editing) {
      values.general_admin_email = fields.general_admin_email;
      values.general_admin_name = fields.general_admin_name;
    }
    return values;
  }

  // Corpo de ativar/inativar: a empresa inteira, com o novo `active`.
  function companyTogglePayload(actorUserId, company, active) {
    return { actor_user_id: actorUserId, name: company.name, legal_name: company.legal_name, cnpj: company.cnpj, logo_type: company.logo_type, plan_name: company.plan_name, user_limit: company.user_limit, contract_start: company.contract_start || '', contract_end: company.contract_end || '', monthly_value: company.monthly_value || 0, addendum_enabled: company.addendum_enabled || 0, license_status: company.license_status, active, commercial_notes: company.commercial_notes || '' };
  }

  // Suporte auditado: justificativa mínima de 10 caracteres (o backend revalida).
  const SUPPORT_REASON_MIN_LENGTH = 10;
  const COMPANY_LOGO_TYPES = Object.freeze(['image/png', 'image/jpeg', 'image/svg+xml']);

  function isValidSupportReason(reason) {
    return String(reason).trim().length >= SUPPORT_REASON_MIN_LENGTH;
  }

  globalThis.__EPI_COMPANIES_BUSINESS__ = Object.freeze({
    COMPANY_LOGO_TYPES,
    SUPPORT_REASON_MIN_LENGTH,
    isCompanyActive,
    companiesSummaryCounts,
    licenseTone,
    usageRisk,
    companySavePayload,
    companyTogglePayload,
    isValidSupportReason
  });
})();
