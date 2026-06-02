import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/bloc/stock_cubit.dart';
import '../../core/utils/epi_status_utils.dart';

class StockScreen extends StatelessWidget {
  const StockScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => StockCubit()..load(),
      child: const _StockBody(),
    );
  }
}

class _StockBody extends StatefulWidget {
  const _StockBody();

  @override
  State<_StockBody> createState() => _StockBodyState();
}

class _StockBodyState extends State<_StockBody> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.stockTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<StockCubit>().load(),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              EpiSpacing.lg, EpiSpacing.lg, EpiSpacing.lg, 0,
            ),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: l10n.episSearchHint,
                prefixIcon: const Icon(Icons.search_rounded),
                border: const OutlineInputBorder(),
                isDense: true,
                suffixIcon: ValueListenableBuilder<TextEditingValue>(
                  valueListenable: _searchController,
                  builder: (_, v, __) => v.text.isEmpty
                      ? const SizedBox.shrink()
                      : IconButton(
                          icon: const Icon(Icons.clear_rounded),
                          onPressed: () {
                            _searchController.clear();
                            context.read<StockCubit>().search('');
                          },
                        ),
                ),
              ),
              onChanged: (q) => context.read<StockCubit>().search(q),
            ),
          ),
          BlocBuilder<StockCubit, StockState>(
            buildWhen: (p, c) =>
                p.criticalCount != c.criticalCount ||
                p.epis.length != c.epis.length,
            builder: (_, state) => state.epis.isEmpty
                ? const SizedBox.shrink()
                : Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: EpiSpacing.lg,
                      vertical: EpiSpacing.sm,
                    ),
                    child: Row(
                      children: [
                        Text(
                          '${state.epis.length} EPIs',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        if (state.criticalCount > 0) ...[
                          const SizedBox(width: EpiSpacing.md),
                          EpiBadge(
                            status: EpiBadgeStatus.critical,
                            label: '${state.criticalCount} ${AppLocalizations.of(context).stockMinimumAlert.toLowerCase()}',
                          ),
                        ],
                      ],
                    ),
                  ),
          ),
          Expanded(
            child: BlocBuilder<StockCubit, StockState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<StockCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(title: AppLocalizations.of(context).noResults);
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<StockCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm, bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
                    itemBuilder: (_, i) => _StockTile(
                      epi: items[i],
                      onMove: (delta) => context
                          .read<StockCubit>()
                          .moveStock(epiId: items[i].id, delta: delta),
                    ),
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

class _StockTile extends StatelessWidget {
  const _StockTile({required this.epi, required this.onMove});
  final Epi epi;
  final void Function(int delta) onMove;

  double get _barValue {
    if (epi.minimumStock == 0) return 1.0;
    return (epi.stockQuantity / (epi.minimumStock * 3)).clamp(0.0, 1.0);
  }

  Color get _barColor {
    if (epi.stockQuantity == 0) return EpiColors.danger;
    if (epi.isCriticalStock) return EpiColors.warning;
    return EpiColors.success;
  }

  @override
  Widget build(BuildContext context) {
    final badge = epiBadgeStatus(epi);
    return InkWell(
      onTap: () => _showMoveSheet(context),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: EpiSpacing.lg,
          vertical: EpiSpacing.md,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    epi.name,
                    style: Theme.of(context).textTheme.bodyLarge,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: EpiSpacing.sm),
                EpiBadge(status: badge),
              ],
            ),
            const SizedBox(height: EpiSpacing.xs),
            Row(
              children: [
                Text(
                  '${epi.stockQuantity}',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: _barColor,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                Text(
                  ' / mín ${epi.minimumStock}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: EpiColors.textMuted,
                      ),
                ),
              ],
            ),
            const SizedBox(height: EpiSpacing.xs),
            LinearProgressIndicator(
              value: _barValue,
              color: _barColor,
              backgroundColor: EpiColors.border,
              minHeight: 6,
              borderRadius: BorderRadius.circular(EpiRadius.full),
            ),
          ],
        ),
      ),
    );
  }

  void _showMoveSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(EpiRadius.lg)),
      ),
      builder: (_) => _StockMoveSheet(epi: epi, onConfirm: onMove),
    );
  }
}

