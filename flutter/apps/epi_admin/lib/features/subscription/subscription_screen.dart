import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';

/// Configurações → Minha Assinatura.
///
/// Mostra a assinatura vigente da empresa e permite cancelar. Toda a lógica
/// financeira vive no backend (`/api/subscriptions/*`); aqui apenas exibimos o
/// estado e disparamos ações autenticadas.
class SubscriptionScreen extends StatefulWidget {
  const SubscriptionScreen({super.key});

  @override
  State<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends State<SubscriptionScreen> {
  late Future<Subscription?> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = ApiClient.subscriptions.getCurrent();
  }

  void _reload() {
    setState(() {
      _future = ApiClient.subscriptions.getCurrent();
    });
  }

  static String _planLabel(String key) {
    switch (key.toLowerCase()) {
      case 'start':
        return 'START';
      case 'business':
        return 'BUSINESS';
      case 'corporate':
        return 'CORPORATE';
      case 'enterprise':
        return 'ENTERPRISE';
      default:
        return key.isEmpty ? '—' : key.toUpperCase();
    }
  }

  static String _statusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'active':
      case 'authorized':
        return 'Ativa';
      case 'pending':
        return 'Pendente';
      case 'paused':
        return 'Pausada';
      case 'cancelled':
      case 'canceled':
        return 'Cancelada';
      case 'expired':
        return 'Expirada';
      default:
        return status.isEmpty ? '—' : status;
    }
  }

  static Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'active':
      case 'authorized':
        return EpiColors.success;
      case 'cancelled':
      case 'canceled':
      case 'expired':
        return EpiColors.danger;
      default:
        return EpiColors.brand;
    }
  }

  static String _cycleLabel(String cycle) =>
      cycle.toLowerCase() == 'annual' ? 'Anual' : 'Mensal';

  static String _methodLabel(String method) {
    switch (method.toLowerCase()) {
      case 'card':
        return 'Cartão (recorrente)';
      case 'pix':
        return 'PIX';
      case 'boleto':
        return 'Boleto';
      default:
        return method.isEmpty ? '—' : method;
    }
  }

  static String _money(double value, String currency) {
    final symbol = currency == 'BRL' ? 'R\$' : currency;
    return '$symbol ${value.toStringAsFixed(2)}';
  }

  static String _date(String iso) {
    if (iso.isEmpty) return '—';
    // ISO 8601 → dd/mm/aaaa (sem dependência de intl).
    final datePart = iso.length >= 10 ? iso.substring(0, 10) : iso;
    final parts = datePart.split('-');
    if (parts.length == 3) return '${parts[2]}/${parts[1]}/${parts[0]}';
    return datePart;
  }

  Future<void> _confirmCancel(Subscription sub) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tem certeza?'),
        content: const Text(
          'Seu acesso continuará disponível até o final do período já pago.\n'
          'Nenhuma nova cobrança será realizada.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Voltar'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: TextButton.styleFrom(foregroundColor: EpiColors.danger),
            child: const Text('Confirmar Cancelamento'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await ApiClient.subscriptions.cancel();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Assinatura cancelada.')),
      );
      _reload();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Não foi possível cancelar: $e'),
          backgroundColor: EpiColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Minha Assinatura'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _busy ? null : _reload,
          ),
        ],
      ),
      body: FutureBuilder<Subscription?>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _ErrorState(message: '${snapshot.error}', onRetry: _reload);
          }
          final sub = snapshot.data;
          if (sub == null) {
            return const _EmptyState();
          }
          return _SubscriptionDetails(
            sub: sub,
            busy: _busy,
            onCancel: () => _confirmCancel(sub),
          );
        },
      ),
    );
  }
}

class _SubscriptionDetails extends StatelessWidget {
  const _SubscriptionDetails({
    required this.sub,
    required this.busy,
    required this.onCancel,
  });

  final Subscription sub;
  final bool busy;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(EpiSpacing.lg),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                _SubscriptionScreenState._planLabel(sub.planKey),
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            _StatusBadge(status: sub.status),
          ],
        ),
        const SizedBox(height: EpiSpacing.lg),
        _InfoRow(label: 'Valor', value: _SubscriptionScreenState._money(sub.amount, sub.currency)),
        _InfoRow(label: 'Periodicidade', value: _SubscriptionScreenState._cycleLabel(sub.paymentCycle)),
        _InfoRow(label: 'Forma de pagamento', value: _SubscriptionScreenState._methodLabel(sub.paymentMethod)),
        _InfoRow(label: 'Data da contratação', value: _SubscriptionScreenState._date(sub.createdAt)),
        _InfoRow(label: 'Próxima cobrança', value: sub.isRecurring ? _SubscriptionScreenState._date(sub.nextPaymentDate) : 'Renovação manual'),
        _InfoRow(label: 'Última cobrança', value: _SubscriptionScreenState._date(sub.lastPaymentDate)),
        if (sub.isCancelled)
          _InfoRow(label: 'Cancelada em', value: _SubscriptionScreenState._date(sub.cancelDate)),
        const Divider(height: EpiSpacing.xl2),
        _InfoRow(label: 'ID da assinatura (MP)', value: sub.preapprovalId.isEmpty ? '—' : sub.preapprovalId),
        _InfoRow(label: 'Status Mercado Pago', value: sub.mpStatus.isEmpty ? '—' : sub.mpStatus),
        _InfoRow(label: 'Empresa', value: sub.companyId?.toString() ?? '—'),
        _InfoRow(label: 'Tenant', value: sub.tenantId.isEmpty ? '—' : sub.tenantId),
        const SizedBox(height: EpiSpacing.xl),
        if (!sub.isCancelled)
          EpiButton(
            label: 'Cancelar assinatura',
            variant: EpiButtonVariant.danger,
            fullWidth: true,
            loading: busy,
            onPressed: busy ? null : onCancel,
          ),
        if (sub.isCancelled)
          Container(
            padding: const EdgeInsets.all(EpiSpacing.lg),
            decoration: BoxDecoration(
              color: EpiColors.danger.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Text(
              'Assinatura cancelada. O acesso permanece ativo até o final do '
              'período já pago; nenhuma nova cobrança será realizada.',
            ),
          ),
        const SizedBox(height: EpiSpacing.xl),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: EpiSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).hintColor,
                  ),
            ),
          ),
          Expanded(
            flex: 3,
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final color = _SubscriptionScreenState._statusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.md,
        vertical: EpiSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        _SubscriptionScreenState._statusLabel(status),
        style: Theme.of(context)
            .textTheme
            .labelMedium
            ?.copyWith(color: color, fontWeight: FontWeight.w700),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.xl2),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.receipt_long_outlined,
                size: 56, color: Theme.of(context).hintColor),
            const SizedBox(height: EpiSpacing.lg),
            Text(
              'Nenhuma assinatura ativa',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              'Quando uma assinatura for contratada, os detalhes aparecerão aqui.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).hintColor,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.xl2),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: EpiColors.danger),
            const SizedBox(height: EpiSpacing.lg),
            Text(
              'Não foi possível carregar a assinatura.',
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).hintColor,
                  ),
            ),
            const SizedBox(height: EpiSpacing.lg),
            EpiButton(label: 'Tentar novamente', onPressed: onRetry),
          ],
        ),
      ),
    );
  }
}
