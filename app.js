
const SESSION_KEY = 'epi-session-v4';
const SESSION_PERMISSIONS_KEY = 'epi-session-v4-permissions';
const ROLE_LABELS = {
  general_admin: 'Administrador Geral',
  admin: 'Administrador',
  user: 'Usuário'
};
const ROLE_PERMISSIONS = {
  general_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view'],
  admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view'],
  user: ['dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'alerts:view', 'companies:view', 'units:view', 'employees:view', 'epis:view']
};
const VIEW_PERMISSIONS = {
  dashboard: 'dashboard:view',
  usuarios: 'users:view',
  unidades: 'units:view',
  colaboradores: 'employees:view',
  epis: 'epis:view',
  entregas: 'deliveries:view',
  fichas: 'fichas:view',
  relatorios: 'reports:view'
};

const state = {
  user: JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'),
  permissions: JSON.parse(localStorage.getItem(SESSION_PERMISSIONS_KEY) || '[]'),
  companies: [], users: [], units: [], employees: [], epis: [], deliveries: [], alerts: [], reports: null,
  editingUserId: null,
  userFilters: { company_id: '', role: '', active: '', search: '' }
};

const refs = {
  loginScreen: document.getElementById('login-screen'),
  mainScreen: document.getElementById('main-screen'),
  loginForm: document.getElementById('login-form'),
  profileLabel: document.getElementById('profile-label'),
  companyBadge: document.getElementById('company-badge'),
  viewTitle: document.getElementById('view-title'),
  currentDate: document.getElementById('current-date'),
  statsGrid: document.getElementById('stats-grid'),
  alertsList: document.getElementById('alerts-list'),
  latestDeliveries: document.getElementById('latest-deliveries'),
  usersTable: document.getElementById('users-table'),
  unitsTable: document.getElementById('units-table'),
  employeesTable: document.getElementById('employees-table'),
  episTable: document.getElementById('epis-table'),
  deliveriesTable: document.getElementById('deliveries-table'),
  fichaView: document.getElementById('ficha-view'),
  fichaEmployee: document.getElementById('ficha-employee'),
  reportSummary: document.getElementById('report-summary'),
  reportUnits: document.getElementById('report-units'),
  reportSectors: document.getElementById('report-sectors'),
  userForm: document.getElementById('user-form'),
  userRole: document.getElementById('user-role'),
  userFilterCompany: document.getElementById('user-filter-company'),
  userFilterRole: document.getElementById('user-filter-role'),
  userFilterStatus: document.getElementById('user-filter-status'),
  userFilterSearch: document.getElementById('user-filter-search'),
  usersSummary: document.getElementById('users-summary')
};

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Falha na requisição.');
  return payload;
}

function normalizePermissions(user, permissions = []) {
  const fallback = ROLE_PERMISSIONS[user?.role] || [];
  return [...new Set([...(permissions || []), ...fallback])];
}

function saveSession(user, permissions = []) {
  state.user = user;
  state.permissions = normalizePermissions(user, permissions);
  localStorage.setItem(SESSION_KEY, JSON.stringify(user));
  localStorage.setItem(SESSION_PERMISSIONS_KEY, JSON.stringify(state.permissions));
}

function clearSession() {
  state.user = null;
  state.permissions = [];
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(SESSION_PERMISSIONS_KEY);
}

function hasPermission(permission) {
  const activePermissions = state.permissions.length ? state.permissions : normalizePermissions(state.user, []);
  return activePermissions.includes(permission);
}

function requirePermission(permission, message = 'Você não tem permissão para acessar esta área.') {
  if (!hasPermission(permission)) {
    alert(message);
    return false;
  }
  return true;
}

