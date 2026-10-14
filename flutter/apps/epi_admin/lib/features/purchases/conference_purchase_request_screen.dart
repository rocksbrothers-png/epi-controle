import 'dart:convert';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';

/// EST-V3.5-R3 — Conferência de recebimento de Requisição (PR) com validade
/// física POR LOTE. Reutiliza o backend existente (nenhum segundo mecanismo):
/// POST /api/purchase-requests/{id}/status com `received_items[].lots`; o
/// backend materializa a validade física POR PEÇA a partir dos lotes. NUNCA usa
/// catálogo/CA nem inventa data.
///
/// Modo padrão: uma data + evidência para TODAS as N peças do item. "Separar em
/// lotes": múltiplos lotes (quantidade/validade/evidência/identificação próprias);
/// exceção individual = lote de 1 peça. Peças sem validade comprovada entram
/// BLOQUEADAS (desconhecida), a regularizar depois em Validade e Bloqueios.
class ConferencePurchaseRequestScreen extends StatefulWidget {
  const ConferencePurchaseRequestScreen({super.key, required this.prId});

  final int prId;

  @override
  State<ConferencePurchaseRequestScreen> createState() =>
      _ConferencePurchaseRequestScreenState();
}

class _Lot {
  _Lot({
    required this.key,
    this.quantity = '',
    this.validity = '',
    this.evidence = '',
  });

  final int key;
  String quantity;
  String validity;
  String evidence;
  // Nunca passado no construtor (preenchido só via onChanged do campo de
  // identificação do lote). Inicializado inline para não declarar um parâmetro
  // opcional sem uso — o analyzer 3.47+ emite `unused_element_parameter`
  // (warning) quando um parâmetro opcional de elemento privado nunca recebe
  // valor em nenhuma chamada.
  String lotCode = '';
}

class _ItemState {
  _ItemState({required this.quantity});

  final int quantity; // quantidade efetiva de recebimento (N)
  bool received = true;
  String validity = '';
  String evidence = '';
  bool expanded = false;
  final List<_Lot> lots = <_Lot>[];
}

