import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/employees_cubit.dart';

/// Form de criação de colaborador. Os campos usam chaves i18n existentes
/// (+ employeeCpfLabel). A empresa é derivada da unidade selecionada
/// (cada unidade do bootstrap carrega `company_id`).
class EmployeeFormScreen extends StatefulWidget {
  const EmployeeFormScreen({super.key, required this.cubit, this.employeeId});
  final EmployeesCubit cubit;

  /// Quando informado, o form abre em modo edição (carrega e atualiza).
  final int? employeeId;

  @override
  State<EmployeeFormScreen> createState() => _EmployeeFormScreenState();
}

/// Valores enviados como `tipo_vinculo` — os mesmos que o web legado grava,
/// para que o mesmo colaborador leia igual nas duas superfícies.
const _kClt = 'CLT';
const _kEmploymentTypes = [
  _kClt,
  'Terceirizado',
  'Temporário',
  'Prestador de Serviço',
  'Menor Aprendiz',
  'Praticante',
  'Estagiário',
];

class _EmployeeFormScreenState extends State<EmployeeFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _code = TextEditingController();
  final _cpf = TextEditingController();
  final _sector = TextEditingController();
  final _role = TextEditingController();
  final _schedule = TextEditingController();
  final _email = TextEditingController();
  final _whatsapp = TextEditingController();
  final _sourceCompany = TextEditingController();

  DateTime? _admission;

  /// Valor enviado como `tipo_vinculo` — texto livre no backend, sem lista
  /// fechada validada no servidor. As opções aqui espelham o web legado.
  String _employmentType = _kClt;
  List<Map<String, dynamic>> _units = const [];
  Map<String, dynamic>? _unit;

  /// CNPJs (LegalEntity) da empresa, vindos do bootstrap já escopados por papel.
  List<Map<String, dynamic>> _legalEntities = const [];
  Map<String, dynamic>? _legalEntity;

  bool _loading = true;
  bool _submitting = false;

  /// O CNPJ é o vínculo jurídico do contrato de trabalho: **imutável após a
  /// admissão**. Na edição o campo aparece somente leitura; a alteração exige o
  /// processo administrativo auditado (transferência de vínculo jurídico).
  bool get _legalEntityLocked => _editing;

  /// O backend só exige o CNPJ quando a empresa tem mais de um CNPJ ativo —
  /// empresa de CNPJ único continua caindo na matriz automaticamente.
  bool get _legalEntityRequired => _legalEntities.length > 1;

  bool get _editing => widget.employeeId != null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final units = bootstrap.units;
      final legalEntities = bootstrap.legalEntities
          .where((e) => (e['active'] ?? 1) != 0)
          .toList(growable: false);
      if (_editing) {
        final emp = await ApiClient.employees
            .getEmployee(widget.employeeId!, actorUserId: ApiClient.actorUserId);
        _prefill(emp, units, legalEntities);
      }
      if (!mounted) return;
      setState(() {
        _units = units;
        _legalEntities = legalEntities;
        // Empresa com um único CNPJ: pré-seleciona, já que o backend cairia
        // nele de qualquer forma — evita um campo com escolha única.
        _legalEntity ??= legalEntities.length == 1 ? legalEntities.first : null;
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
    List<Map<String, dynamic>> legalEntities,
  ) {
    _name.text = '${emp['name'] ?? ''}';
    _code.text = '${emp['employee_id_code'] ?? ''}';
    _cpf.text = '${emp['cpf'] ?? ''}';
    _sector.text = '${emp['sector'] ?? ''}';
    _role.text = '${emp['role_name'] ?? ''}';
    _schedule.text = '${emp['schedule_type'] ?? ''}';
    _email.text = '${emp['email'] ?? ''}';
    _whatsapp.text = '${emp['whatsapp'] ?? ''}';
    final loadedType = '${emp['tipo_vinculo'] ?? ''}'.trim();
    _employmentType = _kEmploymentTypes.contains(loadedType) ? loadedType : _kClt;
    _sourceCompany.text = '${emp['empresa_origem'] ?? ''}';
    final admission = '${emp['admission_date'] ?? ''}';
    _admission = admission.isEmpty ? null : DateTime.tryParse(admission);
    final unitId = emp['unit_id'];
    for (final u in units) {
      if (u['id'] == unitId) {
        _unit = u;
        break;
      }
    }
    final legalEntityId = emp['legal_entity_id'];
    for (final e in legalEntities) {
      if (e['id'] == legalEntityId) {
        _legalEntity = e;
        break;
      }
    }
  }

  /// Rótulo exibido para cada valor de `tipo_vinculo`.
  String _employmentTypeLabel(AppLocalizations l10n, String value) => switch (value) {
        _kClt => l10n.employmentTypeClt,
        'Terceirizado' => l10n.employmentTypeOutsourced,
        'Temporário' => l10n.employmentTypeTemporary,
        'Prestador de Serviço' => l10n.employmentTypeServiceProvider,
        'Menor Aprendiz' => l10n.employmentTypeApprentice,
        'Praticante' => l10n.employmentTypeTrainee,
        'Estagiário' => l10n.employmentTypeIntern,
        _ => value,
      };

  /// Espelha exatamente a regra do web legado
  /// (`syncEmpresaOrigemVisibility`): o campo só aparece quando o vínculo não
  /// é CLT — uma única comparação, sem lista de casos, para que uma opção
  /// nova (como as três que acabaram de entrar) não precise de outra edição
  /// aqui.
  bool get _showSourceCompany => _employmentType != _kClt;

  /// Rótulo do CNPJ no seletor: nome fantasia (ou razão social) + número.
  String _legalEntityLabel(Map<String, dynamic>? entity) {
    if (entity == null) return '';
    final trade = '${entity['trade_name'] ?? ''}'.trim();
    final legal = '${entity['legal_name'] ?? ''}'.trim();
    final cnpj = '${entity['cnpj'] ?? ''}'.trim();
    final name = trade.isNotEmpty ? trade : legal;
    if (name.isEmpty) return cnpj;
    return cnpj.isEmpty ? name : '$name — $cnpj';
  }

  @override
  void dispose() {
    for (final c in [
      _name,
      _code,
      _cpf,
      _sector,
      _role,
      _schedule,
      _email,
      _whatsapp,
      _sourceCompany,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_unit == null || _admission == null) return;
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'company_id': _unit!['company_id'],
      'unit_id': _unit!['id'],
      'name': _name.text.trim(),
      'employee_id_code': _code.text.trim(),
      'cpf': _cpf.text.trim(),
      'sector': _sector.text.trim(),
      'role_name': _role.text.trim(),
      'schedule_type': _schedule.text.trim(),
      'admission_date': _admission!.toIso8601String().split('T').first,
      if (_email.text.trim().isNotEmpty) 'email': _email.text.trim(),
      if (_whatsapp.text.trim().isNotEmpty) 'whatsapp': _whatsapp.text.trim(),
      'tipo_vinculo': _employmentType,
      if (_showSourceCompany) 'empresa_origem': _sourceCompany.text.trim(),
      // Só enviado na criação: na edição o backend ignora legal_entity_id e
      // preserva o vínculo da admissão. Não enviar deixa a intenção explícita.
      if (!_editing && _legalEntity != null) 'legal_entity_id': _legalEntity!['id'],
    };
    if (_editing) {
      await widget.cubit.updateEmployee(widget.employeeId!, body);
    } else {
      await widget.cubit.createEmployee(body);
    }
    if (!mounted) return;
    setState(() => _submitting = false);
    final error = widget.cubit.state.error;
    if (error == null) {
      navigator.pop();
    } else {
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? l10n.required : null;

    return Scaffold(
      appBar: AppBar(title: Text(_editing ? l10n.edit : l10n.employeesNew)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(EpiSpacing.lg),
                children: [
                  TextFormField(
                    controller: _name,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeNameLabel),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _code,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeCodeLabel),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _cpf,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeCpfLabel),
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
                    onChanged: (v) => setState(() => _unit = v),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  // CNPJ ao qual o colaborador pertence juridicamente.
                  // Na edição fica somente leitura: o vínculo do contrato de
                  // trabalho é imutável após a admissão e só muda pelo processo
                  // administrativo auditado.
                  if (_legalEntities.isNotEmpty) ...[
                    if (_legalEntityLocked)
                      TextFormField(
                        readOnly: true,
                        enabled: false,
                        initialValue: _legalEntityLabel(_legalEntity),
                        decoration: InputDecoration(
                          labelText: l10n.employeeLegalEntityLabel,
                        ),
                      )
                    else
                      DropdownButtonFormField<Map<String, dynamic>>(
                        value: _legalEntity,
                        decoration: InputDecoration(
                          labelText: l10n.employeeLegalEntityLabel,
                        ),
                        items: _legalEntities
                            .map((e) => DropdownMenuItem<Map<String, dynamic>>(
                                  value: e,
                                  child: Text(_legalEntityLabel(e)),
                                ))
                            .toList(),
                        validator: (v) =>
                            (_legalEntityRequired && v == null) ? l10n.required : null,
                        onChanged: (v) => setState(() => _legalEntity = v),
                      ),
                    const SizedBox(height: EpiSpacing.md),
                  ],
                  TextFormField(
                    controller: _sector,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeSectorLabel),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _role,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeRoleLabel),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _schedule,
                    validator: req,
                    decoration: InputDecoration(labelText: l10n.employeeScheduleLabel),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  DropdownButtonFormField<String>(
                    value: _employmentType,
                    decoration: InputDecoration(
                      labelText: l10n.employeeEmploymentTypeLabel,
                    ),
                    items: _kEmploymentTypes
                        .map((v) => DropdownMenuItem<String>(
                              value: v,
                              child: Text(_employmentTypeLabel(l10n, v)),
                            ))
                        .toList(),
                    onChanged: (v) => setState(() => _employmentType = v ?? _kClt),
                  ),
                  if (_showSourceCompany) ...[
                    const SizedBox(height: EpiSpacing.md),
                    TextFormField(
                      controller: _sourceCompany,
                      decoration: InputDecoration(
                        labelText: l10n.employeeSourceCompanyLabel,
                        helperText: l10n.employeeSourceCompanyHint,
                      ),
                    ),
                  ],
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
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: InputDecoration(labelText: l10n.employeeContactEmail),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _whatsapp,
                    keyboardType: TextInputType.phone,
                    decoration: InputDecoration(labelText: l10n.employeeContactWhatsapp),
                  ),
                  const SizedBox(height: EpiSpacing.xl),
                  EpiButton(
                    label: l10n.save,
                    onPressed: _submitting ? null : _submit,
                  ),
                ],
              ),
            ),
    );
  }
}
