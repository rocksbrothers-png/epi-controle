import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kKey = 'user_locale';

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
///
/// Contrato (F3): a escolha explicita feita NESTE DISPOSITIVO esta no topo.
///
///   preferencia explicita persistida no dispositivo
///   > preferencia do usuario vinda do backend, se um dia existir
///   > preferencia da empresa, se existir
///   > sistema operacional
///   > pt-BR
///
/// O escopo e por dispositivo/instalacao, por decisao de produto — nao por
/// usuario. Trocar isso e mudanca de contrato, nao correcao.
class LocaleProvider extends ChangeNotifier {
  final _storage = const FlutterSecureStorage();
  Locale _locale = const Locale('pt', 'BR');

  /// `true` somente quando o locale ativo veio de escolha EXPLICITA persistida
  /// neste dispositivo.
  ///
  /// Sem esta distincao, "o usuario escolheu espanhol" e "ninguem escolheu e
  /// caimos no pt-BR" sao indistinguiveis — e foi exatamente por isso que o
  /// fallback passou a vencer a escolha do usuario (D1).
  bool _hasExplicitPreference = false;

  bool get hasExplicitPreference => _hasExplicitPreference;

  Locale get locale => _locale;

  /// Lê a preferência persistida antes do primeiro frame.
  Future<void> init() async {
    // D2 — mesma protecao do tema, e pela mesma razao: falha de storage nao
    // pode impedir o `runApp`. O `try` cobre so a leitura; o parse fica fora.
    String? stored;
    try {
      stored = await _storage.read(key: _kKey);
    } catch (_) {
      stored = null; // sem storage: vale o fallback, e o app inicia
    }
    if (stored != null) {
      final parsed = _parse(stored);
      if (parsed != null) {
        _locale = parsed;
        _hasExplicitPreference = true;
      }
    }
  }

  /// Aplica preferência do usuário/empresa (recebida do /api/bootstrap).
  ///
  /// D1 — nao pode sobrescrever escolha explicita do dispositivo. O backend
  /// HOJE nao emite `preferred_locale` nem `company_locale`: os dois chegam
  /// sempre nulos, `_resolve` cai no sistema operacional, e o resultado
  /// substituia em memoria o idioma que o usuario tinha escolhido — a cada
  /// login, num vai-e-vem com o valor persistido, que nunca era reescrito.
  ///
  /// A correcao NAO e fabricar os campos no servidor. E respeitar o topo do
  /// contrato: havendo escolha explicita neste dispositivo, ela vale.
  void applyUserPreference(String? userLocale, String? companyLocale) {
    if (_hasExplicitPreference) return;
    final resolved = _resolve(userLocale, companyLocale);
    if (resolved != _locale) {
      _locale = resolved;
      notifyListeners();
    }
  }

  /// Troca idioma manualmente (tela de Configurações) e persiste.
  ///
  /// A saida antecipada NAO pode ser so `_locale == locale`: sem preferencia
  /// salva o locale ativo ja pode ser o mesmo por fallback, e ai a escolha
  /// explicita do usuario nao seria persistida nem marcada — voltando a perder
  /// para o fallback no login seguinte. E o mesmo D1 por outro caminho.
  Future<void> setLocale(Locale locale) async {
    if (!_supported.contains(locale)) return;
    if (_locale == locale && _hasExplicitPreference) return;
    final mudou = _locale != locale;
    _locale = locale;
    _hasExplicitPreference = true;
    await _storage.write(key: _kKey, value: '${locale.languageCode}_${locale.countryCode}');
    if (mudou) notifyListeners();
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
