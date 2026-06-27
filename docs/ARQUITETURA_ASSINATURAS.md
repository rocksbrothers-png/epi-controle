# Arquitetura de Assinaturas e Pagamentos — EPI Controle

> **Status:** proposta / roadmap (PR 1 de 6). Este documento é a **fonte única de
> verdade de design** para a reestruturação de pagamentos e assinaturas. Nenhum
> código funcional é alterado aqui — os PRs 2 a 6 implementam o que está descrito,
> e devem **referenciar e atualizar** este documento conforme evoluírem.

## 0. Objetivo

Elevar a estratégia de pagamentos de uma única opção ("Cartão — assinatura
recorrente") para uma experiência SaaS completa, clara e transparente,
inspirada em Stripe Billing, Microsoft 365, Google Workspace, GitHub, Notion e
Asana, mantendo o **backend Python como única fonte de verdade** e o **Access
Token exclusivamente no backend**.

Princípios inegociáveis:

1. **Backend é a fonte de verdade** para planos, assinaturas, faturas e estado.
2. **Nenhum segredo no frontend** (Access Token, Client Secret, Webhook Secret).
3. **Transparência ao cliente**: renovação automática só quando escolhida, sem
   fidelidade, cancelamento a qualquer momento, todas as cobranças auditáveis.
4. **Compatível com todas as superfícies**: site institucional, checkout,
   app Flutter (Web/Android/iOS) e portal do cliente, consumindo a mesma API.
5. **Mudanças incrementais e idempotentes**, preservando a arquitetura atual.

---

## 1. Estado atual (auditoria)

### 1.1 Backend (`modules/payments/`)

| Recurso | Situação |
|---|---|
| `GET /api/payments/config` | ✅ public key + ambiente (sem Access Token) |
| `GET /api/payments/catalog?cycle=` | ✅ catálogo canônico (START/BUSINESS/CORPORATE/ENTERPRISE) |
| `POST /api/payments/plans` (master) | ✅ cria preapproval plan no MP |
| `POST /api/payments/subscriptions` | ✅ assinatura com cartão (preapproval) |
| `POST /api/payments/pix` / `/boleto` | ✅ pagamento avulso Pix/boleto |
| `POST /api/payments/webhook` | ✅ sincroniza status (payment/preapproval) |
| `GET /api/payments/status` | ✅ consulta/atualiza status |
| `GET /pagamento`, `/checkout` | ✅ página de checkout servida pelo backend |
| Access Token | ✅ apenas no backend (`epi_backend/config.py`) |

### 1.2 Banco de dados

Hoje existem **duas** tabelas (`modules/payments/service.py::ensure_payment_tables`):

- `payment_plans` — preapproval plans criados no MP (com `plan_key`).
- `payments` — registros de pagamento/preapproval avulsos.

### 1.3 Lacunas vs. especificação

- **Checkout:** `static/pagamento.html` expõe um `<select>` simples (Cartão/Pix/Boleto),
  sem descrições, sem avisos de renovação automática, sem resumo do pedido.
- **Modelo de assinatura:** não há tabela `subscriptions` nem `invoices`; não há
  campos de ciclo de vida (`renewal_date`, `cancel_date`, `next_payment_date`, etc.).
- **Operações:** não há cancelar, trocar plano (upgrade/downgrade), trocar cartão,
  reativar, recuperação de falhas, reenvio de notificações.
- **Painel "Minha Assinatura":** inexistente (alvo definido: app Flutter `epi_admin`).
- **Histórico financeiro / comprovantes / NF-e:** inexistentes.
- **Auditoria de assinatura:** não há trilha dedicada (quem contratou/alterou/cancelou).

---

## 2. Arquitetura alvo

```
Site institucional (estático)        Backend Python (fonte única de verdade)
─────────────────────────────       ─────────────────────────────────────────
Página de planos ──redirect──▶  GET /pagamento (checkout, mesma origem)
                                        │
                                        ▼
                            GET  /api/payments/config   (public key)
                            GET  /api/payments/catalog   (planos/preços)
                            POST /api/payments/subscriptions|pix|boleto
                            POST /api/payments/webhook   (MP → backend)
                                        │
App Flutter (epi_admin)  ───────────────┤  (mesma API, com sessão autenticada)
  Configurações → Minha Assinatura  ────▶ GET  /api/subscriptions/current
  Histórico Financeiro              ────▶ GET  /api/subscriptions/invoices
  Ações (cancelar/trocar/reativar)  ────▶ POST /api/subscriptions/*
                                        │
                                        ▼
                            Mercado Pago (preapproval / payments)
```

Toda a lógica financeira (criação, renovação, cancelamento, upgrade/downgrade,
sincronização via webhook) roda **somente no backend**. Frontends apenas
apresentam estado e disparam ações autenticadas.

---

## 3. Modelo de dados (PR 3)

Novas tabelas, criadas de forma idempotente (`CREATE TABLE IF NOT EXISTS` +
`ALTER TABLE ADD COLUMN IF NOT EXISTS`, com a ordem **coluna antes do índice** —
ver lição aprendida no fix do bootstrap 503). Mantém-se `payments` e
`payment_plans`.

### 3.1 `subscriptions`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `company_id` | INT | FK lógica para `companies` |
| `tenant_id` | TEXT | multi-tenant |
| `plan_key` | TEXT | `start`/`business`/`corporate` |
| `payment_cycle` | TEXT | `monthly`/`annual` |
| `payment_method` | TEXT | `card`/`pix`/`boleto` |
| `is_recurring` | BOOL | true para cartão (preapproval) |
| `subscription_id` | TEXT | id interno público (uuid) |
| `preapproval_id` | TEXT | id do preapproval no MP |
| `preapproval_plan_id` | TEXT | id do preapproval_plan no MP |
| `status` | TEXT | `pending`/`authorized`/`active`/`paused`/`cancelled`/`expired`/`failed` |
| `mp_status` | TEXT | status bruto do MP (espelho) |
| `amount` | REAL | valor da cobrança recorrente |
| `currency` | TEXT | `BRL` |
| `renewal_date` | TEXT | data da próxima renovação |
| `next_payment_date` | TEXT | próxima cobrança prevista |
| `last_payment_date` | TEXT | última cobrança confirmada |
| `cancel_date` | TEXT | quando foi cancelada |
| `cancel_reason` | TEXT | motivo |
| `created_by` / `updated_by` | INT | user_id responsável |
| `created_at` / `updated_at` | TEXT | timestamps |

### 3.2 `invoices` (faturas/cobranças)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `subscription_id` | TEXT | vínculo com a assinatura |
| `company_id` / `tenant_id` | | |
| `mp_payment_id` | TEXT | id do pagamento no MP |
| `payment_method` | TEXT | `card`/`pix`/`boleto` |
| `amount` / `currency` | | |
| `status` | TEXT | `paid`/`pending`/`cancelled`/`refunded`/`failed` |
| `due_date` / `paid_at` | TEXT | |
| `receipt_url` | TEXT | comprovante (MP) |
| `invoice_url` | TEXT | NF-e (quando integrada — ver §8) |
| `raw_json` | TEXT | payload do MP |
| `created_at` / `updated_at` | | |

### 3.3 `subscription_audit_logs`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `subscription_id` | TEXT | |
| `action` | TEXT | `created`/`changed_plan`/`changed_card`/`cancelled`/`reactivated`/`renewed`/`payment_failed` |
| `actor_user_id` | INT | quem executou |
| `company_id` / `tenant_id` | | |
| `ip` | TEXT | origem da ação |
| `detail_json` | TEXT | antes/depois, metadados |
| `created_at` | TEXT | |

> `payments` permanece para pagamentos avulsos; `invoices` é a visão financeira
> consolidada por assinatura. Um job de reconciliação liga `payments` ↔ `invoices`.

---

## 4. Backend Python (PR 2)

Novo módulo de serviço (`modules/payments/subscriptions_service.py`) e rotas
(`/api/subscriptions/*`), todas autenticadas e resolvendo `company_id`/`tenant_id`
a partir da sessão.

### 4.1 Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/subscriptions/current` | assinatura ativa da empresa (estado completo) |
| `GET` | `/api/subscriptions/invoices` | histórico de cobranças (paginado, filtros) |
| `POST` | `/api/subscriptions/change-plan` | upgrade/downgrade (proration conforme §4.3) |
| `POST` | `/api/subscriptions/change-card` | troca do cartão (novo token) |
| `POST` | `/api/subscriptions/cancel` | cancela no MP + atualiza banco + auditoria |
| `POST` | `/api/subscriptions/reactivate` | reativa assinatura pausada/cancelável |
| `GET` | `/api/subscriptions/:id/receipt` | comprovante de uma cobrança |

### 4.2 Operações de ciclo de vida

- **Renovação:** dirigida por webhook (`preapproval`/`authorized_payment`). Cada
  cobrança gera/atualiza uma `invoice` e move `last_payment_date`/`next_payment_date`.
- **Cancelamento:** `PUT /preapproval/{id}` com `status=cancelled` no MP; grava
  `cancel_date`/`cancel_reason`; acesso mantido até o fim do período pago.
- **Upgrade/Downgrade:** cancela o preapproval atual e cria um novo com o novo
  valor/plano (MP não altera valor de preapproval em vigor), preservando
  histórico; política de proração documentada em §4.3.
- **Troca de cartão:** novo `card_token` → atualiza o preapproval.
- **Recuperação de falhas:** reprocessamento de webhooks, reconciliação via
  `GET /preapproval/{id}` e `GET /v1/payments/{id}`, reenvio de notificações.

### 4.3 Decisões pendentes (produto)

- **Proração** em upgrade/downgrade: imediata com crédito proporcional **ou** troca
  na próxima renovação? (recomendado: troca na próxima renovação no MVP).
- **Carência/retry de cobrança** recusada (dunning): nº de tentativas e janela.

---

## 5. Tela de Checkout — UX (PR 4)

Reescrita de `static/pagamento.html` + `static/js/pagamento.js`. Substitui o
`<select>` por uma seleção rica (rádio/cards) e adiciona resumo do pedido.

### 5.1 Forma de pagamento (substitui o `<select>`)

- ○ **Assinatura Mensal (Renovação Automática)** — cobrança mensal, cancele quando
  quiser, sem fidelidade.
- ○ **Assinatura Anual (Renovação Automática)** — economia vs. mensal, renovação 1×/ano.
- ○ **PIX** — sem renovação automática; novo PIX a cada ciclo.
- ○ **Boleto Bancário** — sem renovação automática; novo boleto a cada ciclo.

### 5.2 Aviso de renovação automática (quando recorrente)

Bloco destacado: cancele a qualquer momento • sem multa • acesso ativo até o fim
do período pago • nenhuma cobrança após o cancelamento.

### 5.3 Resumo do pedido

Plano • Valor • Periodicidade • Forma de pagamento • Próxima cobrança •
Benefícios inclusos • Valor total. Botão **"Assinar Agora"** / **"Finalizar Assinatura"**.

> Usa endpoints já existentes (`/config`, `/catalog`, `/subscriptions`, `/pix`,
> `/boleto`). Material Design 3 e estética de confiança (Stripe-like).

---

## 6. Painel "Minha Assinatura" — App Flutter `epi_admin` (PR 5)

Nova feature em `flutter/apps/epi_admin/lib/features/subscription/`, acessível por
**Configurações → Minha Assinatura**, consumindo `/api/subscriptions/*` via
`core/api/api_client.dart`.

### 6.1 Tela principal

Exibe: Plano atual • Valor • Data da contratação • Próxima cobrança • Forma de
pagamento • Status • ID da assinatura MP • Status MP • Empresa • Tenant •
Administrador responsável.

### 6.2 Ações

Alterar plano • Trocar forma de pagamento • Atualizar cartão • Cancelar •
Reativar • Baixar comprovantes • Baixar notas fiscais • Histórico • Cobranças.

### 6.3 Fluxo de cancelamento

Modal "Tem certeza?" (acesso até o fim do período pago • sem nova cobrança) →
botões **Voltar** / **Confirmar Cancelamento** → backend: cancela no MP, atualiza
banco, registra auditoria, envia e-mail e notificação.

---

## 7. Histórico Financeiro (PR 6)

Tela (Flutter `epi_admin`) listando todas as cobranças: método (PIX/boleto/cartão),
status (pago/pendente/cancelado/reembolsado/falhou), data, valor, ID MP, recibo.
Filtros por período/status/método; exportação CSV. Origem: `GET /api/subscriptions/invoices`.

---

## 8. Comprovantes e Notas Fiscais (decisão pendente)

- **Comprovantes:** o MP fornece `receipt_url`/`ticket_url` — uso direto no MVP.
- **NF-e/NFS-e:** exige integração fiscal externa (ex.: provedor de NFS-e municipal).
  **Decisão pendente:** qual provedor e regime fiscal. Fica fora do MVP; planejado
  para fase posterior com campo `invoice_url` já previsto em `invoices`.

---

## 9. Auditoria (transversal)

Toda ação de assinatura grava `subscription_audit_logs` com: quem contratou/
alterou/cancelou/reativou, data, IP, `company_id`, `tenant_id`, `user_id` e
detalhe antes/depois. Integra-se à trilha de auditoria já existente do sistema.

---

## 10. Notificações (decisão pendente)

E-mail e notificação push em: contratação, renovação, falha de cobrança,
cancelamento, reativação. **Decisão pendente:** provedor de e-mail e canal de push
(reusar o que o sistema já utiliza, se houver). Eventos e gatilhos definidos por PR.

---

## 11. Segurança e compatibilidade

- Access Token, Client Secret e Webhook Secret **somente no backend**.
- Tokenização de cartão no navegador via Public Key (o backend recebe só o token).
- `/api/subscriptions/*` autenticado e isolado por `company_id`/`tenant_id`.
- Compatível com Site institucional, Checkout, Flutter Web/Android/iOS, Painel
  Admin e Portal do Cliente — todos consumindo a mesma API.

---

## 12. Sequência de entrega (PRs)

| PR | Escopo | Depende de |
|---|---|---|
| **PR 1** | **Este documento** (arquitetura/roadmap) | — |
| **PR 2** | Backend Python: MP, planos, webhooks, renovação, cancelamento, upgrade/downgrade | PR 1, PR 3 |
| **PR 3** | Banco de dados: `subscriptions`, `invoices`, `payments`, audit logs | PR 1 |
| **PR 4** | Tela de Checkout (UX) | PR 1 (usa API atual) |
| **PR 5** | Painel "Minha Assinatura" (Flutter `epi_admin`) | PR 2, PR 3 |
| **PR 6** | Histórico Financeiro (Flutter `epi_admin`) | PR 2, PR 3 |

> Observação de ordem prática: **PR 3 (banco)** precede **PR 2 (backend)**, pois o
> serviço depende das tabelas. PR 4 pode avançar em paralelo (usa os endpoints
> atuais). PR 5/PR 6 dependem do backend de assinaturas (PR 2/PR 3).

---

## 13. Decisões pendentes (consolidado)

1. **Proração** em upgrade/downgrade (recomendado: troca na próxima renovação).
2. **Dunning** (retentativas de cobrança recusada): política e janela.
3. **NF-e/NFS-e**: provedor fiscal e regime (fora do MVP).
4. **Notificações**: provedor de e-mail e canal de push.
5. **Portal do Cliente**: reusa as telas do `epi_admin` ou superfície própria?

Estas decisões não bloqueiam PR 3 e PR 4; serão necessárias antes de finalizar PR 2/5/6.
