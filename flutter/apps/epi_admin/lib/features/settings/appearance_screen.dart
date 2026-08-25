import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/i18n/locale_provider.dart';
import '../../core/i18n/theme_mode_notifier.dart';
import 'widgets/settings_page.dart';

/// Configurações → Aparência e idioma.
///
/// Preferências do próprio aparelho/navegador (não do tenant): tema e idioma.
/// Ficam juntas numa subtela porque são as duas únicas opções que não dependem
/// de empresa selecionada nem de permissão.
class AppearanceScreen extends StatelessWidget {
  const AppearanceScreen({
    super.key,
    required this.localeProvider,
    required this.themeNotifier,
  });

  final LocaleProvider localeProvider;
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    return SettingsSubPage(
      title: AppLocalizations.of(context).settingsAppearanceTitle,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
        child: EpiCard(
          padding: const EdgeInsets.symmetric(vertical: EpiSpacing.xs),
          // Ver `SettingsSection`: o `ListTile` precisa de um `Material` entre
          // ele e o fundo pintado do cartão.
          child: Material(
            type: MaterialType.transparency,
            child: Column(
              children: [
                _ThemeSelector(themeNotifier: themeNotifier),
                const Divider(height: 1),
                _LanguageSelector(localeProvider: localeProvider),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Theme selector ─────────────────────────────────────────────────────────

class _ThemeSelector extends StatelessWidget {
  const _ThemeSelector({required this.themeNotifier});
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final options = [
      (mode: ThemeMode.light, label: l10n.settingsThemeLight),
      (mode: ThemeMode.dark, label: l10n.settingsThemeDark),
      (mode: ThemeMode.system, label: l10n.settingsThemeSystem),
    ];
    return ListenableBuilder(
      listenable: themeNotifier,
      builder: (context, _) {
        return ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
          ),
          leading: const Icon(Icons.palette_outlined, color: EpiColors.brand),
          title: Text(l10n.settingsTheme),
          trailing: SegmentedButton<ThemeMode>(
            segments: options
                .map((o) => ButtonSegment(
                      value: o.mode,
                      label: Text(o.label),
                    ))
                .toList(),
            selected: {themeNotifier.mode},
            onSelectionChanged: (s) => themeNotifier.setMode(s.first),
            showSelectedIcon: false,
          ),
        );
      },
    );
  }
}

// ── Language selector ──────────────────────────────────────────────────────

class _LanguageSelector extends StatelessWidget {
  const _LanguageSelector({required this.localeProvider});
  final LocaleProvider localeProvider;

  static const _locales = [
    (tag: 'pt-BR', label: 'Português (BR)'),
    (tag: 'en-US', label: 'English (US)'),
    (tag: 'es-ES', label: 'Español'),
    (tag: 'fr-FR', label: 'Français'),
    (tag: 'no-NO', label: 'Norsk'),
  ];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListenableBuilder(
      listenable: localeProvider,
      builder: (context, _) {
        final current = '${localeProvider.locale.languageCode}-'
            '${localeProvider.locale.countryCode}';
        return ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
          ),
          leading: const Icon(Icons.language_rounded, color: EpiColors.brand),
          title: Text(l10n.settingsLanguage),
          trailing: DropdownButton<String>(
            value: _locales.any((l) => l.tag == current) ? current : 'pt-BR',
            underline: const SizedBox(),
            items: _locales
                .map((l) => DropdownMenuItem(
                      value: l.tag,
                      child: Text(l.label),
                    ))
                .toList(),
            onChanged: (tag) {
              if (tag == null) return;
              final parts = tag.split('-');
              localeProvider.setLocale(
                Locale(parts[0], parts.length > 1 ? parts[1] : null),
              );
            },
          ),
        );
      },
    );
  }
}
