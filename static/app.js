
const SESSION_KEY = 'epi-session-v4';
const SESSION_PERMISSIONS_KEY = 'epi-session-v4-permissions';
const SESSION_TOKEN_KEY = 'epi-session-v4-token';
const ROLE_LABELS = {
  master_admin: 'Administrador Master',
  general_admin: 'Administrador Geral',
  registry_admin: 'Administrador de Registro',
  admin: 'Administrador Local',
  user: 'Gestor de EPI',
  employee: 'Funcionário'
};
const ROLE_PERMISSIONS = {
  master_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'companies:create', 'companies:update', 'companies:license', 'commercial:view', 'usage:view', 'stock:view', 'stock:adjust'],
  general_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'stock:view', 'stock:adjust'],
  registry_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view'],
  admin: ['dashboard:view', 'users:view', 'units:view', 'employees:view', 'employees:update', 'epis:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view', 'stock:adjust'],
  user: ['dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'alerts:view', 'units:view', 'employees:view', 'epis:view', 'stock:view', 'stock:adjust'],
  employee: []
};
const VIEW_PERMISSIONS = {
  dashboard: 'dashboard:view',
  empresas: 'companies:view',
  comercial: 'commercial:view',
  usuarios: 'users:view',
  unidades: 'units:view',
  colaboradores: 'employees:view',
  'gestao-colaborador': 'employees:update',
  epis: 'epis:view',
  estoque: 'stock:view',
  entregas: 'deliveries:view',
  fichas: 'fichas:view',
  relatorios: 'reports:view'
};

const DEFAULT_COMPANY_LOGO = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect width="80" height="80" rx="20" fill="#f6d8c8"/><path d="M20 56h40M26 48V26h28v22" fill="none" stroke="#96401c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>')}`;
const DEFAULT_PLATFORM_BRAND = { display_name: 'Sua Empresa', legal_name: '', cnpj: '', logo_type: '' };
const DEFAULT_COMMERCIAL_SETTINGS = {
  unit_price: 42,
  plans: {
    individual: { label: 'Individual', min_users: 1, max_users: 1 },
    start: { label: 'Start', min_users: 1, max_users: 10 },
    business: { label: 'Business', min_users: 11, max_users: 25 },
    corporate: { label: 'Corporate', min_users: 26, max_users: 100 },
    enterprise: { label: 'Enterprise', min_users: 101, max_users: null }
  }
};
const EPI_ALL_UNITS_VALUE = '__ALL_UNITS__';

function safeStorageRead(key, fallback = 'null') {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch (error) {
    return fallback;
  }
}

function safeJsonParse(rawValue, fallbackValue) {
  try {
    return JSON.parse(rawValue);
  } catch (error) {
    return fallbackValue;
  }
}

function safeStorageWrite(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    // Ambiente com storage bloqueado: mantém sessão apenas em memória.
  }
}

function safeStorageRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    // Ambiente com storage bloqueado: mantém sessão apenas em memória.
  }
}

function debounce(fn, wait = 200) {
  let timer = null;
  return (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function bindSearchInput(target, callback, wait = 180) {
  if (!target) return;
  const handler = debounce(callback, wait);
  target.addEventListener('input', handler);
}

function markRequiredFieldLabels() {
  const labels = Array.from(document.querySelectorAll('label'));
  labels.forEach((label) => {
    if (label.querySelector('.required-star')) return;
    const directControl = label.querySelector('input, select, textarea');
    let required = Boolean(directControl?.required);
    if (!required) {
      const htmlFor = label.getAttribute('for');
      const referenced = htmlFor ? document.getElementById(htmlFor) : null;
      required = Boolean(referenced?.required);
    }
    if (!required) return;
    const star = document.createElement('span');
    star.className = 'required-star';
    star.textContent = ' *';
    star.setAttribute('aria-hidden', 'true');
    label.appendChild(star);
  });
}

const state = {
  user: safeJsonParse(safeStorageRead(SESSION_KEY, 'null'), null),
  permissions: safeJsonParse(safeStorageRead(SESSION_PERMISSIONS_KEY, '[]'), []),
  token: safeStorageRead(SESSION_TOKEN_KEY, ''),
  platformBrand: { ...DEFAULT_PLATFORM_BRAND },
  commercialSettings: JSON.parse(JSON.stringify(DEFAULT_COMMERCIAL_SETTINGS)),
  companies: [], companyAuditLogs: [], users: [], units: [], employees: [], employeeMovements: [], epis: [], deliveries: [], alerts: [], reports: null, lowStock: [], requests: [], fichasPeriods: [], stockGeneratedLabels: [], stockEpis: [], stockEpiMovementItems: [],
  stockMinimumEditor: { editing: false, epiId: null },
  editingUserId: null,
  editingCompanyId: null,
  selectedCompanyId: null,
  userFilters: { company_id: '', role: '', active: '', search: '' },
  commercialFilters: { status: '', date_from: '', date_to: '', actor_name: '' }
};

const qrScannerState = { active: false, stream: null, rafId: null, mode: '', zxingReader: null, zxingControls: null };

const refs = {
  loginScreen: document.getElementById('login-screen'),
  mainScreen: document.getElementById('main-screen'),
  loginForm: document.getElementById('login-form'),
  loginUsername: document.getElementById('login-username'),
  loginPassword: document.getElementById('login-password'),
  recoveryPanel: document.getElementById('recovery-panel'),
  loginMessage: document.getElementById('login-message'),
  recoveryToggle: document.getElementById('forgot-password-btn'),
  recoveryUsername: document.getElementById('recovery-username'),
  recoveryPassword: document.getElementById('recovery-password'),
  recoveryKey: document.getElementById('recovery-key'),
  recoverySubmit: document.getElementById('recovery-submit'),
  platformBrandPanel: document.getElementById('platform-brand-panel'),
  platformBrandLogo: document.getElementById('platform-brand-logo'),
  platformBrandName: document.getElementById('platform-brand-name'),
  profileLabel: document.getElementById('profile-label'),
  companyBadge: document.getElementById('company-badge'),
  viewTitle: document.getElementById('view-title'),
  currentDate: document.getElementById('current-date'),
  statsGrid: document.getElementById('stats-grid'),
  alertsList: document.getElementById('alerts-list'),
  latestDeliveries: document.getElementById('latest-deliveries'),
  approvedEpiTable: document.getElementById('approved-epi-table'),
  approvedEpiSearchName: document.getElementById('approved-epi-search-name'),
  approvedEpiSearchProtection: document.getElementById('approved-epi-search-protection'),
  approvedEpiSearchCa: document.getElementById('approved-epi-search-ca'),
  approvedEpiSearchManufacturer: document.getElementById('approved-epi-search-manufacturer'),
  approvedEpiSearchSection: document.getElementById('approved-epi-search-section'),
  companiesTable: document.getElementById('companies-table'),
  companiesSummary: document.getElementById('companies-summary'),
  companyDetails: document.getElementById('company-details'),
  companyForm: document.getElementById('company-form'),
  companyLogoFile: document.getElementById('company-logo-file'),
  companyLogoPreview: document.getElementById('company-logo-preview'),
  platformBrandForm: document.getElementById('platform-brand-form'),
  commercialSettingsForm: document.getElementById('commercial-settings-form'),
  platformLogoFile: document.getElementById('platform-logo-file'),
  platformLogoPreview: document.getElementById('platform-logo-preview'),
  commercialForm: document.getElementById('commercial-form'),
  commercialCompany: document.getElementById('commercial-company'),
  commercialPlanHint: document.getElementById('commercial-plan-hint'),
  commercialStats: document.getElementById('commercial-stats'),
  commercialFilterStatus: document.getElementById('commercial-filter-status'),
  commercialFilterDateFrom: document.getElementById('commercial-filter-date-from'),
  commercialFilterDateTo: document.getElementById('commercial-filter-date-to'),
  commercialFilterActor: document.getElementById('commercial-filter-actor'),
  commercialContractPdf: document.getElementById('commercial-contract-pdf'),
  commercialExport: document.getElementById('commercial-export'),
  commercialExportExcel: document.getElementById('commercial-export-excel'),
  commercialPrint: document.getElementById('commercial-print'),
  commercialSummary: document.getElementById('commercial-summary'),
  commercialAlerts: document.getElementById('commercial-alerts'),
  commercialExpiring: document.getElementById('commercial-expiring'),
  commercialHistory: document.getElementById('commercial-history'),
  usersTable: document.getElementById('users-table'),
  unitsTable: document.getElementById('units-table'),
  employeesTable: document.getElementById('employees-table'),
  employeesOpsTable: document.getElementById('employees-table-ops'),
  episTable: document.getElementById('epis-table'),
  deliveriesTable: document.getElementById('deliveries-table'),
  stockLowList: document.getElementById('stock-low-list'),
  requestsList: document.getElementById('requests-list'),
  stockEpisTable: document.getElementById('stock-epis-table'),
  stockFilterProtection: document.getElementById('stock-filter-protection'),
  stockFilterName: document.getElementById('stock-filter-name'),
  stockFilterSection: document.getElementById('stock-filter-section'),
  stockFilterManufacturer: document.getElementById('stock-filter-manufacturer'),
  stockFilterCa: document.getElementById('stock-filter-ca'),
  stockEpiMovementSearchName: document.getElementById('stock-epi-search-name'),
  stockEpiMovementSearchManufacturer: document.getElementById('stock-epi-search-manufacturer'),
  stockEpiMovementSearchResults: document.getElementById('stock-epi-search-results'),
  fichaView: document.getElementById('ficha-view'),
  fichaEmployee: document.getElementById('ficha-employee'),
  reportSummary: document.getElementById('report-summary'),
  reportUnits: document.getElementById('report-units'),
  reportSectors: document.getElementById('report-sectors'),
  userForm: document.getElementById('user-form'),
  userRole: document.getElementById('user-role'),
  userLinkedEmployeeSearch: document.getElementById('user-linked-employee-search'),
  userLinkedEmployeeResults: document.getElementById('user-linked-employee-results'),
  userFilterCompany: document.getElementById('user-filter-company'),
  userFilterRole: document.getElementById('user-filter-role'),
  userFilterStatus: document.getElementById('user-filter-status'),
  userFilterSearch: document.getElementById('user-filter-search'),
  usersSummary: document.getElementById('users-summary')
};

function qrCodeImageUrl(value) {
  return `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(String(value || '').trim())}`;
}

async function api(path, options = {}) {
  const authHeader = state.token ? { Authorization: `Bearer ${state.token}` } : {};
  let response;

  try {
    response = await fetch(path, {
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
        ...(options.headers || {})
      },
      ...options
    });
  } catch (error) {
    throw new Error('Falha de conexão com o servidor. Verifique sua internet e tente novamente.');
  }

  const contentType = String(response.headers.get('content-type') || '').toLowerCase();
  const expectsJson = String(path || '').startsWith('/api/');

  let payload = null;
  if (contentType.includes('application/json')) {
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
  } else {
    const raw = await response.text();
    payload = raw ? { error: raw } : null;
  }

  if (response.ok && expectsJson && !contentType.includes('application/json')) {
    const error = new Error('Resposta inválida do servidor. Tente novamente em instantes.');
    error.status = response.status;
    error.code = 'INVALID_API_RESPONSE';
    error.payload = payload;
    throw error;
  }

  if (!response.ok) {
    const message =
      payload?.error ||
      (response.status === 401
        ? 'Usuário ou senha inválidos.'
        : response.status === 403
          ? 'Acesso negado. Faça login novamente.'
          : `Falha na requisição (${response.status}).`);

    const error = new Error(message);
    error.status = response.status;
    error.code = payload?.code || '';
    error.payload = payload;
    throw error;
  }

  return payload || {};
}

function normalizePermissions(user, permissions = []) {
  const fallback = ROLE_PERMISSIONS[user?.role] || [];
  return [...new Set([...(permissions || []), ...fallback])];
}

function saveSession(user, permissions = [], token = '') {
  state.user = user;
  state.permissions = normalizePermissions(user, permissions);
  state.token = String(token || '');
  safeStorageWrite(SESSION_KEY, JSON.stringify(user));
  safeStorageWrite(SESSION_PERMISSIONS_KEY, JSON.stringify(state.permissions));
  if (state.token) safeStorageWrite(SESSION_TOKEN_KEY, state.token);
  else safeStorageRemove(SESSION_TOKEN_KEY);
}

function clearSession() {
  state.user = null;
  state.permissions = [];
  state.token = '';
  safeStorageRemove(SESSION_KEY);
  safeStorageRemove(SESSION_PERMISSIONS_KEY);
  safeStorageRemove(SESSION_TOKEN_KEY);
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

function unitTypeLabel(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'navio' || normalized === 'embarcacao') return 'Embarcação';
  if (normalized === 'plataforma') return 'Plataforma';
  return 'Base';
}

function setLoginMessage(message = '', isError = false) {
  if (!refs.loginMessage) return;
  refs.loginMessage.textContent = message;
  refs.loginMessage.classList.toggle('error', Boolean(isError));
}

function sanitizeLoginUrlParams() {
  const url = new URL(window.location.href);
  let changed = false;
  ['username', 'password'].forEach((key) => {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  });
  if (changed) {
    const query = url.searchParams.toString();
    const nextUrl = `${url.pathname}${query ? `?${query}` : ''}${url.hash || ''}`;
    window.history.replaceState({}, '', nextUrl);
  }
}

function preloadLoginFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const username = String(params.get('username') || '').trim();
  const password = String(params.get('password') || '').trim();
  if (username && refs.loginUsername) refs.loginUsername.value = username;
  if (password && refs.loginPassword) refs.loginPassword.value = password;
  if (username || password) {
    setLoginMessage('Credenciais da URL pré-preenchidas. Clique em "Entrar" para continuar.');
    sanitizeLoginUrlParams();
  }
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('pt-BR').format(new Date(`${value}T00:00:00`)) : '-';
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function cloneCommercialSettings(settings = DEFAULT_COMMERCIAL_SETTINGS) {
  return JSON.parse(JSON.stringify(settings));
}

function getCommercialSettings() {
  return state.commercialSettings || cloneCommercialSettings();
}

function planEntries() {
  return Object.entries(getCommercialSettings().plans || {});
}

function planLabel(planKey) {
  return getCommercialSettings().plans?.[planKey]?.label || planKey;
}

function planOptionMarkup(selectedPlan = '') {
  return planEntries().map(([key, plan]) => `<option value="${key}" ${key === selectedPlan ? 'selected' : ''}>${plan.label}</option>`).join('');
}

function planHintText(planKey, addendumEnabled = false) {
  const plan = getCommercialSettings().plans?.[planKey];
  if (!plan) return '';
  const maxText = plan.max_users === null ? 'sem teto' : `até ${plan.max_users}`;
  return `${plan.label}: mínimo ${plan.min_users} usuário(s), ${maxText}${addendumEnabled ? ' com aditivo contratual.' : '.'}`;
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function parseMonthsValue(rawValue) {
  const digits = String(rawValue ?? '').replace(/[^\d-]/g, '').trim();
  const parsed = Number.parseInt(digits || '0', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function renderEpiPhotoPreview(photoValue) {
  const preview = document.getElementById('epi-photo-preview');
  if (!preview) return;
  if (!photoValue) {
    preview.innerHTML = '<div class="summary-item">Sem foto anexada.</div>';
    return;
  }
  preview.innerHTML = `<div class="logo-preview-card"><img class="company-logo company-logo-lg" src="${photoValue}" alt="Pré-visualização da foto do EPI"><span>Foto do EPI anexada</span></div>`;
}

async function handleEpiPhotoUpload(event) {
  const hiddenField = document.getElementById('epi-photo-data');
  const file = event.target.files?.[0];
  if (!hiddenField) return;
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
    alert(error.message || 'Não foi possível processar a foto do EPI.');
    event.target.value = '';
    hiddenField.value = '';
    renderEpiPhotoPreview('');
  }
}
function getCompanyFormField(name) {
  const field = refs.companyForm?.elements?.namedItem(name) || null;
  if (!field) console.error(`[company-form] Campo esperado não encontrado: ${name}`);
  return field;
}

function setCompanyFieldValue(name, value = '', options = {}) {
  const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
  if (field) field.value = value ?? '';
}

function readCompanyFieldValue(name, fallback = '', options = {}) {
  const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
  return field ? field.value ?? fallback : fallback;
}


function digitsOnly(value) {
  return String(value || '').replace(/\D/g, '');
}

function formatCnpj(value) {
  const digits = digitsOnly(value);
  if (digits.length !== 14) return value || '';
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function companyLogoSrc(logoValue) {
  return String(logoValue || '').startsWith('data:image/') ? logoValue : DEFAULT_COMPANY_LOGO;
}

function companyLogoMarkup(company, className = 'company-logo') {
  const label = company?.name || 'Empresa';
  return `<img class="${className}" src="${companyLogoSrc(company?.logo_type)}" alt="Logotipo de ${label}">`;
}

function renderCompanyLogoPreview(logoValue) {
  if (!refs.companyLogoPreview) return;
  refs.companyLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: 'Empresa', logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${logoValue ? 'Logotipo carregado' : 'Imagem padrão em uso'}</span></div>`;
}

function renderPlatformLogoPreview(logoValue) {
  if (!refs.platformLogoPreview) return;
  refs.platformLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: state.platformBrand?.display_name || 'Sua Empresa', logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${logoValue ? 'Logotipo carregado' : 'Imagem padrão em uso'}</span></div>`;
}

async function handlePlatformLogoUpload(event) {
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

async function fileToJpegDataUrl(file, maxWidth = 720) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Não foi possível ler o arquivo do logotipo.'));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error('Não foi possível processar o logotipo enviado.'));
      image.onload = () => {
        const scale = Math.min(1, maxWidth / (image.width || maxWidth));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        const context = canvas.getContext('2d');
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.92));
      };
      image.src = String(reader.result || '');
    };
    reader.readAsDataURL(file);
  });
}

function renderPlatformBrand() {
  const brand = state.platformBrand || DEFAULT_PLATFORM_BRAND;
  if (refs.platformBrandName) refs.platformBrandName.textContent = brand.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  if (refs.platformBrandLogo) refs.platformBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: brand.logo_type }, 'company-logo company-logo-sm');
  if (refs.platformBrandForm) {
    refs.platformBrandForm.elements.display_name.value = brand.display_name || '';
    refs.platformBrandForm.elements.legal_name.value = brand.legal_name || '';
    refs.platformBrandForm.elements.cnpj.value = brand.cnpj || '';
    refs.platformBrandForm.elements.logo_type.value = brand.logo_type || '';
  }
  if (refs.platformLogoFile) refs.platformLogoFile.value = '';
  renderPlatformLogoPreview(brand.logo_type || '');
}

