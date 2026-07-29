import 'package:dio/dio.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';

/// Movimentação de unidade operacional (transferência), temporária ou
/// definitiva — paridade com a tela "Gestão de Colaborador" do web legado.
///
/// Só o Administrador Local (`employees:transfer`) executa. Diferente da
/// transferência de CNPJ ([LegalEntityTransferDialog]): a unidade é a
/// lotação operacional e não altera o vínculo jurídico do contrato.
class UnitTransferDialog extends StatefulWidget {
  const UnitTransferDialog({
    super.key,
    required this.employeeId,
    required this.currentUnitId,
  });

  final int employeeId;
  final int? currentUnitId;

  @override
  State<UnitTransferDialog> createState() => _UnitTransferDialogState();
}

class _UnitTransferDialogState extends State<UnitTransferDialog> {
  final _formKey = GlobalKey<FormState>();
  final _notes = TextEditingController();

  List<Map<String, dynamic>> _units = const [];
  Map<String, dynamic>? _target;
  String _movementType = 'temporary';
  DateTime? _startDate;
  DateTime? _endDate;
  bool _startDateTouched = false;

  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      if (!mounted) return;
      setState(() {
        // Só unidades diferentes da atual são destinos válidos — o backend
        // recusa a mesma unidade, então nem oferecemos.
        _units = bootstrap.units
            .where((u) => u['id'] != widget.currentUnitId)
            .toList(growable: false);
        _loading = false;
      });
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _message(e);
      });
    }
  }

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  static String _message(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map) {
        final message = data['error'] ?? data['detail'];
        if (message != null) return message.toString();
      }
    }
    return e.toString();
  }

  static String _isoDate(DateTime date) =>
      date.toIso8601String().split('T').first;

  Future<void> _pickDate({required bool isStart}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: (isStart ? _startDate : _endDate) ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _startDate = picked;
      } else {
        _endDate = picked;
      }
    });
  }

  Future<void> _submit() async {
    if (_submitting) return;
    setState(() => _startDateTouched = true);
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_target == null || _startDate == null) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    final navigator = Navigator.of(context);
    try {
      await ApiClient.employees.createUnitMovement(
        actorUserId: ApiClient.actorUserId,
        employeeId: widget.employeeId,
        targetUnitId: (_target!['id'] as num).toInt(),
        movementType: _movementType,
        startDate: _isoDate(_startDate!),
        endDate: _endDate == null ? '' : _isoDate(_endDate!),
        notes: _notes.text.trim(),
      );
      navigator.pop(true);
    } on Exception catch (e) {
      if (!mounted) return;
      // Mantém o diálogo aberto para o operador corrigir sem perder o texto.
      setState(() {
        _submitting = false;
        _error = _message(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.unitTransferTitle),
      content: _loading
          ? const SizedBox(
              height: 80, child: Center(child: CircularProgressIndicator()))
          : SizedBox(
              width: 460,
              child: SingleChildScrollView(
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        l10n.unitTransferHint,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<Map<String, dynamic>>(
                        initialValue: _target,
                        isExpanded: true,
                        decoration: InputDecoration(
                          labelText: l10n.unitTransferTarget,
                        ),
                        items: _units
                            .map((u) => DropdownMenuItem(
                                  value: u,
                                  child: Text(
                                    '${u['name'] ?? ''}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ))
                            .toList(),
                        validator: (v) => v == null ? l10n.required : null,
                        onChanged: (v) => setState(() => _target = v),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<String>(
                        initialValue: _movementType,
                        decoration: InputDecoration(
                          labelText: l10n.unitTransferType,
                        ),
                        items: [
                          DropdownMenuItem(
                            value: 'temporary',
                            child: Text(l10n.unitTransferTypeTemporary),
                          ),
                          DropdownMenuItem(
                            value: 'definitive',
                            child: Text(l10n.unitTransferTypeDefinitive),
                          ),
                        ],
                        onChanged: (v) => setState(
                          () => _movementType = v ?? 'temporary',
                        ),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      InkWell(
                        onTap: () => _pickDate(isStart: true),
                        child: InputDecorator(
                          decoration: InputDecoration(
                            labelText: l10n.unitTransferStartDate,
                            errorText: _startDateTouched && _startDate == null
                                ? l10n.required
                                : null,
                          ),
                          child: Text(
                            _startDate == null ? '—' : _isoDate(_startDate!),
                          ),
                        ),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      InkWell(
                        onTap: () => _pickDate(isStart: false),
                        child: InputDecorator(
                          decoration: InputDecoration(
                            labelText: l10n.unitTransferEndDate,
                          ),
                          child: Text(
                            _endDate == null ? '—' : _isoDate(_endDate!),
                          ),
                        ),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _notes,
                        minLines: 2,
                        maxLines: 4,
                        decoration: InputDecoration(
                          labelText: l10n.unitTransferNotes,
                          border: const OutlineInputBorder(),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: EpiSpacing.md),
                        Text(
                          _error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
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
          onPressed: (_submitting || _loading) ? null : _submit,
          child: Text(l10n.unitTransferAction),
        ),
      ],
    );
  }
}
