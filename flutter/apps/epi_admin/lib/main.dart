import 'package:flutter/material.dart';
import 'app.dart';
import 'core/api/api_client.dart';

const _kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:5000',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.init(baseUrl: _kApiBaseUrl);
  runApp(const EpiAdminApp());
}
