import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_api/epi_api.dart';
import '../../core/utils/epi_status_utils.dart';

class EpiDetailScreen extends StatelessWidget {
  const EpiDetailScreen({super.key, required this.epi});
  final Epi epi;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final badgeStatus = epiBadgeStatus(epi);
    final days = epi.daysUntilCaExpiry;
    return Scaffold(
      appBar: AppBar(title: Text(epi.name)),
      body: ListView(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        children: [
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: EpiColors.brandSoft,
                borderRadius: BorderRadius.circular(EpiRadius.lg),
              ),
              child: const Icon(Icons.shield_outlined, size: 48, color: EpiColors.brand),
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: Text(
              epi.name,
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Center(child: EpiBadge(status: badgeStatus)),
          const SizedBox(height: EpiSpacing.xl2),

          // Stock KPIs
          Row(
            children: [
              Expanded(
                child: EpiKpiCard(
                  label: l10n.epiStockLabel,
                  value: '${epi.stockQuantity}',
                  icon: Icons.inventory_2_outlined,
                  iconColor: epi.isCriticalStock ? EpiColors.danger : EpiColors.success,
                ),
              ),
              const SizedBox(width: EpiSpacing.md),
              Expanded(
                child: EpiKpiCard(
                  label: l10n.epiMinStockLabel,
                  value: '${epi.minimumStock}',
                  icon: Icons.warning_amber_rounded,
                  iconColor: EpiColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.xl),

          // Detail fields
          _DetailSection(
            title: 'Certificado de Aprovação (CA)',
            items: [
              if (epi.caNumber != null)
                _DetailRow(label: l10n.epiCaLabel, value: epi.caNumber!),
              if (epi.caExpiryDate != null)
                _DetailRow(label: l10n.epiCaExpiryLabel, value: epi.caExpiryDate!),
              if (days != null)
                _DetailRow(
                  label: 'Dias restantes',
                  value: days < 0 ? 'Vencido' : '$days dias',
                ),
            ],
          ),
          if (epi.code != null || epi.validityDays != null) ...[
            const SizedBox(height: EpiSpacing.lg),
            _DetailSection(
              title: 'Identificação',
              items: [
                if (epi.code != null)
                  _DetailRow(label: l10n.epiCodeLabel, value: epi.code!),
                if (epi.validityDays != null)
                  _DetailRow(
                    label: l10n.epiValidityDaysLabel,
                    value: '${epi.validityDays} dias',
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

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
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(color: EpiColors.textMuted),
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

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

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
            width: 130,
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
        ],
      ),
    );
  }
}
