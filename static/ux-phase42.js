(function phase42Iife() {
  var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  var ensureModuleBound = typeof helpers.ensureModuleBound === 'function'
    ? helpers.ensureModuleBound
    : function () { return true; };
  if (!ensureModuleBound('phase42')) return;
  var createScopedAbortController = typeof helpers.createScopedAbortController === 'function'
    ? helpers.createScopedAbortController
    : function () { return new AbortController(); };
  var queueStorageWrite = typeof helpers.queueStorageWrite === 'function'
    ? helpers.queueStorageWrite
    : function (key, value) { try { localStorage.setItem(key, value); } catch (_) {} };
  var moduleController = createScopedAbortController('phase42');

  var STORAGE_KEY = 'epi:ux:phase42:memory:v2';
  var MAX_EVENTS = 120;
  var MAX_STORAGE_BYTES = 45000;

  function safeOn(target, eventName, handler, options) {
    try {
      if (typeof globalThis.safeOn === 'function') return globalThis.safeOn(target, eventName, handler, options);
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (_) {
      return false;
    }
  }

  function isEnabled() {
    try {
      var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_phase42_enabled', { defaultValue: false }) === true;
      }
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase42') === '1') return true;
      if (params.get('ux_phase42') === '0') return false;
      return globalThis.localStorage?.getItem('ux_phase42_enabled') === '1';
    } catch (_) {
      return false;
    }
  }

  function byId(id) { return document.getElementById(id); }
  function trim(value) { return String(value || '').trim(); }

  function loadMemory() {
    try {
      var parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      if (!parsed || typeof parsed !== 'object') return {};
      return parsed;
    } catch (_) {
      return {};
    }
  }

  function saveMemory(memory) {
    try {
      var payload = JSON.stringify(memory || {});
      if (payload.length > MAX_STORAGE_BYTES) return;
      queueStorageWrite(STORAGE_KEY, payload, { wait: 220, maxBytes: MAX_STORAGE_BYTES });
    } catch (_) {}
  }

  function resetMemoryIfRequested() {
    try {
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase42_reset') !== '1') return;
      localStorage.removeItem(STORAGE_KEY);
    } catch (_) {}
  }

  function ensurePanels(form) {
    if (!form) return {};
    var suggestion = byId('phase42-suggestion-box');
    if (!suggestion) {
      suggestion = document.createElement('section');
      suggestion.id = 'phase42-suggestion-box';
      suggestion.className = 'phase42-box';
      suggestion.hidden = true;
      suggestion.setAttribute('aria-live', 'polite');
      form.insertBefore(suggestion, form.firstChild.nextSibling);
    }

    var alerts = byId('phase42-alerts-box');
    if (!alerts) {
      alerts = document.createElement('section');
      alerts.id = 'phase42-alerts-box';
      alerts.className = 'phase42-box phase42-alerts';
      alerts.hidden = true;
      alerts.setAttribute('aria-live', 'polite');
      form.insertBefore(alerts, suggestion.nextSibling);
    }

    var quick = byId('phase42-quick-confirm');
    if (!quick) {
      quick = document.createElement('div');
      quick.id = 'phase42-quick-confirm';
      quick.className = 'phase42-quick-confirm';
      quick.hidden = true;
      form.appendChild(quick);
    }

    return { suggestion: suggestion, alerts: alerts, quick: quick };
  }

  function selectedText(selectField) {
    var option = selectField && selectField.selectedOptions ? selectField.selectedOptions[0] : null;
    return trim(option && option.textContent ? option.textContent : '');
  }

  function getRoleName() {
    return trim(byId('delivery-role') && byId('delivery-role').value).toLowerCase();
  }

  function getContext(memory) {
    var employeeField = byId('delivery-employee');
    var unitField = byId('delivery-unit-filter');
    var epiField = byId('delivery-epi');
    var companyField = byId('delivery-company');
    var now = Date.now();

    return {
      now: now,
      memory: memory,
      employeeId: trim(employeeField && employeeField.value),
      employeeText: selectedText(employeeField),
      unitId: trim(unitField && unitField.value),
      unitText: selectedText(unitField),
      epiId: trim(epiField && epiField.value),
      epiText: selectedText(epiField),
      companyId: trim(companyField && companyField.value),
      roleName: getRoleName()
    };
  }

  function appendUsageEvent(memory, ctx) {
    if (!ctx.employeeId || !ctx.epiId) return;
    var events = Array.isArray(memory.events) ? memory.events : [];
    events.push({
      employeeId: ctx.employeeId,
      epiId: ctx.epiId,
      unitId: ctx.unitId,
      roleName: ctx.roleName,
      at: new Date().toISOString()
    });
    memory.events = events.slice(-MAX_EVENTS);
    memory.last = {
      employeeId: ctx.employeeId,
      unitId: ctx.unitId,
      epiId: ctx.epiId,
      companyId: ctx.companyId
    };
  }

  function summarizeHistory(memory, employeeId, roleName) {
    var events = Array.isArray(memory.events) ? memory.events : [];
    var byEmployee = events.filter(function (item) { return String(item.employeeId) === String(employeeId); });
    var epiMap = new Map();
    var unitMap = new Map();

    byEmployee.forEach(function (item) {
      var epi = String(item.epiId || '');
      var unit = String(item.unitId || '');
      if (epi) epiMap.set(epi, (epiMap.get(epi) || 0) + 1);
      if (unit) unitMap.set(unit, (unitMap.get(unit) || 0) + 1);
    });

    var byRole = roleName
      ? events.filter(function (item) { return String(item.roleName || '') === String(roleName || ''); })
      : [];
    var roleEpis = new Map();
    byRole.forEach(function (item) {
      var epi = String(item.epiId || '');
      if (epi) roleEpis.set(epi, (roleEpis.get(epi) || 0) + 1);
    });

    var recent = byEmployee[byEmployee.length - 1] || null;

    return {
      hasHistory: byEmployee.length > 0,
      employeeTopEpis: Array.from(epiMap.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 3),
      employeeTopUnits: Array.from(unitMap.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 1),
      roleTopEpis: Array.from(roleEpis.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 2),
      recent: recent
    };
  }

  function pickValue(selectField, value, meta) {
    if (!selectField || !trim(value)) return false;
    if (meta && meta.userEdited && meta.userEdited.has(selectField.id)) return false;
    if (trim(selectField.value)) return false;
    var optionExists = Array.from(selectField.options || []).some(function (option) {
      return String(option.value) === String(value);
    });
    if (!optionExists) return false;
    if (!selectField.dataset.phase42PrevValue) selectField.dataset.phase42PrevValue = String(selectField.value || '');
    selectField.value = String(value);
    selectField.dataset.phase42Autofill = '1';
    selectField.classList.add('phase42-autofilled');
    selectField.title = 'Sugestão automática aplicada';
    selectField.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function clearAutofillMark(field) {
    if (!field) return;
    field.classList.remove('phase42-autofilled');
    if (field.title === 'Sugestão automática aplicada') field.title = '';
  }

  function renderSuggestionBox(panel, payload) {
    if (!panel) return;
    if (!payload || (!payload.lines.length && !payload.tags.length)) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }

    var tagsHtml = payload.tags.map(function (tag) {
      return '<span class="phase42-badge ' + tag.kind + '">' + tag.label + '</span>';
    }).join('');

    var linesHtml = payload.lines.map(function (line) {
      return '<li>' + line + '</li>';
    }).join('');

    panel.innerHTML = [
      '<header><strong>Assistente inteligente ativo</strong><small> Sugestões opcionais (não bloqueiam o fluxo)</small></header>',
      tagsHtml ? '<div class="phase42-badges">' + tagsHtml + '</div>' : '',
      linesHtml ? '<ul class="phase42-list">' + linesHtml + '</ul>' : '',
      '<div class="phase42-actions"><button type="button" id="phase42-undo-suggestion" class="ghost">Desfazer sugestão</button></div>'
    ].join('');
    panel.hidden = false;
  }

  function renderAlerts(panel, alerts) {
    if (!panel) return;
    if (!alerts.length) {
      panel.hidden = true;
      panel.innerHTML = '';
      return;
    }
    panel.innerHTML = '<strong>Alertas inteligentes</strong><ul class="phase42-list">' + alerts.map(function (item) {
      return '<li>' + item + '</li>';
    }).join('') + '</ul>';
    panel.hidden = false;
  }

  function highlightAction() {
    var employeeId = trim(byId('delivery-employee') && byId('delivery-employee').value);
    var epiId = trim(byId('delivery-epi') && byId('delivery-epi').value);
    var submitBtn = document.querySelector('#delivery-form button[type="submit"], #delivery-form button.primary');
    var backBtn = byId('delivery-ux-back');
    if (backBtn) backBtn.classList.remove('phase42-next-action');
    if (!submitBtn) return;

    submitBtn.classList.remove('phase42-next-action');
    if (!employeeId) {
      var search = byId('delivery-employee-search');
      if (search) search.classList.add('phase42-next-action');
      submitBtn.dataset.phase42NextLabel = 'Próximo: selecionar colaborador';
      return;
    }
    var searchEl = byId('delivery-employee-search');
    if (searchEl) searchEl.classList.remove('phase42-next-action');

    if (!epiId) submitBtn.dataset.phase42NextLabel = 'Próximo: selecionar EPI';
    else submitBtn.dataset.phase42NextLabel = 'Próximo: confirmar entrega';
    submitBtn.classList.add('phase42-next-action');
  }

  function renderQuickConfirm(panel) {
    if (!panel) return;
    var employee = selectedText(byId('delivery-employee')) || '-';
    var epi = selectedText(byId('delivery-epi')) || '-';
    var qty = trim(document.querySelector('#delivery-form [name="quantity"]')?.value || '1');
    var deliveryDate = trim(document.querySelector('#delivery-form [name="delivery_date"]')?.value || '-');
    if (employee === '-' || epi === '-') {
      panel.hidden = true;
      return;
    }
    panel.innerHTML = '<strong>Resumo rápido</strong><span>' + employee + '</span><span>' + epi + '</span><span>Qtd: ' + qty + ' · Data: ' + deliveryDate + '</span><label class="phase42-review-check"><input type="checkbox" id="phase42-review-check"> Revisei os dados sugeridos antes de confirmar</label>';
    panel.hidden = false;
  }

  function hasExplicitReview() {
    return Boolean(document.getElementById('phase42-review-check')?.checked);
  }

  function maybeRestore(memory, userEdited) {
    var last = memory.last || {};
    pickValue(byId('delivery-company'), last.companyId, { userEdited: userEdited });
    pickValue(byId('delivery-unit-filter'), last.unitId, { userEdited: userEdited });
    pickValue(byId('delivery-employee'), last.employeeId, { userEdited: userEdited });
    pickValue(byId('delivery-epi'), last.epiId, { userEdited: userEdited });

    var filterIds = ['deliveries-filter-company', 'deliveries-filter-unit', 'deliveries-filter-date-from', 'deliveries-filter-date-to', 'deliveries-filter-status'];
    var savedFilters = memory.lastFilters || {};
    filterIds.forEach(function (id) {
      var field = byId(id);
      if (!field || trim(field.value)) return;
      var value = trim(savedFilters[id]);
      if (!value) return;
      field.value = value;
      field.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  function bindFiltersMemory(memory) {
    ['deliveries-filter-company', 'deliveries-filter-unit', 'deliveries-filter-date-from', 'deliveries-filter-date-to', 'deliveries-filter-status'].forEach(function (id) {
      var field = byId(id);
      if (!field) return;
      safeOn(field, 'change', function () {
        var current = memory.lastFilters || {};
        current[id] = String(field.value || '');
        memory.lastFilters = current;
        saveMemory(memory);
      });
    });
  }

  function init() {
    try {
      if (!isEnabled()) return;
      document.body.classList.add('phase42-enabled');
      resetMemoryIfRequested();

      var form = byId('delivery-form');
      if (!form) return;
      var panels = ensurePanels(form);
      var memory = loadMemory();
      var userEdited = new Set();
      var autofilledFieldIds = new Set();

      var watched = ['delivery-company', 'delivery-unit-filter', 'delivery-employee', 'delivery-epi'];
      watched.forEach(function (id) {
        var field = byId(id);
        if (!field) return;
        safeOn(field, 'input', function () { userEdited.add(id); }, { signal: moduleController.signal });
        safeOn(field, 'change', function () {
          if (field.dataset.phase42Autofill === '1') {
            delete field.dataset.phase42Autofill;
            autofilledFieldIds.add(id);
            return;
          }
          userEdited.add(id);
          clearAutofillMark(field);
          autofilledFieldIds.delete(id);
        }, { signal: moduleController.signal });
      });

      maybeRestore(memory, userEdited);
      bindFiltersMemory(memory);

      function refreshAssistant() {
        var ctx = getContext(memory);
        var stats = summarizeHistory(memory, ctx.employeeId, ctx.roleName);
        var suggestionLines = [];
        var tags = [];
        var alerts = [];

        if (ctx.employeeId && stats.hasHistory) {
          var topEpi = stats.employeeTopEpis[0];
          var topUnit = stats.employeeTopUnits[0];
          if (topEpi) {
            suggestionLines.push('EPI mais usado para este colaborador: <strong>' + topEpi[0] + '</strong> (' + topEpi[1] + 'x).');
            tags.push({ label: 'Mais usado', kind: 'is-most' });
            pickValue(byId('delivery-epi'), topEpi[0], { userEdited: userEdited });
          }
          if (topUnit) {
            suggestionLines.push('Última unidade recorrente detectada: <strong>' + topUnit[0] + '</strong>.');
            tags.push({ label: 'Recente', kind: 'is-recent' });
            pickValue(byId('delivery-unit-filter'), topUnit[0], { userEdited: userEdited });
          }
          if (stats.recent && stats.recent.at) {
            var recentDays = Math.floor((ctx.now - new Date(stats.recent.at).getTime()) / 86400000);
            if (Number.isFinite(recentDays) && recentDays <= 30 && recentDays >= 0) {
              alerts.push('Este EPI foi entregue recentemente para o colaborador (' + recentDays + ' dia(s)).');
            }
          }
        }

        if (ctx.employeeId && !stats.hasHistory) {
          alerts.push('Colaborador sem histórico local de entrega. Verifique recomendações antes de confirmar.');
        }

        if (stats.roleTopEpis.length) {
          suggestionLines.push('Para a função atual, EPIs frequentes: ' + stats.roleTopEpis.map(function (item) { return '<strong>' + item[0] + '</strong>'; }).join(', ') + '.');
          tags.push({ label: 'Recomendado', kind: 'is-recommended' });
          if (!ctx.epiId) pickValue(byId('delivery-epi'), stats.roleTopEpis[0][0], { userEdited: userEdited });
        }

        var lowStockItems = Array.isArray(globalThis.__EPI_APP_STATE__?.lowStock) ? globalThis.__EPI_APP_STATE__.lowStock : [];
        var hasLowStockFromState = lowStockItems.some(function (item) { return String(item.epi_id || item.id || '') === String(ctx.epiId); });
        if (hasLowStockFromState) alerts.push('Estoque baixo para o EPI selecionado (fonte: state.lowStock).');
        else if (ctx.epiText && /saldo\s*[:=]?\s*[0-2]\b/i.test(ctx.epiText)) alerts.push('Possível estoque baixo para o EPI selecionado.');

        var qty = trim(document.querySelector('#delivery-form [name="quantity"]')?.value || '');
        if (qty && Number(qty) <= 0) alerts.push('Quantidade inconsistente: informe valor maior que zero.');

        renderSuggestionBox(panels.suggestion, { lines: suggestionLines, tags: tags });
        renderAlerts(panels.alerts, alerts);
        highlightAction();
        renderQuickConfirm(panels.quick);
        saveMemory(memory);
      }

      var refreshAssistantDebounced = (function () {
        var timer = null;
        return function () {
          if (timer) clearTimeout(timer);
          timer = setTimeout(refreshAssistant, 120);
        };
      })();
      ['delivery-company', 'delivery-unit-filter', 'delivery-employee', 'delivery-epi', 'delivery-role', 'delivery-employee-search', 'delivery-epi-search'].forEach(function (id) {
        var field = byId(id);
        if (!field) return;
        safeOn(field, 'change', refreshAssistantDebounced, { signal: moduleController.signal });
        safeOn(field, 'input', refreshAssistantDebounced, { signal: moduleController.signal });
      });

      safeOn(form, 'submit', function (event) {
        if (!hasExplicitReview()) {
          var feedback = document.getElementById('delivery-ux-feedback');
          if (feedback) {
            feedback.textContent = 'Revise explicitamente o resumo rápido antes de confirmar a entrega.';
            feedback.classList.add('is-error');
          }
          event.preventDefault();
          return;
        }
        var ctx = getContext(memory);
        appendUsageEvent(memory, ctx);
        saveMemory(memory);
      }, { capture: true, signal: moduleController.signal });

      safeOn(document, 'click', function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.matches('#delivery-ux-clear')) return;
        userEdited.clear();
        autofilledFieldIds.clear();
        setTimeout(refreshAssistant, 40);
      }, { signal: moduleController.signal });

      safeOn(document, 'click', function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.matches('#phase42-undo-suggestion')) return;
        event.preventDefault();
        autofilledFieldIds.forEach(function (id) {
          var field = byId(id);
          if (!field) return;
          var previous = String(field.dataset.phase42PrevValue || '');
          field.value = previous;
          delete field.dataset.phase42PrevValue;
          clearAutofillMark(field);
          field.dispatchEvent(new Event('change', { bubbles: true }));
        });
        autofilledFieldIds.clear();
      }, { signal: moduleController.signal });

      refreshAssistant();
    } catch (error) {
      console.warn('[phase42] fallback para fluxo clássico por segurança.', error);
    }
  }

  if (document.readyState === 'loading') safeOn(document, 'DOMContentLoaded', init, { once: true });
  else init();
})();
