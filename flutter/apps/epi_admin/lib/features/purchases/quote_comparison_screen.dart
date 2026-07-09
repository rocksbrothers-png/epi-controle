import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

/// Comparação de cotações (Fase F3): matriz item × fornecedor com melhor
/// preço/prazo e totais por fornecedor — dados prontos do backend, nada é
/// recalculado no app.
class QuoteComparisonScreen extends StatelessWidget {
  const QuoteComparisonScreen({super.key, required this.comparison});
  final Map<String, dynamic> comparison;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final suppliers = ((comparison['suppliers'] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    final items = ((comparison['items'] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    return Scaffold(
      appBar: AppBar(title: Text(l10n.quoteComparisonTitle)),
      body: ListView(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        children: [
          // Totais por fornecedor (ordenados pelo menor total no backend)
          for (final s in suppliers)
            Card(
              child: ListTile(
                leading: const Icon(Icons.storefront_outlined),
                title: Text('${s['supplier_name'] ?? ''}'),
                subtitle: Text(
                  [
                    '${l10n.quoteFreightLabel}: '
                        'R\$ ${_money(s['freight_value'])}',
                    if ('${s['payment_terms'] ?? ''}'.isNotEmpty)
                      '${s['payment_terms']}',
                  ].join(' · '),
                ),
                trailing: Text(
                  'R\$ ${_money(s['total_with_freight'])}',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
            ),
          const SizedBox(height: EpiSpacing.lg),
          // Matriz por item
          for (final item in items) ...[
            Text(
              '${item['epi_name'] ?? ''} '
              '(x${item['quantity_requested'] ?? 0})',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: EpiSpacing.xs),
            for (final offer in ((item['offers'] as List?) ?? [])
                .map((e) => (e as Map).cast<String, dynamic>()))
              ListTile(
                dense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: EpiSpacing.sm),
                title: Text('${offer['supplier_name'] ?? ''}'),
                subtitle: offer['declined'] == true
                    ? Text(l10n.quoteDeclinedLabel)
                    : Text(
                        '${l10n.quoteUnitPriceLabel}: '
                        'R\$ ${_money(offer['unit_price'])} · '
                        '${l10n.catalogLeadTimeLabel}: '
                        '${offer['lead_time_days'] ?? 0}',
                      ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (offer['best_price'] == true)
                      _Badge(
                          label: l10n.quoteBestPriceLabel,
                          color: EpiColors.success),
                    if (offer['best_lead_time'] == true) ...[
                      const SizedBox(width: EpiSpacing.xs),
                      _Badge(
                          label: l10n.quoteBestLeadTimeLabel,
                          color: EpiColors.info),
                    ],
                  ],
                ),
              ),
            const Divider(),
          ],
        ],
      ),
    );
  }

  static String _money(dynamic value) =>
      (double.tryParse('$value') ?? 0).toStringAsFixed(2);
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.sm,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(EpiRadius.full),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: Theme.of(context)
            .textTheme
            .labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}
