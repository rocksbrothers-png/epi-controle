# Parity Sheets — Legado (Web SPA) × Flutter Web (Fase 4)

> Verificação de **paridade** por tela entre o legado (`static/app.js` + views) e
> o Flutter Web (`flutter/apps/epi_admin`), com endpoints, permissões, fonte de
> dados, testes, critério de aceite e rollback. Primeiro lote: **Login,
> Dashboard, Empresas, Usuários** (ordem do plano). Base: código real em
> 2026-06-16. Complementa `docs/ARQUITETURA_FRONTEND_BACKEND.md`.

## Como ler

Cada tela tem: rota legado, rota Flutter, endpoints/fonte de dados, permissões,
componentes, **estado de paridade** (✅ paridade / 🟡 parcial / 🐞 bug), testes e
rollback. Bugs de paridade encontrados são registrados e, quando triviais e
seguros, corrigidos no mesmo PR.

---

## 1. Login

| Campo | Conteúdo |
|---|---|
| Rota legado | `_login.html` (tela de login do SPA), `handleLogin` em `app.js` |
| Rota Flutter | `Routes.login = '/login'` → `features/auth/login_screen.dart` (`AuthCubit`) |
| Endpoint | `POST /api/login` (ambos). Flutter: `epi_api/endpoints/auth_api.dart` |
| Fonte de sessão | token JWT salvo no cliente; restauração via `getToken`/`getPermissions` (Flutter) e `tryRestoreSession` (legado) |
| Permissões | pública (pré-auth) |
| Componentes | usuário, senha, erro genérico de credencial inválida |
| Paridade | ✅ paridade funcional |
| 🟡 Gap (não bloqueante) | O backend ganhou `POST /api/auth/refresh` e `GET /api/auth/me` (PRs #590/#591), mas o `epi_api` ainda **não os consome** — login continua só com access token. **Follow-up:** adotar refresh + `/me` no `AuthInterceptor` do Flutter. |
| Testes | backend: `test_auth_refresh_token.py`, `test_api_contract_envelope.py`; Flutter: widget test de login + cubit |
| Aceite | login com credencial válida autentica; inválida mostra mensagem genérica; sessão persiste |
| Rollback | legado em `/legacy/` e em `/` (flag de cutover OFF) garante login sempre disponível |

---

## 2. Dashboard

| Campo | Conteúdo |
|---|---|
| Rota legado | view `dashboard` (`app.js renderDashboard`) |
| Rota Flutter | `Routes.dashboard = '/'` (no app Flutter) → `features/dashboard/dashboard_screen.dart` (`DashboardCubit`) |
| Endpoint / fonte | `GET /api/bootstrap` (ambos). Flutter: `DashboardCubit.load()` deriva métricas do bootstrap |
| Métricas | EPIs vencidos/críticos, entregas do dia, alertas |
| Permissões | `dashboard:view` |
| Paridade | ✅ paridade (mesma fonte: bootstrap) |
| 🟡 Observação | `pendingPurchases` marcado como TODO no `DashboardCubit` (bootstrap ainda não traz dados de compras). Follow-up de paridade fina, não bloqueante. |
| Testes | backend: bootstrap (`test_*_bootstrap*`); Flutter: cubit test de métricas |
| Aceite | cartões de métrica refletem os mesmos números do legado para a mesma empresa |
| Rollback | flag de cutover OFF mantém dashboard legado |

---

## 3. Empresas

| Campo | Conteúdo |
|---|---|
| Rota legado | view `empresas` (`app.js renderCompanies/saveCompany`) |
| Rota Flutter | `Routes.companies = '/companies'` → `features/companies/companies_screen.dart` (`CompaniesCubit`) |
| Endpoints | Lista: `GET /api/companies`. Criar/editar: `POST`/`PUT /api/companies[/:id]`. Flutter lista via `CompaniesApi.getCompanies()` |
| Permissões | `companies:view` (lista); `companies:create/update` (mutações; master_admin) |
| Fonte de dados | legado: bootstrap; Flutter: `GET /api/companies` |
| Paridade | 🐞→✅ **bug de paridade encontrado e corrigido neste PR** |
| 🐞 Bug | `CompaniesApi.getCompanies()` lê `data['items']`, mas `GET /api/companies` (PR #584) retornava `{'companies': [...]}` → **lista de empresas vinha vazia no Flutter**. |
| Correção | `handle_get_companies` passa a retornar `{'companies': data, 'items': data}` (aditivo; `companies` mantido por compat). Teste em `test_companies_get_endpoints.py`. |
| Campos | inclui `user_count`, `near_limit`, `limit_reached` (corrigidos nos PRs #584/#586) |
| Testes | `test_companies_get_endpoints.py` (envelope com `items`, escopo, flags) |
| Aceite | Flutter lista as mesmas empresas do legado, com contagem de usuários e badges de risco |
| Rollback | reverter o alias `items` (legado/bootstrap não dependem dele) |

---

## 4. Usuários

| Campo | Conteúdo |
|---|---|
| Rota legado | view `usuarios` (`app.js saveUser/startEditUser/deleteUser`) |
| Rota Flutter | `Routes.users = '/users'` → `features/users/users_screen.dart` (`UsersCubit`) |
| Endpoints | Lista: bootstrap (`bootstrap.users`). Criar: `POST /api/users`. Editar: `PUT /api/users/:id`. Excluir: `DELETE /api/users/:id`. Flutter: `UsersApi` |
| Permissões | `users:view` (lista); `users:create/update/delete` (mutações) |
| Fonte da lista | **ambos via bootstrap** (Flutter `UsersCubit.load()` usa `bootstrap.users`) |
| Paridade | ✅ paridade (lista por bootstrap; CRUD pelos endpoints) |
| 🟡 Observação | Existe `GET /api/users` dedicado (PR #582) retornando `{'users': [...]}`, **não consumido** pelo Flutter (usa bootstrap). Sem mismatch, mas para futura adoção o cliente deve ler `users` (ou padronizar via `send_api_response`). |
| Segurança | senha nunca exposta no `GET /api/users/:id` (sanitizada no #582) |
| Testes | `test_users_units_get_endpoints.py` (escopo, sanitização de senha) |
| Aceite | Flutter cria/edita/exclui usuário com o mesmo RBAC e escopo de empresa do legado |
| Rollback | mutações usam endpoints já estáveis; lista via bootstrap (sem mudança) |

---

## Resumo de achados

| Tela | Estado | Ação |
|---|---|---|
| Login | ✅ paridade | adotar `/auth/refresh` + `/auth/me` no `epi_api` (follow-up) |
| Dashboard | ✅ paridade | trazer `pendingPurchases` ao bootstrap (follow-up fino) |
| Empresas | 🐞→✅ | **bug `items` vs `companies` corrigido neste PR** |
| Usuários | ✅ paridade | (opcional) consumir `GET /api/users` dedicado no futuro |

**Padrão de envelope nos endpoints dedicados:** os GET adicionados nas sprints
anteriores usam chaves específicas (`companies`, `users`, `units`, `employees`).
A convergência para `send_api_response` (`{success,data,message}`) deve ocorrer
**módulo a módulo, junto com o cliente `epi_api`** — registrado como dívida no
plano de contrato (Fase 2). Enquanto isso, aliases aditivos (como `items` em
Empresas) evitam quebra de paridade.

## Próximos parity sheets (lotes seguintes)

Funcionários, EPIs, Estoque, Entregas, Devoluções, Ficha de EPI, Relatórios,
Portal do colaborador, Administração multiempresa — mesmo template.