class _ConferencePurchaseRequestScreenState
    extends State<ConferencePurchaseRequestScreen> {
  final _notes = TextEditingController();
  final _picker = ImagePicker();
  final Map<int, _ItemState> _state = {};
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  int _lotKeySeq = 0;

  static const Set<String> _eligible = {
    'included_in_request',
    'received',
    'not_received',
    'received_partial',
    'approved',
    'ordered',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  int _nextLotKey() => ++_lotKeySeq;

  int _effQty(Map<String, dynamic> it) {
    final v = (it['effective_receive_quantity'] as num?)?.toInt() ?? 0;
    if (v > 0) return v;
    final q = (it['quantity_requested'] as num?)?.toInt() ?? 0;
    return q > 0 ? q : 1;
  }

  Future<void> _load() async {
    try {
      final detail = await ApiClient.purchases.getPurchaseRequest(widget.prId);
      final items = ((detail['items'] as List?) ?? const [])
          .map((e) => (e as Map).cast<String, dynamic>())
          .where((it) => _eligible.contains('${it['status'] ?? ''}'))
          .toList();
      for (final it in items) {
        final id = (it['id'] as num?)?.toInt() ?? 0;
        final st = _ItemState(quantity: _effQty(it));
        st.received = '${it['status'] ?? ''}' != 'not_received';
        _state[id] = st;
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

  static String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  Future<String?> _pickDate(String current) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.tryParse(current) ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    return picked == null ? null : _iso(picked);
  }

  Future<String?> _ocrDate() async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final shot = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1600,
        imageQuality: 85,
      );
      if (shot == null) return null;
      final bytes = await shot.readAsBytes();
      final dataUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
      final detected = await ApiClient.stock.detectDateFromImage(
        actorUserId: ApiClient.actorUserId,
        imageData: dataUrl,
      );
      if (detected.isEmpty) {
        messenger.showSnackBar(SnackBar(content: Text(l10n.poOcrDateNotFound)));
        return null;
      }
      return detected;
    } on Exception {
      messenger.showSnackBar(SnackBar(content: Text(l10n.poOcrCameraFailed)));
      return null;
    }
  }

  /// Lotes efetivos de um item: no modo "lotes", o estado; no modo "único", um
  /// lote sintetizado de N peças com a data/evidência únicas digitadas.
  List<Map<String, dynamic>> _lotsOf(int id) {
    final st = _state[id]!;
    if (st.expanded && st.lots.isNotEmpty) {
      return st.lots
          .map((l) => <String, dynamic>{
                'quantity': int.tryParse(l.quantity.trim()) ?? 0,
                'manufacturer_validity_date': l.validity.trim(),
                'evidence': l.evidence.trim(),
                'lot_code': l.lotCode.trim(),
              })
          .toList();
    }
    return [
      <String, dynamic>{
        'quantity': st.quantity,
        'manufacturer_validity_date': st.validity.trim(),
        'evidence': st.evidence.trim(),
        'lot_code': '',
      }
    ];
  }

  void _expand(int id) {
    final st = _state[id]!;
    setState(() {
      st.expanded = true;
      if (st.lots.isEmpty) {
        st.lots.add(_Lot(
          key: _nextLotKey(),
          quantity: '${st.quantity}',
          validity: st.validity,
          evidence: st.evidence,
        ));
      }
    });
  }

  void _collapse(int id) {
    final st = _state[id]!;
    setState(() {
      st.expanded = false;
      if (st.lots.isNotEmpty) {
        final f = st.lots.first;
        if (st.validity.isEmpty) st.validity = f.validity;
        if (st.evidence.isEmpty) st.evidence = f.evidence;
      }
    });
  }

  Future<void> _submit() async {
    if (_submitting) return;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    setState(() => _error = null);

    final receivedItems = <Map<String, dynamic>>[];
    var hasNotReceived = false;
    for (final it in _items) {
      final id = (it['id'] as num?)?.toInt() ?? 0;
      final st = _state[id]!;
      final lots = _lotsOf(id);
      if (st.received) {
        if (lots.any((l) => (l['quantity'] as int) <= 0)) {
          setState(() => _error = l10n.prConfLotQtyPositive);
          return;
        }
        final sum = lots.fold<int>(
            0, (s, l) => s + ((l['quantity'] as int) > 0 ? l['quantity'] as int : 0));
        if (sum != st.quantity) {
          setState(() => _error = l10n.prConfSumMismatch);
          return;
        }
        for (final l in lots) {
          if ((l['manufacturer_validity_date'] as String).isNotEmpty &&
              (l['evidence'] as String).isEmpty) {
            setState(() => _error = l10n.prConfEvidenceRequired);
            return;
          }
        }
      } else {
        hasNotReceived = true;
      }
      receivedItems.add(<String, dynamic>{
        'id': id,
        'received': st.received,
        'manufacturer_validity_date': st.expanded ? '' : st.validity.trim(),
        'lots': lots,
      });
    }

    if (hasNotReceived && _notes.text.trim().isEmpty) {
      setState(() => _error = l10n.prConfNotesRequired);
      return;
    }

    setState(() => _submitting = true);
    try {
      await ApiClient.purchases.checkPurchaseRequestReceipt(widget.prId, {
        'actor_user_id': ApiClient.actorUserId,
        'status': 'checked',
        'received_items': receivedItems,
        'comment': _notes.text.trim(),
      });
      if (!mounted) return;
      messenger.showSnackBar(SnackBar(content: Text(l10n.prConfDone)));
      navigator.pop(true);
    } on Exception {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = l10n.errorGeneric;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.prConfTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(EpiSpacing.lg),
                    child: Text(l10n.prConfEmpty),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(EpiSpacing.lg),
                  children: [
                    Text(l10n.prConfIntro,
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: EpiSpacing.md),
                    for (final it in _items) _buildItem(context, it),
                    const SizedBox(height: EpiSpacing.sm),
                    TextField(
                      controller: _notes,
                      maxLines: 2,
                      decoration: InputDecoration(labelText: l10n.prConfNotes),
                    ),
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(top: EpiSpacing.sm),
                        child: Text(_error!,
                            style: const TextStyle(color: EpiColors.danger)),
                      ),
                    const SizedBox(height: EpiSpacing.xl),
                    EpiButton(
                      label: l10n.prConfSubmit,
                      onPressed: _submitting ? null : _submit,
                    ),
                  ],
                ),
    );
  }

  Widget _buildItem(BuildContext context, Map<String, dynamic> it) {
    final l10n = AppLocalizations.of(context);
    final id = (it['id'] as num?)?.toInt() ?? 0;
    final st = _state[id]!;
    final name = '${it['epi_name'] ?? it['epi_display_name'] ?? 'EPI'}';
    return Card(
      margin: const EdgeInsets.only(bottom: EpiSpacing.md),
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('$name  (${st.quantity})',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                Switch(
                  value: st.received,
                  onChanged: (v) => setState(() => st.received = v),
                ),
                Text(st.received ? l10n.prConfReceivedYes : l10n.prConfReceivedNo),
              ],
            ),
            if (st.received)
              st.expanded ? _buildLots(context, id, st) : _buildSingle(context, id, st),
          ],
        ),
      ),
    );
  }

  Widget _buildSingle(BuildContext context, int id, _ItemState st) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () async {
                  final d = await _pickDate(st.validity);
                  if (d != null) setState(() => st.validity = d);
                },
                child: InputDecorator(
                  decoration: InputDecoration(
                      labelText: l10n.poManufacturerValidity, isDense: true),
                  child: Text(
                    st.validity.isEmpty ? l10n.poManufacturerValidityHint : st.validity,
                    style: TextStyle(
                        color: st.validity.isEmpty ? EpiColors.danger : null),
                  ),
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.event_rounded),
              tooltip: l10n.poPickDate,
              onPressed: () async {
                final d = await _pickDate(st.validity);
                if (d != null) setState(() => st.validity = d);
              },
            ),
            IconButton(
              icon: const Icon(Icons.photo_camera_rounded),
              tooltip: l10n.poReadDateCamera,
              onPressed: () async {
                final d = await _ocrDate();
                if (d != null) {
                  setState(() {
                    st.validity = d;
                    if (st.evidence.isEmpty) st.evidence = l10n.poReadDateCamera;
                  });
                }
              },
            ),
          ],
        ),
        TextFormField(
          key: ValueKey('ev-$id'),
          initialValue: st.evidence,
          decoration: InputDecoration(
            labelText: l10n.prConfEvidence,
            hintText: l10n.prConfEvidenceHint,
            isDense: true,
          ),
          onChanged: (v) => st.evidence = v,
        ),
        const SizedBox(height: EpiSpacing.xs),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => _expand(id),
            child: Text(l10n.prConfSplitLots),
          ),
        ),
        _previewLine(context, id),
      ],
    );
  }

  Widget _buildLots(BuildContext context, int id, _ItemState st) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final lot in st.lots) _buildLotRow(context, id, st, lot),
        Wrap(
          spacing: EpiSpacing.sm,
          children: [
            TextButton.icon(
              onPressed: () =>
                  setState(() => st.lots.add(_Lot(key: _nextLotKey()))),
              icon: const Icon(Icons.add),
              label: Text(l10n.prConfAddLot),
            ),
            TextButton.icon(
              onPressed: () => setState(
                  () => st.lots.add(_Lot(key: _nextLotKey(), quantity: '1'))),
              icon: const Icon(Icons.add),
              label: Text(l10n.prConfAddException),
            ),
            TextButton(
              onPressed: () => _collapse(id),
              child: Text(l10n.prConfSingleDate),
            ),
          ],
        ),
        _previewLine(context, id),
      ],
    );
  }

  Widget _buildLotRow(BuildContext context, int id, _ItemState st, _Lot lot) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: EpiSpacing.xs),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 60,
                child: TextFormField(
                  key: ValueKey('q${lot.key}'),
                  initialValue: lot.quantity,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                      labelText: l10n.prConfLotQty, isDense: true),
                  onChanged: (v) => setState(() => lot.quantity = v),
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: InkWell(
                  onTap: () async {
                    final d = await _pickDate(lot.validity);
                    if (d != null) setState(() => lot.validity = d);
                  },
                  child: InputDecorator(
                    decoration: InputDecoration(
                        labelText: l10n.poManufacturerValidity, isDense: true),
                    child: Text(
                      lot.validity.isEmpty
                          ? l10n.poManufacturerValidityHint
                          : lot.validity,
                      style: TextStyle(
                          fontSize: 12,
                          color: lot.validity.isEmpty ? EpiColors.danger : null),
                    ),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.photo_camera_rounded),
                tooltip: l10n.poReadDateCamera,
                onPressed: () async {
                  final d = await _ocrDate();
                  if (d != null) {
                    setState(() {
                      lot.validity = d;
                      if (lot.evidence.isEmpty) {
                        lot.evidence = l10n.poReadDateCamera;
                      }
                    });
                  }
                },
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline),
                tooltip: l10n.prConfRemoveLot,
                onPressed: () => setState(() => st.lots.remove(lot)),
              ),
            ],
          ),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  key: ValueKey('ev${lot.key}'),
                  initialValue: lot.evidence,
                  decoration: InputDecoration(
                    labelText: l10n.prConfEvidence,
                    hintText: l10n.prConfEvidenceHint,
                    isDense: true,
                  ),
                  onChanged: (v) => setState(() => lot.evidence = v),
                ),
              ),
              const SizedBox(width: 6),
              SizedBox(
                width: 120,
                child: TextFormField(
                  key: ValueKey('lc${lot.key}'),
                  initialValue: lot.lotCode,
                  decoration: InputDecoration(
                      labelText: l10n.prConfLotCode, isDense: true),
                  onChanged: (v) => lot.lotCode = v,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _previewLine(BuildContext context, int id) {
    final l10n = AppLocalizations.of(context);
    final lots = _lotsOf(id);
    final today = _iso(DateTime.now());
    final parts = <String>[];
    for (final l in lots) {
      final q = l['quantity'] as int;
      final qLabel = q > 0 ? '$q' : '?';
      final date = l['manufacturer_validity_date'] as String;
      if (date.isEmpty) {
        parts.add('$qLabel ${l10n.prConfPiece} → ${l10n.prConfBlocked}');
      } else {
        final expired = date.compareTo(today) < 0;
        parts.add(
            '$qLabel ${l10n.prConfPiece} → $date${expired ? ' ⚠ ${l10n.prConfExpired}' : ''}');
      }
    }
    return Padding(
      padding: const EdgeInsets.only(top: EpiSpacing.xs),
      child: Text('${l10n.prConfPreview}: ${parts.join('; ')}',
          style: Theme.of(context).textTheme.bodySmall),
    );
  }
}
