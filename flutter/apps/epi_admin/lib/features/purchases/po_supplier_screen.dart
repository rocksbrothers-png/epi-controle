import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

import 'data/datasources/purchases_remote_datasource.dart';
import 'data/repository_impl/purchases_repository_impl.dart';
import 'domain/repositories/purchases_repository.dart';

/// Fornecedor e entrega de uma PO (Fase F3): envio ao fornecedor
/// (e-mail/portal), registro manual de confirmação e linha do tempo.
/// O status da PO não muda aqui — apenas os campos paralelos de envio.
class PoSupplierScreen extends StatefulWidget {
  const PoSupplierScreen({super.key, required this.order});
  final Map<String, dynamic> order;

  @override
  State<PoSupplierScreen> createState() => _PoSupplierScreenState();
}

class _PoSupplierScreenState extends State<PoSupplierScreen> {
  final PurchasesRepository _repository =
      const PurchasesRepositoryImpl(ApiPurchasesRemoteDataSource());

  Map<String, dynamic>? _tracking;
  bool _loading = true;
  bool _submitting = false;

  int get _poId => widget.order['id'] as int;
  bool get _sendable {
    final status = '${widget.order['status'] ?? ''}';
    return status == 'approved' || status == 'partially_approved';
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final tracking = await _repository.getPurchaseOrderTracking(_poId);
      if (mounted) setState(() => _tracking = tracking);
    } on Exception catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String message) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _run(Future<void> Function() action,
      {String? successMessage}) async {
    setState(() => _submitting = true);
    try {
      await action();
      if (successMessage != null && mounted) _snack(successMessage);
      await _load();
    } on Exception catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final poNumber =
        '${widget.order['po_number'] ?? widget.order['id'] ?? ''}';
    final confirmations = ((_tracking?['confirmations'] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: Text('${l10n.poSupplierActionsTitle} — $poNumber'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(EpiSpacing.lg),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(EpiSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${widget.order['supplier'] ?? ''}',
                            style:
                                Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: EpiSpacing.xs),
                        Text(
                          [
                            '${widget.order['status'] ?? ''}',
                            if ('${_tracking?['sent_channel'] ?? ''}'
                                .isNotEmpty)
                              '${_tracking?['sent_channel']} — '
                                  '${'${_tracking?['sent_to_supplier_at'] ?? ''}'.split('T').first}',
                            if ('${_tracking?['supplier_confirmation_status'] ?? ''}'
                                .isNotEmpty)
                              '${_tracking?['supplier_confirmation_status']}',
                          ].join(' · '),
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: EpiColors.textMuted),
                        ),
                        const SizedBox(height: EpiSpacing.lg),
                        Wrap(
                          spacing: EpiSpacing.sm,
                          runSpacing: EpiSpacing.sm,
                          children: [
                            FilledButton.icon(
                              icon: const Icon(Icons.mail_outline, size: 18),
                              label: Text(l10n.poSendToSupplier),
                              onPressed: !_sendable || _submitting
                                  ? null
                                  : () => _run(
                                        () => _repository
                                            .sendPurchaseOrderToSupplier(
                                                _poId, {}),
                                        successMessage:
                                            l10n.actionSentSuccess,
                                      ),
                            ),
                            OutlinedButton.icon(
                              icon: const Icon(Icons.link, size: 18),
                              label: Text(l10n.poPortalLinkAction),
                              onPressed: !_sendable || _submitting
                                  ? null
                                  : () => _run(
                                        () => _repository
                                            .sendPurchaseOrderPortalLink(
                                                _poId, {}),
                                        successMessage:
                                            l10n.actionSentSuccess,
                                      ),
                            ),
                            OutlinedButton.icon(
                              icon: const Icon(Icons.fact_check_outlined,
                                  size: 18),
                              label: Text(l10n.poRegisterConfirmation),
                              onPressed: _submitting
                                  ? null
                                  : () => _openConfirmationForm(context),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: EpiSpacing.lg),
                Text(l10n.poTrackingTitle,
                    style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: EpiSpacing.sm),
                if (confirmations.isEmpty)
                  Text(l10n.noResults,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: EpiColors.textMuted))
                else
                  for (final c in confirmations)
                    ListTile(
                      dense: true,
                      leading: const Icon(Icons.local_shipping_outlined),
                      title: Text('${c['status'] ?? ''} · ${c['source'] ?? ''}'),
                      subtitle: Text(
                        [
                          '${c['created_at'] ?? ''}'.split('T').first,
                          if ('${c['delivery_forecast'] ?? ''}'.isNotEmpty)
                            '${l10n.poDeliveryForecastLabel}: '
                                '${c['delivery_forecast']}',
                          if ('${c['carrier'] ?? ''}'.isNotEmpty)
                            '${c['carrier']}',
                          if ('${c['tracking_code'] ?? ''}'.isNotEmpty)
                            '${c['tracking_code']}',
                          if ('${c['comment'] ?? ''}'.isNotEmpty)
                            '${c['comment']}',
                        ].join(' · '),
                      ),
                    ),
              ],
            ),
    );
  }

  Future<void> _openConfirmationForm(BuildContext context) async {
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const _ConfirmationFormDialog(),
    );
    if (body == null) return;
    await _run(
      () => _repository.registerPurchaseOrderConfirmation(_poId, body),
    );
  }
}

class _ConfirmationFormDialog extends StatefulWidget {
  const _ConfirmationFormDialog();

  @override
  State<_ConfirmationFormDialog> createState() =>
      _ConfirmationFormDialogState();
}

class _ConfirmationFormDialogState extends State<_ConfirmationFormDialog> {
  String _status = 'confirmed';
  final _forecast = TextEditingController();
  final _carrier = TextEditingController();
  final _trackingCode = TextEditingController();
  final _comment = TextEditingController();

  @override
  void dispose() {
    _forecast.dispose();
    _carrier.dispose();
    _trackingCode.dispose();
    _comment.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.poRegisterConfirmation),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              value: _status,
              items: const [
                DropdownMenuItem(value: 'confirmed', child: Text('confirmed')),
                DropdownMenuItem(
                    value: 'delivery_update', child: Text('delivery_update')),
                DropdownMenuItem(value: 'rejected', child: Text('rejected')),
              ],
              onChanged: (v) => setState(() => _status = v ?? 'confirmed'),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _forecast,
              decoration: InputDecoration(
                  labelText: l10n.poDeliveryForecastLabel,
                  hintText: 'AAAA-MM-DD'),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _carrier,
              decoration: InputDecoration(labelText: l10n.poCarrierLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _trackingCode,
              decoration:
                  InputDecoration(labelText: l10n.poTrackingCodeLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _comment,
              decoration: InputDecoration(labelText: l10n.commentLabel),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop({
            'status': _status,
            'delivery_forecast': _forecast.text.trim(),
            'carrier': _carrier.text.trim(),
            'tracking_code': _trackingCode.text.trim(),
            'comment': _comment.text.trim(),
          }),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
