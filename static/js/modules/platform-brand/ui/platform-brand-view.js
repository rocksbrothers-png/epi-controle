'use strict';
/* global tr, companyLogoMarkup, escapeHtml, fileToJpegDataUrl, fileToDataUrl,
   formValues, formatCnpj */

// Marca da plataforma — UI extraída do app.js, sem alterar efeitos/mensagens.
// Estado/refs são as pontes vivas, consultadas a cada chamada. O app mantém
// apenas um alias do mesmo DEFAULT_PLATFORM_BRAND (bootstrap e mensagens).
// As quatro síncronas preservam as globais legadas; as três async que eram
// de bloco continuam acessíveis apenas pelo namespace. Listeners ficam no app.
(function () {
  if (globalThis.__EPI_MODULE_PLATFORM_BRAND_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_PLATFORM_BRAND_UI_LOADED__ = true;

  const DEFAULT_PLATFORM_BRAND = { display_name: 'Sua Empresa', legal_name: '', cnpj: '', logo_type: '', login_logo_type: '' };

  function renderPlatformLogoPreview(logoValue) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.platformLogoPreview) {return;}
    refs.platformLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: state.platformBrand?.display_name || tr('commercial.panel.defaultBrandName', 'Sua Empresa'), logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${escapeHtml(logoValue ? tr('commercial.panel.logoLoaded', 'Logotipo carregado') : tr('commercial.panel.logoDefault', 'Imagem padrão em uso'))}</span></div>`;
  }

  function renderPlatformLoginLogoPreview(logoValue) {
    const refs = globalThis.__EPI_REFS__;
    if (!refs.platformLoginLogoPreview) {return;}
    refs.platformLoginLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: tr('commercial.panel.loginLogoName', 'Logo da tela de login'), logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${escapeHtml(logoValue ? tr('commercial.panel.loginLogoLoaded', 'Logotipo de login carregado') : tr('commercial.panel.loginLogoDefault', 'Sem logotipo de login (padrão)'))}</span></div>`;
  }

  async function handlePlatformLogoUpload(event) {
    const refs = globalThis.__EPI_REFS__;
    const file = event.target.files?.[0];
    if (!file) {
      refs.platformBrandForm.elements.logo_type.value = '';
      renderPlatformLogoPreview('');
      return;
    }
    const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];
    if (!allowed.includes(file.type)) {
      alert('Envie um logotipo PNG, JPG ou SVG.');
      event.target.value = '';
      return;
    }
    try {
      refs.platformBrandForm.elements.logo_type.value = await fileToJpegDataUrl(file);
      renderPlatformLogoPreview(refs.platformBrandForm.elements.logo_type.value);
    } catch (error) {
      alert(error.message);
      event.target.value = '';
    }
  }

  async function handlePlatformLoginLogoUpload(event) {
    const refs = globalThis.__EPI_REFS__;
    const file = event.target.files?.[0];
    if (!file) {
      refs.platformBrandForm.elements.login_logo_type.value = '';
      renderPlatformLoginLogoPreview('');
      return;
    }
    const allowed = ['image/png', 'image/svg+xml'];
    if (!allowed.includes(file.type)) {
      alert(tr('commercial.panel.loginLogoFormat', 'A logo da tela de login aceita apenas PNG ou SVG.'));
      event.target.value = '';
      return;
    }
    try {
      refs.platformBrandForm.elements.login_logo_type.value = await fileToDataUrl(file);
      renderPlatformLoginLogoPreview(refs.platformBrandForm.elements.login_logo_type.value);
    } catch (error) {
      alert(error.message);
      event.target.value = '';
    }
  }

  function renderPlatformBrand() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const brand = state.platformBrand || DEFAULT_PLATFORM_BRAND;
    if (refs.platformBrandName) {
      globalThis.EpiI18n?.clearBinding?.(refs.platformBrandName);
      refs.platformBrandName.textContent = brand.display_name || DEFAULT_PLATFORM_BRAND.display_name;
    }
    if (refs.platformBrandLogo) {refs.platformBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: brand.logo_type }, 'company-logo company-logo-sm');}
    if (refs.platformBrandForm) {
      refs.platformBrandForm.elements.display_name.value = brand.display_name || '';
      refs.platformBrandForm.elements.legal_name.value = brand.legal_name || '';
      refs.platformBrandForm.elements.cnpj.value = brand.cnpj || '';
      refs.platformBrandForm.elements.logo_type.value = brand.logo_type || '';
      refs.platformBrandForm.elements.login_logo_type.value = brand.login_logo_type || '';
    }
    if (refs.platformLogoFile) {refs.platformLogoFile.value = '';}
    if (refs.platformLoginLogoFile) {refs.platformLoginLogoFile.value = '';}
    renderPlatformLogoPreview(brand.logo_type || '');
    renderPlatformLoginLogoPreview(brand.login_logo_type || '');
    // Só re-renderiza o login logo se o platformBrand tiver um logo definido.
    // Caso contrário mantém o logo do tenant aplicado pelo tenant-init.js.
    const loginLogoSrc = brand.login_logo_type || '';
    if (refs.loginBrandLogo) {
      if (loginLogoSrc) {
        refs.loginBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: loginLogoSrc }, 'company-logo company-logo-lg');
      } else if (!window.__epiTenant) {
        refs.loginBrandLogo.innerHTML = '';
      }
      // Se não há logo de plataforma mas há tenant, o tenant-init.js já aplicou
    }
  }

  function platformBrandDisplayName() {
    const state = globalThis.__EPI_APP_STATE__;
    return state.platformBrand?.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  }

  async function savePlatformBrand(event) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    event.preventDefault();
    if (state.user?.role !== 'master_admin') {return;}
    try {
      const values = formValues(refs.platformBrandForm);
      values.actor_user_id = state.user.id;
      if (values.cnpj) {values.cnpj = formatCnpj(values.cnpj);}
      const payload = await globalThis.__EPI_PLATFORM_BRAND_API__.saveBrand(values);
      state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...payload.brand };
      renderPlatformBrand();
      alert(tr('commercial.panel.brandUpdated', 'Marca da sua empresa atualizada.'));
    } catch (error) { alert(error.message); }
  }

  const functions = { renderPlatformLogoPreview, renderPlatformLoginLogoPreview, handlePlatformLogoUpload, handlePlatformLoginLogoUpload, renderPlatformBrand, platformBrandDisplayName, savePlatformBrand };
  for (const name of ['renderPlatformLogoPreview','renderPlatformLoginLogoPreview','renderPlatformBrand','platformBrandDisplayName']) {
    globalThis[name] = functions[name];
  }
  globalThis.__EPI_PLATFORM_BRAND_UI__ = Object.freeze({ ...functions, DEFAULT_PLATFORM_BRAND });
})();
