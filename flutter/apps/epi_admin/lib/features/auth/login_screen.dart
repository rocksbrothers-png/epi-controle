import 'package:epi_design/epi_design.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:local_auth/local_auth.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _biometricAvailable = false;

  @override
  void initState() {
    super.initState();
    _checkBiometrics();
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _checkBiometrics() async {
    if (kIsWeb) return; // local_auth não tem suporte na Web
    final localAuth = LocalAuthentication();
    final canCheck = await localAuth.canCheckBiometrics;
    final isSupported = await localAuth.isDeviceSupported();
    if (mounted) {
      setState(() => _biometricAvailable = canCheck || isSupported);
    }
  }

  void _submit() {
    context.read<AuthCubit>().login(
          username: _usernameController.text.trim(),
          password: _passwordController.text,
        );
  }

  void _biometricLogin(String reason) {
    context.read<AuthCubit>().biometricLogin(reason);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Scaffold(
      body: BlocListener<AuthCubit, AuthState>(
        listener: (ctx, state) {
          if (state is! AuthError) return;
          final msg = switch (state.code) {
            'empty' => l10n.loginErrorEmpty,
            'network' => l10n.errorNetwork,
            _ => l10n.loginError,
          };
          ScaffoldMessenger.of(ctx).showSnackBar(
            SnackBar(
              content: Text(msg),
              backgroundColor: EpiColors.danger,
              behavior: SnackBarBehavior.floating,
            ),
          );
        },
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(EpiSpacing.xl2),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(
                      Icons.shield_outlined,
                      size: 72,
                      color: EpiColors.brand,
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    Text(
                      l10n.appName,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineMedium?.copyWith(
                        color: EpiColors.brand,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xs),
                    Text(
                      l10n.loginTitle,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: EpiColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xl3),
                    TextField(
                      controller: _usernameController,
                      textInputAction: TextInputAction.next,
                      autocorrect: false,
                      decoration: InputDecoration(
                        labelText: l10n.loginUsername,
                        hintText: l10n.loginUsernameHint,
                        prefixIcon: const Icon(Icons.person_outline_rounded),
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: l10n.loginPassword,
                        hintText: l10n.loginPasswordHint,
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          tooltip: _obscurePassword
                              ? l10n.loginShowPassword
                              : l10n.loginHidePassword,
                          onPressed: () =>
                              setState(() => _obscurePassword = !_obscurePassword),
                        ),
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.sm),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () {},
                        child: Text(l10n.loginForgotPassword),
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xl),
                    BlocBuilder<AuthCubit, AuthState>(
                      builder: (ctx, state) => EpiButton(
                        label: l10n.loginButton,
                        onPressed: _submit,
                        loading: state is AuthLoading,
                        fullWidth: true,
                        size: EpiButtonSize.lg,
                      ),
                    ),
                    if (_biometricAvailable) ...[
                      const SizedBox(height: EpiSpacing.lg),
                      OutlinedButton.icon(
                        onPressed: () => _biometricLogin(l10n.appName),
                        icon: const Icon(Icons.fingerprint_rounded),
                        label: Text(l10n.loginBiometric),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
