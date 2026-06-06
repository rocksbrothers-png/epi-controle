# Decisões de Arquitetura — EPI Controle (Flutter)

> Documento oficial de decisões (ADR consolidado) para o app `epi_admin` e os
> packages do monorepo (`epi_design`, `epi_api`, `epi_i18n`).
> Cada seção é uma decisão **vigente**. Mudanças exigem PR alterando este arquivo.

Última atualização: 2026-06-05

---

## 1. Idiomas oficiais do MVP

**Decisão:** o MVP suporta **5 idiomas oficiais**, todos tratados como
_first-class_ e mantidos **100% completos** (mesmo conjunto de chaves):

| Locale  | Idioma                  |
|---------|-------------------------|
| `pt_BR` | Português (Brasil) — **template** |
| `en_US` | Inglês (EUA)            |
| `es_ES` | Espanhol (Espanha)      |
| `fr_FR` | Francês (França)        |
| `no_NO` | Norueguês (Noruega)     |

- O template/idioma de referência é **`pt_BR`**. Toda nova chave nasce aqui.
- Nenhum locale pode ficar incompleto: o CI falha se faltar qualquer chave
  (`tool/validate_arb.py`).
- Fallback de runtime: `pt_BR`. A escolha do usuário é persistida
  (`LocaleProvider` + `FlutterSecureStorage`, chave `user_locale`).
- **Exceção de tradução documentada:** autônimos de idioma no seletor de
  Configurações (`Português (BR)`, `English (US)`, `Español`, `Français`,
  `Norsk`) **não são traduzidos** — convenção universal de seletores de idioma.
  Registrados em `tool/i18n_hardcoded_allowlist.txt`.

---

## 2. Estratégia oficial de l10n

**Decisão:** `flutter gen-l10n` com **`output-dir`** (arquivos gerados
versionados no repositório). **Não** usamos o package `flutter_gen`.

### Layout

```
packages/epi_i18n/lib/l10n/           ← fonte da verdade (ARBs)
  app_pt_BR.arb   (template)
  app_en_US.arb  app_es_ES.arb  app_fr_FR.arb  app_no_NO.arb
  app_en.arb …    (aliases language-only — só metadata, apontam p/ o regional)

apps/epi_admin/lib/core/i18n/generated/   ← Dart gerado (versionado)
  app_localizations.dart                   (classe abstrata + delegate)
  app_localizations_{pt,en,es,fr,no}.dart  (implementações por locale)
```

### Configuração (`apps/epi_admin/l10n.yaml`)

```yaml
arb-dir: ../../packages/epi_i18n/lib/l10n
template-arb-file: app_pt_BR.arb
output-localization-file: app_localizations.dart
output-class: AppLocalizations
output-dir: lib/core/i18n/generated
nullable-getter: false
use-deferred-loading: true
```

### Regras

- **Import padrão** nos widgets:
  `import 'package:epi_admin/core/i18n/generated/app_localizations.dart';`
  e acesso via `AppLocalizations.of(context)`.
- ARBs aliases (`app_en.arb` etc.) contêm apenas `@@locale`/`@@comment` e
  **redirecionam** para o ARB regional completo. Isso é intencional e
  reconhecido pelo validador.
- Chaves **parametrizadas** (valor com `{placeholder}`) exigem metadata
  `@chave.placeholders` em **todos** os locales.
- Os arquivos Dart gerados são **commitados**. Quando o Flutter SDK estiver
  disponível, regenere com `melos run gen:l10n`. Em ambientes sem SDK, o
  patcher determinístico `tool/_gen_i18n_keys.py` replica exatamente o formato
  do `gen-l10n` (ponte; a fonte da verdade continua sendo os ARBs).

### Gates de CI (sem necessidade de Flutter SDK — falham rápido)

- `tool/validate_arb.py` — mesmas chaves em todos os ARBs, nenhum vazio,
  metadata de placeholders presente.
- `tool/check_hardcoded_strings.sh` — bloqueia strings hardcoded novas
  (`Text('…')`, `label:/labelText:/hintText:/helperText:/tooltip: '…'`).

---

## 3. Shell oficial (app shell único)

**Decisão:** existe **um único** app shell, definido no design system
(`epi_design`), e o app apenas **delega** para ele.

- Componente canônico: `AppShell` em
  `packages/epi_design/lib/layouts/app_shell.dart`.
- O shell do app (`apps/epi_admin/lib/core/shell/app_shell.dart`) é um
  _wrapper_ fino que mapeia a rota atual do GoRouter para o índice e vice-versa
  (`import 'package:epi_design/epi_design.dart' as ds;`).
- **Sem duplicação** de navegação/scaffold entre app e design system.
- Rótulos de navegação **sempre** via `AppLocalizations` (ex.: `l10n.navFeedback`).

### Breakpoints oficiais (`EpiBreakpoints` em `epi_design`)

