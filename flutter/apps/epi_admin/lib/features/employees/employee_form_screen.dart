import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/employees_cubit.dart';

/// Form de criação de colaborador. Os campos usam chaves i18n existentes
/// (+ employeeCpfLabel). A empresa é derivada da unidade selecionada
/// (cada unidade do bootstrap carrega `company_id`).
class EmployeeFormScreen extends StatefulWidget {
  const EmployeeFormScreen({super.key, required this.cubit});
  final EmployeesCubit cubit;

  @override
  State<EmployeeFormScreen> createState() => _EmployeeFormScreenState();
}

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

  DateTime? _admission;
  List<Map<String, dynamic>> _units = const [];
  Map<String, dynamic>? _unit;
  bool _loading = true;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _loadUnits();
  }

  Future<void> _loadUnits() async {
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      if (!mounted) return;
      setState(() {
        _units = bootstrap.units;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _code, _cpf, _sector, _role, _schedule, _email, _whatsapp]) {
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
    };
    await widget.cubit.createEmployee(body);
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
      appBar: AppBar(title: Text(l10n.employeesNew)),
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
