import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';

/// Processo administrativo de mudança do CNPJ do colaborador.
///
/// O CNPJ é o vínculo jurídico do contrato de trabalho: **imutável na edição
/// comum do cadastro**. Esta é a única via de alteração e exige justificativa,
/// gerando histórico (`employee_legal_entity_movements`) e auditoria no backend.
///
/// A unidade — lotação operacional — segue seus próprios fluxos de
/// transferência e nunca altera este vínculo.
class LegalEntityTransferDialog extends StatefulWidget {
  const LegalEntityTransferDialog({
    super.key,
    required this.employeeId,
    required this.currentLegalEntityId,
  });

  final int employeeId;
  final int? currentLegalEntityId;

  @override
  State<LegalEntityTransferDialog> createState() =>
      _LegalEntityTransferDialogState();
}

class _LegalEntityTransferDialogState extends State<LegalEntityTransferDialog> {
  final _formKey = GlobalKey<FormState>();
  final _reason = TextEditingController();

  List<LegalEntity> _entities = const [];
  LegalEntity? _target;
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
      final all = await ApiClient.legalEntities
          .getLegalEntities(actorUserId: ApiClient.actorUserId);
      if (!mounted) return;
      setState(() {
        // Só CNPJs ativos e diferentes do atual são destinos válidos — o
        // backend recusa ambos os casos, então nem oferecemos.
        _entities = all
            .where((e) => e.active && e.id != widget.currentLegalEntityId)
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
    _reason.dispose();
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

  Future<void> _submit() async {
    if (_submitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_target == null) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    final navigator = Navigator.of(context);
    try {
      await ApiClient.legalEntities.transferEmployeeLegalEntity(
        widget.employeeId,
        actorUserId: ApiClient.actorUserId,
        legalEntityId: _target!.id,
        reason: _reason.text.trim(),
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
      title: Text(l10n.legalEntityTransferTitle),
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
                        l10n.legalEntityTransferHint,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      DropdownButtonFormField<LegalEntity>(
                        initialValue: _target,
                        isExpanded: true,
                        decoration: InputDecoration(
                          labelText: l10n.legalEntityTransferTarget,
                        ),
                        items: _entities
                            .map((e) => DropdownMenuItem(
                                  value: e,
                                  child: Text(e.displayLabel,
                                      overflow: TextOverflow.ellipsis),
                                ))
                            .toList(),
                        validator: (v) => v == null ? l10n.required : null,
                        onChanged: (v) => setState(() => _target = v),
                      ),
                      const SizedBox(height: EpiSpacing.md),
                      TextFormField(
                        controller: _reason,
                        minLines: 2,
                        maxLines: 4,
                        decoration: InputDecoration(
                          labelText: l10n.legalEntityTransferReason,
                          border: const OutlineInputBorder(),
                        ),
                        validator: (v) =>
                            (v == null || v.trim().isEmpty) ? l10n.required : null,
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
          child: Text(l10n.legalEntityTransferAction),
        ),
      ],
    );
  }
}
