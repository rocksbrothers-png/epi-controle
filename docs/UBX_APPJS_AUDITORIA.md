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
| Ciclos / ordem de carga | Mesmos 5 ciclos de funções da §1; módulos UBX carregam antes das views e do `app.js`. Scripts locais no `index.html`: 48 (§1) → 49 com o módulo da UBX-V2 |
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

Dependências declaradas por namespace `__EPI_*__` (publicado com `globalThis.`/`window.`/`self.__EPI_X__ = …`,
em `static/js/**` e nos scripts de nível superior `static/*.js`): **14 arestas, nenhum ciclo** — por
exemplo `views/dashboard.js → views/dashboard-scope.js` e `views/dashboard.js → views/legal-entity-fields.js`.
Os demais acoplamentos passam por **funções globais** (Annex B), invisíveis a esta análise, e por três
registros compartilhados por desenho (`__EPI_FRONTEND_HELPERS__`, `__EPI_APP_STATE__`, `__EPI_REFS__`).
Consequência: a regra de ciclos da guarda cobre o contrato por namespace — por isso todo módulo UBX
publica um namespace congelado além dos nomes legados.

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
  a partir das funções originais (com `undefined`, `0` e `false` preservados), relógio fixo para
  `daysUntil`, ordem de carga e ausência no `app.js`;
- navegador real (backend + PostgreSQL descartável, `main` × branch): valores das 14 funções no
  Chromium, 14 views do master admin, CNPJ de fornecedor, lista/detalhe de PO, detalhe de requisição
  e seletor de fornecedor **idênticos**, mesmos erros de console (400 de seções opcionais e htmx
  bloqueado pelo proxy do sandbox).

Peculiaridades preservadas (mudar qualquer uma é decisão de negócio):
- `formatCnpj` × `formatCNPJ` não são equivalentes: com 14 dígitos ambas formatam; sem isso ambas devolvem
  a entrada como veio (`'123'` → `'123'`), exceto entrada vazia/nula — `''` × `'—'`. `formatCurrency` e
  `fmtBrl` são equivalentes.
- `parseMonthsValue(6.9) === 69` (o ponto é descartado); `formatCurrency('abc') === 'R$ NaN'`.
- **Defeito preexistente:** `addDaysFromBaseDate` usa meia-noite local e `toISOString()` (UTC): em
  fusos a leste de UTC devolve o dia anterior (`'2026-10-22' + 1` → `'2026-10-22'` em Tóquio). Não
  afeta o Brasil. Com dias não numéricos lança `RangeError`. Registrado, não corrigido.

### 10.6 Guarda ampliada

Além das regras da §7:

- (6) catraca de endpoints na camada UI — `static/js/views/`, `modules/<domínio>/ui/` e os scripts de
  UI de nível superior `static/*.js`; template literals contam com a sub-rota (`${id}` → `{}`) e o
  prefixo solto `'/api'` usado para concatenar também é registrado (semente: 69 entradas em 14 arquivos);
- (7) nenhum ciclo novo entre scripts; `business/`/`integrations/` sem dependência de namespace da UI;
  `business/` não lê globais — nem por `globalThis`/`window`/`self` (`.`, `?.`, `[...]`) nem os globais
  do `app.js` usados soltos (`state.`, `refs.`, `tr(`, `hasPermission(`, …) — e não usa HTTP alternativo
  (`XMLHttpRequest`, `sendBeacon`, `EventSource`, `WebSocket`);
- (8) nenhum arquivo em `modules/` acima de 500 linhas (contra um novo monólito em `shared/`).

Cada regra tem teste de sabotagem em `tests/test_app_js_ubx_boundary.py`, inclusive os desvios
apontados pela auditoria independente. **Limite honesto:** a guarda é análise por padrões, não um
analisador de fluxo. Ela barra regressões descuidadas e os idiomas conhecidos; um endpoint montado
em várias variáveis sob um prefixo já registrado no mesmo arquivo, ou uma dependência por função
global (Annex B), ainda passam. A revisão humana continua necessária.

### 10.7 Pendente para a UBX-V3 (executada na §11)

Itens 2–4 da matriz (helpers de DOM, rótulos com `tr`, gate HTTP das views); depois Relatórios,
EPIs e Usuários. Compras, Estoque e Migração só depois de estabilizados; bootstrap por último.

## 11. UBX-V3 (2026-10-26) — seis extrações incrementais

