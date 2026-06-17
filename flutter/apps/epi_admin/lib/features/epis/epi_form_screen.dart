import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/epis_cubit.dart';

/// Form de criação de EPI (escopo global por padrão — sem unidade).
/// A empresa é escolhida num dropdown; os campos cobrem o contrato do
/// POST /api/epis. Labels via chaves i18n existentes (+ chaves epi*Label novas).
class EpiFormScreen extends StatefulWidget {
  const EpiFormScreen({super.key, required this.cubit});
  final EpisCubit cubit;

  @override
  State<EpiFormScreen> createState() => _EpiFormScreenState();
}

class _EpiFormScreenState extends State<EpiFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _code = TextEditingController();
  final _ca = TextEditingController();
  final _sector = TextEditingController();
  final _section = TextEditingController();
  final _model = TextEditingController();
  final _manufacturer = TextEditingController();
  final _supplier = TextEditingController();
  final _unitMeasure = TextEditingController();
  final _manufacturerValidity = TextEditingController();

  DateTime? _caExpiry;
  DateTime? _validityDate;
  List<Company> _companies = const [];
  Company? _company;
  bool _loading = true;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _loadCompanies();
  }

  Future<void> _loadCompanies() async {
    try {
      final companies = await ApiClient.companies.getCompanies();
      if (!mounted) return;
      setState(() {
        _companies = companies;
        _company = companies.length == 1 ? companies.first : null;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    for (final c in [
      _name, _code, _ca, _sector, _section, _model,
      _manufacturer, _supplier, _unitMeasure, _manufacturerValidity,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  String _iso(DateTime d) => d.toIso8601String().split('T').first;

  Future<void> _submit() async {
    if (_submitting) return;
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_company == null || _caExpiry == null || _validityDate == null) return;
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'company_id': _company!.id,
      'name': _name.text.trim(),
      'purchase_code': _code.text.trim(),
      'ca': _ca.text.trim(),
      'sector': _sector.text.trim(),
      'epi_section': _section.text.trim(),
      'model_reference': _model.text.trim(),
      'manufacturer': _manufacturer.text.trim(),
      'supplier_company': _supplier.text.trim(),
      'unit_measure': _unitMeasure.text.trim(),
      'ca_expiry': _iso(_caExpiry!),
      'epi_validity_date': _iso(_validityDate!),
      'manufacturer_validity_months': _manufacturerValidity.text.trim(),
    };
    await widget.cubit.createEpi(body);
    if (!mounted) return;
    setState(() => _submitting = false);
    final error = widget.cubit.state.error;
    if (error == null) {
      navigator.pop();
    } else {
      messenger.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime> onPicked) {
    return InkWell(
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: value ?? DateTime.now(),
          firstDate: DateTime(2000),
          lastDate: DateTime(2100),
        );
        if (picked != null) onPicked(picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(labelText: label),
        child: Text(value == null ? '—' : _iso(value)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? l10n.required : null;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.episNew)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(EpiSpacing.lg),
                children: [
                  DropdownButtonFormField<Company>(
                    value: _company,
                    decoration: InputDecoration(labelText: l10n.companiesTitle),
                    items: _companies
                        .map((c) => DropdownMenuItem<Company>(
                              value: c,
                              child: Text(c.name),
                            ))
                        .toList(),
                    validator: (v) => v == null ? l10n.required : null,
                    onChanged: (v) => setState(() => _company = v),
                  ),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _name, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiNameLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _code, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiCodeLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _ca, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiCaLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _sector, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiSectorLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _section, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiSectionLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _model, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiModelLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _manufacturer, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiManufacturerLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _supplier, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiSupplierLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(controller: _unitMeasure, validator: req,
                      decoration: InputDecoration(labelText: l10n.epiUnitMeasureLabel)),
                  const SizedBox(height: EpiSpacing.md),
                  _dateField(l10n.epiCaExpiryLabel, _caExpiry,
                      (d) => setState(() => _caExpiry = d)),
                  const SizedBox(height: EpiSpacing.md),
                  _dateField(l10n.epiValidityDateLabel, _validityDate,
                      (d) => setState(() => _validityDate = d)),
                  const SizedBox(height: EpiSpacing.md),
                  TextFormField(
                    controller: _manufacturerValidity,
                    validator: req,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(labelText: l10n.epiManufacturerValidityLabel),
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
