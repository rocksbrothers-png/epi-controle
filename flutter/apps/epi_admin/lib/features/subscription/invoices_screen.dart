import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/i18n/presentation_formatters.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';

/// Histórico Financeiro (PR 6) — todas as cobranças da empresa.
///
/// Consome `GET /api/subscriptions/invoices` (PR 2). Backend é a fonte única de
/// verdade; aqui apenas listamos e filtramos. Recibos abrem via url_launcher.
class InvoicesScreen extends StatefulWidget {
  const InvoicesScreen({super.key});

  @override
  State<InvoicesScreen> createState() => _InvoicesScreenState();
}

class _InvoicesScreenState extends State<InvoicesScreen> {
  static List<(String?, String)> _statusFilters(AppLocalizations l) => [
    (null, l.dashboardFilterAll),
    ('paid', l.billingInvoicePaid),
    ('pending', l.billingInvoicePending),
    ('cancelled', l.billingInvoiceCancelled),
    ('refunded', l.billingInvoiceRefunded),
    ('failed', l.billingInvoiceFailed),
  ];

  String? _status;
  late Future<List<Invoice>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Invoice>> _load() =>
      ApiClient.subscriptions.listInvoices(status: _status);

  void _reload() => setState(() => _future = _load());

  void _setStatus(String? status) {
    setState(() {
      _status = status;
      _future = _load();
    });
  }

  static String _statusLabel(String status, AppLocalizations l) {
    switch (status.toLowerCase()) {
      case 'paid':
        return l.billingInvoicePaid;
      case 'pending':
        return l.billingInvoicePending;
      case 'cancelled':
      case 'canceled':
        return l.billingInvoiceCancelled;
      case 'refunded':
        return l.billingInvoiceRefunded;
      case 'failed':
        return l.billingInvoiceFailed;
      default:
        return status.isEmpty ? '—' : status;
    }
  }

  static Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'paid':
        return EpiColors.success;
      case 'cancelled':
      case 'canceled':
      case 'failed':
        return EpiColors.danger;
      case 'refunded':
        return EpiColors.brand;
      case 'pending':
        return EpiColors.warning;
      default:
        return EpiColors.textMuted;
    }
  }

  static String _methodLabel(String method, AppLocalizations l) {
    switch (method.toLowerCase()) {
      case 'card':
      case 'subscription':
        return l.billingCard;
      case 'pix':
        return 'PIX';
      case 'boleto':
        return l.billingBoleto;
      default:
        return method.isEmpty ? '—' : method;
    }
  }

  Future<void> _openReceipt(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Builder(
            builder: (context) =>
                Text(AppLocalizations.of(context).billingReceiptOpenFailed),
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l.settingsInvoicesTileTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _reload,
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _FilterBar(
            filters: _statusFilters(l),
            selected: _status,
            onSelected: _setStatus,
          ),
          Expanded(
            child: FutureBuilder<List<Invoice>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return _CenteredMessage(
                    icon: Icons.error_outline,
                    color: EpiColors.danger,
                    title: l.billingHistoryLoadFailed,
                    subtitle: '${snapshot.error}',
                    onRetry: _reload,
                  );
                }
                final invoices = snapshot.data ?? const [];
                if (invoices.isEmpty) {
                  return _CenteredMessage(
                    icon: Icons.receipt_long_outlined,
                    title: l.billingInvoicesEmptyTitle,
                    subtitle: l.billingInvoicesEmptyBody,
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: EpiSpacing.sm),
                  itemCount: invoices.length,
                  separatorBuilder: (_, _) => const Divider(height: 1),
                  itemBuilder: (context, i) => _InvoiceTile(
                    invoice: invoices[i],
                    onOpenReceipt: _openReceipt,
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.filters,
    required this.selected,
    required this.onSelected,
  });

  final List<(String?, String)> filters;
  final String? selected;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.sm,
      ),
      child: Row(
        children: [
          for (final f in filters)
            Padding(
              padding: const EdgeInsets.only(right: EpiSpacing.sm),
              child: ChoiceChip(
                label: Text(f.$2),
                selected: selected == f.$1,
                onSelected: (_) => onSelected(f.$1),
              ),
            ),
        ],
      ),
    );
  }
}

class _InvoiceTile extends StatelessWidget {
  const _InvoiceTile({required this.invoice, required this.onOpenReceipt});

  final Invoice invoice;
  final Future<void> Function(String url) onOpenReceipt;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final color = _InvoicesScreenState._statusColor(invoice.status);
    final hasReceipt = invoice.receiptUrl.isNotEmpty;
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      title: Row(
        children: [
          Flexible(
            child: Text(
              formatDisplayMoney(
                invoice.amount,
                invoice.currency,
                l.localeName,
              ),
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: EpiSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.sm,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              _InvoicesScreenState._statusLabel(invoice.status, l),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(
          '${formatDisplayDate(invoice.createdAt, l.localeName)} · '
          '${_InvoicesScreenState._methodLabel(invoice.paymentMethod, l)}'
          '${invoice.mpPaymentId.isNotEmpty ? ' · MP ${invoice.mpPaymentId}' : ''}',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
        ),
      ),
      trailing: hasReceipt
          ? IconButton(
              icon: const Icon(Icons.receipt_outlined),
              tooltip: l.billingOpenReceipt,
              onPressed: () => onOpenReceipt(invoice.receiptUrl),
            )
          : null,
    );
  }
}

class _CenteredMessage extends StatelessWidget {
  const _CenteredMessage({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.color,
    this.onRetry,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color? color;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.xl2),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: color ?? Theme.of(context).hintColor),
            const SizedBox(height: EpiSpacing.lg),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).hintColor,
              ),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: EpiSpacing.lg),
              EpiButton(label: l.retry, onPressed: onRetry!),
            ],
          ],
        ),
      ),
    );
  }
}
