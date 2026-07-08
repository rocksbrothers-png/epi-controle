# Plano Técnico — Módulo de Compras (Procurement) integrado ao Controle de EPI

> **Status:** proposta técnica para aprovação. Nenhuma regra existente é alterada
> por este documento — ele mapeia o que já existe, o que falta e como evoluir em
> três níveis de integração com fornecedores, preservando as regras vigentes.
>
> **Plataformas cobertas:** web legado (`static/`), Flutter Web (`/app/`),
> Android e iOS (mesmo código Flutter em `flutter/apps/epi_admin`), e o site
> institucional (`epi-controle-site`, apenas ponto de entrada do Portal do
> Fornecedor).
>
> Gerado em 2026-07-08.

---

## 1. Regras invioláveis (pré-condições do plano)

Estas regras **já existem** no sistema e **não mudam** em nenhuma fase:

| # | Regra vigente | Onde está implementada |
|---|---|---|
| R1 | **Itens aprovados são imutáveis.** Um `purchase_request_item` com status `approved`, `ordered`, `received` ou `closed` não pode ser revisado/alterado. | `modules/purchases/service.py` (guarda `status NOT IN ('approved', 'ordered', 'received', 'closed')`) |
| R2 | Solicitações de colaboradores só viram demanda de compra **depois** de aprovadas pelo Administrador Local (`epi_requests.status = 'aprovado'`). | `fetch_purchase_demands()` em `modules/purchases/service.py` |
| R3 | PO aprovada fecha a requisição; aprovação grava `quantity_approved` e o item não regressa de status. | `epi_backend/purchase_workflow.py` |
| R4 | Estoque baixo entra como demanda quando `quantity <= minimum_stock` (mesma regra do card do dashboard). | `fetch_purchase_demands()` + `modules/stock/service.fetch_low_stock_items` |
| R5 | Recebimento (parcial/total) atualiza estoque, gera QR (`epi_stock_items` + `epi_qr_sequences`) e abre pendências para o comprador quando recebido a menor. | `_record_partial_receipt_pendencies()` e conferência de recebimento |
| R6 | Multi-tenant: **toda** tabela e consulta filtra por `company_id`; RLS ativa no Postgres/Supabase (fases 1–4 + `purchase_pendencies`). | `core/schema.py`, `supabase/migrations/2026*_rls_*` |
| R7 | Auditoria de compras via `purchase_events` (ator, papel, status de/para, IP, timestamp). | `modules/purchases/service.py` |
| R8 | Perfis de compras: `buyer` (Comprador) e `approver` (Aprovador), com escopo por unidade (`purchase_role_unit_links`) e permissões em `core/permissions.py`. | `core/permissions.py`, `PURCHASE_FUNCTION_LABELS` |
| R9 | Flutter não acessa Supabase/banco direto e não duplica regra de negócio; consome apenas a API Python. | `flutter/.../features/purchases/ARCHITECTURE.md` |

Qualquer item deste plano que esbarre nessas regras **estende** o fluxo (novos
status, novas tabelas, novos endpoints) — nunca modifica o comportamento atual.

---

## 2. Diagnóstico — o que JÁ existe hoje

O módulo de compras atual (`modules/purchases/`, ~89 KB de serviço, 35+ endpoints)
já cobre boa parte do pedido:

