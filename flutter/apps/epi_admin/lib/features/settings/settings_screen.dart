import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/bloc/settings_cubit.dart';
import '../../core/i18n/locale_provider.dart';
import '../../core/i18n/theme_mode_notifier.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({
    super.key,
    required this.localeProvider,
    required this.themeNotifier,
  });

  final LocaleProvider localeProvider;
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => SettingsCubit()..load(),
      child: _SettingsBody(
        localeProvider: localeProvider,
        themeNotifier: themeNotifier,
      ),
    );
  }
}

class _SettingsBody extends StatelessWidget {
  const _SettingsBody({
    required this.localeProvider,
    required this.themeNotifier,
  });

  final LocaleProvider localeProvider;
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: BlocConsumer<SettingsCubit, SettingsState>(
        listenWhen: (p, c) =>
            p.successMessage != c.successMessage || p.error != c.error,
        listener: (ctx, state) {
          if (state.successMessage != null) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(content: Text(AppLocalizations.of(ctx).settingsSaved)),
            );
          }
          if (state.error != null) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(
                content: Text(state.error!),
                backgroundColor: EpiColors.danger,
              ),
            );
          }
        },
        builder: (ctx, state) {
          return ListView(
            padding: const EdgeInsets.only(bottom: EpiSpacing.xl5),
            children: [
              _SectionHeader(label: l10n.settingsAppSection),
              _ThemeSelector(themeNotifier: themeNotifier),
              const Divider(height: 1),
              _LanguageSelector(localeProvider: localeProvider),
              const SizedBox(height: EpiSpacing.lg),
              _SectionHeader(label: l10n.settingsFichaSection),
              if (state.isLoading)
                const Padding(
                  padding: EdgeInsets.all(EpiSpacing.xl),
                  child: Center(child: CircularProgressIndicator()),
                )
              else
                _FichaConfigForm(
                  config: state.config ?? const FichaConfig(),
                  isSaving: state.isSaving,
                ),
            ],
          );
        },
      ),
    );
  }
}

// ── Section header ─────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.xl,
        EpiSpacing.lg,
        EpiSpacing.sm,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: EpiColors.brand,
              letterSpacing: 0.5,
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

// ── Ficha config form ──────────────────────────────────────────────────────

class _FichaConfigForm extends StatefulWidget {
  const _FichaConfigForm({required this.config, required this.isSaving});
  final FichaConfig config;
  final bool isSaving;

  @override
  State<_FichaConfigForm> createState() => _FichaConfigFormState();
}

class _FichaConfigFormState extends State<_FichaConfigForm> {
  late final TextEditingController _titulo;
  late final TextEditingController _declaracao;
  late final TextEditingController _observacoes;
  late bool _rastreabilidade;

  @override
  void initState() {
    super.initState();
    _titulo = TextEditingController(text: widget.config.titulo);
    _declaracao = TextEditingController(text: widget.config.declaracao);
    _observacoes = TextEditingController(text: widget.config.observacoes);
    _rastreabilidade = widget.config.rastreabilidade;
  }

  @override
  void didUpdateWidget(_FichaConfigForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.config != widget.config) {
      _titulo.text = widget.config.titulo;
      _declaracao.text = widget.config.declaracao;
      _observacoes.text = widget.config.observacoes;
      _rastreabilidade = widget.config.rastreabilidade;
    }
  }

  @override
  void dispose() {
    _titulo.dispose();
    _declaracao.dispose();
    _observacoes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _titulo,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaTitle,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _declaracao,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaDeclaration,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _observacoes,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaObservations,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.sm),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.settingsFichaTracking),
            value: _rastreabilidade,
            onChanged: (v) => setState(() => _rastreabilidade = v),
          ),
          const SizedBox(height: EpiSpacing.lg),
          EpiButton(
            label: l10n.save,
            loading: widget.isSaving,
            fullWidth: true,
            onPressed: widget.isSaving ? null : _save,
          ),
          const SizedBox(height: EpiSpacing.xl),
        ],
      ),
    );
  }

  void _save() {
    context.read<SettingsCubit>().save(
          widget.config.copyWith(
            titulo: _titulo.text,
            declaracao: _declaracao.text,
            observacoes: _observacoes.text,
            rastreabilidade: _rastreabilidade,
          ),
        );
  }
}
