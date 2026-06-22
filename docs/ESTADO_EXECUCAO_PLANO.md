# Estado de Execução do Plano de Migração Flutter

> Checklist **vivo** do que já está no `main` e do que falta, com o responsável
> de cada pendência. Atualizado em 2026-06-22. Complementa `PLANO_ACAO_FLUTTER_60D.md`,
> `PLANO_INTEGRADO_MIGRACAO_FLUTTER_AUDITORIA.md` e `AUDITORIA_PUBLICACAO_MOBILE.md`.

## ✅ Concluído e no `main`

| Frente | Entrega | PRs |
|---|---|---|
| **F1 Fundação** | refresh token + sessão; `/auth/me`; contrato de `permissions` (login) | #632, #635 |
| | contratos dos 16 clientes `epi_api` | #633 |
| | RBAC de rotas testável (`route_permissions`) | #634 |
| | `SessionContext`, rotas públicas, scaffolding (Codex) | #638–#640 |
| **CI** | conserto dos breaks (`--concurrency`, audit `Check`) | #641 |
| **F2 Multi-tenant** | suíte de isolamento por empresa (units/companies/purchases/employees) | #642, #644 |
| **F3–F7 Arquitetura** | `Cubit→Repository` + testes: employees, reports, purchases, stock, deliveries | #643, #645, #647, #648, #649 |
| **Paridade** | dashboard `pendingPurchases` (Reports PDF já existia) | #636 |
| **Sprint 4 Observabilidade** | `AppMonitoring` (telemetria por tela/API, caps 50/50/100) + wiring | #650 |
| **M0 lojas** | remoção de permissão de localização não usada (Android+iOS) | #646 |
| **M1 lojas** | `PrivacyInfo.xcprivacy` + `Runner.entitlements` + automação **Fastlane** (gera/wira o Xcode no macOS) | #646, #647 |
| **M2–M5 docs** | Política de Privacidade, Termos, Suporte, formulários Data Safety/App Privacy, copy de loja, runbook | #646 |

Cobertura de testes adicionada: 5 cubits (repositório fake), RBAC, contratos
(clients + bootstrap + auth), isolamento multi-tenant (pytest), observabilidade.

## ⏳ Pendências por responsável

### Precisa de **macOS** (não executável neste ambiente Linux)
- [ ] Rodar `bundle exec fastlane prepare` → gera `Runner.xcodeproj`, aplica entitlements/Privacy Manifest; validar/ajustar `wire_xcode.rb`.
- [ ] `fastlane beta` → build assinado + TestFlight (secrets ASC).
- [ ] `flutter build appbundle --release` validado para o Play (AAB).
- [ ] Smoke em **device real** Android + iPhone (câmera/QR/biometria/push/offline).

### Precisa de **consoles / negócio**
- [ ] Publicar URLs: Política de Privacidade, Termos, Suporte (M2).
- [ ] Preencher **Data Safety** (Google) e **App Privacy** (Apple) + IARC (M3).
- [ ] Gerar **assets**: ícone, screenshots, feature graphic (M4).
- [ ] Decidir/ligar o **cutover** `/`→`/app` via `FLUTTER_WEB_ROOT_REDIRECT` (canário por empresa).

### Hardening técnico (executável aqui, mas requer test-infra)
- [x] **Refresh-on-401** integração ponta-a-ponta — `test/refresh_interceptor_test.dart`. Seam de testabilidade `ApiClient.debugDio`/`debugRefreshDio` + `HttpClientAdapter` roteirizado e mock do canal do `flutter_secure_storage`. Sem `http_mock_adapter` (zero dependência nova). Cobre: 401→refresh→retry, single-flight concorrente, refresh inválido limpa sessão, ausência de refresh token.
- [x] Testes **offline**: `StockCubit.moveStock` (3 ramos: offline→fila, online→repo, online-com-falha→fila) e `NewDeliveryCubit.submit` (connectionError→fila, badResponse→erro). Resolvido por **injeção de dependência** (`ConnectivityChecker` + `OfflineQueue`) em vez de mock de platform channels — alinhado ao padrão Cubit→Repository, zero dependência nova.
- [x] Smoke **E2E** em `integration_test/smoke_test.dart` + job **`Integration (Android emulator)`** no `flutter.yml` (`reactivecircus/android-emulator-runner`, API 34/x86_64, KVM). Fluxos backend-free e determinísticos: boot→login, validação de formulário vazio (snackbar), toggle de senha, tema escuro.

## Observação de testabilidade
Os 2 primeiros itens de hardening pedem uma pequena evolução de testabilidade
(injetar `HttpClientAdapter`/mocks de plataforma). É a próxima fronteira técnica
que dá pra atacar aqui, com a ressalva de que o ambiente é backend (sem Flutter
SDK), então a validação real ocorre no Flutter CI.
