# Runbook de Release Mobile (M5) — Play Store & App Store

> Sequência de build, validação em device real e submissão, com o **gate de rejeição**.
> Pré-requisitos: M0 (permissões) ✅, M1 (privacy/entitlements) ⚠️, M2 (legais), M3 (formulários),
> M4 (assets).

## 0) Projeto Xcode iOS — geração automatizada (Fastlane) 🟡 macOS-only
O repositório **não versiona** o projeto iOS (`Runner.xcodeproj`, `AppDelegate`, `Podfile`,
`Assets.xcassets`, `LaunchScreen`). Em vez de commitar o `.xcodeproj` (frágil), a geração +
configuração é **automatizada** e roda no **macOS** (CI `deploy-ios.yml` ou Mac do dev):

**Automação no repo:**
- `ios/fastlane/Fastfile` — lanes `prepare` / `beta` (TestFlight) / `release`.
- `ios/fastlane/wire_xcode.rb` — gem `xcodeproj`: seta
  `CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements` e adiciona `PrivacyInfo.xcprivacy`
  ao *Copy Bundle Resources*.
- `ios/Gemfile` — `fastlane`, `cocoapods`, `xcodeproj`.
- `deploy-ios.yml` roda o passo **"Prepare iOS project"** (gera + wira) antes do build.

**No Mac do dev:**
```bash
cd flutter/apps/epi_admin/ios
bundle install
bundle exec fastlane prepare   # gera Runner.xcodeproj + entitlements + Privacy Manifest
bundle exec fastlane beta      # resolve+valida API_BASE_URL (ci/authorized_backend.json); build assinado + upload TestFlight
```

> `prepare` roda `flutter create . --platforms=ios` se faltar o projeto, **restaura** os
> arquivos versionados (`Info.plist`, `PrivacyInfo.xcprivacy`, `Runner.entitlements`) caso o
> `flutter create` os sobrescreva, e aplica o wiring. A **Capability Push** no App ID é
> configurada no portal Apple / via `match`. ⚠️ **Validar em execução real no macOS** — não é
> executável no ambiente Linux deste repo.

> **Backend obrigatório (EST-V1.6-R1):** todo release nativo deve apontar para o
> backend autorizado DO PRÓPRIO produto. Resolva/valide com o guard — vazio usa o
> backend autorizado (`ci/authorized_backend.json`); backend de outro produto,
> localhost, http ou ausente **abortam** antes do build. Nunca passe uma URL
> manual sem validar.

## 1) Android — AAB
```bash
# na raiz do repo — resolve (vazio → backend autorizado) e valida o backend
API_BASE_URL="$(python3 ci/api_backend_guard.py resolve "${API_BASE_URL:-}")" || exit 1
cd flutter/apps/epi_admin
flutter build appbundle --release \
  --dart-define=API_BASE_URL="$API_BASE_URL"    # artefato Play (NÃO APK)
```
- Assinatura via `key.properties` (CI: `deploy-android.yml` com secrets de keystore).
- Subir no **Internal testing** antes de produção.

## 2) iOS — IPA (após passo 0)
```bash
# na raiz do repo — resolve+valida o backend do produto (vazio → autorizado)
API_BASE_URL="$(python3 ci/api_backend_guard.py resolve "${API_BASE_URL:-}")" || exit 1
cd flutter/apps/epi_admin
flutter build ipa --release \
  --dart-define=API_BASE_URL="$API_BASE_URL" \
  --export-options-plist=ios/ExportOptions.plist
```
- CI: `deploy-ios.yml` (macOS, certificados + provisioning + upload TestFlight).

## 3) Validação em device real (gate)
- [ ] Android real: login → refresh de token → câmera/QR → biometria → push → modo offline.
- [ ] iPhone real: idem + Face ID.
- [ ] Trocar de empresa não vaza dados (multi-tenant).
- [ ] Console limpo / sem crash.

## 4) Gate de rejeição (revisar antes de submeter)
- [ ] **Sem WebView** que empacote site (✅ nativo).
- [ ] **Permissões mínimas** — sem localização (✅ M0); cada permissão tem justificativa.
- [ ] **iOS**: `PrivacyInfo.xcprivacy` presente e consistente com App Privacy; descrições de uso
      (câmera/fotos/Face ID) presentes; ATS sem exceção (HTTPS).
- [ ] **Android**: targetSdk ≥ 35 (✅ 36); Data Safety publicado; `usesCleartextTraffic=false`.
- [ ] Política de Privacidade + Termos + Suporte com **URLs ativas** nos consoles.
- [ ] Conta de teste/credenciais de revisão fornecidas (app exige login).
- [ ] Build sobe sem erros de assinatura.

## 5) Submissão
- **Play:** Internal → Closed → Production (rollout gradual %).
- **Apple:** TestFlight → App Review → Release.

## Comandos de verificação rápida
```bash
flutter analyze && flutter test
grep -R "uses-permission" android/app/src/main/AndroidManifest.xml   # sem LOCATION
grep -R "NSLocation" ios/Runner/Info.plist                          # vazio
ls ios/Runner/PrivacyInfo.xcprivacy ios/Runner/Runner.entitlements  # existem
```
