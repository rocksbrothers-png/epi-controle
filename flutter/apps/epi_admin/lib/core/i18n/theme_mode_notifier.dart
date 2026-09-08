import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kKey = 'theme_mode';

class ThemeModeNotifier extends ChangeNotifier {
  ThemeModeNotifier();

  final _storage = const FlutterSecureStorage();
  ThemeMode _mode = ThemeMode.system;

  ThemeMode get mode => _mode;

  Future<void> init() async {
    // D2 — a leitura pode lancar: keystore corrompido no Android, storage
    // bloqueado no navegador. Antes, isso subia ate o `main()` e impedia o
    // `runApp` — tela preta em vez de degradacao.
    //
    // O `try` envolve SOMENTE a operacao de storage. Um erro de programacao em
    // `_parse` continua propagando, como deve: a protecao e para a falha de
    // ambiente, nao para esconder defeito nosso.
    String? stored;
    try {
      stored = await _storage.read(key: _kKey);
    } catch (_) {
      stored = null; // sem storage: vale o default, e o app inicia
    }
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
