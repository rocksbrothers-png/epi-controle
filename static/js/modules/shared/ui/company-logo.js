'use strict';

// UI compartilhada: logotipo da empresa (Refatoração UBX-V5 — fatia própria
// prevista em docs/UBX_APPJS_AUDITORIA.md §15.1; extraído de static/app.js).
//
// companyLogoSrc e companyLogoMarkup são usados pelo topo, por Empresas,
// Minha Empresa, Comercial e pela ficha do colaborador. Camada UI: devolvem
// markup para innerHTML.
//
// SECURITY-LOGO-XSS-V1 preservado sem alteração: o logotipo vem do banco e
// entra num atributo src via innerHTML. Só uma data URL base64 de
// PNG/JPEG/SVG é usada (o alfabeto base64 não tem aspas, espaços nem < >);
// qualquer outro valor mostra o logotipo padrão. O backend aplica a mesma
// regra ao gravar (modules/commercial/service.py).
//
// No app.js eram declarações de função dentro do bloco `if` de carga (Annex B:
// viravam globais quando o bloco rodava). Agora são publicadas em globalThis e
// o app.js e os módulos chegam a elas pelo nome, na hora da chamada.
// DEFAULT_COMPANY_LOGO era a `const` de bloco do app.js; aqui vem de
// js/core/constants.js (globalThis.DEFAULT_COMPANY_LOGO), com valor idêntico
// (verificado em static/js/test/security-logo-xss-runtime.js). Corpos e textos
// idênticos.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_COMPANY_LOGO_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_COMPANY_LOGO_LOADED__ = true;

  function companyLogoSrc(logoValue) {
    const value = String(logoValue || '');
    return /^data:image\/(?:png|jpeg|jpg|svg\+xml);base64,[A-Za-z0-9+/]+={0,2}$/.test(value) ? value : globalThis.DEFAULT_COMPANY_LOGO;
  }

  function companyLogoMarkup(company, className = 'company-logo') {
    const label = company?.name || 'Empresa';
    // Nome da empresa e src vão escapados para atributo (aspas não fecham o atributo).
    const attr = (text) => String(text).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    return `<img class="${attr(className)}" src="${attr(companyLogoSrc(company?.logo_type))}" alt="Logotipo de ${attr(label)}">`;
  }

  const companyLogoExports = {
    companyLogoSrc,
    companyLogoMarkup
  };

  for (const [name, fn] of Object.entries(companyLogoExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_COMPANY_LOGO__ = Object.freeze({ ...companyLogoExports });
})();
