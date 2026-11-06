'use strict';
/* global canConfigureMyCompany, actorQuery, normalizeHexColor, companyLogoMarkup, fileToJpegDataUrl, fileToDataUrl,
   bindAppListener, loadBootstrap, tr, escapeHtml --
   globais do app.js, de shared/* e de modules/auth, resolvidos na chamada */

// UI: Minha Empresa (Configurações) e domínios da tenant
// (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// A empresa contratante é configurada pelo Administrador Geral (Owner da
// tenant); o backend a deriva do usuário autenticado. Regras puras em
// ../business/my-company-rules.js; HTTP em ../integrations/my-company-api.js.
// renderMyCompanyDomains (tabela e instruções DNS dos domínios) veio do app.js na
// UBX Comercial C4, com o corpo idêntico. O assistente de implantação (app.js) usa
// loadMyCompany, fillMyCompanyFields, wireMyCompanyImageInputs e
// collectMyCompanyFields. As funções async eram de bloco no app.js; agora são
// globais com os mesmos nomes.
(function () {
  if (globalThis.__EPI_MODULE_MY_COMPANY_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_MY_COMPANY_UI_LOADED__ = true;

  function rules() { return globalThis.__EPI_MY_COMPANY_BUSINESS__; }
  function myCompanyApi() { return globalThis.__EPI_MY_COMPANY_API__; }

  function myCompanyThemeMode(company) {
    return rules().myCompanyThemeMode(company);
  }

  function fillMyCompanyFields(container, company) {
    if (!container || !company) {return;}
    container.querySelectorAll('[data-mc-field]').forEach((field) => {
      const name = field.dataset.mcField;
      if (name === 'theme_mode') { field.value = myCompanyThemeMode(company); return; }
      if (field.type === 'color') {
        field.value = normalizeHexColor(company[name], rules().defaultColorFor(name));
        return;
      }
      field.value = company[name] ?? '';
    });
    container.querySelectorAll('[data-mc-preview]').forEach((preview) => {
      renderMyCompanyImagePreview(container, preview.dataset.mcPreview);
    });
  }

  function renderMyCompanyImagePreview(container, name) {
    const preview = container.querySelector(`[data-mc-preview="${name}"]`);
    if (!preview) {return;}
    const hidden = container.querySelector(`[data-mc-field="${name}"]`);
    const value = hidden?.value || '';
    preview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: 'Imagem', logo_type: value }, 'company-logo company-logo-lg')}<span>${value ? 'Imagem carregada' : 'Imagem padrão em uso'}</span></div>`;
  }

  function collectMyCompanyFields(container) {
    const values = {};
    if (!container) {return values;}
    container.querySelectorAll('[data-mc-field]').forEach((field) => {
      const name = field.dataset.mcField;
      if (name === 'theme_mode') {
        values.theme_json = rules().themeJsonFor(field.value);
        return;
      }
      values[name] = String(field.value || '').trim();
    });
    return values;
  }

  function wireMyCompanyImageInputs(container) {
    if (!container) {return;}
    container.querySelectorAll('[data-mc-image]').forEach((input) => {
      if (input.dataset.mcWired) {return;}
      input.dataset.mcWired = '1';
      bindAppListener(input, 'change', async () => {
        const name = input.dataset.mcImage;
        const file = input.files?.[0];
        const hidden = container.querySelector(`[data-mc-field="${name}"]`);
        if (!file || !hidden) {return;}
        if (!rules().isAllowedImageType(name, file.type)) {
          alert('Formato de imagem não suportado para este campo.');
          input.value = '';
          return;
        }
        try {
          hidden.value = name === 'logo_type' ? await fileToJpegDataUrl(file) : await fileToDataUrl(file);
          renderMyCompanyImagePreview(container, name);
        } catch (error) {
          alert(error.message);
          input.value = '';
        }
      });
    });
  }

  async function loadMyCompany(force = false) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!canConfigureMyCompany()) {return null;}
    if (state.myCompany && !force) {return state.myCompany;}
    const payload = await myCompanyApi().getMyCompany(actorQuery());
    state.myCompany = payload.company || null;
    return state.myCompany;
  }

  function renderMyCompanyReadonly(company) {
    const box = document.getElementById('my-company-readonly');
    if (!box || !company) {return;}
    box.innerHTML = `<strong>Contrato (somente leitura)</strong><span>Plano: ${company.plan_name || '-'} · Limite de usuários: ${company.user_limit || '-'} · Licença: ${company.license_status || '-'}</span>`;
  }

  async function loadMyCompanyCard(force = false) {
    const form = document.getElementById('my-company-form');
    if (!form || !canConfigureMyCompany()) {return;}
    try {
      const company = await loadMyCompany(force);
      if (!company) {return;}
      fillMyCompanyFields(form, company);
      renderMyCompanyReadonly(company);
      wireMyCompanyImageInputs(form);
      if (!form.dataset.mcWired) {
        form.dataset.mcWired = '1';
        bindAppListener(form, 'submit', saveMyCompany);
        bindAppListener(document.getElementById('my-company-domain-add'), 'click', addMyCompanyDomain);
        bindAppListener(document.getElementById('my-company-domains-table'), 'click', handleMyCompanyDomainAction);
      }
      void loadMyCompanyDomains();
    } catch (error) {
      console.warn('[my-company] falha ao carregar configurações da empresa', error);
    }
  }

  async function saveMyCompany(event) {
    const state = globalThis.__EPI_APP_STATE__;
    event.preventDefault();
    const form = document.getElementById('my-company-form');
    if (!form || !canConfigureMyCompany()) {return;}
    const feedback = document.getElementById('my-company-feedback');
    if (feedback) {feedback.textContent = '';}
    try {
      const values = collectMyCompanyFields(form);
      values.actor_user_id = state.user.id;
      const payload = await myCompanyApi().updateMyCompany(values);
      state.myCompany = payload.company || state.myCompany;
      if (feedback) {feedback.textContent = 'Configurações da empresa salvas com sucesso.';}
      await loadBootstrap();
    } catch (error) {
      if (feedback) {feedback.textContent = error.message;} else {alert(error.message);}
    }
  }

  // ── Domínios da tenant (Minha Empresa) ──────────────────────────────────────

  async function loadMyCompanyDomains() {
    const table = document.getElementById('my-company-domains-table');
    if (!table || !canConfigureMyCompany()) {return;}
    try {
      const payload = await myCompanyApi().listMyCompanyDomains(actorQuery());
      renderMyCompanyDomains(Array.isArray(payload?.domains) ? payload.domains : []);
    } catch (error) {
      table.innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`;
    }
  }

  function renderMyCompanyDomains(domains) {
    const table = document.getElementById('my-company-domains-table');
    const instructions = document.getElementById('my-company-domain-instructions');
    if (!table) return;
    table.innerHTML = domains.map((item) => {
      const primaryMark = Number(item.is_primary) === 1 ? ` <strong data-i18n="myCompany.domains.primary">${escapeHtml(tr('myCompany.domains.primary', '(principal)'))}</strong>` : '';
      const actions = [];
      if (item.verification_status !== 'verified') {
        actions.push(`<button class="ghost" type="button" data-domain-verify="${escapeHtml(item.id)}" data-i18n="myCompany.domains.verify">${escapeHtml(tr('myCompany.domains.verify', 'Verificar'))}</button>`);
      } else if (Number(item.is_primary) !== 1) {
        actions.push(`<button class="ghost" type="button" data-domain-primary="${escapeHtml(item.id)}" data-i18n="myCompany.domains.makePrimary">${escapeHtml(tr('myCompany.domains.makePrimary', 'Tornar principal'))}</button>`);
      }
      actions.push(`<button class="ghost" type="button" data-domain-delete="${escapeHtml(item.id)}" data-i18n="user.remove">Remover</button>`);
      return `<tr><td>${escapeHtml(item.full_host)}${primaryMark}</td><td>${escapeHtml(item.type_label)}</td>` +
        `<td>${escapeHtml(domainStatusLabel(item.verification_status))}</td><td>${escapeHtml(domainStatusLabel(item.ssl_status))}</td>` +
        `<td><div class="action-group">${actions.join('')}</div></td></tr>`;
    }).join('') || `<tr><td colspan="5" data-i18n="myCompany.domains.none">${escapeHtml(tr('myCompany.domains.none', 'Nenhum domínio registrado.'))}</td></tr>`;

    const pending = domains.find((item) => item.verification_status !== 'verified' && item.domain_type !== 'platform_subdomain');
    if (instructions) {
      // O texto vem do catálogo (sem marcação); só os valores DNS, escapados, recebem <strong>/<code>.
      instructions.innerHTML = pending
        ? escapeHtml(tr('myCompany.domains.instructions', 'Para ativar {host}: crie um CNAME apontando para {cname} e um registro TXT em {txt} com o valor {token}, depois clique em Verificar.', {
          host: '\u0000host\u0000', cname: '\u0000cname\u0000', txt: '\u0000txt\u0000', token: '\u0000token\u0000'
        }))
          .replace('\u0000host\u0000', () => `<strong>${escapeHtml(pending.full_host)}</strong>`)
          .replace('\u0000cname\u0000', () => `<code>${escapeHtml(pending.cname_target)}</code>`)
          .replace('\u0000txt\u0000', () => `<code>${escapeHtml(pending.txt_record)}</code>`)
          .replace('\u0000token\u0000', () => `<code>${escapeHtml(pending.verification_token)}</code>`)
        : '';
    }
  }

  function domainStatusLabel(status) {
    return rules().domainStatusLabel(status);
  }

  async function addMyCompanyDomain() {
    const state = globalThis.__EPI_APP_STATE__;
    const feedback = document.getElementById('my-company-domain-feedback');
    if (feedback) {feedback.textContent = '';}
    try {
      const domain = String(document.getElementById('my-company-domain-input')?.value || '').trim();
      const domainType = String(document.getElementById('my-company-domain-type')?.value || 'custom_domain');
      if (!domain) {throw new Error('Informe o domínio a registrar.');}
      await myCompanyApi().addMyCompanyDomain({ actor_user_id: state.user.id, domain, domain_type: domainType });
      const input = document.getElementById('my-company-domain-input');
      if (input) {input.value = '';}
      if (feedback) {feedback.textContent = 'Domínio registrado. Siga as instruções de DNS e clique em Verificar.';}
      await loadMyCompanyDomains();
    } catch (error) {
      if (feedback) {feedback.textContent = error.message;} else {alert(error.message);}
    }
  }

  async function handleMyCompanyDomainAction(event) {
    const state = globalThis.__EPI_APP_STATE__;
    const target = event.target;
    const feedback = document.getElementById('my-company-domain-feedback');
    if (feedback) {feedback.textContent = '';}
    try {
      if (target.dataset.domainVerify) {
        await myCompanyApi().verifyMyCompanyDomain(target.dataset.domainVerify, { actor_user_id: state.user.id });
        if (feedback) {feedback.textContent = 'Domínio verificado com sucesso.';}
      } else if (target.dataset.domainPrimary) {
        await myCompanyApi().setPrimaryMyCompanyDomain(target.dataset.domainPrimary, { actor_user_id: state.user.id });
      } else if (target.dataset.domainDelete) {
        if (!confirm('Remover este domínio da sua empresa?')) {return;}
        await myCompanyApi().deleteMyCompanyDomain(target.dataset.domainDelete, { actor_user_id: state.user.id });
      } else {
        return;
      }
      await loadMyCompanyDomains();
    } catch (error) {
      if (feedback) {feedback.textContent = error.message;} else {alert(error.message);}
      await loadMyCompanyDomains();
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    myCompanyThemeMode,
    fillMyCompanyFields,
    renderMyCompanyImagePreview,
    collectMyCompanyFields,
    wireMyCompanyImageInputs,
    loadMyCompany,
    renderMyCompanyReadonly,
    loadMyCompanyCard,
    saveMyCompany,
    loadMyCompanyDomains,
    renderMyCompanyDomains,
    domainStatusLabel,
    addMyCompanyDomain,
    handleMyCompanyDomainAction
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_MY_COMPANY_UI__ = Object.freeze({ ...exportsMap });
})();
