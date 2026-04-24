(function phase43Iife() {
  if (globalThis.__EPI_PHASE43_BOUND__) return;
  globalThis.__EPI_PHASE43_BOUND__ = true;

  var STORAGE_KEY = 'epi:ux:phase43:state:v1';
  var PHASE42_MEMORY_KEY = 'epi:ux:phase42:memory:v2';
  var MAX_STORAGE_BYTES = 12000;
  var runtime = {
    listenersBound: false,
    formBound: new WeakSet(),
    currentForm: null,
    userEdited: new Set(),
    manualMode: false,
    lastSuggestion: null,
    quickOpen: false
  };

  function safeOn(target, eventName, handler, options) {
    try {
      if (typeof globalThis.safeOn === 'function') return globalThis.safeOn(target, eventName, handler, options);
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (error) {
      console.warn('[phase43] safeOn falhou', error);
      return false;
    }
  }

  function byId(id) { return document.getElementById(id); }
  function trim(value) { return String(value || '').trim(); }
  function selectedText(selectField) {
    var option = selectField && selectField.selectedOptions ? selectField.selectedOptions[0] : null;
    return trim(option && option.textContent ? option.textContent : '');
  }

  function isEnabled() {
    try {
      var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
      if (typeof helpers.getFeatureFlag === 'function') return helpers.getFeatureFlag('ux_phase43_enabled', { defaultValue: false }) === true;
      if (typeof globalThis.getFeatureFlag === 'function') return globalThis.getFeatureFlag('ux_phase43_enabled', { defaultValue: false }) === true;
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase43') === '1') return true;
      if (params.get('ux_phase43') === '0') return false;
      return globalThis.localStorage?.getItem('ux_phase43_enabled') === '1';
    } catch (_) {
      return false;
    }
  }

  function resetIfRequested() {
    try {
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase43_reset') !== '1') return;
      localStorage.removeItem(STORAGE_KEY);
      runtime.manualMode = false;
      runtime.lastSuggestion = null;
    } catch (_) {}
  }

  function loadState() {
    try {
      var parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      if (!parsed || typeof parsed !== 'object') return {};
      return parsed;
    } catch (_) {
      return {};
    }
  }

  function saveState(payload) {
    try {
      var raw = JSON.stringify(payload || {});
      if (raw.length > MAX_STORAGE_BYTES) return;
      localStorage.setItem(STORAGE_KEY, raw);
    } catch (_) {}
  }

  function loadPhase42Memory() {
    try {
      var parsed = JSON.parse(localStorage.getItem(PHASE42_MEMORY_KEY) || '{}');
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function isDeliveriesViewActive() {
    return Boolean(document.querySelector('#entregas-view.view.active'));
  }

  function isDropdownOpen() {
    return Boolean(document.querySelector('.delivery-ux-dropdown.open, [role="listbox"], select:focus'));
  }

  function isEditableContext(target) {
    var element = target instanceof HTMLElement ? target : document.activeElement;
    if (!(element instanceof HTMLElement)) return false;
    if (element.isContentEditable) return true;
    var tag = String(element.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return true;
    if (tag !== 'input') return false;
    var type = String(element.type || 'text').toLowerCase();
    return type !== 'button' && type !== 'submit' && type !== 'checkbox' && type !== 'radio';
  }

  function getFields(form) {
    return {
      employee: byId('delivery-employee'),
      epi: byId('delivery-epi'),
      unit: byId('delivery-unit-filter'),
      qty: form.querySelector('[name="quantity"]'),
      stockCode: byId('delivery-stock-item-code')
    };
  }

  function validateContext(form) {
    var fields = getFields(form);
    var qty = Number(trim(fields.qty && fields.qty.value) || '0');
    var missing = [];
    if (!trim(fields.employee && fields.employee.value)) missing.push('colaborador');
    if (!trim(fields.epi && fields.epi.value)) missing.push('EPI');
    if (!trim(fields.unit && fields.unit.value)) missing.push('unidade');
    if (!(qty > 0)) missing.push('quantidade');
    if (!trim(fields.stockCode && fields.stockCode.value)) missing.push('código lido');
    return {
      valid: missing.length === 0,
      missing: missing
    };
  }

  function hasSelectionContext(form) {
    var fields = getFields(form);
    var qty = Number(trim(fields.qty && fields.qty.value) || '0');
    return Boolean(trim(fields.employee && fields.employee.value) && trim(fields.epi && fields.epi.value) && trim(fields.unit && fields.unit.value) && qty > 0);
  }

  function ensureUi(form) {
    var fastCard = byId('phase43-fast-card');
    if (!fastCard) {
      fastCard = document.createElement('section');
      fastCard.id = 'phase43-fast-card';
      fastCard.className = 'phase43-fast-card';
      fastCard.hidden = true;
      form.insertBefore(fastCard, form.firstChild.nextSibling);
    }

    var quick = byId('phase43-quick-confirm');
    if (!quick) {
      quick = document.createElement('section');
      quick.id = 'phase43-quick-confirm';
      quick.className = 'phase43-quick-confirm';
      quick.hidden = true;
      form.appendChild(quick);
    }

    var sticky = byId('phase43-sticky-actions');
    if (!sticky) {
      sticky = document.createElement('aside');
      sticky.id = 'phase43-sticky-actions';
      sticky.className = 'phase43-sticky-actions';
      sticky.hidden = true;
      sticky.innerHTML = [
        '<div class="phase43-sticky-main">',
        '  <button type="button" id="phase43-primary-action" class="primary">Confirmar entrega rápida</button>',
        '  <small id="phase43-state" class="phase43-state" data-state="idle">Pronto</small>',
        '</div>'
      ].join('');
      document.body.appendChild(sticky);
    }
    return { fastCard: fastCard, quick: quick, sticky: sticky };
  }

  function setState(text, tone) {
    var node = byId('phase43-state');
    if (!node) return;
    node.textContent = trim(text) || 'Pronto';
    node.dataset.state = trim(tone) || 'idle';
  }

  function readSuggestion(memory, employeeId) {
    var events = Array.isArray(memory.events) ? memory.events : [];
    var filtered = events.filter(function (item) {
      return trim(item && item.employeeId) === trim(employeeId)
        && trim(item && item.epiId)
        && trim(item && item.unitId);
    });
    if (!filtered.length) return null;

    var epiCount = new Map();
    filtered.forEach(function (item) {
      var key = String(item.epiId);
      epiCount.set(key, (epiCount.get(key) || 0) + 1);
    });
    var ranking = Array.from(epiCount.entries()).sort(function (a, b) { return b[1] - a[1]; });
    if (!ranking.length) return null;

    var top = ranking[0];
    var second = ranking[1];
    var inconsistent = Boolean(second && top[1] === second[1]);
    if (inconsistent) return null;

    var recent = filtered[filtered.length - 1];
    if (!recent || !trim(recent.epiId) || !trim(recent.unitId)) return null;

    return {
      employeeId: trim(employeeId),
      epiId: String(top[0]),
      unitId: trim(recent.unitId),
      confidence: top[1],
      badges: ['Mais usado', 'Recente', 'Recomendado']
    };
  }

  function applySuggestionIfSafe(form, suggestion) {
    if (!suggestion || runtime.manualMode) return false;
    var fields = getFields(form);
    var changed = false;

    if (fields.unit && !trim(fields.unit.value) && !runtime.userEdited.has(fields.unit.id)) {
      var unitExists = Array.from(fields.unit.options || []).some(function (option) { return String(option.value) === String(suggestion.unitId); });
      if (unitExists) {
        fields.unit.value = String(suggestion.unitId);
        changed = true;
      }
    }

    if (fields.epi && !trim(fields.epi.value) && !runtime.userEdited.has(fields.epi.id)) {
      var epiExists = Array.from(fields.epi.options || []).some(function (option) { return String(option.value) === String(suggestion.epiId); });
      if (epiExists) {
        fields.epi.value = String(suggestion.epiId);
        changed = true;
      }
    }

    if (changed) {
      if (fields.unit) fields.unit.dispatchEvent(new Event('change', { bubbles: true }));
      if (fields.epi) fields.epi.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return changed;
  }

  function renderSuggestionCard(ui, form, suggestion) {
    var card = ui.fastCard;
    if (!card) return;
    if (!suggestion) {
      card.hidden = true;
      card.innerHTML = '';
      return;
    }
    var fields = getFields(form);
    card.innerHTML = [
      '<header><strong>Entrega rápida sugerida</strong><small>Sugestão automática (não é decisão final)</small></header>',
      '<div class="phase43-badges">',
      suggestion.badges.map(function (label, idx) {
        var klass = idx === 0 ? 'is-most' : (idx === 1 ? 'is-recent' : 'is-recommended');
        return '<span class="phase43-badge ' + klass + '">' + label + '</span>';
      }).join(''),
      '</div>',
      '<div class="phase43-fast-grid">',
      '<div><span>Colaborador</span><strong>' + (selectedText(fields.employee) || '-') + '</strong></div>',
      '<div><span>EPI sugerido</span><strong>' + (selectedText(fields.epi) || '-') + '</strong></div>',
      '</div>',
      '<div class="phase43-actions">',
      '<button type="button" id="phase43-clear-suggestion" class="ghost">Limpar sugestão</button>',
      '<button type="button" id="phase43-manual-flow" class="ghost">Usar fluxo manual</button>',
      '</div>'
    ].join('');
    card.hidden = false;
  }

  function renderQuickSummary(ui, form) {
    var quick = ui.quick;
    if (!quick) return;
    if (!runtime.quickOpen) {
      quick.hidden = true;
      quick.innerHTML = '';
      return;
    }

    var fields = getFields(form);
    var check = validateContext(form);
    var reason = check.valid ? '' : 'Faltando: ' + check.missing.join(', ') + '.';
    quick.innerHTML = [
      '<div class="phase43-quick-panel" data-phase43-summary-visible="1">',
      '<strong>Confirmação rápida</strong>',
      '<div class="phase43-quick-line"><span>Colaborador</span><b>' + (selectedText(fields.employee) || '-') + '</b></div>',
      '<div class="phase43-quick-line"><span>EPI</span><b>' + (selectedText(fields.epi) || '-') + '</b></div>',
      '<div class="phase43-quick-line"><span>Unidade</span><b>' + (selectedText(fields.unit) || '-') + '</b></div>',
      '<div class="phase43-quick-line"><span>Quantidade</span><b>' + (trim(fields.qty && fields.qty.value) || '-') + '</b></div>',
      reason ? '<div class="phase43-hint">' + reason + '</div>' : '<div class="phase43-hint">Resumo validado. Revise e confirme.</div>',
      '<div class="phase43-quick-actions">',
      '<button type="button" class="primary" id="phase43-confirm" ' + (check.valid ? '' : 'disabled') + '>Confirmar</button>',
      '<button type="button" class="ghost" id="phase43-edit">Editar</button>',
      '</div>',
      '</div>'
    ].join('');
    quick.hidden = false;
  }

  function refreshSticky(ui, form) {
    var sticky = ui.sticky;
    if (!sticky) return;
    var primary = byId('phase43-primary-action');
    var validContext = hasSelectionContext(form);
    sticky.hidden = !validContext;
    if (primary) primary.disabled = !validContext || form.dataset.submitting === '1';
    if (!validContext && runtime.quickOpen) {
      runtime.quickOpen = false;
      renderQuickSummary(ui, form);
    }
  }

  function persistSafeSnapshot(form) {
    var fields = getFields(form);
    var snapshot = {
      employee_id: trim(fields.employee && fields.employee.value),
      epi_id: trim(fields.epi && fields.epi.value),
      unit_id: trim(fields.unit && fields.unit.value),
      qty: trim(fields.qty && fields.qty.value),
      manual_mode: runtime.manualMode ? '1' : '0'
    };
    saveState(snapshot);
  }

  function restoreSafeSnapshot(form) {
    var snapshot = loadState();
    runtime.manualMode = snapshot.manual_mode === '1';
    var fields = getFields(form);

    [
      ['employee', snapshot.employee_id],
      ['epi', snapshot.epi_id],
      ['unit', snapshot.unit_id]
    ].forEach(function (entry) {
      var field = fields[entry[0]];
      var value = trim(entry[1]);
      if (!field || !value || trim(field.value)) return;
      var exists = Array.from(field.options || []).some(function (option) { return String(option.value) === value; });
      if (!exists) return;
      field.value = value;
    });
    if (fields.qty && !trim(fields.qty.value) && trim(snapshot.qty)) {
      fields.qty.value = trim(snapshot.qty);
    }
  }

  function confirmQuick(form, ui) {
    var summaryVisible = Boolean(ui.quick && ui.quick.querySelector('[data-phase43-summary-visible="1"]'));
    if (!runtime.quickOpen || !summaryVisible) {
      setState('Abra e revise o resumo antes de confirmar.', 'error');
      return;
    }
    var check = validateContext(form);
    if (!check.valid) {
      setState('Dados incompletos: ' + check.missing.join(', ') + '.', 'error');
      renderQuickSummary(ui, form);
      return;
    }
    setState('Confirmando entrega...', 'loading');
    form.requestSubmit();
  }

  function bindGlobalHandlers() {
    if (runtime.listenersBound) return;
    runtime.listenersBound = true;

    safeOn(document, 'keydown', function (event) {
      if (!isDeliveriesViewActive()) return;
      var form = runtime.currentForm;
      if (!form) return;
      var ui = ensureUi(form);
      var key = String(event.key || '').toLowerCase();

      if (key === 'escape') {
        runtime.quickOpen = false;
        renderQuickSummary(ui, form);
        setState('Resumo rápido fechado.', 'idle');
        return;
      }

      if (isEditableContext(event.target) || isDropdownOpen()) return;

      if (key === 'enter' && event.ctrlKey) {
        if (!runtime.quickOpen) return;
        var checkCtrl = validateContext(form);
        if (!checkCtrl.valid) return;
        event.preventDefault();
        confirmQuick(form, ui);
        return;
      }

      if (key === 'enter') {
        if (!runtime.quickOpen) return;
        event.preventDefault();
        confirmQuick(form, ui);
      }
    }, true);

    safeOn(document, 'click', function (event) {
      var target = event.target;
      if (!(target instanceof HTMLElement)) return;
      var form = runtime.currentForm;
      if (!form) return;
      var ui = ensureUi(form);

      if (target.id === 'phase43-primary-action') {
        event.preventDefault();
        runtime.quickOpen = true;
        renderQuickSummary(ui, form);
        return;
      }
      if (target.id === 'phase43-confirm') {
        event.preventDefault();
        confirmQuick(form, ui);
        return;
      }
      if (target.id === 'phase43-edit') {
        event.preventDefault();
        runtime.quickOpen = false;
        renderQuickSummary(ui, form);
        setState('Edite os campos antes de confirmar.', 'idle');
        return;
      }
      if (target.id === 'phase43-clear-suggestion') {
        event.preventDefault();
        runtime.lastSuggestion = null;
        var card = byId('phase43-fast-card');
        if (card) {
          card.hidden = true;
          card.innerHTML = '';
        }
        setState('Sugestão removida. Fluxo manual ativo.', 'idle');
        return;
      }
      if (target.id === 'phase43-manual-flow') {
        event.preventDefault();
        runtime.manualMode = true;
        persistSafeSnapshot(form);
        var cardManual = byId('phase43-fast-card');
        if (cardManual) {
          cardManual.hidden = true;
          cardManual.innerHTML = '';
        }
        setState('Fluxo manual selecionado.', 'idle');
      }
    });

    safeOn(document, 'epi:delivery-submit-start', function () {
      var form = runtime.currentForm;
      if (!form) return;
      setState('Processando entrega...', 'loading');
      var primary = byId('phase43-primary-action');
      if (primary) primary.disabled = true;
    });

    safeOn(document, 'epi:delivery-submit-success', function () {
      setState('Entrega registrada.', 'success');
      runtime.quickOpen = false;
      var form = runtime.currentForm;
      if (form) {
        var ui = ensureUi(form);
        renderQuickSummary(ui, form);
        refreshSticky(ui, form);
      }
      setTimeout(function () { setState('Pronto', 'idle'); }, 1300);
    });

    safeOn(document, 'epi:delivery-submit-error', function (event) {
      var message = trim(event && event.detail && event.detail.message) || 'Erro ao registrar entrega.';
      setState(message, 'error');
      var primary = byId('phase43-primary-action');
      if (primary) primary.disabled = false;
    });
  }

  function bindForm(form) {
    if (!form || runtime.formBound.has(form)) return;
    runtime.formBound.add(form);
    runtime.currentForm = form;
    document.body.classList.add('phase43-enabled');

    var ui = ensureUi(form);
    restoreSafeSnapshot(form);

    ['delivery-company', 'delivery-unit-filter', 'delivery-employee', 'delivery-epi', 'delivery-stock-item-code'].forEach(function (id) {
      var field = byId(id);
      if (!field) return;
      safeOn(field, 'change', function () {
        runtime.userEdited.add(id);
        persistSafeSnapshot(form);
        refreshSticky(ui, form);
        renderQuickSummary(ui, form);
      });
      safeOn(field, 'input', function () {
        runtime.userEdited.add(id);
        persistSafeSnapshot(form);
        refreshSticky(ui, form);
        renderQuickSummary(ui, form);
      });
    });

    var qtyField = form.querySelector('[name="quantity"]');
    if (qtyField) {
      safeOn(qtyField, 'input', function () {
        runtime.userEdited.add('quantity');
        persistSafeSnapshot(form);
        refreshSticky(ui, form);
        renderQuickSummary(ui, form);
      });
    }

    safeOn(form, 'submit', function (event) {
      var summaryVisible = Boolean(ui.quick && ui.quick.querySelector('[data-phase43-summary-visible="1"]'));
      var check = validateContext(form);
      if (!runtime.quickOpen || !summaryVisible || !check.valid) {
        event.preventDefault();
        runtime.quickOpen = true;
        renderQuickSummary(ui, form);
        setState(!check.valid ? 'Dados incompletos: ' + check.missing.join(', ') + '.' : 'Revise o resumo antes de confirmar.', 'error');
        return;
      }
      setState('Confirmando entrega...', 'loading');
    }, true);

    var memory = loadPhase42Memory();
    var employeeId = trim(byId('delivery-employee') && byId('delivery-employee').value);
    var suggestion = employeeId ? readSuggestion(memory, employeeId) : null;
    runtime.lastSuggestion = suggestion;
    applySuggestionIfSafe(form, suggestion);
    renderSuggestionCard(ui, form, suggestion);

    refreshSticky(ui, form);
    renderQuickSummary(ui, form);
    setState('Pronto', 'idle');
  }

  function init() {
    try {
      resetIfRequested();
      if (!isEnabled()) return;
      var form = byId('delivery-form');
      if (!form) return;
      bindGlobalHandlers();
      bindForm(form);
    } catch (error) {
      console.warn('[phase43] falha na inicialização, fluxo clássico mantido.', error);
    }
  }

  function scheduleRebind() {
    setTimeout(init, 50);
  }

  if (document.readyState === 'loading') safeOn(document, 'DOMContentLoaded', init, { once: true });
  else init();

  safeOn(document, 'epi:viewchange', scheduleRebind);
  safeOn(document.body, 'htmx:afterSwap', scheduleRebind);
  safeOn(globalThis, 'popstate', scheduleRebind);
})();
