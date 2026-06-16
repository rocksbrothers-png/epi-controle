# Parity Sheets — Legado (Web SPA) × Flutter Web (Fase 4)

> Verificação de **paridade** por tela entre o legado (`static/app.js` + views) e
> o Flutter Web (`flutter/apps/epi_admin`), com endpoints, permissões, fonte de
> dados, testes, critério de aceite e rollback. Base: código real em 2026-06-16.
> Complementa `docs/ARQUITETURA_FRONTEND_BACKEND.md`.

## Como ler

Cada tela tem: rota legado, rota Flutter, endpoints/fonte de dados, permissões,
componentes, **estado de paridade** (✅ paridade / 🟡 parcial / 🐞 bug), testes e
rollback. Bugs de paridade encontrados são registrados e, quando triviais e
seguros, corrigidos no mesmo PR.

## Padrão de mismatch encontrado (importante)

Vários clientes Flutter (`epi_api`) leem listas de respostas com chaves
específicas. Quando o backend usa outra chave (ou o endpoint não existe), a tela
fica **vazia/quebrada silenciosamente**. Já encontrados e corrigidos:

| Tela | Sintoma | Correção |
|---|---|---|
| Empresas | `getCompanies()` lê `items`, backend devolvia `companies` | endpoint passa a devolver `companies`+`items` (PR #593) |
| Entregas | `getDeliveries()` chama `GET /api/deliveries` **inexistente** | novo `GET /api/deliveries` escopado (este PR) |

Clientes **tolerantes** (ex.: `deliveries`/`feedback` leem `data ?? deliveries ??
items ?? raw`) e listas vindas do **bootstrap** (employees/epis/users/dashboard)
não sofrem o problema.

---

## LOTE 1 — Login, Dashboard, Empresas, Usuários

### 1. Login
| Campo | Conteúdo |
|---|---|
| Rota legado / Flutter | `_login.html` (`handleLogin`) / `Routes.login` `/login` (`AuthCubit`) |
| Endpoint | `POST /api/login` (ambos) |
| Permissões | pública (pré-auth) |
| Paridade | ✅ funcional |
| 🟡 Gap | backend ganhou `POST /api/auth/refresh` e `GET /api/auth/me` (#590/#591), ainda não consumidos pelo `epi_api` — follow-up no `AuthInterceptor` |
| Rollback | legado em `/legacy/` e em `/` (flag OFF) garante login |

### 2. Dashboard
| Campo | Conteúdo |
|---|---|
| Rota / fonte | `Routes.dashboard` `/` (`DashboardCubit`) / `GET /api/bootstrap` |
| Permissões | `dashboard:view` |
| Paridade | ✅ (mesma fonte: bootstrap) |
| 🟡 Observação | `pendingPurchases` é TODO no cubit (bootstrap ainda não traz compras) |

### 3. Empresas
| Campo | Conteúdo |
|---|---|
| Rota / endpoint | `Routes.companies` `/companies` (`CompaniesCubit`) / `GET /api/companies` |
| Permissões | `companies:view` (lista); `companies:create/update` (master_admin) |
| Paridade | 🐞→✅ corrigido no PR #593 (`items` vs `companies`) |

### 4. Usuários
| Campo | Conteúdo |
|---|---|
| Rota / fonte | `Routes.users` `/users` (`UsersCubit`) / bootstrap + `POST/PUT/DELETE /api/users` |
| Permissões | `users:view`; `users:create/update/delete` |
| Paridade | ✅ (lista via bootstrap; CRUD via endpoints; senha sanitizada no `GET /api/users/:id`) |

---

## LOTE 2 — Funcionários, EPIs, Estoque, Entregas

### 5. Funcionários
| Campo | Conteúdo |
|---|---|
| Rota legado / Flutter | view `colaboradores` / `Routes.employees` `/employees` (`EmployeesCubit`) |
| Fonte da lista | **bootstrap** (`bootstrap.employees`) — paridade por construção |
| Backend CRUD | `POST/PUT/DELETE /api/employees`, `GET /api/employees[/:id]`, movimentações (sprints #5/#582) |
| Permissões | `employees:view`; `employees:create/update/delete` |
| Paridade | 🟡 **parcial** — lista ✅; **não existe `employees_api.dart`** no `epi_api`, logo a tela Flutter é **somente leitura** (CRUD não cabeado) |
| Follow-up | criar `EmployeesApi` no `epi_api` (create/update/delete) consumindo os endpoints já existentes |
| Aceite | lista idêntica ao legado; CRUD via Flutter quando o cliente for criado |
| Rollback | legado mantém CRUD completo |

### 6. EPIs
| Campo | Conteúdo |
|---|---|
| Rota / fonte | `Routes.epis` `/epis` (`EpisCubit`) / **bootstrap** (`bootstrap.epis`) |
| Backend CRUD | `modules/epis` (`/api/epis`) |
| Permissões | `epis:view`; `epis:create/update/delete` |
| Paridade | 🟡 **parcial** — lista ✅; **não existe `epis_api.dart`** → tela Flutter somente leitura |
| Follow-up | criar `EpisApi` no `epi_api` |

### 7. Estoque
| Campo | Conteúdo |
|---|---|
| Rota / fonte | `Routes.stock` `/stock` (`StockCubit`) / bootstrap (epis/units) + `StockApi.recordMovement` (`POST`) |
| Permissões | `stock:view`; `stock:adjust` |
| Paridade | ✅ — saldo/lista via bootstrap; movimento de estoque via endpoint |
| Observação | leitura do saldo derivada de bootstrap; ok para paridade inicial |

### 8. Entregas
| Campo | Conteúdo |
|---|---|
| Rota / endpoint | `Routes.deliveries` `/deliveries` (`deliveries_screen.dart`) / `GET /api/deliveries` (lista) + `POST /api/deliveries` (criar) |
| Permissões | `deliveries:view`; `deliveries:create` |
| Paridade | 🐞→✅ **corrigido neste PR** |
| 🐞 Bug | `DeliveriesApi.getDeliveries()` chamava `GET /api/deliveries`, que **não existia** (o módulo só tinha POST) → lista de entregas quebrada no Flutter |
| Correção | novo `handle_get_deliveries` escopado por empresa/unidade operacional, reusando `fetch_deliveries` (ordem: mais recentes 1º), com `limit` opcional; resposta `{deliveries, items}`. Teste em `test_deliveries_get_endpoint.py` |
| Aceite | tela de entregas do Flutter carrega as mesmas entregas do legado, respeitando escopo |
| Rollback | reverter o endpoint (a tela volta ao estado anterior; legado intacto) |

---

## Resumo de achados (lotes 1–2)

| Tela | Estado | Ação |
|---|---|---|
| Login | ✅ | adotar `/auth/refresh` + `/auth/me` no `epi_api` (follow-up) |
| Dashboard | ✅ | `pendingPurchases` no bootstrap (follow-up) |
| Empresas | 🐞→✅ | bug `items` corrigido (#593) |
| Usuários | ✅ | (opcional) consumir `GET /api/users` dedicado |
| Funcionários | 🟡 | criar `EmployeesApi` (CRUD) no Flutter |
| EPIs | 🟡 | criar `EpisApi` (CRUD) no Flutter |
| Estoque | ✅ | — |
| Entregas | 🐞→✅ | **`GET /api/deliveries` criado (este PR)** |

**Bloqueadores para o cutover (`/`→`/app/`):** as telas de Funcionários e EPIs no
Flutter são **somente leitura** (faltam `EmployeesApi`/`EpisApi`). Antes de ligar
a flag em produção, esses clientes precisam ser criados para não haver regressão
de funcionalidade (CRUD existe no backend; é trabalho do lado Flutter).

---

## LOTE 3 — Devoluções, Ficha de EPI, Relatórios, Portal, Compras, Avaliações

> Todos consomem **clientes dedicados** do `epi_api` (não bootstrap). Os GET
> envolvidos foram cruzados contra as rotas do backend (cross-check de
> 2026-06-16): **existem e casam** (retornam `items`/dict esperado). Nenhum bug
> de endpoint fantasma neste lote.

### 9. Devoluções
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `Routes.returns` `/returns` (`DevolutionsCubit`) / `DevolutionsApi` |
| Endpoints | `GET /api/devolutions` (lista, `items`) · `GET /api/devolutions/open-deliveries` (`items`) · `POST /api/devolutions` (criar) |
| Permissões | `deliveries:view` / `deliveries:create` (escopo de devolução) |
| Paridade | ✅ — endpoints existem e casam |
| Aceite | lista e registro de devolução equivalentes ao legado |

### 10. Ficha de EPI
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `features/fichas` (`FichasCubit`) / `FichasApi` |
| Endpoints | `GET /api/fichas` (`items`) · `GET /api/ficha-config` |
| Permissões | `fichas:view` |
| Paridade | ✅ (finalização de período + WhatsApp já existiam no backend — sprint #2) |
| Observação | geração de PDF/portal CPF do legado já coberta pelo backend; UI do Flutter usa o mesmo fluxo |

### 11. Relatórios
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `Routes.reports` `/reports` (`ReportsCubit`) / `ReportsApi` |
| Endpoints | `GET /api/reports` (dict de agregações) · `GET /api/report-requests` (`items`) · `POST /api/report-requests` |
| Snapshot PDF | `GET /api/reports.pdf` (sprint #6) — **ainda não consumido** pelo `ReportsApi` |
| Permissões | `reports:view` / `stock:view` (requests) |
| Paridade | ✅ leitura; 🟡 follow-up: adicionar botão "Exportar PDF" no Flutter consumindo `/api/reports.pdf` |

### 12. Portal do colaborador
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `features/portal` (`PortalCubit`) / `PortalApi` |
| Endpoints | `POST /api/employee-lookup` · `GET /api/employee-access` · `GET /api/employee-access/pdf` · `POST /api/employee-sign` · `POST /api/employee-sign-batch` · `POST /api/employee-feedback` · `POST /api/employee-contact-launch` |
| Permissões | acesso por token CPF (HMAC, 48h) — sem login de usuário |
| Paridade | ✅ — fluxo CPF→assinatura→feedback equivalente; PDF da ficha disponível |
| Segurança | token assinado, expiração, auditoria de portal (sprint anterior) |

### 13. Compras
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `Routes.purchases` `/purchases` (`PurchasesCubit`) / `PurchasesApi` |
| Endpoints (Flutter) | `GET /api/purchase-requests` (`items`) · `GET /api/purchase-demands` (`items`) · `POST /api/purchase-requests` |
| Backend adicional | **workflow de PO multi-nível** (`POST /api/purchase-orders[/:id/...]`, sprint #3) — **não consumido** pelo `PurchasesApi` |
| Permissões | `purchase_requests:*`, `purchase_orders:*` |
| Paridade | 🟡 **parcial** — requisições ✅; **Ordens de Compra (criar/revisar/aprovar/receber) ausentes no Flutter** (existem no backend) |
| Follow-up | estender `PurchasesApi`/telas para o ciclo de PO |

### 14. Avaliações
| Campo | Conteúdo |
|---|---|
| Rota / cliente | `Routes.feedback` `/feedback` (`FeedbackCubit`) / `FeedbackApi` |
| Endpoints | `GET /api/feedbacks` (tolerante a `items`/`data`/`feedbacks`) · `POST /api/feedbacks/triage` · `/manager-validate` · `/close` |
| Pipeline backend | triagem → HSEQ → validação gestor → pré-avaliação → avaliação final → encerramento (já completo, sprint #7) |
| Permissões | `epi_feedback:*`, `epi_evaluation:*` |
| Paridade | 🟡 **parcial** — triagem/validação/encerramento ✅; **etapas HSEQ/pré-avaliação/avaliação-final/reavaliação/aceitar-sugestão ausentes no `FeedbackApi`** (existem no backend) |
| Follow-up | estender `FeedbackApi`/telas para o pipeline completo |

---

## Resumo consolidado (14 telas) e prontidão para cutover

| # | Tela | Estado | Pendência p/ paridade total |
|---|---|---|---|
| 1 | Login | ✅ | adotar refresh/`me` no Flutter |
| 2 | Dashboard | ✅ | `pendingPurchases` no bootstrap |
| 3 | Empresas | ✅ (corrigido) | — |
| 4 | Usuários | ✅ | — |
| 5 | Funcionários | 🟡 | **criar `EmployeesApi` (CRUD)** |
| 6 | EPIs | 🟡 | **criar `EpisApi` (CRUD)** |
| 7 | Estoque | ✅ | — |
| 8 | Entregas | ✅ (corrigido) | — |
| 9 | Devoluções | ✅ | — |
| 10 | Ficha de EPI | ✅ | — |
| 11 | Relatórios | ✅ | botão Exportar PDF no Flutter |
| 12 | Portal | ✅ | — |
| 13 | Compras | 🟡 | **PO workflow no Flutter** |
| 14 | Avaliações | 🟡 | **pipeline completo no Flutter** |

### Bloqueadores de cutover (todos do lado Flutter — backend pronto)

Antes de ligar `FLUTTER_WEB_ROOT_REDIRECT=1` em produção, sob pena de regressão
de funcionalidade:

1. **Funcionários** — criar `EmployeesApi` (create/update/delete + movimentações).
2. **EPIs** — criar `EpisApi` (CRUD).
3. **Compras** — estender `PurchasesApi`/telas para o ciclo de Ordens de Compra.
4. **Avaliações** — estender `FeedbackApi`/telas para o pipeline completo.

Itens não-bloqueantes (degradação aceitável): refresh/`me` no login, botão de
PDF em Relatórios, `pendingPurchases` no Dashboard.

> **Importante:** esses 4 bloqueadores são **código Dart** (clientes + telas do
> Flutter). Não há Flutter SDK neste ambiente de backend para `flutter test`/
> `build`, então **não devem ser implementados às cegas aqui** — são entregas do
> time/ambiente Flutter, com seus próprios testes de widget/integração. O backend
> já expõe 100% das APIs necessárias (sprints #1–#7 + correções de paridade).

### Estado do plano de migração

| Fase | Estado |
|---|---|
| 0 Congelamento do legado | ✅ (build determinístico + teste round-trip) |
| 1 Refatorar `app.py` | 🟡 (cache extraído; demais extrações opcionais) |
| 2 Contrato de API | 🟡 (`send_api_response` + `/auth/*` prontos; migração por módulo em curso) |
| 3 Coexistência legado+Flutter | ✅ em produção (`/` legado, `/app/` Flutter) |
| 4 Paridade de telas | ✅ **diagnóstico completo (14 telas)**; correções de backend feitas; 4 bloqueadores Flutter mapeados |
| 5 Cutover de `/` | ✅ infra pronta (flag `FLUTTER_WEB_ROOT_REDIRECT`, default OFF) — aguarda resolver bloqueadores Flutter |
| 6 Descomissionar legado | ⬜ futuro (checklist em `docs/ARQUITETURA_FRONTEND_BACKEND.md`) |

**Conclusão:** o lado **backend da migração está concluído** — todas as APIs
existem, os bugs de paridade (Empresas, Entregas) foram corrigidos, a infra de
cutover está pronta e reversível. O caminho crítico restante é **trabalho no app
Flutter** (4 clientes/telas de CRUD) + validação de paridade em produção, ambos
fora do escopo verificável deste ambiente de backend.
