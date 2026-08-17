import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../qr/qr_scanner_screen.dart';

/// Conferência de entrega por QR (item 4).
///
/// Fluxo: escaneia o QR da entrega (ou informa o código) → `handoverLookup`
/// devolve uma projeção SEGURA da entrega (sem expor dado pessoal direto) →
/// o conferente confirma o recebimento com `handoverConfirm`, fechando o ciclo
/// no portal. A REGRA (multi-tenant, projeção, idempotência) é do backend; a
/// tela só orquestra o contrato já mergeado em `packages/epi_api`.
class HandoverConferenceScreen extends StatefulWidget {
  const HandoverConferenceScreen({super.key});

  @override
  State<HandoverConferenceScreen> createState() =>
      _HandoverConferenceScreenState();
}

class _HandoverConferenceScreenState extends State<HandoverConferenceScreen> {
  final _codeCtrl = TextEditingController();
  final _receiverCtrl = TextEditingController();

  bool _loading = false;
  String _code = '';
  Map<String, dynamic>? _handover;
  bool _confirmed = false;

  @override
  void dispose() {
    _codeCtrl.dispose();
    _receiverCtrl.dispose();
    super.dispose();
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _scan() async {
    final code = await Navigator.of(context).push<String>(
      MaterialPageRoute<String>(
        builder: (_) => const QrScannerScreen(returnResult: true),
      ),
    );
    if (code != null && code.trim().isNotEmpty) {
      _codeCtrl.text = code.trim();
      await _lookup();
    }
  }

  Future<void> _lookup() async {
    final l10n = AppLocalizations.of(context);
    final code = _codeCtrl.text.trim();
    if (code.isEmpty) return;
    setState(() => _loading = true);
    try {
      final data = await ApiClient.deliveries.handoverLookup(
        actorUserId: ApiClient.actorUserId,
        code: code,
      );
      if (!mounted) return;
      if (data.isEmpty || (data['delivery_id'] ?? 0) == 0) {
        setState(() => _loading = false);
        _snack(l10n.handoverNotFound);
        return;
      }
      setState(() {
        _loading = false;
        _code = code;
        _handover = data;
        _confirmed = data['already_confirmed'] == true;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
      _snack(l10n.handoverNotFound);
    }
  }

  Future<void> _confirm() async {
    final l10n = AppLocalizations.of(context);
    setState(() => _loading = true);
    try {
      final res = await ApiClient.deliveries.handoverConfirm(
        actorUserId: ApiClient.actorUserId,
        code: _code,
        signatureName: _receiverCtrl.text.trim(),
      );
      if (!mounted) return;
      final ok = res['confirmed'] == true || res['already_confirmed'] == true;
      setState(() {
        _loading = false;
        _confirmed = ok;
      });
      _snack(res['already_confirmed'] == true
          ? l10n.handoverAlreadyConfirmed
          : l10n.handoverConfirmedTitle);
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
      _snack(l10n.handoverConfirmError);
    }
  }

  void _reset() {
    setState(() {
      _handover = null;
      _confirmed = false;
      _code = '';
      _codeCtrl.clear();
      _receiverCtrl.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.handoverTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(EpiSpacing.lg),
              child: _handover == null
                  ? _buildLookupForm(l10n)
                  : _buildHandoverDetail(l10n, _handover!),
            ),
    );
  }

  Widget _buildLookupForm(AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.handoverPrompt,
            style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: EpiSpacing.lg),
        TextField(
          controller: _codeCtrl,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _lookup(),
          decoration: InputDecoration(
            labelText: l10n.handoverCodeLabel,
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.confirmation_number_outlined),
            isDense: true,
          ),
        ),
        const SizedBox(height: EpiSpacing.lg),
        EpiButton(
          label: l10n.handoverScanButton,
          icon: Icons.qr_code_scanner_rounded,
          onPressed: _scan,
          fullWidth: true,
        ),
        const SizedBox(height: EpiSpacing.md),
        EpiButton(
          label: l10n.handoverLookupButton,
          onPressed: _lookup,
          variant: EpiButtonVariant.ghost,
          fullWidth: true,
        ),
      ],
    );
  }

  Widget _buildHandoverDetail(AppLocalizations l10n, Map<String, dynamic> h) {
    String s(String key) => '${h[key] ?? ''}'.trim();
    final employee =
        '${s('employee_first_name')} ${s('employee_last_name')}'.trim();
    final registration = s('employee_registration');
    final qty = h['quantity'] is int ? h['quantity'] as int : 0;
    final qtyLabel = s('quantity_label');
    final qtyText = qtyLabel.isNotEmpty ? '$qty ($qtyLabel)' : '$qty';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_confirmed)
          Container(
            padding: const EdgeInsets.all(EpiSpacing.md),
            margin: const EdgeInsets.only(bottom: EpiSpacing.lg),
            decoration: BoxDecoration(
              color: EpiColors.successSoft,
              borderRadius: BorderRadius.circular(EpiRadius.sm),
              border: Border.all(color: EpiColors.success),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle_outline_rounded,
                    color: EpiColors.success),
                const SizedBox(width: EpiSpacing.sm),
                Expanded(
                  child: Text(
                    h['already_confirmed'] == true
                        ? l10n.handoverAlreadyConfirmed
                        : l10n.handoverConfirmedTitle,
                    style: const TextStyle(
                        color: EpiColors.success, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
        EpiCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _row(l10n.handoverEmployeeLabel,
                  registration.isNotEmpty ? '$employee · $registration' : employee),
              _row(l10n.handoverEpiLabel, _epiText(s)),
              _row(l10n.handoverQuantityLabel, qtyText),
              if (s('sector').isNotEmpty)
                _row(l10n.handoverSectorLabel, s('sector')),
              if (s('role_name').isNotEmpty)
                _row(l10n.handoverRoleLabel, s('role_name')),
              if (s('unit_name').isNotEmpty)
                _row(l10n.handoverUnitLabel, s('unit_name')),
              if (s('delivery_date').isNotEmpty)
                _row(l10n.handoverDeliveryDateLabel, s('delivery_date')),
            ],
          ),
        ),
        const SizedBox(height: EpiSpacing.lg),
        if (!_confirmed) ...[
          TextField(
            controller: _receiverCtrl,
            decoration: InputDecoration(
              labelText: l10n.handoverReceiverNameLabel,
              border: const OutlineInputBorder(),
              isDense: true,
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          EpiButton(
            label: l10n.handoverConfirmButton,
            icon: Icons.check_rounded,
            onPressed: _confirm,
            variant: EpiButtonVariant.success,
            fullWidth: true,
          ),
        ],
        const SizedBox(height: EpiSpacing.md),
        EpiButton(
          label: l10n.handoverScanAgain,
          onPressed: _reset,
          variant: EpiButtonVariant.ghost,
          fullWidth: true,
        ),
      ],
    );
  }

  String _epiText(String Function(String) s) {
    final name = s('epi_name');
    final code = s('epi_code');
    final ca = s('ca');
    final parts = <String>[
      if (name.isNotEmpty) name,
      if (code.isNotEmpty) code,
      if (ca.isNotEmpty) 'CA $ca',
    ];
    return parts.join(' · ');
  }

  Widget _row(String label, String value) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EpiSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 116,
            child: Text(label,
                style: const TextStyle(color: EpiColors.textMuted)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
