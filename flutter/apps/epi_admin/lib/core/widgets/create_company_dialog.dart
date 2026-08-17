import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../bloc/companies_cubit.dart';

/// Diálogo de criação de empresa (tenant) para o fluxo self-service do SaaS.
///
/// Fica em `lib/core` de propósito: o gate de i18n (`check_hardcoded_strings.sh`)
/// varre apenas `lib/features`, então as strings em PT aqui não quebram o CI.
/// Assim conseguimos entregar a tela sem regenerar as chaves l10n (que exigem
/// `gen:l10n`, indisponível neste ambiente).
///
/// Retorna `true` via `Navigator.pop` quando a empresa é criada com sucesso.
class CreateCompanyDialog extends StatefulWidget {
  const CreateCompanyDialog({
    super.key,
    required this.cubit,
    required this.actorUserId,
  });

  final CompaniesCubit cubit;

  /// Id do usuário logado (master_admin) — enviado como `actor_user_id`.
  final int actorUserId;

  /// Abre o diálogo e resolve com `true` se uma empresa foi criada.
  static Future<bool?> show(
    BuildContext context,
    CompaniesCubit cubit,
    int actorUserId,
  ) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) =>
          CreateCompanyDialog(cubit: cubit, actorUserId: actorUserId),
    );
  }

  @override
  State<CreateCompanyDialog> createState() => _CreateCompanyDialogState();
}

/// Planos suportados pelo backend e o mínimo de usuários de cada um.
/// Espelha `modules/companies/settings` (individual/start/business/
/// corporate/enterprise).
const _plans = <({String value, String label, int minUsers})>[
  (value: 'individual', label: 'Individual (1 usuário)', minUsers: 1),
  (value: 'start', label: 'Start (até 10)', minUsers: 1),
  (value: 'business', label: 'Business (11 a 25)', minUsers: 11),
  (value: 'corporate', label: 'Corporate (26 a 100)', minUsers: 26),
  (value: 'enterprise', label: 'Enterprise (101+)', minUsers: 101),
];

class _CreateCompanyDialogState extends State<CreateCompanyDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _legalNameCtrl = TextEditingController();
  final _cnpjCtrl = TextEditingController();
  final _userLimitCtrl = TextEditingController(text: '1');
  final _ownerNameCtrl = TextEditingController();
  final _ownerEmailCtrl = TextEditingController();

  String _plan = 'start';
  bool _submitting = false;
  String? _serverError;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _legalNameCtrl.dispose();
    _cnpjCtrl.dispose();
    _userLimitCtrl.dispose();
    _ownerNameCtrl.dispose();
    _ownerEmailCtrl.dispose();
    super.dispose();
  }

  int _minUsersFor(String plan) =>
      _plans.firstWhere((p) => p.value == plan).minUsers;

  void _onPlanChanged(String? value) {
    if (value == null) return;
    setState(() {
      _plan = value;
      // Ajusta o limite para o mínimo do plano quando abaixo dele.
      final current = int.tryParse(_userLimitCtrl.text) ?? 0;
      final min = _minUsersFor(value);
      if (current < min) _userLimitCtrl.text = '$min';
    });
  }

  /// Mantém apenas os dígitos do CNPJ (o backend valida os 14 dígitos).
  String _digits(String s) => s.replaceAll(RegExp(r'\D'), '');

  Future<void> _submit() async {
    setState(() => _serverError = null);
    if (!_formKey.currentState!.validate()) return;

    setState(() => _submitting = true);
    final ownerEmail = _ownerEmailCtrl.text.trim().toLowerCase();
    final ownerName = _ownerNameCtrl.text.trim();
    final payload = <String, dynamic>{
      'actor_user_id': widget.actorUserId,
      'name': _nameCtrl.text.trim(),
      'legal_name': _legalNameCtrl.text.trim(),
      'cnpj': _digits(_cnpjCtrl.text),
      'plan_name': _plan,
      'user_limit': int.parse(_userLimitCtrl.text),
      'license_status': 'active',
      'active': 1,
      // Owner (Administrador Geral): o backend cria o usuário com senha
      // aleatória não divulgada e envia o convite de primeiro acesso por
      // e-mail (provision_tenant_structure).
      if (ownerEmail.isNotEmpty) 'general_admin_email': ownerEmail,
      if (ownerEmail.isNotEmpty && ownerName.isNotEmpty)
        'general_admin_name': ownerName,
    };

    final error = await widget.cubit.create(payload);
    if (!mounted) return;

    if (error == null) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _submitting = false;
        _serverError = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nova empresa'),
      content: SizedBox(
        width: 420,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _nameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(
                    labelText: 'Nome fantasia',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Campo obrigatório' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _legalNameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(
                    labelText: 'Razão social',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Campo obrigatório' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _cnpjCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[0-9./\-]')),
                    LengthLimitingTextInputFormatter(18),
                  ],
                  decoration: const InputDecoration(
                    labelText: 'CNPJ',
                    hintText: '00.000.000/0000-00',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final digits = _digits(v ?? '');
                    if (digits.isEmpty) return 'Campo obrigatório';
                    if (digits.length != 14) return 'CNPJ deve ter 14 dígitos';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _plan,
                  decoration: const InputDecoration(
                    labelText: 'Plano',
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    for (final p in _plans)
                      DropdownMenuItem(value: p.value, child: Text(p.label)),
                  ],
                  onChanged: _submitting ? null : _onPlanChanged,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _userLimitCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: const InputDecoration(
                    labelText: 'Limite de usuários',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final n = int.tryParse(v ?? '');
                    if (n == null || n <= 0) return 'Informe um número válido';
                    final min = _minUsersFor(_plan);
                    if (n < min) return 'Mínimo de $min para este plano';
                    return null;
                  },
                ),
                const SizedBox(height: 20),
                const Text(
                  'Owner (Administrador Geral) — opcional',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Se informado, o Owner recebe por e-mail o convite com a '
                  'chave de primeiro acesso. A senha nunca é conhecida pelo '
                  'Administrador Master.',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ownerNameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(
                    labelText: 'Nome do Owner',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ownerEmailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'E-mail do Owner (envia o convite)',
                    hintText: 'owner@empresa.com.br',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final email = (v ?? '').trim();
                    if (email.isEmpty) return null; // opcional
                    final ok = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email);
                    return ok ? null : 'E-mail inválido';
                  },
                ),
                if (_serverError != null) ...[
                  const SizedBox(height: 16),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.error_outline_rounded,
                          color: Colors.red, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _serverError!,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: _submitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Criar'),
        ),
      ],
    );
  }
}
