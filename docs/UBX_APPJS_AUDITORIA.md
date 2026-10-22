# Auditoria estrutural do `static/app.js` — Refatoração UBX (Etapa A)

Data: 2026-10-22 · HEAD auditado: `main@306d72a6` (Corporate) / `main@bd8a60c6` (SaaS).
Complementa o índice operacional [`UBX_MIGRATION_PLAN.md`](UBX_MIGRATION_PLAN.md); não cria um plano paralelo.

Inventário reproduzível com:

```bash
npm ci   # acorn vem com o eslint
node scripts/audit_app_js.js static/app.js --json /tmp/app-js-audit.json
```

## 1. Fatos medidos

| Item | Valor |
|---|---|
| Linhas (antes desta fase) | **20.320** (não 30 mil). Arquivo **byte-idêntico** em Corporate e SaaS |
| Linhas (depois desta fase) | 20.193 |
| Estrutura | um único `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) { … }` envolvendo tudo |
| Declarações de nível superior | 960 → 948 (655 → 643 `function`, 178 `async function`, 99 `const`, 26 `let`, 2 `var`) |
| Instruções de efeito no carregamento | 35 (registros em `globalThis`, IIFEs de módulo, limpezas de storage) |
| Funções com DOM | 425 · com HTTP (`api*`/`fetch`) 128 · lendo/escrevendo `state` 313 · com checagem RBAC 59 · com `try/catch` 183 |
| Endpoints `/api/...` distintos | 119 |
| Exportações explícitas para `globalThis` | 37 (além das implícitas — ver §2) |
| Ciclos de dependência (SCC) | 5 — o maior com 13 funções (bootstrap) |
| Funções puras (sem DOM/HTTP/estado/storage, só dependem de puras) | 155 → 144 |
| Scripts carregados pelo `index.html` | 48 locais + htmx (SRI), todos `defer`, em ordem fixa por `static/views/_scripts.html` |

### Pontos de maior acoplamento (fan-in)

`state` (312 referências de funções), `tr` (171), `refs` (144), `api` (118), `hasPermission` (58),
`reportNonCriticalError` (40), `loadBootstrap` (33), `actorQuery` (32), `esc` (29), `requirePermission` (25).

### Maiores funções (risco de regressão)

`init` 985 linhas / fan-out 227 · `refs` 336 · `openConferenciaModal` 324 · `startDeliveryQrCamera` 201 ·
`finalizeFichaPeriod` 197 · `saveSimpleForm` 167 · `loadBootstrap` 158 · `showView` 133 · `handleLogin` 116.

### Ciclos

1. **Bootstrap (13):** `loadBootstrap ↔ renderAll ↔ retryBootstrap ↔ scheduleBootstrapAutoRetry ↔ setBootstrapDegraded ↔ loadOptionalBootstrapSection ↔ … ↔ INTERACTIVE_TOOLS_MODULES`.
2. **Compras — workflow de PR (5):** `openPrDetail ↔ renderPrStatusActions ↔ updatePrStatus ↔ executePurchaseWorkflowAction ↔ executePrConferenciaAction`.
3. **Estoque — regularização pendente (4):** `loadPendingRegularization ↔ applyPendingRegularizationFilter ↔ updatePendingRegularizationSelection ↔ regularizeSelectedStockLot`.
4. **Compras — funções de compra (4):** `loadPurchaseFunctions ↔ renderPurchaseFunctionControls ↔ …`.
5. **Entregas (3):** `loadDeliveryUnitEpis ↔ refreshDeliveryContext ↔ syncDeliveryOptions`.

Ciclos são extraídos **inteiros** (nunca partidos entre arquivos) ou quebrados por callback/evento num PR próprio.

## 2. Regras de escopo que decidem o que pode sair do arquivo

Este é o achado que mais restringe a extração e precisa guiar todo PR seguinte:

- **`function` dentro do bloco `if` vira global** (Annex B do ECMAScript, modo sloppy). Por isso as
  views chamam `globalThis.<fn>()` e funcionam. Uma função extraída para um script carregado **antes**
  do `app.js` continua visível com o mesmo nome — o contrato não muda.
- **`const`/`let` dentro do bloco NÃO são globais.** `state`, `refs`, `ROLE_PERMISSIONS`, `VIEW_PERMISSIONS`
  etc. só existem dentro do `app.js`. Função que lê uma dessas constantes **não pode** ser movida
  sem antes expor a constante por um acessor (`__EPI_APP_STATE__` já faz isso para `state`).
  A auditoria marca isso como dependência; a lista de puras já desconta esses casos.
- `var tr` e `var STORAGE_KEYS` são globais (var no topo do script).
- Como o `app.js` carrega **depois** de `static/js/**`, uma função com o mesmo nome no `app.js`
  **sobrescreve** a do módulo. Logo, módulo com nome repetido não é "extração": é código morto
  ou divergente. Achados (§4).

## 3. Mapa de domínios (inferido por nome; detalhado no JSON da auditoria)

