# Arquitetura Frontend (Flutter) + Backend (Python) — Diagnóstico, Contrato de API e Plano de Separação

> **Etapa de planejamento — não altera código.** Para a reestruturação de pastas
> e a padronização de contrato de API vale a regra explícita: *primeiro o plano,
> sem mover/alterar código.* Métricas reais coletadas em 2026-06-16.
>
> Complementa (não duplica) `docs/PLANO_MIGRACAO_FLUTTER_WEB.md`, que já cobre o
> diagnóstico de `app.py`/`app.js`/`index.html` e as fases de cutover. Aqui o
> foco é: **separação física FE/BE, contrato REST padronizado e segurança.**

---

## Entregável 1 — Relatório da arquitetura atual

**Já é uma arquitetura cliente/servidor real**, apenas não fisicamente separada
em pastas `backend/`/`frontend/`:

| Camada | Hoje | Observação |
|---|---|---|
| Backend Python | `app.py` (http.server) + `core/` + `modules/` (18) + `epi_backend/` | 161 rotas REST via `core/router.py` |
| Frontend Flutter | `flutter/` (monorepo melos): `apps/epi_admin` + `packages/epi_api,epi_design,epi_i18n` | servido em `/app/`, build no Dockerfile |
| Frontend legado | `static/` (`index.html` build + `views/` + `app.js`) | servido em `/`; "Legacy Web SPA" |
| Banco | Postgres/Supabase via `core/database` | **acessado só pelo backend** ✅ |
| Deploy | `Dockerfile` multi-stage + `render.yaml` | Flutter build → `static/app/` |

**Já atende vários critérios de aceite:** banco só no backend; Flutter não acessa
DB; regras de negócio (vencimento de EPI, bloqueio de entrega, estoque, ficha,
PDF) vivem em `modules/*` no Python; legado coexiste com Flutter.

**Lacunas frente ao pedido:**
1. Pastas não separadas em `backend/`/`frontend/`/`legacy/`/`docker/`.
2. Envelope de resposta é `{ok}`, não `{success,data,message}`.
3. Namespaces de auth são `/api/login` etc., não `/api/auth/login`.
4. Pacotes Flutter `epi_auth` e `epi_features` ainda não existem.
5. Refresh token não implementado (só access token com `exp`).

---

## Entregável 2 — Plano de separação Frontend/Backend (reestruturação de pastas)

> **Risco alto** (toca imports Python, Dockerfile, render.yaml, paths de testes
> e `build_index.py`). Executar **só após** o plano aprovado, em PRs isolados.

### Mapa de movimentação

| De (atual) | Para (alvo) | Impacto a tratar |
|---|---|---|
| `app.py`, `core/`, `modules/`, `epi_backend/`, `supabase/` (migrations) | `backend/` | imports `from core...` continuam válidos se `WORKDIR=backend/` (CWD na raiz do pacote) |
| `tests/` | `backend/tests/` | `pytest` roda a partir de `backend/`; ajustar paths relativos (`ROOT`) |
| `flutter/` | `frontend/flutter/` | `Dockerfile` `COPY flutter/ .` → `COPY frontend/flutter/ .`; melos paths |
| `static/`, `scripts/build_index.py` | `legacy/static/`, `legacy/scripts/` | `app.py` `BASE_DIR`, serving, e `build_index` paths; Dockerfile `build_index` |
| `Dockerfile`, `render.yaml` infra | `docker/` (+ raiz aponta) | `render.yaml: dockerfilePath` |

### Estratégia segura (incremental, reversível)

1. **Não mover tudo de uma vez.** Mover um diretório por PR, com testes verdes
   e `docker build` validado a cada passo.
2. **Preferir um "ponteiro" antes do move físico:** ex.: introduzir `backend/`
   como pacote e reexportar, ou usar `git mv` + ajuste de paths num único PR
   atômico por diretório.
3. **Ordem recomendada (menor acoplamento primeiro):**
   `tests/` → `legacy/` (static + scripts) → `frontend/flutter/` → `docker/` →
   por fim `backend/` (core/modules/app.py) — o mais arriscado por último.
4. **Invariantes a cada PR:** `pytest` verde; `node static/js/test/run-tests.js`
   verde; `docker build` ok; `/`, `/app/`, `/api/*`, `/health` inalterados.

### Pontos críticos que quebram se feitos sem cuidado
- `app.py: BASE_DIR = .../static` → vira `.../legacy/static`.
- `Dockerfile`: `COPY --from=flutter-builder /src/apps/...` e `RUN python
  scripts/build_index.py build` e `WORKDIR /app`.
- `render.yaml: dockerfilePath: ./Dockerfile` → `./docker/Dockerfile`.
- `tests/test_index_html_build.py` calcula `ROOT` por path relativo.

> **Recomendação:** a separação de pastas é **cosmética/organizacional** e de
> **alto risco operacional**. Sugiro **adiar** para depois do cutover (Fase 6),
> priorizando contrato de API e migração de telas — que entregam valor real ao
> usuário sem o risco de um "big move".

