import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

import 'presentation/suppliers_cubit.dart';

/// Catálogo de produtos de um fornecedor (Fase F3): lista, upsert por SKU e
/// desativação. Preço/prazo alimentam as cotações futuras.
class SupplierProductsScreen extends StatelessWidget {
  const SupplierProductsScreen({super.key, required this.supplier});
  final Map<String, dynamic> supplier;

  int get _supplierId => supplier['id'] as int;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => SuppliersCubit()..loadProducts(_supplierId),
      child: _ProductsBody(supplier: supplier),
    );
  }
}

class _ProductsBody extends StatelessWidget {
  const _ProductsBody({required this.supplier});
  final Map<String, dynamic> supplier;

  int get _supplierId => supplier['id'] as int;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('${l10n.supplierCatalogTitle} — ${supplier['name']}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () =>
                context.read<SuppliersCubit>().loadProducts(_supplierId),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(context),
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.catalogNewProduct),
      ),
      body: BlocBuilder<SuppliersCubit, SuppliersState>(
        builder: (ctx, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.error != null && state.products.isEmpty) {
            return Center(
              child: EpiButton(
                label: l10n.retry,
                onPressed: () =>
                    ctx.read<SuppliersCubit>().loadProducts(_supplierId),
              ),
            );
          }
          if (state.products.isEmpty) {
            return EpiEmptyState(
              title: l10n.noResults,
              icon: Icons.inventory_2_outlined,
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.only(
              top: EpiSpacing.sm,
              bottom: EpiSpacing.xl5,
            ),
            itemCount: state.products.length,
            separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
            itemBuilder: (_, i) {
              final p = state.products[i];
              final price = double.tryParse('${p['last_price'] ?? 0}') ?? 0;
              final lead = '${p['lead_time_days'] ?? 0}';
              return ListTile(
                title: Text(
                  '${p['description'] ?? p['supplier_sku'] ?? ''}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text(
                  [
                    if ('${p['supplier_sku'] ?? ''}'.isNotEmpty)
                      'SKU ${p['supplier_sku']}',
                    if ('${p['ca'] ?? ''}'.isNotEmpty)
                      '${l10n.epiCaLabel} ${p['ca']}',
                    if (price > 0)
                      '${l10n.catalogLastPriceLabel}: '
                          'R\$ ${price.toStringAsFixed(2)}',
                    if (lead != '0') '${l10n.catalogLeadTimeLabel}: $lead',
                  ].join(' · '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.edit_outlined),
                      tooltip: l10n.edit,
                      onPressed: () => _openForm(context, p),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline),
                      tooltip: l10n.delete,
                      onPressed: () => ctx
                          .read<SuppliersCubit>()
                          .deactivateProduct(_supplierId, p['id'] as int),
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _openForm(BuildContext context,
      [Map<String, dynamic>? product]) async {
    final cubit = context.read<SuppliersCubit>();
    await showDialog<void>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: _ProductFormDialog(supplierId: _supplierId, product: product),
      ),
    );
  }
}

class _ProductFormDialog extends StatefulWidget {
  const _ProductFormDialog({required this.supplierId, this.product});
  final int supplierId;
  final Map<String, dynamic>? product;

  @override
  State<_ProductFormDialog> createState() => _ProductFormDialogState();
}

class _ProductFormDialogState extends State<_ProductFormDialog> {
  late final TextEditingController _sku;
  late final TextEditingController _description;
  late final TextEditingController _ca;
  late final TextEditingController _price;
  late final TextEditingController _leadTime;

  @override
  void initState() {
    super.initState();
    final p = widget.product ?? const <String, dynamic>{};
    _sku = TextEditingController(text: '${p['supplier_sku'] ?? ''}');
    _description = TextEditingController(text: '${p['description'] ?? ''}');
    _ca = TextEditingController(text: '${p['ca'] ?? ''}');
    _price = TextEditingController(
        text: p['last_price'] == null ? '' : '${p['last_price']}');
    _leadTime = TextEditingController(
        text: p['lead_time_days'] == null ? '' : '${p['lead_time_days']}');
  }

  @override
  void dispose() {
    _sku.dispose();
    _description.dispose();
    _ca.dispose();
    _price.dispose();
    _leadTime.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.catalogNewProduct),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _sku,
              decoration: InputDecoration(labelText: l10n.catalogSkuLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _description,
              decoration:
                  InputDecoration(labelText: l10n.catalogDescriptionLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _ca,
              decoration: InputDecoration(labelText: l10n.epiCaLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _price,
              decoration:
                  InputDecoration(labelText: l10n.catalogLastPriceLabel),
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _leadTime,
              decoration:
                  InputDecoration(labelText: l10n.catalogLeadTimeLabel),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        BlocBuilder<SuppliersCubit, SuppliersState>(
          builder: (ctx, state) => FilledButton(
            onPressed: state.isSubmitting ? null : () => _save(ctx),
            child: Text(l10n.save),
          ),
        ),
      ],
    );
  }

  Future<void> _save(BuildContext context) async {
    final ok = await context.read<SuppliersCubit>().saveProduct(
      widget.supplierId,
      {
        'supplier_sku': _sku.text.trim(),
        'description': _description.text.trim(),
        'ca': _ca.text.trim(),
        'last_price': double.tryParse(_price.text.replaceAll(',', '.')) ?? 0,
        'lead_time_days': int.tryParse(_leadTime.text) ?? 0,
      },
    );
    if (ok && mounted) Navigator.of(context).pop();
  }
}
