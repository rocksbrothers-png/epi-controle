import 'dart:convert';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/purchases_cubit.dart';

/// Recebimento de PO com quantidade por item. Quando alguma quantidade é menor
/// que a pedida, registra recebimento parcial (exige observação no backend).
///
/// Antes de enviar ao estoque, o administrador informa a **validade do
/// fabricante** de cada EPI (NT 146/2015) para que nenhum item entre em estoque
/// sem data de vencimento. A captura é por lote: a primeira data de um mesmo EPI
/// é aplicada automaticamente aos demais itens daquele EPI, e há leitura por
/// câmera (OCR) para preenchimento automático.
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
  final Map<int, String> _validity = {}; // item id -> 'YYYY-MM-DD'
  final _picker = ImagePicker();
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

  static String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  /// Aplica a data ao item e, por lote, aos demais itens do mesmo EPI ainda sem
  /// data (a primeira data de um EPI serve para todos).
  void _setValidity(int itemId, int epiId, String iso) {
    setState(() {
      _validity[itemId] = iso;
      for (final it in _items) {
        final id = (it['id'] as num?)?.toInt() ?? 0;
        final eid = (it['epi_id'] as num?)?.toInt() ?? 0;
        if (id != itemId && eid == epiId && (_validity[id] ?? '').isEmpty) {
          _validity[id] = iso;
        }
      }
    });
  }

  Future<void> _pickValidityDate(int itemId, int epiId) async {
    final current = DateTime.tryParse(_validity[itemId] ?? '');
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) _setValidity(itemId, epiId, _iso(picked));
  }

  Future<void> _ocrValidityDate(int itemId, int epiId) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final XFile? shot = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1600,
        imageQuality: 85,
      );
      if (shot == null) return;
      final bytes = await shot.readAsBytes();
      final dataUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
      final detected = await ApiClient.stock.detectDateFromImage(
        actorUserId: ApiClient.actorUserId,
        imageData: dataUrl,
      );
      if (detected.isEmpty) {
        messenger.showSnackBar(SnackBar(content: Text(l10n.poOcrDateNotFound)));
        return;
      }
      _setValidity(itemId, epiId, detected);
    } on Exception {
      messenger.showSnackBar(SnackBar(content: Text(l10n.poOcrCameraFailed)));
    }
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
      // Nenhum item entra em estoque sem a validade do fabricante (NT 146/2015).
      if (received > 0 && (_validity[id] ?? '').isEmpty) {
        messenger.showSnackBar(
          SnackBar(content: Text(l10n.poManufacturerValidityRequired)),
        );
        return;
      }
      entries.add({
        'id': id,
        'quantity_received': received,
        'manufacturer_validity_date': _validity[id] ?? '',
      });
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
                  _ReceiveItemRow(
                    name: '${it['epi_name'] ?? ''}',
                    qtyController: _qty[(it['id'] as num?)?.toInt() ?? 0],
                    validity: _validity[(it['id'] as num?)?.toInt() ?? 0] ?? '',
                    onPickDate: () => _pickValidityDate(
                      (it['id'] as num?)?.toInt() ?? 0,
                      (it['epi_id'] as num?)?.toInt() ?? 0,
                    ),
                    onOcr: () => _ocrValidityDate(
                      (it['id'] as num?)?.toInt() ?? 0,
                      (it['epi_id'] as num?)?.toInt() ?? 0,
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

class _ReceiveItemRow extends StatelessWidget {
  const _ReceiveItemRow({
    required this.name,
    required this.qtyController,
    required this.validity,
    required this.onPickDate,
    required this.onOcr,
  });

  final String name;
  final TextEditingController? qtyController;
  final String validity;
  final VoidCallback onPickDate;
  final VoidCallback onOcr;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: EpiSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(name)),
              SizedBox(
                width: 96,
                child: TextField(
                  controller: qtyController,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(labelText: l10n.poQuantityReceived),
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.xs),
          Row(
            children: [
              Expanded(
                child: InkWell(
                  onTap: onPickDate,
                  child: InputDecorator(
                    decoration: InputDecoration(
                      labelText: l10n.poManufacturerValidity,
                      isDense: true,
                    ),
                    child: Text(
                      validity.isEmpty ? l10n.poManufacturerValidityHint : validity,
                      style: TextStyle(
                        color: validity.isEmpty ? EpiColors.danger : null,
                      ),
                    ),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.event_rounded),
                tooltip: l10n.poPickDate,
                onPressed: onPickDate,
              ),
              IconButton(
                icon: const Icon(Icons.photo_camera_rounded),
                tooltip: l10n.poReadDateCamera,
                onPressed: onOcr,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
