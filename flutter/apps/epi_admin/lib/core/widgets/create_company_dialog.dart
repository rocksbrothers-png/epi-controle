import '../i18n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../bloc/companies_cubit.dart';

/// Diálogo de criação de empresa (tenant) para o fluxo self-service do SaaS.
///
/// Presentation uses the current locale; plan values and provisioning stay canonical.
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
  (value: 'individual', label: 'individual', minUsers: 1),
  (value: 'start', label: 'start', minUsers: 1),
  (value: 'business', label: 'business', minUsers: 11),
  (value: 'corporate', label: 'corporate', minUsers: 26),
  (value: 'enterprise', label: 'enterprise', minUsers: 101),
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
  bool _validationAttempted = false;
  String? _serverError;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_validationAttempted) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _formKey.currentState?.validate();
      });
    }
  }

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
    _validationAttempted = true;
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
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.companyNewTitle),
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
                  decoration: InputDecoration(
                    labelText: l10n.legalEntityTradeNameLabel,
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? l10n.required : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _legalNameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: InputDecoration(
                    labelText: l10n.legalEntityLegalNameLabel,
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? l10n.required : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _cnpjCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[0-9./\-]')),
                    LengthLimitingTextInputFormatter(18),
                  ],
                  decoration: InputDecoration(
                    labelText: l10n.legalEntityCnpjLabel,
                    hintText: '00.000.000/0000-00',
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final digits = _digits(v ?? '');
                    if (digits.isEmpty) return l10n.required;
                    if (digits.length != 14) return l10n.companyCnpjLength;
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _plan,
                  isExpanded: true,
                  itemHeight: null,
                  decoration: InputDecoration(
                    labelText: l10n.myCompanyPlan,
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    for (final p in _plans)
                      DropdownMenuItem(
                        value: p.value,
                        child: Text(switch (p.value) {
                          'individual' => l10n.companyPlanIndividual,
                          'start' => l10n.companyPlanStart,
                          'business' => l10n.companyPlanBusiness,
                          'corporate' => l10n.companyPlanCorporate,
                          _ => 'Enterprise (101+)',
                        }),
                      ),
                  ],
                  onChanged: _submitting ? null : _onPlanChanged,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _userLimitCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: InputDecoration(
                    labelText: l10n.companyUserLimit,
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final n = int.tryParse(v ?? '');
                    if (n == null || n <= 0) return l10n.formValidNumber;
                    final min = _minUsersFor(_plan);
                    if (n < min) return l10n.companyMinimumUsers(min);
                    return null;
                  },
                ),
                const SizedBox(height: 20),
                Text(
                  l10n.companyOwnerOptional(l10n.roleGeneralAdmin),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  l10n.companyOwnerInviteHint(l10n.roleMasterAdmin),
                  style: const TextStyle(fontSize: 12, color: Colors.black54),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ownerNameCtrl,
                  textCapitalization: TextCapitalization.words,
                  decoration: InputDecoration(
                    labelText: l10n.companyOwnerName,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _ownerEmailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: l10n.companyOwnerEmail,
                    hintText: 'owner@empresa.com.br',
                    border: const OutlineInputBorder(),
                  ),
                  validator: (v) {
                    final email = (v ?? '').trim();
                    if (email.isEmpty) return null; // opcional
                    final ok = RegExp(
                      r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
                    ).hasMatch(email);
                    return ok ? null : l10n.formValidEmail;
                  },
                ),
                if (_serverError != null) ...[
                  const SizedBox(height: 16),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.error_outline_rounded,
                        color: Colors.red,
                        size: 18,
                      ),
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
          onPressed: _submitting
              ? null
              : () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: _submitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(l10n.add),
        ),
      ],
    );
  }
}
