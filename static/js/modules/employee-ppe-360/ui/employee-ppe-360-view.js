'use strict';

// Ficha 360° de EPI — painel (F1, camada UI).
//
// Aberta pela linha do colaborador (modules/employees/ui/employees-view.js
// desenha o botão [data-employee-ppe360]); NADA no app.js. O painel é o modal
// estático #employee-ppe-360-modal (static/views/_modals.html), com foco,
// Escape e Tab pelos diálogos compartilhados (shared/ui/dialogs.js).
//
// Ciclo de vida, descarte de respostas obsoletas e invalidação por contexto
// são os da F0 (employee-ppe-360-lifecycle.js). Este arquivo só:
//  - liga o botão de abertura, fechar, atualizar e tentar de novo;
//  - fornece UM loader (o resumo — uma requisição por abertura);
//  - desenha os estados: carregando, pronto, erro e acesso negado.
// Texto sempre por textContent (nunca HTML montado com dado). Sem HTTP aqui.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_VIEW_LOADED__ = true;

  const MODAL_ID = 'employee-ppe-360-modal';
  const ROOT_ID = 'employee-ppe-360-root';
  // Telas que listam colaboradores e trazem a entrada da Ficha (a Ficha fecha
  // ao sair delas): Colaboradores (administradores estruturais) e Gestão do
  // colaborador (Administrador Local).
  const HOST_VIEWS = Object.freeze(['colaboradores', 'gestao-colaborador']);
  const DEFAULT_HOST_VIEW = HOST_VIEWS[0];
  const OPEN_ATTR = 'data-employee-ppe360';

  function lifecycle() { return globalThis.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__; }
  function rules() { return globalThis.__EPI_EMPLOYEE_PPE_360_SUMMARY__; }
  function contract() { return globalThis.__EPI_EMPLOYEE_PPE_360_BUSINESS__; }
  function integration() { return globalThis.__EPI_EMPLOYEE_PPE_360_API__; }
  function dialogs() { return globalThis.__EPI_SHARED_DIALOGS__ || {}; }
  function appState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function doc() { return globalThis.document; }
  function el(id) { return doc() ? doc().getElementById(id) : null; }
  function t(key, fallback, vars) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback, vars || {}) : fallback;
  }

  let openListeners = null;
  let lastPayload = null;

  // ── Helpers de DOM (sempre textContent) ───────────────────────────────────
  function h(tag, attrs, children) {
    const node = doc().createElement(tag);
    for (const [name, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) { continue; }
      if (name === 'className') { node.className = value; } else { node.setAttribute(name, value === true ? '' : String(value)); }
    }
    for (const child of [].concat(children || [])) {
      if (child === null || child === undefined || child === false) { continue; }
      node.append(typeof child === 'string' || typeof child === 'number' ? doc().createTextNode(String(child)) : child);
    }
    return node;
  }

  function locale() {
    const root = doc() && doc().documentElement;
    return (root && root.lang) || 'pt-BR';
  }

  function formatDate(iso) {
    if (!iso) { return ''; }
    try {
      return new Intl.DateTimeFormat(locale(), { dateStyle: 'short' }).format(new Date(`${iso}T00:00:00`));
    } catch (_e) {
      return iso;
    }
  }

  function todayIso() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }

  function employmentLabel(raw) {
    return typeof globalThis.employmentTypeLabel === 'function' ? globalThis.employmentTypeLabel(raw) : raw;
  }

  function roleLabel(role) {
    return t(`role.${role}`, role);
  }

  function statusLabel(code) {
    return t(`employee360.requestStatus.${code}`, code);
  }

  function permissions() {
    const perms = appState().permissions;
    return Array.isArray(perms) ? perms : [];
  }

  // ── Blocos ────────────────────────────────────────────────────────────────
  function meta(label, value) {
    return h('span', { className: 'ppe360-meta' }, [h('span', { className: 'ppe360-meta__label' }, `${label}: `), value || t('employee360.notInformed', 'Não informado')]);
  }

  function identityBlock(data) {
    const emp = data.employee || {};
    const unit = emp.unit || {};
    const lifecycleKey = emp.lifecycle === 'archived' ? 'archived' : 'active';
    const line1 = [
      meta(t('employee360.registration', 'Matrícula'), emp.registration),
      meta(t('employee360.jobTitle', 'Cargo'), emp.job_title),
      meta(t('employee360.unit', 'Unidade'), unit.name),
      meta(t('employee360.company', 'Empresa'), emp.company && emp.company.name)
    ];
    const line2 = [
      meta(t('employee360.employmentType', 'Vínculo'), employmentLabel(emp.employment_type)),
      h('span', { className: `badge ppe360-status ppe360-status--${lifecycleKey}` }, t(`employee360.lifecycle.${lifecycleKey}`, lifecycleKey === 'archived' ? 'Arquivado' : 'Ativo'))
    ];
    if (emp.legal_entity && emp.legal_entity.cnpj) {
      line2.push(meta(t('employee360.legalEntity', 'CNPJ empregador'), `${emp.legal_entity.name} · ${emp.legal_entity.cnpj}`));
    }
    const extra = [];
    if (unit.temporary_allocation) {
      extra.push(h('p', { className: 'hint ppe360-note' }, t('employee360.temporaryAllocation', 'Alocação temporária (unidade base: {unit})', { unit: unit.base_unit_name || '-' })));
    }
    const contracted = rules().contractedView(emp.contracted_workforce);
    if (contracted) {
      const rows = [
        meta(t('employee360.contracted.company', 'Empresa terceirizada'), contracted.companyName || contracted.originName),
        meta(t('employee360.contracted.cnpj', 'CNPJ'), contracted.companyCnpj),
        contracted.hasContract
          ? meta(t('employee360.contracted.contract', 'Contrato'), [contracted.contractRef, contracted.contractStart || contracted.contractEnd
            ? t('employee360.contracted.period', '{start} a {end}', { start: formatDate(contracted.contractStart) || '-', end: formatDate(contracted.contractEnd) || '-' }) : ''].filter(Boolean).join(' · '))
          : meta(t('employee360.contracted.contract', 'Contrato'), t('employee360.contracted.noContract', 'Sem contrato vinculado'))
      ];
      extra.push(h('div', { className: 'ppe360-meta-row ppe360-contracted', 'aria-label': t('employee360.contracted.title', 'Terceirizado') }, rows));
    }
    return h('section', { className: 'ppe360-identity', 'aria-labelledby': 'ppe360-employee-name' }, [
      h('div', { className: 'ppe360-avatar', 'aria-hidden': 'true' }, '👤'),
      h('div', { className: 'ppe360-identity__body' }, [
        h('h3', { id: 'ppe360-employee-name', className: 'ppe360-identity__name' }, emp.name || '-'),
        h('div', { className: 'ppe360-meta-row' }, line1),
        h('div', { className: 'ppe360-meta-row' }, line2),
        ...extra
      ])
    ]);
  }

  function responsiblesBlock(data) {
    const groups = rules().responsibleGroups(data.responsibles);
    const list = (items) => (items.length
      ? h('ul', { className: 'ppe360-people' }, items.map((p) => h('li', null, [h('strong', null, p.name), ` · ${roleLabel(p.role)}`])))
      : h('p', { className: 'hint' }, t('employee360.responsibles.none', 'Nenhum responsável cadastrado')));
    return h('section', { className: 'ppe360-responsibles', 'aria-labelledby': 'ppe360-resp-title' }, [
      h('h4', { id: 'ppe360-resp-title' }, t('employee360.responsibles.title', 'Responsáveis')),
      h('p', { className: 'hint ppe360-note' }, t('employee360.responsibles.note', 'Responsáveis pelo papel na unidade e na empresa. Não há gestor direto vinculado ao colaborador.')),
      h('div', { className: 'ppe360-resp-grid' }, [
        h('div', null, [h('h5', null, t('employee360.responsibles.unit', 'Unidade')), list(groups.unit)]),
        h('div', null, [h('h5', null, t('employee360.responsibles.company', 'Empresa')), list(groups.company)])
      ])
    ]);
  }

  function card(id, icon, title, valueNode, detailNodes, extraClass) {
    return h('article', { className: `ppe360-card ${extraClass || ''}`.trim(), 'data-ppe360-card': id, 'aria-labelledby': `ppe360-card-${id}` }, [
      h('h4', { id: `ppe360-card-${id}`, className: 'ppe360-card__title' }, [h('span', { 'aria-hidden': 'true' }, `${icon} `), title]),
      h('div', { className: 'ppe360-card__value' }, valueNode),
      ...[].concat(detailNodes || [])
    ]);
  }

  function indicatorCards(data) {
    const r = rules();
    const ind = data.indicators;
    const cards = [];
    if (!ind) {
      cards.push(h('p', { className: 'hint ppe360-cards__forbidden', role: 'note' }, t('employee360.indicators.forbidden', 'Indicadores indisponíveis para o seu perfil.')));
    } else {
      const pending = r.pendingView(ind.pending_requests);
      cards.push(card('pending', '⏱', t('employee360.indicators.pending', 'Pendentes'),
        pending.empty ? '—' : String(pending.total),
        pending.empty
          ? h('p', { className: 'hint' }, t('employee360.indicators.pendingNone', 'Nenhuma solicitação pendente'))
          : h('ul', { className: 'ppe360-breakdown', 'aria-label': t('employee360.indicators.pendingBreakdown', 'Pendências por situação') },
            pending.items.map((item) => h('li', { 'data-status': item.code }, [h('strong', null, String(item.count)), ` ${statusLabel(item.code)}`])))));
      const next = r.nextReplacementView(ind.next_replacement, todayIso());
      const overdue = next.empty || !next.overdueCount ? null
        : h('p', { className: 'ppe360-alert' }, t(next.overdueCount === 1 ? 'employee360.indicators.overdueOne' : 'employee360.indicators.overdueMany',
          next.overdueCount === 1 ? '1 troca vencida' : '{count} trocas vencidas', { count: next.overdueCount }));
      cards.push(card('next', '📅', t('employee360.indicators.nextReplacement', 'Próxima troca'),
        next.empty ? '—' : formatDate(next.date),
        next.empty ? h('p', { className: 'hint' }, t('employee360.indicators.nextNone', 'Sem data de troca registrada'))
          : [h('p', { className: 'hint' }, next.epiName), overdue], next.isOverdue ? 'ppe360-card--alert' : ''));
      const use = r.inUseView(ind.in_use);
      cards.push(card('in-use', '🛡', t('employee360.indicators.inUse', 'Em uso'),
        use.empty ? '—' : String(use.units),
        use.empty ? h('p', { className: 'hint' }, t('employee360.indicators.inUseNone', 'Nenhum EPI em uso'))
          : [h('p', { className: 'hint' }, t('employee360.indicators.inUseDetail', '{units} un. · {products} produtos · {categories} categorias', use)),
            use.uncategorized ? h('p', { className: 'hint' }, t('employee360.indicators.uncategorized', '{count} sem categoria', { count: use.uncategorized })) : null]));
    }
    if (r.canSeeFinance(permissions())) {
      for (const item of r.FINANCE_CARDS) {
        cards.push(card(`finance-${item.id}`, '💼', t(item.label, item.fallback),
          t('employee360.unavailable', 'Indisponível'),
          h('p', { className: 'hint' }, t('employee360.nextStage', 'Disponível em uma próxima etapa')), 'ppe360-card--unavailable'));
      }
    }
    return h('section', { className: 'ppe360-cards', 'aria-label': t('employee360.indicators.title', 'Indicadores') }, cards);
  }

  function futureBlock(block, withHint) {
    return h('article', { className: 'ppe360-block ppe360-block--unavailable', 'data-ppe360-block': block.id, 'aria-disabled': 'true' }, [
      h('h4', null, t(block.label, block.fallback)),
      withHint && block.hintLabel ? h('p', { className: 'hint' }, t(block.hintLabel, block.hint)) : null,
      h('span', { className: 'badge ppe360-soon' }, t('employee360.nextStage', 'Disponível em uma próxima etapa'))
    ]);
  }

  function panelBlocks() {
    const r = rules();
    const perms = permissions();
    return [
      h('section', { className: 'ppe360-central', 'aria-label': t('employee360.blocks.centralTitle', 'Painel central') }, [
        h('article', { className: 'ppe360-block ppe360-block--unavailable ppe360-bodymap', 'data-ppe360-block': 'body-map', 'aria-disabled': 'true' }, [
          h('div', { className: 'ppe360-bodymap__icon', 'aria-hidden': 'true' }, '👤'),
          h('h4', null, t('employee360.blocks.bodyMap', 'Mapa corporal de EPIs')),
          h('span', { className: 'badge ppe360-soon' }, t('employee360.nextStage', 'Disponível em uma próxima etapa'))
        ]),
        h('div', { className: 'ppe360-central__list' }, r.futureBlocks('central', perms).map((b) => futureBlock(b, true)))
      ]),
      h('section', { className: 'ppe360-complementary', 'aria-label': t('employee360.blocks.complementaryTitle', 'Áreas complementares') },
        r.futureBlocks('complementary', perms).map((b) => futureBlock(b, false)))
    ];
  }

  // ── Estados ───────────────────────────────────────────────────────────────
  function stateMessage(kind, text, withRetry) {
    return h('div', { className: `ppe360-state ppe360-state--${kind}`, role: kind === 'error' ? 'alert' : 'status' }, [
      h('p', null, text),
      withRetry ? h('button', { type: 'button', className: 'primary', 'data-ppe360-action': 'retry' }, t('employee360.retry', 'Tentar novamente')) : null
    ]);
  }

  function render(payload) {
    lastPayload = payload;
    const root = el(ROOT_ID);
    if (!root) { return; }
    const states = contract().SECTION_STATES;
    root.setAttribute('aria-busy', payload.state === states.LOADING ? 'true' : 'false');
    let content;
    if (payload.state === states.LOADING) {
      content = stateMessage('loading', t('employee360.loading', 'Carregando a Ficha 360°…'), false);
    } else if (payload.state === states.FORBIDDEN) {
      content = stateMessage('forbidden', t('employee360.forbidden', 'Você não tem acesso à Ficha 360° deste colaborador.'), false);
    } else if (payload.state === states.READY && payload.result && payload.result.data) {
      const data = payload.result.data;
      content = h('div', { className: 'ppe360-layout' }, [identityBlock(data), indicatorCards(data), responsiblesBlock(data), ...panelBlocks()]);
    } else {
      content = stateMessage('error', t('employee360.error', 'Não foi possível carregar a Ficha 360°.'), true);
    }
    root.replaceChildren(content);
  }

  // ── Abertura e fechamento ────────────────────────────────────────────────
  function closeShell() {
    if (openListeners) { openListeners.abort(); openListeners = null; }
    lastPayload = null;
    const modal = el(MODAL_ID);
    if (modal && !modal.hidden && typeof dialogs().closeModal === 'function') { dialogs().closeModal(modal); }
  }

  function close() {
    const life = lifecycle();
    if (life) { life.unmountEmployeePpe360('close'); }
    closeShell();
  }

  function bindOpenListeners(modal) {
    openListeners = new AbortController();
    const signal = openListeners.signal;
    modal.addEventListener('click', (event) => {
      const target = event.target;
      if (target === modal) { close(); return; }
      const action = target && target.closest ? target.closest('[data-ppe360-action]') : null;
      if (!action) { return; }
      const kind = action.getAttribute('data-ppe360-action');
      if (kind === 'close') { close(); } else if (kind === 'refresh' || kind === 'retry') { lifecycle().refreshEmployeePpe360(); }
    }, { signal });
    globalThis.addEventListener('epi:langchange', () => { if (lastPayload) { render(lastPayload); } }, { signal });
  }

  function hostViewOf(trigger) {
    const section = trigger && trigger.closest ? trigger.closest('section.view[id$="-view"]') : null;
    const name = section ? section.id.replace(/-view$/, '') : '';
    return HOST_VIEWS.includes(name) ? name : DEFAULT_HOST_VIEW;
  }

  function open(employeeId, options) {
    const life = lifecycle();
    const modal = el(MODAL_ID);
    const root = el(ROOT_ID);
    const user = appState().user;
    if (!life || !modal || !root || !rules().canOpen(user, permissions())) { return Promise.resolve({ ok: false, reason: 'UNAVAILABLE' }); }
    if (openListeners) { openListeners.abort(); }
    bindOpenListeners(modal);
    if (typeof dialogs().openModal === 'function') { dialogs().openModal(modal); } else { modal.hidden = false; }
    if (typeof dialogs().bindModalKeyboard === 'function') { dialogs().bindModalKeyboard(modal, close); }
    return life.mountEmployeePpe360({
      employeeId,
      container: root,
      hostView: HOST_VIEWS.includes((options || {}).hostView) ? options.hostView : DEFAULT_HOST_VIEW,
      sections: { summary: ({ employeeId: id }) => integration().loadSummary(id, user.id) },
      render,
      // Desmontagem por contexto/navegação fecha a casca; troca de colaborador não.
      onUnmount: (reason) => { if (!['replaced', 'switch-employee', 'close'].includes(reason)) { closeShell(); } }
    });
  }

  // Botão na linha do colaborador (desenhado por employees-view.js).
  function openButtonHtml(employeeId, employeeName) {
    if (!rules().canOpen(appState().user, permissions())) { return ''; }
    const id = contract().normalizeEmployeeId(employeeId);
    if (!id) { return ''; }
    const escape = (v) => String(v ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    const label = escape(t('employee360.openFor', 'Abrir Ficha 360° de {name}', { name: employeeName || '' }));
    return `<button type="button" class="ghost ppe360-open" ${OPEN_ATTR}="${id}" aria-label="${label}">${escape(t('employee360.open', 'Ficha 360°'))}</button>`;
  }

  const moduleListeners = new AbortController();
  if (doc() && typeof doc().addEventListener === 'function') {
    doc().addEventListener('click', (event) => {
      const trigger = event.target && event.target.closest ? event.target.closest(`[${OPEN_ATTR}]`) : null;
      if (!trigger) { return; }
      event.preventDefault();
      open(trigger.getAttribute(OPEN_ATTR), { hostView: hostViewOf(trigger) });
    }, { signal: moduleListeners.signal });
  }

  globalThis.__EPI_EMPLOYEE_PPE_360_VIEW__ = Object.freeze({ open, close, render, openButtonHtml });
})();
