import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Idiomas suportados pelo EPI Controle.
const _supported = [
  Locale('pt', 'BR'),
  Locale('en', 'US'),
  Locale('es', 'ES'),
  Locale('fr', 'FR'),
  Locale('no', 'NO'),
];

List<Locale> get supportedLocales => _supported;

/// Gerencia o idioma ativo.
/// Prioridade: usuário > empresa > sistema operacional > pt-BR
class LocaleProvider extends ChangeNotifier {
  Locale _locale = const Locale('pt', 'BR');

  Locale get locale => _locale;

  /// Aplica preferência do usuário (recebida do /api/bootstrap).
  void applyUserPreference(String? userLocale, String? companyLocale) {
    final resolved = _resolve(userLocale, companyLocale);
    if (resolved != _locale) {
      _locale = resolved;
      notifyListeners();
    }
  }

  /// Troca idioma manualmente (tela de Configurações).
  void setLocale(Locale locale) {
    if (!_supported.contains(locale)) return;
    _locale = locale;
    notifyListeners();
  }

  Locale _resolve(String? userLocale, String? companyLocale) {
    // 1. Preferência do usuário
    if (userLocale != null) {
      final parsed = _parse(userLocale);
      if (parsed != null) return parsed;
    }
    // 2. Idioma da empresa
    if (companyLocale != null) {
      final parsed = _parse(companyLocale);
      if (parsed != null) return parsed;
    }
    // 3. Idioma do sistema operacional
    final system = PlatformDispatcher.instance.locale;
    for (final sup in _supported) {
      if (sup.languageCode == system.languageCode) return sup;
    }
    // 4. Fallback pt-BR
    return const Locale('pt', 'BR');
  }

  Locale? _parse(String tag) {
    final parts = tag.replaceAll('_', '-').split('-');
    if (parts.isEmpty) return null;
    final lang    = parts[0].toLowerCase();
    final country = parts.length > 1 ? parts[1].toUpperCase() : null;
    final candidate = country != null ? Locale(lang, country) : Locale(lang);
    return _supported.contains(candidate) ? candidate : null;
  }
}
