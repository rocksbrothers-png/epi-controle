import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/outsourced_companies_cubit.dart';

/// Cadastro Simplificado de Terceirizados e Prestadores (ADR-0002).
///
/// Subpasta dentro de Cadastro de Colaborador — nasce oculta por padrão em
/// todo tenant; só aparece quando o Administrador Geral liga o módulo
/// `terceirizados` em Configuração → Regras → Visualização
/// (`module_visibility`, mesmo mecanismo que já gateia CNPJs/Estoque/
/// Entregas). A lista chega do backend já escopada à empresa do ator.
class OutsourcedCompaniesScreen extends StatelessWidget {
  const OutsourcedCompaniesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => OutsourcedCompaniesCubit()..load(),
      child: const _OutsourcedCompaniesBody(),
    );
  }
}

class _OutsourcedCompaniesBody extends StatelessWidget {
  const _OutsourcedCompaniesBody();

  Future<void> _openForm(BuildContext context, {OutsourcedCompany? company}) async {
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: _OutsourcedCompanyFormDialog(company: company),
      ),
    );
    if (saved == true && context.mounted) cubit.load();
  }

  Future<void> _confirmPromote(BuildContext context, OutsourcedCompany company) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedCompanyPromoteConfirmTitle),
        content: Text('${company.displayLabel}\n\n${l10n.outsourcedCompanyPromoteConfirmBody}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l10n.outsourcedCompanyPromote),
          ),
        ],
      ),
    );
    if (confirmed == true) await cubit.promoteCompany(company.id);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<OutsourcedCompaniesCubit, OutsourcedCompaniesState>(
      listenWhen: (prev, curr) => prev.error != curr.error && curr.error != null,
      listener: (ctx, state) {
        ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(state.error!)));
      },
      builder: (ctx, state) {
        final items = state.visible;
        return Scaffold(
          appBar: AppBar(title: Text(l10n.outsourcedCompaniesTitle)),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: () => _openForm(ctx),
            icon: const Icon(Icons.add),
            label: Text(l10n.outsourcedCompanyNew),
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
                          labelText: l10n.outsourcedCompaniesSearchHint,
                        ),
                        onChanged: ctx.read<OutsourcedCompaniesCubit>().search,
                      ),
                    ),
                    Expanded(
                      child: items.isEmpty
                          ? Center(child: Text(l10n.outsourcedCompaniesEmpty))
                          : ListView.separated(
                              itemCount: items.length,
                              separatorBuilder: (_, __) => const Divider(height: 1),
                              itemBuilder: (_, i) => _OutsourcedCompanyTile(
                                company: items[i],
                                onEdit: () => _openForm(ctx, company: items[i]),
                                onPromote: () => _confirmPromote(ctx, items[i]),
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

class _OutsourcedCompanyTile extends StatelessWidget {
  const _OutsourcedCompanyTile({
    required this.company,
    required this.onEdit,
    required this.onPromote,
  });

  final OutsourcedCompany company;
  final VoidCallback onEdit;
  final VoidCallback onPromote;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListTile(
      title: Row(
        children: [
          Flexible(child: Text(company.legalName)),
          const SizedBox(width: EpiSpacing.sm),
          Chip(
            label: Text(company.isSimplified
                ? l10n.outsourcedCompanySimplifiedBadge
                : l10n.outsourcedCompanyStandardBadge),
            visualDensity: VisualDensity.compact,
          ),
        ],
      ),
      subtitle: Text(
        [
          if (company.cnpj.isNotEmpty) company.cnpj,
          company.companyKindLabel,
          company.epiResponsibility,
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
          if (company.isSimplified)
            IconButton(
              tooltip: l10n.outsourcedCompanyPromote,
              icon: const Icon(Icons.upgrade_outlined),
              onPressed: onPromote,
            ),
        ],
      ),
    );
  }
}

/// Formulário de criação/edição — cobre Cadastro Simplificado (CNPJ
/// opcional) e Padrão (CNPJ obrigatório, aplicado pelo backend na promoção)
/// com o mesmo conjunto de campos, exatamente como o ADR pede: mesma
/// função de gravação, sem caminho de código separado.
class _OutsourcedCompanyFormDialog extends StatefulWidget {
  const _OutsourcedCompanyFormDialog({this.company});
  final OutsourcedCompany? company;

  @override
  State<_OutsourcedCompanyFormDialog> createState() => _OutsourcedCompanyFormDialogState();
}

class _OutsourcedCompanyFormDialogState extends State<_OutsourcedCompanyFormDialog> {
  // Valores técnicos estáveis (inglês) — condição vinculante do ADR-0002:
  // o rótulo em português vive só na UI (ver _companyKindLabel).
  static const _companyKinds = <String>['outsourced', 'service_provider', 'other_contracted'];

  static const _epiResponsibilities = <String>[
    'Empresa Contratante',
    'Empresa Terceirizada',
    'Empresa Prestadora de Serviço',
    'Responsabilidade Compartilhada',
    'Conforme Contrato',
    'Não Definido',
  ];

  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _legalName;
  late final TextEditingController _tradeName;
  late final TextEditingController _cnpj;
  late String _companyKind;
  late String _epiResponsibility;
  bool _submitting = false;

  bool get _editing => widget.company != null;

  @override
  void initState() {
    super.initState();
    final c = widget.company;
    _legalName = TextEditingController(text: c?.legalName ?? '');
    _tradeName = TextEditingController(text: c?.tradeName ?? '');
    _cnpj = TextEditingController(text: c?.cnpj ?? '');
    _companyKind = c?.companyKind ?? 'outsourced';
    _epiResponsibility = c?.epiResponsibility ?? 'Conforme Contrato';
  }

  @override
  void dispose() {
    for (final c in [_legalName, _tradeName, _cnpj]) {
      c.dispose();
    }
    super.dispose();
  }

  String _companyKindLabel(AppLocalizations l10n, String value) => switch (value) {
        'outsourced' => l10n.outsourcedCompanyKindOutsourced,
        'service_provider' => l10n.outsourcedCompanyKindServiceProvider,
        _ => l10n.outsourcedCompanyKindOther,
      };

  Future<void> _submit() async {
    if (_submitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _submitting = true);
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final navigator = Navigator.of(context);
    final body = <String, dynamic>{
      'legal_name': _legalName.text.trim(),
      'trade_name': _tradeName.text.trim(),
      'cnpj': _cnpj.text.trim(),
      'company_kind': _companyKind,
      'epi_responsibility': _epiResponsibility,
    };
    final ok = _editing
        ? await cubit.updateCompany(widget.company!.id, body)
        : await cubit.createCompany(body);
    if (!mounted) return;
    setState(() => _submitting = false);
    if (ok) navigator.pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? l10n.required : null;

    return AlertDialog(
      title: Text(_editing ? l10n.edit : l10n.outsourcedCompanyNew),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _legalName,
                validator: req,
                decoration: InputDecoration(labelText: l10n.outsourcedCompanyLegalNameLabel),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _tradeName,
                decoration: InputDecoration(labelText: l10n.outsourcedCompanyTradeNameLabel),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextFormField(
                controller: _cnpj,
                decoration: InputDecoration(
                  labelText: l10n.outsourcedCompanyCnpjLabel,
                  helperText: l10n.outsourcedCompanyCnpjHint,
                ),
              ),
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<String>(
                value: _companyKind,
                decoration: InputDecoration(labelText: l10n.outsourcedCompanyKindLabel),
                items: _companyKinds
                    .map((k) => DropdownMenuItem(value: k, child: Text(_companyKindLabel(l10n, k))))
                    .toList(),
                onChanged: (v) => setState(() => _companyKind = v ?? 'outsourced'),
              ),
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<String>(
                value: _epiResponsibility,
                decoration: InputDecoration(labelText: l10n.outsourcedCompanyResponsibilityLabel),
                items: _epiResponsibilities
                    .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                    .toList(),
                onChanged: (v) => setState(() => _epiResponsibility = v ?? 'Conforme Contrato'),
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
