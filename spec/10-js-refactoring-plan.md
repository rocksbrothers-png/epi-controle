# Plano de Refatoração JavaScript — EPI SaaS

## Objetivo

Refatorar o frontend JavaScript legado de um bundle monolítico (`app.js` ~758 KB) para uma estrutura modular organizada em `static/js/`, sem alterar lógica de negócio existente e mantendo compatibilidade total com o HTML/Python atual.

## Princípios (AGENTS.md)

1. **Não alterar lógica existente** — mover código, não reescrever
2. **Refatorar apenas a estrutura** — separação por responsabilidade
3. **Manter compatibilidade total** — mesmos `globalThis.*` exportados
4. **Usar separação por módulos** — IIFE por arquivo, guards de duplo-carregamento

## Nova Estrutura de Diretórios

```
static/
├── js/                          ← NOVO: módulos organizados
│   ├── core/                    ← Constantes e configurações imutáveis
│   │   ├── constants.js         ← STORAGE_KEYS, ROLE_LABELS, ROLE_ALIASES
│   │   ├── permissions.js       ← ROLE_PERMISSIONS, VIEW_PERMISSIONS, VIEW_EYEBROW
│   │   ├── feature-flags.js     ← UX_FRONTEND_FLAGS, FEATURE_FLAG_DEFINITIONS
│   │   └── config.js            ← DEFAULT_CONFIGURATION_FRAMEWORK, DEFAULT_COMMERCIAL_SETTINGS
│   ├── utils/                   ← Funções utilitárias puras
│   │   ├── debug.js             ← debugLog, reportNonCriticalError, isDebugModeEnabled
│   │   ├── perf.js              ← EPI_PERF_RUNTIME, markRender*, trackAnalytics
│   │   ├── storage.js           ← safeStorageRead, safeStorageWrite, queueStorageWrite
│   │   ├── dom.js               ← safeOn, isViewActive, resolveFormFieldAutocomplete
│   │   └── abort.js             ← createScopedAbortController, registerAbortableRequest
│   └── modules/                 ← Módulos de funcionalidade
│       ├── auth.js              ← login, logout, validação de sessão, JWT decode
│       ├── api-client.js        ← apiFetch, interceptors, error handling
│       ├── router.js            ← SPA routing, pushState, popstate handler
│       ├── session.js           ← Gerenciamento de estado da sessão
│       ├── permissions.js       ← hasPermission, canViewRoute (runtime)
│       └── feature-flags-rt.js ← getFeatureFlag runtime (lê storage/query)
├── app.js                       ← Mantido: entry point + render de views
├── i18n.js                      ← Mantido: motor i18n
├── navigation.js                ← Mantido: phase46 navigation
└── ...                          ← Demais arquivos mantidos
```

## Fases de Refatoração

### Fase 1 — Extração de Constantes (✓ Completa)

**Arquivos criados:**
- `static/js/core/constants.js`
- `static/js/core/permissions.js`
- `static/js/core/feature-flags.js`
- `static/js/core/config.js`

**app.js:** Linhas 1–202 substituídas por guards que verificam se já foram carregadas pelos módulos.

**Compatibilidade:** Zero quebras — todos os valores ainda disponíveis em `globalThis`.

### Fase 2 — Utilitários + Integração (✓ Completa)

**Arquivos criados:**
- `static/js/utils/debug.js` — `debugLog`, `reportNonCriticalError`, `ensureModuleBound`
- `static/js/utils/perf.js` — `EPI_PERF_RUNTIME`, `markRender*`, `queueStorageWrite`, abort controllers
- `static/js/utils/storage.js` — `safeStorageRead/Write/Remove`, `safeJsonParse/Stringify`
- `static/js/utils/dom.js` — `safeOn`, `isViewActive`, `resolveFormFieldAutocomplete`
- `static/js/modules/feature-flags-rt.js`, `static/js/modules/permissions-rt.js` (runtime; ainda não conectados — ver nota de paridade)

**Integração no `index.html` (via `static/views/_layout.html`):**
Os 8 módulos core/utils são carregados com `defer` **antes** de `app.js`.
Isso é seguro porque:
- `app.js` linha 4 lê `globalThis.STORAGE_KEYS || Object.freeze({…})` → usa o objeto do módulo (idêntico).
- Demais constantes em `app.js` são `const` de bloco (escopo do IIFE), não colidem com os globais dos módulos.
- `app.js` linha 949 faz `globalThis.__EPI_FRONTEND_HELPERS__ = Object.freeze({…})` **depois** dos módulos rodarem — sem erro de escrita em objeto congelado.

**Nota de paridade:** `feature-flags-rt.js` ainda **não** replica a lógica de
kill switch (`UX_FORCE_CLASSIC_FLAGS` + `ux_global_kill_switch`) de `app.js`.
Por isso NÃO está conectado no `index.html` — a resolução canônica continua
sendo a de `app.js`. Conectar somente após paridade total.

