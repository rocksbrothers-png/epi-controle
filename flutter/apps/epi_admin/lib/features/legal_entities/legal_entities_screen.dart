import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/legal_entities_cubit.dart';
import 'paste_import_dialog.dart';

/// Gestão dos CNPJs (LegalEntity) da empresa — Multi-CNPJ / Joint Venture.
///
/// A lista chega do backend já escopada por papel: Administrador Geral e de
/// Registro veem todos os CNPJs da empresa; Administrador Local, apenas os
/// autorizados; Usuário, somente o do seu colaborador.
class LegalEntitiesScreen extends StatelessWidget {
  const LegalEntitiesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => LegalEntitiesCubit()..load(),
      child: const _LegalEntitiesBody(),
    );
  }
}

class _LegalEntitiesBody extends StatelessWidget {
  const _LegalEntitiesBody();

  Future<void> _openForm(BuildContext context, {LegalEntity? entity}) async {
    final cubit = context.read<LegalEntitiesCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: _LegalEntityFormDialog(entity: entity),
      ),
    );
    if (saved == true && context.mounted) cubit.load();
  }

  Future<void> _openImport(BuildContext context) async {
    final cubit = context.read<LegalEntitiesCubit>();
    await showDialog<bool>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: const PasteImportDialog(),
      ),
    );
    if (context.mounted) cubit.load();
  }

  Future<void> _confirmDeactivate(BuildContext context, LegalEntity entity) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<LegalEntitiesCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.legalEntityDeactivate),
        content: Text('${entity.displayLabel}\n\n${l10n.legalEntityDeactivateHint}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l10n.legalEntityDeactivate),
          ),
        ],
      ),
    );
    if (confirmed == true) await cubit.deactivateEntity(entity.id);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<LegalEntitiesCubit, LegalEntitiesState>(
      listenWhen: (prev, curr) => prev.error != curr.error && curr.error != null,
      listener: (ctx, state) {
        // Erros de regra de negócio do backend (ex.: último CNPJ ativo,
        // colaboradores vinculados) chegam prontos para exibição.
        ScaffoldMessenger.of(ctx)
            .showSnackBar(SnackBar(content: Text(state.error!)));
      },
      builder: (ctx, state) {
        final items = state.visible;
        return Scaffold(
          appBar: AppBar(
            title: Text(l10n.legalEntitiesTitle),
            actions: [
              IconButton(
                tooltip: l10n.legalEntitiesImport,
                icon: const Icon(Icons.upload_file_outlined),
                onPressed: () => _openImport(ctx),
              ),
              IconButton(
                tooltip: l10n.legalEntityShowInactive,
                icon: Icon(state.showInactive
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined),
                onPressed: () => ctx.read<LegalEntitiesCubit>().toggleInactiveView(),
              ),
            ],
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: () => _openForm(ctx),
            icon: const Icon(Icons.add),
            label: Text(l10n.legalEntitiesNew),
          ),
          body: state.isLoading && items.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(EpiSpacing.md),
                      child: TextField(
                        decoration: InputDecoration(
                          prefixIcon: const Icon(Icons.search),
                          labelText: l10n.search,
                        ),
                        onChanged: ctx.read<LegalEntitiesCubit>().search,
                      ),
                    ),
                    Expanded(
                      child: items.isEmpty
                          ? Center(child: Text(l10n.legalEntitiesEmpty))
                          : ListView.separated(
                              itemCount: items.length,
                              separatorBuilder: (_, __) => const Divider(height: 1),
                              itemBuilder: (_, i) => _LegalEntityTile(
                                entity: items[i],
                                onEdit: () => _openForm(ctx, entity: items[i]),
                                onDeactivate: () => _confirmDeactivate(ctx, items[i]),
                              ),
                            ),
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _LegalEntityTile extends StatelessWidget {
  const _LegalEntityTile({
    required this.entity,
    required this.onEdit,
    required this.onDeactivate,
  });

  final LegalEntity entity;
  final VoidCallback onEdit;
  final VoidCallback onDeactivate;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListTile(
      title: Row(
        children: [
          Flexible(child: Text(entity.legalName)),
          if (!entity.active) ...[
            const SizedBox(width: EpiSpacing.sm),
            Chip(
              label: Text(l10n.legalEntityInactiveBadge),
              visualDensity: VisualDensity.compact,
            ),
          ],
        ],
      ),
      subtitle: Text(
        [
          entity.cnpj,
          if (entity.tradeName.isNotEmpty) entity.tradeName,
          entity.entityType,
        ].join(' · '),
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: l10n.edit,
            icon: const Icon(Icons.edit_outlined),
            onPressed: onEdit,
          ),
          if (entity.active)
            IconButton(
              tooltip: l10n.legalEntityDeactivate,
              icon: const Icon(Icons.block_outlined),
              onPressed: onDeactivate,
            ),
        ],
      ),
    );
  }
}

