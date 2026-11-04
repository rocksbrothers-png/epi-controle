import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/api/api_client.dart';
import '../../core/bloc/auth_cubit.dart';

/// Troca obrigatória de senha no 1º acesso (credencial temporária provisionada
/// por administrador). Enquanto não concluída, o router prende o usuário aqui.
class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  bool _obscure = true;
  bool _saving = false;
  String? _error;
  bool _genericError = false;
  bool _hasValidated = false;
  Locale? _validationLocale;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final locale = Localizations.localeOf(context);
    if (_validationLocale != null &&
        _validationLocale != locale &&
        _hasValidated) {
      // Refresh only errors that the user has already requested through submit.
      // Controllers, validation rules and API/session state stay untouched.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _hasValidated) _formKey.currentState?.validate();
      });
    }
    _validationLocale = locale;
  }

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _genericError = false;
    });
    _hasValidated = true;
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await ApiClient.changePassword(
        currentPassword: _currentCtrl.text,
        newPassword: _newCtrl.text,
      );
      if (!mounted) return;
      // Libera a navegação preservando a sessão atual.
      context.read<AuthCubit>().completePasswordChange();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = e is ApiException ? e.message : null;
        _genericError = e is! ApiException;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(EpiSpacing.xl2),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(
                      Icons.lock_reset_rounded,
                      size: 72,
                      color: EpiColors.brand,
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    Text(
                      AppLocalizations.of(context).passwordChangeTitle,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        color: EpiColors.brand,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xs),
                    Text(
                      AppLocalizations.of(context).passwordChangeIntro,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: EpiColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xl2),
                    TextFormField(
                      controller: _currentCtrl,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: AppLocalizations.of(
                          context,
                        ).passwordChangeCurrent,
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        border: const OutlineInputBorder(),
                      ),
                      validator: (v) => (v == null || v.isEmpty)
                          ? AppLocalizations.of(
                              context,
                            ).passwordChangeCurrentRequired
                          : null,
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextFormField(
                      controller: _newCtrl,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: AppLocalizations.of(
                          context,
                        ).passwordChangeNew,
                        prefixIcon: const Icon(Icons.lock_reset_rounded),
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscure
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.length < 6) {
                          return AppLocalizations.of(
                            context,
                          ).passwordChangeMinLength;
                        }
                        if (v == _currentCtrl.text) {
                          return AppLocalizations.of(
                            context,
                          ).passwordChangeMustDiffer;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextFormField(
                      controller: _confirmCtrl,
                      obscureText: _obscure,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: AppLocalizations.of(
                          context,
                        ).passwordChangeConfirm,
                        prefixIcon: const Icon(
                          Icons.check_circle_outline_rounded,
                        ),
                        border: const OutlineInputBorder(),
                      ),
                      validator: (v) => (v != _newCtrl.text)
                          ? AppLocalizations.of(context).passwordChangeMismatch
                          : null,
                    ),
                    if (_error != null || _genericError) ...[
                      const SizedBox(height: EpiSpacing.lg),
                      Text(
                        _genericError
                            ? AppLocalizations.of(context).passwordChangeFailed
                            : _error!,
                        style: const TextStyle(color: EpiColors.danger),
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: EpiSpacing.xl),
                    EpiButton(
                      label: AppLocalizations.of(context).passwordChangeSave,
                      onPressed: _saving ? null : _submit,
                      loading: _saving,
                      fullWidth: true,
                      size: EpiButtonSize.lg,
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextButton(
                      onPressed: _saving
                          ? null
                          : () => context.read<AuthCubit>().logout(),
                      child: Text(
                        AppLocalizations.of(context).passwordChangeLogout,
                      ),
                    ),
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