class _StockMoveSheet extends StatefulWidget {
  const _StockMoveSheet({required this.epi, required this.onConfirm});
  final Epi epi;
  final void Function(int delta) onConfirm;

  @override
  State<_StockMoveSheet> createState() => _StockMoveSheetState();
}

class _StockMoveSheetState extends State<_StockMoveSheet> {
  final _qtyController = TextEditingController(text: '1');
  bool _isIn = true;

  @override
  void dispose() {
    _qtyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.viewInsetsOf(context).bottom,
        left: EpiSpacing.xl2,
        right: EpiSpacing.xl2,
        top: EpiSpacing.xl2,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            widget.epi.name,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: EpiSpacing.xs),
          Text(
            '${AppLocalizations.of(context).epiStockLabel}: ${widget.epi.stockQuantity}',
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: EpiColors.textMuted),
          ),
          const SizedBox(height: EpiSpacing.xl),
          // Move type toggle
          Row(
            children: [
              Expanded(
                child: _MoveTypeButton(
                  label: l10n.stockMoveIn,
                  icon: Icons.add_circle_outline_rounded,
                  selected: _isIn,
                  color: EpiColors.success,
                  onTap: () => setState(() => _isIn = true),
                ),
              ),
              const SizedBox(width: EpiSpacing.md),
              Expanded(
                child: _MoveTypeButton(
                  label: l10n.stockMoveOut,
                  icon: Icons.remove_circle_outline_rounded,
                  selected: !_isIn,
                  color: EpiColors.danger,
                  onTap: () => setState(() => _isIn = false),
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.lg),
          TextField(
            controller: _qtyController,
            keyboardType: TextInputType.number,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.displaySmall,
            decoration: InputDecoration(
              labelText: AppLocalizations.of(context).epiStockLabel,
              border: const OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(
                horizontal: EpiSpacing.lg,
                vertical: EpiSpacing.lg,
              ),
            ),
          ),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(
            label: _isIn ? l10n.stockMoveIn : l10n.stockMoveOut,
            onPressed: _confirm,
            variant: _isIn ? EpiButtonVariant.success : EpiButtonVariant.danger,
            fullWidth: true,
            size: EpiButtonSize.lg,
            icon: _isIn
                ? Icons.add_circle_outline_rounded
                : Icons.remove_circle_outline_rounded,
          ),
          const SizedBox(height: EpiSpacing.xl2),
        ],
      ),
    );
  }

  void _confirm() {
    final qty = int.tryParse(_qtyController.text.trim()) ?? 0;
    if (qty <= 0) return;
    final delta = _isIn ? qty : -qty;
    widget.onConfirm(delta);
    Navigator.pop(context);
  }
}

class _MoveTypeButton extends StatelessWidget {
  const _MoveTypeButton({
    required this.label,
    required this.icon,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(
          vertical: EpiSpacing.md,
          horizontal: EpiSpacing.lg,
        ),
        decoration: BoxDecoration(
          color: selected ? color.withOpacity(0.12) : Colors.transparent,
          border: Border.all(
            color: selected ? color : EpiColors.border,
            width: selected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(EpiRadius.md),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: selected ? color : EpiColors.textMuted, size: 20),
            const SizedBox(width: EpiSpacing.sm),
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: selected ? color : EpiColors.textMuted,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RetryView extends StatelessWidget {
  const _RetryView({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 48, color: EpiColors.textMuted),
          const SizedBox(height: EpiSpacing.lg),
          Text(
            AppLocalizations.of(context).errorNetwork,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(
            label: AppLocalizations.of(context).retry,
            onPressed: onRetry,
          ),
        ],
      ),
    );
  }
}