**Compatibilidade:** Zero quebras — verificado por `test_web_hardening_checks.py`,
`test_static_assets.py` e `test_js_syntax.py` (31 passes).

### Fase 3 — Módulo de Auth (✓ Completa)

**Arquivo criado:** `static/js/modules/auth.js`

Reimplementação modular e testável das funções de autenticação e gestão de
sessão de `app.js`, seguindo o **padrão aditivo** dos demais módulos
(`permissions-rt`, `feature-flags-rt`): `app.js` mantém suas cópias locais como
autoridade em runtime; o módulo expõe as versões canônicas em `globalThis` para
o app modular futuro, scripts externos e testes.

**Classificação de erros (puras):**
- `getLoginErrorMessage(error)` — mensagens humanizadas para o login
- `isTemporaryBootstrapUnavailable(error)` — 502/503/504 ou DB_BOOTSTRAP_NOT_READY
- `isSessionRestoreAuthError(error)` — detecta 401/403 em restauração de sessão
- `isBootstrapRequestError(error)` — detecta erros que ativam modo degradado

**Gestão de sessão (operam sobre `globalThis.__EPI_APP_STATE__`):**
- `normalizePermissions(user, permissions)` — une permissões + fallback do role
- `saveSession(user, permissions, token)` — normaliza role (NFD completo, idêntico a app.js) e persiste sessão/permissões/token
- `setPasswordChangeRequired(required)` — persiste flag de troca de senha
- `clearSession()` — zera estado e storage, cancela timers de auto-retry

Como operam sobre o **mesmo objeto de estado global** que `app.js` publica
(`__EPI_APP_STATE__`), callers externos manipulam exatamente a mesma sessão.

**Por que não fazer `app.js` delegar?** `app.js` define suas próprias cópias
locais de `safeStorageWrite`, `normalizeRole`, etc. (não consome os módulos em
runtime). Fazer o monólito delegar a um módulo introduziria uma dependência
dura de carregamento (regressão se o módulo falhar). O padrão estabelecido —
módulos paralelos canônicos, `app.js` intacto — é mantido.

**`handleLogin()`** permanece em `app.js`: é um orquestrador de DOM (`refs`,
`setLoginMessage`, `showScreen`, `renderAll`, ~15 funções locais), não lógica
pura; sua extração pertence à Fase 5 (router/orquestração), após externalizar o
estado de `refs`.

**Parity fix `feature-flags-rt.js`:** paridade total com `app.js`:
- `isUxGlobalKillSwitchActive()` — verifica `globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__` antes da storage
- `getFeatureFlag()` — aplica `UX_FORCE_CLASSIC_FLAGS` kill-switch, idêntico a `app.js`
- Conectado no `index.html` (antes de `app.js`), expondo `globalThis.getFeatureFlag` para scripts externos (ux-phase41/43/44.js, entrega-epi.js).

**Testes:** 32 testes JS passam (17 novos: kill-switch parity 3, auth puras 8, sessão 6).

### Fase 4 — Cliente de API (✓ Completa)

**Arquivo criado:** `static/js/modules/api-client.js`

Reimplementação canônica da camada HTTP de `app.js`, seguindo o padrão aditivo.
`buildApiHeaders` acessa o token via `globalThis.__EPI_APP_STATE__.token` (mesmo
objeto de estado publicado por `app.js`), sem acesso a `refs` ou DOM.

**Funções puras:**
- `createApiError(message, response, payload, code)` — factory de Error com `status/code/payload`
- `isBootstrapApiPath(path)` — detecta rotas `/api/bootstrap*`
- `waitMs(ms)` — delay Promise-based com backoff
- `ensureExpectedApiResponse(path, response, payload, contentType)` — lança `INVALID_API_RESPONSE` para `/api/*` não-JSON
- `throwIfApiRequestFailed(path, response, payload)` — lança erro com mensagem localizada para status ≥ 400; marca `nonFatal` em 502/503/504 e bootstrap paths

**Dependentes de estado (`__EPI_APP_STATE__.token`):**
- `buildApiHeaders(options)` — monta headers HTTP com `Authorization: Bearer <token>`

**Pipeline de fetch:**
- `parseApiPayload(response)` — parse JSON/text; normaliza erros 4xx/5xx e gateway HTML
- `requestApiResponse(path, options)` — executa `fetch` com `buildApiHeaders`; normaliza erros de rede
- `apiFetch(path, options)` — pipeline completo: fetch → parse → validate → throw; unwrap `{ ok, data }`
- `apiFetchOptional(path, options)` — wrapper de `apiFetch` que captura erros e retorna `{ ok, payload/error }`
- `apiFetchWithRetry(path, options, config)` — retry exponential backoff para 502/503; até 4 tentativas

Nota: as funções em `app.js` (`api`, `apiOptional`, `apiWithBootstrapRetry`) mantêm seus
nomes originais. O módulo as expõe como `apiFetch`/`apiFetchOptional`/`apiFetchWithRetry`
para evitar colisão com outras libs que usem `api` como global.

