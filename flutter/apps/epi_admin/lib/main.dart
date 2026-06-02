import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';
import 'core/i18n/theme_mode_notifier.dart';

const _kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:5000',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.init(baseUrl: _kApiBaseUrl);
  final themeNotifier = ThemeModeNotifier();
  await themeNotifier.init();
  runApp(EpiAdminApp(themeNotifier: themeNotifier));
}
