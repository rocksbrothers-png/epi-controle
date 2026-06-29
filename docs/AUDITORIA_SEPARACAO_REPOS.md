# Auditoria e Plano de Separação — `EPI-CONTROLE` vs `EPI-CONTROLE-APP`

> Documento de diagnóstico, arquitetura-alvo e plano de ação para separar com
> segurança os dois repositórios. **Nada é apagado por esta auditoria** — ela
> apenas lista, justifica e propõe. A execução das remoções só ocorre após
> aprovação explícita, em commits pequenos e reversíveis.
>
> Gerado em 2026-06-29.

---

## TL;DR (resumo executivo)

1. **Os dois repositórios são, hoje, byte-a-byte idênticos.** 834 arquivos
   versionados em cada um, **zero** diferenças de conteúdo. A separação
   conceitual (legado vs SaaS) **ainda não existe** no código — são dois clones
   do mesmo monorepo full-stack.
2. **Não é um "repo Flutter" + "repo web legado".** É **um único monorepo
   full-stack** contendo: backend Python/Flask (`app.py` + `modules/`) que
   **é a API** e também **serve** dois frontends — o web legado em JS puro
   (`static/`, servido em `/`) e o **Flutter Web embutido** (servido em `/app/`).
   O app Flutter **depende** desse backend Python (não fala direto com o
   Supabase). Separar "Flutter pra um repo, Python pra outro" **quebraria o
   SaaS**.
3. **Risco crítico de credenciais cruzadas (item 10 da missão):** `env.example`
   fixa o Supabase **corporativo** (`kkmskwmkhyssrxqbsrqv`) e `render.yaml` fixa
   o serviço `epi-controle`. Se o `EPI-CONTROLE-APP` subir com esses defaults,
   ele usa o **banco e o deploy corporativos**. Esta é a separação mais urgente.
4. **Só existe um projeto Supabase visível** nas credenciais desta sessão:
   `kkmskwmkhyssrxqbsrqv` ("epi-control-system's Project", sa-east-1). O
   "Supabase novo do SaaS" mencionado **não aparece** — precisa ser confirmado
   (ref do projeto + chaves) antes de qualquer configuração.
5. **iOS não está pronto para build local.** Não há `Runner.xcodeproj`,
   `xcworkspace`, `Podfile` nem `AppDelegate`. O projeto Xcode é **gerado em
   tempo de CI** via fastlane (`flutter create . --platforms=ios`). `flutter
   build ios` em máquina limpa **falha** sem esse passo de bootstrap.
6. **Higiene de segredos: boa.** Nenhum `.env`, keystore, `google-services.json`
   ou `GoogleService-Info.plist` versionado. Tudo entra por variáveis de
   ambiente (Render) e `--dart-define` (Flutter).

---

# PARTE 1 — Diagnóstico

## 1.1 Estado atual dos dois repositórios

| Item | `EPI-CONTROLE` | `EPI-CONTROLE-APP` |
|---|---|---|
| Arquivos versionados | 834 | 834 |
| Diferenças de conteúdo | — | **0 (idêntico)** |
| Branch da auditoria | `claude/epi-controle-repo-audit-8qjklb` | `claude/epi-controle-repo-audit-8qjklb` |
| Tamanho (sem `.git`) | ~80 MB | ~80 MB |

Os dois repositórios contêm exatamente a mesma árvore. A divergência de
propósito (corporativo/legado × SaaS) ainda **não foi materializada**.

## 1.2 Mapa atual de pastas (vale para os dois repos hoje)

