import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_design/epi_design.dart';
import 'core/bloc/auth_cubit.dart';
import 'core/bloc/auth_state.dart';
import 'core/i18n/locale_provider.dart';
import 'core/i18n/theme_mode_notifier.dart';
import 'core/notifications/notification_overlay.dart';
import 'core/router/app_router.dart';

class EpiAdminApp extends StatefulWidget {
  const EpiAdminApp({super.key, required this.themeNotifier});

  final ThemeModeNotifier themeNotifier;

  @override
  State<EpiAdminApp> createState() => _EpiAdminAppState();
}

class _EpiAdminAppState extends State<EpiAdminApp> {
  final _localeProvider  = LocaleProvider();
  final _isAuthenticated = ValueNotifier<bool>(false);
  final _authCubit       = AuthCubit();
  late final _router     = buildRouter(
    isAuthenticated: _isAuthenticated,
    localeProvider: _localeProvider,
    themeNotifier: widget.themeNotifier,
  );
  StreamSubscription<AuthState>? _authSub;

  @override
  void initState() {
    super.initState();
    _authSub = _authCubit.stream.listen((state) {
      _isAuthenticated.value = state is AuthAuthenticated;
    });
    _authCubit.tryAutoLogin();
  }

  @override
  void dispose() {
    _authSub?.cancel();
    _authCubit.close();
    _localeProvider.dispose();
    _isAuthenticated.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: _authCubit,
      child: ListenableBuilder(
        listenable: Listenable.merge([_localeProvider, widget.themeNotifier]),
        builder: (context, _) {
          return MaterialApp.router(
            title:                      'EPI Controle',
            debugShowCheckedModeBanner: false,

            theme:     EpiTheme.light,
            darkTheme: EpiTheme.dark,
            themeMode: widget.themeNotifier.mode,

            locale:             _localeProvider.locale,
            supportedLocales:   supportedLocales,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],

            builder: (context, child) =>
                NotificationOverlay(child: child ?? const SizedBox.shrink()),
            routerConfig: _router,
          );
        },
      ),
    );
  }
}
