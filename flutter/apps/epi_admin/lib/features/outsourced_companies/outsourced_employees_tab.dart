import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/outsourced_employees_cubit.dart';

/// Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — só
/// terceirizado/prestador, nunca CLT. Escreve na mesma tabela `employees`
/// do cadastro completo, através das rotas `.../outsourced-simplified`.
class OutsourcedEmployeesTab extends StatelessWidget {
  const OutsourcedEmployeesTab({super.key});

  Future<void> _openForm(BuildContext context, {Employee? employee}) async {
    final cubit = context.read<OutsourcedEmployeesCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: _OutsourcedEmployeeFormDialog(employeeId: employee?.id),
      ),
    );
    if (saved == true && context.mounted) cubit.load();
  }

  Future<void> _confirmArchive(BuildContext context, Employee employee) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedEmployeesCubit>();
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedEmployeeArchiveConfirmTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(employee.name),
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
            child: Text(l10n.archive),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.archiveEmployee(employee.id, reason: reasonController.text.trim());
    }
  }

  Future<void> _confirmRestore(BuildContext context, Map<String, dynamic> employee) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<OutsourcedEmployeesCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.outsourcedEmployeeRestoreConfirmTitle),
        content: Text('${employee['name'] ?? ''}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l10n.restore),
          ),
        ],
      ),
    );
    if (confirmed == true) await cubit.restoreEmployee((employee['id'] as num).toInt());
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<OutsourcedEmployeesCubit, OutsourcedEmployeesState>(
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
                  label: Text(l10n.outsourcedEmployeeNew),
                ),
          body: state.isLoading && state.employees.isEmpty && state.archivedEmployees.isEmpty
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
                                labelText: l10n.search,
                              ),
                              onChanged: ctx.read<OutsourcedEmployeesCubit>().search,
                            ),
                          ),
                          IconButton(
                            tooltip: state.showArchived
                                ? l10n.outsourcedShowActive
                                : l10n.outsourcedShowArchived,
                            icon: Icon(
                              state.showArchived
                                  ? Icons.people_outline
                                  : Icons.inventory_2_outlined,
                            ),
                            onPressed: () => ctx.read<OutsourcedEmployeesCubit>().toggleArchivedView(),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: state.showArchived
                          ? (state.filteredArchived.isEmpty
                              ? Center(child: Text(l10n.outsourcedEmployeesArchivedEmpty))
                              : ListView.separated(
                                  itemCount: state.filteredArchived.length,
                                  separatorBuilder: (_, __) => const Divider(height: 1),
                                  itemBuilder: (_, i) => _ArchivedEmployeeTile(
                                    employee: state.filteredArchived[i],
                                    onRestore: () => _confirmRestore(ctx, state.filteredArchived[i]),
                                  ),
                                ))
                          : (state.filtered.isEmpty
                              ? Center(child: Text(l10n.outsourcedEmployeesEmpty))
                              : ListView.separated(
                                  itemCount: state.filtered.length,
                                  separatorBuilder: (_, __) => const Divider(height: 1),
                                  itemBuilder: (_, i) => _EmployeeTile(
                                    employee: state.filtered[i],
                                    onEdit: () => _openForm(ctx, employee: state.filtered[i]),
                                    onArchive: () => _confirmArchive(ctx, state.filtered[i]),
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

class _EmployeeTile extends StatelessWidget {
  const _EmployeeTile({required this.employee, required this.onEdit, required this.onArchive});

  final Employee employee;
  final VoidCallback onEdit;
  final VoidCallback onArchive;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListTile(
      title: Text(employee.name),
      subtitle: Text(
        [
          if (employee.role != null && employee.role!.isNotEmpty) employee.role!,
          if (employee.employmentType != null) employee.employmentType!,
          if (employee.sourceCompany != null && employee.sourceCompany!.isNotEmpty) employee.sourceCompany!,
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
          IconButton(
            tooltip: l10n.archive,
            icon: const Icon(Icons.archive_outlined),
            onPressed: onArchive,
          ),
        ],
      ),
    );
  }
}

class _ArchivedEmployeeTile extends StatelessWidget {
  const _ArchivedEmployeeTile({required this.employee, required this.onRestore});

  final Map<String, dynamic> employee;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final reason = '${employee['archive_reason'] ?? ''}'.trim();
    return ListTile(
      title: Text('${employee['name'] ?? ''}'),
      subtitle: Text(
        [
          '${l10n.archivedAt}: ${employee['archived_at'] ?? ''}',
          if (reason.isNotEmpty) reason,
        ].join(' · '),
      ),
      trailing: TextButton.icon(
        icon: const Icon(Icons.unarchive_outlined),
        label: Text(l10n.restore),
        onPressed: onRestore,
      ),
    );
  }
}

/// Valores aceitos por `tipo_vinculo` no Cadastro de Colaboradores
/// simplificado.
///
/// É a mesma `kContractedVinculos` do `epi_api`, que por sua vez espelha
/// `CONTRACTED_VINCULOS` do backend — a lista não é redigitada aqui. A versão
/// local anterior tinha só dois valores e omitia `Temporário`, que o backend
/// sempre aceitou (`validate_employee_outsourced_simplified_payload`): o
/// resultado era um vínculo válido que o app simplesmente não deixava
/// cadastrar.
const _kOutsourcedEmploymentTypes = kContractedVinculos;

class _OutsourcedEmployeeFormDialog extends StatefulWidget {
  const _OutsourcedEmployeeFormDialog({this.employeeId});

  /// Quando informado, abre em modo edição.
  final int? employeeId;

  @override
  State<_OutsourcedEmployeeFormDialog> createState() => _OutsourcedEmployeeFormDialogState();
}

class _OutsourcedEmployeeFormDialogState extends State<_OutsourcedEmployeeFormDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _cpf = TextEditingController();
  final _role = TextEditingController();
  final _originCompanyRegistration = TextEditingController();
  final _badgeNumber = TextEditingController();
  final _notes = TextEditingController();

  String _tipoVinculo = _kOutsourcedEmploymentTypes.first;
  DateTime? _admission;
  List<Map<String, dynamic>> _units = const [];
  Map<String, dynamic>? _unit;
  List<OutsourcedCompany> _outsourcedCompanies = const [];
  OutsourcedCompany? _outsourcedCompany;

  bool _loading = true;
  bool _submitting = false;

  // Administrador Local/Gestor de EPI só podem operar dentro da própria
  // unidade operacional — o backend já força isso em
  // create/update_employee_outsourced_simplified
  // (ensure_actor_unit_scope_for_target), mas até esta correção o campo
  // aparecia como um seletor livre com todas as unidades do tenant,
  // deixando esses perfis escolherem outra unidade na UI e só descobrirem
  // o bloqueio depois de tentar salvar.
  bool _lockUnitToOwnScope = false;
  int? _ownUnitId;

  bool get _editing => widget.employeeId != null;

  @override
  void initState() {
    super.initState();
    final authState = context.read<AuthCubit>().state;
    if (authState is AuthAuthenticated) {
      final role = authState.sessionContext.role;
      _lockUnitToOwnScope = role == 'admin' || role == 'user';
      _ownUnitId = authState.sessionContext.unitId;
    }
    _load();
  }

  Future<void> _load() async {
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final companies = await ApiClient.outsourcedCompanies
          .getOutsourcedCompanies(actorUserId: ApiClient.actorUserId);
      var units = bootstrap.units;
      if (_lockUnitToOwnScope) {
        units = units.where((u) => (u['id'] as num?)?.toInt() == _ownUnitId).toList();
      }
      if (_editing) {
        final emp = await ApiClient.employees
            .getEmployee(widget.employeeId!, actorUserId: ApiClient.actorUserId);
        _prefill(emp, units, companies);
      } else if (_lockUnitToOwnScope && units.isNotEmpty) {
        _unit = units.first;
      }
      if (!mounted) return;
      setState(() {
        _units = units;
        _outsourcedCompanies = companies;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  void _prefill(
    Map<String, dynamic> emp,
    List<Map<String, dynamic>> units,
    List<OutsourcedCompany> companies,
  ) {
    _name.text = '${emp['name'] ?? ''}';
    _cpf.text = '${emp['cpf'] ?? ''}';
    _role.text = '${emp['role_name'] ?? ''}';
    _originCompanyRegistration.text = '${emp['origin_company_registration'] ?? ''}';
    _badgeNumber.text = '${emp['badge_number'] ?? ''}';
    _notes.text = '${emp['notes'] ?? ''}';
    final loadedType = '${emp['tipo_vinculo'] ?? ''}'.trim();
    _tipoVinculo = _kOutsourcedEmploymentTypes.contains(loadedType)
        ? loadedType
        : _kOutsourcedEmploymentTypes.first;
    final admission = '${emp['admission_date'] ?? ''}';
    _admission = admission.isEmpty ? null : DateTime.tryParse(admission);
    final unitId = emp['unit_id'];
    for (final u in units) {
      if (u['id'] == unitId) {
        _unit = u;
        break;
      }
    }
    final outsourcedCompanyId = emp['outsourced_company_id'];
    for (final c in companies) {
      if (c.id == outsourcedCompanyId) {
        _outsourcedCompany = c;
        break;
      }
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _cpf, _role, _originCompanyRegistration, _badgeNumber, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  String _employmentTypeLabel(AppLocalizations l10n, String value) => switch (value) {
        'Terceirizado' => l10n.employmentTypeOutsourced,
        'Prestador de Serviço' => l10n.employmentTypeServiceProvider,
        _ => value,
      };

  Future<void> _submit() async {
    if (_submitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_unit == null || _outsourcedCompany == null || _admission == null) return;
    setState(() => _submitting = true);
    final cubit = context.read<OutsourcedEmployeesCubit>();
    final navigator = Navigator.of(context);
    final body = <String, dynamic>{
      'company_id': _unit!['company_id'],
      'unit_id': _unit!['id'],
      'outsourced_company_id': _outsourcedCompany!.id,
      'name': _name.text.trim(),
      'cpf': _cpf.text.trim(),
      'role_name': _role.text.trim(),
      'tipo_vinculo': _tipoVinculo,
      'admission_date': _admission!.toIso8601String().split('T').first,
      if (_originCompanyRegistration.text.trim().isNotEmpty)
        'origin_company_registration': _originCompanyRegistration.text.trim(),
      if (_badgeNumber.text.trim().isNotEmpty) 'badge_number': _badgeNumber.text.trim(),
      if (_notes.text.trim().isNotEmpty) 'notes': _notes.text.trim(),
    };
    final ok = _editing
        ? await cubit.updateEmployee(widget.employeeId!, body)
        : await cubit.createEmployee(body);
    if (!mounted) return;
    setState(() => _submitting = false);
    if (ok) navigator.pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? l10n.required : null;

    return AlertDialog(
      title: Text(_editing ? l10n.edit : l10n.outsourcedEmployeeNew),
      content: SizedBox(
        width: 420,
        child: _loading
            ? const Center(
                heightFactor: 3,
                child: CircularProgressIndicator(),
              )
            : SingleChildScrollView(
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextFormField(
                        controller: _name,
                        validator: req,
                        decoration: InputDecoration(labelText: l10n.employeeNameLabel),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _cpf,
                        validator: req,
                        decoration: InputDecoration(labelText: l10n.employeeCpfLabel),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<OutsourcedCompany>(
                        value: _outsourcedCompany,
                        decoration: InputDecoration(labelText: l10n.outsourcedEmployeeCompanyLabel),
                        items: _outsourcedCompanies
                            .map((c) => DropdownMenuItem(value: c, child: Text(c.displayLabel)))
                            .toList(),
                        validator: (v) => v == null ? l10n.required : null,
                        onChanged: (v) => setState(() => _outsourcedCompany = v),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<Map<String, dynamic>>(
                        value: _unit,
                        decoration: InputDecoration(labelText: l10n.employeeUnitLabel),
                        items: _units
                            .map((u) => DropdownMenuItem<Map<String, dynamic>>(
                                  value: u,
                                  child: Text('${u['name'] ?? ''}'),
                                ))
                            .toList(),
                        validator: (v) => v == null ? l10n.required : null,
                        onChanged: _lockUnitToOwnScope ? null : (v) => setState(() => _unit = v),
                      ),
                      if (_lockUnitToOwnScope) ...[
                        const SizedBox(height: EpiSpacing.xs),
                        Text(
                          l10n.employeeUnitLockedHint,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
                        ),
                      ],
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _role,
                        validator: req,
                        decoration: InputDecoration(labelText: l10n.employeeRoleLabel),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<String>(
                        value: _tipoVinculo,
                        decoration: InputDecoration(labelText: l10n.employeeEmploymentTypeLabel),
                        items: _kOutsourcedEmploymentTypes
                            .map((v) => DropdownMenuItem<String>(
                                  value: v,
                                  child: Text(_employmentTypeLabel(l10n, v)),
                                ))
                            .toList(),
                        onChanged: (v) =>
                            setState(() => _tipoVinculo = v ?? _kOutsourcedEmploymentTypes.first),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      InkWell(
                        onTap: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _admission ?? DateTime.now(),
                            firstDate: DateTime(2000),
                            lastDate: DateTime(2100),
                          );
                          if (picked != null) setState(() => _admission = picked);
                        },
                        child: InputDecorator(
                          decoration: InputDecoration(labelText: l10n.employeeAdmissionLabel),
                          child: Text(
                            _admission == null
                                ? '—'
                                : _admission!.toIso8601String().split('T').first,
                          ),
                        ),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _originCompanyRegistration,
                        decoration:
                            InputDecoration(labelText: l10n.outsourcedEmployeeOriginRegistrationLabel),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _badgeNumber,
                        decoration: InputDecoration(labelText: l10n.outsourcedEmployeeBadgeLabel),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _notes,
                        maxLines: 3,
                        decoration: InputDecoration(labelText: l10n.outsourcedEmployeeNotesLabel),
                      ),
                    ],
                  ),
                ),
              ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _submitting || _loading ? null : _submit,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
