import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kKey = 'theme_mode';

class ThemeModeNotifier extends ChangeNotifier {
  ThemeModeNotifier();

  final _storage = const FlutterSecureStorage();
  ThemeMode _mode = ThemeMode.system;

  ThemeMode get mode => _mode;

  Future<void> init() async {
    final stored = await _storage.read(key: _kKey);
    _mode = _parse(stored);
  }

  Future<void> setMode(ThemeMode mode) async {
    if (_mode == mode) return;
    _mode = mode;
    await _storage.write(key: _kKey, value: _serialize(mode));
    notifyListeners();
  }

  static ThemeMode _parse(String? v) => switch (v) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };

  static String _serialize(ThemeMode m) => switch (m) {
        ThemeMode.light => 'light',
        ThemeMode.dark => 'dark',
        _ => 'system',
      };
}
