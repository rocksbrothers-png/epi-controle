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

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _error = null);
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
        _error = e is ApiException ? e.message : 'Erro ao trocar a senha';
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
                    const Icon(Icons.lock_reset_rounded,
                        size: 72, color: EpiColors.brand),
                    const SizedBox(height: EpiSpacing.lg),
                    Text(
                      'Defina uma nova senha',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        color: EpiColors.brand,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: EpiSpacing.xs),
                    Text(
                      'Sua senha é temporária. Por segurança, defina uma nova senha para continuar.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium
                          ?.copyWith(color: EpiColors.textMuted),
                    ),
                    const SizedBox(height: EpiSpacing.xl2),
                    TextFormField(
                      controller: _currentCtrl,
                      obscureText: _obscure,
                      decoration: const InputDecoration(
                        labelText: 'Senha atual (temporária)',
                        prefixIcon: Icon(Icons.lock_outline_rounded),
                        border: OutlineInputBorder(),
                      ),
                      validator: (v) => (v == null || v.isEmpty)
                          ? 'Informe a senha atual'
                          : null,
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextFormField(
                      controller: _newCtrl,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'Nova senha',
                        prefixIcon: const Icon(Icons.lock_reset_rounded),
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.length < 6) {
                          return 'A nova senha deve ter ao menos 6 caracteres';
                        }
                        if (v == _currentCtrl.text) {
                          return 'A nova senha deve ser diferente da temporária';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: EpiSpacing.lg),
                    TextFormField(
                      controller: _confirmCtrl,
                      obscureText: _obscure,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: const InputDecoration(
                        labelText: 'Confirmar nova senha',
                        prefixIcon: Icon(Icons.check_circle_outline_rounded),
                        border: OutlineInputBorder(),
                      ),
                      validator: (v) => (v != _newCtrl.text)
                          ? 'As senhas não coincidem'
                          : null,
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: EpiSpacing.lg),
                      Text(
                        _error!,
                        style: const TextStyle(color: EpiColors.danger),
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: EpiSpacing.xl),
                    EpiButton(
                      label: 'Salvar nova senha',
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
                      child: const Text('Sair'),
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
