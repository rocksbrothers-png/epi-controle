/*
 * Integração de pagamentos no frontend (Mercado Pago).
 *
 * Regras de segurança:
 *  - O frontend NUNCA conhece nem usa o MERCADO_PAGO_ACCESS_TOKEN.
 *  - A Public Key é obtida do backend em /api/payments/config e serve apenas
 *    para tokenizar o cartão com o SDK do Mercado Pago.
 *  - Toda criação de plano/assinatura/pagamento passa pelos endpoints seguros
 *    do backend Python.
 */

const API = {
  config: '/api/payments/config',
  subscriptions: '/api/payments/subscriptions',
  pix: '/api/payments/pix',
  boleto: '/api/payments/boleto',
  status: '/api/payments/status',
};

const $ = (id) => document.getElementById(id);

function readForm() {
  return {
    company_id: $('company_id').value || null,
    plan_id: $('plan_id').value || '',
    payer_email: $('payer_email').value || '',
    amount: parseFloat($('amount').value || '0'),
    method: $('method').value,
  };
}

function showResult(data) {
  $('result').textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

function showPixQr(payment) {
  const qr = $('qr');
  qr.innerHTML = '';
  if (payment.qr_code_base64) {
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${payment.qr_code_base64}`;
    qr.appendChild(img);
  }
  if (payment.qr_code) {
    const code = document.createElement('textarea');
    code.readOnly = true;
    code.rows = 3;
    code.style.width = '100%';
    code.value = payment.qr_code;
    qr.appendChild(code);
  }
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

let mpPublicKey = '';
let cardBrickController = null;

async function loadConfig() {
  const res = await fetch(API.config);
  const data = await res.json();
  mpPublicKey = (data.config && data.config.public_key) || '';
  return data.config || {};
}

async function mountCardBrick() {
  if (!mpPublicKey || !window.MercadoPago) {
    showResult('Public Key do Mercado Pago indisponível. Configure MERCADO_PAGO_PUBLIC_KEY no backend.');
    return;
  }
  const form = readForm();
  const mp = new window.MercadoPago(mpPublicKey);
  const bricks = mp.bricks();
  if (cardBrickController) {
    await cardBrickController.unmount();
    cardBrickController = null;
  }
  cardBrickController = await bricks.create('cardPayment', 'cardPaymentBrick_container', {
    initialization: { amount: form.amount || 1 },
    callbacks: {
      onReady: () => {},
      onError: (error) => showResult(error),
      onSubmit: async (cardFormData) => {
        // cardFormData.token é o token gerado pela Public Key — seguro de enviar.
        const subscription = await postJson(API.subscriptions, {
          company_id: form.company_id,
          plan_id: form.plan_id,
          payer_email: form.payer_email || cardFormData.payer?.email,
          card_token: cardFormData.token,
          amount: form.amount,
        });
        showResult(subscription);
      },
    },
  });
}

async function payPix() {
  const form = readForm();
  const data = await postJson(API.pix, {
    company_id: form.company_id,
    plan_id: form.plan_id,
    payer_email: form.payer_email,
    amount: form.amount,
    description: 'Assinatura EPI Controle',
  });
  showResult(data);
  showPixQr(data.payment || {});
  return data.payment;
}

async function payBoleto() {
  const form = readForm();
  const data = await postJson(API.boleto, {
    company_id: form.company_id,
    plan_id: form.plan_id,
    payer_email: form.payer_email,
    amount: form.amount,
    description: 'Assinatura EPI Controle',
  });
  showResult(data);
  if (data.payment && data.payment.ticket_url) {
    window.open(data.payment.ticket_url, '_blank');
  }
  return data.payment;
}

export async function checkStatus(paymentId, resourceType = 'payment') {
  const url = `${API.status}?payment_id=${encodeURIComponent(paymentId)}&resource_type=${resourceType}`;
  const res = await fetch(url);
  return res.json();
}

function onMethodChange() {
  const method = $('method').value;
  $('card-fields').style.display = method === 'card' ? '' : 'none';
  if (method === 'card') {
    mountCardBrick().catch((e) => showResult(String(e)));
  }
}

async function onPay() {
  try {
    const method = readForm().method;
    if (method === 'pix') {
      await payPix();
    } else if (method === 'boleto') {
      await payBoleto();
    } else {
      showResult('Preencha os dados do cartão no formulário acima e confirme.');
    }
  } catch (err) {
    showResult(String(err));
  }
}

async function init() {
  await loadConfig();
  $('method').addEventListener('change', onMethodChange);
  $('payBtn').addEventListener('click', onPay);
  onMethodChange();
}

init().catch((e) => showResult(String(e)));