| Requisito do módulo | Estado | Implementação atual |
|---|---|---|
| Cadastro de fornecedores | ✅ Parcial | `authorized_suppliers` (nome, CNPJ, categoria, e-mail de contato, notas). Falta: telefone, endereço, condições de pagamento, status ativo/inativo, contatos múltiplos. |
| Catálogo de produtos por fornecedor | ❌ Não existe | Só há `epis.supplier_company` (texto livre no cadastro do EPI). |
| Demanda automática por estoque mínimo | ✅ Existe | `fetch_purchase_demands()` — solicitações aprovadas + estoque `<= minimum_stock`, com sugestão de reposição por tamanho. |
| Requisição de compra (PR) com revisão de itens | ✅ Existe | `purchase_requests` + `purchase_request_items` + workflow de status. |
| Solicitação de cotação (RFQ) | ⚠️ Parcial | Existe **importação de cotação por arquivo CSV** (`epi_backend/purchase_import.py`), mas não há entidade "cotação" nem envio para múltiplos fornecedores. |
| Comparação de preços/prazos | ❌ Não existe | Não há estrutura para N cotações do mesmo item. |
| Criação de PO | ✅ Existe | `purchase_orders` + `purchase_order_items` + `purchase_approvals` (aprovar/reprovar/parcial, resubmissão). |
| Envio da PO ao fornecedor | ❌ Não existe | Não há envio por e-mail (só SMTP de recuperação de senha em `modules/auth/service.py`). |
| Confirmação do pedido pelo fornecedor | ❌ Não existe | Fornecedor não tem acesso ao sistema. |
| Recebimento parcial/total | ✅ Existe | Conferência com pendências de recebimento parcial (`purchase_pendencies`). |
| Atualização automática de estoque | ✅ Existe | Recebimento grava `stock_movements` + `unit_epi_stock`. |
| QR Code dos EPIs recebidos | ✅ Existe | `epi_stock_items` com `qr_code_value` sequencial por empresa. |
| Impressão de etiquetas | ✅ Existe | Labels retornadas na conferência ("Imprimir QR Codes", reutiliza `printStockLabels`). |
| Multi-tenant / auditoria / perfis | ✅ Existe | R6, R7, R8 acima. |

**Frontends existentes:**

- **Web legado:** `static/js/views/purchases.js` (Demandas, Requisições, POs, conferência, etiquetas).
- **Flutter (Web/Android/iOS):** `flutter/apps/epi_admin/lib/features/purchases/` — `purchases_screen`, `new_purchase_screen`, `purchase_orders_screen`, `receive_purchase_order_screen`, com datasource/repository próprios.
- **Portal existente:** `modules/portal/` é o **portal do colaborador** (link tokenizado por CPF, com auditoria própria). Esse padrão será **reaproveitado** para o Portal do Fornecedor.

**Conclusão do diagnóstico:** o núcleo transacional (demanda → PR → PO →
recebimento → estoque/QR/etiqueta) está pronto e testado
(`tests/test_purchase_*`). O que falta é a **camada de relacionamento com o
fornecedor**: catálogo, cotação formal, comparação, envio e confirmação — ou
seja, exatamente os três níveis de integração.

---

## 3. Arquitetura-alvo — três níveis de integração

Princípio: **um único fluxo interno** (demanda → RFQ → cotações → comparação →
PO → envio → confirmação → recebimento) com **três canais** plugáveis de
comunicação com o fornecedor. O canal é um atributo do fornecedor
(`authorized_suppliers.integration_level`), não um fork do fluxo.

```
                         ┌──────────────────────────────┐
 demanda (já existe) ──▶ │  RFQ / Cotação / Comparação  │──▶ PO (já existe)
                         └──────────────┬───────────────┘        │
                                        │ envio/retorno          │ envio/confirmação
                       ┌────────────────┼────────────────────────┤
                       ▼                ▼                        ▼
              Nível 1: E-MAIL   Nível 2: PORTAL DO       Nível 3: API DIRETA
              (manual)          FORNECEDOR (recomendado)  (conector por loja)
```

### 3.1 Nível 1 — Manual + E-mail (fundação)

- Fornecedor cadastrado manualmente; catálogo de produtos alimentado pelo comprador.
- Sistema gera **PDF/HTML da RFQ e da PO** e envia por e-mail (SMTP já configurável
  via `SMTP_HOST/SMTP_USER/SMTP_PASSWORD` — reutilizar e extrair um serviço
  `epi_backend/mailer.py` genérico a partir do código de recuperação de senha).
- Resposta do fornecedor entra manualmente (digitação) **ou** pelo importador CSV
  já existente (`purchase_import.py`), agora vinculado a uma entidade `quote`.
