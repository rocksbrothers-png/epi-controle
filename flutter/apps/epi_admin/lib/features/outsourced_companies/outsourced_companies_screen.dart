import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
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
/// oculto por padrão em todo tenant até o Administrador Geral ligar, agora
/// também configurável por Unidade (bucket por unit_id dentro do próprio
/// module_visibility — Configuração → Regras → Visualização). O backend é a
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
      _canCompanies = (authState.permissions.contains('employees:create') ||
              authState.permissions.contains('employees:create_simplified')) &&
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

  /// "Vincular empresa a esta Unidade" (ADR-0002 §12, F6B da #226).
  ///
  /// Abre a busca no tenant. É o caminho que faltava no app: a listagem comum
  /// mostra só o que ESTA Unidade já vinculou, então uma Unidade que ainda não
  /// trabalha com a empresa não a enxerga — justamente por não ter vínculo. Sem
  /// esta porta, a saída do operador seria cadastrar a empresa de novo, e o
  /// desenho existe para que o cadastro corporativo seja único no tenant.
  Future<void> _openLinkFlow(BuildContext context) async {
    final cubit = context.read<OutsourcedCompaniesCubit>();
    await showDialog<void>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: const _LinkCompanyToUnitDialog(),
      ),
    );
    cubit.clearTenantSearch();
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
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    // Vincular vem ANTES de criar, e é o botão discreto: a
                    // ordem sugere a decisão certa — procurar o cadastro que
                    // já existe no tenant antes de criar mais um.
                    FloatingActionButton.small(
                      heroTag: 'link-company-to-unit',
                      tooltip: l10n.outsourcedCompanyLinkTitle,
                      onPressed: () => _openLinkFlow(ctx),
                      child: const Icon(Icons.add_link),
                    ),
                    const SizedBox(height: EpiSpacing.sm),
                    FloatingActionButton.extended(
                      heroTag: 'new-company',
                      onPressed: () => _openForm(ctx),
                      icon: const Icon(Icons.add),
                      label: Text(l10n.outsourcedCompanyNew),
                    ),
                  ],
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

/// Busca no tenant + vínculo local com esta Unidade (F6B da #226).
///
/// A empresa terceirizada é ÚNICA no tenant e pode ter vínculo com várias
/// Unidades, cada um com estado próprio. Este diálogo é o que permite a uma
/// Unidade localizar o cadastro existente e criar **apenas o seu** vínculo —
/// sem duplicar a empresa e sem herdar contratos, colaboradores ou notas de
/// nenhuma outra Unidade.
class _LinkCompanyToUnitDialog extends StatefulWidget {
  const _LinkCompanyToUnitDialog();

  @override
  State<_LinkCompanyToUnitDialog> createState() => _LinkCompanyToUnitDialogState();
}

class _LinkCompanyToUnitDialogState extends State<_LinkCompanyToUnitDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _confirmDeactivate(BuildContext context, OutsourcedCompany company) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedCompaniesCubit>();
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedCompanyLinkDeactivate),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(company.displayLabel),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: reasonController,
              decoration: InputDecoration(
                labelText: l10n.outsourcedCompanyLinkDeactivateReason,
              ),
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
            child: Text(l10n.outsourcedCompanyLinkDeactivate),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.deactivateCompanyUnitLink(
        company.id,
        reason: reasonController.text.trim(),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.outsourcedCompanyLinkTitle),
      content: SizedBox(
        width: 520,
        child: BlocBuilder<OutsourcedCompaniesCubit, OutsourcedCompaniesState>(
          builder: (ctx, state) {
            final cubit = ctx.read<OutsourcedCompaniesCubit>();
            return Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _controller,
                  autofocus: true,
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.search),
                    labelText: l10n.outsourcedCompanyLinkHint,
                  ),
                  onSubmitted: cubit.searchInTenant,
                  onChanged: cubit.searchInTenant,
                ),
                const SizedBox(height: EpiSpacing.md),
                if (state.isSearching)
                  const Padding(
                    padding: EdgeInsets.all(EpiSpacing.md),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (state.searchQuery.isEmpty)
                  const SizedBox.shrink()
                else if (state.searchResults.isEmpty)
                  Text(l10n.outsourcedCompanyLinkEmpty)
                else
                  Flexible(
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Dois blocos, e a separação não é estética: os itens
                          // "disponíveis" vêm MASCARADOS do backend — sem
                          // contratos, colaboradores ou notas de outra Unidade.
                          // Misturá-los com as vinculadas faria a tela mostrar
                          // registros incompletos como se fossem gerenciáveis.
                          if (state.searchLinked.isNotEmpty) ...[
                            _SectionLabel(l10n.outsourcedCompanyLinkSectionLinked),
                            ...state.searchLinked.map(
                              (c) => _LinkableCompanyTile(
                                company: c,
                                onLink: () => cubit.linkCompanyToUnit(c.id),
                                onActivate: () => cubit.activateCompanyUnitLink(c.id),
                                onDeactivate: () => _confirmDeactivate(ctx, c),
                              ),
                            ),
                          ],
                          if (state.searchAvailable.isNotEmpty) ...[
                            _SectionLabel(l10n.outsourcedCompanyLinkSectionAvailable),
                            ...state.searchAvailable.map(
                              (c) => _LinkableCompanyTile(
                                company: c,
                                onLink: () => cubit.linkCompanyToUnit(c.id),
                                onActivate: () => cubit.activateCompanyUnitLink(c.id),
                                onDeactivate: () => _confirmDeactivate(ctx, c),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.close),
        ),
      ],
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: EpiSpacing.md, bottom: EpiSpacing.xs),
        child: Text(
          text,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        ),
      );
}

