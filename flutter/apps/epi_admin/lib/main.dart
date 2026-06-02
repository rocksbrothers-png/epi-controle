import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';
import 'core/i18n/theme_mode_notifier.dart';

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
  final themeNotifier = ThemeModeNotifier();
  await themeNotifier.init();
  runApp(EpiAdminApp(themeNotifier: themeNotifier));
}
