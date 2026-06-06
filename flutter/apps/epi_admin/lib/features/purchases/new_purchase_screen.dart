import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/purchases_cubit.dart';

class NewPurchaseScreen extends StatefulWidget {
  const NewPurchaseScreen({
    super.key,
    required this.epis,
    required this.units,
  });

  final List<Epi> epis;
  final List<Map<String, dynamic>> units;

  @override
  State<NewPurchaseScreen> createState() => _NewPurchaseScreenState();
}

class _NewPurchaseScreenState extends State<NewPurchaseScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _notesController = TextEditingController();

  int? _selectedUnitId;
  final List<_ItemDraft> _items = [];

  @override
  void dispose() {
    _titleController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  List<DropdownMenuItem<int>> get _unitItems => widget.units
      .map((u) => DropdownMenuItem<int>(
            value: u['id'] as int?,
            child: Text(u['name'] as String? ?? ''),
          ))
      .where((item) => item.value != null)
      .toList();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocProvider(
      create: (_) => PurchasesCubit(),
      child: Builder(builder: (ctx) {
        return Scaffold(
          appBar: AppBar(title: Text(l10n.purchasesNew)),
          body: BlocListener<PurchasesCubit, PurchasesState>(
            listenWhen: (p, c) =>
                p.successMessage != c.successMessage || p.error != c.error,
            listener: (ctx, state) {
              if (state.successMessage != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(state.successMessage!),
                    backgroundColor: EpiColors.success,
                  ),
                );
                Navigator.pop(context, true);
              }
              if (state.error != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(state.error!),
                    backgroundColor: EpiColors.danger,
                  ),
                );
              }
            },
            child: Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(EpiSpacing.lg),
                children: [
                  TextFormField(
                    controller: _titleController,
                    decoration: InputDecoration(
                      labelText: l10n.purchaseTitleLabel,
                      border: const OutlineInputBorder(),
                    ),
                    validator: (v) =>
                        (v?.trim().isEmpty ?? true) ? l10n.required : null,
                  ),
                  const SizedBox(height: EpiSpacing.lg),
                  if (_unitItems.isNotEmpty)
                    DropdownButtonFormField<int>(
                      decoration: InputDecoration(
                        labelText: l10n.employeeUnitLabel,
                        border: const OutlineInputBorder(),
                      ),
                      value: _selectedUnitId,
                      items: _unitItems,
                      onChanged: (v) => setState(() => _selectedUnitId = v),
                      validator: (v) =>
                          v == null ? l10n.purchaseSelectUnit : null,
                    ),
                  const SizedBox(height: EpiSpacing.lg),
                  TextFormField(
                    controller: _notesController,
                    decoration: InputDecoration(
                      labelText: l10n.reportsRequestNotes,
                      border: const OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: EpiSpacing.xl),
                  Row(
                    children: [
                      Text(
                        l10n.purchaseItemsTitle,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const Spacer(),
                      TextButton.icon(
                        onPressed: () => _addItem(context),
                        icon: const Icon(Icons.add_rounded),
                        label: Text(l10n.purchaseAddEpi),
                      ),
                    ],
                  ),
                  const Divider(),
                  if (_items.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                          vertical: EpiSpacing.lg),
                      child: Center(
                        child: Text(
                          l10n.purchaseNoItems,
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(color: EpiColors.textMuted),
                        ),
                      ),
                    )
                  else
                    ..._items.asMap().entries.map(
                          (e) => _ItemRow(
                            item: e.value,
                            onRemove: () =>
                                setState(() => _items.removeAt(e.key)),
                            onQtyChanged: (qty) =>
                                setState(() => _items[e.key].quantity = qty),
                          ),
                        ),
                  const SizedBox(height: EpiSpacing.xl2),
                  BlocBuilder<PurchasesCubit, PurchasesState>(
                    builder: (ctx, state) => EpiButton(
                      label: l10n.purchaseCreate,
                      onPressed:
                          state.isSubmitting ? null : () => _submit(ctx),
                      fullWidth: true,
                      size: EpiButtonSize.lg,
                      loading: state.isSubmitting,
                    ),
                  ),
                  const SizedBox(height: EpiSpacing.xl2),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }

  Future<void> _addItem(BuildContext context) async {
    final result = await showModalBottomSheet<_ItemDraft>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius:
            BorderRadius.vertical(top: Radius.circular(EpiRadius.lg)),
      ),
      builder: (_) => _AddItemSheet(epis: widget.epis),
    );
    if (result != null) setState(() => _items.add(result));
  }

  void _submit(BuildContext ctx) {
    if (!_formKey.currentState!.validate()) return;
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(AppLocalizations.of(context).purchaseAddAtLeastOne)),
      );
      return;
    }
    ctx.read<PurchasesCubit>().createRequest(
          unitId: _selectedUnitId!,
          items: _items
              .map((i) => PurchaseRequestItem(
                    epiId: i.epiId,
                    epiName: i.epiName,
                    quantity: i.quantity,
                  ))
              .toList(),
          title: _titleController.text.trim(),
          notes: _notesController.text.trim(),
        );
  }
}