/// Linha do fluxo de vinculação: identificação + estado + UMA ação.
class _LinkableCompanyTile extends StatelessWidget {
  const _LinkableCompanyTile({
    required this.company,
    required this.onLink,
    required this.onActivate,
    required this.onDeactivate,
  });

  final OutsourcedCompany company;
  final VoidCallback onLink;
  final VoidCallback onActivate;
  final VoidCallback onDeactivate;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      title: Text(company.displayLabel),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(company.cnpj, style: const TextStyle(fontSize: 12)),
          // Só os itens disponíveis trazem estes dois. O backend os expõe de
          // propósito: quem decide se reaproveita o cadastro precisa saber de
          // onde ele veio e quantas Unidades já o usam.
          if (company.isMaskedForLinking) ...[
            if (company.originUnitName.isNotEmpty)
              Text(
                '${l10n.outsourcedCompanyLinkOriginUnit}: ${company.originUnitName}',
                style: const TextStyle(fontSize: 12),
              ),
            if (company.linkedUnitsCount != null)
              Text(
                l10n.outsourcedCompanyLinkUsedByUnits(company.linkedUnitsCount!),
                style: const TextStyle(fontSize: 12, color: EpiColors.textMuted),
              ),
          ],
        ],
      ),
      isThreeLine: company.isMaskedForLinking,
      trailing: _action(l10n),
    );
  }

  /// Uma ação por estado. `null` é o caso que mais engana e por isso vem
  /// primeiro: para Administrador Geral, de Registro e Master a busca **não
  /// anota** o vínculo, e ausência ali significa "não informado", não "sem
  /// vínculo". Oferecer "Vincular" nesse caso agiria sobre uma empresa que
  /// pode já estar vinculada.
  Widget _action(AppLocalizations l10n) {
    if (!company.isMaskedForLinking && company.localUnitLinkStatus == null) {
      return Text(
        l10n.outsourcedCompanyLinkNotInformed,
        style: const TextStyle(fontSize: 11, color: EpiColors.textMuted),
      );
    }
    return switch (company.localUnitLinkStatus) {
      kUnitLinkStatusActive => TextButton(
          onPressed: onDeactivate,
          child: Text(l10n.outsourcedCompanyLinkDeactivate),
        ),
      kUnitLinkStatusInactive => TextButton(
          onPressed: onActivate,
          child: Text(l10n.outsourcedCompanyLinkActivate),
        ),
      // Mascarada: disponível para vincular.
      _ => FilledButton(
          onPressed: onLink,
          child: Text(l10n.outsourcedCompanyLinkLink),
        ),
    };
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
  List<Map<String, dynamic>> _units = const [];
  Map<String, dynamic>? _unit;
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
    _loadUnits();
  }

  Future<void> _loadUnits() async {
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      if (!mounted) return;
      final unitId = widget.company?.unitId;
      setState(() {
        _units = bootstrap.units;
        _unit = unitId == null
            ? null
            : _units.cast<Map<String, dynamic>?>().firstWhere(
                (u) => u?['id'] == unitId,
                orElse: () => null,
              );
      });
    } on Exception {
      // Sem unidades disponíveis (ou falha ao carregar): o campo fica
      // vazio/desabilitado e o formulário segue com unit_id nulo — o
      // backend (resolve_outsourced_company_unit_id) é a autoridade final.
    }
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
      'unit_id': _unit?['id'],
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
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<Map<String, dynamic>?>(
                value: _unit,
                decoration: InputDecoration(labelText: l10n.outsourcedCompanyUnitLabel),
                items: [
                  DropdownMenuItem(value: null, child: Text(l10n.outsourcedCompanyUnitAll)),
                  ..._units.map(
                    (u) => DropdownMenuItem(value: u, child: Text('${u['name'] ?? ''}')),
                  ),
                ],
                onChanged: (v) => setState(() => _unit = v),
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
