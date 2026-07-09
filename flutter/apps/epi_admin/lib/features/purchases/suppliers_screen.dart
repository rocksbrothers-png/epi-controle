import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

import 'presentation/suppliers_cubit.dart';
import 'supplier_products_screen.dart';

/// Fornecedores autorizados (Fase F3): lista, cadastro/edição e acesso ao
/// catálogo. Validações (CNPJ único, nível de integração) são do backend.
class SuppliersScreen extends StatelessWidget {
  const SuppliersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => SuppliersCubit()..loadSuppliers(),
      child: const _SuppliersBody(),
    );
  }
}

class _SuppliersBody extends StatelessWidget {
  const _SuppliersBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.suppliersTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<SuppliersCubit>().loadSuppliers(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(context),
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.supplierNew),
      ),
      body: BlocBuilder<SuppliersCubit, SuppliersState>(
        builder: (ctx, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.error != null && state.suppliers.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.wifi_off_rounded,
                      size: 48, color: EpiColors.textMuted),
                  const SizedBox(height: EpiSpacing.lg),
                  Text(l10n.errorNetwork),
                  const SizedBox(height: EpiSpacing.xl),
                  EpiButton(
                    label: l10n.retry,
                    onPressed: () =>
                        ctx.read<SuppliersCubit>().loadSuppliers(),
                  ),
                ],
              ),
            );
          }
          if (state.suppliers.isEmpty) {
            return EpiEmptyState(
              title: l10n.noResults,
              icon: Icons.storefront_outlined,
            );
          }
          return RefreshIndicator(
            onRefresh: () => ctx.read<SuppliersCubit>().loadSuppliers(),
            child: ListView.separated(
              padding: const EdgeInsets.only(
                top: EpiSpacing.sm,
                bottom: EpiSpacing.xl5,
              ),
              itemCount: state.suppliers.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 1, indent: 16),
              itemBuilder: (_, i) =>
                  _SupplierTile(supplier: state.suppliers[i]),
            ),
          );
        },
      ),
    );
  }

  static Future<void> _openForm(BuildContext context,
      [Map<String, dynamic>? supplier]) async {
    final cubit = context.read<SuppliersCubit>();
    await showDialog<void>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: _SupplierFormDialog(supplier: supplier),
      ),
    );
  }
}

class _SupplierTile extends StatelessWidget {
  const _SupplierTile({required this.supplier});
  final Map<String, dynamic> supplier;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final active = '${supplier['active'] ?? 1}' == '1';
    final level = '${supplier['integration_level'] ?? 'email'}';
    return ListTile(
      title: Text('${supplier['name'] ?? ''}',
          maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        [
          if ('${supplier['contact_email'] ?? ''}'.isNotEmpty)
            '${supplier['contact_email']}',
          level,
          if (!active) l10n.supplierInactiveLabel,
        ].join(' · '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      leading: Icon(
        Icons.storefront_outlined,
        color: active ? EpiColors.brand : EpiColors.textMuted,
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.inventory_2_outlined),
            tooltip: l10n.supplierCatalogTitle,
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => SupplierProductsScreen(supplier: supplier),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            tooltip: l10n.edit,
            onPressed: () => _SuppliersBody._openForm(context, supplier),
          ),
        ],
      ),
    );
  }
}

class _SupplierFormDialog extends StatefulWidget {
  const _SupplierFormDialog({this.supplier});
  final Map<String, dynamic>? supplier;

  @override
  State<_SupplierFormDialog> createState() => _SupplierFormDialogState();
}

class _SupplierFormDialogState extends State<_SupplierFormDialog> {
  late final TextEditingController _name;
  late final TextEditingController _cnpj;
  late final TextEditingController _email;
  late final TextEditingController _phone;
  late final TextEditingController _paymentTerms;
  late String _integrationLevel;
  late bool _active;

  @override
  void initState() {
    super.initState();
    final s = widget.supplier ?? const <String, dynamic>{};
    _name = TextEditingController(text: '${s['name'] ?? ''}');
    _cnpj = TextEditingController(text: '${s['cnpj'] ?? ''}');
    _email = TextEditingController(text: '${s['contact_email'] ?? ''}');
    _phone = TextEditingController(text: '${s['phone'] ?? ''}');
    _paymentTerms = TextEditingController(text: '${s['payment_terms'] ?? ''}');
    _integrationLevel = '${s['integration_level'] ?? 'email'}';
    _active = '${s['active'] ?? 1}' == '1';
  }

  @override
  void dispose() {
    _name.dispose();
    _cnpj.dispose();
    _email.dispose();
    _phone.dispose();
    _paymentTerms.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final isEdit = widget.supplier != null;
    return AlertDialog(
      title: Text(isEdit ? l10n.supplierEdit : l10n.supplierNew),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _name,
              decoration:
                  InputDecoration(labelText: l10n.employeeNameLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _cnpj,
              decoration:
                  InputDecoration(labelText: l10n.supplierCnpjLabel),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _email,
              decoration:
                  InputDecoration(labelText: l10n.employeeContactEmail),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _phone,
              decoration:
                  InputDecoration(labelText: l10n.supplierPhoneLabel),
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _paymentTerms,
              decoration: InputDecoration(
                  labelText: l10n.supplierPaymentTermsLabel),
            ),
            const SizedBox(height: EpiSpacing.md),
            DropdownButtonFormField<String>(
              value: _integrationLevel,
              decoration: InputDecoration(
                  labelText: l10n.supplierIntegrationLevelLabel),
              items: const [
                DropdownMenuItem(value: 'email', child: Text('E-mail')),
                DropdownMenuItem(value: 'portal', child: Text('Portal')),
                DropdownMenuItem(value: 'api', child: Text('API')),
              ],
              onChanged: (v) =>
                  setState(() => _integrationLevel = v ?? 'email'),
            ),
            if (isEdit) ...[
              const SizedBox(height: EpiSpacing.md),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(l10n.supplierInactiveLabel),
                value: !_active,
                onChanged: (v) => setState(() => _active = !v),
              ),
            ],
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
    final cubit = context.read<SuppliersCubit>();
    final id = widget.supplier?['id'] as int?;
    final ok = await cubit.saveSupplier(
      supplierId: id,
      legacyFields: {
        'name': _name.text.trim(),
        'cnpj': _cnpj.text.trim(),
        'contact_email': _email.text.trim(),
      },
      procurementFields: {
        'phone': _phone.text.trim(),
        'payment_terms': _paymentTerms.text.trim(),
        'integration_level': _integrationLevel,
        if (id != null) 'active': _active ? 1 : 0,
      },
    );
    if (ok && mounted) Navigator.of(context).pop();
  }
}
