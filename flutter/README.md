# EPI Controle — Flutter (Web + Android + iOS)

Monorepo Flutter para a plataforma EPI Controle.

## Pré-requisitos

```bash
# Flutter SDK 3.22+
flutter --version

# Melos (gerenciador de monorepo)
dart pub global activate melos

# Verificar setup
flutter doctor
```

## Setup inicial

```bash
cd flutter/
melos bootstrap           # instala dependências em todos os packages/apps
melos run gen:l10n        # gera arquivos Dart de l10n a partir dos ARBs
melos run gen             # code generation (retrofit, json_serializable)
```

## Rodar o app

```bash
# Web (Chrome)
cd apps/epi_admin
flutter run -d chrome

# Android (emulador ou dispositivo)
flutter run -d android

# iOS (apenas macOS com Xcode)
flutter run -d ios
```

## Estrutura

```
flutter/
├── pubspec.yaml            # Workspace (pub workspaces) + config do monorepo (chave `melos:`)
├── analysis_options.yaml   # Linting global (inclui regra i18n)
│
├── packages/
│   ├── epi_design/         # Design System (tokens + theme + componentes)
│   ├── epi_api/            # Cliente HTTP para API UBX
│   └── epi_i18n/           # Arquivos ARB + l10n
│
└── apps/
    └── epi_admin/          # App principal (Web + Android + iOS)
        ├── l10n.yaml       # Configuração do gerador de l10n
        ├── lib/
        │   ├── main.dart
        │   ├── app.dart    # MaterialApp.router + ThemeData + l10n
        │   └── core/
        │       ├── i18n/   # LocaleProvider (user > company > OS > pt-BR)
        │       ├── api/    # DI do cliente HTTP
        │       └── router/ # go_router (todas as rotas)
        ├── ios/Runner/Info.plist       # Permissões iOS
        └── android/app/build.gradle   # Config Android
```

## Idiomas suportados

| Código | Idioma | Status |
|--------|--------|--------|
| pt-BR  | Português (Brasil) | ✅ Completo |
| en-US  | English | ✅ Completo |
| es-ES  | Español | ✅ Completo |
| fr-FR  | Français | 🔄 Parcial (Fase UX-5) |
| no-NO  | Norsk | 🔄 Parcial (Fase UX-5) |

## Regra de i18n obrigatória

**PROIBIDO:**
```dart
Text('Salvar')
SnackBar(content: Text('EPI vencido'))
```

**OBRIGATÓRIO:**
```dart
Text(context.l10n.save)
SnackBar(content: Text(context.l10n.epiStatusExpired))
```

## Build para produção

```bash
# Android App Bundle (Play Store)
melos run build:android
# Arquivo: apps/epi_admin/build/app/outputs/bundle/release/app-release.aab

# iOS IPA (App Store / TestFlight)
melos run build:ios
# Arquivo: apps/epi_admin/build/ios/archive/Runner.xcarchive

# Flutter Web
melos run build:web
# Pasta: apps/epi_admin/build/web/
```

## Sprints

| Sprint | Escopo | Status |
|--------|--------|--------|
| S0 | Design System + i18n + monorepo | ✅ Fundação criada |
| S1 | Login + Dashboard | ⬜ Próximo |
| S2 | Colaboradores + Gestão | ⬜ |
| S3 | EPIs + Estoque + QR | ⬜ |
| S4 | Compras + Entregas + Devoluções | ⬜ |
| S5 | Fichas + Relatórios | ⬜ |
| S6 | Empresas + Configurações | ⬜ |
| S7 | Portal do Colaborador | ⬜ |
| S8 | Polish + Dark Mode + E2E | ⬜ |
| S9 | Google Play | ⬜ |
| S10 | Apple App Store | ⬜ |
