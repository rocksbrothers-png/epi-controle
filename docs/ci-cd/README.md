# Infraestrutura de CI/CD — EPI Controle

Documentação da esteira de Integração e Entrega Contínua do monorepo
`epi-controle` (Flutter + Backend Python + Web legado), preservando a
arquitetura **Multi-Tenant** e mantendo a regra de negócio centralizada no
Backend.

> Escopo desta versão: repositório `epi-controle`. Os repositórios irmãos
> `epi-controle-app` (port SaaS) e `epi-controle-site` (site) recebem a mesma
> infra numa etapa subsequente.

---

## 1. Visão geral dos workflows

| Workflow | Arquivo | Dispara em | Papel |
|----------|---------|-----------|-------|
| Flutter CI | `flutter.yml` | push/PR em `flutter/**` | analyze + test + build APK/AAB/Web + integração Android |
| iOS CI | `ios_ci.yml` | push/PR em `flutter/**` | analyze + test + build iOS (no-codesign) |
| Backend CI | `backend-ci.yml` | push/PR no backend | pytest + cobertura + ruff + validação PostgreSQL/Multi-Tenant |
| Contract Tests | `contract-tests.yml` | push/PR na API | contratos REST/JSON/enum/escopo entre Flutter e Backend |
| CodeQL | `codeql.yml` | push/PR + semanal | SAST (Python + JavaScript) |
| Security | `security.yml` | push/PR | Dependency Review + Secret Scan (gitleaks) + pip-audit |
| Deploy Android | `deploy-android.yml` | tag `vX.Y.Z` / manual | build assinado + upload Google Play |
| Deploy iOS | `deploy-ios.yml` | tag `vX.Y.Z` / manual | build assinado + TestFlight/App Store |

Config auxiliar: `dependabot.yml` (atualização de deps), `release.yml`
(agrupamento das release notes), `CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`,
`ISSUE_TEMPLATE/`.

### Por que não há `flutter-build.yml` separado
O build de APK/AAB/Web já vive dentro de `flutter.yml` (jobs `build-apk-debug`,
`build-android`, `build-web`), com `needs: analyze-and-test`. Criar um segundo
arquivo duplicaria toolchain e cache. Mantivemos **um** pipeline Flutter para
evitar duplicidade, conforme a diretriz de auditoria.

---

## 2. Fluxograma de execução

```
                         Pull Request / Push
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
   Flutter CI               Backend CI                  Segurança
   ──────────               ──────────                  ─────────
   ARB/i18n gate            test + coverage             CodeQL (py/js)
   flutter analyze          ruff (lint)                 Dependency Review
   flutter test             postgres-schema             Secret Scan
   widget/golden            (RLS/tenant_id)             pip-audit
        │                        │
        ▼                        ▼
   build Web/APK/AAB      Contract Tests
   integração Android     (envelope/enum/escopo)
        │                        │
        └───────────┬────────────┘
                    ▼
              Todos os checks verdes
                    ▼
            Merge (via Branch Protection)
                    ▼
            Tag vX.Y.Z → Release
                    ▼
        deploy-android.yml / deploy-ios.yml
        → Google Play / TestFlight + Artifacts
```

---

## 3. Dependências / toolchain instaladas na CI

| Ferramenta | Versão | Onde |
|-----------|--------|------|
| Flutter SDK | canal `stable` (deploy fixa `3.24.x`) | `subosito/flutter-action@v2` |
| Dart SDK | acompanha o Flutter (`>=3.3.0 <4.0.0`) | idem |
| Melos | `^6.3.2` | `dart pub global activate melos` |
| Java | Temurin 17 | `actions/setup-java@v4` |
| Android SDK | API 34 (emulador integração) | `android-emulator-runner@v2` |
| Python | 3.11 (paridade com Dockerfile/Render) | `actions/setup-python@v5` |
| PostgreSQL | 16 (service container) | `backend-ci.yml` job `postgres-schema` |
| Tesseract OCR | pacotes eng/por/spa/nor/fra | `apt-get` no backend |

---

## 4. Secrets necessários

Configurar em **Settings → Secrets and variables → Actions**.

### Build/Deploy Android
- `ANDROID_KEYSTORE_BASE64` — keystore de upload em base64
- `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `ANDROID_STORE_PASSWORD`
- `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD` (usados por `deploy-android.yml`)
- `GOOGLE_PLAY_JSON_KEY` — service account JSON do Google Play

### Build/Deploy iOS
- `BUILD_CERTIFICATE_BASE64`, `P12_PASSWORD`
- `BUILD_PROVISION_PROFILE_BASE64`
- `APP_STORE_CONNECT_API_KEY_BASE64`, `APP_STORE_CONNECT_API_KEY_ID`, `APPLE_TEAM_ID`

### Firebase (config de cliente — push)
- `FIREBASE_PROJECT_ID`, `FIREBASE_SENDER_ID`, `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_ANDROID_API_KEY`, `FIREBASE_ANDROID_APP_ID`
- `FIREBASE_IOS_API_KEY`, `FIREBASE_IOS_APP_ID`
- `FIREBASE_WEB_API_KEY`, `FIREBASE_WEB_APP_ID`

Nenhum secret é exigido para os jobs de **teste/lint/segurança** — eles rodam
sem credenciais (o `GITHUB_TOKEN` padrão basta para gitleaks e dependency-review).

## 5. Variáveis de ambiente (Repository variables)

- `API_BASE_URL` — base da API Python (default: `https://epi-controle-app-gupy.onrender.com`)

---

## 6. Branch Protection recomendada (`main`)

Configurar em **Settings → Branches → Add rule** (exige admin — não é aplicável
por commit):