| Token     | Valor (px) | Uso                          |
|-----------|-----------:|------------------------------|
| `tablet`  | 600        | mobile → tablet              |
| `desktop` | 768        | tablet → desktop (rail/menu) |
| `wide`    | 1200       | desktop → wide               |

Fonte única de verdade — proibido reintroduzir literais `600`/`768`/`1200`
espalhados pelo código.

---

## 4. Web: painel apenas (sem landing page)

**Decisão:** o Flutter Web entrega **somente o painel administrativo**. Não há
landing page / site institucional no escopo do MVP.

- **Co-deploy** com o backend Python (mesma origem). O `Dockerfile` multi-stage
  builda o web e serve junto ao runtime Python — sem CORS, mesma origem.
- Sem SSR e sem SEO de marketing (painel é pós-login, não indexável).
- Itens de robustez web tratados como tarefa dedicada (P1 — Website Strategy):
  fallback de 404 (`errorBuilder`), URLs limpas (`PathUrlStrategy`) e
  PWA básico (`manifest.json`). **Status:** pendente, fora deste PR.

---

## 5. Rotas públicas e privadas

**Decisão:** rotas públicas são uma lista fechada; todo o resto é privado e vive
sob o `ShellRoute`, protegido por `redirect` de autenticação.

### Públicas (sem sessão)

| Rota      | Tela                | Observação                          |
|-----------|---------------------|-------------------------------------|
| `/login`  | `LoginScreen`       | entrada do painel                   |
| `/portal` | `PortalScreen`      | portal do colaborador (CPF/QR)      |
| `/qr`     | `QrScannerScreen`   | leitura de QR                       |

### Privadas (sob `ShellRoute`, exigem sessão)

`/` (dashboard), `/employees` (+`/employees/:id`), `/epis` (+`/epis/:id`),
`/stock`, `/deliveries` (+`/deliveries/new`), `/returns`, `/records`,
`/purchases`, `/reports`, `/settings`, `/companies`, `/users`, `/units`,
`/feedback`.

### Guarda

- `redirect` no GoRouter: sem sessão e fora de `/login` → `/login`; com sessão em
  `/login` → `/` (dashboard). Controlado pela flag `USAR_FLUTTER_LOGIN`
  (default `true`).
- A guarda do frontend é **conveniência de UX**. A autorização real é sempre do
  backend (ver seção 6).

---

## 6. Navegação por permissions (Navigation Matrix) — base para P1

**Decisão:** a navegação do frontend é dirigida por **permissions**, não por
roles.

- As **roles continuam existindo no backend** (`core/roles.py`), mas o frontend
  **não** decide visibilidade por role.
- O menu é montado a partir da **lista de permissões** retornada no
  **login** (`POST /api/login` → campo `permissions`) e no **bootstrap**
  (`GET /api/bootstrap` → `data.permissions`). São strings no formato
  `dominio:acao` (ex.: `deliveries:view`, `purchase_requests:view`).
- **Defesa em profundidade:** nenhuma rota protegida pode depender _apenas_ do
  menu estar oculto. O backend **continua validando** cada permissão em toda
  requisição (`core/permissions.py` / `authorize_action`). Ocultar item de menu
  é UX — **não** é segurança.

### Matriz rota → permissão (a implementar em P1)

| Item de menu / rota | Permissão exigida (mostra item se presente) |
|---------------------|---------------------------------------------|
| `/` Dashboard       | `dashboard:view`                            |
| `/employees`        | `employees:view`                            |
| `/epis`             | `epis:view`                                 |
| `/stock`            | `stock:view`                                |
| `/deliveries`       | `deliveries:view`                           |
| `/returns`          | `deliveries:view`                           |
| `/records` (fichas) | `fichas:view`                               |
| `/purchases`        | `purchase_requests:view`                    |
| `/reports`          | `reports:view`                              |
| `/companies`        | `companies:view`                            |
| `/users`            | `users:view`                                |
| `/units`            | `units:view`                                |
| `/feedback`         | `epi_feedback:view`                         |
| `/settings`         | `settings:view`                             |

> A matriz acima é o contrato. A implementação (ler `permissions` do estado de
> auth e filtrar os itens do `AppShell`) é a tarefa P1 — Navigation Matrix.

---

## 7. Gerência de estado e offline-first (resumo)

- **BLoC/Cubit** (`flutter_bloc`) para estado de tela.
- **Offline-first**: operações de escrita (entrega, devolução) enfileiram em
  `SyncDatabase` (sqflite) quando há falha de rede; `SyncService` reexecuta ao
  reconectar. Estados expõem `offlineQueued` para feedback de UI.
- Detalhes em `ARCHITECTURE.md` e `PATTERNS.md`.

---

## Referências

- `ARCHITECTURE.md` — layout do monorepo, responsabilidades, fluxo de i18n, CI.
- `PATTERNS.md` — padrões de navegação, i18n, componentes, temas, offline.
- `tool/validate_arb.py`, `tool/check_hardcoded_strings.sh` — gates de i18n.
