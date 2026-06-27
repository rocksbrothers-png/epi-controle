# Integração Mercado Pago (backend Python)

Toda a lógica sensível de pagamentos/assinaturas do EPI Controle vive no
**backend Python** — fonte única de verdade para web legado, Flutter Web,
Android e iOS. O website institucional **não** executa nenhuma lógica com
Access Token: ele apenas apresenta os planos e **redireciona para o checkout
servido pelo backend**.

## Arquitetura (fonte única de verdade)

```
Website institucional (estático)          Backend Python (este repositório)
─────────────────────────────────        ─────────────────────────────────
Página de planos  ──redireciona──▶  GET /pagamento?plan=&cycle=&lang=
(START/BUSINESS/...)                       (página de checkout servida aqui)
                                              │  same-origin, sem CORS
                                              ▼
                                     GET  /api/payments/config   (Public Key)
                                     GET  /api/payments/catalog  (planos/preços)
                                     POST /api/payments/pix|boleto|subscriptions
                                     POST /api/payments/webhook  (MP → backend)
```

O website é apenas interface institucional/comercial. O checkout, os preços e
toda a lógica de Mercado Pago ficam no backend, evitando duplicação e mantendo
uma única fonte de verdade consumível por web legado e pelos apps Flutter.

## Como o website integra (1 ajuste)

O botão "Começar Agora" de cada plano deve apenas redirecionar para o checkout
do backend, passando a chave do plano e o ciclo:

```js
function goToCheckout(plan, cycle, lang) {
  // BACKEND_URL = URL pública do backend (ex.: https://epi-controle.onrender.com)
  window.location.href =
    `${BACKEND_URL}/pagamento?plan=${plan}&cycle=${cycle}&lang=${lang || 'pt'}`;
}
```

O 404 anterior (`epi-controle-site.onrender.com/pagamento`) ocorria porque o
`goToCheckout` apontava para uma página inexistente no próprio site. A página
`/pagamento` agora é servida pelo backend.

## Catálogo de planos (canônico no backend)

Definido em `modules/payments/service.py` (`SUBSCRIPTION_PLANS`) e exposto por
`GET /api/payments/catalog?cycle=monthly|annual`. Reflete os planos do site:

| Chave | Rótulo | Usuários | Mensal | Anual (2 meses grátis) |
|---|---|---|---|---|
| `start` | START | até 10 | R$ 297,00 | R$ 2.970,00 |
| `business` | BUSINESS | até 25 | R$ 597,00 | R$ 5.970,00 |
| `corporate` | CORPORATE | até 100 | R$ 1.297,00 | R$ 12.970,00 |
| `enterprise` | ENTERPRISE | +100 | sob consulta | sob consulta |

`enterprise` é `contact_only` (sem checkout direto — encaminha ao comercial).
Quando um preapproval plan é criado (`POST /api/payments/plans` com `plan_key`),
o `plan_id` do Mercado Pago é anexado ao item do catálogo correspondente, para
assinatura com cartão.

## Por que saiu do website

Um Static Site não tem runtime seguro: qualquer `MERCADO_PAGO_ACCESS_TOKEN`
embutido em build/JS fica exposto publicamente. Por isso o script
`scripts/create-mp-preapproval-plans.js` (criado no repositório do website
estático) deve ser **removido** de lá. A criação de planos/preapproval plans
passa a ser feita pelo endpoint `POST /api/payments/plans` do backend.

> Ação no repositório do website: apagar `scripts/create-mp-preapproval-plans.js`
> e qualquer referência a `MERCADO_PAGO_ACCESS_TOKEN`; ajustar `goToCheckout`
> para redirecionar a `${BACKEND_URL}/pagamento?...`. A página de checkout em si
> (`static/pagamento.html` + `static/js/pagamento.js`) é servida pelo backend.

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
| `GET` | `/api/payments/catalog?cycle=` | Catálogo de planos/preços | Público |
| `GET` | `/api/payments/plans` | Lista planos persistidos | Master admin |
| `POST` | `/api/payments/plans` | Cria preapproval plan no MP | Master admin |
| `POST` | `/api/payments/subscriptions` | Cria assinatura com cartão tokenizado | Público (checkout) |
| `POST` | `/api/payments/pix` | Cria pagamento Pix | Público (checkout) |
| `POST` | `/api/payments/boleto` | Cria pagamento boleto | Público (checkout) |
| `POST` | `/api/payments/webhook` | Recebe notificações do MP | Público (MP) |
| `GET` | `/api/payments/status?payment_id=...` | Consulta/atualiza status | Público |
| `GET` | `/pagamento` , `/checkout` | Página de checkout (servida pelo backend) | Público |

### Exemplos de corpo

`POST /api/payments/plans` (master) — `plan_key` liga o plano à chave do site:
```json
{ "actor_user_id": 1, "plan_key": "start", "reason": "EPI Controle START",
  "amount": 297.00, "frequency": 1, "frequency_type": "months" }
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

Os registros são gravados nas tabelas `payment_plans` (inclui `plan_key`) e
`payments`. Em `payments` ficam salvos, entre outros, **`company_id`,
`plan_id`, `payer_email`, `payment_method` e `status`** (atualizado via webhook
e via `/api/payments/status`).

## Webhook

Configure a URL `https://<backend>/api/payments/webhook` no painel do Mercado
Pago. Se `MERCADO_PAGO_WEBHOOK_SECRET` estiver definido, o backend valida a
assinatura `x-signature`. O handler busca o recurso atualizado no MP e
sincroniza o `status` no banco.

## Segurança

- O Access Token **só** existe no backend (`epi_backend/config.py`).
- `/api/payments/config` devolve apenas a Public Key e URLs públicas.
- O frontend nunca recebe nem manipula o Access Token.
