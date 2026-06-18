import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/purchases_cubit.dart';

/// Recebimento de PO com quantidade por item. Quando alguma quantidade é menor
/// que a pedida, registra recebimento parcial (exige observação no backend).
class ReceivePurchaseOrderScreen extends StatefulWidget {
  const ReceivePurchaseOrderScreen({super.key, required this.cubit, required this.poId});
  final PurchasesCubit cubit;
  final int poId;

  @override
  State<ReceivePurchaseOrderScreen> createState() => _ReceivePurchaseOrderScreenState();
}

class _ReceivePurchaseOrderScreenState extends State<ReceivePurchaseOrderScreen> {
  final _notes = TextEditingController();
  final Map<int, TextEditingController> _qty = {};
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final detail = await ApiClient.purchases.getPurchaseOrder(widget.poId);
      final items = ((detail['items'] as List?) ?? const [])
          .map((e) => (e as Map).cast<String, dynamic>())
          .toList();
      for (final it in items) {
        final id = (it['id'] as num?)?.toInt() ?? 0;
        final qty = (it['quantity'] as num?)?.toInt() ?? 0;
        _qty[id] = TextEditingController(text: '$qty');
      }
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _notes.dispose();
    for (final c in _qty.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final entries = <Map<String, dynamic>>[];
    var partial = false;
    for (final it in _items) {
      final id = (it['id'] as num?)?.toInt() ?? 0;
      final ordered = (it['quantity'] as num?)?.toInt() ?? 0;
      final received = int.tryParse(_qty[id]?.text.trim() ?? '') ?? 0;
      if (received < ordered) partial = true;
      entries.add({'id': id, 'quantity_received': received});
    }
    if (partial && _notes.text.trim().isEmpty) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.required)));
      return;
    }
    setState(() => _submitting = true);
    final ok = await widget.cubit.receivePurchaseOrder(widget.poId, {
      'action': partial ? 'received_partial' : 'received',
      'items': entries,
      'notes': _notes.text.trim(),
    });
    if (!mounted) return;
    setState(() => _submitting = false);
    if (ok) {
      navigator.pop();
    } else {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorGeneric)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.poReceive)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(EpiSpacing.lg),
              children: [
                for (final it in _items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: EpiSpacing.md),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text('${it['epi_name'] ?? ''}'),
                        ),
                        SizedBox(
                          width: 96,
                          child: TextField(
                            controller: _qty[(it['id'] as num?)?.toInt() ?? 0],
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(labelText: l10n.poQuantityReceived),
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: EpiSpacing.sm),
                TextField(
                  controller: _notes,
                  decoration: InputDecoration(labelText: l10n.poReceiveNotes),
                ),
                const SizedBox(height: EpiSpacing.xl),
                EpiButton(
                  label: l10n.poReceive,
                  onPressed: _submitting ? null : _submit,
                ),
              ],
            ),
    );
  }
}
