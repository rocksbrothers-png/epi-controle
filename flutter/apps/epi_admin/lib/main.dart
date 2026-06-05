import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;
import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';
import 'core/i18n/locale_provider.dart';
import 'core/i18n/theme_mode_notifier.dart';
import 'core/notifications/notification_service.dart';
import 'core/sync/sync_service.dart';
import 'firebase_options.dart';

// Configurável via: flutter run --dart-define=API_BASE_URL=https://api.example.com
// Produção Web (co-deploy com backend): API_BASE_URL vazio → URLs relativas (mesmo origin).
// Dev Web (flutter run -d chrome): usa localhost:5000 automaticamente em kDebugMode.
const _kApiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final String baseUrl;
  if (_kApiBaseUrl.isNotEmpty) {
    baseUrl = _kApiBaseUrl;
  } else if (kIsWeb) {
    // Release Web: app e backend no mesmo origin → URLs relativas.
    // Debug Web: flutter run -d chrome → backend corre separado na porta 5000.
    baseUrl = kDebugMode ? 'http://localhost:5000' : '';
  } else {
    baseUrl = 'http://localhost:5000';
  }

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
