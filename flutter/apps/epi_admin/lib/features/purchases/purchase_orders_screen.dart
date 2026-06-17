import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/purchases_cubit.dart';

/// Lista de Ordens de Compra (PO). Read-only nesta etapa; ações de workflow
/// (criar/aprovar/receber) vêm em seguida, consumindo o PurchasesCubit.
class PurchaseOrdersScreen extends StatelessWidget {
  const PurchaseOrdersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => PurchasesCubit()..loadPurchaseOrders(),
      child: const _PurchaseOrdersBody(),
    );
  }
}

class _PurchaseOrdersBody extends StatelessWidget {
  const _PurchaseOrdersBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.purchaseOrdersTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<PurchasesCubit>().loadPurchaseOrders(),
          ),
        ],
      ),
      body: BlocBuilder<PurchasesCubit, PurchasesState>(
        builder: (ctx, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.error != null) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.wifi_off_rounded,
                      size: 48, color: EpiColors.textMuted),
                  const SizedBox(height: EpiSpacing.lg),
                  Text(l10n.errorNetwork),
                  const SizedBox(height: EpiSpacing.xl),
                  EpiButton(
                    label: l10n.retry,
                    onPressed: () =>
                        context.read<PurchasesCubit>().loadPurchaseOrders(),
                  ),
                ],
              ),
            );
          }
          final orders = state.purchaseOrders;
          if (orders.isEmpty) {
            return EpiEmptyState(title: l10n.noResults);
          }
          return RefreshIndicator(
            onRefresh: () => context.read<PurchasesCubit>().loadPurchaseOrders(),
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
              itemCount: orders.length,
              separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
              itemBuilder: (_, i) => _PoTile(order: orders[i]),
            ),
          );
        },
      ),
    );
  }
}

class _PoTile extends StatelessWidget {
  const _PoTile({required this.order});
  final Map<String, dynamic> order;

  @override
  Widget build(BuildContext context) {
    final number = '${order['po_number'] ?? ''}'.isEmpty
        ? 'PO #${order['id'] ?? ''}'
        : '${order['po_number']}';
    final supplier = '${order['supplier'] ?? ''}';
    final status = '${order['status'] ?? ''}';
    final subtitle = [supplier, status].where((s) => s.isNotEmpty).join(' • ');
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: EpiColors.brandSoft,
          borderRadius: BorderRadius.circular(EpiRadius.sm),
        ),
        child: const Icon(Icons.receipt_long_outlined,
            color: EpiColors.brand, size: 24),
      ),
      title: Text(number),
      subtitle: subtitle.isNotEmpty ? Text(subtitle) : null,
      trailing: Text('${order['total_value'] ?? ''}'),
    );
  }
}
