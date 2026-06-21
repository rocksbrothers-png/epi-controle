# Auditoria de Publicação Mobile — Google Play & App Store

> **Tipo:** auditoria (somente análise — **nenhuma alteração de código foi feita**, conforme
> instrução). As correções estão propostas e integradas ao plano de ação.
> **Base:** `flutter/apps/epi_admin` (Android/iOS reais), `pubspec.yaml`, em 2026-06-21.
> **Legenda:** 🟢 OK · 🟡 Parcial · 🔴 Pendente · ⚠️ Risco de rejeição.

---

## Resposta executiva

| Pergunta | Resposta |
|---|---|
| O plano já contempla Play Store e App Store? | **Parcialmente.** Infra de build/CI e a maior parte da config Android existem; faltam itens de **privacidade/compliance** obrigatórios. |
| App pronto para **APK de teste**? | 🟢 **Sim** (CI já gera `Build Android APK (debug)`). |
| App pronto para **AAB da Play Store**? | 🟡 **Quase** — bloqueado por: remover permissão de **localização** não usada + formulário **Data Safety** + **Política de Privacidade**. |
| App pronto para **submissão na App Store**? | 🔴 **Não** — falta **`PrivacyInfo.xcprivacy`**, **entitlement de push (APNs)**, e os mesmos itens de privacidade/legais. |
| Risco de rejeição por "parecer um site"? | 🟢 **Baixo** — é Flutter nativo real (ver §1). |

**O que pode causar rejeição (prioridade):**
1. ⚠️ **Localização declarada e não usada** (Android + iOS) — não há plugin de GPS nem código. Play Data Safety/Apple reprovam permissão sem uso. → **remover**.
2. ⚠️ **iOS sem Privacy Manifest** (`PrivacyInfo.xcprivacy`) — obrigatório pela Apple; plugins usam "required reason APIs". → **criar**.
3. 🔴 **Política de Privacidade + Termos** ausentes (URL obrigatória nas duas lojas).
4. 🔴 **Formulários de dados** (Play Data Safety / Apple App Privacy) não preenchidos.

---

## 1. Flutter nativo × WebView

| Item | Status | Evidência |
|---|---|---|
| Usa WebView? | 🟢 Não | `grep webview/InAppWebView` em `lib/` e `pubspec.yaml` → **nenhum** |
| Navegação nativa | 🟢 Sim | `go_router` + `ShellRoute` (`app_router.dart`) |
| Telas são widgets Flutter | 🟢 Sim | `features/*/*_screen.dart` — Material widgets |
| Depende de HTML/JS legado no mobile | 🟢 Não | legado (`app.js`) só serve Web em `/`; mobile consome **API REST** |
| Risco "site adaptado" (Guideline 4.2 Apple) | 🟢 Baixo | UI 100% nativa; sem empacotamento de site |

**Diagnóstico:** o app é um cliente Flutter nativo real consumindo a API Python via Dio/HTTPS.
Nenhuma ação corretiva neste eixo.

## 2. Auditoria Android — Play Store

| Item | Valor / Status |
|---|---|
| `applicationId` | `com.rocksbrothers.epicontrole` 🟢 |
| `compileSdk` / `targetSdk` | 36 / 36 🟢 (atende exigência ≥35 do Play) |
| `minSdk` | 21 🟢 |
| `versionCode` / `versionName` | de `flutter` (`pubspec: 1.0.0+1`) 🟢 |
| Assinatura release | `signingConfigs.release` via `key.properties` 🟢 (secrets no CI: `deploy-android.yml`) |
| `minifyEnabled` + `shrinkResources` + proguard | 🟢 |
| AAB com splits (language/density/abi) | 🟢 |
| `allowBackup=false` / `fullBackupContent=false` | 🟢 (sem necessidade de backup rules) |
| `usesCleartextTraffic="false"` | 🟢 (HTTPS forçado) |
| `queries` p/ url_launcher (https/mailto/file) | 🟢 |
| Ícones adaptativos | 🟡 verificar `mipmap-anydpi-v26/ic_launcher.xml` (foreground/background) |
| Splash screen | 🟢 `launch_background.xml` (+ night) |
| `flutter build appbundle --release` | 🟢 (script `build:android` no melos + `deploy-android.yml`) |
| **Permissão LOCATION** | 🔴⚠️ `ACCESS_FINE/COARSE_LOCATION` declaradas **sem plugin/uso** |

**Permissões declaradas:** INTERNET, ACCESS_NETWORK_STATE, CAMERA, USE_BIOMETRIC/FINGERPRINT,
READ_MEDIA_IMAGES, READ_EXTERNAL_STORAGE(≤32), **ACCESS_FINE/COARSE_LOCATION**,
POST_NOTIFICATIONS, RECEIVE_BOOT_COMPLETED, VIBRATE.

**Riscos:** a localização cai no formulário **Data Safety** e exige justificativa de uso real —
como não há recurso de GPS, é **permissão sobrando** (motivo comum de revisão/reprovação).

