# EPI Controle — Flutter Architecture

## Monorepo Layout (Melos)

```
flutter/
├── apps/
│   └── epi_admin/          # Main app (Web + Android + iOS)
└── packages/
    ├── epi_design/          # Design System (Atomic Design)
    ├── epi_api/             # API client (Dio + Retrofit)
    └── epi_i18n/            # ARB source files (5 locales)
```

Run `melos bootstrap` after cloning. Key scripts: `melos run gen`, `melos run lint`, `melos run test`.

---

## Package Responsibilities

### epi_design
Pure-Flutter, no business logic. Exports:

| Layer | Examples |
|---|---|
| Tokens | `EpiColors`, `EpiTypography`, `EpiSpacing`, `EpiBreakpoints` |
| Atoms | `EpiButton`, `EpiTextField`, `EpiChip` |
| Molecules | `EpiCard`, `EpiSearchBar`, `EpiStatusBadge` |
| Organisms | `EpiDataTable`, `EpiFormSection` |
| Layouts | `AppShell` (NavigationRail / BottomNavigationBar) |

**Breakpoints** (single source of truth — `tokens/breakpoints.dart`):

| Name | Value | Meaning |
|---|---|---|
| `EpiBreakpoints.tablet` | 600 px | Mobile → Tablet |
| `EpiBreakpoints.desktop` | 768 px | Tablet → Desktop |
| `EpiBreakpoints.wide` | 1200 px | Desktop → Wide |

### epi_api
Generated Retrofit endpoints + Dio interceptors. `ApiClient` is a singleton initialised in `main.dart` with the resolved base URL. Never import `epi_api` directly from UI widgets — go through BLoC/Cubit.

### epi_i18n
Source ARB files only. Code-generation (`flutter gen-l10n`) runs inside `epi_admin`. All 5 locales (`pt_BR`, `en_US`, `es_ES`, `fr_FR`, `no_NO`) must have identical keys — enforced by `epi_i18n/test/epi_i18n_test.dart`.

---

## Application Structure (`epi_admin`)

```
lib/
├── main.dart                 # Bootstrap: ApiClient, SyncService, ThemeModeNotifier, LocaleProvider
├── app.dart                  # MaterialApp.router + providers
└── core/
    ├── api/                  # ApiClient singleton
    ├── bloc/                 # BLoC/Cubit state management
    ├── database/             # SyncDatabase (sqflite offline queue)
    ├── i18n/                 # LocaleProvider, ThemeModeNotifier, generated/
    ├── notifications/        # Firebase push + NotificationOverlay
    ├── router/               # GoRouter (app_router.dart, routes.dart)
    ├── shell/                # AppShell wrapper (delegates to epi_design AppShell)
    └── sync/                 # SyncService (offline flush on reconnect)
```

---

## Navigation (GoRouter)

`buildRouter()` in `app_router.dart` creates a single `ShellRoute` that wraps all authenticated routes with `AppShell`. Redirect guard checks `_isAuthenticated` before every navigation event.

**Route constants** live in `routes.dart`. Never hard-code path strings outside that file.

```
/login           → LoginScreen (outside shell)
/dashboard       → DashboardScreen
/employees       → EmployeesScreen
/epis            → EpisScreen
/deliveries      → DeliveriesScreen
/returns         → ReturnsScreen
/records         → RecordsScreen
/stock           → StockScreen
/purchases       → PurchasesScreen
/companies       → CompaniesScreen
/reports         → ReportsScreen
/users           → UsersScreen
/units           → UnitsScreen
/feedback        → FeedbackScreen
/settings        → SettingsScreen
/portal          → PortalScreen
```

---

## Internationalisation

- **Source**: `epi_i18n/lib/l10n/app_<locale>.arb` — edit these files.
- **Generated**: `epi_admin/lib/core/i18n/generated/` — never edit by hand; run `melos run gen:l10n`.
- **Runtime**: `LocaleProvider` (ChangeNotifier) persists the selected locale via `FlutterSecureStorage` key `user_locale`.
- **Priority**: persisted user choice → `/api/bootstrap` user preference → company preference → OS locale → `pt_BR`.

Adding a translation key:
1. Add to all 5 ARB files with identical key name.
2. Run `melos run gen:l10n`.
3. Use `AppLocalizations.of(context).yourKey` in the widget.
4. CI will block the PR if any locale is missing the key.

---

## State Management (BLoC/Cubit)

- Each screen or feature has a dedicated Cubit in `core/bloc/`.
- Cubits talk to `ApiClient` (never to Dio directly).
- UI listens via `BlocBuilder` / `BlocListener`.
- No business logic in widgets.

---

## Offline-First

`SyncService` (singleton) starts listening to `connectivity_plus` events in `main()`. When connectivity is restored it calls `flush()`, which drains `SyncDatabase` in order.

Supported operation types:

| `op_type` | Triggered by |
|---|---|
| `stock_movement` | StockCubit |
| `delivery_create` | NewDeliveryCubit (network failure) |
| `devolution_create` | DevolutionsCubit (network failure) |

Offline UI feedback:
- `NewDeliveryState.offlineQueued == true` → show `l10n.deliveryOfflineQueued`
- `DevolutionsState.offlineQueued == true` → show `l10n.returnOfflineQueued`
- `DevolutionsState.successMessage == ''` (sentinel) → show `l10n.returnSuccess`

---

## Theme

`ThemeModeNotifier` persists `ThemeMode` via `FlutterSecureStorage` key `theme_mode`. Tokens live in `epi_design` (`EpiTheme.light`, `EpiTheme.dark`). Material 3 is enabled globally.

---

## CI (GitHub Actions)

`.github/workflows/flutter.yml` jobs:

1. `analyze-and-test` — `flutter analyze` + `flutter test` (all packages)
2. `build-apk-debug` — debug APK artifact
3. `build-android` — release AAB
4. `build-web` — Web artifact (deployed alongside Python backend)

A PR cannot be merged if any job fails.