```
.
├── app.py                  # Backend Flask (1106 linhas) — API + roteamento dos frontends
├── server_postgres.py      # Camada de conexão PostgreSQL
├── requirements.txt        # Deps Python (psycopg2, gunicorn, opencv, pytesseract, …)
├── Dockerfile              # Multi-stage: build Flutter Web → runtime Python (co-deploy)
├── render.yaml             # Blueprint Render (1 serviço web Docker "epi-controle")
├── env.example             # Modelo de variáveis (contém ref Supabase CORPORATIVO)
├── package.json            # Apenas ESLint do JS de static/ (lint do web legado)
├── modules/                # 21 módulos de domínio do backend (auth, tenant, payments…)
│   ├── auth/ tenant/ companies/ employees/ epis/ deliveries/ devolutions/
│   ├── stock/ purchases/ payments/ commercial/ reports/ portal/ ficha/ …
├── epi_backend/            # OCR (Tesseract/manufacture_date_ocr) e utilitários backend
├── core/                   # Núcleo compartilhado backend
├── static/                 # FRONTEND WEB LEGADO (JS puro) — servido em "/"
│   ├── index.html, app.js, styles.css, *.js
│   ├── views/ fragments/ (HTML montado por scripts/build_index.py)
│   ├── js/ (modules, views, core, utils) e i18n/
├── flutter/                # MONOREPO FLUTTER (melos) — servido em "/app/" e mobile
│   ├── melos.yaml, pubspec.yaml
│   ├── apps/epi_admin/      # App: Web + Android + iOS
│   │   ├── lib/ (main.dart, firebase_options.dart, core/, features/)
│   │   ├── android/  ios/  web/  assets/  test/  integration_test/
│   ├── packages/epi_api/    # Cliente HTTP (dio/retrofit) → backend Python
│   ├── packages/epi_design/ # Design system
│   ├── packages/epi_i18n/   # i18n (ARB)
│   └── tool/                # validate_arb.py, check_hardcoded_strings.sh
├── supabase/migrations/     # 10 migrações SQL (RLS hardening, multi-tenant, whitelabel)
├── scripts/                 # build_index.py, check_ocr_runtime.py, auditorias, …
├── spec/  tests/            # specs e 91 testes Python (pytest)
├── project/                 # tokens/previews do design system
├── docs/                    # ~30+ documentos de arquitetura e planos
└── .github/workflows/       # 5 workflows (Python CI, Flutter CI, iOS CI, deploy Android/iOS)
```

## 1.3 Arquitetura real (como as peças se conectam)

```
                ┌──────────────────────── Render (1 serviço Docker) ────────────────────────┐
                │  Dockerfile multi-stage:                                                   │
   Navegador ──▶│   Stage 1 (Flutter): melos build:web  →  apps/epi_admin/build/web          │
   / Mobile     │   Stage 2 (Python):  copia build/web → static/app/  +  app.py (Flask)      │
                │                                                                            │
                │   app.py roteia:                                                           │
                │     "/"        → static/  (WEB LEGADO em JS puro)                          │
                │     "/app/"    → Flutter Web (SPA)                                         │
                │     "/api/…"   → API REST (modules/, epi_backend/)                         │
                └──────────────────────────────┬─────────────────────────────────────────────┘
                                                │  DATABASE_URL
                                                ▼
                                   Supabase Postgres (kkmskwmkhyssrxqbsrqv)
                                   (Supabase usado só como banco + RLS)

   App Flutter (Android/iOS) ── HTTP (API_BASE_URL) ──▶ mesmo backend Python
```

Consequências diretas:
- **Supabase é só banco.** O Flutter **não** usa `supabase_flutter`/anon key; ele
  consome a API Python. A "Supabase anon key" só importa para o backend e
  para acesso direto (se houver) — não há SDK Supabase no app.
- **Flutter Web e backend são co-deployados** numa única imagem. O
  `build:web` usa `--base-href /app/` exatamente por isso.
- **O app Flutter não roda sem o backend Python.** Logo, o `EPI-CONTROLE-APP`
  **precisa** levar o backend junto (ou apontar para um backend SaaS dedicado).

## 1.4 Diferença entre os arquivos

**Nenhuma.** Verificado com `git ls-files` + `cmp` arquivo a arquivo: 834/834
idênticos. Não há, hoje, um arquivo sequer que distinga "legado" de "SaaS".

## 1.5 Duplicações perigosas (mesmo conteúdo nos dois repos)

Por estarem 100% duplicados, todo arquivo é "duplicado". Os **perigosos** são os
que carregam identidade de ambiente e, se não forem diferenciados, fazem um repo
agir como o outro:

