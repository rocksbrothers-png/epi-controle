'use strict';

// Módulo de negócio: Minha Empresa (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Puro: sem DOM, HTTP, storage nem leitura de globais. Tipos de imagem aceitos
// por campo, cores padrão, modo de tema gravado em theme_json e os rótulos de
// situação dos domínios. A empresa é a do usuário autenticado: o backend a
// deriva da sessão e o front nunca envia company_id/tenant_id para estas rotas.
(function () {
  if (globalThis.__EPI_MODULE_MY_COMPANY_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_MY_COMPANY_BUSINESS_LOADED__ = true;

  const MY_COMPANY_IMAGE_TYPES = Object.freeze({
    logo_type: Object.freeze(['image/png', 'image/jpeg', 'image/svg+xml']),
    favicon_type: Object.freeze(['image/png', 'image/svg+xml']),
    login_logo_type: Object.freeze(['image/png', 'image/svg+xml'])
  });
  const MY_COMPANY_COLOR_DEFAULTS = Object.freeze({ primary_color: '#1565C0', secondary_color: '#42A5F5', accent_color: '#FF6F00' });
  const FALLBACK_COLOR = '#1565C0';

  function myCompanyThemeMode(company) {
    try { return JSON.parse(company?.theme_json || '{}').mode || 'auto'; } catch { return 'auto'; }
  }

  function themeJsonFor(mode) {
    return JSON.stringify({ mode: mode || 'auto' });
  }

  function defaultColorFor(name) {
    return MY_COMPANY_COLOR_DEFAULTS[name] || FALLBACK_COLOR;
  }

  function isAllowedImageType(name, mimeType) {
    return (MY_COMPANY_IMAGE_TYPES[name] || []).includes(mimeType);
  }

  // Situação de verificação/SSL do domínio (texto do próprio app.js).
  function domainStatusLabel(status) {
    return { pending: 'Pendente', verified: 'Verificado', failed: 'Falhou', active: 'Ativo' }[status] || status || '-';
  }

  globalThis.__EPI_MY_COMPANY_BUSINESS__ = Object.freeze({
    MY_COMPANY_IMAGE_TYPES,
    MY_COMPANY_COLOR_DEFAULTS,
    myCompanyThemeMode,
    themeJsonFor,
    defaultColorFor,
    isAllowedImageType,
    domainStatusLabel
  });
})();
