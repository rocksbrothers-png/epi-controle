# Integração Mercado Pago (backend Python)

Toda a lógica sensível de pagamentos/assinaturas do EPI Controle vive no
**backend Python**. O website (Static Site no Render) **não** executa nenhuma
lógica com Access Token — ele apenas chama os endpoints seguros descritos
abaixo e usa a Public Key para tokenizar o cartão no navegador.

## Por que saiu do website

Um Static Site não tem runtime seguro: qualquer `MERCADO_PAGO_ACCESS_TOKEN`
embutido em build/JS fica exposto publicamente. Por isso o script
`scripts/create-mp-preapproval-plans.js` (criado no repositório do website
estático) deve ser **removido** de lá. A criação de planos/preapproval plans
passa a ser feita pelo endpoint `POST /api/payments/plans` do backend.

> Ação no repositório do website: apagar `scripts/create-mp-preapproval-plans.js`
> e qualquer referência a `MERCADO_PAGO_ACCESS_TOKEN`. Manter apenas HTML/JS
> que chama os endpoints do backend (ver `static/checkout.html` e
> `static/js/payments.js` como referência).

## Variáveis de ambiente (somente no backend)

| Variável | Uso | Exposição |
|---|---|---|
| `MERCADO_PAGO_ACCESS_TOKEN` | Autenticação na API do MP | **SECRETO — nunca no frontend** |
| `MERCADO_PAGO_PUBLIC_KEY` | Tokenização de cartão no navegador | Pública (servida via `/api/payments/config`) |
| `MERCADO_PAGO_ENV` | `sandbox` ou `production` | Pública |
| `MERCADO_PAGO_WEBHOOK_SECRET` | Validação do `x-signature` do webhook (opcional) | Secreto |
| `WEB_BASE_URL` | URL do website (back_urls) | Pública |
| `WEB_APP_URL` | URL do app (retorno pós-pagamento) | Pública |

## Endpoints

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/api/payments/config` | Public key + ambiente (seguro p/ frontend) | Público |
| `GET` | `/api/payments/plans` | Lista planos persistidos | Master admin |
| `POST` | `/api/payments/plans` | Cria preapproval plan no MP | Master admin |
| `POST` | `/api/payments/subscriptions` | Cria assinatura com cartão tokenizado | Público (checkout) |
| `POST` | `/api/payments/pix` | Cria pagamento Pix | Público (checkout) |
| `POST` | `/api/payments/boleto` | Cria pagamento boleto | Público (checkout) |
| `POST` | `/api/payments/webhook` | Recebe notificações do MP | Público (MP) |
| `GET` | `/api/payments/status?payment_id=...` | Consulta/atualiza status | Público |

### Exemplos de corpo

`POST /api/payments/plans` (master):
```json
{ "actor_user_id": 1, "company_id": 12, "reason": "Plano Start",
  "amount": 99.90, "frequency": 1, "frequency_type": "months" }
```

`POST /api/payments/subscriptions`:
```json
{ "company_id": 12, "plan_id": "<mp_plan_id>", "payer_email": "cliente@empresa.com",
  "card_token": "<token gerado pela Public Key>" }
```

`POST /api/payments/pix` / `POST /api/payments/boleto`:
```json
{ "company_id": 12, "plan_id": "start", "payer_email": "cliente@empresa.com",
  "amount": 42.00, "description": "Assinatura EPI Controle" }
```

## Persistência

Os registros são gravados nas tabelas `payment_plans` e `payments`. Em
`payments` ficam salvos, entre outros, **`company_id`, `plan_id`,
`payer_email`, `payment_method` e `status`** (atualizado via webhook e via
`/api/payments/status`).

## Webhook

Configure a URL `https://<backend>/api/payments/webhook` no painel do Mercado
Pago. Se `MERCADO_PAGO_WEBHOOK_SECRET` estiver definido, o backend valida a
assinatura `x-signature`. O handler busca o recurso atualizado no MP e
sincroniza o `status` no banco.

## Segurança

- O Access Token **só** existe no backend (`epi_backend/config.py`).
- `/api/payments/config` devolve apenas a Public Key e URLs públicas.
- O frontend nunca recebe nem manipula o Access Token.
