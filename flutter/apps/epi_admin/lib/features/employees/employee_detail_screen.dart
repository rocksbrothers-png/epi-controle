import 'dart:io';
import 'dart:typed_data';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_api/epi_api.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import 'legal_entity_transfer_dialog.dart';

/// Rótulo exibido para cada valor de `tipo_vinculo` — mesmo mapeamento do
/// formulário de edição, para que a leitura e a escrita concordem.
String _employmentTypeLabel(AppLocalizations l10n, String value) => switch (value) {
      'CLT' => l10n.employmentTypeClt,
      'Terceirizado' => l10n.employmentTypeOutsourced,
      'Temporário' => l10n.employmentTypeTemporary,
      'Prestador de Serviço' => l10n.employmentTypeServiceProvider,
      'Menor Aprendiz' => l10n.employmentTypeApprentice,
      'Praticante' => l10n.employmentTypeTrainee,
      'Estagiário' => l10n.employmentTypeIntern,
      _ => value,
    };

class EmployeeDetailScreen extends StatelessWidget {
  const EmployeeDetailScreen({super.key, required this.employee});
  final Employee employee;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(employee.name)),
      body: ListView(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        children: [
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: EpiAvatar(name: employee.name, imageUrl: employee.photoUrl, size: 88),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: Text(
              employee.name,
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
          ),
          if (employee.role != null) ...[
            const SizedBox(height: EpiSpacing.xs),
            Center(
              child: Text(
                employee.role!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: EpiColors.textMuted,
                ),
              ),
            ),
          ],
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: EpiBadge(
              status: employee.isActive
                  ? EpiBadgeStatus.active
                  : EpiBadgeStatus.inactive,
            ),
          ),
          const SizedBox(height: EpiSpacing.xl2),
          // ── Contact action row ─────────────────────────────────────────────
          _ContactRow(employee: employee),
          const SizedBox(height: EpiSpacing.xl2),
          _DetailSection(
            title: 'Dados do colaborador',
            items: [
              if (employee.code != null)
                _DetailRow(label: l10n.employeeCodeLabel, value: employee.code!),
              if (employee.sector != null)
                _DetailRow(label: l10n.employeeSectorLabel, value: employee.sector!),
              if (employee.role != null)
                _DetailRow(label: l10n.employeeRoleLabel, value: employee.role!),
              if (employee.unitName != null)
                _DetailRow(label: l10n.employeeUnitLabel, value: employee.unitName!),
              // Vínculo jurídico (CNPJ) do contrato de trabalho. Ausente
              // enquanto o schema Multi-CNPJ não estiver provisionado.
              if (employee.legalEntityCnpj != null &&
                  employee.legalEntityCnpj!.isNotEmpty)
                _DetailRow(
                  label: l10n.employeeLegalEntityLabel,
                  value: employee.legalEntityName == null ||
                          employee.legalEntityName!.isEmpty
                      ? employee.legalEntityCnpj!
                      : '${employee.legalEntityName!} — ${employee.legalEntityCnpj!}',
                  // Alterar o vínculo jurídico é processo administrativo
                  // auditado — nunca edição comum de cadastro.
                  trailing: _LegalEntityTransferButton(employee: employee),
                ),
              if (employee.admissionDate != null)
                _DetailRow(
                  label: l10n.employeeAdmissionLabel,
                  value: employee.admissionDate!,
                ),
              if (employee.schedule != null)
                _DetailRow(label: l10n.employeeScheduleLabel, value: employee.schedule!),
              if (employee.employmentType != null &&
                  employee.employmentType!.isNotEmpty)
                _DetailRow(
                  label: l10n.employeeEmploymentTypeLabel,
                  value: _employmentTypeLabel(l10n, employee.employmentType!),
                ),
              // Só faz sentido junto do vínculo não-CLT — mesma regra
              // condicional do formulário e do web legado.
              if (employee.employmentType != null &&
                  employee.employmentType != 'CLT' &&
                  employee.sourceCompany != null &&
                  employee.sourceCompany!.isNotEmpty)
                _DetailRow(
                  label: l10n.employeeSourceCompanyLabel,
                  value: employee.sourceCompany!,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── _ContactRow ───────────────────────────────────────────────────────────────

class _ContactRow extends StatefulWidget {
  const _ContactRow({required this.employee});
  final Employee employee;

  @override
  State<_ContactRow> createState() => _ContactRowState();
}

class _ContactRowState extends State<_ContactRow> {
  bool _whatsappLoading = false;
  bool _emailLoading = false;
  bool _pdfLoading = false;

  Future<void> _launch({required String channel}) async {
    final l10n = AppLocalizations.of(context);
    final actorUserId = ApiClient.actorUserId;

    setState(() {
      if (channel == 'whatsapp') _whatsappLoading = true;
      if (channel == 'email') _emailLoading = true;
    });

    try {
      final result = await ApiClient.portal.contactLaunch(
        actorUserId: actorUserId,
        employeeId: widget.employee.id,
        channel: channel,
      );

      final uri = Uri.tryParse(result.launchUrl);
      if (uri == null || !await canLaunchUrl(uri)) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n.employeeContactErrorNoApp)),
          );
        }
        return;
      }
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Exception {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.employeeContactErrorGeneric)),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _whatsappLoading = false;
          _emailLoading = false;
        });
      }
    }
  }

  Future<void> _downloadPdf() async {
    final l10n = AppLocalizations.of(context);
    final actorUserId = ApiClient.actorUserId;

    setState(() => _pdfLoading = true);

    try {
      final Uint8List bytes = await ApiClient.portal.downloadFichaPdf(
        actorUserId: actorUserId,
        employeeId: widget.employee.id,
      );

      final dir = await getTemporaryDirectory();
      final safeName = widget.employee.name.replaceAll(RegExp(r'[^\w]'), '_');
      final file = File('${dir.path}/ficha_$safeName.pdf');
      await file.writeAsBytes(bytes, flush: true);

      final uri = Uri.file(file.path);
      if (!await canLaunchUrl(uri)) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n.employeeContactErrorNoApp)),
          );
        }
        return;
      }
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Exception {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.employeeContactPdfError)),
        );
      }
    } finally {
      if (mounted) setState(() => _pdfLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.employeeContactTitle,
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(color: EpiColors.textMuted),
        ),
        const SizedBox(height: EpiSpacing.sm),
        Row(
          children: [
            Expanded(
              child: _ContactButton(
                label: l10n.employeeContactWhatsapp,
                icon: Icons.chat_rounded,
                color: EpiColors.success,
                loading: _whatsappLoading,
                onPressed: () => _launch(channel: 'whatsapp'),
              ),
            ),
            const SizedBox(width: EpiSpacing.sm),
            Expanded(
              child: _ContactButton(
                label: l10n.employeeContactEmail,
                icon: Icons.email_rounded,
                color: EpiColors.info,
                loading: _emailLoading,
                onPressed: () => _launch(channel: 'email'),
              ),
            ),
            const SizedBox(width: EpiSpacing.sm),
            Expanded(
              child: _ContactButton(
                label: l10n.employeeContactPdf,
                icon: Icons.picture_as_pdf_rounded,
                color: EpiColors.brand,
                loading: _pdfLoading,
                onPressed: _downloadPdf,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ── _ContactButton ─────────────────────────────────────────────────────────────

class _ContactButton extends StatelessWidget {
  const _ContactButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onPressed,
    this.loading = false,
  });

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: loading ? null : onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: color,
        side: BorderSide(color: color),
        padding: const EdgeInsets.symmetric(
          horizontal: EpiSpacing.md,
          vertical: EpiSpacing.sm,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      child: loading
          ? SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2, color: color),
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 22, color: color),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: Theme.of(context)
                      .textTheme
                      .labelSmall
                      ?.copyWith(color: color),
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
    );
  }
}