| Arquivo | Por que é perigoso duplicado |
|---|---|
| `env.example` | Fixa `SUPABASE_URL=…kkmskwmkhyssrxqbsrqv…` (corporativo). Copiado para `.env` no SaaS → SaaS grava no banco corporativo. |
| `render.yaml` | `name: epi-controle` e `autoDeploy: true`. Dois repos com o mesmo blueprint podem disputar/duplicar o serviço. |
| `flutter/apps/epi_admin/android/app/build.gradle` | `applicationId "com.rocksbrothers.epicontrole"` igual nos dois → colisão de pacote na Play Store se ambos publicarem. |
| `ios/Runner/Info.plist`, `ios/fastlane/Appfile` | `com.rocksbrothers.epicontrole` igual → colisão de bundle id na App Store. |
| `firebase_options.dart` (via secrets de CI) | Mesmo projeto Firebase para os dois → push/analytics misturados. |
| `.github/workflows/*` | Deploys idênticos disparando para os mesmos alvos a partir de dois repos. |

## 1.6 Configurações compartilhadas indevidamente

- **Supabase:** `env.example` aponta para o projeto corporativo. Não há arquivo
  de ambiente separado para o SaaS.
- **Render:** um único `render.yaml`, nome `epi-controle`, sem variante SaaS.
- **Firebase:** um conjunto único de secrets (`FIREBASE_*`) consumido por todos
  os workflows.
- **Identidade mobile:** `applicationId`/bundle id únicos.
- **`WEB_BASE_URL` / `WEB_APP_URL`:** definidos uma vez (corporativo) no
  `render.yaml`/`env.example`.

## 1.7 Riscos encontrados (consolidado — item 10 da missão)

| # | Risco | Severidade | Evidência |
|---|---|---|---|
| R1 | `EPI-CONTROLE-APP` usar **banco corporativo** | **Crítico** | `env.example` fixa ref `kkmskwmkhyssrxqbsrqv` |
| R2 | `EPI-CONTROLE-APP` usar **deploy/serviço corporativo** | **Crítico** | `render.yaml name: epi-controle`, `autoDeploy: true` |
| R3 | App Flutter **sem backend** se separado ingenuamente | **Crítico** | Flutter consome API Python (`API_BASE_URL`) |
| R4 | **Colisão de identidade mobile** (Play/App Store, Firebase) | Alto | `com.rocksbrothers.epicontrole` único nos dois |
| R5 | **iOS não builda local** (sem projeto Xcode) | Alto | Não há `Runner.xcodeproj`/`Podfile`; gerado em CI |
| R6 | "Supabase do SaaS" **não confirmado** | Alto | `list_projects` mostra só o corporativo |
| R7 | Deploys cruzados disparados por workflows idênticos | Médio | `.github/workflows/*` iguais nos dois repos |
| R8 | Divergência futura sem fonte de verdade (drift) | Médio | Dois clones sem dono claro de cada parte |

> **Positivo:** nenhum segredo está versionado (`.gitignore` cobre `.env*`,
> keystores, etc.); a config sensível entra por env/secret. Isso reduz muito o
> risco de vazamento — o problema é de **endereçamento** (apontar para o
> ambiente errado), não de **exposição**.

---

# PARTE 2 — Arquitetura final recomendada

> **Princípio:** a estrutura de pastas **não precisa mudar** para separar os
> repos — ela já está bem organizada (backend modular + monorepo Flutter melos).
> A separação real é por **propósito + configuração de ambiente + o que cada
> repo publica**, não por reescrita. Mexer o mínimo na lógica (alinha com
> `AGENTS.md`: "não alterar lógica existente").

## 2.1 `EPI-CONTROLE-APP` (produto SaaS) — alvo

Mantém o full-stack (precisa do backend para o app funcionar), mas vira o
**produto SaaS multi-tenant** e é o **único** que publica mobile.