### 11.1 Base e preparação

| Repositório | `main` de partida |
|---|---|
| Corporate (`rocksbrothers-png/epi-controle`) | `8c63ea005cbf732a7bf4fea42dafa389273c4c9f` → rebase sobre `3e6fe8c592c4c738c6bc1b55d8bba2969c52d4b8` |
| SaaS (`rocksbrothers-png/epi-controle-app`) | `102064e9e8b550c5187445a936da33ab2268529f` → rebase sobre `b25147b3a28bca41d6479daf95d7cfeed1b54664` |

Durante a UBX-V3 entraram nas duas `main` dois PRs do Codex: ícone da Biblioteca de Segurança
(epi-controle#1051 / epi-controle-app#424) e navegação do alerta de validade física para os lotes
pendentes (epi-controle#1052 / epi-controle-app#425, `modules/stock/ui/pending-validity-navigation.js`
e dois ajustes em `loadPendingRegularization`). Os commits da UBX-V3 foram rebaseados sobre elas sem
conflito de código — só `index.html` e os digestos F4/F5-B foram regerados pelas ferramentas do repo,
commit a commit —, e foi conferido que o diff da UBX-V3 e o diff do Codex ficaram idênticos (fora
deslocamento de linhas). Nenhuma função tocada pelo Codex saiu do `app.js`.

UBX-V1, associação de cotações e UBX-V2 (epi-controle#1050 / epi-controle-app#423) integrados nas
duas `main`. Nenhum PR aberto no início; nenhuma branch recente fora de `main` alterava o `app.js` (os dois PRs do Codex abaixo entraram depois e foram integrados por rebase).
`static/app.js` byte-idêntico entre os dois repositórios (20.200 linhas em 8c63ea00; 20.205 após os PRs do Codex). As correções recentes de
Estoque, Compras, Migração e Biblioteca de Segurança não foram tocadas (`views/procurement.js`,
`views/safety-library.js`, `views/stock-*.js` e os módulos de migração ficaram fora do diff).

### 11.2 Método (igual em todas as etapas)

1. Funções originais fatiadas por nome do `app.js` **congelado no commit da etapa anterior**;
2. o MESMO roteiro roda sobre as originais (gera as tabelas esperadas) e sobre os módulos, em `vm`
   com DOM falso e espiões — saída, DOM, chamadas (com argumentos e ordem), requisições e erros;
3. sabotagem conferida em cada etapa (uma mudança de ordem, chave, texto ou corpo faz o teste falhar);
4. navegador real: backend + PostgreSQL descartável, `main` × etapa, master admin e admin de empresa
   (pt-BR e en-GB real via `EpiI18n.setLang`) — ids/autocomplete de campos, textos das views,
   requisições (método, caminho, query, `Authorization`, `Content-Type`) e erros de console, mais
   um fluxo de interação por domínio. **0 diferenças em todas as etapas.**

### 11.3 Etapas

| Etapa | Módulos | Saiu do `app.js` | `app.js` (linhas) | Declarações / endpoints |
|---|---|---|---:|---:|
| início (`3e6fe8c5`) | — | — | 20.205 | 936 / 121 |
| 1 — helpers de DOM | `shared/ui/form-field-identity.js` | `isViewActive`, `resolveFormFieldAutocomplete`, `describeFieldNode`, `getElementIdAttribute`, `isValidDomId`, `toSafeId`, `setElementIdAttribute`, `normalizeInvalidDomIds`, `ensureFormFieldAttributes`, `auditFormFieldIssues`, `setupFormFieldHardening` | 19.929 | 925 / 121 |
| 2 — rótulos com `tr` | `shared/ui/domain-labels.js` | `unitTypeLabel`, `formatCompanyAvailabilityText`, `employmentTypeLabel`, `allocationTypeLabel`, `outsourcedEmployeeLinkLabel`, `epiProtectionLabel`, `epiMeasureLabel` | 19.876 | 918 / 121 |
| 3 — HTTP das views | `api`, `apiOptional`, `apiWithBootstrapRetry` → `modules/api-client.js`; `api` local de 5 views delega a `globalThis.api` | os 3 delegadores | 19.865 | 915 / 121 |
| 4 — Relatórios | `reports/{business/report-filters, integrations/reports-api, ui/reports-view}.js` | filtros, render, arquivo de fichas, exportação PDF | 19.675 | 908 / 118 |
| 5 — EPIs | `shared/ui/file-data-url.js`, `epis/{business/epi-form-values, ui/epi-registration}.js` | foto, escopo de unidades, JV, edição, preparo dos valores, reset, linha | 19.420 | 892 / 118 |
| 6 — Usuários | `users/{business/user-form, integrations/users-api, ui/users-view}.js` | filtros, resumo, feedback, acesso de empresa, botões por linha, edição, reset, mudança de acesso | **19.227** | **878 / 117** |

Total: **−978 linhas** (−4,8%), **−58 declarações**, **−4 endpoints** no `app.js`; 11 módulos novos
(1.477 linhas, maior com 332). Testes de caracterização: `shared-form-field-identity-runtime.js`,
`shared-domain-labels-runtime.js`, `api-client-legacy-runtime.js`, `reports-view-runtime.js`,
`epis-registration-runtime.js`, `users-view-runtime.js` (523 → 570 testes JS sobre a `main` atual).

Etapa 6, fronteiras: `saveUser` e `deleteUser` ficam no `app.js` como orquestradores finos — o
primeiro chama `__EPI_USERS_BUSINESS__.prepareUserFormValues` (mesmas validações, ordem e mensagens)
passando o `ROLE_LABELS` **do app.js**, e ambos enviam pela integração. As regras `can*` (fallback
visual de RBAC) continuam no `app.js` e decidem os botões como antes; a autorização efetiva segue no
backend, sem nenhuma mudança.

### 11.4 Acoplamento — caiu ou só mudou de lugar?

Medido no `app.js` (`3e6fe8c5` → branch; os PRs do Codex não alteram estas contagens):

| Medida | Antes | Depois |
|---|---:|---:|
| chamadas `api(`/`apiOptional(`/`apiWithBootstrapRetry(` | 171 | 163 |
| `state.` | 992 | 922 |
| `refs.` | 1.064 | 1.026 |
| `document.` | 1.251 | 1.214 |
| `innerHTML` | 244 | 226 |
| `tr(` | 640 | 569 |
| `fetch(` cru nas views/UI (guarda, regra 9) | 9 | 4 |

O que **realmente** desacoplou:
- HTTP de Relatórios e Usuários saiu da UI para `integrations/` (sem DOM, pela guarda); as 5 views
  deixaram de ter `fetch` próprio e passam pelo cliente único;
- regras de cliente (filtros de relatório, valores do EPI, validação do usuário, corpo do PUT de
  acesso) estão em `business/` puro — sem DOM, HTTP, storage nem leitura de globais (guarda);
- cada módulo publica namespace congelado; o grafo de namespaces segue **sem ciclo**.

O que **só mudou de lugar** (dito com honestidade): as UIs extraídas ainda leem `state`/`refs` do
`app.js` (os mesmos objetos, por `__EPI_APP_STATE__`/`__EPI_REFS__`) e chamam funções globais dele
— 11 em `reports-view.js`, 19 em `epi-registration.js`, 17 em `users-view.js` (declaradas no
cabeçalho `/* global */` de cada módulo), cerca de 47 chamadas. No sentido inverso, o `app.js` faz
cerca de 84 chamadas soltas aos nomes movidos. Ou seja: `app.js` ↔ `reports-view`/`epi-registration`/
`users-view` são **ciclos reais por função global** (Annex B), que o grafo de namespaces ("0 ciclos")
não enxerga. Efeito colateral: as chamadas internas do `app.js` a esses nomes (e às 163 de `api(`)
passaram de ligação de bloco para busca em `globalThis` na hora da chamada — um script que
reatribuísse um deles interceptaria o próprio `app.js`. Para fixar isso, o teste
`extracted-globals-ownership-runtime.js` falha se qualquer arquivo de `static/` fora do módulo dono
publicar um nome extraído (exceção registrada: os três de `utils/dom.js`, achado 1, com a ordem de
carga verificada). Reduzi-lo exige mover `confirmDestructive`, as regras `can*` e o
bootstrap/`renderTables` — itens de risco alto da matriz (§10.3).

### 11.5 Guarda

Regra 9 nova: catraca de `fetch` cru na camada UI (`uiRawFetch`, semente 9 → 4 após a Etapa 3).
`--update` só remove. Sabotagem em `tests/test_app_js_ubx_boundary.py`. Os limites da §10.6 continuam,
e a auditoria independente mostrou os desta regra: não conta `fetch?.(…)`, `globalThis['fetch'](…)`,
`fetch.call(…)`, `(0, fetch)(…)`, alias (`const f = fetch`), `XMLHttpRequest`/`sendBeacon` na UI,
um `fetch` na mesma linha depois de uma string com `//`, nem arquivos fora de `views/`,
`modules/*/ui` e `static/*.js`. Ela barra o idioma comum; a revisão humana segue necessária.

### 11.6 Achados registrados (nenhum corrigido — mudar é decisão de negócio)

1. `getElementIdAttribute` diverge entre `js/utils/dom.js` (lê `node.id`) e o `app.js` (lê o
   atributo). O módulo da Etapa 1 carrega **depois** de `utils/dom.js` e mantém a versão do `app.js`,
   que era a vigente em tempo de execução.
2. `user-email` recebe `autocomplete="username"` (regra preexistente de `resolveFormFieldAutocomplete`).
3. `api-client`: headers passados pelo chamador **substituem** os montados — quem passa `headers`
   perde `Authorization`/`Content-Type`. Hoje só o portal do colaborador passa `{ headers: {} }`.
   Fixado em teste; corrigir muda comportamento.
4. `views/procurement.js` tem `fetch` próprio e **não** desembrulha `{ ok, data }`: unificar mudaria o
   contrato da tela. Proposta para decisão separada. `views/safety-library.js` mantém um `fetch` de
   contingência (Biblioteca de Segurança, fora do escopo).
5. `ROLE_LABELS` do `app.js` ≠ o de `core/constants.js` (este tem `certification_readonly`). A
   validação "Perfil inválido." do salvar usa o do `app.js`; a UI usa o de `core` só para os 8 rótulos
   do filtro, iguais nos dois. Ambos fixados em teste.
6. `confirmDestructive` é `async function` de bloco (não global) — por isso `deleteUser` ficou no
   `app.js`. Movê-lo para `shared/ui` é o próximo passo natural.
7. Validação da Etapa 6 no navegador: o salvar de usuário mostra "Campo obrigatório: employee_id_code"
   para perfis que não exigem colaborador — comportamento idêntico em `main` (validação HTML/genérica
   preexistente), registrado para triagem.
8. Continuam valendo: `addDaysFromBaseDate` em fusos a leste de UTC (§10.5) e os limites da guarda.
9. Fallback removido das views (Etapa 3): em `main`, o `api` local de `fichas`/`profile`/`purchases`/
   `employee-portal` caía num `fetch` **sem JWT** se `globalThis.api` ainda não existisse; agora vai
   sempre ao cliente autenticado (carregado antes). Caso-limite: se `api-client.js` não carregar, essas
   quatro lançam `TypeError` síncrono em vez de devolver promessa rejeitada. No SaaS, o
   `views/feedback-detail.js` tinha o mesmo wrapper com fallback — removido na Etapa 3 do SaaS
   (passa a chamar `globalThis.apiFetch`, como no Corporate; `api` só delegava a `apiFetch`), e o
   arquivo ficou byte-idêntico ao do Corporate.
10. CodeQL no PR (código movido aparece como novo): **corrigido**, sem efeito em valor legítimo —
    `renderEpiPhotoPreview` passou a escapar a foto no atributo `src` (XSS armazenado se
    `epi_photo_data` tivesse aspas; data URL base64 sai idêntica, teste em
    `epis-registration-runtime.js`), e o par `nearestFormId`/`formId` sobrescrito de
    `describeFieldNode` foi removido (valia o segundo; mesma ordem de chaves e mesmo objeto).

### 11.8 Auditoria independente (adversarial)

Feita por um agente separado, só leitura, sobre a série completa. **Nenhum P0/P1.** Conferido: as
58 funções removidas casadas por AST com as versões dos módulos (53 idênticas; 5 mudadas de propósito
— `collectReportFilters`, `renderReports`, `loadArchiveReports`, `exportReportPdf`, `updateUserAccess`
— revisadas à mão: ordem e mensagens de validação, URLs, query, ordem das chaves do JSON, escopo do
`try` e caminhos de 403 iguais); o resto do `app.js` idêntico fora `saveUser`, `deleteUser` e a lista
do `Object.assign`; resolução de cada nome antes de bloco; nomes que viraram globais sem colisão;
tabelas de caracterização reproduzidas a partir das originais (0 divergências); literais e U+00AD;
baseline só encolheu; Estoque, Compras, Migração e Biblioteca intocados. Os P2/P3 apontados
(base defasada, digestos de paridade, limites da regra 9, ligação por `globalThis`, fallback das
views, ciclo por função global) foram tratados acima: rebase, mesmos commits no SaaS, registro dos
limites, teste de dono único e a correção da §11.4.

### 11.7 Próximos módulos recomendados

1. `confirmDestructive` + diálogos → `shared/ui` (destrava `deleteUser` e outras remoções);
2. Colaboradores/terceirizados (item 8 da §10.3), com a mesma caracterização;
3. regras `can*` → `modules/auth/business` (puras, por parâmetro), sem tocar o backend;
4. Empresas/Unidades/CNPJ (risco alto: escopo de tenant) só com teste de isolamento por empresa;
5. Compras, Estoque e Migração só depois de estabilizados; bootstrap/`init`/navegação por último.

## 12. UBX-V4 (2026-10-26) — diálogos, Colaboradores/Terceirizados e regras `can*`

### 12.1 Base e preparação

| Repositório | `main` de partida |
|---|---|
| Corporate (`rocksbrothers-png/epi-controle`) | `7694bef196aaf1c035d11a400c080286588a301e` |
| SaaS (`rocksbrothers-png/epi-controle-app`) | `053f0749a2aafe26315739ced56cf1f0d70433d3` |

UBX-V3 integrada nas duas `main` (epi-controle#1053 / epi-controle-app#426); `app.js` byte-idêntico
(19.227 linhas, 878 declarações, 117 endpoints). Depois dela só entraram atualizações de dependências
(dependabot). Internacionalização: 1.751 chaves alinhadas nos cinco idiomas (pt-BR, en-GB, es-ES,
fr-FR, nb-NO), idênticas entre Corporate e SaaS; as branches de tradução existentes são de junho a
agosto e estão paradas — nenhum trabalho de i18n paralelo a coordenar. Nenhuma branch do Codex tocada.

### 12.2 Etapas

| Etapa | Módulos | `app.js` (linhas) | Declarações / endpoints |
|---|---|---:|---:|
| início (`7694bef1`) | — | 19.227 | 878 / 117 |
| A — diálogos | `shared/ui/dialogs.js` (`confirmDestructive`, `getFocusableElements`, `openModal`, `closeModal`, `bindModalKeyboard` + WeakMaps privados); `deleteUser` → `users/ui/users-view.js` | 19.159 | 870 / 117 |
| B1 — Colaboradores | `employees/{business/employee-rules, integrations/employees-api, ui/employees-view}.js` | 18.928 | 850 / 117 |
| B2 — Terceirizados e Prestadores | `outsourced/{integrations/outsourced-api, ui/outsourced-companies-view, ui/outsourced-company-requests-view, ui/outsourced-employees-view}.js` | 18.185 | 814 / 112 |
| C — regras `can*` | `auth/{business/access-rules, ui/access-context}.js`; `canAccessView` vira adaptador | **18.106** | **798 / 112** |

Total: **−1.121 linhas** (−5,8%), **−80 declarações**, **−5 endpoints**; 13 módulos novos (1.669 linhas, maior
com 443). Ficaram no `app.js`, de propósito: `archiveOutsourcedEmployee` (depende de `archiveEntityRecord`,
`async` de bloco), `canAccessView` (adaptador: os mapas `VIEW_*` são usados também por `showView`/menus),
`canViewConfiguration` e `canManageStockConfig` (só delegam), `hasPermission` (central; não alterado).

### 12.3 Validação

- Caracterização gerada das funções ORIGINAIS de cada etapa (fatiadas do `app.js` do commit anterior,
  dentro de um bloco com as constantes de bloco de que dependem): diálogos 21 cenários, Colaboradores 42,
  Terceirizados 87 (com e sem os módulos de regras puras reais). Sabotagem conferida em todas; cada
  sabotagem não detectada virou cenário (perfil Gestor de EPI no escopo por Unidade; valores de
  visibilidade "falsos" não booleanos; permissões que só vêm do backend, como `employees:transfer`).
- **RBAC antes × depois:** `static/js/test/access-rules-runtime.js` compara as decisões das regras
  originais (trechos congelados em `static/js/test/fixtures/app-before-ubx-v4-c.js.txt`) com as novas
  numa matriz de 11 atores (9 perfis, perfil desconhecido, sem usuário) × 5 conjuntos de permissões
  (perfil, vazia → fallback real de `ROLE_PERMISSIONS`, só leitura, arbitrária, todas) × 30 alvos ×
  todas as views × 7 estados de visibilidade de módulos: **23.320 decisões (4.488 concessões,
  18.832 negações), 0 divergências**. Nenhuma permissão ampliada; a matriz RBAC do backend não foi tocada.
- Navegador real (backend + PostgreSQL descartável, antes × depois de cada etapa): confirmação
  (Escape/Enter/cancelar/OK), modal real (foco, Tab, Escape), remoção de usuário, cadastro/edição/lote/CSV
  de Colaboradores, cadastro/edição/promoção de empresa terceirizada, colaborador terceirizado e headcount,
  menus por perfil e botões por linha — idênticos. A única variação dos smokes gerais é a corrida conhecida
  do pré-carregamento de `/api/i18n/en-GB`, que oscila também entre duas execuções do mesmo lado.
- i18n: nenhum texto novo — todos os literais dos módulos da V4 já existiam no `app.js` (verificado por
  tokenização); chaves e fallbacks inalterados; CA/CE/CPF intocados.

### 12.4 Acoplamento

| Medida no `app.js` | `7694bef1` | branch |
|---|---:|---:|
| chamadas `api(`/`apiOptional(`/`apiWithBootstrapRetry(` | 163 | 152 |
| `hasPermission(` | 101 | 76 |
| `state.` | 922 | 839 |
| `refs.` | 1.026 | 987 |
| `document.` | 1.214 | 1.183 |
| `innerHTML` | 226 | 213 |
| `tr(` | 569 | 524 |

Desacoplou de verdade: as regras de acesso da interface viraram negócio puro testável sem DOM nem estado
(contexto explícito `{ actor, permissions }`); o HTTP de Colaboradores e Terceirizados está em
`integrations/`; a seleção em lote tem um dono (o módulo) e o `app.js` a lê pelo namespace. Continua
acoplado (dito com honestidade): as UIs extraídas ainda chamam funções globais do `app.js`
(`hasPermission`, `requirePermission`, `showView`, `setFormSubmitLabel`, …) e o `app.js` chama as delas —
ciclo por função global, invisível ao grafo de namespaces (§11.4). O grafo de namespaces segue sem ciclos.

### 12.5 Achados (registrados; nenhum corrigido — mudar é decisão de negócio)

1. **`toggleEmployeeUnitLink` chama `loadEmployees()`, que não existe** em lugar nenhum: depois do POST
   bem-sucedido o `catch` mostra "loadEmployees is not defined" e a lista não re-renderiza. Preservado
   e fixado em teste; correção sugerida: chamar `loadBootstrap()` (ou o loader real) — decisão separada.
2. `canManageUsers`, `canManageEpi` e `canViewReports` não têm chamador no frontend (código morto
   preservado como global).
3. `globalThis.hasPermission` é definido por `modules/permissions-rt.js` com outra assinatura
   (`(roleOrPermsList, permission)`) e sobrescrito pelo `hasPermission(permission)` do `app.js` no carregamento;
   o adaptador de acesso não depende de nenhum dos dois (usa a lista ativa direto).
4. Depois de cadastrar uma empresa terceirizada a lista não recarrega até reabrir a tela (comportamento
   igual em `main`, observado no smoke).
5. No smoke de Colaboradores, após "Editar" o snapshot do formulário veio sem os valores (igual em `main`);
   a triar — pode ser o reset de navegação de `showView` (F5-B) atuando depois da edição.
6. Continuam valendo os achados da §11.6.

### 12.6 Próximos candidatos (UBX-V5, não iniciada — requer autorização)

1. Corrigir/decidir os achados 1, 4 e 5 acima (são comportamento, fora de refatoração pura);
2. `archiveEntityRecord`/arquivamento genérico (`ARCHIVAL_ENTITIES`) → módulo próprio (destrava
   `archiveOutsourcedEmployee`);
3. Empresas/Unidades/CNPJ (risco alto: escopo de tenant), com o mesmo teste de matriz por empresa;
4. mapas `VIEW_*` + `showView`/menus (navegação) — último bloco antes do bootstrap.