/// Formulário de criação/edição de CNPJ.
class _LegalEntityFormDialog extends StatefulWidget {
  const _LegalEntityFormDialog({this.entity});
  final LegalEntity? entity;

  @override
  State<_LegalEntityFormDialog> createState() => _LegalEntityFormDialogState();
}

class _LegalEntityFormDialogState extends State<_LegalEntityFormDialog> {
  static const _entityTypes = <String>[
    'matriz', 'filial', 'subsidiaria', 'spe', 'jv_partner', 'consorciada', 'outro',
  ];

  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _cnpj;
  late final TextEditingController _legalName;
  late final TextEditingController _tradeName;
  late final TextEditingController _municipality;
  late final TextEditingController _uf;
  late String _entityType;
  bool _submitting = false;

  bool get _editing => widget.entity != null;

  @override
  void initState() {
    super.initState();
    final e = widget.entity;
    _cnpj = TextEditingController(text: e?.cnpj ?? '');
    _legalName = TextEditingController(text: e?.legalName ?? '');
    _tradeName = TextEditingController(text: e?.tradeName ?? '');
    _municipality = TextEditingController(text: e?.municipality ?? '');
    _uf = TextEditingController(text: e?.uf ?? '');
    _entityType = e?.entityType ?? 'filial';
  }

  @override
  void dispose() {
    for (final c in [_cnpj, _legalName, _tradeName, _municipality, _uf]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _submitting = true);
    final cubit = context.read<LegalEntitiesCubit>();
    final navigator = Navigator.of(context);
    final body = <String, dynamic>{
      'cnpj': _cnpj.text.trim(),
      'legal_name': _legalName.text.trim(),
      'trade_name': _tradeName.text.trim(),
      'entity_type': _entityType,
      'municipality': _municipality.text.trim(),
      'uf': _uf.text.trim().toUpperCase(),
      // Edição preserva o estado atual; a inativação tem fluxo próprio.
      'active': (widget.entity?.active ?? true) ? 1 : 0,
    };
    if (_editing) {
      await cubit.updateEntity(widget.entity!.id, body);
    } else {
      await cubit.createEntity(body);
    }
    if (!mounted) return;
    setState(() => _submitting = false);
    // O cubit publica o erro do backend (CNPJ inválido/duplicado, UF inválida);
    // mantém o diálogo aberto para correção.
    if (cubit.state.error == null) navigator.pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? l10n.required : null;

    return AlertDialog(
      title: Text(_editing ? l10n.edit : l10n.legalEntitiesNew),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _cnpj,
                validator: req,
                decoration: const InputDecoration(labelText: 'CNPJ'),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _legalName,
                validator: req,
                decoration:
                    InputDecoration(labelText: l10n.legalEntityLegalNameLabel),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _tradeName,
                decoration:
                    InputDecoration(labelText: l10n.legalEntityTradeNameLabel),
              ),
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<String>(
                value: _entityType,
                decoration: InputDecoration(labelText: l10n.legalEntityTypeLabel),
                items: _entityTypes
                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                    .toList(),
                onChanged: (v) => setState(() => _entityType = v ?? 'filial'),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _municipality,
                decoration: InputDecoration(labelText: l10n.legalEntityMunicipalityLabel),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _uf,
                maxLength: 2,
                decoration: const InputDecoration(labelText: 'UF'),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
