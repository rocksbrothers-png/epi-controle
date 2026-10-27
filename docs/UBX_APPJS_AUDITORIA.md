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
| 53 funções sem chamador interno nem export explícito: 35 usadas por outros scripts; **18 sem nenhuma referência estática** (`loadScript`, `canManageUsers`, `canManageEpi`, `canViewReports`, `accessibleViews`, `renderUsersSummary`, `companyUsageText`, `copyUserAccessMessage`, `setTemporaryPassword`, `generateAndCopyTemporaryPassword`, `buildDeliveryRow`, `deleteRegistryEntity` (era `async` de bloco, nunca global; removida na UBX-V5 Etapa 1, §13), `preencherCampoPorQr`, `_workflowReasonOptions`, `openEditSupplierModal`, `poStatusLabel`, `checkSupplierAuthorized`, `loadUnitLinks`) | **Não removidas.** São globais (Annex B) e podem ser chamadas por console, Flutter WebView ou nome dinâmico. Remover só com evidência de runtime |

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

Total: **−1.121 linhas** (−5,8%), **−80 declarações**, **−5 endpoints**; 10 módulos novos (1.669 linhas, maior
com 443). Ficaram no `app.js`, de propósito: `archiveOutsourcedEmployee` (depende de `archiveEntityRecord`,
`async` de bloco), `canAccessView` (adaptador: os mapas `VIEW_*` são usados também por `showView`/menus),
`canViewConfiguration` e `canManageStockConfig` (só delegam), `hasPermission` (central; não alterado).
`hasConfigurationAccess` virou adaptador da mesma regra pura usada por `canAccessView('configuracao')` —
fonte única (achado da auditoria; coberto pela matriz RBAC).

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
ciclo por função global, invisível ao grafo de namespaces (§11.4). O grafo de namespaces segue sem ciclos,
mas também há dependências mútuas por função global ENTRE módulos: a UI de empresas terceirizadas chama a
de colaboradores terceirizados (`syncOutsourcedEmployeeCompanySelect`, `renderOutsourcedEmployees`) e
vice-versa (`outsourcedCompaniesViewHelpers`), e a UI de Colaboradores chama `isContractedVinculoJs`.

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

### 12.6 Auditoria independente (adversarial)

Agente separado, só leitura, sobre `61593f2a`. **Nenhum P0/P1.** Conferido: o resto do `app.js` igual token a
token (834 × 834 instruções; só `canAccessView` e a linha de `employeesBulk` mudam); nenhum identificador
solto; nenhuma leitura de nome de bloco do `app.js` nos módulos; sem colisão de nomes; ordem de carga do lote;
RBAC equivalente — fixture fiel ao original e fuzz diferencial próprio de 680.000 chamadas (usuário nulo,
permissão como string com espaços, visibilidade não booleana, views `constructor`/`__proto__`/`''`), 0
diferenças; contratos HTTP idênticos (inclusive o que fica dentro/fora do `try`); diálogos equivalentes;
tabelas de caracterização regeneradas das originais com 0 diferenças; baseline da guarda só encolheu;
métricas da §12.4 reproduzidas. P2/P3 tratados: regra de configuração unificada (acima); dependências
mútuas entre módulos registradas (§12.4); contagem de módulos e comentário de `employees-view.js` corrigidos.
Registrados como risco residual:

- os módulos chamam `hasPermission` solto, que só é a versão do `app.js` porque ela sobrescreve (Annex B) o
  `globalThis.hasPermission(roleOrPermsList, permission)` de `modules/permissions-rt.js`; se a do `app.js`
  virar `const`/`async` ou carregar antes, os gates de Terceirizados passam a negar tudo (falha fechada,
  nunca amplia);
- `canAccessView`/`hasConfigurationAccess` dependem de `modules/auth/*` sem fallback: se um desses scripts não
  carregar, a navegação nega tudo (falha fechada);
