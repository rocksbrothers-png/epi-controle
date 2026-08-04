import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/outsourced_companies_cubit.dart';
import '../../core/bloc/outsourced_employees_cubit.dart';
import 'outsourced_employees_reports_tab.dart';
import 'outsourced_employees_tab.dart';

/// Cadastro Simplificado de Terceirizados e Prestadores (ADR-0002), agora
/// com o Cadastro de Colaboradores simplificado (ADR-0002 §10) como aba
/// irmã dentro da mesma tela.
///
/// A tela em si só é alcançável quando o ator tem `employees:create` OU
/// `employees:create_simplified` — cada uma dessas duas permissões abre uma
/// aba diferente (Empresas / Cadastro de Colaboradores). module_visibility
/// (`terceirizados`/`terceirizados_colaboradores`) segue a mesma regra:
/// oculto por padrão em todo tenant até o Administrador Geral ligar,
/// agora também configurável por Unidade (module_unit_scope). O backend é a
/// autoridade final em ambos os casos — esta tela só orienta a navegação.
class OutsourcedCompaniesScreen extends StatefulWidget {
  const OutsourcedCompaniesScreen({super.key});

  @override
  State<OutsourcedCompaniesScreen> createState() => _OutsourcedCompaniesScreenState();
}

class _OutsourcedCompaniesScreenState extends State<OutsourcedCompaniesScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _canCompanies = false;
  bool _canEmployees = false;

  @override
  void initState() {
    super.initState();
    final authState = context.read<AuthCubit>().state;
    if (authState is AuthAuthenticated) {
      _canCompanies = authState.permissions.contains('employees:create') &&
          authState.isModuleVisible('terceirizados');
      _canEmployees = authState.permissions.contains('employees:create_simplified') &&
          authState.isModuleVisible('terceirizados_colaboradores');
    }
    final tabCount = (_canCompanies ? 1 : 0) + (_canEmployees ? 1 : 0) + 1;
    _tabController = TabController(length: tabCount, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.outsourcedCompaniesTitle),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            if (_canCompanies) Tab(text: l10n.outsourcedTabCompanies),
            if (_canEmployees) Tab(text: l10n.outsourcedTabEmployees),
            Tab(text: l10n.outsourcedTabReports),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          if (_canCompanies)
            BlocProvider(
              create: (_) => OutsourcedCompaniesCubit()..load(),
              child: const _CompaniesTabBody(),
            ),
          if (_canEmployees)
            BlocProvider(
              create: (_) => OutsourcedEmployeesCubit()..load(),
              child: const OutsourcedEmployeesTab(),
            ),
          const OutsourcedEmployeesReportsTab(),
        ],
      ),
    );
  }
}

class _CompaniesTabBody extends StatelessWidget {
  const _CompaniesTabBody();

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

  Future<void> _confirmArchive(BuildContext context, OutsourcedCompany company) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedCompanyArchiveConfirmTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(company.displayLabel),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: reasonController,
              decoration: InputDecoration(labelText: l10n.archiveReasonLabel),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: EpiColors.danger),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l10n.outsourcedCompanyArchive),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.archiveCompany(company.id, reason: reasonController.text.trim());
    }
  }

  Future<void> _confirmRestore(BuildContext context, Map<String, dynamic> company) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedCompanyRestoreConfirmTitle),
        content: Text('${company['legal_name'] ?? ''}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l10n.outsourcedCompanyRestore),
          ),
        ],
      ),
    );
    if (confirmed == true) await cubit.restoreCompany((company['id'] as num).toInt());
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
        return Scaffold(
          floatingActionButton: state.showArchived
              ? null
              : FloatingActionButton.extended(
                  onPressed: () => _openForm(ctx),
                  icon: const Icon(Icons.add),
                  label: Text(l10n.outsourcedCompanyNew),
                ),
          body: state.isLoading && state.companies.isEmpty && state.archivedCompanies.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(EpiSpacing.md),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              decoration: InputDecoration(
                                prefixIcon: const Icon(Icons.search),
                                labelText: l10n.outsourcedCompaniesSearchHint,
                              ),
                              onChanged: ctx.read<OutsourcedCompaniesCubit>().search,
                            ),
                          ),
                          IconButton(
                            tooltip: state.showArchived
                                ? l10n.outsourcedShowActive
                                : l10n.outsourcedShowArchived,
                            icon: Icon(
                              state.showArchived
                                  ? Icons.business_outlined
                                  : Icons.inventory_2_outlined,
                            ),
                            onPressed: () => ctx.read<OutsourcedCompaniesCubit>().toggleArchivedView(),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: state.showArchived
                          ? (state.visibleArchived.isEmpty
                              ? Center(child: Text(l10n.outsourcedCompaniesArchivedEmpty))
                              : ListView.separated(
                                  itemCount: state.visibleArchived.length,
                                  separatorBuilder: (_, __) => const Divider(height: 1),
                                  itemBuilder: (_, i) => _ArchivedOutsourcedCompanyTile(
                                    company: state.visibleArchived[i],
                                    onRestore: () => _confirmRestore(ctx, state.visibleArchived[i]),
                                  ),
                                ))
                          : (state.visible.isEmpty
                              ? Center(child: Text(l10n.outsourcedCompaniesEmpty))
                              : ListView.separated(
                                  itemCount: state.visible.length,
                                  separatorBuilder: (_, __) => const Divider(height: 1),
                                  itemBuilder: (_, i) => _OutsourcedCompanyTile(
                                    company: state.visible[i],
                                    onEdit: () => _openForm(ctx, company: state.visible[i]),
                                    onPromote: () => _confirmPromote(ctx, state.visible[i]),
                                    onArchive: () => _confirmArchive(ctx, state.visible[i]),
                                  ),
                                )),
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
    required this.onArchive,
  });

  final OutsourcedCompany company;
  final VoidCallback onEdit;
  final VoidCallback onPromote;
  final VoidCallback onArchive;

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
          IconButton(
            tooltip: l10n.outsourcedCompanyArchive,
            icon: const Icon(Icons.archive_outlined),
            onPressed: onArchive,
          ),
        ],
      ),
    );
  }
}

class _ArchivedOutsourcedCompanyTile extends StatelessWidget {
  const _ArchivedOutsourcedCompanyTile({required this.company, required this.onRestore});

  final Map<String, dynamic> company;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final reason = '${company['archive_reason'] ?? ''}'.trim();
    return ListTile(
      title: Text('${company['legal_name'] ?? ''}'),
      subtitle: Text(
        [
          '${l10n.archivedAt}: ${company['archived_at'] ?? ''}',
          if (reason.isNotEmpty) reason,
        ].join(' · '),
      ),
      trailing: TextButton.icon(
        icon: const Icon(Icons.unarchive_outlined),
        label: Text(l10n.outsourcedCompanyRestore),
        onPressed: onRestore,
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
