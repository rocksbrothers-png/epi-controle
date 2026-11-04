/*
 * Checkout servido pelo backend (mesma origem da API /api/payments/*).
 *
 * Arquitetura (fonte única de verdade no backend):
 *  - O site institucional apenas apresenta planos e redireciona para esta
 *    página, passando ?plan=<chave>&cycle=<ciclo>&lang=<idioma>.
 *  - Toda a lógica de Mercado Pago (planos, assinatura, Pix, boleto, cartão,
 *    webhook, validação) vive no backend Python. Esta página só usa a Public
 *    Key para tokenizar o cartão e consome os endpoints do backend.
 *  - O Access Token NUNCA chega ao frontend.
 *
 * UX (PR 4): seleção rica de forma de pagamento (Mensal/Anual recorrentes,
 * PIX e Boleto), aviso de renovação automática e resumo do pedido. Os preços
 * dos dois ciclos vêm do catálogo do backend (uma chamada por ciclo).
 */

const API = {
  config: '/api/payments/config',
  catalog: '/api/payments/catalog',
  subscriptions: '/api/payments/subscriptions',
  pix: '/api/payments/pix',
  boleto: '/api/payments/boleto',
  status: '/api/payments/status',
};



const params = new URLSearchParams(window.location.search);
const ctx = {
  plan: (params.get('plan') || '').trim(),
  cycle: (params.get('cycle') || 'monthly').trim().toLowerCase() === 'annual' ? 'annual' : 'monthly',
  lang: globalThis.EpiI18n.SUPPORTED.find(code => code.toLowerCase() === (params.get('lang') || '').trim().toLowerCase())
    || ({pt:'pt-BR',en:'en-GB',es:'es-ES',fr:'fr-FR',nb:'nb-NO',no:'nb-NO'})[(params.get('lang') || 'pt').trim().toLowerCase().split('-')[0]] || 'pt-BR',
};
const t = (key, vars) => globalThis.EpiI18n.t('checkout.' + key, vars);

const $ = (id) => document.getElementById(id);
const money = (value, currency = 'BRL') =>
  new Intl.NumberFormat(ctx.lang, { style: 'currency', currency }).format(value || 0);

let mpPublicKey = '';
// plans[cycle] = item do catálogo do plano escolhido naquele ciclo.
const plans = { monthly: null, annual: null };
let options = [];          // opções de pagamento construídas
let selected = null;       // opção selecionada
let cardBrickController = null;
let statusTimer = null;

