import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import 'new_delivery_screen.dart';

class DeliveriesScreen extends StatefulWidget {
  const DeliveriesScreen({super.key});

  @override
  State<DeliveriesScreen> createState() => _DeliveriesScreenState();
}

class _DeliveriesScreenState extends State<DeliveriesScreen> {
  List<Delivery>? _deliveries;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDeliveries();
  }

  Future<void> _loadDeliveries() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await ApiClient.deliveries.getDeliveries();
      if (mounted) setState(() => _deliveries = items);
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openNew() async {
    final bootstrap = await _loadBootstrap();
    if (!mounted) return;
    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => NewDeliveryScreen(
          employees: bootstrap.$1,
          epis: bootstrap.$2,
          companyId: bootstrap.$3,
        ),
      ),
    );
    if (result == true) _loadDeliveries();
  }

  Future<(List<Employee>, List<Epi>, int)> _loadBootstrap() async {
    try {
      final b = await ApiClient.auth.bootstrap();
      final employees = b.employees.map(Employee.fromJson).toList();
      final epis = b.epis.map(Epi.fromJson).toList();
      final companyId =
          b.units.isNotEmpty ? (b.units.first['company_id'] as int?) ?? 0 : 0;
      return (employees, epis, companyId);
    } on Exception {
      return (<Employee>[], <Epi>[], 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.deliveriesTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _loadDeliveries,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openNew,
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.deliveryNew),
      ),
      body: _buildBody(l10n),
    );
  }

  Widget _buildBody(AppLocalizations l10n) {
    if (_loading) {
      return ListView.separated(
        padding: const EdgeInsets.only(
          top: EpiSpacing.sm,
          bottom: EpiSpacing.xl5,
        ),
        itemCount: 6,
        separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
        itemBuilder: (_, __) => const _DeliverySkeletonTile(),
      );
    }

    if (_error != null) {
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
              onPressed: _loadDeliveries,
            ),
          ],
        ),
      );
    }

    final items = _deliveries ?? [];

    if (items.isEmpty) {
      return EpiEmptyState(
        title: l10n.noResults,
        icon: Icons.local_shipping_outlined,
        ctaLabel: l10n.deliveryNew,
        onCtaPressed: _openNew,
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDeliveries,
      child: ListView.separated(
        padding: const EdgeInsets.only(
          top: EpiSpacing.sm,
          bottom: EpiSpacing.xl5,
        ),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
        itemBuilder: (_, i) => _DeliveryTile(delivery: items[i]),
      ),
    );
  }
}

// ── Delivery Tile ────────────────────────────────────────────────────────────

class _DeliveryTile extends StatelessWidget {
  const _DeliveryTile({required this.delivery});
  final Delivery delivery;

  @override
  Widget build(BuildContext context) {
    final subtitle = [
      delivery.deliveryDate,
      if (delivery.sector != null && delivery.sector!.isNotEmpty)
        delivery.sector!,
    ].join(' · ');

    return ListTile(
      leading: const CircleAvatar(
        backgroundColor: EpiColors.border,
        child: Icon(
          Icons.local_shipping_outlined,
          color: EpiColors.textMuted,
        ),
      ),
      title: Text(
        '${delivery.employeeName} — ${delivery.epiName}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: subtitle.isNotEmpty
          ? Text(
              subtitle,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            )
          : null,
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: EpiColors.brand.withOpacity(0.12),
          borderRadius: BorderRadius.circular(EpiRadius.full),
          border: Border.all(color: EpiColors.brand.withOpacity(0.4)),
        ),
        child: Text(
          '×${delivery.quantity}',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: EpiColors.brand,
                fontWeight: FontWeight.w600,
              ),
        ),
      ),
    );
  }
}

// ── Skeleton Tile ────────────────────────────────────────────────────────────

class _DeliverySkeletonTile extends StatelessWidget {
  const _DeliverySkeletonTile();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          EpiLoadingSkeleton(width: 40, height: 40, borderRadius: 20),
          SizedBox(width: EpiSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                EpiLoadingSkeleton(height: 14, width: double.infinity),
                SizedBox(height: EpiSpacing.xs),
                EpiLoadingSkeleton(height: 11, width: 160),
              ],
            ),
          ),
          SizedBox(width: EpiSpacing.md),
          EpiLoadingSkeleton(width: 32, height: 20, borderRadius: 10),
        ],
      ),
    );
  }
}
