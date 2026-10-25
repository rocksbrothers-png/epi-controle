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

**Decisão aplicada (2026-10-22):** o estoque entrou primeiro (epi-controle#1043 e
epi-controle-app#416 integrados em `main`). A branch UBX incorporou `main` por merge (sem rebase)
e o baseline da guarda passou a incluir as quatro entradas acima, que já estavam em `main` quando a
guarda foi introduzida. Daqui em diante a catraca vale para elas também: extraí-las para
`modules/stock/` é a próxima oportunidade natural; adicionar outras ao `app.js` reprova.

## 10. UBX-V2 (2026-10-25) — auditoria de integração e primeira extração

### 10.1 Base auditada

| Repositório | `main` auditada |
|---|---|
| Corporate (`rocksbrothers-png/epi-controle`) | `1bd22272d0ffae66e861a7a633dd334d46162453` |
| SaaS (`rocksbrothers-png/epi-controle-app`) | `d3e92dda185631b1c070b7ab0b7e70e8be8f2d8c` |

Integrados nas duas `main` (confirmado pelo histórico): estoque bloqueado/destinação (#1043/#416),
UBX-V1 (#1044/#417), associação de cotações (#1045/#418), integridade de PO (#1046/#419),
CI Flutter/Melos (#1047/#420), migração de seis categorias e rollback com estoque reconciliado
(#1048/#421, Fases 3–4 do Centro de Migração) e rastreabilidade de linhas assinadas (#1049/#422).
Nenhum PR aberto em nenhum dos dois repositórios no início da UBX-V2. `static/app.js` byte-idêntico
entre Corporate e SaaS.

### 10.2 O que as correções integradas fizeram com o `app.js`

| Verificação | Resultado |
|---|---|
| Linhas | 20.193 (fim da UBX-V1) → **20.281** (+88), só por mudanças dentro de funções existentes |
| Declarações de nível superior / endpoints | **950 / 121 — sem crescimento** (a guarda segurou) |
| Novas globais, listeners ou mudanças de inicialização | Nenhuma nova declaração; o listener de migração ganhou o caso `data-migracao-homologate` dentro de `bindDataMigrationEvents` (já existente) |
| HTTP fora da camada de integração | Melhorou: revert/homologação da migração passou a usar `modules/data-migration/integrations/job-decisions.js` (`__EPI_MIGRATION_DECISIONS__`) |
| Regra de negócio na UI | Migração: filtro de entidades excluídas (`empresas`, `usuarios`, `solicitacoes`) no `app.js` — espelho visual de regra que o backend já aplica (#1048). Compras: `esc()` na lista/detalhe de PO e `_parsePoImportFile(file, purchaseRequestId)` (#1045/#1049). Nada movido nesta fase: são fluxos críticos recém-alterados |
| Ciclos / ordem de carga | Mesmos 5 ciclos de funções da §1; módulos UBX carregam antes das views e do `app.js` |
| Duplicação nova | Nenhuma |

### 10.3 Matriz de extração (estado em `main` 1bd22272)

Risco: **B** baixo (puro, sem DOM/HTTP/estado), **M** médio (DOM ou `state`, sem ciclo), **A** alto
(ciclo, HTTP + DOM + RBAC, ou fluxo crítico recém-alterado).

| Ordem | Domínio / conjunto | No `app.js` hoje | Linhas | Dependências | Risco | Testes existentes | Testes necessários |
|---:|---|---|---:|---|:---:|---|---|
| **1 (feito)** | Formatação/leitura de valores (`shared/business/value-format.js`) | 14 funções puras | 81 | nenhuma (só entre si) | B | indiretos (stock-panels mocka `formatCurrency`) | caracterização + diferencial (feitos) |
| 2 | Helpers de id/atributo de DOM (`toSafeId`, `isValidDomId`, `getElementIdAttribute`, `describeFieldNode`, `resolveFormFieldAutocomplete`) | 5 | ≈60 | DOM por parâmetro | B | nenhum | caracterização com nós falsos |
| 3 | Rótulos puros de domínio que só usam `tr` (`employmentTypeLabel`, `allocationTypeLabel`, `contractStatusLabel`, `retentionStatusBadge`, `domainStatusLabel`, `pendingRegularizationGroupLabel`) | 6 | ≈45 | `tr` (global `var`, injetável) | B | parciais | tabela de rótulos por chave |
| 4 | Gate HTTP: wrappers `api` locais das 6 views → `api-client.js` | 6 views | — | `api-client`, `state` | M | `run-tests.js` (api-client) | contrato por view (URL, método, corpo) |
| 5 | Relatórios (`syncReportOptions`, `renderReports`, `loadPendingReportRequests`, …) | 16 | 300 | `state`, `refs`, `api`, RBAC | M | estruturais | runtime da view + RBAC |
| 6 | EPIs (formulário/validade/QR) | 34 | 517 | `state`, `refs`, `api` | M | estruturais | runtime + navegador |
| 7 | Usuários | 17 | 233 | RBAC, `api` | M | estruturais | runtime + RBAC |
| 8 | Colaboradores/terceirizados | 62 | 935 | RBAC, view helpers | M | parity tests | runtime + navegador |
| 9 | Empresas/unidades/CNPJ/comercial | 131 | 1.474 | RBAC, escopo de tenant | A | parciais | tenant + navegador |
| 10 | Entregas/QR | 66 | 1.285 | ciclo de 3, câmera | A | estruturais | navegador (QR) |
| 11 | Compras restante (ciclo de workflow de PR) | 49 | 791 | ciclo de 5, recém-alterado | A | runtime de cotação/lote | estabilizar antes |
| 12 | Estoque (regularização, lotes) | 89 | 1.793 | ciclo de 4, recém-alterado | A | 5 runtimes | estabilizar antes |
| 13 | Migração de dados | 26 | 583 | Fases 3–4 em homologação | A | runtime de decisões | estabilizar antes |
| 14 | Navegação/bootstrap/`init`/`refs`, fallback RBAC | 72 + 48 + 25 | ≈2.750 | ciclo de 13, fan-out 226 | A | bootstrap resilience | por último |

### 10.4 Mapa de dependências entre scripts (namespaces)

Dependências declaradas por namespace `__EPI_*__` (publicado com `globalThis.__EPI_X__ = …`):
apenas `views/dashboard.js → views/dashboard-scope.js` e `views/dashboard.js → views/legal-entity-fields.js`.
Os demais acoplamentos passam por **funções globais** (Annex B) e por três registros compartilhados
por desenho (`__EPI_FRONTEND_HELPERS__`, `__EPI_APP_STATE__`, `__EPI_REFS__`). Consequência: a regra de
ciclos da guarda cobre o contrato por namespace — por isso todo módulo UBX publica um namespace
congelado além dos nomes legados.

### 10.5 Primeira extração da UBX-V2

`static/js/modules/shared/business/value-format.js` — `formatCurrency`, `fmtBrl`, `digitsOnly`,
`formatCnpj`, `formatCNPJ`, `parseMonthsValue`, `parsePositiveInteger`, `parseCsvList`,
`parseCsvNumberList`, `parseOptionalJson`, `normalizeSearchText`, `normalizeHexColor`, `daysUntil`,
`addDaysFromBaseDate` + namespace `__EPI_SHARED_VALUE_FORMAT__`. Carregado antes das views e do
`app.js`. `app.js`: **20.281 → 20.200 linhas**, **950 → 936 declarações**.

Prova de equivalência:
- diferencial fora do repositório (originais fatiadas do `app.js` de `main` × módulo):
  350.000 comparações por fuso em 5 fusos (São Paulo, Noronha, UTC, Tóquio, Kiritimati), 0 divergências;
  a sabotagem de um caractere é detectada;
- caracterização no repositório (`static/js/test/shared-value-format-runtime.js`): tabelas geradas
  a partir das funções originais, relógio fixo para `daysUntil`, ordem de carga e ausência no `app.js`;
- navegador real (backend + PostgreSQL descartável, `main` × branch): valores das 14 funções no
  Chromium, 14 views do master admin, CNPJ de fornecedor, lista/detalhe de PO, detalhe de requisição
  e seletor de fornecedor **idênticos**, mesmos erros de console (400 de seções opcionais e htmx
  bloqueado pelo proxy do sandbox).

Peculiaridades preservadas (mudar qualquer uma é decisão de negócio):
- `formatCnpj` (fallback `''`) × `formatCNPJ` (fallback `'—'`) não são equivalentes; `formatCurrency` e `fmtBrl` são.
- `parseMonthsValue(6.9) === 69` (o ponto é descartado); `formatCurrency('abc') === 'R$ NaN'`.
- **Defeito preexistente:** `addDaysFromBaseDate` usa meia-noite local e `toISOString()` (UTC): em
  fusos a leste de UTC devolve o dia anterior (`'2026-10-22' + 1` → `'2026-10-22'` em Tóquio). Não
  afeta o Brasil. Com dias não numéricos lança `RangeError`. Registrado, não corrigido.

### 10.6 Guarda ampliada

Além das regras da §7: (6) catraca de endpoints na camada UI (`static/js/views/*.js`, semente: 44
endpoints em 12 arquivos); (7) nenhum ciclo novo entre scripts e `business/`/`integrations/` sem
dependência de namespace da camada UI; `business/` não lê globais (entrada por parâmetro);
(8) nenhum arquivo em `modules/` acima de 500 linhas (contra um novo monólito em `shared/`).
Cada regra tem teste de sabotagem em `tests/test_app_js_ubx_boundary.py`.

### 10.7 Pendente para a UBX-V3 (não iniciada)

Itens 2–4 da matriz (helpers de DOM, rótulos com `tr`, gate HTTP das views); depois Relatórios,
EPIs e Usuários. Compras, Estoque e Migração só depois de estabilizados; bootstrap por último.