```
EPI-CONTROLE-APP/
├── flutter/                      # PRODUTO: Web + Android + iOS (foco principal)
│   ├── apps/epi_admin/           #   (renomeação opcional do diretório de produto)
│   └── packages/ epi_api · epi_design · epi_i18n
├── app.py · modules/ · epi_backend/ · core/   # BACKEND/API do SaaS (necessário)
├── supabase/migrations/          # mesmas migrações → aplicadas no Supabase SaaS
├── static/app/                   # (gerado no build) Flutter Web embutido
├── android/ ios/ web/            # já vivem sob flutter/apps/epi_admin/
├── render.app.yaml               # NOVO: blueprint Render do SaaS (nome próprio)
├── .env.saas.example             # NOVO: modelo de ambiente SaaS (sem ref corporativa)
├── .github/workflows/            # CI/CD do SaaS (deploy mobile + web SaaS)
└── docs/                         # docs do produto
```

Decisões-chave para o SaaS:
- **Banco:** `DATABASE_URL`/`SUPABASE_URL` → **projeto Supabase do SaaS** (a
  confirmar — ver R6). Nunca o `kkmskwmkhyssrxqbsrqv`.
- **Deploy:** `render.app.yaml` com `name: epi-controle-app` (serviço novo).
- **Mobile:** se o app da loja for o **mesmo produto**, manter
  `com.rocksbrothers.epicontrole` **só aqui** e remover capacidade de publicar
  mobile do repo legado. Se forem produtos distintos, usar id próprio
  (ex.: `com.rocksbrothers.epicontrole.saas`).
- **Web legado (`static/` JS):** pode ser **removido** do SaaS no futuro (o
  Flutter Web o substitui em `/app/`), servindo o Flutter na raiz `/`
  (`--base-href /`). **Não remover agora** — só após o Flutter Web cobrir 100%
  das telas (há vários planos de migração em `docs/PLANO_MIGRACAO_FLUTTER_WEB.md`).
- **Multi-tenant:** já há base (`modules/tenant/`, `companies_whitelabel`
  migration, RLS hardening). Manter e evoluir.

## 2.2 `EPI-CONTROLE` (corporativo/legado) — alvo

Continua o sistema corporativo **web** atual, no Supabase e Render atuais.
**Não publica mobile** e não muda de banco/deploy.

```
EPI-CONTROLE/
├── app.py · server_postgres.py · modules/ · epi_backend/ · core/   # backend legado
├── static/                       # FRONTEND WEB LEGADO (mantido como está)
├── supabase/migrations/          # Supabase CORPORATIVO atual (inalterado)
├── render.yaml                   # serviço Render atual "epi-controle" (inalterado)
├── env.example                   # ambiente corporativo (mantém ref atual)
├── requirements.txt · Dockerfile · package.json (lint do static/)
├── scripts/ · tests/ · spec/ · docs/
└── flutter/                      # CANDIDATO À REMOÇÃO (legado não envia mobile)
```

Decisões-chave para o legado:
- **Banco/Deploy:** **inalterados** (corporativo). Zero mudança de credencial.
- **`flutter/`:** pode ser **removido** do legado (o corporativo não publica
  apps). **Listado para remoção, não removido nesta auditoria.** Antes de
  remover, confirmar que nenhuma rota corporativa serve `/app/` em produção.
- **Workflows mobile** (`deploy-android.yml`, `deploy-ios.yml`, `ios_ci.yml`,
  `flutter.yml`): remover do legado; manter só `node.js.yml` (Python CI).

---

# PARTE 3 — Plano de ação (commits pequenos, reversíveis)

> Cada etapa = 1 PR pequeno, com CI verde antes do merge. Ordem pensada para
> **nunca** deixar um repo apontando para o ambiente do outro.

### Fase 0 — Backup e proteção
1. **Tag de backup** em cada repo no estado atual:
   `git tag pre-split-2026-06-29 && git push origin pre-split-2026-06-29`
   (permite rollback total a qualquer momento).
2. Proteger `main` (review obrigatório + CI) nos dois repos.
3. Branch de organização (já criada): `claude/epi-controle-repo-audit-8qjklb`.