| Domínio | Declarações | Linhas | Com HTTP | Com DOM | Puras |
|---|---:|---:|---:|---:|---:|
| shared (utilitários, UI genérica) | 238 | 4.700 | 25 | 68 | 96 |
| estoque | 87 | 1.726 | 18 | 52 | 14 |
| navegação/views | 72 | 1.623 | 3 | 43 | 11 |
| empresas/unidades/CNPJ/comercial | 131 | 1.474 | 22 | 66 | 34 |
| entregas/QR/assinatura | 66 | 1.285 | 6 | 42 | 13 |
| configuração/flags/visibilidade | 59 | 1.047 | 3 | 25 | 15 |
| colaboradores/terceirizados | 62 | 935 | 11 | 32 | 13 |
| compras/fornecedores | 56 | 889 | 13 | 23 | 24 |
| auth/sessão/bootstrap | 48 | 873 | 5 | 15 | 14 |
| migração de dados | 26 | 569 | 6 | 14 | 3 |
| EPIs | 34 | 517 | 3 | 15 | 8 |
| fichas/comprovantes | 15 | 365 | 4 | 9 | 3 |
| relatórios/dashboard | 17 | 305 | 4 | 8 | 5 |
| permissões/RBAC (fallback visual) | 25 | 262 | 1 | 2 | 14 |
| usuários | 17 | 233 | 3 | 8 | 2 |
| feedback/avaliações, biblioteca, portal, i18n | 7 | 86 | 1 | 3 | 3 |

Funcionalidades reais não citadas no pedido original e presentes no arquivo: Comercial/licenciamento
de empresas, Joint Venture de unidades (`activeJoinventureToken`), arquivamento de entidades
(`ARCHIVAL_ENTITIES`), personalização de visibilidade de módulos por papel, preferências por
dispositivo, HUD de performance (`ux_perf_debug`, só master_admin), QR de entrega com câmera,
conferência de recebimento com captura de lote, avaliações/sugestões de EPI e EPI em teste (`ppe_test:*`).

**Segurança:** `ROLE_PERMISSIONS`/`VIEW_PERMISSIONS` no cliente são **fallback de bootstrap**
(comentado no próprio código como espelho de `core/permissions.py`). A autorização efetiva, o escopo
de tenant (`company_id` aparece 244 vezes; `actorQuery` 42) e a validação de token são do backend.
Nenhuma extração pode mover decisão de autorização para o cliente nem remover o envio do escopo.

## 4. Duplicações e código aparentemente morto

| Achado | Situação |
|---|---|
| `isDebugModeEnabled`, `debugLog`, `reportNonCriticalError`, `ensureModuleBound` idênticos em `utils/debug.js` e `app.js` | **Resolvido nesta fase** (cópias do `app.js` removidas; equivalência provada) |
| `safeStorageRead/Write/Remove`, `safeJsonParse` em `utils/storage.js` **divergem** do `app.js` (fallback `'null'` × `null`, escrita de `null`) | Mantido. O `app.js` vence em runtime; unificar muda comportamento — exige decisão |
| Helpers de perf (`markRender*`, `queueStorageWrite`, …) em `utils/perf.js` e `app.js` | Mantido; comparar corpo a corpo num PR próprio |
| `formatCnpj` (L3184) × `formatCNPJ` (L17624); `formatCurrency` × `fmtBrl` | Candidatos a unificação em `shared/` — conferir formato antes |
| Wrappers locais `api` em 6 views | Já registrado como gate P0 no plano UBX |
| 53 funções sem chamador interno nem export explícito: 35 usadas por outros scripts; **18 sem nenhuma referência estática** (`loadScript`, `canManageUsers`, `canManageEpi`, `canViewReports`, `accessibleViews`, `renderUsersSummary`, `companyUsageText`, `copyUserAccessMessage`, `setTemporaryPassword`, `generateAndCopyTemporaryPassword`, `buildDeliveryRow`, `deleteRegistryEntity`, `preencherCampoPorQr`, `_workflowReasonOptions`, `openEditSupplierModal`, `poStatusLabel`, `checkSupplierAuthorized`, `loadUnitLinks`) | **Não removidas.** São globais (Annex B) e podem ser chamadas por console, Flutter WebView ou nome dinâmico. Remover só com evidência de runtime |

## 5. Arquitetura UBX adotada (sobre o layout existente)

Não há `web/`: o SPA vive em `static/` e já tem `static/js/{core,utils,modules,views}`. A camada UBX é
encaixada **dentro** de `static/js/modules/<domínio>/`, sem criar pastas vazias:

```
static/js/modules/<domínio>/
  ui/            render, eventos, formulários           (≈ purchases.view/events do plano)
  business/      regras, transformações, orquestração   (≈ purchases.state/controller)
  integrations/  endpoints via api-client canônico      (≈ purchases.api)
```

Dependência permitida: `ui → business → integrations`. `business` sem DOM, HTTP, storage ou
`__EPI_APP_STATE__` (entrada por parâmetro); `integrations` sem DOM. Sem bundler, sem ES Modules:
os scripts continuam clássicos com `defer` (compatível com o CSP atual, o cache-buster por hash e
os testes estruturais), publicando o contrato legado em `globalThis` mais um namespace congelado.

## 6. Ordem de extração proposta

