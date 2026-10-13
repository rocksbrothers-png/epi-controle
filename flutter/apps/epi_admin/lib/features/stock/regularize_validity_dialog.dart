import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

import '../../core/bloc/stock_cubit.dart';

/// EST-V3.5-R2 (F4): ação "Regularizar validade física" da Gestão de Validade.
///
/// Fluxo guiado pela PEÇA física: o operador a identifica pelo QR/código,
/// informa a validade comprovada, a evidência e a justificativa. A
/// CLASSIFICAÇÃO é do backend — esta folha só coleta, envia e EXIBE o resultado
/// (inclusive o bloqueio por vencimento). Nenhuma decisão de validade acontece
/// no Flutter.
///
/// Só é alcançável por quem tem `stock:regularize_validity`: o botão que a abre
/// já fica escondido sem a permissão, e o backend reconfere RBAC e isolamento
/// antes de gravar — a tela nunca é a autoridade.
class RegularizeValiditySheet extends StatefulWidget {
  const RegularizeValiditySheet({super.key});

  /// Abre a folha reaproveitando o `StockCubit` da tela (como
  /// `AvailableItemsSheet.show`): o cubit vive acima do Navigator, então é
  /// repassado por `BlocProvider.value` ao contexto do modal.
  static Future<void> show(BuildContext context) {
    final cubit = context.read<StockCubit>();
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(EpiRadius.lg)),
      ),
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: const RegularizeValiditySheet(),
      ),
    );
  }

  @override
  State<RegularizeValiditySheet> createState() =>
      _RegularizeValiditySheetState();
}

class _RegularizeValiditySheetState extends State<RegularizeValiditySheet> {
  final _qrController = TextEditingController();
  final _evidenceController = TextEditingController();
  final _justificationController = TextEditingController();
  DateTime? _expiry;
  bool _submitting = false;
  String? _error;
  RegularizationResult? _result;

  @override
  void dispose() {
    _qrController.dispose();
    _evidenceController.dispose();
    _justificationController.dispose();
    super.dispose();
  }

  /// `YYYY-MM-DD` literal — o contrato de data do backend. Formatar à mão evita
  /// depender do locale do aparelho para uma data que é dado, não texto de UI.
  String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _expiry ?? now,
      firstDate: DateTime(now.year - 20),
      lastDate: DateTime(now.year + 30),
    );
    if (picked != null) setState(() => _expiry = picked);
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<StockCubit>();
    final qr = _qrController.text.trim();
    final evidence = _evidenceController.text.trim();
    final justification = _justificationController.text.trim();
    final expiry = _expiry;
    // Guarda só de PREENCHIMENTO: a validade da data, da evidência e do escopo
    // é do backend. Aqui apenas evita-se um POST que já se sabe incompleto.
    if (qr.isEmpty ||
        expiry == null ||
        evidence.isEmpty ||
        justification.isEmpty) {
      setState(() => _error = l10n.stockRegularizeIncomplete);
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await cubit.regularizeValidity(
        companyId: cubit.state.companyId,
        qrCode: qr,
        physicalExpiryDate: _iso(expiry),
        evidence: evidence,
        justification: justification,
      );
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _result = result;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = e.toString();
      });
    }
  }

  /// Mensagem derivada dos campos ESTRUTURADOS do backend (não do texto cru, que
  /// vem só em pt-BR): vencida → bloqueada; apta → elegível; demais → concluída.
  String _resultMessage(AppLocalizations l10n, RegularizationResult r) {
    if (r.blockedExpired) return l10n.stockRegularizeResultBlocked;
    if (r.eligible) return l10n.stockRegularizeResultEligible;
    return l10n.stockRegularizeResultDone;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final result = _result;
    final expiry = _expiry;
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.viewInsetsOf(context).bottom,
        left: EpiSpacing.xl2,
        right: EpiSpacing.xl2,
        top: EpiSpacing.xl2,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.stockRegularizeValidityTitle,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: EpiSpacing.xs),
            Text(
              l10n.stockRegularizeValiditySubtitle,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
            ),
            const SizedBox(height: EpiSpacing.lg),
            TextField(
              controller: _qrController,
              decoration: InputDecoration(
                labelText: l10n.stockRegularizeQrLabel,
                prefixIcon: const Icon(Icons.qr_code_2_rounded),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: EpiSpacing.md),
            InkWell(
              onTap: _submitting ? null : _pickDate,
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: l10n.stockRegularizeExpiryLabel,
                  prefixIcon: const Icon(Icons.event_rounded),
                  border: const OutlineInputBorder(),
                ),
                child: Text(
                  expiry != null ? _iso(expiry) : l10n.stockRegularizeExpirySelect,
                ),
              ),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _evidenceController,
              minLines: 1,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: l10n.stockRegularizeEvidenceLabel,
                prefixIcon: const Icon(Icons.attachment_rounded),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: _justificationController,
              minLines: 1,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: l10n.stockRegularizeJustificationLabel,
                prefixIcon: const Icon(Icons.notes_rounded),
                border: const OutlineInputBorder(),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: EpiSpacing.md),
              Row(
                children: [
                  const Icon(
                    Icons.error_outline_rounded,
                    size: 18,
                    color: EpiColors.danger,
                  ),
                  const SizedBox(width: EpiSpacing.xs),
                  Expanded(
                    child: Text(
                      _error!,
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(color: EpiColors.danger),
                    ),
                  ),
                ],
              ),
            ],
            if (result != null) ...[
              const SizedBox(height: EpiSpacing.md),
              Container(
                padding: const EdgeInsets.all(EpiSpacing.md),
                decoration: BoxDecoration(
                  color:
                      (result.blockedExpired
                              ? EpiColors.danger
                              : EpiColors.success)
                          .withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(EpiRadius.md),
                ),
                child: Row(
                  children: [
                    Icon(
                      result.blockedExpired
                          ? Icons.block_rounded
                          : Icons.check_circle_rounded,
                      color: result.blockedExpired
                          ? EpiColors.danger
                          : EpiColors.success,
                    ),
                    const SizedBox(width: EpiSpacing.sm),
                    Expanded(child: Text(_resultMessage(l10n, result))),
                  ],
                ),
              ),
            ],
            const SizedBox(height: EpiSpacing.xl),
            Row(
              children: [
                Expanded(
                  child: EpiButton(
                    label: l10n.cancel,
                    variant: EpiButtonVariant.ghost,
                    onPressed: () => Navigator.pop(context),
                  ),
                ),
                const SizedBox(width: EpiSpacing.md),
                Expanded(
                  child: EpiButton(
                    label: l10n.stockRegularizeSubmit,
                    onPressed: _submitting ? null : _submit,
                    loading: _submitting,
                    icon: Icons.verified_rounded,
                  ),
                ),
              ],
            ),
            const SizedBox(height: EpiSpacing.xl2),
          ],
        ),
      ),
    );
  }
}