## 3. Auditoria iOS — App Store

| Item | Status |
|---|---|
| `CFBundleIdentifier` | `com.rocksbrothers.epicontrole` 🟢 |
| Versão (`CFBundleShortVersionString`/`Version`) | 1.0.0 / 1 🟢 |
| `NSCameraUsageDescription` | 🟢 (QR + fotos) |
| `NSPhotoLibraryUsageDescription` | 🟢 (evidências) |
| `NSFaceIDUsageDescription` | 🟢 (biometria) |
| `NSLocationWhenInUseUsageDescription` | 🔴⚠️ presente **sem uso real** → remover (par do item Android) |
| `NSMicrophoneUsageDescription` | 🟢 não necessário (mobile_scanner é só câmera) |
| App Transport Security (HTTPS) | 🟢 ATS default ON (sem exceção) — bloqueia HTTP |
| `UIBackgroundModes` (remote-notification/fetch) | 🟢 |
| **`PrivacyInfo.xcprivacy`** | 🔴⚠️ **AUSENTE** — obrigatório (required-reason APIs de path_provider/secure_storage/sqflite/drift) |
| **`Runner.entitlements`** (aps-environment) | 🔴 ausente — push iOS precisa do entitlement APNs |
| Risco WebView | 🟢 baixo (nativo) |

**Ajustes necessários (iOS):** criar `PrivacyInfo.xcprivacy` (declarar `NSPrivacyTracking=false`,
`NSPrivacyCollectedDataTypes` e `NSPrivacyAccessedAPITypes` com motivos — ex.: `C617.1` p/
UserDefaults, `DDA9.1`/`0A2A.1` p/ file-timestamp do path_provider); adicionar
`Runner.entitlements` com `aps-environment`; remover a chave de localização.

## 4. Backend Python & comunicação segura

