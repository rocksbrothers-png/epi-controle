import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';
import 'core/i18n/theme_mode_notifier.dart';
import 'core/notifications/notification_service.dart';
import 'core/sync/sync_service.dart';
import 'firebase_options.dart';

const _kApiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Web production: empty string → relative URLs (same origin as the Python server).
  // Mobile dev / non-web: fall back to localhost.
  final baseUrl = _kApiBaseUrl.isNotEmpty
      ? _kApiBaseUrl
      : kIsWeb
          ? ''
          : 'http://localhost:5000';
  await ApiClient.init(baseUrl: baseUrl);
  SyncService().startListening();
  final themeNotifier = ThemeModeNotifier();
  await themeNotifier.init();
  try {
    await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform);
    NotificationService.firebaseAvailable = true;
    await NotificationService().init();
  } on Exception {
    // Firebase not yet configured — app runs without push notifications
  }
  runApp(EpiAdminApp(themeNotifier: themeNotifier));
}