1. **Feito:** `modules/purchases/business/purchase-import-matching.js` (8 funções puras, sem
   chamadores internos, consumidas só por `views/purchases.js`) + deduplicação de `utils/debug.js`.
2. Gate HTTP do plano UBX: unificar os wrappers `api` locais das views no `api-client.js`.
3. Puras de formatação/rótulos que não leem `const` do bloco (`digitsOnly`, `formatCnpj`,
   `formatCurrency`, `parseCsvList`, `normalizeSearchText`, …) → `modules/shared/business` ou
   `utils/`, unificando duplicatas com prova de equivalência.
4. Compras restante (Fase 2 do plano), quebrando o ciclo de workflow de PR inteiro.
5. Entregas, Estoque, Relatórios, Colaboradores, Dashboard (ordem do plano), um por PR.
6. Por último: bootstrap/`init`/`refs` (ciclo de 13) e o fallback de RBAC.

Domínios em desenvolvimento paralelo devem ser reavaliados no início de cada PR
(`git log origin/main -- static/app.js` e PRs abertos). Em 2026-10-22 não havia PR aberto em nenhum
dos dois repositórios; as branches `codex/mig-data-fix-v1-*` e `codex/stock-*` já estão em `main`.
**Migração de Dados fica por último entre os domínios** (Fase 3 recém-integrada, ainda em homologação).

## 7. Guarda contra crescimento do monólito

`static/js/test/app-js-boundary.js` (roda no job *Frontend Tests* e em `tests/test_app_js_ubx_boundary.py`)
reprova: declaração de nível superior nova no `app.js`; endpoint `/api/` novo no `app.js`; função
extraída que volta ao `app.js`; módulo extraído não carregado antes do `app.js`; `business` usando
DOM/HTTP/storage/estado global; `integrations` usando DOM. O baseline
(`static/js/test/app-js-baseline.json`) é uma catraca: só diminui (`--update` remove, nunca adiciona).

## 8. Registro formal: defeitos preexistentes encontrados na validação (2026-10-22)

Teste funcional da importação de cotação (Compras → Requisição → importar arquivo) no Chromium,
com backend real e só os endpoints da requisição/cotação interceptados, **idêntico em `main` e na
UBX-V1** (5 cenários: fluxo real, parse HTTP 500, arquivo sem linhas, salvar HTTP 400, detalhe
exposto). A refatoração não altera o comportamento; o comportamento de `main` é que tem defeitos:

| Sev. | Defeito (preexistente em `main`) | Evidência | Tratamento |
|---|---|---|---|
| P1 | `views/purchases.js` lê `globalThis._currentPrDetail`, mas no `app.js` é `let` de bloco fora da ponte de acessores: a conciliação recebe lista vazia e "Salvar Preços"/"Criar PO a partir do arquivo" respondem sempre "Nenhum item do CSV foi associado" | navegador: nenhum payload enviado; com o detalhe exposto, 3 itens associados | PR separado `claude/compras-importacao-cotacao-falhas-silenciosas` (epi-controle#1045 / epi-controle-app#418) |
| P2 | Chamadas `globalThis._parsePurchase*?.(…) ?? 0` / `_matchPurchaseImportRows?.(…) \|\| []`: se o script das regras não carregar, a prévia mostra R$ 0,00 e quantidade 1 sem aviso | navegador com o módulo bloqueado | mesmo PR separado: erro explícito no painel, nada enviado |
| P3 | A prévia calcula a quantidade sem o fallback da quantidade requisitada (linha sem `qtd` mostra 1; o salvamento usa a requisitada) | navegador: prévia 1, payload 2 | apenas registrado — regra de exibição, decisão de produto |

Os PRs UBX-V1 não foram ampliados para corrigir esses itens.

## 9. Coordenação com os PRs de estoque (epi-controle#1043 / epi-controle-app#416)

Arquivos compartilhados: `static/app.js`, `static/index.html`, `static/views/_scripts.html`,
`static/js/test/run-tests.js` e os dígitos F4/F5b. Mesclagem simulada (worktree descartável, sem
tocar a branch de estoque): `app.js`, `_scripts.html` e `run-tests.js` mesclam sem conflito; os
conflitos são só em artefatos gerados (`index.html` → `build_index.py build`; dígitos → recálculo
pelo próprio teste). Com os dois integrados, 468 testes JS passam, mas **a guarda UBX reprova**
o que o PR de estoque adiciona ao monólito: `loadStockPhysicalRecords`, `openStockPhysicalDialog`,
`/api/stock/dispositions` e `/api/stock/incomplete-items`.

É exatamente o que a guarda existe para sinalizar; a decisão de ordem é humana:

- **Estoque primeiro:** a branch UBX incorpora `main` e regenera o baseline — as quatro entradas
  passam a fazer parte do estado inicial congelado (o baseline registra `main` no momento em que a
  guarda entra).
- **UBX primeiro:** o PR de estoque move as duas funções para `static/js/modules/stock/{ui,integrations}/`
  (ou um humano decide explicitamente aceitá-las no baseline daquele PR).

Nenhuma alteração foi feita nas branches de estoque.