| Item | Status |
|---|---|
| API externa (fora do app) | 🟢 backend Python roda no Render; app só consome REST |
| HTTPS obrigatório | 🟢 release usa origin HTTPS / `onrender.com`; ATS + cleartext=false reforçam |
| Auth JWT + refresh + expiração | 🟢 `/api/login`, `/api/auth/refresh`, `/api/auth/me`; refresh-on-401 no app (#632) |
| Isolamento por `company_id` | 🟢 testado (#642/#644 — suíte de isolamento multi-tenant) |
| Logs de auditoria | 🟢 `structured_log`, eventos de portal/compras |
| Erros amigáveis a mobile | 🟢 envelope `{success,data,message}` + `humanize_integrity_error` |
| Resiliência a conexão instável | 🟢 retry/backoff no Dio (`_RetryInterceptor`), offline DB (drift/sqflite) |
| CORS | 🟡 confirmar allowlist para o origin do `/app` (web) — mobile não usa CORS |
| Python dentro do app? | 🟢 **Não** (confirmação explícita) |

## 5. Permissões × pacotes (necessidade real)

| Permissão | Pacote que exige | Uso real? | Android | iOS | Ação |
|---|---|---|---|---|---|
| Internet | dio/retrofit | ✅ | INTERNET | (n/a) | manter 🟢 |
| Network state | connectivity_plus | ✅ | ACCESS_NETWORK_STATE | — | manter 🟢 |
| Câmera | mobile_scanner + image_picker + mlkit | ✅ | CAMERA | NSCamera | manter 🟢 |
| Galeria/fotos | image_picker | ✅ | READ_MEDIA_IMAGES (+≤32) | NSPhotoLibrary | manter 🟢 |
| Biometria | local_auth | ✅ | USE_BIOMETRIC/FINGERPRINT | NSFaceID | manter 🟢 |
| Notificações | firebase_messaging | ✅ | POST_NOTIFICATIONS | UIBackgroundModes | manter 🟢 |
| **Localização** | **nenhum** | ❌ | ACCESS_FINE/COARSE | NSLocationWhenInUse | **REMOVER** 🔴⚠️ |
| Armazenamento local | drift/sqflite/path_provider/secure_storage | ✅ | (sem runtime perm) | Keychain | manter 🟢 |
| OCR | google_mlkit_text_recognition | ✅ | (usa câmera) | (usa câmera) | manter 🟢; refletir no Privacy Manifest |

> **RECEIVE_BOOT_COMPLETED / VIBRATE**: justificáveis por push; manter, mas declarar no Data Safety.

## 6. Privacidade & dados (matriz)

| Dado | Finalidade | Onde fica | Quem acessa | Retenção | Política? | Play Data Safety | Apple App Privacy |
|---|---|---|---|---|---|---|---|
| Nome/matrícula funcionário | Controle de EPI | Backend Postgres | Admins da empresa | Legal/trabalhista | Sim | Personal info | Contact/Identifiers |
| CPF | Identificação/portal | Backend (HMAC token) | Admins | Legal | Sim | Personal info (sensível) | Sensitive |
| Assinatura digital | Comprovação de entrega | Backend | Admins | Legal | Sim | Sim | Sim |
| Foto de evidência | Evidência de entrega/devolução | Backend | Admins | Legal | Sim | Photos | Photos |
| QR Code | Rastreio de estoque/EPI | Backend | Admins | Operacional | Sim | App activity | Sim |
| Dados de login/token | Autenticação | `flutter_secure_storage` (device) + backend | Próprio usuário | Sessão | Sim | Sim | Sim |
| Empresa/estoque/entregas | Operação | Backend | Escopo `company_id` | Operacional | Sim | Sim | Sim |
| Localização | — | **não coletar** (remover) | — | — | — | — | — |

## 7. Documentos obrigatórios para publicação

| Documento | Status |
|---|---|
| Política de Privacidade (URL) | 🔴 ausente |
| Termos de Uso | 🔴 ausente |
| Página/E-mail de suporte | 🔴 definir |
| Descrição curta/completa | 🔴 criar |
| Ícone (loja) | 🟡 confirmar 512×512 (Play) / 1024×1024 (Apple) |
| Screenshots Android (telefone) | 🔴 gerar |
| Screenshots iPhone (6.7"/6.5") | 🔴 gerar |
| Screenshots iPad (se publicar) | 🟡 opcional |
| Classificação indicativa (IARC) | 🔴 responder questionário |
| Data Safety (Google) | 🔴 preencher |
| App Privacy (Apple) | 🔴 preencher |

## 8. Critérios de aceite (gate de publicação)

- [x] Flutter nativo sem WebView crítico
- [x] Build AAB release gerável (CI) · APK debug ✅
- [x] HTTPS obrigatório (ATS + cleartext=false)
- [x] Backend externo seguro (JWT/refresh/isolamento testado)
- [ ] **AndroidManifest limpo** (remover LOCATION)
- [ ] **Info.plist** sem chave de localização
- [ ] **`PrivacyInfo.xcprivacy`** criado e revisado
- [ ] **`Runner.entitlements`** (APNs) p/ push iOS
- [ ] Permissões mínimas (só as usadas)
- [ ] Política de Privacidade + Termos publicados
- [ ] Formulários Data Safety / App Privacy mapeados
- [ ] Teste em Android real + iPhone real
- [ ] Checklist de rejeição revisado

## 9. Correções (a entrar no plano de ação) — **aguardam autorização**

### 🔴 Obrigatórias antes de qualquer build release de loja
1. **Remover localização** não usada: `ACCESS_FINE/COARSE_LOCATION` (AndroidManifest) e
   `NSLocationWhenInUseUsageDescription` (Info.plist). *(Reintroduzir só se houver feature de GPS.)*
2. **Criar `ios/Runner/PrivacyInfo.xcprivacy`** com tracking=false, tipos de dados coletados e
   `NSPrivacyAccessedAPITypes` (UserDefaults, file timestamp, disk space conforme plugins).
3. **Criar `ios/Runner/Runner.entitlements`** com `aps-environment` (push) e referenciar no projeto.
4. **Política de Privacidade + Termos de Uso** (página pública, URL para as lojas).
5. **Preencher Data Safety (Google) e App Privacy (Apple)** conforme a matriz §6.

### 🟡 Recomendadas
6. Confirmar **ícone adaptativo** Android (`ic_launcher.xml` foreground+background) e assets de loja.
7. Revisar **CORS** do backend para o origin do `/app` (web).
8. Adicionar **screenshots** e textos de loja ao repositório/processo de release.
9. Smoke **em device real** (Android + iPhone) cobrindo câmera/QR/biometria/push.

## 10. Comandos de validação (rodar no ambiente Flutter/CI)

```bash
flutter doctor -v
flutter pub deps
flutter analyze
flutter test
flutter build appbundle --release   # artefato Play Store (não APK)
flutter build ios --release
grep -R "uses-permission" android/app/src/main/AndroidManifest.xml
grep -R "NSCameraUsageDescription"     ios/Runner/Info.plist
grep -R "NSPhotoLibraryUsageDescription" ios/Runner/Info.plist
grep -R "NSLocation" ios/Runner/Info.plist   # deve ficar VAZIO após a correção #1
```

> **Nota:** este ambiente é o backend (sem Flutter SDK). Os builds release e o `flutter doctor`
> rodam no CI (`flutter.yml` + `deploy-android.yml`/`deploy-ios.yml`) ou em máquina com SDK.

---

## Integração ao plano de migração

Estas correções entram como **FASE 8-mobile (pré-loja)**, **antes** do cutover de produção e da
geração dos artefatos de loja. As 5 obrigatórias são bloqueantes para AAB/iOS; as recomendadas
podem correr em paralelo. Próximo passo: aprovar as correções 🔴 para eu aplicá-las (são de
configuração Android/iOS — fora do código Dart de negócio).
