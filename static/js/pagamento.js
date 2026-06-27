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

const I18N = {
  pt: {
    plan_unavailable: 'Plano indisponível no momento. Tente novamente mais tarde ou fale com o suporte.',
    pix_instructions: 'Escaneie o QR Code ou copie o código Pix abaixo.',
    boleto_opened: 'Boleto gerado. Abrindo em nova aba…',
    processing: 'Processando…',
    approved: 'Pagamento aprovado!',
    pending: 'Pagamento pendente de confirmação.',
    contact_sales: 'Plano sob consulta. Fale com nosso time comercial.',
    talk_sales: 'Falar com Comercial',
    subscribe_now: 'Assinar Agora',
    finish_payment: 'Finalizar Pagamento',
    per_month: '/mês', per_year: '/ano', monthly: 'Mensal', annual: 'Anual',
    opt_monthly_title: 'Assinatura Mensal (Renovação Automática)',
    opt_monthly_desc: 'Cobrança automática todos os meses. Cancele quando quiser pelo painel administrativo. Não há fidelidade.',
    opt_annual_title: 'Assinatura Anual (Renovação Automática)',
    opt_annual_desc: 'Economia em relação ao plano mensal. Renovação automática uma vez por ano. Cancele a qualquer momento antes da próxima renovação.',
    opt_pix_title: 'PIX',
    opt_pix_desc: 'Pagamento via PIX. A renovação não é automática. Um novo PIX será gerado na próxima cobrança.',
    opt_boleto_title: 'Boleto Bancário',
    opt_boleto_desc: 'Pagamento por boleto. A renovação não é automática. Um novo boleto será enviado na próxima cobrança.',
    save_badge: 'Economize', method_card: 'Cartão', method_pix: 'PIX', method_boleto: 'Boleto',
    manual_renew: 'Renovação manual', users_up_to: 'Até {n} usuários',
    benefit_support: 'Suporte e atualizações inclusos', benefit_cancel: 'Cancele quando quiser, sem fidelidade',
  },
  en: {
    plan_unavailable: 'Plan unavailable right now. Try again later or contact support.',
    pix_instructions: 'Scan the QR Code or copy the Pix code below.',
    boleto_opened: 'Boleto generated. Opening in a new tab…',
    processing: 'Processing…',
    approved: 'Payment approved!',
    pending: 'Payment pending confirmation.',
    contact_sales: 'Custom plan. Talk to our sales team.',
    talk_sales: 'Talk to Sales',
    subscribe_now: 'Subscribe Now',
    finish_payment: 'Complete Payment',
    per_month: '/mo', per_year: '/yr', monthly: 'Monthly', annual: 'Annual',
    opt_monthly_title: 'Monthly Subscription (Auto-renewal)',
    opt_monthly_desc: 'Charged automatically every month. Cancel anytime from the admin panel. No lock-in.',
    opt_annual_title: 'Annual Subscription (Auto-renewal)',
    opt_annual_desc: 'Save compared to monthly. Auto-renews once a year. Cancel anytime before the next renewal.',
    opt_pix_title: 'PIX',
    opt_pix_desc: 'Pay via PIX. Renewal is not automatic. A new PIX is generated for the next cycle.',
    opt_boleto_title: 'Bank Slip (Boleto)',
    opt_boleto_desc: 'Pay via boleto. Renewal is not automatic. A new boleto is issued for the next cycle.',
    save_badge: 'Save', method_card: 'Card', method_pix: 'PIX', method_boleto: 'Boleto',
    manual_renew: 'Manual renewal', users_up_to: 'Up to {n} users',
    benefit_support: 'Support and updates included', benefit_cancel: 'Cancel anytime, no lock-in',
  },
};

const params = new URLSearchParams(window.location.search);
const ctx = {
  plan: (params.get('plan') || '').trim(),
  cycle: (params.get('cycle') || 'monthly').trim().toLowerCase() === 'annual' ? 'annual' : 'monthly',
  lang: (params.get('lang') || 'pt').trim().toLowerCase().slice(0, 2),
};
const t = (key) => (I18N[ctx.lang] || I18N.pt)[key] || (I18N.pt[key] || key);

const $ = (id) => document.getElementById(id);
const money = (value, currency = 'BRL') =>
  new Intl.NumberFormat(ctx.lang === 'en' ? 'en-US' : 'pt-BR', { style: 'currency', currency }).format(value || 0);