- ✅ Require a pull request before merging (1+ aprovação)
- ✅ Require review from Code Owners
- ✅ Require status checks to pass before merging:
  - `Analyze & Test` (flutter.yml)
  - `Test & Coverage` (backend-ci.yml)
  - `API Contract & Multi-Tenant Scope` (contract-tests.yml)
  - `Analyze (python)` e `Analyze (javascript-typescript)` (codeql.yml)
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

> Os jobs marcados como `continue-on-error` (ruff, pip-audit, postgres migration
> dry-run) **não** devem ser exigidos até o baseline estar limpo.

---

## 7. Estratégia de cache

| Cache | Chave | Onde |
|-------|-------|------|
| Flutter SDK | gerenciado pela `flutter-action` (`cache: true`) | todos os jobs Flutter |
| Pub cache | idem | idem |
| Gradle | `gradle/actions/setup-gradle@v4` | jobs Android |
| Pip | `actions/setup-python` (`cache: pip`) | jobs Python |

---

## 8. Estratégia de Release

1. Merge na `main` com todos os checks verdes.
2. Criar tag semver `vX.Y.Z` (`git tag v1.4.0 && git push origin v1.4.0`).
3. A tag dispara `deploy-android.yml` e `deploy-ios.yml` (builds assinados).
4. As Release Notes são geradas automaticamente e agrupadas por label
   (`release.yml`).
5. Artefatos (Web, APK, AAB, coverage) ficam anexados aos runs / release.

Versionamento: **SemVer** + **Conventional Commits** (o tipo do commit orienta
o incremento — `feat` → minor, `fix` → patch, `BREAKING CHANGE` → major).

---

## 9. Estratégia de rollback

- **App (Play/TestFlight):** promover a build anterior na respectiva track
  (interna → produção) ou publicar patch a partir da última tag boa.
- **Backend (Render):** redeploy do commit anterior (Render mantém histórico) ou
  `git revert` do commit problemático + novo deploy.
- **CI/CD:** cada workflow é isolado; reverter um arquivo `.github/workflows/*.yml`
  não afeta os demais. Como cada PR desta infra é aditivo, o rollback é
  `git revert` do PR sem tocar em código de produto.
- **Banco:** migrations não são revertidas automaticamente — toda migration
  destrutiva deve vir acompanhada de script de reversão documentado.

---

## 10. Plano de migração (rollout)

Implantação em PRs pequenos e reversíveis:

1. **PR 1 — Infra fundacional** (este): Dependabot, CodeQL, Security, Backend CI,
   Contract Tests, CODEOWNERS, templates, release notes, documentação.
2. **PR 2** — Ligar gates de cobertura no backend após medir baseline.
3. **PR 3** — Golden tests no Flutter + `ruff.toml` e remoção do `continue-on-error`.
4. **PR 4** — Runner de schema-base para tornar `postgres-schema` bloqueante.
5. **PR 5** — Replicar a infra em `epi-controle-app` e variante leve em `-site`.

---

## 11. Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| Suíte de testes usa SQLite; sistema usa PostgreSQL | Job `postgres-schema` valida RLS/tenant_id de forma estática + dry-run; migração dos testes para Postgres é trilha própria (PR futuro) |
| Gate de cobertura quebra CI verde sem baseline | Cobertura é reportada, não bloqueante, até medir o baseline |
| `ruff`/`pip-audit` acusam passivo pré-existente | `continue-on-error` até zerar o passivo |
| Renomear `node.js.yml`→`backend-ci.yml` muda nome do check | Atualizar Branch Protection ao aplicar; branch protection ainda não configurada |
| CODEOWNERS com times inexistentes é ignorado | Usa handle válido `@rocksbrothers-png`; trocar por times quando criados |

---

## 12. Testes obrigatórios (matriz)

| Categoria | Onde roda | Status |
|-----------|-----------|--------|
| Flutter Analyze / Test / Widget | `flutter.yml` | ✅ ativo |
| Golden Tests | `flutter.yml` (quando existirem) | ⏳ a adicionar |
| Backend Tests + Coverage | `backend-ci.yml` | ✅ ativo (gate ⏳) |
| Contract Tests | `contract-tests.yml` | ✅ ativo |
| Multi-Tenant / Scope | `contract-tests.yml` + `backend-ci.yml` | ✅ ativo |
| Migration / Schema | `backend-ci.yml` (`postgres-schema`) | ⚠️ não bloqueante |
| Integração Android | `flutter.yml` (emulador) | ✅ ativo |
| Segurança (SAST/deps/secrets) | `codeql.yml` + `security.yml` | ✅ ativo |

---

## 13. Rodando localmente

```bash
# Backend
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v --cov=epi_backend --cov=modules

# Flutter (na pasta flutter/)
dart pub global activate melos
melos bootstrap
melos run gen:l10n && melos run gen
melos run lint      # flutter analyze
melos run test      # flutter test
melos run build:web # build web

# Lint backend (opcional)
pip install ruff && ruff check epi_backend modules app.py
```

## 14. Como adicionar um novo workflow

1. Crie `.github/workflows/<nome>.yml` com `on:` restrito por `paths:` para não
   rodar à toa.
2. Reutilize a toolchain existente (mesmas versões de Python/Flutter/Java).
3. Adicione `concurrency:` para cancelar runs antigos do mesmo ref.
4. Se for um gate obrigatório, inclua o nome do job na Branch Protection.
5. Documente-o na tabela da seção 1.

## 15. Depuração

- Abra o run em **Actions**, expanda o job/step vermelho.
- Baixe os artefatos (`*-coverage-*`, `*-junit*`, `postgres-migration-log-*`).
- Re-rode com **Re-run jobs → Enable debug logging** para logs verbosos.
- Reproduza local com os comandos da seção 13.