- os digestos de paridade F4/F5-B foram re-baselinados: o SaaS recebeu exatamente os mesmos commits
  (epi-controle-app#433), com os mesmos digestos;
- os testes estruturais Python de Terceirizados leem `app.js` + módulos juntos; quem barra uma cópia voltando
  ao `app.js` são os testes JS e a guarda (`extracted`).

### 12.7 Próximos candidatos (UBX-V5, não iniciada — requer autorização)

1. Corrigir/decidir os achados 1, 4 e 5 acima (são comportamento, fora de refatoração pura);
2. `archiveEntityRecord`/arquivamento genérico (`ARCHIVAL_ENTITIES`) → módulo próprio (destrava
   `archiveOutsourcedEmployee`);
3. Empresas/Unidades/CNPJ (risco alto: escopo de tenant), com o mesmo teste de matriz por empresa;
4. mapas `VIEW_*` + `showView`/menus (navegação) — último bloco antes do bootstrap.

## 13. UBX-V5, Etapa 1 (2026-10-27) — arquivamento genérico

Base: Corporate `63da879f` / SaaS `0ea3cb08` (`main` com FIX-COLAB-TERC-V1 e FIX-NAV-REFRESH-V1 integradas;
`app.js` idêntico byte a byte nos dois). Refatoração pura: sem mudança de backend, rota, corpo HTTP, permissão,
regra de negócio, texto ou chave i18n.

### 13.1 O que saiu do `app.js`

| Destino | Conteúdo |
|---|---|
| `modules/archival/business/archival-rules.js` (233) | `ARCHIVAL_ENTITIES` (congelado, `path` → `resource`), `UNIT_PURGE_RECORD_LABELS`, filtro único das listas de arquivados (Unidades e genérico eram cópias), normalização dos filtros, quem vê cada botão (`canManageArchived`, `canPurgeArchived`, `canManageArchivedUnits`), retenção/bloqueio jurídico, linhas do resumo de exclusão e nome de confirmação. Puro. |
| `modules/archival/integrations/archival-api.js` (96) | As 25 chamadas (4 recursos × listar/arquivar/desarquivar/pedir, cancelar e confirmar exclusão + `archival-state` do EPI), com caminho e método literais: o contrato front↔back (`tests/test_frontend_api_contract.py`) agora confere todas — antes, `${cfg.path}/…` ficava fora dele. |
| `modules/archival/ui/archival-view.js` (257) | `_epiArchivalPreflight`, `archiveEntityRecord`, `loadArchivedRecords`, `formatArchivedRecordRow`, `renderArchivedRecords`, `syncArchivedRecordsFilters`, `restoreArchivedRecord`, `purgeArchivedRecord` e as células comuns da linha (retenção e selos). |
| `modules/archival/ui/unit-archival-view.js` (164) | `archiveUnit`, `loadArchivedUnits`, `formatArchivedUnitRow`, `renderArchivedUnits`, `syncArchivedUnitsFilters`, `restoreArchivedUnit`, `purgeArchivedUnit`. |
| `modules/outsourced/ui/outsourced-employees-view.js` | `archiveOutsourcedEmployee` (ficava no `app.js` só porque `archiveEntityRecord` era `async` de bloco). |
| removido | `deleteRegistryEntity` (código morto, sem chamadores — registrado na FIX-NAV-REFRESH-V1). |

As funções `async` eram de bloco e agora são globais publicadas pelos módulos (o `app.js` as chama por nome em
`showView`, `VIEW_FILTER_RESET`, `limparFiltrosArquivados` e nos listeners do `init`, sempre em tempo de
execução). As correções da FIX-COLAB-TERC-V1 (lista de Empresas recarregada, `preserveView`, nome de confirmação
das Empresas) e da FIX-NAV-REFRESH-V1 (`runExclusiveMutation`, `refreshAfterMutation`, `coalesceLoad`, gravação
em `try` próprio) estão preservadas e cobertas pelos mesmos testes.

### 13.2 Métricas

| Métrica | Antes | Depois |
|---|---|---|
| `app.js` (linhas, `wc -l`) | 18.167 | 17.638 (−529) |
| Declarações no `app.js` (guarda) | 798 | 778 (−20) |
| Endpoints literais no `app.js` | 112 | 108 (−4) |
| Módulos UBX criados | — | 4 (`archival/business`, `integrations`, 2 × `ui`) |
| Maior módulo novo | — | 257 linhas (limite 500) |
| Ciclos entre scripts | 0 | 0 |
| Testes JS | 644 | 646 (+2 do novo runtime; os de FIX-COLAB-TERC/FIX-NAV-REFRESH passam a carregar os módulos reais) |

Dependências eliminadas: o arquivamento não lê mais nada de bloco do `app.js` (estado e `refs` via
`__EPI_APP_STATE__`/`__EPI_REFS__`, helpers via globais publicados); `archiveOutsourcedEmployee` deixou de prender
o módulo de Terceirizados ao `app.js`; os filtros duplicados (Unidades × genérico) viraram uma regra só. Nenhuma
dependência nova do negócio/integração para a UI (guarda: camadas OK).

### 13.3 Equivalência

`static/js/test/archival-view-runtime.js` roda **214 cenários** contra os módulos e contra as funções originais
(`fixtures/app-before-ubx-v5-archival.js.txt`: cada declaração copiada literalmente de `63da879f`, sem os
comentários de seção e com `ARCHIVAL_ENTITIES` ao lado de `UNIT_PURGE_RECORD_LABELS`), no mesmo ambiente, e exige
resultado idêntico: chamadas HTTP (método, caminho, corpo), diálogos, prompts, alertas, toasts, recargas
(bootstrap com `preserveView`, Empresas, listas), estado final de listas e filtros e o HTML das tabelas.
Cobre 6 papéis × 5 filtros na renderização, tabela ausente e vazia, carga com/sem permissão, falha e o
comportamento herdado de `updatePermission.replace(':update', ':view')` (só a 1ª ocorrência), e arquivar,
desarquivar e excluir para os 4 tipos, um tipo desconhecido e Unidades — ok, cancelar, motivo vazio/nulo,
falha da gravação, falha da recarga, sem permissão, registro ausente, clique duplo, pré-voo do EPI (falha,
vínculos, sem saldo bloqueável, sem motivo, cancelado), nome fantasia na confirmação e sessão sem usuário no meio
da exclusão. Também registra as chaves de `runExclusiveMutation`/`coalesceLoad` e a ordem das chaves das
opções HTTP. A referência não pode
quebrar (nenhum cenário com exceção).

Sabotagem: 17 mutações nos módulos (papéis de exclusão e de gestão, filtro `outsourced_only`, `replaceAll` na
permissão de leitura, ordem do nome de confirmação, limite de retenção, recarga de Empresas na exclusão,
atualização do Estoque Bloqueado, guarda de registro ausente, `preserveView` das Unidades, papel das Unidades,
recarga fora de `refreshAfterMutation`, método HTTP, chave de `coalesceLoad`, chave de `runExclusiveMutation`,
id do ator lido fora do `try`) — **todas detectadas**. A do `replaceAll` e as três últimas só passaram a ser
detectadas depois dos cenários `soLeituraSimplificada` e `semUsuario` e do registro das chaves (achados P3 da
auditoria, §13.6).

Navegador (Chromium, 5 idiomas): `fix_colab_terc.py` 40/40 e `fix_nav_refresh.py` 35/35 contra o código
extraído. Os idiomas não mudam: nenhum texto ou chave foi alterado, só a origem das chamadas a `tr()`.

### 13.4 Mudança deliberada mínima

`archivalConfig(kind)` só aceita chaves próprias (`hasOwnProperty`): antes, `ARCHIVAL_ENTITIES['constructor']`
devolvia uma função do protótipo. Nenhum chamador passa esse valor (os `kind` vêm de `data-archived-*` que o
próprio front escreve); o efeito é recusar em vez de quebrar.

### 13.5 Riscos residuais

- As funções passaram de bloco para globais: um script que declare o mesmo nome depois dos módulos as
  sobrescreveria. A guarda (`extracted`) barra o nome voltando ao `app.js`;
  `extracted-globals-ownership-runtime.js` só pega `globalThis.nome =`/`globalThis['nome'] =`, não o laço
  `globalThis[name] = fn` dos módulos, então uma reexportação por outro módulo não seria apontada. Hoje nenhum
  outro script declara ou publica esses nomes (conferido pela auditoria). `_epiArchivalPreflight`,
  `formatArchivedRecordRow` e `formatArchivedUnitRow` constam de `extracted` mas não são mais globais (só nos
  namespaces); `applyArchivedUnitsFilters` e as duas `format*Row` eram globais (Annex B) e deixaram de ser —
  nenhuma referência fora de testes/docs, inclusive em `flutter/`.
- `loadArchivalPolicy` (configuração da política) ficou no `app.js`: é domínio de configuração, vai com a
  Etapa 2/3.
- O teste Python de paridade de permissões (web × Flutter) e os testes estruturais de arquivamento passaram a
  ler `archival-rules.js`/os módulos; quem barra uma cópia voltando ao `app.js` são o teste JS e a guarda.

### 13.6 Auditoria independente

Agente separado, só leitura, sobre `d182f659`/`9d04c618` (e o ajuste de CodeQL `fb07349d`/`28bf15a`). **Nenhum
P0/P1/P2.** Conferido de forma independente:

- equivalência linha a linha das 25 chamadas HTTP (método, caminho, query, ordem das chaves do corpo), diálogos,
  `alert` × `showToast`, fronteiras de `try`, recargas, papéis e HTML;
- cada declaração do fixture idêntica à de `63da879f`;
- resolução de nomes (bloco × Annex B, provado em `vm`), ordem de carga e ausência de colisão;
- regras de camada, contrato HTTP e `filterByUserCompany` em todas as listas;
- paridade SaaS byte a byte;
- 20 mutações próprias: 17 detectadas, 2 sobreviventes (renomear chaves) e 1 controle neutro.

Os 7 achados P3 foram tratados no PR:

- id do ator lido uma vez fora do `try` na exclusão: voltou a ser lido em cada chamada, como no original, com
  cenário `semUsuario`;
- delta de linhas corrigido;
- cobertura real do teste de propriedade dos globais;
- helpers que deixaram de ser globais;
- `deleteRegistryEntity` na §4;
- descrição do fixture;
- chaves de execução única e de leitura coalescida agora registradas pelo teste, de modo que as duas mutações
  sobreviventes passam a ser detectadas.

## 14. UBX-V5, Etapa 2 — fatia 1 (2026-10-27): Unidades e CNPJ

Base: Corporate `4aca4ada` / SaaS `58235935` (`main` com a Etapa 1 integrada; `app.js` idêntico nos dois).
Refatoração pura: sem mudança de backend, rota, corpo HTTP, permissão, regra de negócio, texto ou chave i18n.
Ordem autorizada da Etapa 2: Unidades e CNPJ → Empresas → Minha Empresa → Comercial (este após a I18N-FULL-V1).

### 14.1 O que saiu do `app.js`

| Destino | Conteúdo |
|---|---|
| `modules/legal-entities/integrations/legal-entities-api.js` (21) | Inativação de CNPJ (`DELETE /api/legal-entities/<id>?actor`), com caminho e método literais (agora conferida pelo contrato front↔back). Cadastro e edição seguem pelo `saveSimpleForm` do `app.js`. |
| `modules/legal-entities/ui/legal-entities-view.js` (284) | Seletores de vínculo jurídico (`legalEntityHelpers`, `legalEntitiesForCompany`, `unitLegalEntityLabel`, `legalEntityOptionsHtml`, `syncUnitLegalEntityOptions`, `syncReportLegalEntityOptions`) e a tela de CNPJs (`legalEntitiesViewHelpers`, `renderLegalEntities`, `formatLegalEntityRow`, `syncLegalEntitiesFilters`, `syncLegalEntityCompanyField`, `setLegalEntityFormMode`, `resetLegalEntityForm`, `startEditLegalEntity`, `deactivateLegalEntity`). |
| `modules/units/business/unit-rules.js` (29) | Filtro da lista de Unidades e Unidades por empresa. Puro. |
| `modules/units/ui/units-view.js` (89) | `unitsForSearchByCompany`, `syncUnitsSearchFilters`, `applyUnitsFilters`, `formatUnitTableRow`, `formatUnitOption`, `startEditUnit`. A tabela continua montada em `renderTables` (app.js). |

As regras puras já existentes (`js/views/legal-entity-fields.js`, `js/views/legal-entities-view.js`) não mudaram:
o I18N-FULL-V1 (Codex, ainda aberto) altera `js/views/legal-entities-view.js`, e mexer nele agora criaria
conflito. Nenhuma das 21 funções extraídas é alterada por aquele PR (conferido hunk a hunk sobre a base dele).
Todas eram globais do `app.js` (Annex B), exceto `deactivateLegalEntity` (`async` de bloco); continuam
publicadas com os mesmos nomes — `modules/employees`, `modules/reports` e o `app.js` as chamam.

### 14.2 Métricas

| Métrica | Antes | Depois |
|---|---|---|
| `app.js` (linhas, `wc -l`) | 17.638 | 17.342 (−296) |
| Declarações no `app.js` (guarda) | 778 | 757 (−21) |
| Endpoints literais no `app.js` | 108 | 107 (−1) |
| Módulos UBX criados | — | 4 (`legal-entities/integrations`, `legal-entities/ui`, `units/business`, `units/ui`) |
| Maior módulo novo | — | 284 linhas (limite 500) |
| Ciclos entre scripts | 0 | 0 |
| Testes JS | 646 | 648 (+2 do novo runtime) |

Dependências eliminadas: a tela de CNPJs e a edição de Unidade não leem mais nada de bloco do `app.js` (estado e
`refs` via `__EPI_APP_STATE__`/`__EPI_REFS__`); o filtro de Unidades virou regra pura com os filtros por
parâmetro. Nenhuma dependência nova de negócio/integração para a UI.

### 14.3 Equivalência

`static/js/test/units-legal-entities-runtime.js` roda **102 cenários** contra os módulos e contra as funções
originais (`fixtures/app-before-ubx-v5-units-legal-entities.js.txt`: cada declaração copiada literalmente de
`4aca4ada`), no mesmo ambiente, com e sem as regras puras carregadas (fallbacks). Compara chamadas (API,
`confirm`, `alert`, `loadBootstrap`, rótulo do botão, navegação, `populateSelect`, `renderTables`), campos e
formulários, HTML das tabelas e filtros. Cobre permissões de editar/inativar, CNPJ inativo e único ativo, filtros
da tela, campo de empresa (Master × demais × sem nome × sem elementos), modo de edição, reset, edição com e sem
campo de empresa/CNPJ, inativação (ok, cancelada, sem permissão, inexistente, falha da API e da recarga),
seletores de CNPJ de Unidade e Relatórios (empresa do campo × do usuário, seleção mantida × descartada) e
Unidades (busca por empresa, filtros, linha com/sem gestão, opção, edição). 0 divergências; a referência não
quebra em nenhum cenário.

Sabotagem: 19 mutações nos módulos (`activeOnly`, papel do Master, recarga com `preserveView`, situação na edição,
permissão de inativar, campo de empresa habilitado, confirmação ignorada, seleção anterior não validada, HTML sem
escape, método HTTP, caixa do tipo de Unidade, Unidades sem empresa no filtro, escopo `filterByUserCompany`, coluna de CNPJ,
sincronização do CNPJ na edição, filtros sem minúsculas, e as três que a auditoria achou sobreviventes: escape da
coluna de CNPJ das Unidades, ordem campo de empresa × valor na edição, id não limpo no "Novo CNPJ") — **todas
detectadas**. Cinco só passaram a ser detectadas depois de aproximar o ambiente falso do DOM: reescrever as opções
limpa o valor, trocar as opções seleciona a primeira, `form.reset()` não limpa o id oculto, o `company_id` do
formulário é o próprio `#legal-entity-company`, mais uma Unidade com tipo em maiúsculas e outra com HTML no rótulo
do CNPJ.

Navegador (Chromium, 5 idiomas): `scripts/browser/ubx_units_legal_entities.py` (novo, roda no workflow
*Colaboradores and outsourced browser regression*) — tela de CNPJs (lista só ativos, campo de empresa desabilitado
fora do Master, editar preenche o formulário
inclusive a situação, "Novo CNPJ" volta a cadastrar), inativação (confirmação + `DELETE` com o ator) e Unidades
(coluna de CNPJ, filtro por nome, edição com o CNPJ vinculado sem sair da tela): **15/15**, e 15/15 também contra a
`main` (mesmo comportamento antes e depois). `fix_colab_terc.py` 40/40 e `fix_nav_refresh.py` 35/35 continuam.

### 14.4 Observações e riscos residuais

- Comportamento herdado preservado, não corrigido: `syncUnitsSearchFilters` guarda o tipo em minúsculas e o filtro
  compara com o tipo do registro sem normalizar; uma Unidade com tipo em maiúsculas nunca casaria. Os tipos
  cadastrados hoje são minúsculos.
- O novo harness acusou um erro de página que já existe na `main` e nos harnesses da FIX: o fixture base responde
  `/api/reports` com um payload genérico e `renderReports` quebra ao montar o resumo. É do fixture, não do produto
  (o backend sempre manda `deliveries`); o harness novo responde no formato real e exige zero erros de página.
- `deactivateLegalEntity` continua recarregando com `loadBootstrap()` sem `preserveView` (grupo D da
  FIX-NAV-REFRESH-V1, fora do escopo desta refatoração).
- O I18N-FULL-V1 altera `UNIT_PURGE_RECORD_LABELS`, que a Etapa 1 moveu para `archival-rules.js`: o Codex terá
  conflito ao atualizar a branch dele (aviso registrado no relatório da etapa).

### 14.5 Auditoria independente

Agente separado, só leitura, sobre `131bca79`/`5000626`. **Nenhum P0/P1/P2.** Conferido de forma independente:

- equivalência linha a linha contra `4aca4ada` (escrita no DOM e sua ordem, permissões, chamada HTTP, `confirm`,
  `alert`, `loadBootstrap()` sem argumentos, escape, fallbacks sem as regras);
- fixture idêntico declaração a declaração (comparação por AST);
- só as 21 declarações saíram do `app.js` (AST antes × depois);
- resolução de nomes (inclusive `hasPermission` de um argumento, que o `app.js` sobrescreve pelo Annex B) e todos os
  chamadores; nenhum outro script publica esses nomes;
- isolamento por empresa e campo de empresa fora do Master;
- paridade SaaS byte a byte;
- conflitos com o I18N-FULL-V1 (`624d8915`): os mesmos 9 arquivos e hunks da Etapa 1, nenhum novo —
  `formatUnitOption`/`syncReportLegalEntityOptions` caem dentro de hunks que já existiam. Ao resolver, o Codex
  precisa descartar a cópia dessas duas do lado dele; a guarda e o teste "voltou ao app.js" acusam o engano.

Achados P3 e tratamento:

- 3 mutações (de 32 do auditor) passavam pelo teste de caracterização: escape da coluna de CNPJ, ordem na edição e
  id no reset. O ambiente falso foi aproximado do DOM (§14.3) e as três passaram a ser detectadas. A quarta
  sobrevivente é equivalente (`mode !== 'edit'` × `mode === 'create'` para os únicos valores usados).
- O harness Chromium não conferia o campo de empresa fora do Master: passou a conferir (desabilitado, empresa da
  conta).
- Registrado como risco residual, sem mudança: se `unit-rules.js` ou `legal-entities-api.js` não carregar,
  `applyUnitsFilters` lança (e `renderTables` aborta) e inativar mostra um `alert` com o `TypeError` — antes tudo
  estava num arquivo só. É o mesmo padrão aceito na Etapa 1; a ordem de carga é conferida pelo teste de contrato.
- Preexistente, preservado: `formatUnitTableRow`/`formatUnitOption` interpolam nome, empresa e cidade da Unidade
  sem escape (como no `app.js`). Correção de segurança, se desejada, vai num PR próprio.
- Os testes do harness ainda não cobrem os seletores de CNPJ de Colaboradores e Relatórios nem o listener de troca
  de empresa da Unidade (cobertos pelo teste de caracterização).

## 15. UBX-V5, Etapa 2 — fatia 2 (2026-10-27): Empresas

Base: Corporate `a2358206` / SaaS `c6f6d687` (`main` com Unidades e CNPJ integradas; `app.js` idêntico nos dois).
Refatoração pura: sem mudança de backend, rota, corpo HTTP, permissão, regra de negócio, texto ou chave i18n.

### 15.1 O que saiu do `app.js`

| Destino | Conteúdo |
|---|---|
| `modules/companies/business/company-rules.js` (93) | Contagens do resumo, tom do selo de licença, risco de uso (no limite × próxima do limite), corpos de gravação da empresa (cadastro/edição e ativar/inativar, mesmas chaves e padrões) e as regras do suporte auditado de logotipo (justificativa ≥ 10, tipos de imagem). Puro. |
| `modules/companies/integrations/companies-api.js` (29) | `POST /api/companies`, `PUT /api/companies/<id>`, `POST /api/companies/<id>/support-update`, com caminho e método literais (o `PUT`/`POST` condicional do `saveCompany` virou dois ramos literais, agora conferidos pelo contrato front↔back). |
| `modules/companies/ui/companies-view.js` (294) | `getCompanyFormField`, `setCompanyFieldValue`, `readCompanyFieldValue`, `renderCompaniesSummary`, `companyStatusBadges`, `companyUsageText`, `renderCompanyDetails`, `companyRowActions`, `formatCompanyRow`, `renderCompanies`, `resetCompanyForm`, `startEditCompany`, `openCompanyLogoEditor`, `saveCompany`, `toggleCompany`. |

Ficam no `app.js`: `companyLogoSrc`/`companyLogoMarkup` (compartilhados por topo, Comercial e Fichas — vão para
`shared/` numa fatia própria), `formatCompanyCurrency` e `updateTopbarCompanyBadge` (alterados pelo I18N-FULL-V1;
nenhuma das 15 funções extraídas é alterada por aquele PR, conferido hunk a hunk sobre a ponta `454bee68`) e os
filtros do Comercial. `companyUsageText` não tem chamador, mas era global (Annex B) e continua publicada.
`saveCompany` lê `state.user.id` antes do formulário, como o original (sem sessão, falha antes de ler os campos).

### 15.2 Métricas

| Métrica | Antes | Depois |
|---|---|---|
| `app.js` (linhas, `wc -l`) | 17.342 | 17.120 (−222) |
| Declarações no `app.js` (guarda) | 757 | 742 (−15) |
| Endpoints literais no `app.js` | 107 | 106 (−1) |
| Módulos UBX criados | — | 3 (`companies/business`, `integrations`, `ui`) |
| Maior módulo novo | — | 294 linhas (limite 500) |
| Ciclos entre scripts | 0 | 0 |
| Testes JS | 648 | 650 (+2 do novo runtime) |

### 15.3 Equivalência

`static/js/test/companies-view-runtime.js` roda **53 cenários** contra os módulos e contra as funções originais
(`fixtures/app-before-ubx-v5-companies.js.txt`, cada declaração copiada literalmente de `a2358206`): resumo, lista e
detalhes por permissão, área comercial, visibilidade e seleção; selos e ações de linha para cada estado de licença
e uso; campos do formulário presentes/ausentes (com o `console.error` do original); reset; edição; gravação (criar
com/sem Administrador Geral inicial, editar, empresa incompleta, campos ausentes, sem permissão, falha da API, sem
sessão); ativar/inativar; logotipo por suporte (ok, SVG, tipo inválido, sem arquivo, falha da API, justificativa
curta/vazia/cancelada/exatamente 10, vários arquivos, não-Master, empresa inexistente), mais sem sessão com campos
ausentes (fixa a ordem de leitura) e empresa inativa sem o campo de status. 0 divergências; a referência não quebra.

Sabotagem: 24 mutações — 23 detectadas; a restante é equivalente (forçar os campos do Administrador Geral também na
edição: chegam `undefined` e `JSON.stringify` os descarta, o corpo enviado é o mesmo). Quatro delas (ordem ator ×
formulário, `?? 1` × `|| 1`, justificativa vazia, primeiro arquivo) só passaram a ser detectadas com os cenários
acrescentados após a auditoria (§15.5).

Navegador (Chromium, 5 idiomas): `scripts/browser/ubx_companies.py` (novo, no workflow *Colaboradores and
outsourced browser regression*, cujo limite passou de 20 para 30 minutos com quatro harnesses) — lista/resumo/
detalhes, editar e gravar (`PUT` com os valores comerciais atuais e sem o Administrador Geral), cadastrar (`POST`
com o Administrador Geral) e inativar (`PUT` com `active: 0`, sem diálogos): **20/20**, e 20/20 também contra a `main`.
O fixture aceita `active: ''`; o harness fixa esse valor com o marcador `KNOWN-DEFECT` (§15.4), para que a correção
apareça como falha esperada, e não passe em silêncio.

### 15.4 Defeito preexistente encontrado (fora do escopo, não corrigido)

O `<select name="active">` do formulário de Empresas (`static/views/empresas.html`) usa `data-i18n-value` nas
opções; o `i18n.js` troca o `value` delas pelo texto traduzido ("Ativa"/"Inativa"), o seletor perde `1`/`0` e o
formulário envia `active: ''`. O backend recusa (`require_fields` → "Campo obrigatório: active", antes de qualquer
autorização, em `POST` e `PUT`), então cadastrar e editar Empresa pelo web falha em todos os idiomas — reproduzido no
Chromium contra a `main`. Se o usuário escolher a opção à mão, vai o texto traduzido ("Inativa"/"Inactive") e o backend
falha no `int()` (`modules/companies/routes.py:155`, `service.py:423/456`). As opções também não têm `data-i18n`: o
texto visível fica em português em todos os idiomas. Ativar/inativar pela lista não é afetado (não lê o formulário).
Nenhum outro `data-i18n-value` em `<option>`/campo enviado existe em `static/views` ou `static/index.html`. Vem de #974; o
I18N-FULL-V1 mantém o atributo. Correção proposta à parte (remover `data-i18n-value` das duas opções, mantendo o
texto traduzido por `data-i18n`, com teste), por ser mudança de comportamento.

### 15.5 Auditoria independente

Agente separado, só leitura, sobre `1e09e160`/`b743a9f`. **Nenhum P0/P1 na refatoração.** Conferido de forma
independente: equivalência função a função contra `a2358206` (escritas no DOM e ordem, ordem de avaliação do
`saveCompany`, corpos com as mesmas chaves e ordem, métodos/caminhos, permissões, checagem de Master, textos de
prompt/alert, `try/catch`); fixture idêntico e só as 15 declarações removidas (AST); resolução de todos os nomes
livres (inclusive `planLabel` — o de `pagamento.js` só carrega em `pagamento.html` — e `hasPermission` de um
argumento, que o `app.js` sobrescreve antes de qualquer chamada) e de todos os chamadores; camadas, contrato HTTP
(3 mutações de rota detectadas), isolamento por empresa; paridade SaaS byte a byte; métricas da §15.2; e o
I18N-FULL-V1 (ponta `0f83da08`): mesmos arquivos e hunks de conflito das fatias anteriores, nenhum novo.

Achados e tratamento:

- Defeito preexistente da §15.4 confirmado e detalhado (texto acima).
- P2 — o harness aceitava `active` qualquer: passou a fixar `active == ''` com o marcador `KNOWN-DEFECT`, a conferir
  `general_admin_name` no cadastro e a exigir nenhum diálogo ao inativar.
- P3 — 4 mutações do auditor (de 26) sobreviviam ao teste de caracterização; os 4 cenários acrescentados as detectam.
- P3, registrados sem mudança: `saveCompany`/`toggleCompany` passaram de `async` de bloco a globais (o backend autoriza
  cada chamada); os módulos dependem do `hasPermission` de um argumento do `app.js` (mesmo padrão das fatias
  anteriores); os módulos rodam em modo estrito (sem efeito observável).

## 16. UBX-V5, Etapa 2 — fatia 3 (2026-10-27): Minha Empresa

Base: Corporate `c1c9ac6f` / SaaS `b936120a` (`main` com Empresas integrada; `app.js` idêntico nos dois).
Refatoração pura: sem mudança de backend, rota, corpo HTTP, permissão, regra de negócio, texto ou chave i18n.

### 16.1 O que saiu do `app.js`

| Destino | Conteúdo |
|---|---|
| `modules/my-company/business/my-company-rules.js` (51) | Tipos de imagem por campo, cores padrão, modo de tema em `theme_json` e os rótulos de situação dos domínios. Puro. |
| `modules/my-company/integrations/my-company-api.js` (52) | `GET`/`PUT /api/my-company` e os domínios (`GET`/`POST /api/my-company/domains`, `POST .../verify`, `POST .../primary`, `DELETE` com corpo), com caminho e método literais. A empresa vem da sessão no backend. |
| `modules/my-company/ui/my-company-view.js` (228) | `myCompanyThemeMode`, `fillMyCompanyFields`, `renderMyCompanyImagePreview`, `collectMyCompanyFields`, `wireMyCompanyImageInputs`, `loadMyCompany`, `renderMyCompanyReadonly`, `loadMyCompanyCard`, `saveMyCompany`, `loadMyCompanyDomains`, `domainStatusLabel`, `addMyCompanyDomain`, `handleMyCompanyDomainAction`; e as constantes `MY_COMPANY_IMAGE_TYPES`/`MY_COMPANY_COLOR_DEFAULTS` (no negócio). |

Fica no `app.js` `renderMyCompanyDomains` (alterada pelo I18N-FULL-V1; nenhuma das 15 declarações extraídas é
alterada por aquele PR, conferido hunk a hunk sobre a ponta `5baea4bc`), chamada pelo módulo pelo nome global. As
ações de domínio tiveram de vir junto: eram `async` de bloco e `loadMyCompanyCard` as liga. O assistente de
implantação (`app.js`) continua chamando `loadMyCompany`, `fillMyCompanyFields`, `wireMyCompanyImageInputs` e
`collectMyCompanyFields`, agora globais publicadas pelo módulo.

### 16.2 Métricas

| Métrica | Antes | Depois |
|---|---|---|
| `app.js` (linhas, `wc -l`) | 17.120 | 16.941 (−179) |
| Declarações no `app.js` (guarda) | 742 | 727 (−15) |
| Endpoints literais no `app.js` | 106 | 104 (−2) |
| Módulos UBX criados | — | 3 (`my-company/business`, `integrations`, `ui`) |
| Maior módulo novo | — | 228 linhas (limite 500) |
| Ciclos entre scripts | 0 | 0 |
| Testes JS | 650 | 652 (+2 do novo runtime) |

### 16.3 Equivalência

`static/js/test/my-company-view-runtime.js` roda **64 cenários** contra os módulos e contra as funções originais
(`fixtures/app-before-ubx-v5-my-company.js.txt`, cada declaração copiada literalmente de `c1c9ac6f`): preencher e
coletar (tema válido/inválido/ausente, cores normalizadas, campos ausentes, espaços), prévia, contrato somente
leitura, rótulos; carga (cache, forçada, sem permissão, sem empresa, falha que propaga como no original); cartão
(primeira carga liga os listeners uma vez, segunda não, sem formulário, falha com `console.warn`); imagens (logo em
JPEG, favicon, tipo inválido, sem arquivo, campo desconhecido, falha de conversão, sem campo oculto, vários
arquivos, sem religar); gravação (ok, resposta sem empresa, falha com e sem retorno, sem permissão, sem
formulário, sem sessão); domínios (listar, resposta não-lista/nula, falha, sem tabela, sem permissão; registrar com
e sem tipo, vazio, falha, sem campos, sem sessão; verificar, principal, remover com e sem confirmação, nenhuma
ação, falhas, falha do `loadBootstrap` após gravar, recarga depois de falha). O registro inclui o nome do handler
ligado e o instante em que a função devolve. 0 divergências.

Sabotagem: 27 mutações (tipos de imagem, cores, tema padrão e gravado, rótulos, método e corpo HTTP, cache, estado
após a resposta, `trim`, religar imagens, limpar o arquivo recusado, JPEG do logo, religar o formulário, recarga dos
domínios, retorno sem feedback, confirmação de remoção, recarga após falha, permissão, domínio vazio, e — após a auditoria — handler errado no submit, no botão de
adicionar e nos dois trocados, `loadBootstrap` sem `await` e recarga sem `await` no erro de ação de domínio) —
**todas detectadas**.

Navegador (Chromium, 5 idiomas): `scripts/browser/ubx_my_company.py` (novo, no workflow) — aba Empresa das
Configurações (formulário preenchido com tema e cores, contrato somente leitura, `PUT` sem `company_id`) e domínios
(registrar, instruções de DNS, verificar, remover com confirmação): **10/10**, e 10/10 também contra a `main`.

### 16.4 Auditoria independente e riscos residuais

Auditoria somente leitura (Corporate `3327065d`, SaaS `9e561cd2`): **aprovada, sem bloqueios**. Confirmou, declaração
a declaração, equivalência de ramos, textos, ids, chaves e ordem dos corpos HTTP, momento da avaliação de
`state.user.id` e da ligação dos listeners; que todo chamador restante resolve na chamada; fixture literal de
`c1c9ac6f`; contrato HTTP (7 chamadas, método e caminho literais); paridade byte a byte com o SaaS; e os números da
§16.2. Achados tratados neste PR:

| Achado | Tratamento |
|---|---|
| Stub de `bindAppListener` não registrava qual função era ligada (3 trocas de handler passavam) | Log com `handler.name`; as 3 trocas agora divergem |
| `loadBootstrap` nunca falhava (remover o `await` passava) | Cenário `salvar:falhaBootstrap` |
| Ordem do `await` na recarga após falha de ação de domínio | Marca `resolved` no fim de cada cenário + `dominio:acao:falhaRecarrega` |
| Guarda "nada volta ao app.js" só via declarações na coluna 0 | Regex aceita indentação |
| Comentário dizia que a I18N-FULL-V1 já alterou `renderMyCompanyDomains` | Corrigido: PR pendente |

Riscos residuais (não tratados aqui):

- **Segurança — preexistente, alta (CodeQL "DOM text reinterpreted as HTML" na prévia de imagem).** A validação de
  logotipo (`validate_logo_payload`, `modules/commercial/service.py`) e `companyLogoSrc` só conferem o prefixo
  `data:image/`; um valor como `data:image/png" onerror="…"` é aceito, gravado e fecha o atributo `src` onde
  `companyLogoMarkup` renderiza (topbar, lista de Empresas do Administrador Master, prévias). Grava quem tem
  `company_settings:update` (Administrador Geral) ou o Master; afeta os usuários da empresa e o Master. O CSP do app é
  *Report-Only*. A linha só mudou de arquivo (na `main`: `static/app.js:11427`). Correção proposta em PR de segurança
  separado, aguardando autorização: regex estrita de data URL base64 (PNG/JPEG/SVG) no backend e escape do atributo no
  frontend.
- O assistente de implantação (`app.js`) chama `loadMyCompany`, `fillMyCompanyFields`, `wireMyCompanyImageInputs` e
  `collectMyCompanyFields` pelo nome global; a resolução foi conferida estaticamente, mas nenhum teste de navegador
  percorre o assistente.
- Seis funções antes `async` de bloco agora são globais (mesmo padrão da §15); nada as sonda e as guardas de
  permissão são as mesmas.
- O teste de navegador não clica em "Tornar principal" nem envia imagem (ambos cobertos pelo teste de runtime).
