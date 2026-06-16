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

## Próximos parity sheets (lote 3)

Devoluções, Ficha de EPI, Relatórios, Portal do colaborador, Administração
multiempresa, Compras, Avaliações — mesmo template.
