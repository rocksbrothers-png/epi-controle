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
  final define = apiBaseUrlDefine;
  // Web: contrato inalterado — define explícito (split deploy) ou same-origin
  // (release) / localhost (debug).
  if (isWeb) {
    if (define.isNotEmpty) return define;
    return isDebugMode ? 'http://localhost:5000' : '';
  }
  // Nativo RELEASE: fail-closed + validação ESTRUTURAL (defesa em profundidade).
  // Product-agnostic de propósito: NÃO amarra a um domínio (a allowlist por
  // produto é imposta no workflow, antes do build — ver ci/api_backend_guard.py),
  // para que este arquivo permaneça idêntico nos dois repositórios (paridade).
  if (isReleaseMode) {
    final value = define.trim();
    if (value.isEmpty) {
      throw StateError(
        'API_BASE_URL ausente em build RELEASE nativo. Compile com '
        '--dart-define=API_BASE_URL=<url https do backend do produto> '
        '(ver workflows de deploy). O fallback localhost só vale para debug.',
      );
    }
    if (!_isStructurallyValidReleaseUrl(value)) {
      throw StateError(
        'API_BASE_URL inválida para RELEASE nativo: "$value". Exigido https, '
        'host real (sem localhost/loopback), sem userinfo (user:pass@) nem '
        'fragmento (#...).',
      );
    }
    return value;
  }
  // Nativo debug/profile: contrato inalterado — localhost permitido; um define
  // explícito continua valendo.
  if (define.isNotEmpty) return define;
  return 'http://localhost:5000';
}

/// Validação estrutural (sem domínio) de uma API_BASE_URL para release nativo.
/// Não substitui a allowlist por produto do workflow; é defesa em profundidade
/// contra localhost/http/whitespace/malformada embutidos no binário publicado.
bool _isStructurallyValidReleaseUrl(String value) {
  final uri = Uri.tryParse(value);
  if (uri == null) return false;
  if (uri.scheme != 'https') return false;
  if (uri.host.isEmpty) return false;
  if (uri.userInfo.isNotEmpty) return false;
  if (uri.hasFragment) return false;
  const loopback = {'localhost', '127.0.0.1', '::1', '0.0.0.0', '10.0.2.2'};
  if (loopback.contains(uri.host.toLowerCase())) return false;
  return true;
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