**Testes:** 14 novos (funções puras + buildApiHeaders + waitMs).

### Fase 5 — Router SPA (✓ Parcialmente Completa)

**Arquivo criado:** `static/js/modules/router.js`

**Escopo desta fase:** funções puras de URL que não dependem de `refs` (objeto de
referências DOM privado do IIFE de `app.js`).

**Funções puras extraídas:**
- `resolveViewFromLocation()` — lê `?view=<name>` do `location.search`
- `buildNavigationUrl(view)` — constrói URL com `?view=` atualizado; preserva demais params

**Por que as demais funções ficam em `app.js`?**
`showView`, `navigateToView`, `runSpaPartialNavigation`, `bindSpaNavigationHistory`,
`handleLogin` e `renderAll` dependem de `refs.*` (private `const refs = {}` do IIFE de
`app.js`). Extraí-las requer primeiro externalizar `refs` — planejado para a próxima fase
junto com a extração das views individuais (Fase 6).

**Testes:** 5 novos (resolveViewFromLocation + buildNavigationUrl com params e edge cases).

**Testes totais:** 51 JS (19 novos nas Fases 4/5) + 760 Python passam.

### Fase 6 — Módulos de View

Extração progressiva de cada view em arquivo próprio:

| View | Arquivo | Prioridade |
|------|---------|-----------|
| Dashboard | `js/views/dashboard.js` | Alta |
| EPIs | `js/views/epis.js` | Alta |
| Estoque | `js/views/stock.js` | Alta |
| Entregas | `js/views/deliveries.js` | Média |
| Colaboradores | `js/views/employees.js` | Média |
| Compras | `js/views/purchases.js` | Média |
| Relatórios | `js/views/reports.js` | Baixa |
| Configuração | `js/views/settings.js` | Baixa |

### Fase 7 — Linting e Tipagem

**Arquivos a criar:**
- `static/js/.eslintrc.json` — regras de linting
- `static/js/jsconfig.json` — type checking via JSDoc

**ESLint config:**
```json
{
  "env": { "browser": true, "es2021": true },
  "extends": ["eslint:recommended"],
  "rules": {
    "no-var": "error",
    "prefer-const": "error",
    "eqeqeq": ["error", "always"],
    "no-unused-vars": "warn"
  }
}
```

## Estratégia de Compatibilidade

### Guard Padrão para app.js

Após cada extração, em app.js:

```javascript
// Antes: declaração inline
const STORAGE_KEYS = Object.freeze({ session: 'epi-session-v4', ... });

// Depois: verificação + fallback
if (typeof globalThis.STORAGE_KEYS === 'undefined') {
  // Módulo static/js/core/constants.js não foi carregado
  // Fallback inline para compatibilidade
  globalThis.STORAGE_KEYS = Object.freeze({ session: 'epi-session-v4', ... });
}
const STORAGE_KEYS = globalThis.STORAGE_KEYS;
```

### Carregamento dos Novos Módulos

Os arquivos `static/js/core/*.js` e `static/js/utils/*.js` devem ser referenciados em `index.html` **antes** de `app.js`:

```html
<!-- NOVO: Módulos core (carregados antes de app.js) -->
<script src="/js/core/constants.js?v=20260614"></script>
<script src="/js/core/permissions.js?v=20260614"></script>
<script src="/js/core/feature-flags.js?v=20260614"></script>
<script src="/js/core/config.js?v=20260614"></script>
<script src="/js/utils/debug.js?v=20260614"></script>

<!-- Existente -->
<script src="/app.js?v=20260614"></script>
```

## Métricas de Sucesso

| Métrica | Atual | Meta |
|---------|-------|------|
| Tamanho de app.js | 758 KB | < 200 KB |
| Linhas em app.js | 15.129 | < 4.000 |
| Módulos isolados | 0 | ≥ 15 |
| Cobertura de linting | 0% | 100% |
| Testes unitários JS | 0 | ≥ 20 |

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Quebra de ordem de carregamento | Média | Guards de verificação em cada módulo |
| Variável global não encontrada | Baixa | Fallback inline em app.js |
| Teste de sintaxe falha | Baixa | CI valida sintaxe via `test_js_syntax.py` |
| Regressão de feature flag | Baixa | Flags independentes de localização do código |

## Cronograma Estimado

| Fase | Estimativa | Dependências |
|------|-----------|-------------|
| Fase 1 (Constantes) | ✓ Completa | — |
| Fase 2 (Utilitários) | 3–5 dias | Fase 1 |
| Fase 3 (Auth) | 3–5 dias | Fase 2 |
| Fase 4 (API Client) | 2–3 dias | Fase 2 |
| Fase 5 (Router) | 2–3 dias | Fase 3, 4 |
| Fase 6 (Views) | 10–15 dias | Fase 3, 4, 5 |
| Fase 7 (Linting) | 2–3 dias | Fase 1+ |
