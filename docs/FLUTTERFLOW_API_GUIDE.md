# Guia de Integração FlutterFlow ↔ API EPI Controle

> Para construir o frontend no **FlutterFlow** consumindo a API REST Python já
> existente. **Decisão de arquitetura:** o FlutterFlow é um frontend **novo** que
> chama os endpoints `/api/*`; ele **não** roda o app hand-coded
> `flutter/apps/epi_admin` (que usa melos/BLoC/retrofit — incompatível com o
> modelo do FlutterFlow). O backend já expõe tudo o que o FlutterFlow precisa.

## 0. Por que FlutterFlow consumindo a API (e não importando o Flutter atual)

| | App `epi_admin` (atual) | FlutterFlow |
|---|---|---|
| Natureza | Flutter hand-coded (62 .dart, cubits, retrofit) | low-code visual, gera projeto próprio |
| Como roda | `flutter run`/`melos` (precisa Flutter SDK) | runner web do FlutterFlow |
| Reuso do existente | total | **não importa** o `epi_admin` |
| Acoplamento com backend | clientes tipados `epi_api` | **API Calls** (REST) configuradas na UI |

Conclusão: no FlutterFlow você **recria as telas** e as liga aos endpoints abaixo.
O backend (auth, RBAC, multiempresa, regras de EPI, PDF, etc.) permanece a fonte
da verdade.

## 1. Base URL e ambientes

- Produção (Render): `https://<seu-servico>.onrender.com`
- API sob `/api/...`; legado em `/`; Flutter atual em `/app/`.
- No FlutterFlow: **Settings → API Calls → API Base URL** = a URL acima.

## 2. Autenticação (JWT Bearer)

Fluxo:
1. `POST /api/login` com `{ "username": "...", "password": "..." }`.
2. Resposta inclui `token` (access, ~8h), `refresh_token` (~30d), `permissions`, `user`.
3. Guarde `token` em **App State** (`authToken`) e envie em todas as chamadas:
   header `Authorization: Bearer [authToken]`.
4. Quando uma chamada retornar **401 "Sessão expirada"**, chame
   `POST /api/auth/refresh` com `{ "refresh_token": "[refreshToken]" }` para obter
   novo `token` (+ `refresh_token` rotacionado), e repita a chamada.
5. `GET /api/auth/me` (Bearer) devolve `{ data: { user, permissions } }` — útil
   para reidratar a sessão ao abrir o app.

> Multiempresa/RBAC são garantidos no **backend** pelo token (claims `sub`,
> `role`, `company_id`). O FlutterFlow só exibe o que a API retorna; não confie em
> esconder dados só na UI — o backend já isola por empresa.

### Configuração no FlutterFlow
- Header comum em todas as API Calls: `Authorization: Bearer [authToken]`.
- Alguns endpoints aceitam também `?actor_user_id=<id>` (compat); com Bearer não
  é necessário.

## 3. Envelope de resposta (como parsear)

Dois formatos convivem (transição):
- **Novos** (`/api/auth/me`, e futuros): `{ "success": true, "data": {...}, "message": "" }`.
- **Existentes**: sucesso `{ "ok": true, ...campos }`; listas em chaves próprias
  (`items`, `companies`, `users`, `deliveries`, `epis`, ...). Erro:
  `{ "ok": false, "error": { "code", "message" } }` com HTTP status correto.

No FlutterFlow, em cada API Call use **JSON Path** para extrair:
- lista: `$.items` (ou `$.companies`, `$.users`, `$.deliveries` conforme a tabela).
- erro: status HTTP ≥ 400 → ler `$.error.message`.

> **Nunca** exiba `error.message` técnico cru? Pode exibir — as mensagens já são
> seguras para o usuário (o backend não vaza stacktrace; isso fica só em log).

## 4. CORS (necessário para o Test Mode do FlutterFlow)

O Test Mode roda no navegador → precisa de CORS.
- **Dev** (`APP_ENV` ≠ prod): `Access-Control-Allow-Origin: *` (já liberado).
- **Prod**: defina a env `CORS_ALLOW_ORIGIN` com o domínio do app FlutterFlow
  (ex.: `https://app.flutterflow.io,https://<seu-app>.flutterflow.app`).
  Preflight `OPTIONS` já é tratado (204 + headers CORS).

## 5. Catálogo de endpoints (curado para um MVP)

Auth e bootstrap:
| Método | Path | Corpo / Query | Resposta (JSON path) |
|---|---|---|---|
| POST | `/api/login` | `{username,password}` | `token`, `refresh_token`, `user`, `permissions` |
| POST | `/api/auth/refresh` | `{refresh_token}` | `token`, `refresh_token` |
| GET | `/api/auth/me` | Bearer | `$.data.user`, `$.data.permissions` |
| GET | `/api/bootstrap` | Bearer | `companies`, `users`, `units`, `employees`, `epis`, `deliveries`, `alerts`, ... (carga inicial) |

Cadastros (CRUD):
| Método | Path | Observação |
|---|---|---|
| GET/POST | `/api/companies` | lista em `$.items` (e `$.companies`); criar empresa |
| GET | `/api/companies/{id}` | `$.company` (inclui `user_count`, `near_limit`, `limit_reached`) |
| PUT | `/api/companies/{id}` | atualizar |
| GET/POST | `/api/users` | lista `$.users`; criar |
| GET/PUT/DELETE | `/api/users/{id}` | item (senha nunca exposta), atualizar, excluir |
| GET/POST | `/api/units` | lista `$.units` |
| GET | `/api/units/{id}` | `$.unit` |
| PUT/DELETE | `/api/units/{id}` | atualizar/excluir |
| GET/POST | `/api/employees` | lista `$.employees`; criar |
| GET | `/api/employees/{id}` | `$.employee` (com `current_unit_name`, `unit_allocation_type`) |
| PUT/DELETE | `/api/employees/{id}` | atualizar/excluir |
| GET/POST | `/api/employee-unit-movements` | movimentações de unidade |
| POST/PUT/DELETE | `/api/epis`, `/api/epis/{id}` | CRUD de EPI |

