# EPI Controle — Design System (referência)

Referência **auto-contida** do Design System do EPI Controle, exportada a partir
dos componentes que já estão em produção (`static/styles.css` + módulos `static/js`).
Cada arquivo é HTML estático que abre direto no navegador; todos compartilham
`tokens.css` (cores/espaçamento/etc.) e `components.css` (estilos `.ds-*`).

> **Tema:** cada preview tem um botão **🌓 tema** que alterna claro/escuro
> (`<html data-theme="dark">`), demonstrando a compatibilidade dos tokens.

## Estrutura

```
project/
├── tokens.css                 # Design tokens (claro + dark) — fonte de verdade
├── components.css             # Estilos dos componentes .ds-* + base (btn/badge/card)
├── index.html                 # Galeria com links para todos os previews
├── preview/
│   ├── component-toast.html
│   ├── component-modal.html
│   ├── component-status-pipeline.html
│   ├── component-alert-banner.html
│   ├── component-empty-state.html
│   ├── component-pagination.html
│   ├── component-loading-skeleton.html
│   └── component-filter-bar.html
└── ui_kits/
    ├── login/index.html       # Tela de login
    └── admin/index.html       # Shell admin (sidebar agrupada + topbar + dashboard)
```

## Mapa componente → implementação em produção

| Preview | Implementação (produção) |
|---|---|
| `component-toast` | `showToast()` em `static/js/views/ui-helpers.js` |
| `component-modal` | `dsConfirm()` (+ gate de identidade na assinatura) |
| `component-status-pipeline` | `dsStatusPipeline()` |
| `component-alert-banner` | `dsAlertBanner()` — fixo no topo do dashboard |
| `component-empty-state` | `dsTableState({kind:'empty'\|'error'})` |
| `component-pagination` | `dsPaginate()` + `dsPaginationControls()` |
| `component-loading-skeleton` | `dsSkeletonRows()` / `.skeleton` |
| `component-filter-bar` | `dsFilterChips()` |
| `ui_kits/login` | `static/views/_login.html` |
| `ui_kits/admin` | `_sidebar.html` + `_topbar.html` + `dashboard.html` |

## Tokens semânticos

`--success`, `--warning`, `--danger`, `--info`, `--pending` (+ variantes `-soft`),
mais a paleta de marca `--accent` (terracotta). Aliases `--color-*` para
compatibilidade. Tudo remapeado sob `[data-theme="dark"]`.

## Convenção de cards

Cada preview começa com `<!-- @dsCard group="…" name="…" subtitle="…" -->` na
primeira linha — compatível com o índice do Design System do Claude Design.