---

## Entregável 3 — Mapa de endpoints REST (atual → alvo)

### Envelope de resposta — decisão de contrato

**Hoje:** sucesso `{"ok": true, ...campos}`; erro `{"ok": false, "error":
{"code","message"}}` com HTTP status correto. Consumido pelo `epi_api` (Flutter)
**e** pelo `app.js` (legado).

**Pedido:** `{"success": true, "data": {}, "message": "..."}` /
`{"success": false, "error": {"code","message"}}`.

**Plano (sem big-bang, sem quebrar Flutter/legado):**
1. Criar helper `send_api_response(handler, status, *, data=None, message='',
   error=None)` que emite o **novo** envelope, **incluindo também `ok`** por um
   período (compat): `{"success": true, "ok": true, "data": {...}, "message": ...}`.
2. **Novos** endpoints (ex.: `/api/auth/*`) nascem no envelope novo.
3. Migrar endpoints existentes **um módulo por vez**, atualizando o cliente
   `epi_api` correspondente no mesmo PR; manter `ok` até o legado deixar de usá-lo.
4. Remover o campo `ok` legado só na Fase 7 (descomissionamento).

> Regra mantida: **nunca** retornar erro técnico interno ao cliente — `code`
> estável + `message` segura; stacktrace só em log (`structured_log`). Isso já é
> o comportamento atual nos `do_*` (500 genérico + log).

### Namespaces (atual → alvo)

| Alvo (pedido) | Atual | Ação |
|---|---|---|
| `POST /api/auth/login` | `POST /api/login` | **alias novo** que reusa o handler atual (manter `/api/login` até Flutter migrar) |
| `POST /api/auth/logout` | (logout é client-side: descarta token) | criar endpoint stateless (registra auditoria) |
| `GET /api/auth/me` | parte de `/api/bootstrap` | extrair "me" enxuto do bootstrap |
| `GET/POST /api/companies` | ✅ existe (+ `GET /:id`) | manter |
| `GET/POST /api/users` | ✅ existe (+ `GET /:id`) | manter |
| `GET/POST /api/employees` | ✅ existe (+ `GET /:id`, movimentações) | manter |
| `/api/epis` | ✅ existe | manter |
| `/api/stock` | ✅ `modules/stock` | manter |
| `/api/deliveries` | ✅ `modules/deliveries` | manter |
| `/api/returns` | ✅ `modules/devolutions` | alinhar nome (`returns` ↔ `devolutions`) |
| `/api/reports` | ✅ (+ `/api/reports.pdf`) | manter |
| `/api/audit` | parcial (`*_audit_logs` no bootstrap) | endpoint dedicado a criar |
| `/api/portal` | ✅ `modules/portal` | manter |

> **161 rotas** já existem. O trabalho é de **padronização de envelope + alias de
> namespaces**, não de criar a API do zero.

---

## Entregável 4 — Plano de migração legado → Flutter

Ver `docs/PLANO_MIGRACAO_FLUTTER_WEB.md` (Fases 0–6). Mapeamento para as 7 fases
deste pedido:

| Fase (pedido) | Estado | Onde |
|---|---|---|
| 1 Diagnóstico | ✅ feito | este doc + plano anterior |
| 2 API Contract | 🟡 a fazer | Entregável 3 (envelope + namespaces) |
| 3 Flutter ↔ Backend (API/Auth client, token, interceptor, sessão) | ✅ em grande parte | `epi_api` (auth interceptor, models) já existe |
| 4 Migrar telas essenciais | 🟡 paridade | telas Flutter já existem; verificar paridade |
| 5 Coexistência | ✅ em produção | `/` legado, `/app/` Flutter, `/api/` |
| 6 Virada oficial | ⬜ próximo | flag de cutover de `/` (default OFF) |
| 7 Remoção do legado | ⬜ futuro | checklist (Entregável 8) |

---

## Entregável 5 — Plano de testes

- **Backend (pytest, ~851 testes):** contrato de envelope (`success`+`ok` no
  período de compat), namespaces alias, RBAC, **tenant isolation** (empresa A ⊄
  empresa B — já coberto), auth (login, rate-limit, token expirado).
- **Frontend legado:** `node static/js/test/run-tests.js` (89) + round-trip do
  `index.html`.
- **Flutter:** `flutter test` (widget + cubits + `epi_api`) e `integration_test`;
  `melos run build:web`.
- **Deploy:** `docker build` multi-stage; Render (`render.yaml`, assets, cache).
- **Contrato:** testes de "golden response" garantindo o shape `{success,data,
  message}` por endpoint migrado.

---

## Entregável 6 — Plano de segurança (relatório de validação)