// Idempotência (1J-C): nonce ESTÁVEL por intenção de checkout. Gerado uma vez
// por seleção (plano/ciclo/método); reutilizado em TODO retry da MESMA intenção
// (timeout, duplo clique, re-tokenização do cartão) para que o backend/Mercado
// Pago nunca criem um segundo preapproval. Uma nova seleção gera uma nova chave.
let checkoutIntentKey = '';
function newIntentKey() {
  try {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return `corp-${window.crypto.randomUUID()}`;
    }
    if (window.crypto && window.crypto.getRandomValues) {
      const b = new Uint8Array(16);
      window.crypto.getRandomValues(b);
      return 'corp-' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
    }
  } catch (_e) { /* fallthrough */ }
  return `corp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function showResult(data) {
  $('result').textContent = data == null ? '' : (typeof data === 'string' ? data : JSON.stringify(data, null, 2));
}

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return res.json().catch(() => ({}));
}

// Token da sessão autenticada (mesma origem da API). O checkout Corporate é
// AUTENTICADO (1G-C, #1009/#1010): a identidade/empresa vêm do Bearer, não do
// corpo. A chave de storage espelha STORAGE_KEYS.token do app (constants.js).
const SESSION_TOKEN_KEY = 'epi-session-v4-token';
function getAuthToken() {
  try { return (window.localStorage.getItem(SESSION_TOKEN_KEY) || '').trim(); }
  catch (_e) { return ''; }
}

async function postJson(url, body) {
  const token = getAuthToken();
  // Sem sessão não há como provar a identidade: o servidor responderia 401.
  // Falha cedo, com mensagem clara, sem disparar a requisição.
  if (!token) { throw new Error(t('login_required')); }
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error((data.error && data.error.message) || `Erro HTTP ${res.status}`);
  }
  return data;
}

function addMonths(date, months) {
  const d = new Date(date.getTime());
  d.setMonth(d.getMonth() + months);
  return d;
}

function fmtDate(date) {
  return new Intl.DateTimeFormat(ctx.lang, { dateStyle: 'medium' }).format(date);
}

function planLabel() {
  const p = plans.monthly || plans.annual;
  return (p && (p.label || p.key)) || ctx.plan || '—';
}

function benefitsFor() {
  const p = plans.monthly || plans.annual;
  const list = [];
  if (p && p.max_users) list.push(t('users_up_to', {n:p.max_users, count:Number(p.max_users)}));
  list.push(t('benefit_support'));
  list.push(t('benefit_cancel'));
  return list;
}

/* Constrói as opções a partir dos preços disponíveis nos dois ciclos. */
function buildOptions() {
  const opts = [];
  if (plans.monthly && plans.monthly.amount != null) {
    opts.push({ id: 'card-monthly', method: 'card', cycle: 'monthly', recurring: true,
      amount: plans.monthly.amount, plan_id: plans.monthly.plan_id,
      title: t('opt_monthly_title'), desc: t('opt_monthly_desc') });
  }
  if (plans.annual && plans.annual.amount != null) {
    let badge = '';
    if (plans.monthly && plans.monthly.amount) {
      const saving = plans.monthly.amount * 12 - plans.annual.amount;
      if (saving > 0) badge = `${t('save_badge')} ${money(saving, plans.annual.currency)}`;
    }
    opts.push({ id: 'card-annual', method: 'card', cycle: 'annual', recurring: true,
      amount: plans.annual.amount, plan_id: plans.annual.plan_id,
      title: t('opt_annual_title'), desc: t('opt_annual_desc'), badge });
  }
  // PIX / Boleto: pagamento avulso no ciclo originalmente escolhido (renovação manual).
  const oneTime = plans[ctx.cycle] || plans.monthly || plans.annual;
  if (oneTime && oneTime.amount != null) {
    opts.push({ id: 'pix', method: 'pix', cycle: oneTime.cycle, recurring: false,
      amount: oneTime.amount, title: t('opt_pix_title'), desc: t('opt_pix_desc') });
    opts.push({ id: 'boleto', method: 'boleto', cycle: oneTime.cycle, recurring: false,
      amount: oneTime.amount, title: t('opt_boleto_title'), desc: t('opt_boleto_desc') });
  }
  return opts;
}

function cycleLabel(opt) {
  if (!opt.recurring) return t('manual_renew');
  return opt.cycle === 'annual' ? t('annual') : t('monthly');
}

function methodLabel(opt) {
  if (opt.method === 'pix') return t('method_pix');
  if (opt.method === 'boleto') return t('method_boleto');
  return t('method_card');
}

function renderOptions() {
  const box = $('pay-options');
  box.innerHTML = '';
  options.forEach((opt) => {
    const per = opt.cycle === 'annual' ? t('per_year') : t('per_month');
    const priceText = opt.recurring ? `${money(opt.amount, plans[opt.cycle].currency)}${per}` : money(opt.amount);
    const el = document.createElement('label');
    el.className = 'pay-opt' + (selected && selected.id === opt.id ? ' selected' : '');
    el.innerHTML = `
      <input type="radio" name="paymethod" value="${opt.id}" ${selected && selected.id === opt.id ? 'checked' : ''} />
      <div class="opt-body">
        <div class="opt-title">
          <span>${opt.title}${opt.badge ? `<span class="badge">${opt.badge}</span>` : ''}</span>
          <span class="opt-price">${priceText}</span>
        </div>
        <div class="opt-desc">${opt.desc}</div>
      </div>`;
    el.querySelector('input').addEventListener('change', () => selectOption(opt.id));
    box.appendChild(el);
  });
}

function renderSummary() {
  if (!selected) return;
  const currency = (plans[selected.cycle] && plans[selected.cycle].currency) || 'BRL';
  const per = selected.cycle === 'annual' ? t('per_year') : t('per_month');
  $('s-plan').textContent = planLabel();
  $('s-value').textContent = selected.recurring ? `${money(selected.amount, currency)}${per}` : money(selected.amount, currency);
  $('s-cycle').textContent = cycleLabel(selected);
  $('s-method').textContent = methodLabel(selected);
  if (selected.recurring) {
    const next = addMonths(new Date(), selected.cycle === 'annual' ? 12 : 1);
    $('s-next').textContent = fmtDate(next);
  } else {
    $('s-next').textContent = t('manual_renew');
  }
  const benefits = benefitsFor();
  $('s-benefits').innerHTML = benefits.map((b) => `<li>${b}</li>`).join('');
  $('s-total').textContent = money(selected.amount, currency);
  const labelKey = selected.recurring ? 'subscribe_now' : 'finish_payment';
  $('payBtn').textContent = globalThis.EpiI18n.textFor($('payBtn'), 'checkout.' + labelKey, t(labelKey));
}

function selectOption(id) {
  selected = options.find((o) => o.id === id) || null;
  // Nova seleção = nova intenção → nova chave de idempotência. Retries da MESMA
  // seleção (sem passar por aqui de novo) mantêm a mesma chave.
  checkoutIntentKey = newIntentKey();
  renderOptions();
  renderSummary();
  $('renew-note').hidden = !(selected && selected.recurring);
  $('card-fields').hidden = !(selected && selected.method === 'card');
  $('qr').innerHTML = '';
  $('status-line').textContent = '';
  showResult('');
  if (selected && selected.method === 'card') {
    mountCardBrick().catch((e) => showResult(String(e)));
  }
}

function basePayload() {
  // Contrato 1G-C (#1009/#1010): o cliente envia APENAS plan_key/cycle/
  // payer_email/payment_method (e card_token no cartão). Empresa, tenant, ator,
  // auditoria, preço e o plano do Mercado Pago são SEMPRE server-side — enviar
  // campos de autoridade agora resulta em HTTP 400.
  return {
    plan_key: ctx.plan,
    cycle: selected ? selected.cycle : ctx.cycle,
    payer_email: $('payer_email').value.trim(),
    payment_method: selected ? selected.method : '',
    // Nonce da intenção (1J-C): estável no retry, novo a cada nova seleção.
    idempotency_key: checkoutIntentKey || (checkoutIntentKey = newIntentKey()),
  };
}

function showPixQr(payment) {
  const qr = $('qr');
  qr.innerHTML = `<p>${t('pix_instructions')}</p>`;
  if (payment.qr_code_base64) {
    const img = document.createElement('img');
    img.alt = 'QR Code Pix';
    img.src = `data:image/png;base64,${payment.qr_code_base64}`;
    qr.appendChild(img);
  }
  if (payment.qr_code) {
    const code = document.createElement('textarea');
    code.readOnly = true; code.rows = 3; code.value = payment.qr_code;
    qr.appendChild(code);
  }
}

function startStatusPolling(paymentId, resourceType) {
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = setInterval(async () => {
    const data = await getJson(`${API.status}?payment_id=${encodeURIComponent(paymentId)}&resource_type=${resourceType}`);
    const status = data.payment && data.payment.status;
    if (status) $('status-line').textContent = `Status: ${status}`;
    if (['approved', 'authorized', 'cancelled', 'rejected'].includes(status)) {
      clearInterval(statusTimer);
      if (['approved', 'authorized'].includes(status)) $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.approved', t('approved'));
    }
  }, 5000);
}

async function mountCardBrick() {
  const container = $('cardPaymentBrick_container');
  container.innerHTML = '';
  if (!mpPublicKey || !window.MercadoPago || !selected) { showResult(t('plan_unavailable')); return; }
  const mp = new window.MercadoPago(mpPublicKey, { locale: ctx.lang === 'pt-BR' ? 'pt-BR' : ctx.lang === 'es-ES' ? 'es-AR' : 'en-US' });
  const bricks = mp.bricks();
  if (cardBrickController) { await cardBrickController.unmount(); cardBrickController = null; }
  cardBrickController = await bricks.create('cardPayment', 'cardPaymentBrick_container', {
    initialization: { amount: selected.amount || 1 },
    callbacks: {
      onReady: () => {},
      onError: (error) => showResult(error),
      onSubmit: async (cardFormData) => {
        $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.processing', t('processing'));
        const data = await postJson(API.subscriptions, {
          ...basePayload(),
          payer_email: $('payer_email').value.trim() || (cardFormData.payer && cardFormData.payer.email),
          card_token: cardFormData.token,
        });
        showResult(data.subscription || data);
        $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.pending', t('pending'));
        if (data.subscription && data.subscription.subscription_id) {
          startStatusPolling(data.subscription.subscription_id, 'preapproval');
        }
      },
    },
  });
}

async function payPix() {
  $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.processing', t('processing'));
  const data = await postJson(API.pix, basePayload());
  showResult(data.payment || data);
  showPixQr(data.payment || {});
  if (data.payment && data.payment.payment_id) startStatusPolling(data.payment.payment_id, 'payment');
}

async function payBoleto() {
  $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.processing', t('processing'));
  const data = await postJson(API.boleto, basePayload());
  showResult(data.payment || data);
  if (data.payment && data.payment.ticket_url) {
    $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.boleto_opened', t('boleto_opened'));
    window.open(data.payment.ticket_url, '_blank');
  }
  if (data.payment && data.payment.payment_id) startStatusPolling(data.payment.payment_id, 'payment');
}

async function onPay() {
  try {
    if (!selected) return;
    if (selected.method === 'pix') await payPix();
    else if (selected.method === 'boleto') await payBoleto();
    // Cartão é submetido pelo Brick (onSubmit); o botão apenas reforça a ação.
    else $('status-line').textContent = globalThis.EpiI18n.textFor($('status-line'), 'checkout.processing', t('processing'));
  } catch (err) {
    showResult(String(err));
  }
}

function renderUnavailable() {
  $('methods-card').querySelector('#pay-options').innerHTML = `<p class="muted">${t('plan_unavailable')}</p>`;
  $('payBtn').disabled = true;
  $('summary-body').innerHTML = `<p class="muted">${t('plan_unavailable')}</p>`;
}

function renderContactOnly() {
  $('methods-card').hidden = true;
  $('card-fields').hidden = true;
  $('summary-body').innerHTML = `<p>${t('contact_sales')}</p>`;
  $('payBtn').textContent = globalThis.EpiI18n.textFor($('payBtn'), 'checkout.talk_sales', t('talk_sales'));
  $('payBtn').onclick = () => { window.location.href = (window.WEB_BASE_URL || '') + '/#contato'; };
}

function pickFromCatalog(catalog) {
  if (!Array.isArray(catalog)) return null;
  const key = ctx.plan.toLowerCase();
  return catalog.find((p) => (p.key || '').toLowerCase() === key)
    || catalog.find((p) => (p.reason || '').toLowerCase() === key) || null;
}

async function init() {
  ctx.lang = await globalThis.EpiI18n.setLang(ctx.lang, {persist:false});
  if (globalThis.EpiI18n.loadError) {
    const notice = document.createElement('p');
    notice.setAttribute('role', 'alert');
    notice.className = 'result';
    notice.textContent = globalThis.trEpi('i18n.languageLoadFailed','Não foi possível carregar o idioma. Tente novamente.');
    document.querySelector('.checkout').prepend(notice);
    if (!Object.keys(globalThis.EpiI18n.translations).length) return;
  }
  $('plan-name').textContent = ctx.plan || '—';
  const [config, monthlyResp, annualResp] = await Promise.all([
    getJson(API.config),
    getJson(`${API.catalog}?cycle=monthly`),
    getJson(`${API.catalog}?cycle=annual`),
  ]);
  mpPublicKey = (config.config && config.config.public_key) || '';
  window.WEB_BASE_URL = (config.config && config.config.web_base_url) || '';
  plans.monthly = pickFromCatalog(monthlyResp.catalog || []);
  plans.annual = pickFromCatalog(annualResp.catalog || []);

  const any = plans.monthly || plans.annual;
  if (!any) { renderUnavailable(); return; }
  if (any.contact_only || (plans.monthly && plans.monthly.amount == null && plans.annual && plans.annual.amount == null)) {
    renderContactOnly(); return;
  }

  options = buildOptions();
  if (!options.length) { renderUnavailable(); return; }
  // Pré-seleciona o ciclo que o usuário escolheu no site (cartão), se houver.
  const preferred = options.find((o) => o.method === 'card' && o.cycle === ctx.cycle) || options[0];
  $('payBtn').addEventListener('click', onPay);
  selectOption(preferred.id);
}

// Atualização apenas visual: conservar a seleção, a chave de idempotência e
// os dados do cartão mantidos pelo componente do provedor.
window.addEventListener('epi:langchange', () => {
  ctx.lang = globalThis.EpiI18n.lang;
  const any = plans.monthly || plans.annual;
  if (!any) return;
  if (any.contact_only) {renderContactOnly();return;}
  if (!options.length) {renderUnavailable();return;}
  const selectedId = selected?.id;
  options = buildOptions();
  selected = options.find(option => option.id === selectedId) || null;
  renderOptions();
  renderSummary();
});

init().catch((e) => showResult(String(e)));
