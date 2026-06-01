import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:epi_design/epi_design.dart';
import 'core/i18n/locale_provider.dart';
import 'core/router/app_router.dart';

class EpiAdminApp extends StatefulWidget {
  const EpiAdminApp({super.key});

  @override
  State<EpiAdminApp> createState() => _EpiAdminAppState();
}

class _EpiAdminAppState extends State<EpiAdminApp> {
  final _localeProvider  = LocaleProvider();
  final _isAuthenticated = ValueNotifier<bool>(false);
  late final _router     = buildRouter(isAuthenticated: _isAuthenticated);

  @override
  void dispose() {
    _localeProvider.dispose();
    _isAuthenticated.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _localeProvider,
      builder: (context, _) {
        return MaterialApp.router(
          title:            'EPI Controle',
          debugShowCheckedModeBanner: false,

          // Design System Themes
          theme:     EpiTheme.light,
          darkTheme: EpiTheme.dark,
          themeMode: ThemeMode.system,

          // i18n
          locale:                       _localeProvider.locale,
          supportedLocales:             supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],

          // Navigation
          routerConfig: _router,
        );
      },
    );
  }
}

// Extension para acesso conveniente: context.l10n.save
extension L10nX on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}
