import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/purchases_cubit.dart';
import 'po_supplier_screen.dart';
import 'receive_purchase_order_screen.dart';

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

  /// Ação disponível no caminho principal de avanço, conforme o status.
  /// Retorna (labelKey, future) ou null se não houver ação simples.
  ({String label, Future<bool> Function() run})? _action(
      BuildContext context, AppLocalizations l10n) {
    final cubit = context.read<PurchasesCubit>();
    final id = (order['id'] as num?)?.toInt() ?? 0;
    final status = '${order['status'] ?? ''}';
    switch (status) {
      case 'pending_approval':
      case 'postponed':
        return (label: l10n.poApprove, run: () => cubit.approvePurchaseOrder(id, {'decision': 'approved'}));
      case 'received':
        return (label: l10n.poCheck, run: () => cubit.receivePurchaseOrder(id, {'action': 'checked'}));
      case 'checked':
        return (label: l10n.close, run: () => cubit.receivePurchaseOrder(id, {'action': 'closed'}));
      default:
        return null;
    }
  }

  Future<void> _confirm(BuildContext context, String label, Future<bool> Function() run) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final number = '${order['po_number'] ?? order['id'] ?? ''}';
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(l10n.confirm),
        content: Text('$label — $number'),
        actions: [
          TextButton(onPressed: () => Navigator.of(d).pop(false), child: Text(l10n.cancel)),
          TextButton(onPressed: () => Navigator.of(d).pop(true), child: Text(l10n.confirm)),
        ],
      ),
    );
    if (ok != true) return;
    final success = await run();
    if (!success) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorGeneric)));
    }
  }

  /// Reprovar a PO (na fase de aprovação) — exige comentário no backend.
  Future<void> _reject(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<PurchasesCubit>();
    final messenger = ScaffoldMessenger.of(context);
    final id = (order['id'] as num?)?.toInt() ?? 0;
    final controller = TextEditingController();
    final comment = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(l10n.feedbackReject),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(labelText: l10n.feedbackJustification),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(d).pop(), child: Text(l10n.cancel)),
          TextButton(
            onPressed: () => Navigator.of(d).pop(controller.text.trim()),
            child: Text(l10n.confirm),
          ),
        ],
      ),
    );
    controller.dispose();
    if (comment == null || comment.isEmpty) return;
    final ok = await cubit.approvePurchaseOrder(id, {'decision': 'rejected', 'comment': comment});
    if (!ok) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorGeneric)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final number = '${order['po_number'] ?? ''}'.isEmpty
        ? 'PO #${order['id'] ?? ''}'
        : '${order['po_number']}';
    final supplier = '${order['supplier'] ?? ''}';
    final status = '${order['status'] ?? ''}';
    final subtitle = [supplier, status].where((s) => s.isNotEmpty).join(' • ');
    final action = _action(context, l10n);
    final canReject = status == 'pending_approval' || status == 'postponed';
    final canReceive = status == 'approved' || status == 'received_partial';
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
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('${order['total_value'] ?? ''}'),
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'reject') {
                _reject(context);
              } else if (v == 'receive') {
                final cubit = context.read<PurchasesCubit>();
                final id = (order['id'] as num?)?.toInt() ?? 0;
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        ReceivePurchaseOrderScreen(cubit: cubit, poId: id),
                  ),
                );
              } else if (v == 'supplier') {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => PoSupplierScreen(order: order),
                  ),
                );
              } else if (action != null) {
                _confirm(context, action.label, action.run);
              }
            },
            itemBuilder: (_) => [
              if (action != null)
                PopupMenuItem<String>(value: 'go', child: Text(action.label)),
              if (canReceive)
                PopupMenuItem<String>(value: 'receive', child: Text(l10n.poReceive)),
              if (canReject)
                PopupMenuItem<String>(value: 'reject', child: Text(l10n.feedbackReject)),
              PopupMenuItem<String>(
                  value: 'supplier',
                  child: Text(l10n.poSupplierActionsTitle)),
            ],
          ),
        ],
      ),
    );
  }
}