### Fase 1 — Diagnóstico (este documento)
4. Mergear esta auditoria nos dois repos (additivo, sem risco).

### Fase 2 — Separar **configuração de ambiente** (a parte urgente — R1/R2)
5. **`EPI-CONTROLE-APP`:** criar `.env.saas.example` (sem ref corporativa) e
   `render.app.yaml` (`name: epi-controle-app`). Documentar que `DATABASE_URL`
   e `SUPABASE_URL` apontam para o **Supabase do SaaS**.
6. **`EPI-CONTROLE`:** manter `env.example`/`render.yaml` como estão
   (corporativo). Apenas anotar no topo que é o ambiente corporativo.

### Fase 3 — Separar **identidade mobile** (R4) — só no APP
7. No `EPI-CONTROLE-APP`, confirmar/ajustar `applicationId`, bundle id e projeto
   Firebase do SaaS (manter o atual se for o mesmo produto).
8. No `EPI-CONTROLE`, **remover** os workflows e a capacidade de publicar mobile.

### Fase 4 — Enxugar cada repo (remoções **com aprovação**, ver Parte ⑤/⑥)
9. **`EPI-CONTROLE`:** remover `flutter/` + workflows mobile (após validar que
   produção corporativa não serve `/app/`).
10. **`EPI-CONTROLE-APP`:** (futuro) remover `static/` JS legado quando o
    Flutter Web cobrir todas as telas; servir Flutter na raiz `/`.

### Fase 5 — Infra
11. **Supabase SaaS:** confirmar ref/chaves (R6), aplicar as 10 migrações no
    projeto SaaS, validar RLS via `get_advisors`.
12. **Render SaaS:** criar serviço a partir de `render.app.yaml`, popular env
    (sync:false) com credenciais do SaaS.
13. **Corporativo:** confirmar que nada mudou (mesmo Supabase, mesmo serviço).

### Fase 6 — Validação e fechamento
14. Validar builds Flutter (Parte 5) no APP; validar web legado no corporativo.
15. Website comercial: documentar o contrato de conexão (URL pública do SaaS +
    CORS `CORS_ALLOW_ORIGIN` + `WEB_BASE_URL`/`WEB_APP_URL`).
16. README + docs de deploy por repo; merge só com **CI verde**.

---

# PARTE 4 — Checklist técnico

Legenda: ✅ feito · 🟡 parcial/precisa ação · ⬜ pendente · ⚠️ risco/bloqueio

| Item | `EPI-CONTROLE-APP` (SaaS) | `EPI-CONTROLE` (legado) |
|---|---|---|
| Supabase SaaS configurado | ⚠️ **não confirmado** (R6: só o corporativo é visível) | — |
| Supabase corporativo preservado | — | ✅ inalterado (`kkmskwmkhyssrxqbsrqv`) |
| Render SaaS configurado | ⬜ falta `render.app.yaml` + serviço | — |
| Render corporativo preservado | — | ✅ `render.yaml` "epi-controle" |
| Flutter Web funcionando | 🟡 código pronto; build não validado aqui (sem SDK) | n/a (remover) |
| Android APK gerando | 🟡 config OK (`build:apk`); não validado aqui | n/a |
| Android App Bundle gerando | 🟡 `build:android` + assinatura via secrets; não validado | n/a |
| iOS build preparado | ⚠️ **não** — sem projeto Xcode (gerado em CI) (R5) | n/a |
| Website comercial pronta p/ conectar | 🟡 depende de `WEB_*_URL`+CORS do SaaS | — |
| Variáveis separadas por ambiente | ⬜ falta `.env.saas.example` | ✅ `env.example` (corporativo) |
| GitHub Actions separado | ⬜ workflows ainda idênticos (R7) | 🟡 manter só Python CI |
| README atualizado | ⬜ | ⬜ |
| Documentação de deploy criada | 🟡 existe muita doc; falta guia "deploy SaaS" | 🟡 `docs/DOCKER_RENDER_OCR.md` |
| Segredos fora do git | ✅ | ✅ |

---

