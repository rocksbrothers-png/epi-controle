# Runbook de Release Mobile (M5) — Play Store & App Store

> Sequência de build, validação em device real e submissão, com o **gate de rejeição**.
> Pré-requisitos: M0 (permissões) ✅, M1 (privacy/entitlements) ⚠️, M2 (legais), M3 (formulários),
> M4 (assets).

## 0) BLOQUEADOR iOS — projeto Xcode ausente 🔴
O repositório **não contém o projeto iOS** (`ios/Runner.xcodeproj/project.pbxproj`,
`AppDelegate`, `Podfile`, `Assets.xcassets`, `LaunchScreen`). `flutter build ipa` **falha** sem ele.
**Remediação (em macOS):**
```bash
cd flutter/apps/epi_admin
flutter create . --platforms=ios --org com.rocksbrothers   # gera o projeto sem apagar Info.plist*
```
\* Conferir que o `Info.plist` customizado (descrições de permissão) e o `PrivacyInfo.xcprivacy`
foram preservados; se sobrescritos, restaurar deste repositório. Depois, no Xcode:
- Adicionar `Runner/PrivacyInfo.xcprivacy` ao target Runner (**Copy Bundle Resources**).
- Build Setting `CODE_SIGN_ENTITLEMENTS = Runner/Runner.entitlements`.
- Capability **Push Notifications** + **Background Modes** (remote notifications).
- Commitar `ios/` completo.

## 1) Android — AAB
```bash
cd flutter/apps/epi_admin
flutter build appbundle --release    # artefato Play (NÃO APK)
```
- Assinatura via `key.properties` (CI: `deploy-android.yml` com secrets de keystore).
- Subir no **Internal testing** antes de produção.

## 2) iOS — IPA (após passo 0)
```bash
flutter build ipa --release --export-options-plist=ios/ExportOptions.plist
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
