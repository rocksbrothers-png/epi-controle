import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/purchases_cubit.dart';
import 'new_purchase_screen.dart';

class PurchasesScreen extends StatelessWidget {
  const PurchasesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => PurchasesCubit()..load(),
      child: const _PurchasesBody(),
    );
  }
}

class _PurchasesBody extends StatelessWidget {
  const _PurchasesBody();

  static const _statusFilters = [
    (label: 'Todos', value: ''),
    (label: 'Aguardando', value: 'pending'),
    (label: 'Aprovado', value: 'approved'),
    (label: 'Rejeitado', value: 'rejected'),
    (label: 'Recebido', value: 'received'),
  ];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.purchasesTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<PurchasesCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openNew(context),
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.purchasesNew),
      ),
      body: Column(
        children: [
          const _StatusFilterBar(filters: _statusFilters),
          Expanded(
            child: BlocBuilder<PurchasesCubit, PurchasesState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<PurchasesCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(
                    title: l10n.noResults,
                    icon: Icons.shopping_cart_outlined,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<PurchasesCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm,
                      bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1, indent: 16),
                    itemBuilder: (_, i) => _PurchaseTile(request: items[i]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openNew(BuildContext context) async {
    final cubit = context.read<PurchasesCubit>();
    final data = await _bootstrapData();
    if (!context.mounted) return;
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => NewPurchaseScreen(
          epis: data.$1,
          units: data.$2,
        ),
      ),
    );
    if (created == true) cubit.load();
  }

  Future<(List<Epi>, List<Map<String, dynamic>>)> _bootstrapData() async {
    try {
      final b = await ApiClient.auth.bootstrap();
      return (
        b.epis.map(Epi.fromJson).toList(),
        b.units,
      );
    } on Exception {
      return (<Epi>[], <Map<String, dynamic>>[]);
    }
  }
}

class _StatusFilterBar extends StatelessWidget {
  const _StatusFilterBar({required this.filters});
  final List<({String label, String value})> filters;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<PurchasesCubit, PurchasesState>(
      buildWhen: (p, c) => p.statusFilter != c.statusFilter,
      builder: (ctx, state) {
        return SizedBox(
          height: 44,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
            separatorBuilder: (_, __) =>
                const SizedBox(width: EpiSpacing.sm),
            itemCount: filters.length,
            itemBuilder: (_, i) {
              final f = filters[i];
              final selected = (state.statusFilter ?? '') == f.value;
              return ChoiceChip(
                label: Text(f.label),
                selected: selected,
                onSelected: (_) =>
                    ctx.read<PurchasesCubit>().filterByStatus(f.value),
              );
            },
          ),
        );
      },
    );
  }
}

class _PurchaseTile extends StatelessWidget {
  const _PurchaseTile({required this.request});
  final PurchaseRequest request;

  static const _statusColors = <String, Color>{
    'draft': EpiColors.textMuted,
    'pending': EpiColors.warning,
    'approved': EpiColors.success,
    'rejected': EpiColors.danger,
    'received': EpiColors.info,
    'ordering': EpiColors.brand,
  };

  static const _statusLabels = <String, String>{
    'draft': 'Rascunho',
    'pending': 'Aguardando',
    'approved': 'Aprovado',
    'rejected': 'Rejeitado',
    'received': 'Recebido',
    'ordering': 'Em pedido',
    'waiting_requester_correction': 'Correção solicitada',
    'waiting_approval': 'Aguardando aprovação',
    'waiting_receipt': 'Aguardando recebimento',
    'completed': 'Concluído',
    'cancelled': 'Cancelado',
  };

  Color get _statusColor =>
      _statusColors[request.status] ?? EpiColors.textMuted;
  String get _statusLabel =>
      _statusLabels[request.status] ?? request.status;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  request.title,
                  style: Theme.of(context).textTheme.bodyLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: EpiSpacing.xs),
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 14,
                      color: EpiColors.textMuted,
                    ),
                    const SizedBox(width: 2),
                    Text(
                      request.unitName,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: EpiColors.textMuted),
                    ),
                    const SizedBox(width: EpiSpacing.md),
                    const Icon(
                      Icons.inventory_2_outlined,
                      size: 14,
                      color: EpiColors.textMuted,
                    ),
                    const SizedBox(width: 2),
                    Text(
                      '${request.items.length} iten${request.items.length == 1 ? "" : "s"}',
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: EpiColors.textMuted),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: EpiSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.sm,
              vertical: 3,
            ),
            decoration: BoxDecoration(
              color: _statusColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(EpiRadius.full),
              border: Border.all(color: _statusColor.withOpacity(0.4)),
            ),
            child: Text(
              _statusLabel,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: _statusColor,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RetryView extends StatelessWidget {
  const _RetryView({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded,
              size: 48, color: EpiColors.textMuted),
          const SizedBox(height: EpiSpacing.lg),
          Text(l10n.errorNetwork,
              style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(label: l10n.retry, onPressed: onRetry),
        ],
      ),
    );
  }
}
