'use strict';
/* global tr, isMobileUserAgent, isOperationalProfile, filterByUserCompany, unitTypeLabel, EPI_ALL_UNITS_VALUE,
   EPI_ALL_UNITS_PROFILES, parseActiveJoinventureToken, renderJoinventureList, currentJoinventures,
   activeJoinventureToken, setFormSubmitLabel, showView, setEpiValidity, normalizeEpiSizes, fileToDataUrl,
   fileToJpegDataUrl, epiProtectionLabel, epiMeasureLabel --
   globais do app.js, de core/constants.js e dos módulos shared/epis, resolvidos na chamada (ver abaixo) */

// UI: EPIs — cadastro (Refatoração UBX-V3, Etapa 5 — extraído de static/app.js).
//
// Foto do EPI (prévia, upload, câmera), escopo de unidade ("Todas as Unidades"
// para perfis de empresa), regras de Joint Venture no formulário, edição,
// preparo dos valores enviados, limpeza do formulário e a linha da tabela.
//
// Estado: o MESMO objeto do app.js (globalThis.__EPI_APP_STATE__, lido na
// chamada). EPI_ALL_UNITS_VALUE/EPI_ALL_UNITS_PROFILES vêm de core/constants.js,
// com os mesmos valores do app.js. Joint Venture, setEpiValidity,
// setFormSubmitLabel e showView continuam no app.js (globais). Estoque e
// validade física NÃO passam por aqui. handleEpiPhotoUpload, setEpiPhotoData e
// prepareEpiFormValues eram `async function` de bloco no app.js; agora são
// publicadas em globalThis e o app.js chega a elas pelo nome.
(function () {
  if (globalThis.__EPI_MODULE_EPIS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_EPIS_UI_LOADED__ = true;

  // Mesmo escape de views/view-helpers.js (escapeHtml). A foto é uma data URL
  // (base64 não tem & < > " '), então o valor legítimo sai igual; um
  // epi_photo_data salvo com aspas deixa de injetar HTML no atributo src.
  function escapeAttribute(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderEpiPhotoPreview(photoValue) {
    const preview = document.getElementById('epi-photo-preview');
    if (!preview) {return;}
    // SECURITY-OUTPUT-XSS-V1: só data URL base64 de imagem vira <img>.
    if (!/^data:image\/[a-z0-9.+-]{1,40};base64,[A-Za-z0-9+/]+={0,2}$/.test(String(photoValue || ''))) {
      photoValue = '';
    }
    if (!photoValue) {
      preview.innerHTML = `<div class="summary-item">${tr('epi.photoMissing', 'Sem foto anexada.')}</div>`;
      return;
    }
    preview.innerHTML = `<div class="logo-preview-card"><img class="company-logo company-logo-lg" src="${escapeAttribute(photoValue)}" alt="Preview da foto do EPI"><span>${tr('epi.photoAttached', 'Foto do EPI anexada')}</span></div>`;
  }

  async function handleEpiPhotoUpload(event) {
    const hiddenField = document.getElementById('epi-photo-data');
    const file = event.target.files?.[0];
    if (!hiddenField) {return;}
    if (!file) {
      hiddenField.value = '';
      renderEpiPhotoPreview('');
      return;
    }
    if (!String(file.type || '').startsWith('image/')) {
      alert('Envie um arquivo de imagem válido para o EPI.');
      event.target.value = '';
      return;
    }
    try {
      hiddenField.value = await fileToJpegDataUrl(file, 960);
      renderEpiPhotoPreview(hiddenField.value);
    } catch (error) {
      alert(error.message || 'Não foi possí­vel processar a foto do EPI.');
      event.target.value = '';
      hiddenField.value = '';
      renderEpiPhotoPreview('');
    }
  }

  function openEpiPhotoPicker({ preferCamera = false } = {}) {
    const input = document.getElementById('epi-photo-file');
    if (!input) {return;}
    if (preferCamera && isMobileUserAgent()) {
      input.setAttribute('capture', 'environment');
    } else {
      input.removeAttribute('capture');
    }
    input.click();
  }

  function configureEpiPhotoInputCapture() {
    const input = document.getElementById('epi-photo-file');
    if (!input) {return;}
    input.setAttribute('accept', 'image/*');
    if (isMobileUserAgent()) {
      input.setAttribute('capture', 'environment');
    } else {
      input.removeAttribute('capture');
    }
  }

  function canUseEpiAllUnitsScope() {
    const state = globalThis.__EPI_APP_STATE__;
    return EPI_ALL_UNITS_PROFILES.includes(state.user?.role);
  }

  function syncEpiUnitOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const companyField = document.getElementById('epi-company');
    const unitField = document.getElementById('epi-unit');
    if (!companyField || !unitField) {return;}
    const operationalProfile = isOperationalProfile();
    const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
    if (operationalProfile && state.user?.company_id) {
      companyField.value = String(state.user.company_id);
      companyField.disabled = true;
    } else {
      companyField.disabled = false;
    }
    const companyId = companyField.value || state.user?.company_id || '';
    const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    const previous = String(unitField.value || '');
    const unitOptions = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
    const allowAllUnitsScope = canUseEpiAllUnitsScope();
    if (operationalProfile) {
      const scopedUnits = units.filter((item) => String(item.id) === operationalUnitId);
      unitField.innerHTML = scopedUnits.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('') || '<option value="">Sem unidade operacional vinculada</option>';
      unitField.value = scopedUnits.length ? String(scopedUnits[0].id) : '';
      unitField.disabled = true;
    } else {
      const allUnitsOption = allowAllUnitsScope ? `<option value="${EPI_ALL_UNITS_VALUE}">${tr('epi.allUnits', 'Todas as Unidades')}</option>` : '';
      unitField.innerHTML = `${allUnitsOption}${unitOptions}`;
      if (allowAllUnitsScope && (!previous || previous === EPI_ALL_UNITS_VALUE)) {
        unitField.value = EPI_ALL_UNITS_VALUE;
      } else if (previous && units.some((item) => String(item.id) === previous)) {
        unitField.value = previous;
      } else if (units.length) {
        unitField.value = String(units[0].id);
      } else {
        unitField.value = '';
      }
      unitField.disabled = false;
    }
    applyEpiJoinventureRules();
  }

  function applyEpiJoinventureRules() {
    const unitField = document.getElementById('epi-unit');
    const activeSelect = document.getElementById('epi-joinventure-active');
    const hint = document.getElementById('epi-unit-rule-hint');
    if (!unitField || !activeSelect) {return;}
    const selected = parseActiveJoinventureToken(activeSelect.value);
    if (selected.name && selected.unit_id) {
      unitField.value = String(selected.unit_id);
      unitField.disabled = true;
      if (hint) {hint.textContent = (globalThis.EpiI18n?.textFor?.(hint,'epi.lockedByJoinventureHint','Unidade travada pela Joint Venture ativa: {name}.', { name: selected.name }) ?? tr('epi.lockedByJoinventureHint', 'Unidade travada pela Joint Venture ativa: {name}.', { name: selected.name }));}
    } else {
      unitField.disabled = isOperationalProfile();
      if (!unitField.value && !isOperationalProfile() && canUseEpiAllUnitsScope()) {unitField.value = EPI_ALL_UNITS_VALUE;}
      if (hint) {hint.textContent = (globalThis.EpiI18n?.textFor?.(hint,'epi.noActiveJoinventureHint','Sem Joint Venture ou Unidade Única ativa: você pode usar "Todas as Unidades" para aprovar o EPI em nível de empresa.') ?? tr('epi.noActiveJoinventureHint', 'Sem Joint Venture ou Unidade Única ativa: você pode usar "Todas as Unidades" para aprovar o EPI em nível de empresa.'));}
    }
  }

  function startEditEpi(epiId) {
    const state = globalThis.__EPI_APP_STATE__;
    const item = state.epis.find((epi) => String(epi.id) === String(epiId));
    const form = document.getElementById('epi-form');
    if (!item || !form) {return;}
    form.elements.id.value = item.id;
    form.elements.company_id.value = item.company_id;
    syncEpiUnitOptions();
    form.elements.unit_id.value = item.unit_id || '';
    form.elements.name.value = item.name || '';
    form.elements.purchase_code.value = item.purchase_code || '';
    form.elements.ca.value = item.ca || '';
    form.elements.sector.value = item.sector || '';
    form.elements.epi_section.value = item.epi_section || '';
    form.elements.model_reference.value = item.model_reference || '';
    if (!form.elements.sector.value) {form.elements.sector.value = 'Proteção-Membros Superiores';}
    form.elements.manufacturer.value = item.manufacturer || '';
    form.elements.supplier_company.value = item.supplier_company || '';
    form.elements.unit_measure.value = item.unit_measure || 'unidade';
    form.elements.ca_expiry.value = item.ca_expiry || '';
    form.elements.epi_validity_date.value = item.epi_validity_date || '';
    if (form.elements.glove_size) {form.elements.glove_size.value = item.glove_size || 'N/A';}
    if (form.elements.size) {form.elements.size.value = item.size || 'N/A';}
    if (form.elements.uniform_size) {form.elements.uniform_size.value = item.uniform_size || 'N/A';}
    form.elements.manufacturer_validity_months.value = String(item.manufacturer_validity_months ?? item.validity_months ?? 0);
    form.elements.manufacturer_recommendations.value = item.manufacturer_recommendations || '';
    form.elements.epi_photo_data.value = item.epi_photo_data || '';
    if (document.getElementById('epi-photo-file')) {document.getElementById('epi-photo-file').value = '';}
    renderEpiPhotoPreview(form.elements.epi_photo_data.value);
    document.getElementById('epi-joinventures').value = item.joinventures_json || '[]';
    renderJoinventureList();
    const existingEntry = currentJoinventures().find((entry) => entry.name === String(item.active_joinventure || '').trim());
    form.elements.active_joinventure.value = existingEntry ? activeJoinventureToken(existingEntry) : '';
    applyEpiJoinventureRules();
    setFormSubmitLabel('epi-form', 'Atualizar EPI');
    showView('epis');
  }

  async function setEpiPhotoData(values, editingId) {
    const state = globalThis.__EPI_APP_STATE__;
    const photoFile = document.getElementById('epi-photo-file')?.files?.[0];
    if (photoFile) {
      values.epi_photo_data = await fileToDataUrl(photoFile);
    } else if (editingId) {
      const currentEpi = state.epis.find((epi) => String(epi.id) === String(editingId));
      values.epi_photo_data = currentEpi?.epi_photo_data || '';
    }
  }

  async function prepareEpiFormValues(values, editingId, event) {
    const parsedActiveJoinventure = parseActiveJoinventureToken(values.active_joinventure);
    if (parsedActiveJoinventure.name && parsedActiveJoinventure.unit_id) {
      values.unit_id = parsedActiveJoinventure.unit_id;
    }
    if (!parsedActiveJoinventure.name && String(values.unit_id || '') === EPI_ALL_UNITS_VALUE) {
      values.unit_id = '';
    }
    values.active_joinventure = parsedActiveJoinventure.name || '';
    values.stock = 0;

    normalizeEpiSizes(values);
    setEpiValidity(values);

    values.joinventures_json = document.getElementById('epi-joinventures')?.value || '[]';

    if (!values.epi_photo_data && editingId) {
      await setEpiPhotoData(values, editingId);
    }
    return values;
  }

  function resetEpiForm(form) {
    if (form.elements.id) {form.elements.id.value = '';}
    const hidden = document.getElementById('epi-joinventures');
    if (hidden) {hidden.value = '[]';}
    if (form.elements.epi_photo_data) {form.elements.epi_photo_data.value = '';}
    const photoFile = document.getElementById('epi-photo-file');
    if (photoFile) {photoFile.value = '';}
    renderEpiPhotoPreview('');
    renderJoinventureList();
    if (form.elements.unit_id) {
      form.elements.unit_id.value = canUseEpiAllUnitsScope()
        ? EPI_ALL_UNITS_VALUE
        : (form.elements.unit_id.options[0]?.value || '');
    }
    if (form.elements.active_joinventure) {form.elements.active_joinventure.value = '';}
    applyEpiJoinventureRules();
    setFormSubmitLabel('epi-form', 'Salvar EPI');
  }

  function buildEpiRow(item, canManageEpiRecords) {
    const actions = canManageEpiRecords ? `<div class="action-group"><button class="ghost" data-epi-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-epi-archive="${item.id}">${tr('epi.archive', 'Arquivar')}</button></div>` : '-';
    const scopeLabel = item.scope_label
      || (String(item.scope_type || '').toUpperCase() === 'GLOBAL'
        ? tr('epi.allUnits', 'Todas as Unidades')
        : `${item.unit_name || '-'}${Number(item.is_joint_venture || 0) === 1 ? ' (Joint Venture)' : ''}`);
    // SECURITY-OUTPUT-XSS-V1: dados do cadastro entram escapados (mesmo escape da foto).
    // `${v}` mantém a saída anterior para campo ausente ("undefined"), só que escapada.
    const e = (value) => escapeAttribute(`${value}`);
    return `<tr><td>${e(item.company_name)}</td><td>${e(scopeLabel)}</td><td>${e(item.name)}</td><td>${e(item.purchase_code)}</td><td>${e(epiProtectionLabel(item.sector))}</td><td>${e(item.epi_section || '-')}</td><td>${e(item.manufacturer || '-')}</td><td>${e(item.supplier_company || '-')}</td><td>${e(item.active_joinventure || '-')}</td><td>${e(epiMeasureLabel(item.unit_measure))}</td><td>${actions}</td></tr>`;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const epiRegistrationExports = {
    renderEpiPhotoPreview,
    handleEpiPhotoUpload,
    openEpiPhotoPicker,
    configureEpiPhotoInputCapture,
    canUseEpiAllUnitsScope,
    syncEpiUnitOptions,
    applyEpiJoinventureRules,
    startEditEpi,
    setEpiPhotoData,
    prepareEpiFormValues,
    resetEpiForm,
    buildEpiRow
  };

  for (const [name, fn] of Object.entries(epiRegistrationExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_EPIS_VIEW__ = Object.freeze({ ...epiRegistrationExports });
})();