// ── _DetailSection ────────────────────────────────────────────────────────────

class _DetailSection extends StatelessWidget {
  const _DetailSection({required this.title, required this.items});
  final String title;
  final List<Widget> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: EpiColors.textMuted,
              ),
        ),
        const SizedBox(height: EpiSpacing.sm),
        Card(
          margin: EdgeInsets.zero,
          child: Column(children: items),
        ),
      ],
    );
  }
}

// ── _DetailRow ────────────────────────────────────────────────────────────────

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value, this.trailing});
  final String label;
  final String value;

  /// Ação opcional à direita da linha (ex.: transferência de vínculo jurídico).
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

/// Botão que abre o processo administrativo de transferência de CNPJ.
///
/// Fica no detalhe (e não no formulário de edição) porque a alteração do
/// vínculo jurídico não é edição de cadastro: exige justificativa e gera
/// auditoria.
class _LegalEntityTransferButton extends StatelessWidget {
  const _LegalEntityTransferButton({required this.employee});
  final Employee employee;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return IconButton(
      tooltip: l10n.legalEntityTransferTitle,
      icon: const Icon(Icons.swap_horiz_rounded),
      onPressed: () async {
        final messenger = ScaffoldMessenger.of(context);
        final done = await showDialog<bool>(
          context: context,
          builder: (_) => LegalEntityTransferDialog(
            employeeId: employee.id,
            currentLegalEntityId: employee.legalEntityId,
          ),
        );
        if (done == true) {
          messenger.showSnackBar(
            SnackBar(content: Text(l10n.legalEntityTransferTitle)),
          );
        }
      },
    );
  }
}