- Confirmação de pedido: comprador registra manualmente ("confirmado pelo
  fornecedor em DD/MM, via e-mail/telefone") — vira evento em `purchase_events`.

### 3.2 Nível 2 — Portal do Fornecedor (recomendado, foco principal)

Portal web externo, sem login com senha na v1: **link tokenizado por RFQ/PO**,
seguindo exatamente o padrão do portal do colaborador
(`employee_portal_links` + `employee_portal_audit_logs`):

- Comprador clica "Enviar cotação ao fornecedor" → sistema cria
  `supplier_portal_links` (token forte, expiração, escopo = 1 RFQ ou 1 PO) e
  envia o link por e-mail (reutiliza o mailer do Nível 1).
- No portal o fornecedor pode: ver os itens solicitados; **informar preço
  unitário, prazo de entrega e frete por item**; **anexar proposta** (PDF);
  recusar itens; enviar a cotação. Depois da PO: **confirmar pedido**,
  **informar previsão de entrega** e **atualizar status** (separação, faturado,
  em transporte, entregue).
- Todas as ações do fornecedor são auditadas em `supplier_portal_audit_logs`
  (empresa, fornecedor, token, IP, ação) e refletidas em `purchase_events`.
- O portal é servido pelo mesmo backend (rota pública `/fornecedor/<token>`),
  com página própria (HTML leve no legado — não requer Flutter), rate-limit
  (`core/rate_limit.py`) e sem acesso a nenhum dado fora do escopo do token.

### 3.3 Nível 3 — API direta com lojas de EPI (conectores)

- Padrão **adapter/conector**: interface única
  (`epi_backend/supplier_connectors/base.py`) com operações
  `get_catalog()`, `get_price_and_stock(items)`, `create_order(po)`,
  `get_order_status(po)`.
- Um conector por loja parceira (REST/EDI/planilha automatizada), configurado em
  `supplier_integrations` (credenciais cifradas por tenant, nunca no código).
- O fluxo interno não muda: quando `integration_level = 'api'`, o envio da RFQ/PO
  chama o conector em vez do e-mail/portal; a resposta preenche as mesmas
  tabelas de cotação/confirmação.
- Fica para a última fase — depende de parceria comercial com as lojas.

---

## 4. Modelo de dados novo (aditivo — nenhuma tabela existente é alterada de forma destrutiva)

Novas tabelas (todas com `company_id`, índices e RLS desde a criação, no padrão
das migrações `supabase/migrations/` + `epi_backend/migrations/`):

```sql
-- Catálogo de produtos por fornecedor
supplier_products (
  id, company_id, supplier_id → authorized_suppliers,
  epi_id → epis (nullable: produto pode ainda não estar mapeado a um EPI),
  supplier_sku, description, ca, manufacturer, unit_measure,
  last_price, last_price_at, lead_time_days, min_order_qty,
  active, created_at, updated_at,
  UNIQUE (company_id, supplier_id, supplier_sku)
)

-- Cotação (RFQ)
purchase_quotes (
  id, company_id, purchase_request_id → purchase_requests,
  supplier_id → authorized_suppliers,
  status,           -- draft | sent | answered | expired | declined | selected | discarded
  channel,          -- email | portal | api | manual
  sent_at, answered_at, valid_until,
  freight_value, payment_terms, notes,
  proposal_file_id → purchase_order_files (proposta anexada),
  created_by, created_at, updated_at
)

purchase_quote_items (
  id, company_id, quote_id → purchase_quotes,
  purchase_request_item_id → purchase_request_items,
  unit_price, quantity_available, lead_time_days,
  supplier_product_id → supplier_products (nullable),
  declined (bool), notes
)

-- Acesso externo do fornecedor (padrão employee_portal_links)
supplier_portal_links (
  id, company_id, supplier_id, entity_type,  -- 'quote' | 'purchase_order'
  entity_id, token_hash, expires_at, revoked_at,
  created_by, created_at, last_access_at
)

supplier_portal_audit_logs (
  id, company_id, supplier_id, link_id, action, detail,
  ip_address, user_agent, created_at
)

-- Confirmação e acompanhamento de entrega pelo fornecedor
purchase_order_confirmations (
  id, company_id, purchase_order_id, supplier_id,
  status,           -- confirmed | rejected | delivery_update
  delivery_forecast, carrier, tracking_code, comment,
  source,           -- email_manual | portal | api
  created_at
)

-- Nível 3: configuração de conectores
supplier_integrations (
  id, company_id, supplier_id, connector_key,  -- ex.: 'loja_x_rest_v1'
  config_encrypted, active, last_sync_at, created_at, updated_at
)
```

Alterações **aditivas** em tabelas existentes (colunas novas com default,
sem tocar nas existentes):

- `authorized_suppliers`: `+ phone, address, payment_terms, active (default 1), integration_level (default 'email')`.
- `purchase_orders`: `+ sent_to_supplier_at, sent_channel, supplier_confirmation_status (default null)` — a máquina de estados atual **não muda**; confirmação é informação paralela, não um novo status obrigatório.

---

## 5. Endpoints novos (contratos REST atuais permanecem intactos)

Internos (autenticados, com permissões novas `purchases.quotes.*` somadas aos
perfis `buyer`/`approver` em `core/permissions.py` — permissões existentes não mudam):

```
GET/POST  /api/suppliers/<id>/products            catálogo por fornecedor
POST      /api/purchase-requests/<id>/quotes      criar RFQ (1..N fornecedores)
GET       /api/purchase-requests/<id>/quotes      listar cotações + comparação
POST      /api/quotes/<id>/send                   enviar (email | portal | api)
POST      /api/quotes/<id>/answer                 resposta manual (Nível 1)
POST      /api/quotes/<id>/select                 selecionar vencedora → pré-preenche PO
POST      /api/purchase-orders/<id>/send          enviar PO ao fornecedor
POST      /api/purchase-orders/<id>/confirmation  registrar confirmação manual
GET       /api/purchase-orders/<id>/tracking      linha do tempo de entrega
```

Públicos (token, rate-limited, escopo mínimo — padrão do portal do colaborador):

```
GET   /fornecedor/<token>                 página do portal (HTML)
GET   /api/portal/supplier/<token>        dados da RFQ/PO do token
POST  /api/portal/supplier/<token>/quote  responder cotação (+ upload proposta)
POST  /api/portal/supplier/<token>/confirm|status   confirmar pedido / status entrega
```

A **comparação de preços/prazos** é um endpoint de leitura que agrega
`purchase_quote_items` por `purchase_request_item_id` (melhor preço, melhor
prazo, frete rateado, total por fornecedor) — sem gravar nada.

Seleção de cotação → criação de PO usa o fluxo existente
(`handle_post_purchase_orders`) apenas **pré-preenchendo** itens/preços; a
aprovação da PO continua idêntica (R3).

---

## 6. Frontends — o que muda em cada plataforma

### 6.1 Web legado (`static/js/views/purchases.js`)
- Novas abas na tela de Compras: **Fornecedores** (CRUD completo + catálogo),
  **Cotações** (criar RFQ, acompanhar, comparar em matriz item × fornecedor,
  selecionar vencedora).
- Na PO: botões "Enviar ao fornecedor" (escolhe canal), selo de confirmação e
  linha do tempo de entrega.
- Página pública nova do Portal do Fornecedor (HTML/JS puro, sem dependências,
  responsiva — fornecedor abre no celular).

### 6.2 Flutter — Web (`/app/`), Android e iOS (mesmo código)
- Seguir `features/purchases/ARCHITECTURE.md` (presentation/domain/data): novos
  use cases e datasources para fornecedores, catálogo, cotações e comparação.
- Telas novas: `suppliers_screen`, `supplier_products_screen`, `quotes_screen`,
  `quote_comparison_screen`; extensões em `purchase_orders_screen`
  (envio/confirmação/tracking) e `receive_purchase_order_screen` (sem mudança
  de regra — só exibe dados de confirmação).
- **Paridade com o legado validada antes de substituir tela em produção** (regra
  R9 do repositório Flutter). Nenhuma regra de negócio no app: tudo via API.
- Android/iOS: nada específico de plataforma além do que o Flutter já cobre;
  impressão de etiquetas continua pelo fluxo atual (labels vêm da API).

### 6.3 Site institucional (`epi-controle-site`)
- Apenas divulgação/entrada: link "Portal do Fornecedor" no rodapé/menu
  apontando para o backend (`/fornecedor/<token>` é acessado via link de
  e-mail; o site só explica o recurso). Nenhuma lógica no site.

---

## 7. Fases de entrega

| Fase | Entrega | Conteúdo | Dependências |
|---|---|---|---|
| **F0** | Fundação | Migrações (tabelas §4), `epi_backend/mailer.py` genérico, permissões novas, testes de esquema/RLS | — |
| **F1** | Nível 1 completo | CRUD fornecedores ampliado + catálogo; RFQ manual; resposta manual/CSV (liga `purchase_import.py` a `purchase_quotes`); comparação; PO pré-preenchida; envio por e-mail (PDF via `core/pdf.py`); confirmação manual | F0 |
| **F2** | Nível 2 — Portal | `supplier_portal_links` + página pública + resposta de cotação com anexo + confirmação de pedido + status de entrega + auditoria | F1 |
| **F3** | Frontends Flutter | Telas novas no `epi_admin` (web/Android/iOS) com paridade validada | F1 (dados), F2 (portal não afeta o app) |
| **F4** | Nível 3 — Conectores | Interface `supplier_connectors`, `supplier_integrations`, 1º conector piloto | F2 e parceria com loja |

Cada fase é um PR separado, com testes (`tests/test_purchase_quotes*.py`,
`tests/test_supplier_portal*.py`) e sem tocar nos testes existentes — se algum
teste atual precisar mudar, é sinal de quebra de regra e a mudança volta para
análise de impacto.

---

## 8. Segurança e conformidade

- **Multi-tenant:** `company_id` em todas as tabelas novas; RLS habilitada na
  mesma migração que cria a tabela (padrão das fases de hardening já feitas).
- **Portal externo:** token com hash armazenado (nunca o token em claro),
  expiração curta, revogação, rate-limit por IP, sem enumeração de recursos,
  escopo de 1 entidade por link. Upload de proposta com validação de
  tipo/tamanho (mesmo pipeline de `purchase_order_files`).
- **Auditoria:** toda ação (interna e do fornecedor) gera `purchase_events`;
  ações externas também em `supplier_portal_audit_logs`.
- **Perfis:** `buyer` cria RFQ/envia PO; `approver` continua aprovando PO
  (inalterado); administrador da empresa gerencia fornecedores/catálogo;
  fornecedor externo não tem usuário no sistema (Nível 2) — só token.
- **Credenciais de conectores (Nível 3):** cifradas por tenant, fora do código
  e fora de logs.

## 9. Mapa de impacto (o que este plano NÃO altera)

- Máquina de estados de `purchase_requests`/`purchase_orders`: **inalterada**
  (novos dados são paralelos; R1–R3 preservadas).
- Demanda por estoque mínimo, recebimento parcial/total, atualização de
  estoque, QR e etiquetas: **inalterados** (R4, R5).
- Portal do colaborador (`modules/portal/`): **inalterado** — apenas serve de
  referência de padrão.
- Contratos REST consumidos pelo Flutter e pelo legado: **inalterados**; tudo
  novo é endpoint novo.
- Repositórios `epi-controle` × `epi-controle-app`: hoje idênticos (ver
  `docs/AUDITORIA_SEPARACAO_REPOS.md`); este plano vale para os dois e deve ser
  aplicado em paralelo até a separação legado × SaaS ser concluída.
