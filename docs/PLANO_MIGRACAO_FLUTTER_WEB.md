# Plano de Migração para Flutter Web + Refatoração do Legado

> **Status deste documento:** diagnóstico técnico (Etapa 1 — somente análise, sem
> alteração de código). Baseado em métricas reais do repositório coletadas em
> 2026-06-16.

---

## Sumário executivo (reality check)

O briefing original assume um cenário "greenfield" (introduzir o Flutter Web do
zero). **A auditoria do código mostra um estado bem mais avançado.** Os números
abaixo re-ancoram o plano na realidade:

| Frente | Premissa do briefing | Estado real medido |
|---|---|---|
| Backend `app.py` | monolito a quebrar | **já modular**: 1.063 linhas, 18 módulos, 161 rotas via `register_routes` + `core/router.py` |
| Coexistência legado+Flutter (Fase 3) | a construir | **já em produção**: `/` = legado, `/app/` = Flutter Web, mesma API |
| Build do Flutter Web | a configurar | **já no Dockerfile** (multi-stage melos → `static/app/`) |
| App Flutter (`epi_admin`) | a criar | **62 arquivos Dart**, cubits + telas para *todos* os domínios |
| Cliente de API Flutter (`epi_api`) | a criar | **presente**: clientes tipados + modelos + auth interceptor |
| Extração do `app.js` (Fase 2) | a iniciar | **em andamento**: ~5.678 de ~12.313 linhas já em `static/js/` |
| Decomposição do `index.html` | a planejar | **feita**: build a partir de 33 fragmentos, round-trip byte-idêntico testado |

**Implicação:** o trabalho restante **não é construir** o Flutter, e sim
**verificar paridade, fazer o cutover de `/` e descomissionar o legado com
segurança** — além de concluir a higienização incremental de `app.py`/`app.js`
já em curso. As fases foram reescritas para marcar explicitamente *JÁ FEITO* vs
*PENDENTE*.

Planos correlatos já existentes no repositório (a serem referenciados, não
duplicados):
- `spec/10-js-refactoring-plan.md` — refatoração do `app.js` (em andamento).
- `spec/11-index-html-refactoring-plan.md` — decomposição do `index.html` (concluída).
- `docs/PLANO_MODERNIZACAO_NAVEGACAO_UX.md` — modernização de navegação/UX.

---

# PARTE 1 — Diagnóstico

## 1.1 `app.py` (1.063 linhas)

Não é Flask: é um servidor `http.server` (`ThreadingHTTPServer` +
`EpiHandler(SimpleHTTPRequestHandler)`). O roteamento de API foi extraído para
`core/router.py` (`router.dispatch`) e cada módulo registra suas rotas.

**Estrutura medida:**

| Trecho | Linhas (aprox.) | Responsabilidade | Classificação |
|---|---|---|---|
| Imports + 20× `from modules.* import register_routes` | 1–115 | Wiring de módulos | **manter** (é o bootstrap de rotas) |
| `authenticate_login()` | 546 | Autenticação | **extrair → `modules/auth/`** (regra de negócio em app.py) |
| `bad_request/forbidden/not_found` | 567–577 | Respostas de erro | **extrair → `core/responses.py`/`core/errors.py`** |
| `humanize_integrity_error()` | 579 | Tradução de erro de banco | **extrair → `core/errors.py`** |
| `EpiHandler._apply_default_response_headers` | 625 | Headers de segurança/CORS | **extrair → `core/http_headers.py`** |
| `EpiHandler._handle_csp_report` | 695 | Coleta de CSP report | **extrair → `core/security_reports.py`** |
| `_is_static_request` / `_resolve_static_fallback_path` / `guess_type` | 731–778 | Arquivos estáticos + fallback SPA (legado `/` e Flutter `/app/`) | **extrair → `core/static_files.py`** |
| `_legacy_flutter_web_redirect` / `_redirect_legacy_flutter_web` | 745–765 | Redirect 308 `/flutter_web`→`/app/` | **extrair → `core/static_files.py`** |
| `_require_bootstrap_ready` (gate 503 enquanto migração roda) | 779 | Middleware de readiness | **extrair → `core/bootstrap_gate.py`** |
| `do_GET/HEAD/POST/PUT/DELETE/OPTIONS` | 726–967 | Dispatch HTTP | **manter** (fino; só orquestra) |
| `/health`, `/health/live`, `/ready`, `/health/ready` | 835–845 | Health checks | **extrair → `core/health.py`** |
| `main()` + `_run_init_db` (sobe porta antes do init_db, thread daemon) | 969–1063 | Bootstrap da aplicação | **manter** (é o entrypoint) |

