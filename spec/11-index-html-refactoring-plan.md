# Plano de Refatoração do index.html — EPI SaaS

## Objetivo

Decompor o `static/index.html` monolítico (~2.592 linhas) em fragmentos
modulares editáveis por view, **sem nenhuma mudança de comportamento em
runtime** e mantendo o arquivo servido byte-idêntico.

## Princípios (AGENTS.md)

1. **Não alterar lógica existente** — apenas reorganizar a estrutura.
2. **Manter compatibilidade total** — o `index.html` servido permanece idêntico.
3. **Separação por módulos** — uma view por arquivo.
4. **Reversível e verificável** — round-trip byte-idêntico garantido por teste.

## Estratégia: Montagem em Build-Time

Como o projeto não possui bundler para HTML e o `app.js` faz binding direto no
DOM no carregamento, qualquer injeção assíncrona de fragmentos introduziria
condições de corrida. A abordagem escolhida é **assemblagem em build-time**:

```
static/views/_layout.html   ← casca (head, login, sidebar, topbar, modais, scripts)
static/views/<view>.html    ← 15 fragmentos de view (um por seção)
        │
        ▼  scripts/build_index.py build
static/index.html           ← gerado, byte-idêntico ao original
```

O layout contém marcadores de inclusão (`<!-- EPI_VIEW_INCLUDE:<id> -->`) na
posição exata onde cada `<section id="<id>-view">` ficava. O build substitui
cada marcador pelo conteúdo do fragmento correspondente.

### Garantia de byte-identidade

O processo é, por construção, um simples fatiamento e rejunção do texto
original: cada fragmento é uma fatia contígua de linhas entre a abertura de uma
view e a abertura da próxima (a última via contagem de profundidade de
`<section>`/`</section>`). Portanto `pre + frag₀ + frag₁ + … + post == original`.

## Estrutura de Fragmentos

| Fragmento | Linhas (aprox.) | View |
|-----------|-----------------|------|
| `views/dashboard.html` | 63 | Dashboard / KPIs |
| `views/empresas.html` | 61 | Empresas (multi-tenant) |
| `views/comercial.html` | 149 | Comercial / contratos |
| `views/usuarios.html` | 80 | Usuários |
| `views/unidades.html` | 24 | Unidades |
| `views/colaboradores.html` | 86 | Cadastro de colaborador |
| `views/gestao-colaborador.html` | 49 | Gestão de colaborador |
| `views/epis.html` | 109 | Cadastro de EPI |
| `views/entregas.html` | 163 | Entrega de EPI |
| `views/estoque.html` | 279 | Controle de estoque |
| `views/fichas.html` | 45 | Ficha de EPI |
| `views/configuracao.html` | 173 | Configuração |
| `views/compras.html` | 537 | Compras (solicitação/pedido) |
| `views/relatorios.html` | 48 | Relatórios |
| `views/avaliacoes.html` | 379 | Avaliações e sugestões |
| `views/_layout.html` | 347 | Casca (não-view) |

## Comandos

```bash
# Reconstruir index.html após editar fragmentos
python scripts/build_index.py build

# Verificar sincronia (usado no CI / teste)
python scripts/build_index.py check

# Re-extrair fragmentos a partir do index.html (raro)
python scripts/build_index.py extract
```

## Guarda de Drift (CI)

`tests/test_index_html_build.py` roda o modo `check` e falha se o `index.html`
divergir dos fragmentos. Isso impede que alguém edite só o `index.html` (ou só
um fragmento) e deixe os dois fora de sincronia.

**Fluxo de edição correto:**
1. Editar `static/views/<view>.html`
2. Rodar `python scripts/build_index.py build`
3. Commitar fragmento + `index.html` juntos

## Fases

### Fase 1 — Extração de Views (✓ Completa)

- [x] Script `scripts/build_index.py` (extract/build/check)
- [x] 15 fragmentos de view + `_layout.html`
- [x] Round-trip byte-idêntico verificado
- [x] Teste de guarda `tests/test_index_html_build.py`
- [x] Integração dos módulos JS core/utils no `_layout.html` (antes de app.js)

### Fase 2 — Decomposição da Casca (✓ Completa)

O `_layout.html` foi decomposto em 6 sub-fragmentos via
`python scripts/build_index.py split-layout`. O `_layout.html` ficou reduzido a
um esqueleto de marcadores (`<!-- EPI_SHELL_INCLUDE:* -->` + `<!-- EPI_VIEW_INCLUDE:* -->`).

| Sub-fragmento | Linhas | Conteúdo |
|---------------|--------|----------|
| `views/_head.html` | 12 | `<head>` (meta, CSP, links) + `<body>` |
| `views/_login.html` | 92 | Tela de login + recuperação de senha |
| `views/_sidebar.html` | 79 | `<section main-screen>` + navegação lateral |
| `views/_topbar.html` | 38 | `<main main-content>` + topbar + banners |
| `views/_modals.html` | 63 | Fechamento do conteúdo + modais globais |
| `views/_scripts.html` | 71 | Bloco de `<script>` + `</body></html>` |

Round-trip byte-idêntico verificado; `index.html` servido inalterado.

### Fase 3 — Sub-fragmentos de Modais por Domínio (✓ Completa)

Modais embutidos nas views grandes foram extraídos para `static/views/modals/`
via `python scripts/build_index.py split-modals`. A extração usa contagem de
profundidade de `<div>`/`</div>` e é byte-idêntica.

| Modal | Linhas | View origem |
|-------|--------|-------------|
| `modals/aval-action-modal.html` | 139 | avaliacoes |
| `modals/modal-supplier-pos.html` | 27 | compras |
| `modals/aprovacoes-reprovar-modal.html` | 21 | compras |
| `modals/modal-edit-supplier.html` | 17 | compras |
| `modals/aprovacoes-prorrogar-modal.html` | 12 | compras |

Redução: `compras` 537 → 460 linhas; `avaliacoes` 379 → 240 linhas.
O `_assemble()` expande os marcadores `<!-- EPI_MODAL_INCLUDE:<id> -->` após
inserir as views.

### Fase 4 — Geração no Deploy

Integrar `build_index.py build` ao pipeline de deploy (Dockerfile) para que o
`index.html` seja sempre gerado a partir da fonte modular, eliminando a
necessidade de commitar o arquivo gerado.

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Drift entre fragmentos e index.html | Teste `check` no CI |
| Regressão de runtime | Build byte-idêntico (verificado) |
| Ordem de scripts quebrada | Scripts ficam no `_layout.html`, ordem preservada |
| Marcador acidentalmente removido | `test_layout_has_all_include_markers` |

## Métricas

| Métrica | Antes | Depois (Fases 1–3) |
|---------|-------|--------------------|
| Maior arquivo HTML editável | 2.592 linhas | 460 linhas (compras) |
| Arquivos de view isolados | 0 | 15 |
| Sub-fragmentos de casca | 0 | 6 |
| Modais extraídos | 0 | 5 |
| Round-trip verificado | — | Sim |
| Guarda de CI | — | Sim |