async function handleCompanyLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) {
    refs.companyForm.elements.logo_type.value = '';
    renderCompanyLogoPreview('');
    return;
  }
  const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];
  if (!allowed.includes(file.type)) {
    alert('Envie um logotipo PNG, JPG ou SVG.');
    event.target.value = '';
    return;
  }
  try {
    refs.companyForm.elements.logo_type.value = await fileToJpegDataUrl(file);
    renderCompanyLogoPreview(refs.companyForm.elements.logo_type.value);
  } catch (error) {
    alert(error.message);
    event.target.value = '';
  }
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
  if (!state.user || state.user.role === 'master_admin') return items;
  return items.filter((item) => {
    const directCompanyId = item?.company_id;
    if (directCompanyId !== undefined && directCompanyId !== null && String(directCompanyId) !== '') {
      return String(directCompanyId) === String(state.user.company_id || '');
    }
    const isCompanyRecord = item && Object.prototype.hasOwnProperty.call(item, 'license_status') && Object.prototype.hasOwnProperty.call(item, 'user_limit');
    if (isCompanyRecord) {
      return String(item.id || '') === String(state.user.company_id || '');
    }
    return false;
  });
}

function canManageMinimumStock() {
  return ['admin', 'user'].includes(state.user?.role);
}

function accessibleViews() {
  return Object.entries(VIEW_PERMISSIONS).filter(([, permission]) => hasPermission(permission)).map(([view]) => view);
}

function defaultView() {
  const ordered = ['dashboard', 'comercial', 'empresas', 'usuarios', 'unidades', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque', 'entregas', 'fichas', 'relatorios'];
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
    const view = item.dataset.view;
    let visible = hasPermission(VIEW_PERMISSIONS[view]);
    if (['epis', 'colaboradores', 'unidades', 'usuarios'].includes(view)) {
      visible = visible && ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
    }
    if (['gestao-colaborador', 'estoque', 'entregas', 'fichas'].includes(view)) {
      visible = visible && ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'].includes(state.user?.role);
    }
    item.style.display = visible ? '' : 'none';
  });
  const companyFormCard = refs.companyForm?.closest('.user-form-card');
  if (companyFormCard) companyFormCard.style.display = hasPermission('companies:create') || hasPermission('companies:update') ? '' : 'none';
  const platformBrandCard = refs.platformBrandForm?.closest('.user-form-card');
  if (platformBrandCard) platformBrandCard.style.display = state.user?.role === 'master_admin' ? '' : 'none';
  refs.profileLabel.textContent = state.user ? roleLabel(state.user.role) : 'Perfil';
  refs.companyBadge.innerHTML = state.user?.company_name ? `${companyLogoMarkup({ name: state.user.company_name, logo_type: state.user.logo_type }, 'company-logo company-logo-sm')}<span>${state.user.company_name}<br>${state.user.company_cnpj}</span>` : 'Acesso geral';
}

function populateRoleOptions() {
  const roleMap = {
    master_admin: [['general_admin', 'Administrador Geral'], ['registry_admin', 'Administrador de Registro'], ['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']],
    general_admin: [['registry_admin', 'Administrador de Registro'], ['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']],
    registry_admin: [['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']]
  };
  const roles = roleMap[state.user?.role] || [];
  refs.userRole.innerHTML = roles.map((item) => `<option value="${item[0]}">${item[1]}</option>`).join('');
}

function populateUserFilters() {
  if (!refs.userFilterCompany) return;
  const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
  refs.userFilterCompany.innerHTML = `<option value="">Todas</option>${companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('')}`;
  refs.userFilterCompany.value = state.userFilters.company_id;
  refs.userFilterRole.value = state.userFilters.role;
  refs.userFilterStatus.value = state.userFilters.active;
  refs.userFilterSearch.value = state.userFilters.search;
}

function renderUsersSummary() {
  const visible = filteredUsers();
  const admins = visible.filter((item) => ['master_admin', 'general_admin', 'admin'].includes(item.role)).length;
  const active = visible.filter((item) => Number(item.active) === 1).length;
  refs.usersSummary.innerHTML = [
    ['Visíveis', visible.length],
    ['Administradores', admins],
    ['Ativos', active]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function renderCompaniesSummary() {
  if (!refs.companiesSummary) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const active = visibleCompanies.filter((item) => Number(item.active) === 1).length;
  const nearLimit = visibleCompanies.filter((item) => item.near_limit && Number(item.limit_reached) !== 1).length;
  const blocked = visibleCompanies.filter((item) => Number(item.active) !== 1 || ['suspended', 'expired'].includes(item.license_status)).length;
  refs.companiesSummary.innerHTML = [
    ['Empresas', visibleCompanies.length],
    ['Ativas', active],
    ['Próximas do limite', nearLimit],
    ['Bloqueadas', blocked]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function companyStatusBadges(company) {
  const badges = [renderBadge('status', Number(company.active) === 1 ? 'active' : 'inactive', Number(company.active) === 1 ? 'Empresa ativa' : 'Empresa inativa')];
  const licenseTone = company.license_status === 'active' ? 'active' : company.license_status === 'trial' ? 'warning' : 'inactive';
  badges.push(renderBadge('status', licenseTone, company.license_status_label || company.license_status));
  if (Number(company.limit_reached) === 1) badges.push(renderBadge('status', 'inactive', 'No limite'));
  else if (company.near_limit) badges.push(renderBadge('status', 'warning', 'Próxima do limite'));
  return badges.join(' ');
}

function companyUsageText(company) {
  return `${company.user_count} faturável(eis) de ${company.user_limit} contratado(s)`;
}

function renderCompanyDetails(companyId = null) {
  if (!refs.companyDetails) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  if (!visibleCompanies.length) {
    refs.companyDetails.innerHTML = '<div class="summary-item">Nenhuma empresa disponível.</div>';
    return;
  }
  const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || state.selectedCompanyId)) || visibleCompanies[0];
  state.selectedCompanyId = selected.id;
  const monthly = formatCurrency(selected.monthly_value || 0);
  const projected = formatCurrency(selected.projected_monthly_value || 0);
  refs.companyDetails.innerHTML = `
    <div class="company-detail-hero">
      ${companyLogoMarkup(selected, 'company-logo company-logo-lg')}
      <div>
        <strong>${selected.name}</strong>
        <span>${selected.legal_name || '-'}</span>
        <span>CNPJ: ${selected.cnpj}</span>
      </div>
    </div>
    <div class="company-detail-badges">${companyStatusBadges(selected)}</div>
    <div class="company-detail-grid">
      <div class="summary-chip"><strong>${selected.user_count}</strong><span>Usuários faturáveis</span></div>
      <div class="summary-chip"><strong>${selected.user_limit}</strong><span>Limite contratado</span></div>
      <div class="summary-chip"><strong>${monthly}</strong><span>Valor mensal atual</span></div>
      <div class="summary-chip"><strong>${projected}</strong><span>Valor projetado</span></div>
      <div class="summary-chip"><strong>${selected.available_slots || 0}</strong><span>Vagas disponíveis</span></div>
    </div>
    <div class="company-detail-list">
      <div class="summary-item"><strong>Plano / licença:</strong> ${planLabel(selected.plan_name) || '-'}</div>
      <div class="summary-item"><strong>Valor unitário:</strong> ${formatCurrency(selected.unit_price || 0)}</div>
      <div class="summary-item"><strong>Vigência:</strong> ${formatDate(selected.contract_start)} até ${formatDate(selected.contract_end)}</div>
      <div class="summary-item"><strong>Aditivo contratual:</strong> ${Number(selected.addendum_enabled || 0) === 1 ? 'Ativo' : 'Não'}</div>
      <div class="summary-item"><strong>Observações comerciais:</strong> ${selected.commercial_notes || 'Sem observações comerciais.'}</div>
    </div>`;
}

function filteredCommercialCompanies() {
  const companies = filterByUserCompany(state.companies);
  if (!state.commercialFilters.status) return companies;
  return companies.filter((item) => item.license_status === state.commercialFilters.status);
}

function filteredCommercialLogs() {
  const selectedCompanyId = refs.commercialCompany?.value || '';
  return state.companyAuditLogs.filter((item) => {
    if (selectedCompanyId && String(item.company_id) !== String(selectedCompanyId)) return false;
    if (state.commercialFilters.actor_name && item.actor_name !== state.commercialFilters.actor_name) return false;
    const day = String(item.created_at || '').slice(0, 10);
    if (state.commercialFilters.date_from && day < state.commercialFilters.date_from) return false;
    if (state.commercialFilters.date_to && day > state.commercialFilters.date_to) return false;
    return true;
  });
}

function daysUntil(dateValue) {
  if (!dateValue) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${dateValue}T00:00:00`);
  return Math.round((target - today) / 86400000);
}

function fillCommercialSettingsForm() {
  if (!refs.commercialSettingsForm) return;
  const settings = getCommercialSettings();
  refs.commercialSettingsForm.elements.unit_price.value = settings.unit_price ?? 42;
  refs.commercialSettingsForm.elements.individual_max.value = settings.plans.individual.max_users ?? 1;
  refs.commercialSettingsForm.elements.start_max.value = settings.plans.start.max_users ?? 10;
  refs.commercialSettingsForm.elements.business_max.value = settings.plans.business.max_users ?? 25;
  refs.commercialSettingsForm.elements.corporate_max.value = settings.plans.corporate.max_users ?? 100;
  refs.commercialSettingsForm.elements.enterprise_min.value = settings.plans.enterprise.min_users ?? 101;
}

function refreshCommercialPreview(company = null) {
  if (!refs.commercialForm) return;
  const currentCompany = company || state.companies.find((item) => String(item.id) === String(refs.commercialCompany?.value || ''));
  const unitPrice = Number(getCommercialSettings().unit_price || 0);
  const activeUsers = Number(currentCompany?.user_count || 0);
  const userLimit = Number(refs.commercialForm.elements.user_limit.value || currentCompany?.user_limit || 0);
  const planName = refs.commercialForm.elements.plan_name.value || currentCompany?.plan_name || 'start';
  const addendumEnabled = refs.commercialForm.elements.addendum_enabled.checked;
  refs.commercialForm.elements.unit_price_display.value = formatCurrency(unitPrice);
  refs.commercialForm.elements.monthly_value.value = formatCurrency(activeUsers * unitPrice);
  refs.commercialForm.elements.projected_monthly_value.value = formatCurrency(userLimit * unitPrice);
  if (refs.commercialPlanHint) refs.commercialPlanHint.textContent = planHintText(planName, addendumEnabled);
}

function fillCommercialForm(companyId) {
  if (!refs.commercialForm || !refs.commercialCompany) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  refs.commercialCompany.innerHTML = visibleCompanies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
  refs.commercialForm.elements.plan_name.innerHTML = planOptionMarkup();
  const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || refs.commercialCompany.value)) || visibleCompanies[0];
  if (!selected) return;
  refs.commercialCompany.value = selected.id;
  refs.commercialForm.elements.company_id.value = selected.id;
  refs.commercialForm.elements.plan_name.value = selected.plan_name || 'start';
  refs.commercialForm.elements.user_limit.value = selected.user_limit || 1;
  refs.commercialForm.elements.addendum_enabled.checked = Number(selected.addendum_enabled || 0) === 1;
  refs.commercialForm.elements.contract_start.value = selected.contract_start || '';
  refs.commercialForm.elements.contract_end.value = selected.contract_end || '';
  refs.commercialForm.elements.license_status.value = selected.license_status || 'active';
  refs.commercialForm.elements.active.value = String(Number(selected.active || 1));
  refs.commercialForm.elements.commercial_notes.value = selected.commercial_notes || '';
  refreshCommercialPreview(selected);
}

function commercialRiskMeta(company) {
  if (Number(company.active) !== 1) return { label: 'Empresa inativa', tone: 'inactive' };
  if (company.license_status === 'expired') return { label: 'Contrato expirado', tone: 'inactive' };
  if (company.license_status === 'suspended') return { label: 'Contrato suspenso', tone: 'inactive' };
  if (Number(company.limit_reached) === 1) return { label: 'No limite', tone: 'inactive' };
  if (company.near_limit) return { label: 'Próxima do limite', tone: 'warning' };
  return { label: 'Saudável', tone: 'active' };
}

function commercialActions(company) {
  if (!hasPermission('companies:update')) return '';
  const canReactivate = company.license_status === 'suspended' || company.license_status === 'expired' || Number(company.active) !== 1;
  const toggleLabel = canReactivate ? 'Reativar' : 'Suspender';
  return `<div class="action-group commercial-actions"><button class="ghost" data-company-commercial="${company.id}">Abrir contrato</button><button class="ghost" data-commercial-toggle="${company.id}" data-commercial-mode="${canReactivate ? 'reactivate' : 'suspend'}">${toggleLabel}</button></div>`;
}

async function toggleCommercialStatus(companyId, mode) {
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company || !hasPermission('companies:update')) return;
  const next = mode === 'reactivate'
    ? { active: 1, license_status: 'active' }
    : { active: 0, license_status: 'suspended' };
  try {
    await api(`/api/companies/${company.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        name: company.name,
        legal_name: company.legal_name,
        cnpj: company.cnpj,
        logo_type: company.logo_type || '',
        plan_name: company.plan_name,
        user_limit: company.user_limit,
        contract_start: company.contract_start || '',
        contract_end: company.contract_end || '',
        monthly_value: company.monthly_value || 0,
        addendum_enabled: company.addendum_enabled || 0,
        license_status: next.license_status,
        active: next.active,
        commercial_notes: company.commercial_notes || ''
      })
    });
    await loadBootstrap();
    fillCommercialForm(company.id);
  } catch (error) { alert(error.message); }
}

function renderCommercialStats() {
  if (!refs.commercialStats) return;
  const companies = filterByUserCompany(state.companies);
  const monthlyTotal = companies.reduce((total, item) => total + Number(item.monthly_value || 0), 0);
  const activeCount = companies.filter((item) => item.license_status === 'active').length;
  const suspendedCount = companies.filter((item) => item.license_status === 'suspended').length;
  const expiredCount = companies.filter((item) => item.license_status === 'expired').length;
  refs.commercialStats.innerHTML = [
    ['Faturamento mensal', monthlyTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })],
    ['Empresas ativas', activeCount],
    ['Suspensas', suspendedCount],
    ['Expiradas', expiredCount]
  ].map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
}