let mpPublicKey = '';
// plans[cycle] = item do catálogo do plano escolhido naquele ciclo.
const plans = { monthly: null, annual: null };
let options = [];          // opções de pagamento construídas
let selected = null;       // opção selecionada
let cardBrickController = null;
let statusTimer = null;

function showResult(data) {
  $('result').textContent = data == null ? '' : (typeof data === 'string' ? data : JSON.stringify(data, null, 2));
}

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return res.json().catch(() => ({}));
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
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
  return new Intl.DateTimeFormat(ctx.lang === 'en' ? 'en-US' : 'pt-BR', { dateStyle: 'medium' }).format(date);
}

function planLabel() {
  const p = plans.monthly || plans.annual;
  return (p && (p.label || p.key)) || ctx.plan || '—';
}

function benefitsFor() {
  const p = plans.monthly || plans.annual;
  const list = [];
  if (p && p.max_users) list.push(t('users_up_to').replace('{n}', p.max_users));
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
  $('payBtn').textContent = selected.recurring ? t('subscribe_now') : t('finish_payment');
}

function selectOption(id) {
  selected = options.find((o) => o.id === id) || null;
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
  return {
    plan_id: selected ? (selected.plan_id || ctx.plan) : ctx.plan,
    payer_email: $('payer_email').value.trim(),
    amount: selected ? selected.amount : undefined,
    cycle: selected ? selected.cycle : ctx.cycle,
    external_reference: `web|${ctx.plan}|${selected ? selected.cycle : ctx.cycle}|${selected ? selected.method : ''}`,
    description: `Assinatura EPI Controle — ${planLabel()} (${selected ? cycleLabel(selected) : ctx.cycle})`,
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
      if (['approved', 'authorized'].includes(status)) $('status-line').textContent = t('approved');
    }
  }, 5000);
}

async function mountCardBrick() {
  const container = $('cardPaymentBrick_container');
  container.innerHTML = '';
  if (!mpPublicKey || !window.MercadoPago || !selected) { showResult(t('plan_unavailable')); return; }
  const mp = new window.MercadoPago(mpPublicKey, { locale: ctx.lang === 'en' ? 'en-US' : 'pt-BR' });
  const bricks = mp.bricks();
  if (cardBrickController) { await cardBrickController.unmount(); cardBrickController = null; }
  cardBrickController = await bricks.create('cardPayment', 'cardPaymentBrick_container', {
    initialization: { amount: selected.amount || 1 },
    callbacks: {
      onReady: () => {},
      onError: (error) => showResult(error),
      onSubmit: async (cardFormData) => {
        $('status-line').textContent = t('processing');
        const data = await postJson(API.subscriptions, {
          ...basePayload(),
          payer_email: $('payer_email').value.trim() || (cardFormData.payer && cardFormData.payer.email),
          card_token: cardFormData.token,
        });
        showResult(data.subscription || data);
        $('status-line').textContent = t('pending');
        if (data.subscription && data.subscription.subscription_id) {
          startStatusPolling(data.subscription.subscription_id, 'preapproval');
        }
      },
    },
  });
}

async function payPix() {
  $('status-line').textContent = t('processing');
  const data = await postJson(API.pix, basePayload());
  showResult(data.payment || data);
  showPixQr(data.payment || {});
  if (data.payment && data.payment.payment_id) startStatusPolling(data.payment.payment_id, 'payment');
}

async function payBoleto() {
  $('status-line').textContent = t('processing');
  const data = await postJson(API.boleto, basePayload());
  showResult(data.payment || data);
  if (data.payment && data.payment.ticket_url) {
    $('status-line').textContent = t('boleto_opened');
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
    else $('status-line').textContent = t('processing');
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
  $('payBtn').textContent = t('talk_sales');
  $('payBtn').onclick = () => { window.location.href = (window.WEB_BASE_URL || '') + '/#contato'; };
}

function pickFromCatalog(catalog) {
  if (!Array.isArray(catalog)) return null;
  const key = ctx.plan.toLowerCase();
  return catalog.find((p) => (p.key || '').toLowerCase() === key)
    || catalog.find((p) => (p.reason || '').toLowerCase() === key) || null;
}

async function init() {
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

init().catch((e) => showResult(String(e)));
