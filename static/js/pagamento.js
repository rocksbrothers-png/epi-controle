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
 * Como a página é servida pelo próprio backend, as chamadas são same-origin
 * (sem CORS). Os apps Flutter (Web/Android/iOS) consomem os mesmos endpoints.
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
    fill_card: 'Preencha os dados do cartão acima e confirme.',
    pix_instructions: 'Escaneie o QR Code ou copie o código Pix abaixo.',
    boleto_opened: 'Boleto gerado. Abrindo em nova aba…',
    processing: 'Processando…',
    approved: 'Pagamento aprovado!',
    pending: 'Pagamento pendente de confirmação.',
    contact_sales: 'Plano sob consulta. Fale com nosso time comercial.',
    talk_sales: 'Falar com Comercial',
    per_month: '/mês',
    per_year: '/ano',
  },
  en: {
    plan_unavailable: 'Plan unavailable right now. Try again later or contact support.',
    fill_card: 'Fill in the card details above and confirm.',
    pix_instructions: 'Scan the QR Code or copy the Pix code below.',
    boleto_opened: 'Boleto generated. Opening in a new tab…',
    processing: 'Processing…',
    approved: 'Payment approved!',
    pending: 'Payment pending confirmation.',
    contact_sales: 'Custom plan. Talk to our sales team.',
    talk_sales: 'Talk to Sales',
    per_month: '/month',
    per_year: '/year',
  },
};

const params = new URLSearchParams(window.location.search);
const ctx = {
  plan: (params.get('plan') || '').trim(),
  cycle: (params.get('cycle') || 'monthly').trim(),
  lang: (params.get('lang') || 'pt').trim().toLowerCase().slice(0, 2),
};
const t = (key) => (I18N[ctx.lang] || I18N.pt)[key] || (I18N.pt[key] || key);

const $ = (id) => document.getElementById(id);
const money = (value, currency = 'BRL') =>
  new Intl.NumberFormat(ctx.lang === 'en' ? 'en-US' : 'pt-BR', { style: 'currency', currency }).format(value || 0);

let mpPublicKey = '';
let selectedPlan = null;
let cardBrickController = null;
let statusTimer = null;

function showResult(data) {
  $('result').textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return res.json().catch(() => ({}));
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error((data.error && data.error.message) || `Erro HTTP ${res.status}`);
  }
  return data;
}

function renderPlanSummary() {
  const box = $('plan-summary');
  if (!selectedPlan) {
    box.innerHTML = `<strong>${ctx.plan || '—'}</strong> · ${t('plan_unavailable')}`;
    $('payBtn').disabled = true;
    $('method').disabled = true;
    return;
  }
  const label = selectedPlan.label || selectedPlan.key || ctx.plan;
  // Enterprise / "sob consulta": não há checkout direto — encaminha ao comercial.
  if (selectedPlan.contact_only || selectedPlan.amount == null) {
    box.innerHTML = `<strong>${label}</strong> — ${t('contact_sales')}`;
    $('payBtn').textContent = t('talk_sales');
    $('method').style.display = 'none';
    $('card-fields').style.display = 'none';
    $('payBtn').onclick = () => {
      const url = (window.WEB_BASE_URL || '') + '/#contato';
      window.location.href = url;
    };
    return;
  }
  const cycleLabel = ctx.cycle === 'annual' ? t('per_year') : t('per_month');
  box.innerHTML = `<strong>${label}</strong> — ${money(selectedPlan.amount, selectedPlan.currency)} ${cycleLabel}`;
}

function basePayload() {
  return {
    plan_id: selectedPlan ? (selectedPlan.plan_id || selectedPlan.key) : ctx.plan,
    payer_email: $('payer_email').value.trim(),
    amount: selectedPlan ? selectedPlan.amount : undefined,
    external_reference: `web|${ctx.plan}|${ctx.cycle}`,
    description: `Assinatura EPI Controle — ${ctx.plan} (${ctx.cycle})`,
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
    code.readOnly = true;
    code.rows = 3;
    code.value = payment.qr_code;
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
  if (!mpPublicKey || !window.MercadoPago || !selectedPlan) {
    showResult(t('plan_unavailable'));
    return;
  }
  const mp = new window.MercadoPago(mpPublicKey, { locale: ctx.lang === 'en' ? 'en-US' : 'pt-BR' });
  const bricks = mp.bricks();
  if (cardBrickController) {
    await cardBrickController.unmount();
    cardBrickController = null;
  }
  cardBrickController = await bricks.create('cardPayment', 'cardPaymentBrick_container', {
    initialization: { amount: selectedPlan.amount || 1 },
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

function onMethodChange() {
  const method = $('method').value;
  $('card-fields').style.display = method === 'card' ? '' : 'none';
  $('qr').innerHTML = '';
  if (method === 'card') mountCardBrick().catch((e) => showResult(String(e)));
}

async function onPay() {
  try {
    const method = $('method').value;
    if (method === 'pix') await payPix();
    else if (method === 'boleto') await payBoleto();
    else showResult(t('fill_card'));
  } catch (err) {
    showResult(String(err));
  }
}

function resolveSelectedPlan(catalog) {
  if (!Array.isArray(catalog) || !catalog.length) return null;
  const key = ctx.plan.toLowerCase();
  return (
    catalog.find((p) => (p.key || '').toLowerCase() === key) ||
    catalog.find((p) => (p.reason || '').toLowerCase() === key) ||
    null
  );
}

async function init() {
  $('plan-name').textContent = ctx.plan || '—';
  const [config, catalogResp] = await Promise.all([
    getJson(API.config),
    getJson(`${API.catalog}?cycle=${encodeURIComponent(ctx.cycle)}`),
  ]);
  mpPublicKey = (config.config && config.config.public_key) || '';
  window.WEB_BASE_URL = (config.config && config.config.web_base_url) || '';
  selectedPlan = resolveSelectedPlan(catalogResp.catalog || []);
  renderPlanSummary();
  $('method').addEventListener('change', onMethodChange);
  $('payBtn').addEventListener('click', onPay);
  if (selectedPlan) onMethodChange();
}

init().catch((e) => showResult(String(e)));