function renderCommercialSummary() {
  if (!refs.commercialSummary) return;
  const companies = filteredCommercialCompanies();
  refs.commercialSummary.innerHTML = companies.map((item) => {
    const usage = `${item.user_count}/${item.user_limit}`;
    const monthly = formatCurrency(item.monthly_value || 0);
    const projected = formatCurrency(item.projected_monthly_value || 0);
    const risk = commercialRiskMeta(item);
    return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>${usage} usuários faturáveis</span><span>${monthly} atual | ${projected} projetado</span><span>${planLabel(item.plan_name)}</span></div><span class="badge badge-status-${risk.tone}">${risk.label}</span></div>${commercialActions(item)}</div>`;
  }).join('') || '<div class="summary-item">Sem empresas cadastradas.</div>';
}

function renderCommercialAlerts() {
  if (!refs.commercialAlerts) return;
  const alerts = filteredCommercialCompanies().filter((item) => Number(item.limit_reached) === 1 || item.near_limit || ['suspended', 'expired'].includes(item.license_status) || Number(item.active) !== 1);
  refs.commercialAlerts.innerHTML = alerts.map((item) => {
    const reasons = [];
    if (Number(item.limit_reached) === 1) reasons.push('limite contratado atingido');
    else if (item.near_limit) reasons.push('próxima do limite contratado');
    if (['suspended', 'expired'].includes(item.license_status)) reasons.push(`licença ${item.license_status_label.toLowerCase()}`);
    if (Number(item.active) !== 1) reasons.push('empresa inativa');
    return `<div class="commercial-card"><div class="alert-item ${Number(item.limit_reached) === 1 || item.license_status === 'expired' ? 'danger' : 'warning'}"><strong>${item.name}</strong><div>${reasons.join(' | ')}</div></div>${commercialActions(item)}</div>`;
  }).join('') || '<div class="summary-item">Nenhuma empresa em alerta comercial.</div>';
}

function renderCommercialHistory() {
  if (!refs.commercialHistory) return;
  const logs = filteredCommercialLogs();
  refs.commercialHistory.innerHTML = logs.slice(0, 12).map((item) => `<div class="commercial-card"><div class="commercial-row"><div class="company-logo company-logo-sm"></div><div><strong>${item.company_name}</strong><span>${item.action_label} por ${item.actor_name}</span><span>${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at))}</span></div><span class="badge badge-status-active">${item.action_label}</span></div><div class="summary-item">${item.summary}</div>${(item.details || []).length ? `<div class="audit-details">${item.details.map((detail) => `<div class=\"audit-detail-row\"><strong>${detail.field}</strong><span>${detail.before || '-'} -> ${detail.after || '-'}</span></div>`).join('')}</div>` : ''}</div>`).join('') || '<div class="summary-item">Sem histórico comercial registrado.</div>';
}

function renderCommercialExpiring() {
  if (!refs.commercialExpiring) return;
  const expiring = filterByUserCompany(state.companies)
    .map((item) => ({ item, days: daysUntil(item.contract_end) }))
    .filter((entry) => entry.days !== null && entry.days >= 0 && entry.days <= 30)
    .sort((a, b) => a.days - b.days);
  refs.commercialExpiring.innerHTML = expiring.map(({ item, days }) => `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>Vence em ${formatDate(item.contract_end)}</span><span>${days} dia(s) restantes</span></div><span class="badge badge-status-${days <= 7 ? 'inactive' : 'warning'}">${days <= 7 ? 'Urgente' : 'Acompanhar'}</span></div>${commercialActions(item)}</div>`).join('') || '<div class="summary-item">Nenhum contrato vencendo nos próximos 30 dias.</div>';
}

function populateCommercialActors() {
  if (!refs.commercialFilterActor) return;
  const names = [...new Set(state.companyAuditLogs.map((item) => item.actor_name))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  refs.commercialFilterActor.innerHTML = `<option value="">Todos</option>${names.map((name) => `<option value="${name}">${name}</option>`).join('')}`;
  refs.commercialFilterActor.value = state.commercialFilters.actor_name;
  refs.commercialFilterDateFrom.value = state.commercialFilters.date_from;
  refs.commercialFilterDateTo.value = state.commercialFilters.date_to;
  refs.commercialFilterStatus.value = state.commercialFilters.status;
}

function exportCommercialExcel() {
  const rows = filteredCommercialLogs();
  const brandName = state.platformBrand?.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  const header = ['Marca', 'Empresa', 'Ação', 'Responsável', 'Data', 'Resumo', 'Detalhes'];
  const body = rows.map((item) => `<tr><td>${brandName}</td><td>${item.company_name}</td><td>${item.action_label}</td><td>${item.actor_name}</td><td>${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at))}</td><td>${item.summary}</td><td>${(item.details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join('<br>')}</td></tr>`).join('');
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>table{border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif}th,td{border:1px solid #cfc7bb;padding:8px;text-align:left;vertical-align:top}th{background:#f6d8c8}</style></head><body><table><thead><tr>${header.map((item) => `<th>${item}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></body></html>`;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'historico-comercial.xls';
  link.click();
  URL.revokeObjectURL(link.href);
}

function printCommercialHistory() {
  const rows = filteredCommercialLogs();
  const currentCompany = state.companies.find((item) => String(item.id) === String(refs.commercialCompany?.value || ''));
  const brand = state.platformBrand || DEFAULT_PLATFORM_BRAND;
  const popup = window.open('', '_blank', 'width=1100,height=800');
  if (!popup) return alert('Não foi possível abrir a janela de impressão.');
  const filters = [
    state.commercialFilters.status ? `Status: ${state.commercialFilters.status}` : 'Status: todos',
    state.commercialFilters.actor_name ? `Responsável: ${state.commercialFilters.actor_name}` : 'Responsável: todos',
    state.commercialFilters.date_from ? `De: ${formatDate(state.commercialFilters.date_from)}` : '',
    state.commercialFilters.date_to ? `At?: ${formatDate(state.commercialFilters.date_to)}` : ''
  ].filter(Boolean).join(' | ');
  popup.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Histórico comercial</title><style>body{font-family:Segoe UI,Arial,sans-serif;padding:24px;color:#1d2a24}h1,h2{margin:0 0 8px}.brand{display:flex;align-items:center;gap:12px;margin-bottom:16px}.brand img{width:56px;height:56px;border-radius:16px;border:1px solid #d7d0c6;object-fit:cover}table{border-collapse:collapse;width:100%;margin-top:18px}th,td{border:1px solid #d7d0c6;padding:8px;vertical-align:top;text-align:left}th{background:#f6d8c8}.meta{color:#66726b;margin-bottom:14px}.detail{font-size:12px;color:#4c5a53}</style></head><body><div class="brand"><img src="${companyLogoSrc(brand.logo_type)}" alt="Marca"><div><h1>${brand.display_name}</h1><div class="meta">${brand.legal_name || ''}<br>${brand.cnpj || ''}</div></div></div><h2>Histórico comercial</h2><div class="meta">${currentCompany ? `Empresa: ${currentCompany.name}` : 'Todas as empresas'}<br>${filters}</div><table><thead><tr><th>Empresa</th><th>Ação</th><th>Responsável</th><th>Data</th><th>Resumo</th><th>Detalhes</th></tr></thead><tbody>${rows.map((item) => `<tr><td>${item.company_name}</td><td>${item.action_label}</td><td>${item.actor_name}</td><td>${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at))}</td><td>${item.summary}</td><td class="detail">${(item.details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join('<br>')}</td></tr>`).join('')}</tbody></table><script>window.onload=()=>window.print();<\/script></body></html>`);
  popup.document.close();
}

async function savePlatformBrand(event) {
  event.preventDefault();
  if (state.user?.role !== 'master_admin') return;
  try {
    const values = formValues(refs.platformBrandForm);
    values.actor_user_id = state.user.id;
    if (values.cnpj) values.cnpj = formatCnpj(values.cnpj);
    const payload = await api('/api/platform-brand', { method: 'POST', body: JSON.stringify(values) });
    state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...(payload.brand || {}) };
    renderPlatformBrand();
    alert('Marca da sua empresa atualizada.');
  } catch (error) { alert(error.message); }
}

function downloadCommercialContractPdf() {
  const companyId = refs.commercialCompany?.value;
  if (!companyId) return;
  const params = new URLSearchParams({ actor_user_id: state.user.id, company_id: companyId });
  window.open(`/api/commercial-contract.pdf?${params.toString()}`, '_blank');
}

function exportCommercialHistory() {
  const rows = filteredCommercialLogs();
  const brandName = state.platformBrand?.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  const header = ['Marca', 'Empresa', 'Ação', 'Responsável', 'Data', 'Resumo', 'Detalhes'];
  const lines = rows.map((item) => [
    brandName,
    item.company_name,
    item.action_label,
    item.actor_name,
    item.created_at,
    item.summary,
    (item.details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join(' | ')
  ]);
  const csv = [header, ...lines].map((row) => row.map((value) => `"${String(value || '').replace(/"/g, '""')}"`).join(';')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'historico-comercial.csv';
  link.click();
  URL.revokeObjectURL(link.href);
}

function syncCommercialFilter() {
  state.commercialFilters.status = refs.commercialFilterStatus?.value || '';
  state.commercialFilters.date_from = refs.commercialFilterDateFrom?.value || '';
  state.commercialFilters.date_to = refs.commercialFilterDateTo?.value || '';
  state.commercialFilters.actor_name = refs.commercialFilterActor?.value || '';
  renderCommercialSummary();
  renderCommercialAlerts();
  renderCommercialHistory();
}

async function saveCommercial(event) {
  event.preventDefault();
  if (!requirePermission('commercial:view')) return;
  const companyId = refs.commercialCompany?.value;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company) return;
  try {
    const values = formValues(refs.commercialForm);
    values.actor_user_id = state.user.id;
    values.name = company.name;
    values.legal_name = company.legal_name;
    values.cnpj = company.cnpj;
    values.logo_type = company.logo_type || '';
    values.addendum_enabled = refs.commercialForm.elements.addendum_enabled.checked ? 1 : 0;
    values.monthly_value = Number(company.monthly_value || 0);
    await api(`/api/companies/${company.id}`, { method: 'PUT', body: JSON.stringify(values) });
    await loadBootstrap();
    fillCommercialForm(company.id);
  } catch (error) { alert(error.message); }
}

async function saveCommercialSettings(event) {
  event.preventDefault();
  if (state.user?.role !== 'master_admin') return;
  try {
    const form = refs.commercialSettingsForm;
    const startMax = Number(form.elements.start_max.value || 10);
    const businessMax = Number(form.elements.business_max.value || 25);
    const corporateMax = Number(form.elements.corporate_max.value || 100);
    const payload = {
      actor_user_id: state.user.id,
      unit_price: Number(form.elements.unit_price.value || 0),
      plans: {
        individual: { label: 'Individual', min_users: 1, max_users: Number(form.elements.individual_max.value || 1) },
        start: { label: 'Start', min_users: 1, max_users: startMax },
        business: { label: 'Business', min_users: startMax + 1, max_users: businessMax },
        corporate: { label: 'Corporate', min_users: businessMax + 1, max_users: corporateMax },
        enterprise: { label: 'Enterprise', min_users: Number(form.elements.enterprise_min.value || 101), max_users: null }
      }
    };
    await api('/api/commercial-settings', { method: 'POST', body: JSON.stringify(payload) });
    await loadBootstrap();
    fillCommercialSettingsForm();
    fillCommercialForm(refs.commercialCompany?.value);
  } catch (error) { alert(error.message); }
}

function renderCompanies() {
  if (!refs.companiesTable) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const canManageCompanies = hasPermission('companies:create') || hasPermission('companies:update');
  const selectedId = String(state.selectedCompanyId || visibleCompanies[0]?.id || '');
  refs.companiesTable.innerHTML = visibleCompanies.map((item) => {
    const actions = canManageCompanies
      ? `<div class="action-group"><button class="ghost" data-company-details="${item.id}">Visualizar detalhes</button><button class="ghost" data-company-edit="${item.id}">Editar</button><button class="ghost" data-company-logo="${item.id}">Alterar logotipo</button><button class="ghost" data-company-commercial="${item.id}">Configurar licen\u00e7a</button><button class="ghost" data-company-toggle="${item.id}" data-company-active="${Number(item.active) === 1 ? 0 : 1}">${Number(item.active) === 1 ? 'Inativar' : 'Ativar'}</button></div>`
      : `<div class="action-group"><button class="ghost" data-company-details="${item.id}">Visualizar detalhes</button></div>`;
    return `
      <tr class="${selectedId === String(item.id) ? 'selected-row' : ''}">
        <td><div class="company-cell"><strong>${item.name}</strong><span>${item.legal_name || '-'}</span></div></td>
        <td><div class="company-cell"><strong>${item.cnpj}</strong><span>${item.plan_name || '-'}</span></div></td>
        <td><div class="company-cell">${companyStatusBadges(item)}<span>Vig\u00eancia: ${formatDate(item.contract_start)} at\u00e9 ${formatDate(item.contract_end)}</span></div></td>
        <td><div class="company-logo-slot">${companyLogoMarkup(item, 'company-logo company-logo-sm')}</div></td>
        <td><div class="company-cell"><strong>${item.user_count}</strong><span>${Number(item.limit_reached) === 1 ? 'Limite atingido' : `${item.available_slots || 0} vaga(s) dispon\u00edveis`}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_limit}</strong><span>${Number(item.monthly_value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span></div></td>
        <td>${actions}</td>
      </tr>`;
  }).join('') || '<tr><td colspan="7">Sem empresas dispon\u00edveis.</td></tr>';
}

function resetCompanyForm() {
  if (!refs.companyForm) return;
  state.editingCompanyId = null;
  refs.companyForm.reset();
  setCompanyFieldValue('id', '');
  setCompanyFieldValue('active', '1');
  setCompanyFieldValue('logo_type', '');
  if (refs.companyLogoFile) refs.companyLogoFile.value = '';
  renderCompanyLogoPreview('');
  renderCompanyDetails();
}

function startEditCompany(companyId, options = {}) {
  if (!hasPermission('companies:update')) return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company || !refs.companyForm) return;
  state.editingCompanyId = company.id;
  state.selectedCompanyId = company.id;
  setCompanyFieldValue('id', company.id);
  setCompanyFieldValue('name', company.name || '');
  setCompanyFieldValue('legal_name', company.legal_name || '');
  setCompanyFieldValue('cnpj', company.cnpj || '');
  setCompanyFieldValue('logo_type', company.logo_type || '');
  setCompanyFieldValue('active', String(Number(company.active || 1)));
  if (refs.companyLogoFile) refs.companyLogoFile.value = '';
  renderCompanyLogoPreview(company.logo_type || '');
  renderCompanies();
  renderCompanyDetails(company.id);
  refs.companyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (options.focusLogo && refs.companyLogoFile) {
    setTimeout(() => refs.companyLogoFile.click(), 120);
  }
}

function openCompanyLogoEditor(companyId) {
  startEditCompany(companyId, { focusLogo: true });
}

async function saveCompany(event) {
  event.preventDefault();
  if (!requirePermission(state.editingCompanyId ? 'companies:update' : 'companies:create')) return;
  try {
    const currentCompany = state.companies.find((item) => String(item.id) === String(state.editingCompanyId || '')) || {};
    const values = {
      actor_user_id: state.user.id,
      name: readCompanyFieldValue('name', currentCompany.name || ''),
      legal_name: readCompanyFieldValue('legal_name', currentCompany.legal_name || ''),
      cnpj: formatCnpj(readCompanyFieldValue('cnpj', currentCompany.cnpj || '')),
      logo_type: readCompanyFieldValue('logo_type', currentCompany.logo_type || ''),
      plan_name: currentCompany.plan_name || 'start',
      user_limit: currentCompany.user_limit || 10,
      addendum_enabled: currentCompany.addendum_enabled || 0,
      contract_start: currentCompany.contract_start || '',
      contract_end: currentCompany.contract_end || '',
      monthly_value: currentCompany.monthly_value || 0,
      license_status: currentCompany.license_status || 'active',
      active: readCompanyFieldValue('active', String(Number(currentCompany.active ?? 1))),
      commercial_notes: currentCompany.commercial_notes || ''
    };
    await api(state.editingCompanyId ? `/api/companies/${state.editingCompanyId}` : '/api/companies', { method: state.editingCompanyId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    resetCompanyForm();
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function toggleCompany(companyId, active) {
  if (!hasPermission('companies:update')) return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company) return;
  try {
    await api(`/api/companies/${companyId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, name: company.name, legal_name: company.legal_name, cnpj: company.cnpj, logo_type: company.logo_type, plan_name: company.plan_name, user_limit: company.user_limit, contract_start: company.contract_start || '', contract_end: company.contract_end || '', monthly_value: company.monthly_value || 0, addendum_enabled: company.addendum_enabled || 0, license_status: company.license_status, active, commercial_notes: company.commercial_notes || '' }) });
    await loadBootstrap();
  } catch (error) { alert(error.message); }
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
    state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...(payload.platform_brand || {}) };
    state.commercialSettings = cloneCommercialSettings(payload.commercial_settings || DEFAULT_COMMERCIAL_SETTINGS);
    state.companies = payload.companies;
    state.companyAuditLogs = payload.company_audit_logs || [];
    state.users = payload.users;
    state.units = payload.units;
    state.employees = payload.employees;
    state.employeeMovements = payload.employee_movements || [];
    state.epis = payload.epis;
    state.deliveries = payload.deliveries;
    state.alerts = payload.alerts;
    state.permissions = normalizePermissions(state.user, payload.permissions || state.permissions);
    if (hasPermission('stock:view')) {
      const lowStockPayload = await api(`/api/stock/low?${actorQuery()}`);
      state.lowStock = lowStockPayload.items || [];
      const requestsPayload = await api(`/api/requests?${actorQuery()}`);
      state.requests = requestsPayload.items || [];
      await loadStockEpis();
    } else {
      state.lowStock = [];
      state.requests = [];
      state.stockEpis = [];
    }
    if (hasPermission('fichas:view')) {
      const fichasPayload = await api(`/api/fichas?${actorQuery()}`);
      state.fichasPeriods = fichasPayload.items || [];
    } else {
      state.fichasPeriods = [];
    }
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
  const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
  populateSelect('user-company', companies, (item) => `${item.name} - ${item.cnpj}`, 'id', true, 'Sem vínculo');
  populateSelect('unit-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('employee-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('epi-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('epi-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('delivery-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('stock-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('delivery-unit-filter', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`, 'id', true, 'Todas as Unidades');
  populateSelect('report-company', companies, (item) => item.name, 'id', true, 'Todas');
  populateSelect('employee-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('movement-target-unit-id', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('movement-employee-id', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-epi', state.epis, (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('stock-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('stock-epi', state.epis, (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('ficha-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('report-unit', state.units, (item) => item.name, 'id', true, 'Todas');
  populateSelect('report-epi', state.epis, (item) => item.name, 'id', true, 'Todos');
  const sectors = [...new Set(filterByUserCompany(state.employees).map((item) => item.sector))].sort();
  document.getElementById('report-sector').innerHTML = `<option value="">Todos</option>${sectors.map((item) => `<option value="${item}">${item}</option>`).join('')}`;
  const defaultCompanyId = companies[0]?.id ? String(companies[0].id) : '';
  ['unit-company', 'employee-company', 'epi-company', 'delivery-company', 'stock-company'].forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (field && !field.value && defaultCompanyId) field.value = defaultCompanyId;
  });
  populateLinkedEmployeeOptions();
  syncEmployeeUnitOptions();
  syncEpiUnitOptions();
  syncDeliveryOptions();
  syncStockOptions();
  populateStockProtectionFilter();
}

function renderStats() {
  const cards = [['Empresas', state.user?.role === 'master_admin' ? state.companies.length : filterByUserCompany(state.companies).length], ['Colaboradores', filterByUserCompany(state.employees).length], ['EPIs', filterByUserCompany(state.epis).length], ['Entregas', filterByUserCompany(state.deliveries).length], ['Alertas', filterByUserCompany(state.alerts).length]];
  refs.statsGrid.innerHTML = cards.map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
}

function sameCompany(target) {
  return String(target.company_id || '') === String(state.user?.company_id || '');
}

function canManageUser(target) {
  if (!hasPermission('users:update')) return false;
  if (state.user?.role === 'master_admin') return target.role !== 'master_admin';
  if (state.user?.role === 'general_admin') return ['registry_admin', 'admin', 'user', 'employee'].includes(target.role) && sameCompany(target);
  if (state.user?.role === 'registry_admin') return ['admin', 'user', 'employee'].includes(target.role) && sameCompany(target);
  return false;
}
function canDeleteUser(target) { return hasPermission('users:delete') && canManageUser(target) && String(target.id) !== String(state.user?.id || ''); }
function canPromoteToAdmin(target) { return ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role) && target.role === 'user' && (state.user?.role === 'master_admin' || sameCompany(target)); }
function canPromoteToGeneralAdmin(target) { return state.user?.role === 'master_admin' && ['admin', 'user'].includes(target.role); }
function canDemoteAdmin(target) { return ['master_admin', 'general_admin'].includes(state.user?.role) && target.role === 'admin' && (state.user?.role === 'master_admin' || sameCompany(target)); }
function canDemoteGeneralAdmin(target) { return state.user?.role === 'master_admin' && target.role === 'general_admin'; }
function canToggleActive(target) { return canManageUser(target) && String(target.id) !== String(state.user?.id || ''); }

function setUserFormFeedback(message = '', isError = false) {
  const field = document.getElementById('user-form-feedback');
  if (!field) return;
  field.textContent = String(message || '');
  field.classList.toggle('error', Boolean(isError));
}

function syncUserFormAccess() {
  const roleField = refs.userForm?.elements?.role;
  const companyField = refs.userForm?.elements?.company_id;
  if (!roleField || !companyField) return;

  const selectedRole = String(roleField.value || '').trim();
  const requiresCompany = ['general_admin', 'registry_admin', 'admin', 'user', 'employee'].includes(selectedRole);
  const companyLocked = ['general_admin', 'registry_admin', 'admin'].includes(state.user?.role);

  if (companyLocked) {
    companyField.value = state.user?.company_id || '';
    companyField.disabled = true;
  } else {
    companyField.disabled = !requiresCompany;
    if (!requiresCompany) companyField.value = '';
  }

  if (requiresCompany && !companyField.value) {
    companyField.value = String(state.selectedCompanyId || state.user?.company_id || state.companies[0]?.id || '');
  }

  populateLinkedEmployeeOptions();
  syncUserEmployeeLink();
}

function userActionButtons(target) {
  if (!canManageUser(target) && !canDeleteUser(target) && target.role !== 'employee') return '-';
  const actions = [];
  if (canManageUser(target)) actions.push(`<button class="ghost" data-user-edit="${target.id}">Editar</button>`);
  if (canPromoteToAdmin(target)) actions.push(`<button class="ghost" data-user-promote-admin="${target.id}">Tornar Administrador</button>`);
  if (canPromoteToGeneralAdmin(target)) actions.push(`<button class="ghost" data-user-promote-general="${target.id}">Tornar Adm. Geral</button>`);
  if (canDemoteGeneralAdmin(target)) actions.push(`<button class="ghost" data-user-demote-general="${target.id}">Remover do Geral</button>`);
  if (canDemoteAdmin(target)) actions.push(`<button class="ghost" data-user-demote-admin="${target.id}">Rebaixar para Usuário</button>`);
  if (canToggleActive(target)) actions.push(`<button class="ghost" data-user-toggle="${target.id}">${Number(target.active) === 1 ? 'Desativar Usuário' : 'Reativar Usuário'}</button>`);
  if (canDeleteUser(target)) actions.push(`<button class="ghost" data-user-delete="${target.id}">Remover</button>`);
  if (target.role === 'employee' && target.employee_access_token) actions.push(`<button class="ghost" data-user-employee-qr="${target.id}">QR Acesso Externo</button>`);
  return `<div class="action-group">${actions.join('')}</div>`;
}

function printEmployeeAccessQr(userId) {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target?.employee_access_token) return alert('Funcionário sem token externo.');
  const accessLink = `${window.location.origin}${window.location.pathname}?employee_token=${encodeURIComponent(target.employee_access_token)}`;
  const popup = window.open('', '_blank', 'width=520,height=700');
  if (!popup) return alert('Não foi possível abrir a janela de impressão.');
  popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Acesso Funcionário</title><style>body{font-family:Segoe UI,Arial,sans-serif;padding:22px;text-align:center}img{width:240px;height:240px;margin:18px auto;display:block}a{word-break:break-all;color:#96401c}</style></head><body><h2>${target.full_name}</h2><p>Funcionário - Acesso externo</p><img src="${qrCodeImageUrl(accessLink)}" alt="QR acesso funcionário"><p><a href="${accessLink}">${accessLink}</a></p><script>window.onload=()=>window.print();<\/script></body></html>`);
  popup.document.close();
}

async function printEmployeePortalLink(employeeId) {
  try {
    const payload = await api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_id: Number(employeeId) })
    });
    const employee = state.employees.find((item) => String(item.id) === String(employeeId));
    const accessLink = payload.access_link || payload.qr_code_value || `${window.location.origin}${window.location.pathname}?employee_token=${encodeURIComponent(payload.token || '')}`;
    const popup = window.open('', '_blank', 'width=520,height=700');
    if (!popup) return alert('Não foi possível abrir a janela de impressão.');
    popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Link do Colaborador</title><style>body{font-family:Segoe UI,Arial,sans-serif;padding:22px;text-align:center}img{width:240px;height:240px;margin:18px auto;display:block}a{word-break:break-all;color:#96401c}</style></head><body><h2>${employee?.name || 'Colaborador'}</h2><p>Link de acesso externo</p><img src="${qrCodeImageUrl(accessLink)}" alt="Link acesso colaborador"><p><a href="${accessLink}">${accessLink}</a></p><script>window.onload=()=>window.print();<\/script></body></html>`);
    popup.document.close();
  } catch (error) {
    alert(error.message);
  }
}

function startEditUser(userId) {
  const user = state.users.find((item) => String(item.id) === String(userId));
  if (!user) return;
  state.editingUserId = user.id;
  setUserFormFeedback('');
  refs.userForm.elements.id.value = user.id;
  refs.userForm.elements.full_name.value = user.full_name;
  refs.userForm.elements.username.value = user.username;
  refs.userForm.elements.password.value = '';
  populateRoleOptions();
  refs.userForm.elements.role.value = canManageUser(user) ? user.role : refs.userRole.value;
  refs.userForm.elements.company_id.value = user.company_id || '';
  refs.userForm.elements.linked_employee_id.value = user.linked_employee_id || '';
  syncUserFormAccess();
}

async function updateUserAccess(userId, changes, successMessage = '') {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  try {
    await api(`/api/users/${userId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, username: target.username, full_name: target.full_name, password: '', role: changes.role || target.role, company_id: changes.company_id === undefined ? target.company_id : changes.company_id, active: changes.active === undefined ? target.active : changes.active }) });
    if (successMessage) alert(successMessage);
    setUserFormFeedback(successMessage || 'Usuário atualizado com sucesso.');
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

async function deleteUser(userId) {
  if (!window.confirm('Deseja remover este usuário?')) return;
  try {
    await api(`/api/users/${userId}?${actorQuery()}`, { method: 'DELETE' });
    if (String(state.editingUserId || '') === String(userId)) resetUserForm();
    setUserFormFeedback('Usuário removido com sucesso.');
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

function resetUserForm() {
  state.editingUserId = null;
  refs.userForm.reset();
  if (refs.userLinkedEmployeeSearch) refs.userLinkedEmployeeSearch.value = '';
  setUserFormFeedback('');
  refs.userForm.elements.id.value = '';
  populateRoleOptions();
  syncUserFormAccess();
}

function renderAlerts() { refs.alertsList.innerHTML = filterByUserCompany(state.alerts).map((item) => `<div class="alert-item ${item.type}"><strong>${item.title}</strong><div>${item.description}</div></div>`).join('') || '<div class="summary-item">Sem alertas.</div>'; }
function renderLatestDeliveries() { refs.latestDeliveries.innerHTML = filterByUserCompany(state.deliveries).slice(0, 5).map((item) => `<div class="list-item"><strong>${item.employee_name}</strong><div>${item.epi_name} - ${item.quantity} ${item.quantity_label}(s)</div><small>${item.company_name}  ${formatDate(item.delivery_date)}</small></div>`).join('') || '<div class="summary-item">Sem entregas.</div>'; }

function renderTables() {
  const canManageRecords = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
  refs.usersTable.innerHTML = filteredUsers().map((item) => `<tr><td>${item.full_name}</td><td>${renderBadge('role', item.role, roleLabel(item.role))}</td><td>${renderBadge('status', Number(item.active) === 1 ? 'active' : 'inactive', activeLabel(item.active))}</td><td>${item.company_name || 'Sistema'}</td><td>${userActionButtons(item)}</td></tr>`).join('') || '<tr><td colspan="5">Sem usuários.</td></tr>';
  refs.unitsTable.innerHTML = filterByUserCompany(state.units).map((item) => `<tr><td>${item.company_name}</td><td>${item.name}</td><td>${unitTypeLabel(item.unit_type)}</td><td>${item.city}</td><td>${canManageRecords ? `<div class="action-group"><button class="ghost" data-unit-edit="${item.id}">Editar</button><button class="ghost" data-unit-delete="${item.id}">Remover</button></div>` : '-'}</td></tr>`).join('') || '<tr><td colspan="5">Sem unidades.</td></tr>';
  refs.employeesTable.innerHTML = filterByUserCompany(state.employees).map((item) => `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${item.current_unit_name || item.unit_name}</td><td>${item.unit_allocation_type === 'temporary' ? 'Temporário' : 'Principal'}</td><td><button class="ghost" data-employee-link="${item.id}">Gerar Link</button></td><td>${canManageRecords ? `<div class="action-group"><button class="ghost" data-employee-edit="${item.id}">Editar</button><button class="ghost" data-employee-delete="${item.id}">Remover</button></div>` : '-'}</td></tr>`).join('') || '<tr><td colspan="9">Sem colaboradores.</td></tr>';
  if (refs.employeesOpsTable) refs.employeesOpsTable.innerHTML = refs.employeesTable.innerHTML;
  refs.episTable.innerHTML = filterByUserCompany(state.epis).map((item) => `<tr><td>${item.company_name}</td><td>${item.unit_name || '-'}</td><td>${item.name}</td><td>${item.purchase_code}</td><td>${item.sector}</td><td>${item.epi_section || '-'}</td><td>${item.manufacturer || '-'}</td><td>${item.supplier_company || '-'}</td><td>${item.active_joinventure || '-'}</td><td>${item.unit_measure}</td><td>${canManageRecords ? `<div class="action-group"><button class="ghost" data-epi-edit="${item.id}">Editar</button><button class="ghost" data-epi-delete="${item.id}">Remover</button></div>` : '-'}</td></tr>`).join('') || '<tr><td colspan="11">Sem EPIs.</td></tr>';
  refs.deliveriesTable.innerHTML = filterByUserCompany(state.deliveries).map((item) => `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.employee_name}</td><td>${item.epi_name}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td></tr>`).join('') || '<tr><td colspan="7">Sem entregas.</td></tr>';
  renderApprovedEpis();
}

function renderApprovedEpis() {
  if (!refs.approvedEpiTable) return;
  const byName = String(refs.approvedEpiSearchName?.value || '').toLowerCase();
  const byProtection = String(refs.approvedEpiSearchProtection?.value || '').toLowerCase();
  const byCa = String(refs.approvedEpiSearchCa?.value || '').toLowerCase();
  const byManufacturer = String(refs.approvedEpiSearchManufacturer?.value || '').toLowerCase();
  const bySection = String(refs.approvedEpiSearchSection?.value || '').toLowerCase();
  const rows = filterByUserCompany(state.epis).filter((item) =>
    String(item.name || '').toLowerCase().includes(byName)
    && String(item.sector || '').toLowerCase().includes(byProtection)
    && String(item.ca || '').toLowerCase().includes(byCa)
    && String(item.manufacturer || '').toLowerCase().includes(byManufacturer)
    && String(item.epi_section || '').toLowerCase().includes(bySection)
  );
  refs.approvedEpiTable.innerHTML = rows.map((item) => `<tr>
    <td>${item.name || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.model_reference || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${formatDate(item.ca_expiry)}</td>
    <td>${Number(item.manufacturer_validity_months || 0)}</td>
    <td>${item.sector || '-'}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.epi_photo_data ? `<img src="${item.epi_photo_data}" alt="Foto ${item.name}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;">` : '-'}</td>
    <td>${item.manufacturer_recommendations || '-'}</td>
  </tr>`).join('') || '<tr><td colspan="10">Sem EPIs aprovados para os filtros informados.</td></tr>';
}

function populateStockProtectionFilter() {
  if (!refs.stockFilterProtection) return;
  const epiProtectionField = document.querySelector('#epi-form [name="sector"]');
  const fallbackOptions = [
    'Proteção-Membros Superiores',
    'Proteção-Membros Inferiores',
    'Proteção-Auditiva',
    'Proteção-Olhos e Face',
    'Proteção-Respiratória',
    'Proteção-Mãos e Braços',
    'Proteção-Cabeça',
    'Proteção-Combate a Incêndio',
    'Proteção-Contra Queda',
    'Proteção-Eletricidade'
  ];
  const options = Array.from(epiProtectionField?.options || [])
    .map((option) => String(option.value || '').trim())
    .filter(Boolean);
  const protectionOptions = options.length ? options : fallbackOptions;
  refs.stockFilterProtection.innerHTML = `<option value="">Todas</option>${protectionOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}`;
}

async function loadStockEpis() {
  if (!hasPermission('stock:view')) return;
  const params = new URLSearchParams();
  params.set('actor_user_id', String(state.user.id));
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  if (companyId) params.set('company_id', String(companyId));
  if (unitId) params.set('unit_id', String(unitId));
  if (refs.stockFilterProtection?.value) params.set('protection', refs.stockFilterProtection.value);
  if (refs.stockFilterName?.value) params.set('name', refs.stockFilterName.value);
  if (refs.stockFilterSection?.value) params.set('section', refs.stockFilterSection.value);
  if (refs.stockFilterManufacturer?.value) params.set('manufacturer', refs.stockFilterManufacturer.value);
  if (refs.stockFilterCa?.value) params.set('ca', refs.stockFilterCa.value);
  const payload = await api(`/api/stock/epis?${params.toString()}`);
  state.stockEpis = payload.items || [];
  renderStockEpis();
  syncSelectedEpiMinimumStockField();
  refreshStockMovementItemsFromLocal();
}

function refreshStockMovementItemsFromLocal() {
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  const stockByEpiId = new Map((state.stockEpis || []).map((item) => [String(item.id), item]));
  const baseItems = filterByUserCompany(state.epis).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (unitId && item.unit_id && String(item.unit_id) !== String(unitId)) return false;
    return true;
  }).map((item) => {
    const stockEntry = stockByEpiId.get(String(item.id));
    return {
      ...item,
      stock: Number(stockEntry?.stock ?? 0),
      size_balances: Array.isArray(stockEntry?.size_balances) ? stockEntry.size_balances : []
    };
  });
  state.stockEpiMovementItems = baseItems;
  renderStockEpiSearchResults();
}

let stockSearchTimer = null;
function scheduleStockMovementSearchLoad() {
  if (stockSearchTimer) clearTimeout(stockSearchTimer);
  stockSearchTimer = setTimeout(() => {
    loadStockMovementSearchItems().catch((error) => console.error(error));
  }, 180);
}

async function loadStockMovementSearchItems() {
  if (!hasPermission('stock:view')) return;
  const params = new URLSearchParams();
  params.set('actor_user_id', String(state.user.id));
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  if (companyId) params.set('company_id', String(companyId));
  if (unitId) params.set('unit_id', String(unitId));
  const name = String(refs.stockEpiMovementSearchName?.value || '').trim();
  const manufacturer = String(refs.stockEpiMovementSearchManufacturer?.value || '').trim();
  if (name) params.set('name', name);
  if (manufacturer) params.set('manufacturer', manufacturer);
  const payload = await api(`/api/stock/epis?${params.toString()}`);
  const localById = new Map((state.stockEpiMovementItems || []).map((item) => [String(item.id), item]));
  for (const item of (payload.items || [])) localById.set(String(item.id), item);
  state.stockEpiMovementItems = Array.from(localById.values());
  renderStockEpiSearchResults();
}

function renderStockEpis() {
  if (!refs.stockEpisTable) return;
  const rows = state.stockEpis || [];
  refs.stockEpisTable.innerHTML = rows.map((item) => `<tr>
    <td>${item.name}</td>
    <td>${item.sector || '-'}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${item.unit_name || '-'}</td>
    <td>${item.stock} ${item.unit_measure}(s)</td>
    <td>${Number(item.minimum_stock ?? 0)}</td>
    <td>${canManageMinimumStock() ? `<div class="action-group"><button class="ghost" type="button" data-stock-minimum-edit="${item.id}">Editar Estoque mínimo</button></div>` : '-'}</td>
  </tr>`).join('') || '<tr><td colspan="9">Nenhum EPI encontrado para os filtros.</td></tr>';
}

function selectedStockEpi() {
  const epiField = document.getElementById('stock-epi');
  const selectedId = String(epiField?.value || '');
  if (!selectedId) return null;
  return (state.stockEpis || []).find((item) => String(item.id) === selectedId)
    || filterByUserCompany(state.epis).find((item) => String(item.id) === selectedId)
    || null;
}

function syncSelectedEpiMinimumStockField() {
  const valueField = document.getElementById('stock-minimum-selected-value');
  const editButton = document.getElementById('stock-minimum-selected-edit');
  const saveButton = document.getElementById('stock-minimum-selected-save');
  const selected = selectedStockEpi();
  if (!valueField) return;
  const selectedId = selected?.id ? String(selected.id) : null;
  const keepEditingCurrentEpi = Boolean(
    state.stockMinimumEditor.editing
    && selectedId
    && String(state.stockMinimumEditor.epiId || '') === selectedId
  );
  if (!keepEditingCurrentEpi) {
    valueField.value = String(Number(selected?.minimum_stock ?? 0));
    valueField.readOnly = true;
    valueField.classList.remove('is-editing');
    state.stockMinimumEditor.editing = false;
    state.stockMinimumEditor.epiId = selectedId;
  } else {
    valueField.readOnly = false;
  }
  valueField.value = String(Number(selected?.minimum_stock ?? 0));
  valueField.readOnly = true;
  const enabled = canManageMinimumStock() && Boolean(selected?.id);
  if (editButton) editButton.disabled = !enabled;
  if (saveButton) saveButton.disabled = !enabled || !keepEditingCurrentEpi;
}

function toggleSelectedMinimumStockEditMode(editing) {
  const valueField = document.getElementById('stock-minimum-selected-value');
  const saveButton = document.getElementById('stock-minimum-selected-save');
  const selected = selectedStockEpi();
  if (!valueField) return;
  if (editing && !selected?.id) return;
  state.stockMinimumEditor.editing = Boolean(editing);
  state.stockMinimumEditor.epiId = selected?.id ? String(selected.id) : null;
  valueField.readOnly = !editing;
  valueField.classList.toggle('is-editing', Boolean(editing));
  if (editing) {
    valueField.focus();
    valueField.select();
  }
  if (saveButton) saveButton.disabled = !canManageMinimumStock() || !selected?.id || !editing;
  if (!valueField) return;
  valueField.readOnly = !editing;
  if (editing) valueField.focus();
  if (saveButton) saveButton.disabled = !canManageMinimumStock() || !selectedStockEpi();
}

async function saveSelectedEpiMinimumStock() {
  if (!canManageMinimumStock()) {
    alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
    return;
  }
  if (!requirePermission('stock:adjust')) return;
  const selected = selectedStockEpi();
  const valueField = document.getElementById('stock-minimum-selected-value');
  if (!selected?.id || !valueField) return alert('Selecione um EPI para definir o estoque mínimo.');
  const minimumStock = Math.max(0, Number(valueField.value || 0));
  try {
    await api('/api/stock/minimum', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, epi_id: Number(selected.id), minimum_stock: minimumStock })
    });
    for (const list of [state.stockEpis, state.epis]) {
      const target = (list || []).find((item) => String(item.id) === String(selected.id));
      if (target) target.minimum_stock = minimumStock;
    }
    valueField.value = String(minimumStock);
    toggleSelectedMinimumStockEditMode(false);
    state.stockMinimumEditor.epiId = String(selected.id);
    await loadStockEpis();
    await loadLowStock();
    alert('Estoque mínimo salvo com sucesso.');
  } catch (error) {
    alert(error.message);
  }
}

async function saveMinimumStockByEpi(epiId) {
  if (!canManageMinimumStock()) {
    alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
    return;
  }
  if (!requirePermission('stock:adjust')) return;
  const input = document.querySelector(`[data-stock-minimum-input="${epiId}"]`);
  if (!input) return;
  const minimumStock = Math.max(0, Number(input.value || 0));
  try {
    await api('/api/stock/minimum', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id, epi_id: Number(epiId), minimum_stock: minimumStock }) });
    await loadStockEpis();
    await loadLowStock();
    alert('Estoque mínimo salvo com sucesso.');
  } catch (error) {
    alert(error.message);
  }
}

function openMinimumStockEditor(epiId) {
  if (!canManageMinimumStock()) {
    alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
    return;
  }
  const item = (state.stockEpis || []).find((row) => String(row.id) === String(epiId));
  if (!item) return;
  const card = document.getElementById('stock-minimum-card');
  const form = document.getElementById('stock-minimum-form');
  if (!card || !form) return;
  card.style.display = 'block';
  document.getElementById('stock-minimum-epi-id').value = String(item.id);
  document.getElementById('stock-minimum-epi-name').value = String(item.name || '');
  document.getElementById('stock-minimum-unit-name').value = String(item.unit_name || '-');
  const valueField = document.getElementById('stock-minimum-value');
  valueField.value = String(item.minimum_stock ?? 0);
  valueField.readOnly = true;
}

function stockEpiMatchesMovementSearch(item) {
  const byName = String(refs.stockEpiMovementSearchName?.value || '').trim().toLowerCase();
  const byManufacturer = String(refs.stockEpiMovementSearchManufacturer?.value || '').trim().toLowerCase();
  if (byName && !String(item.name || '').toLowerCase().includes(byName)) return false;
  if (byManufacturer && !String(item.manufacturer || '').toLowerCase().includes(byManufacturer)) return false;
  return true;
}

function renderStockEpiSearchResults() {
  const list = refs.stockEpiMovementSearchResults;
  if (!list) return;
  const source = (state.stockEpiMovementItems || []).filter(stockEpiMatchesMovementSearch);
  if (!source.length && (refs.stockEpiMovementSearchName?.value || refs.stockEpiMovementSearchManufacturer?.value)) {
    list.innerHTML = '<div class="summary-item">Nenhum EPI encontrado com esse nome/fabricante na unidade selecionada.</div>';
    return;
  }
  list.innerHTML = source.slice(0, 40).map((item) => {
    const sizeBalances = Array.isArray(item.size_balances) ? item.size_balances : [];
    const sizeLabel = sizeBalances.length
      ? sizeBalances.slice(0, 3).map((entry) => {
        const parts = [entry.glove_size, entry.size, entry.uniform_size].filter((value) => value && value !== 'N/A');
        const value = parts.length ? parts.join('/') : 'N/A';
        return `${value} (${entry.quantity})`;
      }).join(' | ')
      : 'Sem tamanho em estoque';
    const summary = `${item.name || '-'} • ${item.manufacturer || 'Sem fabricante'} • Tam: ${sizeLabel} • CA: ${item.ca || '-'}`;
    return `<button type="button" class="ghost stock-epi-search-item" data-stock-epi-pick="${item.id}">${summary}</button>`;
  }).join('') || '<div class="summary-item">Digite nome e/ou fabricante para buscar o EPI.</div>';
}

function selectStockEpiFromSearch(epiId) {
  const epiField = document.getElementById('stock-epi');
  if (!epiField) return;
  epiField.value = String(epiId);
  syncStockSizeDefaults();
  syncSelectedEpiMinimumStockField();
  const target = (state.stockEpiMovementItems || []).find((item) => String(item.id) === String(epiId))
    || (state.stockEpis || []).find((item) => String(item.id) === String(epiId));
  if (target) {
    if (refs.stockEpiMovementSearchName) refs.stockEpiMovementSearchName.value = String(target.name || '');
    if (refs.stockEpiMovementSearchManufacturer) refs.stockEpiMovementSearchManufacturer.value = String(target.manufacturer || '');
  }
  renderStockEpiSearchResults();
}

function renderLowStock() {
  if (!refs.stockLowList) return;
  const items = state.lowStock || [];
  refs.stockLowList.innerHTML = items.map((item) => `<div class="summary-item"><strong>${item.company_name} / ${item.unit_name}</strong><div>${item.epi_name}: ${item.stock} ${item.unit_measure}(s) (mínimo ${item.minimum_stock})</div></div>`).join('') || '<div class="summary-item">Sem itens com estoque baixo.</div>';
}

function renderRequests() {
  if (!refs.requestsList) return;
  const items = state.requests || [];
  refs.requestsList.innerHTML = items.map((item) => `<div class="summary-item"><strong>#${item.id} - ${item.employee_name}</strong><div>${item.epi_name} • ${item.quantity} un • ${item.unit_name}</div><small>Status: ${item.status}</small></div>`).join('') || '<div class="summary-item">Sem solicitações.</div>';
}

function syncEpiUnitOptions() {
  const companyField = document.getElementById('epi-company');
  const unitField = document.getElementById('epi-unit');
  if (!companyField || !unitField) return;
  const companyId = companyField.value || state.user?.company_id || '';
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  const previous = String(unitField.value || '');
  unitField.innerHTML = `<option value="${EPI_ALL_UNITS_VALUE}">Todas</option>${units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('')}`;
  if (previous && previous !== EPI_ALL_UNITS_VALUE && units.some((item) => String(item.id) === previous)) {
    unitField.value = previous;
  } else {
    unitField.value = EPI_ALL_UNITS_VALUE;
  }
  applyEpiJoinventureRules();
}

function currentJoinventures() {
  const hidden = document.getElementById('epi-joinventures');
  const companyId = document.getElementById('epi-company')?.value || state.user?.company_id || '';
  if (!hidden) return [];
  try {
    const parsed = JSON.parse(hidden.value || '[]');
    if (!Array.isArray(parsed)) return [];
    const normalized = parsed.map((entry) => {
      if (typeof entry === 'string') {
        return { name: entry.trim(), unit_id: null };
      }
      if (!entry || typeof entry !== 'object') return null;
      const name = String(entry.name || '').trim();
      const unitId = entry.unit_id === null || entry.unit_id === undefined || entry.unit_id === '' ? null : String(entry.unit_id).trim();
      return name ? { name, unit_id: unitId || null } : null;
    }).filter(Boolean);
    return normalized.filter((entry) => {
      if (!entry.unit_id) return true;
      const unit = state.units.find((item) => String(item.id) === String(entry.unit_id));
      return unit && (!companyId || String(unit.company_id) === String(companyId));
    });
  } catch (_) {
    return [];
  }
}

function persistJoinventures(values) {
  const hidden = document.getElementById('epi-joinventures');
  if (!hidden) return;
  hidden.value = JSON.stringify(values.map((item) => ({ name: item.name, unit_id: item.unit_id || null })));
}

function activeJoinventureToken(entry) {
  if (!entry?.name) return '';
  return `${entry.name}@@${entry.unit_id || ''}`;
}

function parseActiveJoinventureToken(value) {
  const raw = String(value || '').trim();
  if (!raw) return { name: '', unit_id: null };
  if (!raw.includes('@@')) return { name: raw, unit_id: null };
  const [name, unitId] = raw.split('@@');
  return { name: String(name || '').trim(), unit_id: String(unitId || '').trim() || null };
}

function applyEpiJoinventureRules() {
  const unitField = document.getElementById('epi-unit');
  const activeSelect = document.getElementById('epi-joinventure-active');
  const hint = document.getElementById('epi-unit-rule-hint');
  if (!unitField || !activeSelect) return;
  const selected = parseActiveJoinventureToken(activeSelect.value);
  if (selected.name && selected.unit_id) {
    unitField.value = String(selected.unit_id);
    unitField.disabled = true;
    if (hint) hint.textContent = `Unidade travada pela Joint Venture ativa: ${selected.name}.`;
  } else {
    unitField.disabled = false;
    if (!unitField.value) unitField.value = EPI_ALL_UNITS_VALUE;
    if (hint) hint.textContent = 'Sem Joint Venture ativa: você pode usar "Todas as Unidades" para aprovar o EPI em nível de empresa.';
    if (hint) hint.textContent = 'Sem Joint Venture ativa: você pode usar "Todas" para aprovar o EPI em nível de empresa.';
  }
}

function renderJoinventureList() {
  const list = document.getElementById('epi-joinventure-list');
  const activeSelect = document.getElementById('epi-joinventure-active');
  const addButton = document.getElementById('epi-joinventure-add');
  const addInput = document.getElementById('epi-joinventure-name');
  if (!list || !activeSelect) return;
  const canManageJoinventure = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
  if (addButton) addButton.disabled = !canManageJoinventure;
  if (addInput) addInput.disabled = !canManageJoinventure;
  const values = currentJoinventures();
  persistJoinventures(values);
  list.innerHTML = values.map((entry) => {
    const unit = state.units.find((item) => String(item.id) === String(entry.unit_id || ''));
    const unitLabel = unit ? `${unit.name}` : 'Sem unidade definida';
    const token = activeJoinventureToken(entry);
    return `<button class="ghost" type="button" data-joinventure-remove="${token}">${entry.name} (${unitLabel}) - Apagar</button>`;
  }).join('') || '<span class="hint">Nenhuma JoinVenture cadastrada.</span>';
  const previous = parseActiveJoinventureToken(activeSelect.value);
  activeSelect.innerHTML = '<option value="">Sem Joint Venture ativa (EPI geral)</option>' + values.map((entry) => `<option value="${activeJoinventureToken(entry)}">${entry.name}${entry.unit_id ? ` - ${state.units.find((item) => String(item.id) === String(entry.unit_id))?.name || `Unidade #${entry.unit_id}`}` : ''}</option>`).join('');
  const previousToken = activeJoinventureToken(previous);
  const stillExists = values.some((entry) => activeJoinventureToken(entry) === previousToken);
  activeSelect.value = stillExists ? previousToken : '';
  applyEpiJoinventureRules();
}

function addJoinventure() {
  if (!['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role)) return;
  const input = document.getElementById('epi-joinventure-name');
  const unitField = document.getElementById('epi-unit');
  if (!input || !unitField) return;
  const name = String(input.value || '').trim();
  if (!name) return;
  if (String(unitField.value || '') === EPI_ALL_UNITS_VALUE) {
    alert('Selecione uma unidade específica antes de cadastrar uma Joint Venture.');
    return;
  }
  const unitId = String(unitField.value || '').trim();
  const values = currentJoinventures();
  if (!values.some((item) => item.name.toLowerCase() === name.toLowerCase() && String(item.unit_id || '') === unitId)) {
    values.push({ name, unit_id: unitId });
  }
  persistJoinventures(values);
  input.value = '';
  renderJoinventureList();
}

function removeJoinventure(token) {
  const values = currentJoinventures().filter((item) => activeJoinventureToken(item) !== String(token));
  persistJoinventures(values);
  renderJoinventureList();
}

function setFormSubmitLabel(formId, text) {
  const button = document.querySelector(`#${formId} button[type="submit"]`);
  if (button) button.textContent = text;
}

function startEditUnit(unitId) {
  const item = state.units.find((unit) => String(unit.id) === String(unitId));
  const form = document.getElementById('unit-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  form.elements.name.value = item.name || '';
  form.elements.unit_type.value = item.unit_type || 'base';
  form.elements.city.value = item.city || '';
  form.elements.notes.value = item.notes || '';
  setFormSubmitLabel('unit-form', 'Atualizar unidade');
  showView('unidades');
}

function startEditEmployee(employeeId) {
  const item = state.employees.find((employee) => String(employee.id) === String(employeeId));
  const form = document.getElementById('employee-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  syncEmployeeUnitOptions();
  form.elements.unit_id.value = item.unit_id || '';
  form.elements.employee_id_code.value = item.employee_id_code || '';
  form.elements.name.value = item.name || '';
  form.elements.sector.value = item.sector || '';
  form.elements.role_name.value = item.role_name || '';
  form.elements.schedule_type.value = item.schedule_type || '14x14';
  form.elements.admission_date.value = item.admission_date || '';
  setFormSubmitLabel('employee-form', 'Atualizar colaborador');
  showView('colaboradores');
}

function startEditEpi(epiId) {
  const item = state.epis.find((epi) => String(epi.id) === String(epiId));
  const form = document.getElementById('epi-form');
  if (!item || !form) return;
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
  if (!form.elements.sector.value) form.elements.sector.value = 'Proteção-Membros Superiores';
  form.elements.manufacturer.value = item.manufacturer || '';
  form.elements.supplier_company.value = item.supplier_company || '';
  form.elements.unit_measure.value = item.unit_measure || 'unidade';
  form.elements.ca_expiry.value = item.ca_expiry || '';
  form.elements.epi_validity_date.value = item.epi_validity_date || '';
  form.elements.manufacture_date.value = item.manufacture_date || '';
  form.elements.glove_size.value = item.glove_size || 'N/A';
  form.elements.size.value = item.size || 'N/A';
  form.elements.uniform_size.value = item.uniform_size || 'N/A';
  form.elements.manufacturer_validity_months.value = String(item.manufacturer_validity_months ?? item.validity_months ?? 0);
  form.elements.manufacturer_recommendations.value = item.manufacturer_recommendations || '';
  form.elements.epi_photo_data.value = item.epi_photo_data || '';
  if (document.getElementById('epi-photo-file')) document.getElementById('epi-photo-file').value = '';
  renderEpiPhotoPreview(form.elements.epi_photo_data.value);
  document.getElementById('epi-joinventures').value = item.joinventures_json || '[]';
  renderJoinventureList();
  const existingEntry = currentJoinventures().find((entry) => entry.name === String(item.active_joinventure || '').trim());
  form.elements.active_joinventure.value = existingEntry ? activeJoinventureToken(existingEntry) : '';
  applyEpiJoinventureRules();
  setFormSubmitLabel('epi-form', 'Salvar');
  showView('epis');
}

async function deleteRegistryEntity(path, entityId, permission, message) {
  if (!requirePermission(permission)) return;
  if (!confirm(message)) return;
  try {
    await api(`${path}/${entityId}?actor_user_id=${encodeURIComponent(state.user.id)}`, { method: 'DELETE' });
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  }
}

function syncDeliveryOptions() {
  const companyField = document.getElementById('delivery-company');
  const unitFilterField = document.getElementById('delivery-unit-filter');
  const searchField = document.getElementById('delivery-employee-search');
  const employeeField = document.getElementById('delivery-employee');
  const epiField = document.getElementById('delivery-epi');
  const unitHint = document.getElementById('delivery-unit-hint');
  if (!companyField || !employeeField || !epiField) return;
  const companyId = companyField.value || state.user?.company_id || '';
  const operationalUnitId = state.user?.operational_unit_id;
  const lockByOperationalProfile = ['admin', 'user'].includes(state.user?.role);
  const lockUnitByProfile = lockByOperationalProfile && operationalUnitId;
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  const unitOptions = lockByOperationalProfile
    ? (lockUnitByProfile ? units.filter((item) => String(item.id) === String(operationalUnitId)) : [])
    : units;
  if (unitFilterField) {
    const previous = String(unitFilterField.value || '');
    unitFilterField.innerHTML = `${lockByOperationalProfile ? '' : '<option value="">Todas as unidades</option>'}${unitOptions.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('')}`;
    if (lockUnitByProfile && unitOptions.length) unitFilterField.value = String(unitOptions[0].id);
    if (lockByOperationalProfile && !unitOptions.length) unitFilterField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
    else if (previous && unitOptions.some((item) => String(item.id) === previous)) unitFilterField.value = previous;
    unitFilterField.disabled = Boolean(lockByOperationalProfile);
  }
  companyField.disabled = Boolean(lockByOperationalProfile);
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  const unitFilter = lockByOperationalProfile
    ? String(operationalUnitId || '__NO_UNIT__')
    : String(unitFilterField?.value || '');
  const search = String(searchField?.value || '').trim().toLowerCase();
  const employees = filterByUserCompany(state.employees).filter((item) => {
    if (unitFilter === '__NO_UNIT__') return false;
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    const currentUnitId = item.current_unit_id || item.unit_id;
    if (unitFilter && String(currentUnitId) !== String(unitFilter)) return false;
    if (search) {
      const haystack = `${item.name} ${item.employee_id_code} ${item.id}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });
  const epis = filterByUserCompany(state.epis).filter((item) => {
    if (unitFilter === '__NO_UNIT__') return false;
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (unitFilter && item.unit_id && String(item.unit_id) !== String(unitFilter)) return false;
    return true;
  });
  employeeField.innerHTML = employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
  epiField.innerHTML = epis.map((item) => `<option value="${item.id}">${item.name} - ${item.unit_measure}</option>`).join('');
  if (employees.length && !employees.some((item) => String(item.id) === String(employeeField.value))) employeeField.value = String(employees[0].id);
  if (epis.length && !epis.some((item) => String(item.id) === String(epiField.value))) epiField.value = String(epis[0].id);
}

function syncEmployeeUnitOptions() {
  const companyField = document.getElementById('employee-company');
  const unitField = document.getElementById('employee-unit');
  if (!companyField || !unitField) return;
  const companyId = companyField.value || state.user?.company_id || '';
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  unitField.innerHTML = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
  if (units.length && !units.some((item) => String(item.id) === String(unitField.value))) {
    unitField.value = String(units[0].id);
  }
}

function syncStockOptions() {
  const companyField = document.getElementById('stock-company');
  const unitField = document.getElementById('stock-unit');
  const epiField = document.getElementById('stock-epi');
  const unitHint = document.getElementById('stock-unit-hint');
  if (!companyField || !unitField || !epiField) return;
  const lockByOperationalProfile = ['admin', 'user'].includes(state.user?.role);
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
  }
  const companyId = lockByOperationalProfile
    ? (state.user?.company_id || '')
    : (companyField.value || state.user?.company_id || '');
  const operationalUnitId = state.user?.operational_unit_id;
  const lockUnitByProfile = lockByOperationalProfile && operationalUnitId;
  let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  if (lockByOperationalProfile && !operationalUnitId) units = [];
  if (lockUnitByProfile) units = units.filter((item) => String(item.id) === String(operationalUnitId));
  const epis = filterByUserCompany(state.epis).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    return true;
  });
  unitField.innerHTML = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
  if (!units.length) {
    unitField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
  }
  if (lockUnitByProfile && units.length) unitField.value = String(units[0].id);
  unitField.disabled = Boolean(lockByOperationalProfile);
  companyField.disabled = Boolean(lockByOperationalProfile);
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  epiField.innerHTML = epis.map((item) => {
    const sizeParts = [item.glove_size, item.size, item.uniform_size].filter((value) => value && value !== 'N/A');
    const manufacturer = item.manufacturer ? ` • ${item.manufacturer}` : '';
    const sizeLabel = sizeParts.length ? ` • Tam: ${sizeParts.join(' / ')}` : '';
    return `<option value="${item.id}">${item.name}${manufacturer}${sizeLabel} • ${item.unit_measure}</option>`;
  }).join('');
  if (epis.length && !epis.some((item) => String(item.id) === String(epiField.value))) epiField.value = String(epis[0].id);
  syncStockSizeDefaults();
  syncSelectedEpiMinimumStockField();
  refreshStockMovementItemsFromLocal();
  scheduleStockMovementSearchLoad();
  renderStockEpiSearchResults();
}

function syncStockSizeDefaults() {
  const form = document.getElementById('stock-form');
  const epiField = document.getElementById('stock-epi');
  if (!form || !epiField) return;
  const selectedEpi = state.epis.find((item) => String(item.id) === String(epiField.value || ''));
  if (!selectedEpi) return;
  if (form.elements.glove_size) form.elements.glove_size.value = selectedEpi.glove_size || 'N/A';
  if (form.elements.size) form.elements.size.value = selectedEpi.size || 'N/A';
  if (form.elements.uniform_size) form.elements.uniform_size.value = selectedEpi.uniform_size || 'N/A';
}

function handleDeliveryQrScan() {
  const input = document.getElementById('delivery-qr-scan');
  if (!input) return;
  const value = String(input.value || '').trim();
  if (!value) return;
  const epi = filterByUserCompany(state.epis).find((item) => item.qr_code_value === value || item.purchase_code === value);
  if (!epi) return;
  const companyField = document.getElementById('delivery-company');
  const epiField = document.getElementById('delivery-epi');
  companyField.value = String(epi.company_id);
  syncDeliveryOptions();
  epiField.value = String(epi.id);
  refreshDeliveryContext();
}

async function applyEmployeeQrLookup() {
  const qrValue = String(document.getElementById('delivery-employee-qr-scan')?.value || '').trim();
  if (!qrValue) return;
  try {
    const payload = await api('/api/employee-lookup', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_qr_code: qrValue })
    });
    const employee = payload.employee;
    if (!employee) return;
    document.getElementById('delivery-company').value = String(employee.company_id);
    syncDeliveryOptions();
    document.getElementById('delivery-employee').value = String(employee.id);
    refreshDeliveryContext();
  } catch (error) {
    alert(error.message);
  }
}

async function generateDeliveryEmployeeLink() {
  const employeeId = Number(document.getElementById('delivery-employee')?.value || 0);
  if (!employeeId) return alert('Selecione um colaborador para gerar o link.');
  try {
    const payload = await api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_id: employeeId })
    });
    const accessLink = payload.access_link || '';
    const linkField = document.getElementById('delivery-employee-link');
    if (linkField) linkField.value = accessLink;
    if (accessLink) await navigator.clipboard?.writeText(accessLink);
    alert('Link gerado com sucesso. O acesso contém: Ficha de EPI, Solicitação de EPI e Avaliação/Sugestão.');
  } catch (error) {
    alert(error.message);
  }
}

function setDeliveryQrStatus(message, isError = false) {
  const status = document.getElementById('delivery-qr-status');
  if (!status) return;
  status.textContent = String(message || '');
  status.style.color = isError ? '#a13b2b' : '#96401c';
}

let zxingLoaderPromise = null;
function loadZxingLibrary() {
  if (window.ZXingBrowser?.BrowserMultiFormatReader) return Promise.resolve(window.ZXingBrowser);
  if (zxingLoaderPromise) return zxingLoaderPromise;
  zxingLoaderPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/@zxing/browser@0.1.5/umd/index.min.js';
    script.async = true;
    script.onload = () => window.ZXingBrowser?.BrowserMultiFormatReader ? resolve(window.ZXingBrowser) : reject(new Error('ZXing não disponível.'));
    script.onerror = () => reject(new Error('Falha ao carregar biblioteca de leitura.'));
    document.head.appendChild(script);
  });
  return zxingLoaderPromise;
}

function stopDeliveryQrCamera() {
  qrScannerState.active = false;
  if (qrScannerState.rafId) cancelAnimationFrame(qrScannerState.rafId);
  qrScannerState.rafId = null;
  if (qrScannerState.zxingControls?.stop) qrScannerState.zxingControls.stop();
  qrScannerState.zxingControls = null;
  qrScannerState.zxingReader = null;
  qrScannerState.mode = '';
  if (qrScannerState.stream) {
    qrScannerState.stream.getTracks().forEach((track) => track.stop());
  }
  qrScannerState.stream = null;
  const wrap = document.getElementById('delivery-qr-camera-wrap');
  const video = document.getElementById('delivery-qr-video');
  if (video) video.srcObject = null;
  if (wrap) wrap.style.display = 'none';
  setDeliveryQrStatus('Leitura encerrada.');
}

async function startDeliveryQrWithBarcodeDetector(video, input) {
  const detector = new BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'itf'] });
  qrScannerState.mode = 'barcode-detector';
  const detectFrame = async () => {
    if (!qrScannerState.active) return;
    try {
      const codes = await detector.detect(video);
      if (codes?.length) {
        const rawValue = String(codes[0].rawValue || '').trim();
        if (rawValue) {
          input.value = rawValue;
          setDeliveryQrStatus(`Código lido (${codes[0].format || 'desconhecido'}): ${rawValue}`);
          handleDeliveryQrScan();
          stopDeliveryQrCamera();
          return;
        }
      }
    } catch (error) {
      setDeliveryQrStatus('Erro na leitura por câmera. Tentando novamente...', true);
    }
    qrScannerState.rafId = requestAnimationFrame(detectFrame);
  };
  setDeliveryQrStatus('Câmera ativa. Aponte para QR Code ou código de barras.');
  detectFrame();
}

async function startDeliveryQrWithZxing(videoElementId, input) {
  const ZXingBrowser = await loadZxingLibrary();
  qrScannerState.mode = 'zxing';
  qrScannerState.zxingReader = new ZXingBrowser.BrowserMultiFormatReader();
  setDeliveryQrStatus('Câmera ativa (modo compatibilidade). Aponte para QR/Barcode.');
  qrScannerState.zxingControls = await qrScannerState.zxingReader.decodeFromVideoDevice(undefined, videoElementId, (result, error) => {
    if (result?.text) {
      input.value = String(result.text).trim();
      setDeliveryQrStatus(`Código lido: ${input.value}`);
      handleDeliveryQrScan();
      stopDeliveryQrCamera();
    } else if (error?.name && error.name !== 'NotFoundException') {
      setDeliveryQrStatus('Aguardando leitura...', false);
    }
  });
}

async function startDeliveryQrCamera() {
  const input = document.getElementById('delivery-qr-scan');
  const wrap = document.getElementById('delivery-qr-camera-wrap');
  const video = document.getElementById('delivery-qr-video');

  if (!input || !wrap || !video) return;

  if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
    setDeliveryQrStatus('Navegador sem acesso à câmera. Use leitor USB ou digite o código.', true);
    alert('Câmera não disponível neste navegador. Você pode digitar ou usar leitor USB.');
    return;
  }

  stopDeliveryQrCamera();

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false
    });

    qrScannerState.stream = stream;
    qrScannerState.active = true;
    wrap.style.display = 'grid';
    video.srcObject = stream;
    await video.play();

    if ('BarcodeDetector' in window) {
      await startDeliveryQrWithBarcodeDetector(video, input);
    } else {
      await startDeliveryQrWithZxing('delivery-qr-video', input);
    }
  } catch (error) {
    stopDeliveryQrCamera();
    setDeliveryQrStatus('Permissão negada ou câmera indisponível.', true);
    alert('Não foi possível acessar a câmera. Verifique permissões do navegador.');
  }
}

async function handleDeliveryQrImageUpload(event) {
  const inputField = document.getElementById('delivery-qr-scan');
  const file = event?.target?.files?.[0];
  if (!file || !inputField) return;
  try {
    const ZXingBrowser = await loadZxingLibrary();
    const imageReader = new ZXingBrowser.BrowserMultiFormatReader();
    const imageUrl = URL.createObjectURL(file);
    const tempImage = new Image();
    tempImage.src = imageUrl;
    await tempImage.decode();
    const result = await imageReader.decodeFromImageElement(tempImage);
    URL.revokeObjectURL(imageUrl);
    if (!result?.text) throw new Error('Código não identificado na imagem.');
    inputField.value = String(result.text).trim();
    setDeliveryQrStatus(`Código lido por imagem: ${inputField.value}`);
    handleDeliveryQrScan();
  } catch (error) {
    setDeliveryQrStatus('Não foi possível ler o código da imagem.', true);
    alert('Falha ao ler imagem. Tente outra foto com melhor iluminação/foco.');
  } finally {
    if (event?.target) event.target.value = '';
  }
}

function renderFicha() {
  const filteredEmployees = filterByUserCompany(state.employees);
  const employeeId = refs.fichaEmployee.value || filteredEmployees[0]?.id;
  const employee = filteredEmployees.find((item) => String(item.id) === String(employeeId));
  if (!employee) { refs.fichaView.innerHTML = '<div class="summary-item">Nenhum colaborador disponível.</div>'; return; }
  refs.fichaEmployee.value = employee.id;
  const deliveries = filterByUserCompany(state.deliveries).filter((item) => String(item.employee_id) === String(employee.id));
  const periods = (state.fichasPeriods || []).filter((item) => String(item.employee_id) === String(employee.id));
  refs.fichaView.innerHTML = `<div class="summary-item"><strong>Empresa:</strong> ${employee.company_name} (${employee.company_cnpj})</div><div class="summary-item ficha-logo"><strong>Logotipo:</strong> ${companyLogoMarkup({ name: employee.company_name, logo_type: employee.logo_type }, 'company-logo company-logo-sm')}</div><div class="summary-item"><strong>Colaborador:</strong> ${employee.name}</div><div class="summary-item"><strong>ID:</strong> ${employee.employee_id_code}</div><div class="summary-item"><strong>SETOR:</strong> ${employee.sector}</div><div class="summary-item"><strong>Função:</strong> ${employee.role_name}</div><div class="summary-item"><strong>Escala:</strong> ${employee.schedule_type}</div><div class="summary-item"><strong>Períodos:</strong> ${periods.map((item) => `${formatDate(item.period_start)} a ${formatDate(item.period_end)} (${item.status})`).join(' | ') || 'Sem período registrado'}</div><div class="table-wrap"><table><thead><tr><th>EPI</th><th>Código</th><th>Qtd</th><th>Medida</th><th>Entrega</th><th>Assinatura</th><th>Fabricação</th><th>Validade</th></tr></thead><tbody>${deliveries.map((item) => `<tr><td>${item.epi_name}</td><td>${item.purchase_code}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td><td>${item.signature_name}</td><td>${formatDate(item.manufacture_date)}</td><td>${formatDate(item.epi_validity_date)}</td></tr>`).join('') || '<tr><td colspan="8">Sem itens nesta ficha.</td></tr>'}</tbody></table></div>`;
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
  const deliveryCompanyField = document.getElementById('delivery-company');
  const unit = state.units.find((item) => String(item.id) === String(employee?.current_unit_id || employee?.unit_id || ''));
  const linkField = document.getElementById('delivery-employee-link');
  if (employee?.company_id && deliveryCompanyField) deliveryCompanyField.value = String(employee.company_id);
  if (linkField) {
    const accessLink = employee?.employee_access_token ? `${window.location.origin}${window.location.pathname}?employee_token=${encodeURIComponent(employee.employee_access_token)}` : '';
    linkField.value = accessLink;
  }
  document.getElementById('delivery-unit').value = unit ? `${unit.name} - ${unitTypeLabel(unit.unit_type)}` : '';
  document.getElementById('delivery-employee-code').value = employee?.employee_id_code || '';
  document.getElementById('delivery-sector').value = employee?.sector || '';
  document.getElementById('delivery-role').value = employee?.role_name || '';
  document.getElementById('delivery-unit-measure').value = epi?.unit_measure || '';
}

function normalizeSearchText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function filteredLinkedEmployees() {
  const companyId = refs.userForm?.elements.company_id?.value || state.user?.company_id || '';
  const searchValue = normalizeSearchText(refs.userLinkedEmployeeSearch?.value || '');
  return filterByUserCompany(state.employees).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (!searchValue) return true;
    const haystack = normalizeSearchText(`${item.employee_id_code || ''} ${item.name || ''} ${item.role_name || ''}`);
    return haystack.includes(searchValue);
  });
}

function renderLinkedEmployeeSearchResults() {
  const box = refs.userLinkedEmployeeResults;
  if (!box) return;
  const employees = filteredLinkedEmployees();
  if (!employees.length) {
    box.innerHTML = '<div class="summary-item">Nenhum colaborador encontrado para o filtro informado.</div>';
    return;
  }
  box.innerHTML = employees.slice(0, 8).map((item) => {
    const subtitle = `${item.employee_id_code} • ${item.role_name || 'Sem função'} • ${item.name}`;
    return `<button type="button" class="ghost" data-user-linked-pick="${item.id}">${subtitle}</button>`;
  }).join('');
}

function populateLinkedEmployeeOptions() {
  const field = document.getElementById('user-linked-employee');
  if (!field) return;
  const employees = filteredLinkedEmployees();
  const canUseWithoutLink = ['master_admin', 'general_admin'].includes(state.user?.role);
  field.innerHTML = `${canUseWithoutLink ? '<option value="">Sem vínculo</option>' : ''}${employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('')}`;
  if (!canUseWithoutLink && !field.value && employees.length) field.value = String(employees[0].id);
  renderLinkedEmployeeSearchResults();
}

function setManualEmployeeFieldsEnabled(enabled) {
  const editableFields = [
    'employee_id_code',
    'employee_role_name',
    'employee_sector',
    'employee_schedule_type',
    'employee_admission_date',
    'employee_unit_id'
  ];
  editableFields.forEach((name) => {
    const input = refs.userForm?.elements?.[name];
    if (!input) return;
    if (input.tagName === 'SELECT') input.disabled = !enabled;
    else input.readOnly = !enabled;
  });
}

function syncUserEmployeeLink() {
  const selectedRole = String(refs.userForm?.elements?.role?.value || '').trim();
  const linkedId = refs.userForm?.elements.linked_employee_id?.value;
  const companyId = refs.userForm?.elements.company_id?.value || state.user?.company_id || '';
  const unitField = refs.userForm?.elements.employee_unit_id;
  const unitFieldLabel = unitField?.closest('label');
  if (unitField) {
    const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    unitField.innerHTML = `<option value="">Selecione</option>${units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('')}`;
  }
  const employee = state.employees.find((item) => String(item.id) === String(linkedId || ''));
  const canManual = ['master_admin', 'general_admin'].includes(state.user?.role);
  const isWithoutLink = !linkedId;
  const isOperationalRole = ['admin', 'user'].includes(selectedRole);

  if (employee) {
    refs.userForm.elements.employee_id_code.value = employee.employee_id_code || '';
    refs.userForm.elements.employee_role_name.value = employee.role_name || '';
    refs.userForm.elements.employee_sector.value = employee.sector || '';
    refs.userForm.elements.employee_schedule_type.value = employee.schedule_type || '';
    refs.userForm.elements.employee_admission_date.value = employee.admission_date || '';
    if (unitField) unitField.value = String(employee.unit_id || '');
    if (employee?.company_id) refs.userForm.elements.company_id.value = employee.company_id;
  } else if (isWithoutLink && !canManual) {
    refs.userForm.elements.linked_employee_id.value = '';
  } else if (!employee && isWithoutLink) {
    refs.userForm.elements.employee_id_code.value = '';
    refs.userForm.elements.employee_role_name.value = '';
    refs.userForm.elements.employee_sector.value = '';
    refs.userForm.elements.employee_schedule_type.value = '';
    refs.userForm.elements.employee_admission_date.value = '';
    if (unitField) unitField.value = '';
  }

  const allowManualEmployeeCreation = isWithoutLink && canManual && selectedRole === 'employee';
  if (isOperationalRole && !employee && refs.userForm?.elements.linked_employee_id) {
    refs.userForm.elements.linked_employee_id.value = '';
  }
  if (unitFieldLabel) {
    unitFieldLabel.style.display = allowManualEmployeeCreation ? '' : 'none';
  }
  setManualEmployeeFieldsEnabled(allowManualEmployeeCreation);
}

function renderAll() {
  refs.currentDate.textContent = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date());
  applyRoleVisibility();
  renderPlatformBrand();
  populateRoleOptions();
  populateUserFilters();
  bindDependentSelects();
  renderStats();
  renderAlerts();
  renderLatestDeliveries();
  renderCompaniesSummary();
  renderCompanies();
  renderCompanyDetails();
  fillCommercialSettingsForm();
  fillCommercialForm();
  populateCommercialActors();
  renderCommercialStats();
  renderCommercialSummary();
  renderCommercialAlerts();
  renderCommercialExpiring();
  renderCommercialHistory();
  renderTables();
  renderLowStock();
  renderRequests();
  renderStockEpis();
  renderFicha();
  renderReports();
  refreshDeliveryContext();
  syncUserFormAccess();
  markRequiredFieldLabels();
  showView(defaultView());
}

async function handleLogin(event) {
  event.preventDefault();
  setLoginMessage('');

  const submitButton = refs.loginForm?.querySelector('button[type="submit"]');

  try {
    const username = String(refs.loginUsername?.value || '').trim();
    const password = String(refs.loginPassword?.value || '');

    if (!username || !password.trim()) {
      setLoginMessage('Informe usuário e senha para entrar.', true);
      return;
    }

    if (submitButton) submitButton.disabled = true;

    console.info('[auth] Tentativa de login', { username });

    const payload = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    if (!payload?.user || !payload?.token) {
      throw new Error('Falha ao autenticar: resposta inválida do servidor.');
    }

    console.info('[auth] Login concluído com sucesso', {
      user_id: payload.user.id,
      username: payload.user.username
    });

    saveSession(payload.user, payload.permissions || [], payload.token || '');
    showScreen(true);
    await loadBootstrap();
  } catch (error) {
    console.error('[auth] Falha no login', {
      message: error?.message,
      status: error?.status,
      code: error?.code,
      payload: error?.payload
    });

    const code = String(error?.code || '').toUpperCase();
    let message = error.message || 'Falha ao autenticar. Verifique usuário e senha.';

    if (code === 'USER_NOT_FOUND') message = 'Usuário não encontrado.';
    if (code === 'INVALID_PASSWORD') message = 'Senha incorreta.';
    if (code === 'USER_INACTIVE') message = 'Usuário inativo. Procure o administrador do sistema.';
    if (error?.status === 401 && !code) message = 'Usuário ou senha inválidos.';
    if (error?.status === 403 && !code) message = 'Acesso negado ou sessão inválida.';

    setLoginMessage(message, true);
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

function toggleRecoveryPanel() {
  if (!refs.recoveryPanel) return;
  const isVisible = refs.recoveryPanel.style.display !== 'none';
  refs.recoveryPanel.style.display = isVisible ? 'none' : 'block';
}

async function handlePasswordRecovery() {
  try {
    const payload = {
      username: String(refs.recoveryUsername?.value || '').trim(),
      new_password: String(refs.recoveryPassword?.value || '').trim(),
      recovery_key: String(refs.recoveryKey?.value || '').trim()
    };
    await api('/api/recover-password', { method: 'POST', body: JSON.stringify(payload) });
    alert('Senha redefinida com sucesso. Faça login com a nova senha.');
    if (refs.recoveryPanel) refs.recoveryPanel.style.display = 'none';
    const passwordField = refs.loginPassword;
    if (passwordField) passwordField.value = '';
  } catch (error) {
    alert(error.message);
  }
}

async function saveUser(event) {
  event.preventDefault();
  if (!requirePermission(state.editingUserId ? 'users:update' : 'users:create')) return;
  try {
    setUserFormFeedback('');
    const values = formValues(refs.userForm);
    values.actor_user_id = state.user.id;
    if (['general_admin', 'admin'].includes(state.user.role)) values.company_id = state.user.company_id;

    values.active = Number(values.active || 1);
    if (!String(values.company_id || '').trim()) throw new Error('Empresa é obrigatória no cadastro de usuário.');
    if (!ROLE_LABELS[values.role]) throw new Error('Perfil inválido.');
    const noLink = !String(values.linked_employee_id || '').trim();
    if (['admin', 'user'].includes(values.role) && noLink) {
      throw new Error('Administrador Local e Gestor de EPI devem ser vinculados a um colaborador com unidade.');
    }
    if (noLink && !['master_admin', 'general_admin'].includes(state.user?.role)) {
      throw new Error('Seu perfil não pode criar usuário sem vínculo de colaborador.');
    }

    if (!String(values.password || '').trim() && !state.editingUserId) {
      throw new Error('Informe uma senha para criar o usuário.');
    }
    await api(state.editingUserId ? `/api/users/${state.editingUserId}` : '/api/users', { method: state.editingUserId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    setUserFormFeedback(state.editingUserId ? 'Usuário atualizado com sucesso.' : 'Usuário criado com sucesso.');
    resetUserForm();
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

async function saveSimpleForm(event, path, permission) {
  event.preventDefault();
  if (!requirePermission(permission)) return;
  if (event.target.dataset.submitting === '1') return;
  event.target.dataset.submitting = '1';
  const submitButton = event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  try {
    const values = formValues(event.target);
    const editingId = String(values.id || '').trim();
    if ('id' in values) delete values.id;
    if (event.target.id === 'epi-form') {
      const parsedActiveJoinventure = parseActiveJoinventureToken(values.active_joinventure);
      if (parsedActiveJoinventure.name && parsedActiveJoinventure.unit_id) {
        values.unit_id = parsedActiveJoinventure.unit_id;
      }
      if (!parsedActiveJoinventure.name && String(values.unit_id || '') === EPI_ALL_UNITS_VALUE) {
        values.unit_id = '';
      }
      values.active_joinventure = parsedActiveJoinventure.name || '';
      values.stock = 0;
      values.glove_size = String(values.glove_size || 'N/A');
      values.size = String(values.size || 'N/A');
      values.uniform_size = String(values.uniform_size || 'N/A');
      values.manufacturer_validity_months = parseMonthsValue(values.manufacturer_validity_months);
      values.validity_years = 0;
      values.validity_months = values.manufacturer_validity_months;
      values.validity_days = values.manufacturer_validity_months * 30;
      values.joinventures_json = document.getElementById('epi-joinventures')?.value || '[]';
      if (!values.epi_photo_data && editingId) {
        const photoFile = document.getElementById('epi-photo-file')?.files?.[0];
        if (photoFile) {
          values.epi_photo_data = await fileToDataUrl(photoFile);
        } else if (editingId) {
          const currentEpi = state.epis.find((epi) => String(epi.id) === String(editingId));
          values.epi_photo_data = currentEpi?.epi_photo_data || '';
        }
      }
    }
    values.actor_user_id = state.user.id;
    if (state.user?.role !== 'master_admin' && values.company_id !== undefined && !values.company_id) values.company_id = state.user.company_id;
    const updatePermission = event.target.dataset.updatePermission || permission;
    if (editingId && !requirePermission(updatePermission)) return;
    const requestPath = editingId ? `${path}/${editingId}` : path;
    const payload = await api(requestPath, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    if (event.target.id === 'employee-form' && payload?.employee_access_link) {
      try {
        await navigator.clipboard?.writeText(payload.employee_access_link);
      } catch (_) {
        // noop: clipboard can fail in insecure contexts
      }
      alert(`Colaborador cadastrado com sucesso.\nLink de acesso externo:\n${payload.employee_access_link}`);
    }
    event.target.reset();
    if (event.target.id === 'epi-form') {
      const hidden = document.getElementById('epi-joinventures');
      if (hidden) hidden.value = '[]';
      if (event.target.elements.epi_photo_data) event.target.elements.epi_photo_data.value = '';
      if (document.getElementById('epi-photo-file')) document.getElementById('epi-photo-file').value = '';
      renderEpiPhotoPreview('');
      renderJoinventureList();
      if (event.target.elements.unit_id) event.target.elements.unit_id.value = EPI_ALL_UNITS_VALUE;
      if (event.target.elements.active_joinventure) event.target.elements.active_joinventure.value = '';
      applyEpiJoinventureRules();
      setFormSubmitLabel('epi-form', 'Salvar');
    }
    if (event.target.id === 'unit-form') {
      setFormSubmitLabel('unit-form', 'Salvar unidade');
    }
    if (event.target.id === 'employee-form') {
      setFormSubmitLabel('employee-form', 'Salvar colaborador');
    }
    if (event.target.id === 'delivery-form') {
      event.target.elements.delivery_date.value = new Date().toISOString().split('T')[0];
      event.target.elements.next_replacement_date.value = new Date().toISOString().split('T')[0];
    }
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  } finally {
    event.target.dataset.submitting = '0';
    if (submitButton) submitButton.disabled = false;
  }
}

function printStockLabels(qrItems, copies = 1) {
  if (!Array.isArray(qrItems) || !qrItems.length) return;
  const repeat = Math.max(1, Number(copies || 1));
  const blocks = qrItems.flatMap((item) => Array.from({ length: repeat }).map(() => `
    <div class="label">
      <img src="${qrCodeImageUrl(item.qr_code_value)}" alt="QR item estoque">
      <div><strong>${item.epi_name}</strong></div>
      <div>Tamanho-Luvas: ${item.glove_size || 'N/A'}</div>
      <div>Tamanho: ${item.size || 'N/A'}</div>
      <div>Tamanho Uniforme: ${item.uniform_size || 'N/A'}</div>
      <div>Tamanho: ${item.size || 'N/A'}</div>
      <div>ID: ${item.stock_item_id || '-'}</div>
      <div>${item.qr_code_value}</div>
      <div>${item.unit_name || '-'}</div>
    </div>
  `)).join('');
  const popup = window.open('', '_blank');
  if (!popup) return;
  popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Etiquetas EPI</title><style>body{font-family:Arial,sans-serif;padding:12px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.label{border:1px dashed #999;padding:8px;text-align:center;font-size:12px}img{width:110px;height:110px}</style></head><body><div class="grid">${blocks}</div><script>window.onload=()=>window.print();<\/script></body></html>`);
  popup.document.close();
}

async function handleStockMovementSubmit(event) {
  event.preventDefault();
  if (!requirePermission('stock:adjust')) return;
  if (event.target.dataset.submitting === '1') return;
  event.target.dataset.submitting = '1';
  const submitButton = event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  try {
    const values = formValues(event.target);
    const companyField = document.getElementById('stock-company');
    const unitField = document.getElementById('stock-unit');
    const epiField = document.getElementById('stock-epi');
    if (!values.company_id) values.company_id = companyField?.value || state.user?.company_id || '';
    if (!values.unit_id) values.unit_id = unitField?.value || state.user?.operational_unit_id || '';
    if (!values.epi_id) values.epi_id = epiField?.value || '';
    if (!values.company_id) throw new Error('Campo obrigatório: company_id');
    if (!values.unit_id) throw new Error('Campo obrigatório: unit_id');
    if (!values.epi_id) throw new Error('Campo obrigatório: epi_id');
    values.actor_user_id = state.user.id;
    values.glove_size = String(values.glove_size || 'N/A');
    values.size = String(values.size || 'N/A');
    values.uniform_size = String(values.uniform_size || 'N/A');
    values.label_copies = Number(values.label_copies || 1);
    const result = await api('/api/stock/movements', { method: 'POST', body: JSON.stringify(values) });
    state.stockGeneratedLabels = result?.qr_labels || [];
    if (state.stockGeneratedLabels.length) printStockLabels(state.stockGeneratedLabels, values.label_copies);
    event.target.reset();
    event.target.elements.glove_size.value = 'N/A';
    event.target.elements.size.value = 'N/A';
    event.target.elements.uniform_size.value = 'N/A';
    event.target.elements.quantity.value = 1;
    event.target.elements.label_copies.value = 1;
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  } finally {
    event.target.dataset.submitting = '0';
    if (submitButton) submitButton.disabled = false;
  }
}

async function saveEmployeeMovement(event) {
  event.preventDefault();
  if (!requirePermission('employees:update')) return;
  try {
    const values = formValues(event.target);
    values.actor_user_id = state.user.id;
    await api('/api/employee-unit-movements', { method: 'POST', body: JSON.stringify(values) });
    event.target.reset();
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  }
}

async function renderEmployeeExternalAccess(token) {
  const payload = await api(`/api/employee-access?token=${encodeURIComponent(token)}`, { headers: {} });
  const employee = payload.employee || {};
  const deliveries = payload.deliveries || [];
  const fichas = payload.fichas || [];
  const requests = payload.requests || [];
  const feedbacks = payload.feedbacks || [];
  const availableEpis = payload.available_epis || [];
  document.body.innerHTML = `
    <section class="screen active">
      <div class="login-panel employee-portal-shell">
        <h2>Acesso do Colaborador</h2>
        <p><strong>${employee.employee_name || '-'}</strong> • ${employee.company_name || '-'}</p>
        <p>ID: ${employee.employee_id_code || '-'} | Setor: ${employee.sector || '-'}</p>
        <label>Assinatura digital (nome)</label>
        <input id="employee-signature-name" type="text" placeholder="Digite seu nome completo">
        <label>Assinatura por desenho (canvas)</label>
        <canvas id="employee-signature-canvas" width="520" height="180" style="border:1px solid #d9c7ba;border-radius:8px;background:#fff;"></canvas>
        <div class="action-group"><button id="employee-signature-clear" class="ghost" type="button">Limpar assinatura</button></div>
        <label>Período da ficha</label>
        <select id="employee-ficha-period">${fichas.map((item) => `<option value="${item.id}">${formatDate(item.period_start)} a ${formatDate(item.period_end)} (${item.status})</option>`).join('')}</select>
        <button id="employee-sign-batch" class="btn btn-primary" type="button">Assinar em lote (período)</button>
        <button id="employee-download-pdf" class="btn btn-secondary" type="button">Baixar PDF da ficha</button>
        <div class="table-wrap users-table-wrap"><table><thead><tr><th>EPI</th><th>Entrega</th><th>Próxima troca</th><th>Assinatura</th><th>Ação</th></tr></thead><tbody>${deliveries.map((item) => `<tr><td>${item.epi_name}</td><td>${formatDate(item.delivery_date)}</td><td>${formatDate(item.next_replacement_date)}</td><td>${item.signature_name || '-'}</td><td><button class="ghost" data-employee-sign="${item.id}">Assinar</button></td></tr>`).join('') || '<tr><td colspan="5">Sem EPIs disponíveis.</td></tr>'}</tbody></table></div>
        <p>ID: ${employee.employee_id_code || '-'} | Setor: ${employee.sector || '-'} | Escala: ${employee.schedule_type || '-'}</p>
        <div class="portal-tabs">
          <button class="menu-link active" data-portal-tab="ficha">Ficha de EPI</button>
          <button class="menu-link" data-portal-tab="solicitacao">Solicitação de EPI</button>
          <button class="menu-link" data-portal-tab="avaliacao">Avaliação / Sugestão</button>
        </div>
        <div data-portal-pane="ficha">
          <label>Assinatura digital (nome)</label>
          <input id="employee-signature-name" type="text" placeholder="Digite seu nome completo">
          <label>Assinatura por desenho (canvas)</label>
          <canvas id="employee-signature-canvas" width="520" height="180" style="border:1px solid #d9c7ba;border-radius:8px;background:#fff;"></canvas>
          <div class="action-group"><button id="employee-signature-clear" class="ghost" type="button">Limpar assinatura</button></div>
          <label>Período da ficha</label>
          <select id="employee-ficha-period">${fichas.map((item) => `<option value="${item.id}">${formatDate(item.period_start)} a ${formatDate(item.period_end)} (${item.status})</option>`).join('')}</select>
          <button id="employee-sign-batch" class="btn btn-primary" type="button">Assinar em lote (período)</button>
          <button id="employee-download-pdf" class="btn btn-secondary" type="button">Baixar PDF da ficha</button>
          <div class="table-wrap users-table-wrap"><table><thead><tr><th>EPI</th><th>Entrega</th><th>Próxima troca</th><th>Assinatura</th><th>Ação</th></tr></thead><tbody>${deliveries.map((item) => `<tr><td>${item.epi_name}</td><td>${formatDate(item.delivery_date)}</td><td>${formatDate(item.next_replacement_date)}</td><td>${item.signature_name || '-'}</td><td><button class="ghost" data-employee-sign="${item.id}">Assinar</button></td></tr>`).join('') || '<tr><td colspan="5">Sem EPIs disponíveis.</td></tr>'}</tbody></table></div>
        </div>
        <div data-portal-pane="solicitacao" style="display:none;">
          <h3>Solicitar EPI cadastrado</h3>
          <label>EPI disponível</label>
          <select id="employee-request-epi">${availableEpis.map((item) => `<option value="${item.id}">${item.name} (${item.purchase_code || '-'})</option>`).join('')}</select>
          <label>Quantidade</label>
          <input id="employee-request-quantity" type="number" min="1" value="1">
          <label>Justificativa</label>
          <textarea id="employee-request-justification" rows="3" placeholder="Motivo da solicitação"></textarea>
          <button id="employee-request-submit" class="btn btn-primary" type="button">Enviar solicitação</button>
          <div class="table-wrap users-table-wrap"><table><thead><tr><th>ID</th><th>EPI</th><th>Qtd</th><th>Status</th><th>Data</th></tr></thead><tbody>${requests.map((item) => `<tr><td>#${item.id}</td><td>${item.epi_name}</td><td>${item.quantity}</td><td>${item.status}</td><td>${formatDate(item.requested_at)}</td></tr>`).join('') || '<tr><td colspan="5">Sem solicitações.</td></tr>'}</tbody></table></div>
        </div>
        <div data-portal-pane="avaliacao" style="display:none;">
          <h3>Avaliação de uso e sugestões</h3>
          <label>EPI utilizado</label>
          <select id="employee-feedback-epi"><option value="">Selecione (opcional para nova sugestão)</option>${availableEpis.map((item) => `<option value="${item.id}">${item.name} (${item.purchase_code || '-'})</option>`).join('')}</select>
          <div class="grid cols-2">
            <label>Conforto (0-5)<input id="employee-rate-comfort" type="number" min="0" max="5" value="0"></label>
            <label>Qualidade (0-5)<input id="employee-rate-quality" type="number" min="0" max="5" value="0"></label>
            <label>Adequação (0-5)<input id="employee-rate-adequacy" type="number" min="0" max="5" value="0"></label>
            <label>Desempenho (0-5)<input id="employee-rate-performance" type="number" min="0" max="5" value="0"></label>
          </div>
          <label>Observações</label>
          <textarea id="employee-feedback-comments" rows="3"></textarea>
          <label>Sugestão de melhoria</label>
          <textarea id="employee-feedback-improvement" rows="2"></textarea>
          <label>Sugestão de novo EPI para aquisição</label>
          <input id="employee-feedback-new-name" type="text" placeholder="Nome do EPI sugerido">
          <textarea id="employee-feedback-new-notes" rows="2" placeholder="Detalhes da sugestão"></textarea>
          <button id="employee-feedback-submit" class="btn btn-primary" type="button">Enviar avaliação/sugestão</button>
          <div class="table-wrap users-table-wrap"><table><thead><tr><th>ID</th><th>EPI</th><th>Status</th><th>Avaliação</th><th>Sugestão nova</th></tr></thead><tbody>${feedbacks.map((item) => `<tr><td>#${item.id}</td><td>${item.epi_name || '-'}</td><td>${item.status}</td><td>C:${item.comfort_rating} Q:${item.quality_rating} A:${item.adequacy_rating} D:${item.performance_rating}</td><td>${item.suggested_new_epi_name || '-'}</td></tr>`).join('') || '<tr><td colspan="5">Sem avaliações registradas.</td></tr>'}</tbody></table></div>
        </div>
      </div>
    </section>`;
  const canvas = document.getElementById('employee-signature-canvas');
  const ctx = canvas?.getContext('2d');
  let drawing = false;
  const drawStart = (x, y) => { drawing = true; ctx?.beginPath(); ctx?.moveTo(x, y); };
  const drawMove = (x, y) => { if (!drawing) return; ctx?.lineTo(x, y); ctx.lineWidth = 2; ctx.strokeStyle = '#333'; ctx.stroke(); };
  const stopDraw = () => { drawing = false; };
  canvas?.addEventListener('mousedown', (event) => drawStart(event.offsetX, event.offsetY));
  canvas?.addEventListener('mousemove', (event) => drawMove(event.offsetX, event.offsetY));
  canvas?.addEventListener('mouseup', stopDraw);
  canvas?.addEventListener('mouseleave', stopDraw);
  canvas?.addEventListener('touchstart', (event) => {
    const rect = canvas.getBoundingClientRect();
    const touch = event.touches[0];
    drawStart(touch.clientX - rect.left, touch.clientY - rect.top);
    event.preventDefault();
  }, { passive: false });
  canvas?.addEventListener('touchmove', (event) => {
    const rect = canvas.getBoundingClientRect();
    const touch = event.touches[0];
    drawMove(touch.clientX - rect.left, touch.clientY - rect.top);
    event.preventDefault();
  }, { passive: false });
  canvas?.addEventListener('touchend', stopDraw);
  document.getElementById('employee-signature-clear')?.addEventListener('click', () => ctx?.clearRect(0, 0, canvas.width, canvas.height));

  document.getElementById('employee-download-pdf')?.addEventListener('click', () => {
    window.open(`/api/employee-access/pdf?token=${encodeURIComponent(token)}`, '_blank');
  });
  document.querySelectorAll('[data-portal-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-portal-tab]').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('[data-portal-pane]').forEach((pane) => { pane.style.display = 'none'; });
      button.classList.add('active');
      const pane = document.querySelector(`[data-portal-pane="${button.dataset.portalTab}"]`);
      if (pane) pane.style.display = 'block';
    });
  });
  document.getElementById('employee-sign-batch')?.addEventListener('click', async () => {
    const fichaPeriodId = document.getElementById('employee-ficha-period')?.value;
    if (!fichaPeriodId) return alert('Nenhum período disponível para assinatura em lote.');
    const signatureName = String(document.getElementById('employee-signature-name')?.value || '').trim();
    const signatureData = canvas?.toDataURL('image/png') || '';
    try {
      await api('/api/employee-sign-batch', { method: 'POST', body: JSON.stringify({ token, ficha_period_id: fichaPeriodId, signature_name: signatureName, signature_data: signatureData }) });
      alert('Assinatura em lote aplicada.');
      await renderEmployeeExternalAccess(token);
    } catch (error) {
      alert(error.message);
    }
  });
  document.querySelectorAll('[data-employee-sign]').forEach((button) => {
    button.addEventListener('click', async () => {
      const signatureName = String(document.getElementById('employee-signature-name')?.value || '').trim();
      const signatureData = canvas?.toDataURL('image/png') || '';
      try {
        await api('/api/employee-sign', { method: 'POST', body: JSON.stringify({ token, delivery_id: button.dataset.employeeSign, signature_name: signatureName, signature_data: signatureData }) });
        alert('Assinatura registrada com sucesso.');
        await renderEmployeeExternalAccess(token);
      } catch (error) {
        alert(error.message);
      }
    });
  });
  document.getElementById('employee-request-submit')?.addEventListener('click', async () => {
    try {
      await api('/api/requests', {
        method: 'POST',
        body: JSON.stringify({
          token,
          epi_id: Number(document.getElementById('employee-request-epi')?.value || 0),
          quantity: Number(document.getElementById('employee-request-quantity')?.value || 1),
          justification: String(document.getElementById('employee-request-justification')?.value || '').trim()
        })
      });
      alert('Solicitação enviada com sucesso.');
      await renderEmployeeExternalAccess(token);
    } catch (error) {
      alert(error.message);
    }
  });
  document.getElementById('employee-feedback-submit')?.addEventListener('click', async () => {
    try {
      await api('/api/employee-feedback', {
        method: 'POST',
        body: JSON.stringify({
          token,
          epi_id: document.getElementById('employee-feedback-epi')?.value || null,
          comfort_rating: Number(document.getElementById('employee-rate-comfort')?.value || 0),
          quality_rating: Number(document.getElementById('employee-rate-quality')?.value || 0),
          adequacy_rating: Number(document.getElementById('employee-rate-adequacy')?.value || 0),
          performance_rating: Number(document.getElementById('employee-rate-performance')?.value || 0),
          comments: String(document.getElementById('employee-feedback-comments')?.value || '').trim(),
          improvement_suggestion: String(document.getElementById('employee-feedback-improvement')?.value || '').trim(),
          suggested_new_epi_name: String(document.getElementById('employee-feedback-new-name')?.value || '').trim(),
          suggested_new_epi_notes: String(document.getElementById('employee-feedback-new-notes')?.value || '').trim()
        })
      });
      alert('Avaliação enviada com sucesso.');
      await renderEmployeeExternalAccess(token);
    } catch (error) {
      alert(error.message);
    }
  });
}

function syncUserFilters() { state.userFilters.company_id = refs.userFilterCompany.value; state.userFilters.role = refs.userFilterRole.value; state.userFilters.active = refs.userFilterStatus.value; state.userFilters.search = refs.userFilterSearch.value.trim().toLowerCase(); renderTables(); }

async function init() {
  const employeeToken = new URLSearchParams(window.location.search).get('employee_token');
  if (employeeToken) {
    await renderEmployeeExternalAccess(String(employeeToken).trim());
    return;
  }

  preloadLoginFromUrl();
  markRequiredFieldLabels();

  refs.loginForm?.addEventListener('submit', handleLogin);
  refs.recoveryToggle?.addEventListener('click', toggleRecoveryPanel);
  refs.recoverySubmit?.addEventListener('click', handlePasswordRecovery);
  refs.userForm?.addEventListener('submit', saveUser);
  refs.companyForm?.addEventListener('submit', saveCompany);
  refs.platformBrandForm?.addEventListener('submit', savePlatformBrand);
  refs.commercialSettingsForm?.addEventListener('submit', saveCommercialSettings);
  refs.commercialForm?.addEventListener('submit', saveCommercial);

  refs.commercialCompany?.addEventListener('change', () => {
    fillCommercialForm(refs.commercialCompany.value);
    renderCommercialHistory();
  });

  refs.commercialForm?.elements.plan_name?.addEventListener('change', () => refreshCommercialPreview());
  refs.commercialForm?.elements.user_limit?.addEventListener('input', () => refreshCommercialPreview());
  refs.commercialForm?.elements.addendum_enabled?.addEventListener('change', () => refreshCommercialPreview());

  refs.commercialFilterStatus?.addEventListener('change', syncCommercialFilter);
  refs.commercialFilterDateFrom?.addEventListener('change', syncCommercialFilter);
  refs.commercialFilterDateTo?.addEventListener('change', syncCommercialFilter);
  refs.commercialFilterActor?.addEventListener('change', syncCommercialFilter);

  refs.commercialContractPdf?.addEventListener('click', downloadCommercialContractPdf);
  refs.commercialExport?.addEventListener('click', exportCommercialHistory);
  refs.commercialExportExcel?.addEventListener('click', exportCommercialExcel);
  refs.commercialPrint?.addEventListener('click', printCommercialHistory);

  refs.companyLogoFile?.addEventListener('change', handleCompanyLogoUpload);
  refs.platformLogoFile?.addEventListener('change', handlePlatformLogoUpload);
  document.getElementById('epi-photo-file')?.addEventListener('change', handleEpiPhotoUpload);

  refs.companyForm?.elements.cnpj?.addEventListener('blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
  });

  refs.platformBrandForm?.elements.cnpj?.addEventListener('blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
  });

  document.getElementById('unit-form')?.addEventListener('submit', (event) => saveSimpleForm(event, '/api/units', 'units:create'));
  document.getElementById('employee-form')?.addEventListener('submit', (event) => saveSimpleForm(event, '/api/employees', 'employees:create'));
  document.getElementById('epi-form')?.addEventListener('submit', (event) => saveSimpleForm(event, '/api/epis', 'epis:create'));
  document.getElementById('delivery-form')?.addEventListener('submit', (event) => saveSimpleForm(event, '/api/deliveries', 'deliveries:create'));
  document.getElementById('stock-form')?.addEventListener('submit', handleStockMovementSubmit);

  document.getElementById('epi-company')?.addEventListener('change', () => {
    syncEpiUnitOptions();
  });
  document.getElementById('epi-unit')?.addEventListener('change', () => {
    if (String(document.getElementById('epi-joinventure-active')?.value || '').trim()) {
      applyEpiJoinventureRules();
    }
  });
  document.getElementById('epi-joinventure-active')?.addEventListener('change', applyEpiJoinventureRules);
  document.getElementById('employee-company')?.addEventListener('change', () => {
    syncEmployeeUnitOptions();
  });
  document.getElementById('epi-joinventure-add')?.addEventListener('click', addJoinventure);
  document.getElementById('epi-joinventure-name')?.addEventListener('keyup', (event) => {
    if (event.key === 'Enter') addJoinventure();
  });
  document.getElementById('epi-joinventure-list')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-joinventure-remove]');
    if (!button) return;
    removeJoinventure(button.dataset.joinventureRemove || '');
  });
  renderJoinventureList();
  renderEpiPhotoPreview(document.getElementById('epi-photo-data')?.value || '');

  document.getElementById('movement-form')?.addEventListener('submit', saveEmployeeMovement);
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    stopDeliveryQrCamera();
    clearSession();
    showScreen(false);
  });

  document.getElementById('delivery-company')?.addEventListener('change', () => {
    syncDeliveryOptions();
    refreshDeliveryContext();
  });
  document.getElementById('stock-company')?.addEventListener('change', async () => { syncStockOptions(); await loadStockEpis(); scheduleStockMovementSearchLoad(); });
  document.getElementById('stock-unit')?.addEventListener('change', async () => { syncStockOptions(); await loadStockEpis(); scheduleStockMovementSearchLoad(); });
  document.getElementById('stock-epi')?.addEventListener('change', () => {
    syncStockSizeDefaults();
    syncSelectedEpiMinimumStockField();
    renderStockEpiSearchResults();
  });
  document.getElementById('delivery-unit-filter')?.addEventListener('change', syncDeliveryOptions);
  bindSearchInput(document.getElementById('delivery-employee-search'), syncDeliveryOptions, 140);
  document.getElementById('delivery-qr-scan')?.addEventListener('change', handleDeliveryQrScan);
  document.getElementById('delivery-qr-scan')?.addEventListener('keyup', (event) => {
    if (event.key === 'Enter') handleDeliveryQrScan();
  });
  document.getElementById('delivery-qr-start')?.addEventListener('click', startDeliveryQrCamera);
  document.getElementById('delivery-qr-stop')?.addEventListener('click', stopDeliveryQrCamera);
  document.getElementById('delivery-qr-image')?.addEventListener('change', handleDeliveryQrImageUpload);
  document.getElementById('delivery-employee-qr-apply')?.addEventListener('click', applyEmployeeQrLookup);
  document.getElementById('delivery-employee-qr-scan')?.addEventListener('keyup', (event) => {
    if (event.key === 'Enter') applyEmployeeQrLookup();
  });
  document.getElementById('delivery-employee-link-generate')?.addEventListener('click', generateDeliveryEmployeeLink);
  document.getElementById('delivery-employee')?.addEventListener('change', refreshDeliveryContext);
  document.getElementById('delivery-epi')?.addEventListener('change', refreshDeliveryContext);

  bindSearchInput(refs.userFilterSearch, syncUserFilters, 140);
  refs.userFilterCompany?.addEventListener('change', syncUserFilters);
  refs.userFilterRole?.addEventListener('change', syncUserFilters);
  refs.userFilterStatus?.addEventListener('change', syncUserFilters);

  refs.userForm?.elements.company_id?.addEventListener('change', () => {
    populateLinkedEmployeeOptions();
    syncUserEmployeeLink();
  });
  refs.userForm?.elements.linked_employee_id?.addEventListener('change', syncUserEmployeeLink);
  refs.userForm?.elements.role?.addEventListener('change', syncUserFormAccess);
  bindSearchInput(refs.userLinkedEmployeeSearch, () => {
    const previousValue = String(refs.userForm?.elements.linked_employee_id?.value || '');
    populateLinkedEmployeeOptions();
    if (refs.userForm?.elements.linked_employee_id) {
      const stillExists = Array.from(refs.userForm.elements.linked_employee_id.options || []).some((option) => String(option.value) === previousValue);
      refs.userForm.elements.linked_employee_id.value = stillExists ? previousValue : '';
    }
    syncUserEmployeeLink();
  });
  refs.userLinkedEmployeeResults?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-user-linked-pick]');
    if (!button || !refs.userForm?.elements?.linked_employee_id) return;
    refs.userForm.elements.linked_employee_id.value = String(button.dataset.userLinkedPick || '');
    syncUserEmployeeLink();
  });
  refs.fichaEmployee?.addEventListener('change', renderFicha);
  bindSearchInput(refs.approvedEpiSearchName, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchProtection, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchCa, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchManufacturer, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchSection, renderApprovedEpis, 120);
  refs.stockFilterProtection?.addEventListener('change', loadStockEpis);
  bindSearchInput(refs.stockFilterName, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterSection, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterManufacturer, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterCa, loadStockEpis, 220);
  bindSearchInput(refs.stockEpiMovementSearchName, scheduleStockMovementSearchLoad, 150);
  bindSearchInput(refs.stockEpiMovementSearchManufacturer, scheduleStockMovementSearchLoad, 150);
  bindSearchInput(refs.stockEpiMovementSearchName, renderStockEpiSearchResults, 80);
  bindSearchInput(refs.stockEpiMovementSearchManufacturer, renderStockEpiSearchResults, 80);
  refs.stockEpiMovementSearchResults?.addEventListener('click', (event) => {
    const pickButton = event.target.closest('[data-stock-epi-pick]');
    if (!pickButton) return;
    selectStockEpiFromSearch(pickButton.dataset.stockEpiPick);
  });

  document.getElementById('report-filter-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!requirePermission('reports:view')) return;
    await renderReports(formValues(event.target));
  });

  document.querySelectorAll('.menu-link').forEach((button) =>
    button.addEventListener('click', () => showView(button.dataset.view))
  );

  refs.companiesTable?.addEventListener('click', (event) => {
    if (event.target.dataset.companyDetails) {
      state.selectedCompanyId = event.target.dataset.companyDetails;
      renderCompanies();
      renderCompanyDetails(event.target.dataset.companyDetails);
    }
    if (event.target.dataset.companyEdit) startEditCompany(event.target.dataset.companyEdit);
    if (event.target.dataset.companyLogo) openCompanyLogoEditor(event.target.dataset.companyLogo);
    if (event.target.dataset.companyToggle) toggleCompany(event.target.dataset.companyToggle, Number(event.target.dataset.companyActive));
    if (event.target.dataset.companyCommercial) {
      state.selectedCompanyId = event.target.dataset.companyCommercial;
      fillCommercialForm(event.target.dataset.companyCommercial);
      showView('comercial');
    }
  });

  document.getElementById('comercial-view')?.addEventListener('click', (event) => {
    if (event.target.dataset.companyCommercial) {
      fillCommercialForm(event.target.dataset.companyCommercial);
    }
    if (event.target.dataset.commercialToggle) {
      toggleCommercialStatus(event.target.dataset.commercialToggle, event.target.dataset.commercialMode);
    }
  });

  refs.usersTable?.addEventListener('click', (event) => {
    if (event.target.dataset.userEdit) startEditUser(event.target.dataset.userEdit);
    if (event.target.dataset.userDelete) deleteUser(event.target.dataset.userDelete);
    if (event.target.dataset.userEmployeeQr) printEmployeeAccessQr(event.target.dataset.userEmployeeQr);
    if (event.target.dataset.userPromoteAdmin) updateUserAccess(event.target.dataset.userPromoteAdmin, { role: 'admin' }, 'Perfil alterado para Administrador.');
    if (event.target.dataset.userPromoteGeneral) updateUserAccess(event.target.dataset.userPromoteGeneral, { role: 'general_admin' }, 'Perfil alterado para Administrador Geral.');
    if (event.target.dataset.userDemoteAdmin) updateUserAccess(event.target.dataset.userDemoteAdmin, { role: 'user' }, 'Administrador rebaixado para Usuário.');
    if (event.target.dataset.userDemoteGeneral) updateUserAccess(event.target.dataset.userDemoteGeneral, { role: 'admin' }, 'Administrador Geral rebaixado para Administrador.');
    if (event.target.dataset.userToggle) {
      const target = state.users.find((item) => String(item.id) === String(event.target.dataset.userToggle));
      if (target) updateUserAccess(target.id, { active: Number(target.active) === 1 ? 0 : 1 }, Number(target.active) === 1 ? 'Usuário desativado.' : 'Usuário reativado.');
    }
  });

  refs.employeesTable?.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.employeeLink) printEmployeePortalLink(button.dataset.employeeLink);
    if (button.dataset.employeeEdit) startEditEmployee(button.dataset.employeeEdit);
    if (button.dataset.employeeDelete) deleteRegistryEntity('/api/employees', button.dataset.employeeDelete, 'employees:delete', 'Remover este colaborador?');
  });
  refs.employeesOpsTable?.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.employeeLink) printEmployeePortalLink(button.dataset.employeeLink);
    if (button.dataset.employeeEdit) startEditEmployee(button.dataset.employeeEdit);
    if (button.dataset.employeeDelete) deleteRegistryEntity('/api/employees', button.dataset.employeeDelete, 'employees:delete', 'Remover este colaborador?');
  });
  refs.unitsTable?.addEventListener('click', (event) => {
    if (event.target.dataset.unitEdit) startEditUnit(event.target.dataset.unitEdit);
    if (event.target.dataset.unitDelete) deleteRegistryEntity('/api/units', event.target.dataset.unitDelete, 'units:delete', 'Remover esta unidade?');
  });
  refs.episTable?.addEventListener('click', (event) => {
    if (event.target.dataset.epiEdit) startEditEpi(event.target.dataset.epiEdit);
    if (event.target.dataset.epiDelete) deleteRegistryEntity('/api/epis', event.target.dataset.epiDelete, 'epis:delete', 'Remover este EPI?');
  });


  document.getElementById('stock-minimum-edit')?.addEventListener('click', () => {
    if (!canManageMinimumStock()) {
      alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
      return;
    }
    const valueField = document.getElementById('stock-minimum-value');
    if (valueField) valueField.readOnly = false;
  });

  document.getElementById('stock-minimum-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!canManageMinimumStock()) {
      alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
      return;
    }
    if (!requirePermission('stock:adjust')) return;
    try {
      const epiId = Number(document.getElementById('stock-minimum-epi-id')?.value || 0);
      const minimumStock = Number(document.getElementById('stock-minimum-value')?.value || 0);
      await api('/api/stock/minimum', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id, epi_id: epiId, minimum_stock: minimumStock }) });
      document.getElementById('stock-minimum-value').readOnly = true;
      await loadBootstrap();
      alert('Estoque mínimo salvo com sucesso.');
    } catch (error) {
      alert(error.message);
    }
  });

  refs.stockEpisTable?.addEventListener('click', (event) => {
    const saveButton = event.target.closest('[data-stock-minimum-save]');
    if (saveButton) {
      saveMinimumStockByEpi(saveButton.dataset.stockMinimumSave);
      return;
    }
    const button = event.target.closest('[data-stock-minimum-edit]');
    if (!button) return;
    openMinimumStockEditor(button.dataset.stockMinimumEdit);
  });

  document.getElementById('stock-minimum-selected-edit')?.addEventListener('click', () => {
    if (!canManageMinimumStock()) {
      alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mínimo.');
      return;
    }
    if (!selectedStockEpi()) {
      alert('Selecione um EPI para editar o estoque mínimo.');
      return;
    }
    toggleSelectedMinimumStockEditMode(true);
  });

  document.getElementById('stock-minimum-selected-save')?.addEventListener('click', saveSelectedEpiMinimumStock);
  document.getElementById('stock-minimum-selected-value')?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    if (!state.stockMinimumEditor.editing) return;
    event.preventDefault();
    saveSelectedEpiMinimumStock();
  });

  document.getElementById('stock-print-labels')?.addEventListener('click', () => {
    if (!state.stockGeneratedLabels.length) return alert('Nenhuma etiqueta gerada ainda. Registre uma entrada no estoque primeiro.');
    const copies = Number(document.querySelector('#stock-form [name="label_copies"]')?.value || 1);
    printStockLabels(state.stockGeneratedLabels, copies);
  });

  window.addEventListener('beforeunload', stopDeliveryQrCamera);

  resetCompanyForm();


const deliveryDateInput = document.querySelector('#delivery-form input[name="delivery_date"]');
if (deliveryDateInput) {
  deliveryDateInput.value = new Date().toISOString().split('T')[0];
}

const nextReplacementInput = document.querySelector('#delivery-form input[name="next_replacement_date"]');
if (nextReplacementInput) {
  nextReplacementInput.value = new Date().toISOString().split('T')[0];
}

  showScreen(Boolean(state.user));
  if (state.user) await loadBootstrap();
}

document.addEventListener('DOMContentLoaded', () => {
  init().catch((error) => {
    console.error(error);
    setLoginMessage('Erro ao carregar a tela de login. Atualize a página (Ctrl+F5).', true);
  });
});
