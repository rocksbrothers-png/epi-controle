# Frontend JavaScript — EPI SaaS

## Visão Geral

O frontend web legado é uma SPA (Single Page Application) em **JavaScript vanilla** sem bundler ou framework. Os scripts são servidos diretamente pelo Python como arquivos estáticos em `/static/`.

## Inventário de Arquivos JS

| Arquivo | Tamanho | Responsabilidade |
|---------|---------|-----------------|
| `app.js` | 758 KB / ~15.129 linhas | Bundle principal — entrada da aplicação |
| `app.v20260326.js` | 141 KB | Versão legada em manutenção |
| `i18n.js` | 7.8 KB | Motor de internacionalização |
| `i18n-helper.js` | 849 B | Adaptador legado de i18n |
| `navigation.js` | 11 KB | Navegação hierárquica (Phase 4.6) |
| `navigation-controls.js` | 15 KB | Controles de navegação UI |
| `multitab-navigation.js` | 17 KB | Suporte a navegação multi-aba |
| `error-monitor.js` | 10 KB | Monitoramento de erros e rollback |
| `ux-global.js` | 8.6 KB | UX global unificada (Phase 4.4+) |
| `ux-phase41.js` | 17 KB | Módulo UX Phase 4.1 |
| `ux-phase42.js` | 19 KB | Módulo UX Phase 4.2 |
| `ux-phase43.js` | 20 KB | Módulo UX Phase 4.3 |
| `ux-phase44.js` | 22 KB | Módulo UX Phase 4.4 |
| `ux-analytics.js` | 18 KB | Analytics e telemetria |
| `tenant-init.js` | 12 KB | Inicialização de tenant/white-label |
| `share-modal.js` | 2.5 KB | Modal de compartilhamento |
| `colab-list.js` | 4.5 KB | Lista de colaboradores (HTMX) |
| `gestao-colab.js` | 4.6 KB | Gestão de colaborador (HTMX) |
| `entrega-epi.js` | 12 KB | Entrega de EPI (HTMX) |
| `estoque.js` | 4.6 KB | Controle de estoque (HTMX) |

## Padrões Adotados

### IIFE (Immediately Invoked Function Expression)

Todos os módulos usam IIFE para isolamento de escopo:

```javascript
(function () {
  'use strict';

  // código do módulo
  // exporta via globalThis.__EPI_MODULE_NAME__ ou window.*

})();
```

### Guard de Duplo-Carregamento

```javascript
// Padrão para módulos que não devem ser carregados mais de uma vez
if (!globalThis.__EPI_MODULE_LOADED__) {
  globalThis.__EPI_MODULE_LOADED__ = true;
  // ...código do módulo
}

// Padrão alternativo (para módulos menores)
if (globalThis.__EPI_MODULE_BOUND__) return;
globalThis.__EPI_MODULE_BOUND__ = true;
```

### Comunicação entre Módulos

Via `globalThis` / `window`:
- `globalThis.__EPI_FRONTEND_HELPERS__` — helpers compartilhados
- `globalThis.__EPI_APP_STATE__` — estado global da aplicação
- `globalThis.EpiI18n` — motor de i18n
- `globalThis.trEpi(key)` — função de tradução global
- `globalThis.__EPI_VIEW_STACK__` — pilha de navegação

### Feature Flags no Frontend

```javascript
// Leitura de flag
const enabled = helpers.getFeatureFlag('ux_phase41_enabled', { 
  defaultValue: false, 
  allowStorage: true 
});

// Fontes de flags (por prioridade):
// 1. localStorage ('ux_phase41_enabled' === '1')
// 2. Query param (?ux_phase41=1)
// 3. defaultValue
```

## Estrutura do app.js (Seções Principais)

O `app.js` é o bundle monolítico que contém, em ordem:

1. **Guard de carregamento** (`__EPI_APP_RUNTIME_LOADED__`)
2. **Constantes** — `STORAGE_KEYS`, `ROLE_LABELS`, `ROLE_ALIASES`
3. **Permissões** — `ROLE_PERMISSIONS`, `VIEW_PERMISSIONS`, `VIEW_EYEBROW`
4. **Feature Flags** — `UX_FRONTEND_FLAGS`, `FEATURE_FLAG_DEFINITIONS`, matrizes de rollout
5. **Configuração padrão** — `DEFAULT_CONFIGURATION_FRAMEWORK`, `DEFAULT_COMMERCIAL_SETTINGS`
6. **Debug e Perf** — `debugLog`, `EPI_PERF_RUNTIME`, `markRenderStart/End`
7. **Storage Utils** — `safeStorageRead`, `safeStorageWrite`, `queueStorageWrite`
8. **DOM Utils** — `safeOn`, `isViewActive`, `resolveFormFieldAutocomplete`
9. **Módulo de Auth** — login, logout, validação de sessão, token refresh
10. **Módulo de API** — `apiFetch`, interceptors, error handling
11. **Módulo de Navegação** — roteamento SPA, histórico de navegação
12. **Módulos de Render** — renderização de cada view (dashboard, epis, estoque, etc.)
13. **Bootstrap** — inicialização da aplicação, carregamento de scripts auxiliares

## Dependências Externas

Carregadas via CDN com SRI no `index.html`:
- Nenhuma dependência JS de terceiros no bundle principal
- HTMX (opcional, controlado por feature flag)
- Alpine.js (opcional, controlado por feature flag)

## Estado da Aplicação

```javascript
// globalThis.__EPI_APP_STATE__ shape
{
  user: {
    id: 'uuid',
    name: 'string',
    email: 'string',
    role: 'admin',
    company_id: 'uuid',
    unit_id: 'uuid | null'
  },
  company: {
    id: 'uuid',
    name: 'string',
    logo_type: 'string',
    plan: 'string'
  },
  permissions: ['dashboard:view', 'epis:view', ...],
  featureFlags: {},
  currentView: 'dashboard'
}
```

## Modo de Diagnóstico

Ativado via `localStorage.epi_diagnostic_mode_enabled = '1'`:
- Logs detalhados no console
- HUD de performance em overlay
- Rollback automático após múltiplos erros

## Limitações Conhecidas

1. **Bundle monolítico**: `app.js` com 15.129 linhas dificulta manutenção
2. **Sem bundler**: impossível usar ES modules, tree-shaking, minificação eficiente
3. **`var` e `function` globais**: poluição do escopo global
4. **Sem type checking**: ausência de TypeScript ou JSDoc consistente
5. **Sem linter formal**: regras de estilo inconsistentes entre arquivos
6. **Testes**: sem testes unitários JS (apenas `test_js_syntax.py` valida sintaxe)

Ver `spec/10-js-refactoring-plan.md` para o plano de modernização.