// ── Internal helpers ───────────────────────────────────────────────────────

class _ItemDraft {
  _ItemDraft({required this.epiId, required this.epiName, this.quantity = 1});
  final int epiId;
  final String epiName;
  int quantity;
}

class _ItemRow extends StatelessWidget {
  const _ItemRow({
    required this.item,
    required this.onRemove,
    required this.onQtyChanged,
  });

  final _ItemDraft item;
  final VoidCallback onRemove;
  final void Function(int qty) onQtyChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EpiSpacing.sm),
      child: Row(
        children: [
          Expanded(
              child: Text(item.epiName,
                  style: Theme.of(context).textTheme.bodyMedium)),
          SizedBox(
            width: 80,
            child: TextFormField(
              initialValue: item.quantity.toString(),
              keyboardType: TextInputType.number,
              textAlign: TextAlign.center,
              decoration: const InputDecoration(
                isDense: true,
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: OutlineInputBorder(),
              ),
              onChanged: (v) {
                final qty = int.tryParse(v);
                if (qty != null && qty > 0) onQtyChanged(qty);
              },
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded,
                color: EpiColors.danger),
            onPressed: onRemove,
          ),
        ],
      ),
    );
  }
}

class _AddItemSheet extends StatefulWidget {
  const _AddItemSheet({required this.epis});
  final List<Epi> epis;

  @override
  State<_AddItemSheet> createState() => _AddItemSheetState();
}

class _AddItemSheetState extends State<_AddItemSheet> {
  final _searchController = TextEditingController();
  Epi? _selected;
  int _qty = 1;
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Epi> get _filtered {
    if (_query.isEmpty) return widget.epis;
    final q = _query.toLowerCase();
    return widget.epis
        .where((e) => e.name.toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.viewInsetsOf(context).bottom,
        left: EpiSpacing.lg,
        right: EpiSpacing.lg,
        top: EpiSpacing.lg,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.purchaseAddEpi,
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: EpiSpacing.lg),
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: l10n.searchEpiHint,
              prefixIcon: const Icon(Icons.search_rounded),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (q) => setState(() => _query = q),
          ),
          const SizedBox(height: EpiSpacing.md),
          SizedBox(
            height: 200,
            child: ListView.builder(
              itemCount: _filtered.length,
              itemBuilder: (_, i) {
                final epi = _filtered[i];
                return RadioListTile<Epi>(
                  title: Text(epi.name),
                  value: epi,
                  groupValue: _selected,
                  onChanged: (v) => setState(() => _selected = v),
                  dense: true,
                );
              },
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          Row(
            children: [
              Text(l10n.purchaseQuantityColon),
              const SizedBox(width: EpiSpacing.md),
              SizedBox(
                width: 80,
                child: TextFormField(
                  initialValue: '1',
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  decoration: const InputDecoration(
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  onChanged: (v) {
                    final q = int.tryParse(v);
                    if (q != null && q > 0) setState(() => _qty = q);
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.lg),
          EpiButton(
            label: l10n.add,
            onPressed: _selected == null
                ? null
                : () => Navigator.pop(
                      context,
                      _ItemDraft(
                        epiId: _selected!.id,
                        epiName: _selected!.name,
                        quantity: _qty,
                      ),
                    ),
            fullWidth: true,
          ),
          const SizedBox(height: EpiSpacing.lg),
        ],
      ),
    );
  }
}
