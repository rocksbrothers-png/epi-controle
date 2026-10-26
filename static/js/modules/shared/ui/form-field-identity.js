'use strict';

// Módulo de UI compartilhado: identificação de elementos e campos de
// formulário (Refatoração UBX-V3, Etapa 1 — extraído de static/app.js).
//
// Localizar a view ativa, ler/gravar `id` com validação, gerar ids estáveis
// para campos sem id/name, preencher `autocomplete`, normalizar ids
// duplicados ou "[object …]" e auditar pendências de acessibilidade, com um
// MutationObserver que mantém isso para o DOM inserido depois do boot.
//
// Camada UI: toca DOM; sem HTTP, sem estado do app. Os corpos são os das
// funções originais do app.js (só chaves acrescentadas para o lint).
//
// Ordem de carga: DEPOIS de js/utils/dom.js e ANTES do app.js. utils/dom.js
// publica versões próprias de isViewActive, resolveFormFieldAutocomplete e
// getElementIdAttribute; no runtime, as do app.js sobrescreviam as dele — e a
// de getElementIdAttribute NÃO é equivalente (utils lê `node.id`; esta lê o
// atributo `id`). Carregar depois de utils/dom.js preserva exatamente o que
// valia antes. Peculiaridades preservadas: describeFieldNode repete as chaves
// nearestFormId/formId (vale a última, lida da propriedade `id`), e
// normalizeInvalidDomIds varre `document` inteiro mesmo recebendo `root`.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_FORM_FIELD_IDENTITY_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_FORM_FIELD_IDENTITY_LOADED__ = true;

  function isViewActive(viewSelector) {
    if (!viewSelector) {return false;}
    const viewElement = document.querySelector(viewSelector);
    if (!viewElement) {return false;}
    return viewElement.classList.contains('active');
  }

  function resolveFormFieldAutocomplete(field) {
    if (!field || typeof field.getAttribute !== 'function') {return null;}
    const tag = String(field.tagName || '').toLowerCase();
    if (tag === 'select' || tag === 'textarea') {return 'off';}
    const type = String(field.getAttribute('type') || 'text').toLowerCase();
    if (['hidden', 'checkbox', 'radio', 'file', 'button', 'submit', 'reset', 'range', 'color'].includes(type)) {return null;}
    if (type === 'password') {
      const marker = String(field.id || field.name || '').toLowerCase();
      if (marker.includes('new') || marker.includes('confirm') || marker.includes('recovery')) {return 'new-password';}
      return 'current-password';
    }
    const marker = String((field.id || '') + ' ' + (field.name || '')).toLowerCase();
    if (marker.includes('user') || marker.includes('login')) {return 'username';}
    if (marker.includes('email')) {return 'email';}
    if (marker.includes('phone') || marker.includes('whatsapp') || marker.includes('tel')) {return 'tel';}
    if (marker === 'name' || marker.endsWith(' name') || marker.includes('-name') || marker.includes('_name')) {return 'name';}
    if (type === 'search' || type === 'date' || type === 'number') {return 'off';}
    return 'off';
  }

  function describeFieldNode(node) {
    if (!node || !(node instanceof HTMLElement)) {return null;}
    const nearestForm = node.closest('form');
    const id = getElementIdAttribute(node);
    const classSuffix = String(node.className || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    const selector = `${String(node.tagName || '').toLowerCase()}${id ? `#${id}` : ''}${classSuffix ? `.${classSuffix}` : ''}`;
    return {
      id,
      rawDomIdProperty: String(node.id || ''),
      tagName: String(node.tagName || '').toLowerCase(),
      name: String(node.getAttribute('name') || ''),
      type: String(node.getAttribute('type') || ''),
      placeholder: String(node.getAttribute('placeholder') || ''),
      // O app.js declarava nearestFormId/formId duas vezes; valia o segundo par
      // (abaixo). O primeiro par (getElementIdAttribute, sem efeito colateral)
      // era sobrescrito e foi removido — mesmo objeto resultante.
      nearestFormId: String((nearestForm && nearestForm.id) || ''),
      formId: String((nearestForm && nearestForm.id) || ''),
      outerHTML: String(node.outerHTML || '').replace(/\s+/g, ' ').trim().slice(0, 220),
      selector
    };
  }

  function getElementIdAttribute(node) {
    if (!node || typeof node.getAttribute !== 'function') {return '';}
    return String(node.getAttribute('id') || '').trim();
  }

  function isValidDomId(value) {
    if (typeof value !== 'string') {return false;}
    const normalized = value.trim();
    if (!normalized) {return false;}
    if (normalized.includes('[object')) {return false;}
    if (/[<>"']/.test(normalized)) {return false;}
    if (/^(undefined|null|nan)$/i.test(normalized)) {return false;}
    return true;
  }

  function toSafeId(value, fallback) {
    const raw = typeof value === 'string' ? value : '';
    const base = raw.trim() || String(fallback || 'form');
    const sanitized = String(base)
      .replace(/[^a-zA-Z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .toLowerCase();
    return sanitized || String(fallback || 'form');
  }

  function setElementIdAttribute(node, value, contextLabel = 'unknown') {
    if (!node || typeof node.setAttribute !== 'function') {return false;}
    if (value instanceof HTMLElement) {
      console.warn('[forms] tentativa de usar elemento como ID ignorada', { contextLabel });
      return false;
    }
    if (typeof value !== 'string') {
      console.warn('[forms] id inválido ignorado', { contextLabel });
      return false;
    }
    const normalized = String(value || '').trim();
    if (!isValidDomId(normalized)) {return false;}
    node.setAttribute('id', normalized);
    return true;
  }

  function normalizeInvalidDomIds(root = document) {
    if (!root || typeof root.querySelectorAll !== 'function') {return [];}
    const isObjectLikeId = (value) => /^\[object\s+[^\]]+\]$/i.test(String(value || '').trim());
    const allNodes = Array.from(document.querySelectorAll('[id]'));
    const idCounts = new Map();
    allNodes.forEach((node) => {
      const id = getElementIdAttribute(node);
      if (!id) {return;}
      idCounts.set(id, (idCounts.get(id) || 0) + 1);
    });
    const toNormalize = allNodes.filter((node) => {
      const id = getElementIdAttribute(node);
      return Boolean(id) && (isObjectLikeId(id) || (idCounts.get(id) || 0) > 1);
    });
    const updates = [];
    toNormalize.forEach((node, index) => {
      const previousId = getElementIdAttribute(node);
      if (!previousId) {return;}
      const tagName = String(node.tagName || 'node').toLowerCase();
      const nearestForm = node.closest('form');
      const basePrefix = nearestForm ? `${nearestForm.id || 'epi-form'}-${tagName}` : `epi-${tagName}`;
      let candidateId = `${basePrefix}-normalized-${index + 1}`.replace(/[^a-zA-Z0-9_-]+/g, '-');
      let seq = 1;
      while (candidateId && document.getElementById(candidateId) && document.getElementById(candidateId) !== node) {
        seq += 1;
        candidateId = `${basePrefix}-normalized-${index + 1}-${seq}`.replace(/[^a-zA-Z0-9_-]+/g, '-');
      }
      if (!candidateId) {return;}
      setElementIdAttribute(node, candidateId, 'normalizeInvalidDomIds');
      Array.from(document.querySelectorAll(`label[for="${CSS.escape(previousId)}"]`)).forEach((label) => {
        label.setAttribute('for', candidateId);
      });
      updates.push({ previousId, newId: candidateId, node: describeFieldNode(node) });
    });
    return updates;
  }

  function ensureFormFieldAttributes(root = document) {
    if (!root || typeof root.querySelectorAll !== 'function') {return;}
    if (!globalThis.__EPI_FORM_FIELD_ID_SEQ__) {globalThis.__EPI_FORM_FIELD_ID_SEQ__ = 0;}

    const isObjectLikeId = (value) => /^\[object\s+[^\]]+\]$/i.test(String(value || '').trim());
    const hasDuplicateId = (value, exceptNode = null) => {
      const normalized = String(value || '').trim();
      if (!normalized) {return false;}
      const nodes = Array.from(document.querySelectorAll(`[id="${CSS.escape(normalized)}"]`));
      if (!exceptNode) {return nodes.length > 1;}
      return nodes.some((node) => node !== exceptNode);
    };
    const buildSafeFieldId = (baseId) => {
      let candidateId = String(baseId || '').trim() || `epi-field-${Date.now()}`;
      while (document.getElementById(candidateId)) {
        globalThis.__EPI_FORM_FIELD_ID_SEQ__ += 1;
        candidateId = `${String(baseId || 'epi-field').trim() || 'epi-field'}-${globalThis.__EPI_FORM_FIELD_ID_SEQ__}`;
      }
      return candidateId;
    };
    const buildStableFieldId = (formId, field, fieldIndex) => {
      const safeFormId = isValidDomId(formId) ? formId : `form-${fieldIndex + 1}`;
      const rawName = String(field?.getAttribute?.('name') || getElementIdAttribute(field) || field?.getAttribute?.('type') || 'field');
      const normalizedName = rawName.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'field';
      return buildSafeFieldId(`${String(safeFormId || 'form').replace(/[^a-zA-Z0-9_-]+/g, '-')}-${normalizedName}-${fieldIndex + 1}`);
    };

    const forms = Array.from(root.querySelectorAll('form'));
    if (root instanceof HTMLFormElement) {forms.unshift(root);}

    forms.forEach((form, formIndex) => {
      const currentFormId = getElementIdAttribute(form);
      let formId = currentFormId;

      if (!isValidDomId(formId) || isObjectLikeId(formId) || hasDuplicateId(formId, form)) {
        const fallback = `form-${formIndex + 1}`;
        const safeId = toSafeId(form.getAttribute('name'), fallback);
        formId = buildSafeFieldId(safeId);
        setElementIdAttribute(form, formId, 'ensureFormFieldAttributes:form');
      }

      const fields = Array.from(form.querySelectorAll('input, select, textarea'));
      fields.forEach((field, fieldIndex) => {
        const hasId = field.hasAttribute('id');
        const hasName = field.hasAttribute('name');
        const currentFieldId = getElementIdAttribute(field);
        const shouldNormalizeInvalidId = hasId && (!isValidDomId(currentFieldId) || isObjectLikeId(currentFieldId) || hasDuplicateId(currentFieldId, field));

        if (shouldNormalizeInvalidId || (!hasId && !hasName)) {
          const previousId = currentFieldId;
          const fallback = `${formId || 'form'}-${field.getAttribute('name') || field.getAttribute('type') || 'field'}-${fieldIndex + 1}`;
          let candidateId = toSafeId(currentFieldId, fallback);
          if (!isValidDomId(candidateId) || isObjectLikeId(candidateId) || hasDuplicateId(candidateId, field)) {
            candidateId = buildStableFieldId(formId, field, fieldIndex);
          }
          setElementIdAttribute(field, candidateId, 'ensureFormFieldAttributes:field');
          if (previousId && previousId !== candidateId) {
            Array.from(form.querySelectorAll(`label[for="${CSS.escape(previousId)}"]`)).forEach((label) => {
              if (!label.control || label.control === field) {label.setAttribute('for', candidateId);}
            });
          }
        }

        if ((field.hasAttribute('id') || field.hasAttribute('name')) && !field.hasAttribute('autocomplete')) {
          const autocompleteValue = resolveFormFieldAutocomplete(field);
          if (autocompleteValue) {field.setAttribute('autocomplete', autocompleteValue);}
        }
      });
    });
  }

  function auditFormFieldIssues(root = document) {
    if (!root || typeof root.querySelectorAll !== 'function') {return { missingIdOrName: 0, missingAutocomplete: 0, duplicateIds: [], brokenLabels: [] };}
    const scope = root.querySelectorAll ? root : document;
    const fields = Array.from(scope.querySelectorAll('form input, form select, form textarea'));
    const missingIdOrName = fields.filter((field) => !field.id && !field.name).length;
    const missingAutocomplete = fields.filter((field) => {
      if (!field.id && !field.name) {return false;}
      if (field.hasAttribute('autocomplete')) {return false;}
      return Boolean(resolveFormFieldAutocomplete(field));
    }).length;

    const idMap = new Map();
    Array.from(document.querySelectorAll('[id]')).forEach((node) => {
      const id = getElementIdAttribute(node);
      if (!id) {return;}
      if (!idMap.has(id)) {
        idMap.set(id, { count: 0, nodes: [] });
      }
      const entry = idMap.get(id);
      entry.count += 1;
      const tag = String(node.tagName || 'node').toLowerCase();
      const marker = node.className ? `${tag}#${id}.${String(node.className).trim().replace(/\s+/g, '.')}` : `${tag}#${id}`;
      if (entry.nodes.length < 4) {entry.nodes.push(marker);}
    });
    const duplicateIds = Array.from(idMap.entries())
      .filter(([, entry]) => entry.count > 1)
      .map(([id, entry]) => ({ id, count: entry.count, nodes: entry.nodes }));

    const brokenLabels = Array.from(document.querySelectorAll('label[for]')).filter((label) => {
      const targetId = String(label.getAttribute('for') || '').trim();
      if (!targetId) {return false;}
      return !document.getElementById(targetId);
    }).map((label) => label.getAttribute('for'));

    return { missingIdOrName, missingAutocomplete, duplicateIds, brokenLabels };
  }

  function setupFormFieldHardening() {
    if (globalThis.__EPI_FORM_FIELD_HARDENING_BOUND__) {return;}
    globalThis.__EPI_FORM_FIELD_HARDENING_BOUND__ = true;

    ensureFormFieldAttributes(document);
    const normalizedIdsOnBoot = normalizeInvalidDomIds(document);
    ensureFormFieldAttributes(document);
    if (normalizedIdsOnBoot.length && globalThis.__EPI_DEBUG_FORMS__) {console.warn('[forms] normalized invalid ids on boot', normalizedIdsOnBoot);}
    const observer = new MutationObserver((records) => {
      records.forEach((record) => {
        record.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) {return;}
          if (node.matches('form, input, select, textarea')) {
            ensureFormFieldAttributes(node.closest('form') || node);
            normalizeInvalidDomIds(node.closest('form') || document);
            return;
          }
          if (node.querySelector) {
            ensureFormFieldAttributes(node);
            normalizeInvalidDomIds(node);
          }
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    globalThis.__EPI_FORM_FIELD_HARDENING_OBSERVER__ = observer;

    const audit = auditFormFieldIssues(document);
    globalThis.__EPI_FORM_FIELD_AUDIT__ = audit;
    if (audit.missingIdOrName || audit.missingAutocomplete || audit.duplicateIds.length || audit.brokenLabels.length) {
      const duplicateIdNames = audit.duplicateIds.map((entry) => `${entry.id} (${entry.count}x)`).join(', ');
      const duplicateNodes = audit.duplicateIds.flatMap((entry) => {
        const escapedId = CSS.escape(String(entry.id || ''));
        return Array.from(document.querySelectorAll(`[id="${escapedId}"]`)).map((node) => ({
          duplicateId: entry.id,
          ...describeFieldNode(node)
        }));
      });
      console.warn('[forms] pending accessibility issues', {
        ...audit,
        duplicateIdsSummary: duplicateIdNames || 'none',
        duplicateNodes
      });
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  // Mesmos nomes globais de antes (Annex B do app.js); chamados pelo init do
  // app.js, por static/*.js legados e pelo console de diagnóstico.

  const formFieldIdentityExports = {
    isViewActive,
    resolveFormFieldAutocomplete,
    describeFieldNode,
    getElementIdAttribute,
    isValidDomId,
    toSafeId,
    setElementIdAttribute,
    normalizeInvalidDomIds,
    ensureFormFieldAttributes,
    auditFormFieldIssues,
    setupFormFieldHardening
  };

  for (const [name, fn] of Object.entries(formFieldIdentityExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_FORM_FIELD_IDENTITY__ = Object.freeze({ ...formFieldIdentityExports });
})();
