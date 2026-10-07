import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart'
    show kDebugMode, kIsWeb, kReleaseMode, visibleForTesting;
import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';
import 'core/i18n/locale_provider.dart';
import 'core/i18n/theme_mode_notifier.dart';
import 'core/notifications/notification_service.dart';
import 'core/observability/app_monitoring.dart';
import 'core/sync/sync_service.dart';
import 'firebase_options.dart';

// Configurável via: flutter run --dart-define=API_BASE_URL=https://api.example.com
// Produção Web (co-deploy com backend): API_BASE_URL vazio → URLs relativas (mesmo origin).
// Dev Web (flutter run -d chrome): usa localhost:5000 automaticamente em kDebugMode.
const _kApiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

/// Resolve a base URL da API conforme o target e o modo de build (BP1).
///
/// Contrato, preservando o comportamento anterior e fechando o furo de release:
/// - **Com `API_BASE_URL`** (`--dart-define`): usa exatamente esse valor, em
///   qualquer target/modo.
/// - **Web release/profile** sem define: `''` → URLs relativas (app e backend
///   no mesmo origin, servido em `/app/`). Contrato inalterado.
/// - **Web debug** sem define: `http://localhost:5000` (backend separado em
///   `flutter run -d chrome`). Contrato inalterado.
/// - **Nativo debug/profile** sem define: `http://localhost:5000` (dev local).
/// - **Nativo RELEASE** sem define: **falha explícita** (fail-closed). Um app
///   publicado jamais deve cair silenciosamente em `localhost:5000` — os
///   workflows de publicação passam `--dart-define=API_BASE_URL` (ver
///   `.github/workflows/deploy-android.yml` / `deploy-ios.yml`).
@visibleForTesting
String resolveApiBaseUrl({
  required bool isWeb,
  required bool isDebugMode,
  required bool isReleaseMode,
  required String apiBaseUrlDefine,
}) {
  if (apiBaseUrlDefine.isNotEmpty) return apiBaseUrlDefine;
  if (isWeb) return isDebugMode ? 'http://localhost:5000' : '';
  if (isReleaseMode) {
    throw StateError(
      'API_BASE_URL ausente em build RELEASE nativo. Compile com '
      '--dart-define=API_BASE_URL=<url do backend> (ver workflows de deploy). '
      'O fallback http://localhost:5000 só vale para debug/desenvolvimento.',
    );
  }
  return 'http://localhost:5000';
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Observabilidade: captura erros de framework como falhas críticas (telemetria
  // por tela para o cutover). Mantém a apresentação padrão do erro.
  final previousOnError = FlutterError.onError;
  FlutterError.onError = (details) {
    AppMonitoring.instance.recordCritical(details.exceptionAsString());
    previousOnError?.call(details);
  };

  final String baseUrl = resolveApiBaseUrl(
    isWeb: kIsWeb,
    isDebugMode: kDebugMode,
    isReleaseMode: kReleaseMode,
    apiBaseUrlDefine: _kApiBaseUrl,
  );

  await ApiClient.init(baseUrl: baseUrl);
  SyncService().startListening();
  final themeNotifier = ThemeModeNotifier();
  final localeProvider = LocaleProvider();
  await Future.wait([themeNotifier.init(), localeProvider.init()]);
  try {
    await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform);
    NotificationService.firebaseAvailable = true;
    await NotificationService().init();
  } catch (_) {
    // Firebase não configurado — app funciona sem push notifications
  }
  runApp(EpiAdminApp(themeNotifier: themeNotifier, localeProvider: localeProvider));
}
