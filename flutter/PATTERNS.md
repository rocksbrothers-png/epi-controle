# EPI Controle — Guia de Padrões

Receitas práticas ("como fazer") para o dia a dia. Para a visão estrutural, veja [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 1. Navegação

**Sempre** use as constantes de `core/router/routes.dart` — nunca strings literais de path.

```dart
// ✅ Correto
context.go(Routes.deliveries);

// ❌ Errado
context.go('/deliveries');
```

Nova rota:
1. Adicione a constante em `routes.dart`.
2. Registre no `ShellRoute` em `app_router.dart`.
3. Se aparecer no menu, adicione um `EpiNavItem` em `core/shell/app_shell.dart` (com label `l10n.*`).

Toda rota autenticada vive dentro do único `ShellRoute` que aplica o `AppShell`. O guard de `redirect` decide login/logout — não duplique checagem de auth dentro das telas.

---

## 2. Internacionalização (i18n)

Nenhuma string visível ao usuário pode ser hardcoded. O gate de CI (`tool/check_hardcoded_strings.sh`) bloqueia novas ocorrências.

```dart
final l10n = AppLocalizations.of(context);
Text(l10n.deliverySuccess);
```

Adicionar uma chave:
1. Edite os **5** ARBs em `packages/epi_i18n/lib/l10n/app_*.arb` com a **mesma chave**.
2. Rode `melos run gen:l10n`.
3. Use `l10n.suaChave`.
4. O teste `epi_i18n_test.dart` falha o PR se algum locale estiver sem a chave.

Strings com parâmetros precisam de metadata `@chave`:

```json
"epiStatusExpiring": "Expira em {days} dias",
"@epiStatusExpiring": { "placeholders": { "days": { "type": "int" } } }
```

Mensagens de sucesso vindas de Cubit usam o **sentinel `''`** (string vazia) → a tela mapeia para `l10n.*`. Nunca coloque texto em português direto no Cubit.

---

## 3. Componentes (Design System)

Use sempre os widgets de `epi_design`. Não recrie botões, cards ou campos na camada de feature.

```dart
import 'package:epi_design/epi_design.dart';

EpiButton(label: l10n.save, onPressed: _save);
EpiTextField(label: l10n.employeeNameLabel, controller: _name);
```

Cores, espaçamentos e tipografia vêm de tokens — nunca valores mágicos:

```dart
// ✅
padding: const EdgeInsets.all(EpiSpacing.lg),
color: EpiColors.success,

// ❌
padding: const EdgeInsets.all(16),
color: const Color(0xFF226B4C),
```

---

## 4. Responsividade

Use `EpiBreakpoints` (`packages/epi_design/lib/tokens/breakpoints.dart`) — fonte única de verdade. Não escreva `width < 600` solto.

```dart
final w = MediaQuery.sizeOf(context).width;
if (EpiBreakpoints.isMobile(w)) {
  // bottom navigation
} else {
  // navigation rail
}
```

| Faixa | Limite |
|---|---|
| Mobile | `< tablet` (600) |
| Tablet | `tablet`–`desktop` (600–768) |
| Desktop | `desktop`–`wide` (768–1200) |
| Wide | `>= wide` (1200) |

O `AppShell` já alterna `NavigationRail` ↔ `BottomNavigationBar` por esses breakpoints; telas não precisam reimplementar isso.

---

## 5. Temas

`ThemeMode` é gerenciado por `ThemeModeNotifier` e persistido via `FlutterSecureStorage`. Tokens em `EpiTheme.light` / `EpiTheme.dark`.

```dart
// Trocar tema
context.read<ThemeModeNotifier>().setMode(ThemeMode.dark); // já persiste
```

Nunca hardcode cores claras/escuras na tela — derive do `Theme.of(context)` ou use tokens semânticos (`EpiColors.success`, `.warning`, `.danger`).

---

## 6. Idioma persistido

`LocaleProvider` persiste a escolha em `FlutterSecureStorage` (chave `user_locale`) e é inicializado em `main()` antes do `runApp`.

```dart
// Trocar idioma (tela de Configurações)
await context.read<LocaleProvider>().setLocale(const Locale('en', 'US'));
```

Prioridade de resolução: escolha persistida → preferência do usuário (`/api/bootstrap`) → preferência da empresa → locale do SO → `pt_BR`.

---

## 7. Offline-first

Operações que mutam dados devem degradar para a fila offline em falha de rede, em vez de mostrar erro.

Padrão no Cubit:

```dart
try {
  await ApiClient.deliveries.createDelivery(...);
  emit(state.copyWith(successId: id));
} on DioException catch (e) {
  if (e.type == DioExceptionType.connectionError ||
      e.type == DioExceptionType.connectionTimeout) {
    await SyncDatabase.enqueue(opType: 'delivery_create', payload: {...});
    emit(state.copyWith(offlineQueued: true));
    return;
  }
  emit(state.copyWith(error: e.toString()));
}
```

Padrão na tela (BlocListener):

```dart
if (state.offlineQueued) {
  showSnackBar(l10n.deliveryOfflineQueued); // cor warning
  Navigator.pop(context, true);
  return;
}
if (state.successId != null) {
  showSnackBar(l10n.deliverySuccess);      // cor success
  Navigator.pop(context, true);
}
```

Novo tipo de operação offline:
1. Adicione um `case` em `SyncService._execute()` que reexecuta a chamada de API a partir do payload.
2. Use o mesmo `opType` no `enqueue()` do Cubit.
3. O `SyncService` drena a fila automaticamente quando a conectividade volta.

---

## 8. State management

- Um Cubit por feature em `core/bloc/`.
- Cubit fala com `ApiClient`; **nunca** com `Dio` direto.
- Widget escuta via `BlocBuilder` / `BlocListener`. Sem lógica de negócio no widget.
- Estado é imutável (`Equatable` + `copyWith`).
