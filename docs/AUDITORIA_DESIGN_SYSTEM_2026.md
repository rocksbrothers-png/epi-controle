# Auditoria do Design System — EPI Controle (2026-06)

> Auditoria **grounded no código real** deste repositório. Substitui notas
> anteriores que descreviam o projeto-mock interno da ferramenta claude.ai/design
> (92 tokens / 21 cards / 2 UI kits / JetBrains Mono upload) — esse material
> **não corresponde a este codebase** e não foi usado como base.

## 0. Escopo e princípio

Evoluir UI/UX para padrão **Enterprise** (referência: SAP Fiori, Microsoft
Fluent, IBM Carbon, Material Design 3) **sem alterar a lógica de negócio**.
Mudanças permitidas: UI, CSS, componentes reutilizáveis e Design System.

## 1. Estado real (duas frentes)

O produto tem **duas UIs** com maturidades diferentes de Design System:

### 1a. Web SPA (`static/`) — vanilla JS + `static/styles.css` (~3.3k linhas)
Build do shell: `scripts/build_index.py` monta `static/index.html` a partir de
`static/views/*` e injeta cache-buster por hash de conteúdo (`__ASSET_VERSION__`).

**Já existia e está bom:**
- Tokens semânticos: cores, `--radius-*`, `--shadow-*` (xs→lg), `--transition-*`, soft-variants.
- Tipografia racionalizada (h1–h4, eyebrow, lead), Inter como fonte base.
- Componentes: `btn` (primary/secondary/danger/ghost/sm/lg/**loading**), `badge`
  (status, role, EPI, expiring/expired), `card`, `field`/`form-grid`/`field-error-msg`,
  sidebar com active state, topbar, breadcrumb (`hierarchy-*`), **toast**
  (`epi-toast-container`), **skeleton** (`.skeleton*`), **modal** (`modal-overlay`/
  `modal-card`/`modal-close-btn`), KPI cards e **mini-bar charts** no dashboard,
  signature pad, alert-critical-pulse.
- `@media print` já cobre ocultar sidebar/topbar/toasts e formatar tabelas/cards.
- `@media (prefers-reduced-motion)` respeitado em vários blocos.

### 1b. App Flutter (`flutter/packages/epi_design`) — **mais maduro**
- Material 3 (`useMaterial3: true`), temas **claro e escuro** completos.
- Tokens: `breakpoints.dart`, `spacing.dart`, `colors.dart`, `typography.dart`.
- Biblioteca de componentes (atoms→organisms): button, chip, avatar, input,
  divider, badge; card, search_bar, form_field, status_row, kpi_card; app_bar,
  **stepper**, **timeline**, **empty_state**, data_table, modal, signature_pad,
  sidebar; patterns: **loading_skeleton**, **toast**, **error_boundary**;
  layouts: app_shell, auth_layout.

**Conclusão:** o Flutter já está próximo de Enterprise. A **web SPA** era a
frente atrás — faltavam tokens nomeados de fundação e vários componentes de
estado/navegação que o Flutter já tinha. Parte disso foi corrigida neste ciclo.

## 2. Entregue neste ciclo (web SPA)

Camada **aditiva** ao final de `static/styles.css` (`ENTERPRISE DESIGN SYSTEM LAYER`),
sem remover nem sobrescrever regras existentes — risco de regressão mínimo.
`index.html` rebuildado (`build_index.py build` + `check` OK).

**Tokens de fundação adicionados:**
- Escala de espaçamento `--space-0…16` (base 4px).
- Movimento `--duration-fast/base/slow`, `--ease-default/in/out/emphasized`.
- Z-index nomeado `--z-base/sticky/dropdown/overlay/drawer/modal/toast/tooltip`
  (alinhado ao `.modal-overlay` legado em z-index:200).
- Breakpoints como fonte única `--bp-sm/md/lg/xl` (640/768/1080/1280).
- Acessibilidade: `--focus-ring`, `--control-h` (36/44px alvo de toque).

**Acessibilidade:** anel `:focus-visible` global para botões, links, inputs,
`menu-link` e `[role=button]` (complementa os pontuais já existentes).

**Tema escuro (opt-in):** `[data-theme="dark"]` remapeia tokens semânticos +
`color-scheme: dark`. **Não muda a aparência atual** até alguém setar o atributo
no `<html>` — estrutura pronta para rollout, paridade conceitual com o Flutter.

**Componentes reutilizáveis novos (namespaced `.ds-*`, sem colisão):**
`ds-spinner`, `ds-empty`, `ds-error-state`, `ds-drawer` (+ backdrop, left),
`ds-stepper`, `ds-timeline`, `ds-pipeline` (status solicitado→aprovado→entregue→
assinado), `ds-pagination`, `ds-alert-banner` (+ danger), `ds-tooltip`,
utilitário `ds-tnum` (tabular-nums em tabelas). Todos respeitam
`prefers-reduced-motion`.

## 3. Backlog priorizado (rumo a Enterprise)

Legenda: **P0** crítico · **P1** alto · **P2** médio · **P3** baixo.
`[web]` SPA · `[flutter]` app · `[ambos]` paridade.

### P0 — Crítico  ·  *atendido neste ciclo (PR de wiring)*
- [x] **P0-1 [web]** Feedback pós-ação via `showToast` — infra existente
      (`ui-helpers.js`, `role=status/alert`) já usada nas ações de API.
- [x] **P0-2 [web]** `dsConfirm` (modal acessível, variant danger/warning) substitui
      `window.confirm` nos 5 pontos destrutivos de `app.js` (remover usuário, excluir
      entidade de registro, expiração/purge, fornecedor, vínculos de compra).
- [x] **P0-3 [web]** Declaração de identidade obrigatória no `signature-modal`
      (checkbox NR-6 + gate no confirm). Primitivo `dsConfirm({challenge})` pronto
      para desafio matrícula/CPF quando o backend expuser o dado.
- [~] **P0-4 [web]** Justificativa obrigatória na rejeição **já enforced** em
      `feedback.js` (`if (!justification)`) e aprovação item-a-item em `purchases.js`.
      Falta unificar numa tela única de Aprovação/Rejeição (follow-up).
- [x] **P0-5 [web]** `dsStatusPipeline` aplicado ao ciclo do EPI no portal do
      colaborador (solicitado→aprovado→entregue→assinado). Estender à ficha/entrega admin (follow-up).
- [x] **P0-6 [web]** `dsAlertBanner` (danger) no topo dos alertas do dashboard quando
      há estoque crítico / CA vencendo. CTA direto para compra: follow-up.

> Primitivos reutilizáveis adicionados em `static/js/views/ui-helpers.js` (node-testáveis):
> `dsConfirm`, `dsStatusPipeline`, `dsAlertBanner`, `dsChallengeMatches`, `dsEsc` —
> cobertos por 6 novos testes (95 testes JS no total).

### P1 — Alto
- [~] **P1-1 [web]** Helpers `dsPaginate` + `dsPaginationControls` (puros, 3 testes) +
      barra `.ds-pagination-bar`. Cabeada na tabela de **Entregas** (alta volumetria,
      20/página, reset ao filtrar). Estender a colaboradores/usuários e migrar para
      paginação server-side (`?page=&limit=`) — follow-up.
- [~] **P1-2 [web]** Helpers `dsTableState` (empty/error/loading) + `dsSkeletonRows`
      em `ui-helpers.js` (4 testes). Cabeados em usuários, entregas, fichas arquivadas,
      logs de ficha, EPIs, fornecedores (empty+error) e POs de fornecedor (loading).
      Falta cobrir as tabelas restantes (avaliações, hierarquia, etc.) — follow-up.
- [x] **P1-3 [web]** Sidebar agrupada (Visão geral / Cadastros / Operação / Análise),
      com ocultação de rótulos de grupo sem itens visíveis. *(PR #662)*
- [x] **P1-4 [web]** Badge de empresa/unidade ativa sempre visível no topbar
      (`#topbar-company-badge`, multi-tenant). *(PR #662)*
- [x] **P1-5 [web]** `dsStepper` no detalhe da PO (Pedido→Recebido→Conferido→Fechado),
      mapeado a partir do status real da PO. Helper puro + 2 testes.
- [~] **P1-6 [web]** `dsTimeline` aplicado ao **histórico de eventos da PO** (substitui
      a lista textual). Helper puro + 2 testes. Estender ao histórico do colaborador
      (entregas/devoluções/trocas) — follow-up.
- [~] **P1-7 [web]** Helper `dsFilterChips` (puro, 2 testes) + barra `.ds-filter-bar`.
      Cabeada na view de **Entregas**: chips removíveis dos filtros opcionais
      (colaborador, EPI, datas, status) + "Limpar filtros". **Não** expõe os filtros
      de escopo (empresa/unidade) para não burlar o multi-tenant. Estender às demais views — follow-up.
- [x] **P1-8 [web]** Auditoria de contraste AA dos tokens. `--muted` escurecido de
      `#66726b` → `#5c6760` (sobre `--bg`: 4.09→**4.80**; sobre painel: 5.67 — passa AA texto normal).
      Tema escuro já passa (7.25/6.45). `--accent`/`--warning` reprovam só para texto
      *normal* mas são usados em texto grande/bold/badges (AA-large ✓) — mantidos por
      serem cor de marca; documentados.

> **Faixa P1 concluída** (PRs #662–#666 + este). Componentes DS cabeados com pilotos
> em alta-volumetria/segurança; extensões às demais views ficam como follow-up incremental.

### P2 — Médio
- [~] **P2-1 [web]** Controller `dsOpenDrawer`/`dsCloseDrawer` (`.ds-drawer`, fecha em
      ✕/backdrop/Esc, foco gerenciado). Cabeado como botão **"Detalhes"** nas linhas de
      Entrega: abre o drawer com os dados da entrega + pipeline de status, sem mudar de
      rota. Estender a colaborador/EPI/outras tabelas — follow-up. *(requer revisão visual)*
- [~] **P2-2 [web]** Pré-requisito do dark mode em andamento. **Passo 1 feito:**
      definidos os 14 aliases `--color-*` (antes referenciados ~150× mas **indefinidos**
      → cor herdada/transparente) mapeando para os tokens semânticos. Corrige bugs
      latentes (ex.: texto `--color-danger` não ficava vermelho) e faz o tema escuro
      valê-los por cascata de `var()`. **Passo 2 feito:** toggle exposto no topbar
      (opt-in, padrão claro, persistido em `localStorage['epi-theme']`, bootstrap inline
      no `<head>` sem flash). **Passo 3 feito:** novos tokens semânticos `--info`/`--pending`
      (+`-soft`) e `--muted-soft`; literais frios do **portal do colaborador**,
      **feedback-detail** e **avaliações** migrados para tokens. Badges de status
      refatorados de `bg sólido + texto branco` → `bg soft + texto colorido`
      (theme-safe, padrão consistente). Mantido só o gradiente decorativo do hero do
      portal (texto branco, theme-agnostic). **Falta:** demais telas admin com literais
      inline pontuais — follow-up. (Flutter já tem `theme_mode_notifier`.)
- [~] **P2-3 [web]** Sidebar colapsável (mobile-menu-toggle) e scroll horizontal de
      tabelas (`.table-wrap { overflow-x: auto }` + `min-width`) já existiam. **Adicionado:**
      alvos de toque ≥44px (`--control-h-lg`) em controles primários no mobile (≤768px)
      + scroll com inércia. Ajuste fino visual de telas específicas — follow-up (revisão visual).
- [~] **P2-4 [web]** Validadores puros `dsValidateCNPJ` + `dsIsDateNotPast` e helpers
      `dsSetFieldError`/`dsClearFieldError` (4 testes) + estilo `[aria-invalid]`.
      Cabeado no CNPJ do formulário de Empresa (valida no blur, limpa ao reeditar).
      Estender a CA/datas e demais formulários — follow-up.
- [ ] **P2-5 [ambos]** Relatórios com filtros período/empresa + export, e Logs de auditoria (actor, timestamp, ação).
- [x] **P2-6 [web]** `scope="col"` em **280** `<th>` de todos os fragmentos de view;
      `aria-label` nos botões icon-only (✕ fechar/remover) estáticos e gerados.
      `role="status"/"alert"` nos toasts já existia. Headers de tabelas geradas via
      template em `app.js` — follow-up incremental.

### P3 — Baixo
- [ ] **P3-1 [web]** Fonte mono real: hospedar JetBrains Mono local (`.woff2` + `@font-face`) ou remover a referência em `code,pre` deixando só o fallback. Hoje renderiza o fallback (`Fira Code`/`Courier New`).
- [ ] **P3-2 [web]** `@media print` dedicado para ficha de EPI e relatórios (refinar além do bloco genérico atual).
- [ ] **P3-3 [web]** `ds-tooltip` aplicado ao glossário (siglas de NR, tipos de CA).
- [ ] **P3-4 [web]** Recuperação de senha — a UI já existe no login; revisar estados de erro/loading.
- [ ] **P3-5 [ambos]** `ds-tnum`/tabular-nums em todos os valores numéricos de tabelas (já em stats).

## 4. Riscos e notas
- Toda mudança CSS desta frente é **aditiva** e namespaced; não altera classes em uso.
- Após mexer em qualquer JS/CSS de `static/`, rodar `python scripts/build_index.py build`
  (atualiza o cache-buster) e `... check` (garante sincronia do `index.html`).
- A frente Flutter já tem a maioria dos componentes; o esforço Enterprise concentra-se
  na **web SPA** e na **paridade de comportamento** (não de pixel) entre as duas.