**Veredito `app.py`:** já está enxuto para um handler `http.server`. As extrações
acima são **cosméticas/organizacionais** (reduzem ~300–400 linhas para `core/`),
não estruturais. Prioridade **baixa**, ganho real **médio** (testabilidade
isolada de headers/health/static).

## 1.2 `app.js` (12.313 linhas) + `static/js/` (5.678 linhas já extraídas)

`app.js` permanece a autoridade de runtime; `static/js/` recebe cópias modulares
de forma **aditiva** (padrão do `spec/10`: `globalThis.*` preservado, IIFE com
guard de duplo-carregamento). Já extraído:

```
static/js/core/      constants, permissions, feature-flags, config
static/js/utils/     debug, perf, storage, dom
static/js/modules/   api-client, auth, router, permissions-rt, feature-flags-rt
static/js/views/     dashboard, epis, estoque, fichas, purchases, feedback(+detail),
                     devolution, employee-portal, profile, ui-helpers, view-helpers
```

**Blocos ainda concentrados em `app.js` (classificação para o destino):**

| Bloco | Classificação |
|---|---|
| `state` global + sessão (`saveSession`, `tryRestoreSession`, storage keys) | **transformar em serviço compartilhado** (`static/js/modules/session.js`) |
| `hasPermission` (versão de 1 arg, conflitante com a de 2 args) — ver nota | **consolidar/remover** (dívida técnica já causou bug RBAC corrigido na #581) |
| `renderAll`, `showView`, `navigateToView`, `refs` (bindings de DOM) | **manter no legado temporariamente** (dependem de `refs` do IIFE) |
| Formulários CRUD (`saveUser`, `saveSimpleForm`, `saveCompany`, …) | **migrar para Flutter** (já há telas equivalentes) — manter no legado até cutover |
| Validações de formulário inline | **transformar em serviço compartilhado** ou migrar p/ Flutter |
| Fluxos de PO/compras, fichas, avaliações (lógica de workflow no cliente) | **migrar para Flutter** (cubits já existem) |
| Código duplicado entre `app.js` e `static/js/views/*` | **remover após migração** (manter sync até lá) |

> **Nota (dívida conhecida):** há duas funções globais `hasPermission` com
> assinaturas diferentes (`app.js` 1 arg vs `permissions-rt.js` 2 args). A ordem
> de carregamento faz `app.js` sobrescrever o global — já causou o falso
> `[RBAC] nenhuma view liberada` (corrigido na PR #581 usando `canViewRoute`).
> Consolidar para uma única fonte é pré-requisito de qualquer reescrita de auth no JS.

## 1.3 `static/index.html` (2.620 linhas) — **artefato de build, não editar**

Confirmado: é **gerado** por `python scripts/build_index.py build` a partir de:
- **22** fragmentos de view em `static/views/*.html`;
- **6** fragmentos de casca (`_head, _login, _sidebar, _topbar, _modals, _scripts`);
- **5** modais extraídos em `static/views/modals/*.html`;
- marcadores de inclusão no `_layout.html`.

**Dependências confirmadas (não remover agora):**
- Servido por `app.py` em `/` e `/index.html` (fallback SPA do legado).
- Construído no **Dockerfile** (`RUN python scripts/build_index.py build`).
- Coberto por **testes**: `tests/test_index_html_build.py` garante round-trip
  byte-idêntico (`build._assemble() == index.html`) e a existência de todos os
  fragmentos/marcadores.
- Health: `/health` e `/ready` **não** dependem do HTML (são JSON), mas o
  smoke de `/` depende do arquivo existir.

**Regra operacional confirmada:** **nunca editar `static/index.html` à mão.**
Editar fragmentos em `static/views/` e rodar o build (foi exatamente o que esta
sessão fez ao adicionar o botão "Exportar PDF" em `relatorios.html`).

---

# PARTE 2 — Arquitetura alvo

## 2.1 Backend Python (destino)

`app.py` como **bootstrap mínimo** (entrypoint + `main()` + thread de init_db).
Extrair para `core/` (já parcialmente existente — `core/router.py`,
`core/security.py`, `core/auth.py`, `core/responses` parcial):

```
app.py                  ← bootstrap mínimo (porta, init_db thread, servidor)
core/config.py          ← (já existe via epi_backend/config) consolidar
core/router.py          ← já existe (dispatch)
core/http_headers.py    ← NOVO: headers de segurança/CORS/CSP
core/static_files.py    ← NOVO: serving estático + fallback SPA (/ e /app/) + redirects
core/health.py          ← NOVO: /health, /health/live, /ready, /health/ready
core/bootstrap_gate.py  ← NOVO: gate 503 enquanto schema migra
core/errors.py          ← NOVO: humanize_integrity_error + mapeamento de exceções
core/responses.py       ← NOVO: bad_request/forbidden/not_found/send_json helpers
modules/*               ← já existem (auth, users, companies, employees, epis,
                          deliveries, stock, portal, reports, i18n, … 18 módulos)
```

**O que sai do `app.py`:** headers, CSP report, static/fallback, health,
bootstrap-gate, helpers de erro/resposta, `authenticate_login`. **O que fica:**
`main()`, threading de init_db, e os `do_*` (finos, só fazem dispatch).

## 2.2 Frontend legado — `Legacy Web SPA` (manter temporariamente)

Componentes a **manter e congelar** (descontinuação por fases):
`static/index.html` · `static/views/` · `static/app.js` · `static/js/` ·
`scripts/build_index.py`. Documentado como **Legacy Web SPA**, servido em `/`.

## 2.3 Flutter Web — frontend oficial (já existente)

Monorepo `flutter/` (melos), **já presente**:

```
flutter/
  apps/epi_admin/      ← app principal (62 .dart): main, app_shell, router,
                         features/* (login, dashboard, companies, employees,
                         epis, stock, deliveries, returns, records, purchases,
                         reports, settings, units, users, feedback, portal, qr),
                         core/bloc/* (18 cubits), core/i18n (5 idiomas gerados),
                         core/sync, notifications
  packages/epi_api/    ← cliente HTTP tipado + modelos + auth interceptor
  packages/epi_design/ ← design system
  packages/epi_i18n/   ← internacionalização
  (sugeridos, ainda NÃO criados): packages/epi_auth, packages/epi_features
```

**Roteamento (atual):** `/` = legado; `/app/` = Flutter Web (servido por
`app.py` a partir de `static/app/`, gerado no Dockerfile); `/flutter_web*`
redireciona 308 → `/app/`. Rotas internas do Flutter em
`flutter/apps/epi_admin/lib/core/router/routes.dart` (login, dashboard,
employees, epis, stock, deliveries, returns, records, purchases, reports,
settings, companies, users, units, portal, qr, feedback).

**Alvo final:** após paridade comprovada, `/` redireciona para `/app/` e
`/legacy/` mantém o SPA antigo como saída de emergência.

---

# PARTE 3 — Estratégia de migração em fases (re-ancorada)

> Marcadores: ✅ JÁ FEITO · 🟡 EM ANDAMENTO · ⬜ PENDENTE

## Fase 0 — Congelamento seguro do legado · 🟡
- ✅ Build determinístico `static/views/` → `build_index.py` → `index.html`.
- ✅ Teste de round-trip byte-idêntico (`tests/test_index_html_build.py`).
- ⬜ **Documento** "Legacy Web SPA" + checklist de não-remoção (este arquivo é a base).
- ⬜ Guard-rail extra opcional: hook/CI que falhe se `index.html` for editado sem
  o build correspondente (o teste já cobre, mas um aviso de pre-commit ajuda).
- **Rollback:** nenhum (somente documentação/teste).

## Fase 1 — Refatorar `app.py` sem mudar comportamento · 🟡
- ✅ Roteamento já modular (`core/router.py` + 18× `register_routes`).
- ⬜ Extrair, **um por PR**, com teste antes: headers → `core/http_headers.py`;
  health → `core/health.py`; static/fallback → `core/static_files.py`;
  bootstrap-gate → `core/bootstrap_gate.py`; erros → `core/errors.py`;
  `authenticate_login` → `modules/auth/`.
- **Critérios de aceite:** `pytest` verde; `/`, `/index.html`, `/app/`,
  `/health`, `/ready` inalterados; `docker build` ok.
- **Rollback:** cada extração é um PR isolado e revertível; `app.py` mantém o
  comportamento via import do novo `core/*`.

## Fase 2 — Refatorar `app.js` · 🟡
- ✅ ~46% extraído para `static/js/` (core/utils/modules/views) de forma aditiva.
- ⬜ Concluir extração por responsabilidade (session, validações), consolidar a
  duplicidade de `hasPermission`, eliminar duplicação `app.js` ↔ `static/js/views`.
- **Critérios de aceite:** login, navegação e telas principais funcionam;
  `node static/js/test/run-tests.js` verde; sem mudança de `globalThis.*`.
- **Rollback:** padrão aditivo — `app.js` continua autoridade; remover o módulo
  novo restaura o estado anterior.

## Fase 3 — Coexistência Legado + Flutter Web · ✅ **CONCLUÍDA**
- ✅ Dockerfile multi-stage builda o Flutter e copia para `static/app/`.
- ✅ `app.py` serve `/app/` com fallback SPA; `/` permanece no legado.
- ✅ Ambos consomem a mesma API; redirect `/flutter_web`→`/app/`.
- ⬜ **Pendência de robustez:** validar cabeçalhos de cache para assets do Flutter
  (hash no nome) vs `no-cache` do HTML; confirmar CSP cobre `/app/`.

## Fase 4 — Paridade de telas (não "migrar do zero") · 🟡
Como as telas Flutter **já existem**, esta fase é **verificação de paridade**
por domínio, não construção. Para cada tela, produzir um *parity sheet*:

| Campo | Conteúdo |
|---|---|
| Rota legado | ex.: `?view=usuarios` |
| Rota Flutter | ex.: `/users` (`Routes.users`) |
| Endpoints usados | ex.: `GET/POST/PUT/DELETE /api/users`, `GET /api/users/:id` |
| Permissões | ex.: `users:view/create/update/delete` |
| Componentes | tabela, form, modal de exclusão |
| Testes | widget test + integração (Flutter) + teste de API (pytest) |
| Aceite | CRUD completo + RBAC + multiempresa idênticos ao legado |
| Rollback | feature flag por tela / usuário continua no legado |

**Ordem recomendada** (baixo risco → alto, audiência → criticidade):
1. Login · 2. Dashboard · 3. Empresas · 4. Usuários · 5. Funcionários ·
6. EPIs · 7. Estoque · 8. Entregas · 9. Ficha de EPI · 10. Relatórios ·
11. Portal do colaborador · 12. Administração master · 13. Configurações multiempresa.

**Critério de "tela pronta":** parity sheet 100% verde + 1 piloto real em produção
acessando via `/app/` sem fallback ao legado.

## Fase 5 — Cutover de `/` → Flutter Web · ⬜ (próximo grande marco)
- ⬜ Atrás de **feature flag/rollout gradual** (ex.: % de tenants), `/` passa a
  redirecionar para `/app/`.
- ⬜ Manter `/legacy/` servindo o SPA antigo (saída de emergência).
- ⬜ Atualizar testes de `/` (passa a esperar redirect), smoke de `/legacy/`.
- ⬜ Health/Docker inalterados (o legado continua no build).
- **Critérios de aceite:** `/` abre Flutter; `/legacy/` abre legado; operação normal.
- **Rollback:** desligar a flag → `/` volta ao legado **sem deploy**.

## Fase 6 — Descomissionar legado · ⬜ (somente após validação em produção)
- ⬜ Remover, em ordem e com teste de regressão: dependência de `index.html` em
  `/` → `static/views/` → `scripts/build_index.py` → `static/app.js`/`static/js/`
  → testes do legado → ajustes no Dockerfile/health.
- **Critérios de aceite:** nenhum teste/deploy/rota depende do legado; Flutter é
  o frontend único.
- **Rollback:** reverter o PR de remoção (manter por ≥1 ciclo de release antes
  de apagar de fato).

---

# PARTE 4 — Plano de testes

## Backend (pytest — já há suíte ~843 testes)
- Rotas: `GET /` (200 + HTML), `GET /index.html`, `GET /app/` (Flutter shell),
  `GET /app/<rota-inexistente>` (fallback `/app/index.html`), `/flutter_web`→308.
- Health: `/health`, `/health/live`, `/ready`, `/health/ready`.
- Headers de segurança/CSP presentes nas respostas relevantes.
- Auth/permissões/`tenant isolation` (escopo por empresa) — já coberto; manter ao extrair.

## Frontend legado
- `node static/js/test/run-tests.js` (89 testes) — manter verde a cada extração.
- `tests/test_index_html_build.py` — round-trip do `index.html`.
- Smoke manual: login, carregamento de scripts (cache-bust `?v=`), campos
  obrigatórios, modais principais.

## Flutter Web
- `flutter test` (widget + unit dos cubits/`epi_api`) e `integration_test/`.
- Build: `melos run build:web` (já no Dockerfile).
- Por tela: login, navegação, consumo de API, i18n (5 idiomas), responsividade,
  troca de empresa (multiempresa).

## Deploy
- `docker build` local (multi-stage) — não quebrar nenhum estágio.
- Render: `render.yaml` (env docker, `Dockerfile`), variáveis de ambiente, assets
  estáticos (`static/app/`), cache, fallback SPA.

---

# PARTE 5 — Plano de rollback (por fase)

| Fase | Como reverter | Arquivos críticos | Validação |
|---|---|---|---|
| 0 | Reverter doc/teste | docs, tests | `pytest` |
| 1 | Reverter PR de extração (cada um isolado) | `app.py`, `core/*` | `pytest`, `docker build` |
| 2 | Remover módulo novo (padrão aditivo) | `static/js/*` | run-tests.js, smoke login |
| 3 | (concluída) desabilitar `/app/` no serving | `app.py`, Dockerfile | `/` segue legado |
| 4 | Feature flag por tela → usuário no legado | flag store | parity sheet |
| 5 | **Desligar flag de cutover** (sem deploy) | flag store | `/` volta ao legado |
| 6 | Reverter PR de remoção | Dockerfile, static/* | suíte completa |

**Rollback mínimo obrigatório (invariantes):**
- Se o Flutter falhar, `/` continua no legado.
- Se `/app/` falhar, o legado permanece operacional.
- Nenhuma migração pode impedir o login no sistema legado.

---

# PARTE 6 — Entregáveis e checklist de descomissionamento

**Entregáveis (este documento cobre 1–9; 10 abaixo):**
1. Relatório de diagnóstico — Parte 1.
2. Mapa de dependências do legado — Parte 1.3 + Dockerfile/testes.
3. Plano de refatoração do `app.py` — Parte 2.1 + Fase 1.
4. Plano de refatoração do `app.js` — Parte 1.2 + Fase 2 (+ `spec/10`).
5. Plano de migração do `index.html` — Parte 1.3 (+ `spec/11`, já concluído).
6. Plano de coexistência — Parte 2.3 + Fase 3 (já em produção).
7. Ordem de migração das telas — Fase 4.
8. Plano de testes — Parte 4.
9. Plano de rollback — Parte 5.

**10. Checklist para remover o legado (Fase 6 — não executar agora):**
- [ ] `/` redireciona para `/app/` há ≥1 ciclo de release sem incidentes.
- [ ] `/legacy/` validado como saída de emergência e sem tráfego relevante.
- [ ] Nenhum teste depende de `static/index.html`/`static/views/`/`app.js`.
- [ ] Nenhuma rota do backend serve `index.html` (exceto `/legacy/`, se mantido).
- [ ] Dockerfile não roda mais `build_index.py` (após remover o legado).
- [ ] Health/smoke atualizados para o Flutter como frontend único.
- [ ] Remoções em PRs separados e reversíveis: `index.html` → `views/` →
      `build_index.py` → `app.js`/`static/js/` → testes do legado → Dockerfile.

---

## Próximos passos recomendados (menor risco → maior valor)

1. **Fechar a Fase 0** (este doc + checklist) e validar caches/CSP do `/app/` (Fase 3 residual).
2. **Fase 4 — parity sheets** começando por Login/Dashboard/Empresas/Usuários
   (domínios onde os GET dedicados e correções desta sprint já deram paridade de dados).
3. **Preparar a flag de cutover** (Fase 5) para um rollout gradual e reversível de `/`.
4. **Fase 1** (extrações de `app.py`) em paralelo, como higienização de baixo risco.

> Nenhuma das ações acima remove legado nem altera comportamento sem teste —
> respeitando todas as regras obrigatórias da Etapa 1.