Operação:
| Método | Path | Observação |
|---|---|---|
| GET/POST | `/api/deliveries` | lista `$.deliveries`/`$.items`; registrar entrega |
| GET/POST | `/api/devolutions` | lista `$.items`; registrar devolução |
| GET | `/api/devolutions/open-deliveries` | entregas elegíveis a devolução |
| GET | `/api/fichas` | períodos de ficha `$.items` |
| POST | `/api/fichas/finalize` | finaliza período + gera link WhatsApp |
| GET | `/api/stock/epis`, `/api/stock/low`, `/api/stock/available-items` | estoque |
| POST | `/api/stock/movements` | movimento de estoque |
| GET | `/api/reports` | relatório (dict de agregações) |
| GET | `/api/reports.pdf` | **snapshot PDF** (download) |

Portal do colaborador (acesso por CPF, sem login):
| Método | Path | Observação |
|---|---|---|
| POST | `/api/employee-lookup` | `{cpf}` → token de portal |
| GET | `/api/employee-access` | dados da ficha do colaborador |
| GET | `/api/employee-access/pdf` | PDF da ficha |
| POST | `/api/employee-sign`, `/api/employee-sign-batch` | assinatura |
| POST | `/api/employee-feedback` | avaliação de EPI pelo colaborador |

Compras (ciclo completo no backend):
| Método | Path | Observação |
|---|---|---|
| GET/POST | `/api/purchase-requests` | requisições `$.items` |
| GET | `/api/purchase-requests/{id}` | detalhe + itens + eventos |
| POST | `/api/purchase-requests/{id}/workflow` | ações de aprovação da requisição |
| GET/POST | `/api/purchase-orders` | Ordens de Compra |
| POST | `/api/purchase-orders/{id}/review\|approve\|receive\|resubmit\|files` | workflow de PO multi-nível |

Avaliações (pipeline triage→admin):
| Método | Path | Observação |
|---|---|---|
| GET | `/api/feedbacks`, `/api/feedbacks/{id}` | lista `$.items`; detalhe |
| POST | `/api/feedbacks/triage\|hseq-review\|manager-validate\|manager-reject\|forward-admin\|close` | etapas do pipeline |
| POST | `/api/avaliacoes/pre-evaluate\|admin-evaluate\|set-reassessment\|accept-suggestion\|compute-status` | avaliação técnica |
| GET | `/api/avaliacoes/summary\|ranking\|ranking-sugestoes` | dashboards |

> Os corpos exatos (campos por endpoint) estão nas rotas em `modules/<dominio>/
> routes.py` (`require_fields(...)`). Use-os como contrato de request no FlutterFlow.

## 6. i18n e tenant (opcionais)

- `GET /api/i18n` e `GET /api/i18n/{locale}` → traduções (pt-BR, en-GB, es-ES, fr-FR, nb-NO).
- `GET /api/tenant/resolve`, `/api/tenant/branding` → white-label por empresa (logo, cores).

## 7. Ordem recomendada de construção no FlutterFlow

Espelha os parity sheets (`docs/PARITY_SHEETS.md`), do mais simples ao mais rico:

1. **Login** (+ App State `authToken`/`refreshToken`; ação de refresh em 401).
2. **Dashboard** (consumir `/api/bootstrap`: contadores de EPIs vencidos/críticos, entregas do dia, alertas).
3. **Empresas** (`/api/companies`).
4. **Usuários** (`/api/users`).
5. **Funcionários** (`/api/employees`).
6. **EPIs** (`/api/epis`).
7. **Estoque** (`/api/stock/*`).
8. **Entregas** (`/api/deliveries`) — incluir QR (FlutterFlow tem widget de scanner) e assinatura na tela.
9. **Devoluções** (`/api/devolutions`).
10. **Ficha de EPI** (`/api/fichas` + finalize).
11. **Relatórios** (`/api/reports` + download `/api/reports.pdf`).
12. **Portal do colaborador** (fluxo CPF → assinatura).
13. **Compras** e **Avaliações** (workflows mais ricos, por último).

## 8. Boas práticas de segurança (já garantidas no backend)

- Senha: bcrypt; JWT assinado + expiração; refresh com rotação; rate-limit no login.
- Multiempresa: isolamento por empresa no backend (`authorize_action`/escopo).
- **Nenhum segredo no FlutterFlow**: só a base URL e o token do usuário (em App
  State). Não embuta chaves/segredos no app.

## 9. Limitações do FlutterFlow "basic" a considerar

- Recursos nativos (câmera/QR/assinatura): disponíveis via widgets do FlutterFlow,
  mas confira limites do plano free para deploy/custom code.
- Download de PDF (`/api/reports.pdf`, ficha): abrir a URL autenticada em nova aba
  ou via ação de download do FlutterFlow.
- Para produção, configure CORS (seção 4) e a base URL de prod.

---

**Resumo:** o backend está pronto para o FlutterFlow consumir hoje. Comece pelo
Login (seção 7), use Bearer + refresh (seção 2) e os JSON paths da seção 5. As
telas de CRUD que faltavam no `epi_admin` (Funcionários/EPIs/Compras/Avaliações)
deixam de ser bloqueador, porque no FlutterFlow você as constrói direto sobre a
API — sem depender do app hand-coded.