# PARTE 5 — Comandos de validação

> ⚠️ Nesta sessão **Flutter/Dart não estão instalados** — os comandos abaixo
> não foram executados aqui; são o roteiro oficial de validação (refletem os
> scripts reais do `melos.yaml`). Python 3 e Node estão disponíveis.

## 5.1 `EPI-CONTROLE-APP` — Flutter (rodar dentro de `flutter/`)

```bash
cd flutter
dart pub get
dart pub global activate melos
melos bootstrap                 # resolve todos os pacotes do monorepo
melos run gen:l10n              # gera l10n a partir dos ARB
melos run gen                   # retrofit + json_serializable (build_runner)

melos run lint                  # == flutter analyze --no-fatal-infos (todos os pacotes)
melos run test                  # == flutter test (todos os pacotes)

# Builds do app de produto (scope epi_admin):
melos run build:web             # flutter build web --release --base-href /app/
melos run build:apk             # flutter build apk --debug
melos run build:android         # flutter build appbundle --release
melos run build:ios             # flutter build ipa --release --no-codesign  (⚠️ ver R5)

# Equivalentes "flutter ..." diretos (a partir de flutter/apps/epi_admin):
flutter clean && flutter pub get
flutter analyze
flutter test
flutter build web --base-href /app/      # use --base-href / se servir Flutter na raiz
flutter build apk
flutter build appbundle
flutter build ios --no-codesign          # exige bootstrap do Xcode antes (R5)
```

Gates de i18n (rodam no CI, independem do SDK Flutter):
```bash
cd flutter
python3 tool/validate_arb.py
bash    tool/check_hardcoded_strings.sh
```

## 5.2 Backend / web legado (Python — vale para os dois repos)

```bash
# Não há "npm test/build" de aplicação: package.json só faz lint do JS legado.
npm install
npm run lint                    # eslint static/js

# Backend Python (a API + web legado):
python -m pip install -r requirements.txt pytest
pytest tests/ -v --tb=short     # 91 testes (espelha o workflow node.js.yml → "Python CI")
python scripts/check_ocr_runtime.py   # valida runtime OCR (Tesseract)

# Build de produção (igual ao Render):
docker build -t epi-controle .        # multi-stage: Flutter Web + Python
```

---

# PARTE 6 — Resultado final esperado

Ao concluir o plano, teremos **dois repositórios limpos e com donos claros**:

- **`EPI-CONTROLE-APP`** — produto **SaaS multi-tenant**: app Flutter
  (Web + Android + iOS) + backend/API Python próprio, apontando para o
  **Supabase do SaaS** e deployado num **serviço Render dedicado**
  (`epi-controle-app`), pronto para conectar à website comercial. Único repo que
  publica mobile.
- **`EPI-CONTROLE`** — sistema **corporativo/legado web**, mantendo o
  **Supabase e o Render atuais** (`epi-controle`), sem capacidade mobile, com o
  frontend `static/` JS intacto.

## Bloqueios a resolver antes de executar remoções (precisam de você)

1. **R6 — Supabase do SaaS:** informar o `ref` do projeto SaaS e confirmar que
   as chaves/`DATABASE_URL` do SaaS estão prontas. Hoje só vejo o corporativo.
2. **R5 — iOS:** decidir entre (a) versionar o projeto Xcode (`Runner.xcodeproj`,
   `Podfile`, `AppDelegate`) ou (b) manter geração via CI (fastlane). Para
   `flutter build ios` local funcionar, precisa de (a) ou do passo de bootstrap.
3. **Identidade mobile:** o app SaaS é o **mesmo** produto (mantém
   `com.rocksbrothers.epicontrole`) ou um produto **novo** (id próprio)?
4. **Render:** confirmar que o serviço `epi-controle-app` já existe e como ele
   deve buildar (Docker full-stack? ou static site só com Flutter Web + backend
   separado?).

> Assim que esses pontos forem confirmados, executo o plano em **commits
> pequenos** (1 PR por fase), preservando histórico e com a tag
> `pre-split-2026-06-29` garantindo rollback.