| Item | Estado | Evidência / ação |
|---|---|---|
| Senha com bcrypt | ✅ | `core/security.hash_password`/`verify_password`, `BCRYPT_AVAILABLE` |
| JWT assinado + expiração | ✅ | HMAC-SHA256, claim `exp` = `JWT_EXP_SECONDS`, valida `exp` |
| Rate limit no login | ✅ | `core/rate_limit.login_limiter`, code `AUTH_RATE_LIMITED` |
| Mensagem genérica de login inválido | ✅ validar | confirmar que não distingue "usuário" de "senha" |
| Sem senha padrão | ✅ validar | `ensure_initial_master_admin` exige config; teste `test_phase21a` cobre JWT em prod |
| Headers de segurança | ✅ | `_apply_default_response_headers` (CTO, XFO, Referrer, Permissions-Policy, HSTS em prod) |
| CSP | 🟡 report-only | mover a blocking só após modularizar inline (e `'wasm-unsafe-eval'` p/ Flutter) |
| CORS restrito | 🟡 | `CORS_ALLOW_ORIGIN` default `*` (em prod restringir por env) |
| Auditoria de ações críticas | ✅ parcial | `*_audit_logs` (company, ficha, portal, purchase_events) |
| Validação de tenant | ✅ | `authorize_action` + `ensure_resource_company`/`ensure_company_access` |
| Permissão por perfil | ✅ | `core/permissions.PERMISSIONS` + `hasPermission`/`canViewRoute` |
| Nenhum segredo no Flutter | ✅ validar | `epi_api` usa só base URL + token; sem chaves embutidas |
| **Refresh token** | ⬜ **gap** | implementar refresh + rotação; hoje só access token com `exp` |

**Ações de segurança priorizadas:** (1) refresh token + rotação; (2) restringir
CORS em produção via env; (3) endpoint `/api/auth/me` enxuto; (4) caminho para
CSP enforce.

---

## Entregável 7 — Plano de rollback

- **Reestruturação de pastas:** cada move é um PR atômico revertível; manter
  símbolo/compat até o build validar; reverter restaura paths.
- **Contrato de API:** envelope é **aditivo** (`success` ao lado de `ok`) →
  reverter o helper não quebra clientes que ainda leem `ok`.
- **Cutover de `/`:** atrás de feature flag → desligar a flag volta ao legado
  **sem deploy**.
- **Invariante absoluto:** login do legado nunca pode quebrar; se o Flutter
  falhar, `/` permanece no legado.

---

## Entregável 8 — Checklist final para remover o legado (Fase 7)

- [ ] `/` redireciona para `/app/` há ≥1 release sem incidentes.
- [ ] `/legacy/` validado como emergência, sem tráfego relevante.
- [ ] Nenhum teste depende de `static/index.html` / `static/views/` / `app.js`.
- [ ] Nenhuma rota serve `index.html` (exceto `/legacy/`, se mantido).
- [ ] Dockerfile não roda mais `build_index.py`.
- [ ] Health/smoke atualizados para Flutter como frontend único.
- [ ] Clientes não leem mais o campo `ok` (envelope só `{success,data,message}`).
- [ ] Remoções em PRs separados e reversíveis.

---

## Entregável 9 — Estrutura de pastas final (alvo)

```text
/
├── backend/         core/ modules/ epi_backend/ migrations/ tests/ app.py
├── frontend/flutter/ apps/epi_admin  packages/{epi_api,epi_design,epi_auth,epi_i18n,epi_features}
├── legacy/          static/ static/views/ static/app.js scripts/build_index.py
├── docker/          Dockerfile (+ compose)
├── docs/
└── README.md
```
(`epi_auth` e `epi_features` a criar; ver Entregável 2 para a estratégia de move.)

---

## Entregável 10 — Ordem de implementação por prioridade

> Menor risco / maior valor primeiro. Cada item = 1+ PR com testes e rollback.

1. **Segurança incremental** (alto valor, baixo risco): refresh token; CORS
   restrito por env em prod; `/api/auth/me` enxuto. *(começa já)*
2. **API Contract (Fase 2)**: helper `send_api_response` (envelope `success`
   aditivo) + alias `/api/auth/login`/`logout`/`me`; migrar `epi_api` em paralelo.
3. **Cutover flag (Fase 6)**: redirect `/`→`/app/` atrás de flag default OFF +
   `/legacy/`. *(reversível sem deploy)*
4. **Paridade de telas (Fase 4)**: parity sheets Login/Dashboard/Empresas/Usuários.
5. **Pacotes Flutter** `epi_auth`/`epi_features` (refatoração interna do FE).
6. **Reestruturação de pastas (Entregável 2)**: **por último**, pós-cutover,
   1 diretório por PR — o passo mais arriscado e de menor valor imediato.

---

## Conclusão

O EPI Controle **já é** FE (Flutter) + BE (Python) conversando por REST, com
banco isolado no backend, segurança sólida (JWT/bcrypt/rate-limit/tenant) e
coexistência legado+Flutter em produção. O caminho para "sistema único e
profissional" é **padronizar o contrato de API, fechar gaps de segurança
(refresh/CORS), virar `/` para o Flutter atrás de flag e, por último, reorganizar
as pastas** — tudo incremental, testado e reversível, sem perder funcionalidade
nem quebrar Docker/Render.