function actorQuery() {
  return `actor_user_id=${encodeURIComponent(state.user?.id || '')}`;
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('pt-BR').format(new Date(`${value}T00:00:00`)) : '-';
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function showScreen(authenticated) {
  refs.loginScreen.classList.toggle('active', !authenticated);
  refs.mainScreen.classList.toggle('active', authenticated);
}

function roleLabel(role) {
  return ROLE_LABELS[role] || role;
}

function activeLabel(active) {
  return Number(active) === 1 ? 'Ativo' : 'Inativo';
}

function renderBadge(type, value, label) {
  return `<span class="badge badge-${type}-${value}">${label}</span>`;
}

function filterByUserCompany(items) {
  if (!state.user || state.user.role === 'general_admin') return items;
  return items.filter((item) => String(item.company_id || '') === String(state.user.company_id || ''));
}

function accessibleViews() {
  return Object.entries(VIEW_PERMISSIONS).filter(([, permission]) => hasPermission(permission)).map(([view]) => view);
}

function defaultView() {
  const ordered = ['dashboard', 'entregas', 'fichas', 'usuarios', 'unidades', 'colaboradores', 'epis', 'relatorios'];
  return ordered.find((view) => hasPermission(VIEW_PERMISSIONS[view])) || 'dashboard';
}

function showView(view) {
  const permission = VIEW_PERMISSIONS[view];
  if (permission && !hasPermission(permission)) {
    alert('Seu perfil não pode acessar esta área.');
    view = defaultView();
  }
  document.querySelectorAll('.view').forEach((item) => item.classList.remove('active'));
  document.querySelectorAll('.menu-link').forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  document.getElementById(`${view}-view`).classList.add('active');
  refs.viewTitle.textContent = document.querySelector(`.menu-link[data-view="${view}"]`).textContent;
}

function applyRoleVisibility() {
  document.querySelectorAll('.menu-link').forEach((item) => {
    item.style.display = hasPermission(VIEW_PERMISSIONS[item.dataset.view]) ? '' : 'none';
  });
  refs.profileLabel.textContent = state.user ? roleLabel(state.user.role) : 'Perfil';
  refs.companyBadge.textContent = state.user?.company_name ? `${state.user.company_name} • ${state.user.company_cnpj}` : 'Acesso geral';
}

function populateRoleOptions() {
  const roles = state.user?.role === 'general_admin' ? [['admin', 'Administrador'], ['user', 'Usuário']] : [['user', 'Usuário']];
  refs.userRole.innerHTML = roles.map((item) => `<option value="${item[0]}">${item[1]}</option>`).join('');
}

function populateUserFilters() {
  if (!refs.userFilterCompany) return;
  const companies = state.user?.role === 'general_admin' ? state.companies : filterByUserCompany(state.companies);
  refs.userFilterCompany.innerHTML = `<option value="">Todas</option>${companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('')}`;
  refs.userFilterCompany.value = state.userFilters.company_id;
  refs.userFilterRole.value = state.userFilters.role;
  refs.userFilterStatus.value = state.userFilters.active;
  refs.userFilterSearch.value = state.userFilters.search;
}

function renderUsersSummary() {
  const visible = filteredUsers();
  const admins = visible.filter((item) => item.role === 'admin' || item.role === 'general_admin').length;
  const active = visible.filter((item) => Number(item.active) === 1).length;
  refs.usersSummary.innerHTML = [
    ['Vis?veis', visible.length],
    ['Administradores', admins],
    ['Ativos', active]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function filteredUsers() {
  return filterByUserCompany(state.users).filter((item) => {
    if (state.userFilters.company_id && String(item.company_id || '') !== String(state.userFilters.company_id)) return false;
    if (state.userFilters.role && item.role !== state.userFilters.role) return false;
    if (state.userFilters.active !== '' && String(Number(item.active)) !== String(state.userFilters.active)) return false;
    if (state.userFilters.search) {
      const haystack = `${item.full_name} ${item.username} ${item.company_name || ''}`.toLowerCase();
      if (!haystack.includes(state.userFilters.search)) return false;
    }
    return true;
  });
}

async function loadBootstrap() {
  try {
    const payload = await api(`/api/bootstrap?${actorQuery()}`);
    state.companies = payload.companies;
    state.users = payload.users;
    state.units = payload.units;
    state.employees = payload.employees;
    state.epis = payload.epis;
    state.deliveries = payload.deliveries;
    state.alerts = payload.alerts;
    state.permissions = normalizePermissions(state.user, payload.permissions || state.permissions);
    renderAll();
  } catch (error) {
    clearSession();
    showScreen(false);
    throw error;
  }
}

function populateSelect(selectId, items, labelBuilder, valueKey = 'id', includeEmpty = false, emptyLabel = 'Selecione') {
  const select = document.getElementById(selectId);
  const filtered = filterByUserCompany(items);
  select.innerHTML = `${includeEmpty ? `<option value="">${emptyLabel}</option>` : ''}${filtered.map((item) => `<option value="${item[valueKey]}">${labelBuilder(item)}</option>`).join('')}`;
}

function bindDependentSelects() {
  const companies = state.user?.role === 'general_admin' ? state.companies : filterByUserCompany(state.companies);
  populateSelect('user-company', companies, (item) => `${item.name} - ${item.cnpj}`, 'id', true, 'Sem vínculo');
  populateSelect('unit-company', companies, (item) => `${item.name} - ${item.logo_type}`);
  populateSelect('employee-company', companies, (item) => `${item.name} - ${item.logo_type}`);
  populateSelect('epi-company', companies, (item) => `${item.name} - ${item.logo_type}`);
  populateSelect('delivery-company', companies, (item) => `${item.name} - ${item.logo_type}`);
  populateSelect('report-company', companies, (item) => item.name, 'id', true, 'Todas');
  populateSelect('employee-unit', state.units, (item) => `${item.name} - ${item.unit_type}`);
  populateSelect('delivery-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-epi', state.epis, (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('ficha-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('report-unit', state.units, (item) => item.name, 'id', true, 'Todas');
  populateSelect('report-epi', state.epis, (item) => item.name, 'id', true, 'Todos');
  const sectors = [...new Set(filterByUserCompany(state.employees).map((item) => item.sector))].sort();
  document.getElementById('report-sector').innerHTML = `<option value="">Todos</option>${sectors.map((item) => `<option value="${item}">${item}</option>`).join('')}`;
}

function renderStats() {
  const cards = [['Empresas', filterByUserCompany(state.companies).length], ['Colaboradores', filterByUserCompany(state.employees).length], ['EPIs', filterByUserCompany(state.epis).length], ['Entregas', filterByUserCompany(state.deliveries).length], ['Alertas', filterByUserCompany(state.alerts).length]];
  refs.statsGrid.innerHTML = cards.map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
}

function canManageUser(target) {
  if (!hasPermission('users:update')) return false;
  if (state.user.role === 'general_admin') return target.role !== 'general_admin';
  if (state.user.role === 'admin') return target.role === 'user' && String(target.company_id || '') === String(state.user.company_id || '');
  return false;
}
function canPromoteToAdmin(target) { return state.user?.role === 'general_admin' && target.role === 'user'; }
function canDemoteAdmin(target) { return state.user?.role === 'general_admin' && target.role === 'admin'; }
function canToggleActive(target) { return canManageUser(target) && String(target.id) !== String(state.user?.id || ''); }

function userActionButtons(target) {
  if (!canManageUser(target)) return '-';
  const actions = [`<button class="ghost" data-user-edit="${target.id}">Editar</button>`];
  if (canPromoteToAdmin(target)) actions.push(`<button class="ghost" data-user-promote="${target.id}">Tornar Administrador</button>`);
  if (canDemoteAdmin(target)) actions.push(`<button class="ghost" data-user-demote="${target.id}">Remover da Administração</button>`);
  if (canToggleActive(target)) {
    actions.push(`<button class="ghost" data-user-toggle="${target.id}">${Number(target.active) === 1 ? 'Desativar Usuário' : 'Reativar Usuário'}</button>`);
    actions.push(`<button class="ghost" data-user-delete="${target.id}">Remover</button>`);
  }
  return `<div class="action-group">${actions.join('')}</div>`;
}

function startEditUser(userId) {
  const user = state.users.find((item) => String(item.id) === String(userId));
  if (!user) return;
  state.editingUserId = user.id;
  refs.userForm.elements.id.value = user.id;
  refs.userForm.elements.full_name.value = user.full_name;
  refs.userForm.elements.username.value = user.username;
  refs.userForm.elements.password.value = '';
  populateRoleOptions();
  refs.userForm.elements.role.value = canManageUser(user) ? user.role : refs.userRole.value;
  refs.userForm.elements.company_id.value = user.company_id || '';
}

async function updateUserAccess(userId, changes, successMessage = '') {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  try {
    await api(`/api/users/${userId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, username: target.username, full_name: target.full_name, password: '', role: changes.role || target.role, company_id: changes.company_id === undefined ? target.company_id : changes.company_id, active: changes.active === undefined ? target.active : changes.active }) });
    if (successMessage) alert(successMessage);
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function deleteUser(userId) {
  if (!window.confirm('Deseja remover este usuário?')) return;
  try {
    await api(`/api/users/${userId}?${actorQuery()}`, { method: 'DELETE' });
    if (String(state.editingUserId || '') === String(userId)) resetUserForm();
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

function resetUserForm() {
  state.editingUserId = null;
  refs.userForm.reset();
  refs.userForm.elements.id.value = '';
  populateRoleOptions();
  if (state.user?.role === 'admin') refs.userForm.elements.company_id.value = state.user.company_id || '';
}

function renderAlerts() { refs.alertsList.innerHTML = filterByUserCompany(state.alerts).map((item) => `<div class="alert-item ${item.type}"><strong>${item.title}</strong><div>${item.description}</div></div>`).join('') || '<div class="summary-item">Sem alertas.</div>'; }
function renderLatestDeliveries() { refs.latestDeliveries.innerHTML = filterByUserCompany(state.deliveries).slice(0, 5).map((item) => `<div class="list-item"><strong>${item.employee_name}</strong><div>${item.epi_name} - ${item.quantity} ${item.quantity_label}(s)</div><small>${item.company_name} • ${formatDate(item.delivery_date)}</small></div>`).join('') || '<div class="summary-item">Sem entregas.</div>'; }

function renderTables() {
  refs.usersTable.innerHTML = filteredUsers().map((item) => `<tr><td>${item.full_name}</td><td>${renderBadge('role', item.role, roleLabel(item.role))}</td><td>${renderBadge('status', Number(item.active) === 1 ? 'active' : 'inactive', activeLabel(item.active))}</td><td>${item.company_name || 'Geral'}</td><td>${userActionButtons(item)}</td></tr>`).join('') || '<tr><td colspan="5">Sem usuários.</td></tr>';
  refs.unitsTable.innerHTML = filterByUserCompany(state.units).map((item) => `<tr><td>${item.company_name}</td><td>${item.name}</td><td>${item.unit_type}</td><td>${item.city}</td></tr>`).join('') || '<tr><td colspan="4">Sem unidades.</td></tr>';
  refs.employeesTable.innerHTML = filterByUserCompany(state.employees).map((item) => `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${item.unit_name}</td></tr>`).join('') || '<tr><td colspan="6">Sem colaboradores.</td></tr>';
  refs.episTable.innerHTML = filterByUserCompany(state.epis).map((item) => `<tr><td>${item.company_name}</td><td>${item.name}</td><td>${item.purchase_code}</td><td>${item.sector}</td><td>${item.stock}</td><td>${item.unit_measure}</td></tr>`).join('') || '<tr><td colspan="6">Sem EPIs.</td></tr>';
  refs.deliveriesTable.innerHTML = filterByUserCompany(state.deliveries).map((item) => `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.employee_name}</td><td>${item.epi_name}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td></tr>`).join('') || '<tr><td colspan="7">Sem entregas.</td></tr>';
}

function renderFicha() {
  const filteredEmployees = filterByUserCompany(state.employees);
  const employeeId = refs.fichaEmployee.value || filteredEmployees[0]?.id;
  const employee = filteredEmployees.find((item) => String(item.id) === String(employeeId));
  if (!employee) { refs.fichaView.innerHTML = '<div class="summary-item">Nenhum colaborador disponível.</div>'; return; }
  refs.fichaEmployee.value = employee.id;
  const deliveries = filterByUserCompany(state.deliveries).filter((item) => String(item.employee_id) === String(employee.id));
  refs.fichaView.innerHTML = `<div class="summary-item"><strong>Empresa:</strong> ${employee.company_name} (${employee.company_cnpj})</div><div class="summary-item"><strong>Logo tipo:</strong> ${employee.logo_type}</div><div class="summary-item"><strong>Colaborador:</strong> ${employee.name}</div><div class="summary-item"><strong>ID:</strong> ${employee.employee_id_code}</div><div class="summary-item"><strong>SETOR:</strong> ${employee.sector}</div><div class="summary-item"><strong>Função:</strong> ${employee.role_name}</div><div class="summary-item"><strong>Escala:</strong> ${employee.schedule_type}</div><div class="table-wrap"><table><thead><tr><th>EPI</th><th>Código</th><th>Qtd</th><th>Medida</th><th>Entrega</th><th>Assinatura</th><th>Fabricação</th><th>Validade</th></tr></thead><tbody>${deliveries.map((item) => `<tr><td>${item.epi_name}</td><td>${item.purchase_code}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td><td>${item.signature_name}</td><td>${formatDate(item.manufacture_date)}</td><td>${formatDate(item.epi_validity_date)}</td></tr>`).join('') || '<tr><td colspan="8">Sem itens nesta ficha.</td></tr>'}</tbody></table></div>`;
}

async function renderReports(filters = null) {
  if (!hasPermission('reports:view')) return;
  const params = new URLSearchParams({ ...(filters || {}), actor_user_id: state.user.id });
  state.reports = await api(`/api/reports?${params.toString()}`);
  refs.reportSummary.innerHTML = `<div class="summary-item"><strong>Entregas:</strong> ${state.reports.deliveries.length}</div><div class="summary-item"><strong>Total entregue:</strong> ${state.reports.total_quantity}</div>`;
  refs.reportUnits.innerHTML = Object.entries(state.reports.by_unit).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || '<div class="summary-item">Sem dados.</div>';
  refs.reportSectors.innerHTML = Object.entries(state.reports.by_sector).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || '<div class="summary-item">Sem dados.</div>';
}

function refreshDeliveryContext() {
  const employee = state.employees.find((item) => String(item.id) === String(document.getElementById('delivery-employee').value));
  const epi = state.epis.find((item) => String(item.id) === String(document.getElementById('delivery-epi').value));
  document.getElementById('delivery-employee-code').value = employee?.employee_id_code || '';
  document.getElementById('delivery-sector').value = employee?.sector || '';
  document.getElementById('delivery-role').value = employee?.role_name || '';
  document.getElementById('delivery-unit-measure').value = epi?.unit_measure || '';
}

function renderAll() {
  refs.currentDate.textContent = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date());
  applyRoleVisibility();
  populateRoleOptions();
  populateUserFilters();
  bindDependentSelects();
  renderStats();
  renderAlerts();
  renderLatestDeliveries();
  renderTables();
  renderFicha();
  renderReports();
  refreshDeliveryContext();
  if (state.user?.role === 'admin') refs.userForm.elements.company_id.value = state.user.company_id || '';
  showView(defaultView());
}

async function handleLogin(event) {
  event.preventDefault();
  try {
    const payload = await api('/api/login', { method: 'POST', body: JSON.stringify({ username: document.getElementById('username').value.trim(), password: document.getElementById('password').value.trim() }) });
    saveSession(payload.user, payload.permissions || []);
    showScreen(true);
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function saveUser(event) {
  event.preventDefault();
  if (!requirePermission(state.editingUserId ? 'users:update' : 'users:create')) return;
  try {
    const values = formValues(refs.userForm);
    values.actor_user_id = state.user.id;
    if (state.user.role === 'admin') values.company_id = state.user.company_id;
    await api(state.editingUserId ? `/api/users/${state.editingUserId}` : '/api/users', { method: state.editingUserId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    resetUserForm();
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function saveSimpleForm(event, path, permission) {
  event.preventDefault();
  if (!requirePermission(permission)) return;
  try {
    const values = formValues(event.target);
    values.actor_user_id = state.user.id;
    if (state.user?.role !== 'general_admin' && values.company_id !== undefined && !values.company_id) values.company_id = state.user.company_id;
    await api(path, { method: 'POST', body: JSON.stringify(values) });
    event.target.reset();
    if (event.target.id === 'delivery-form') {
      event.target.elements.delivery_date.value = new Date().toISOString().split('T')[0];
      event.target.elements.next_replacement_date.value = new Date().toISOString().split('T')[0];
    }
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

function syncUserFilters() { state.userFilters.company_id = refs.userFilterCompany.value; state.userFilters.role = refs.userFilterRole.value; state.userFilters.active = refs.userFilterStatus.value; state.userFilters.search = refs.userFilterSearch.value.trim().toLowerCase(); renderTables(); }

async function init() {
  refs.loginForm.addEventListener('submit', handleLogin);
  refs.userForm.addEventListener('submit', saveUser);
  document.getElementById('unit-form').addEventListener('submit', (event) => saveSimpleForm(event, '/api/units', 'units:create'));
  document.getElementById('employee-form').addEventListener('submit', (event) => saveSimpleForm(event, '/api/employees', 'employees:create'));
  document.getElementById('epi-form').addEventListener('submit', (event) => saveSimpleForm(event, '/api/epis', 'epis:create'));
  document.getElementById('delivery-form').addEventListener('submit', (event) => saveSimpleForm(event, '/api/deliveries', 'deliveries:create'));
  document.getElementById('delivery-employee').addEventListener('change', refreshDeliveryContext);
  document.getElementById('delivery-epi').addEventListener('change', refreshDeliveryContext);
  refs.fichaEmployee.addEventListener('change', renderFicha);
  document.getElementById('report-filter-form').addEventListener('submit', async (event) => { event.preventDefault(); if (!requirePermission('reports:view')) return; await renderReports(formValues(event.target)); });
  document.getElementById('logout-btn').addEventListener('click', () => { clearSession(); showScreen(false); });
  document.querySelectorAll('.menu-link').forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)));
  refs.userFilterCompany?.addEventListener('change', syncUserFilters);
  refs.userFilterRole?.addEventListener('change', syncUserFilters);
  refs.userFilterStatus?.addEventListener('change', syncUserFilters);
  refs.userFilterSearch?.addEventListener('input', syncUserFilters);
  refs.usersTable?.addEventListener('click', (event) => {
    if (event.target.dataset.userEdit) startEditUser(event.target.dataset.userEdit);
    if (event.target.dataset.userDelete) deleteUser(event.target.dataset.userDelete);
    if (event.target.dataset.userPromote) updateUserAccess(event.target.dataset.userPromote, { role: 'admin' }, 'Usuário promovido para Administrador.');
    if (event.target.dataset.userDemote) updateUserAccess(event.target.dataset.userDemote, { role: 'user' }, 'Administrador removido da administração.');
    if (event.target.dataset.userToggle) {
      const target = state.users.find((item) => String(item.id) === String(event.target.dataset.userToggle));
      if (target) updateUserAccess(target.id, { active: Number(target.active) === 1 ? 0 : 1 }, Number(target.active) === 1 ? 'Usuário desativado.' : 'Usuário reativado.');
    }
  });
  document.querySelector('#delivery-form input[name="delivery_date"]').value = new Date().toISOString().split('T')[0];
  document.querySelector('#delivery-form input[name="next_replacement_date"]').value = new Date().toISOString().split('T')[0];
  showScreen(Boolean(state.user));
  if (state.user) await loadBootstrap();
}

init();

