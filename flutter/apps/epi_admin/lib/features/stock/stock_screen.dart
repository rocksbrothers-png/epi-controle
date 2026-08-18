import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
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
    return DefaultTabController(
      length: 2,
      child: Scaffold(
      appBar: AppBar(
        title: Text(l10n.stockTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<StockCubit>().load(),
          ),
        ],
        bottom: TabBar(
          // A aba de bloqueados carrega sob demanda: só o primeiro toque
          // dispara a consulta, e trocar de aba não recarrega o que já veio.
          onTap: (index) {
            if (index == 1 &&
                context.read<StockCubit>().state.blockedStatus ==
                    StockListStatus.idle) {
              context.read<StockCubit>().loadBlockedItems();
            }
          },
          tabs: [
            Tab(text: l10n.navEpis),
            Tab(text: l10n.stockTabBlocked),
          ],
        ),
      ),
      body: TabBarView(
        children: [
          _buildEpisTab(context, l10n),
          const _BlockedTab(),
        ],
      ),
    ));
  }

  /// Aba de EPIs — a lista que já existia, agora em aba própria para dar
  /// lugar aos itens bloqueados sem empurrar a busca e os filtros de
  /// conformidade para dentro de uma aba que não os usa.
  Widget _buildEpisTab(BuildContext context, AppLocalizations l10n) {
    return Column(
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
          const _ComplianceFilters(),
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
    );
  }
}

/// Rótulo traduzido para uma chave de status vinda do backend.
///
/// O backend envia junto um mapa `statuses` com textos em português. Usar
/// aquele texto deixaria o app em português nos outros quatro idiomas — por
/// isso a chave é o contrato e o rótulo sai do ARB. Chave desconhecida cai num
/// rótulo genérico em vez de sumir da tela: um item bloqueado que não aparece
/// é pior que um item com rótulo impreciso.
String stockStatusLabel(AppLocalizations l10n, String statusKey) =>
    switch (statusKey) {
      'blocked_expired' => l10n.stockStatusBlockedExpired,
      'blocked_discard' => l10n.stockStatusBlockedDiscard,
      'blocked_return' => l10n.stockStatusBlockedReturn,
      'blocked_analysis' => l10n.stockStatusBlockedAnalysis,
      'blocked_rejected' => l10n.stockStatusBlockedRejected,
      'blocked_archived' => l10n.stockStatusBlockedArchived,
      _ => l10n.stockStatusUnknown,
    };

/// Estados de uma lista carregada sob demanda: carregando, sem permissão de
/// contexto (403), erro com retry, vazio, ou a lista.
class _StockListView extends StatelessWidget {
  const _StockListView({
    required this.status,
    required this.items,
    required this.emptyMessage,
    required this.onRetry,
    this.idleMessage,
  });

  final StockListStatus status;
  final List<StockItem> items;
  final String emptyMessage;
  final VoidCallback onRetry;

  /// Mensagem para `idle` — nada foi consultado ainda. Sem isto, a tela
  /// mostraria "nenhum item" antes de existir consulta, o que é falso.
  final String? idleMessage;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    switch (status) {
      case StockListStatus.idle:
        return EpiEmptyState(title: idleMessage ?? emptyMessage);
      case StockListStatus.loading:
        return const Center(child: CircularProgressIndicator());
      case StockListStatus.forbidden:
        // Sem botão de repetir: tentar de novo não cria uma unidade
        // operacional para o perfil.
        return EpiEmptyState(title: l10n.stockNoOperationalUnit);
      case StockListStatus.error:
        return _RetryView(onRetry: onRetry);
      case StockListStatus.ready:
        if (items.isEmpty) return EpiEmptyState(title: emptyMessage);
        return ListView.separated(
          padding: const EdgeInsets.only(
            top: EpiSpacing.sm, bottom: EpiSpacing.xl5,
          ),
          itemCount: items.length,
          separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
          itemBuilder: (_, i) => _StockItemTile(item: items[i]),
        );
    }
  }
}

class _StockItemTile extends StatelessWidget {
  const _StockItemTile({required this.item});
  final StockItem item;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final detalhes = <String>[
      if (item.qrCodeValue != null) item.qrCodeValue!,
      if (item.displaySize != null) item.displaySize!,
      if (item.lotCode != null) '${l10n.stockItemLotLabel} ${item.lotCode}',
      if (item.unitName != null) item.unitName!,
    ];
    return ListTile(
      title: Text(item.epiName),
      subtitle: detalhes.isEmpty ? null : Text(detalhes.join(' · ')),
      trailing: item.status == 'in_stock'
          ? null
          : Text(
              stockStatusLabel(l10n, item.status),
              style: Theme.of(context).textTheme.bodySmall,
            ),
    );
  }
}

/// Aba de itens bloqueados. A consulta é disparada pela TabBar no primeiro
/// toque; aqui só se reage ao estado.
class _BlockedTab extends StatelessWidget {
  const _BlockedTab();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<StockCubit, StockState>(
      buildWhen: (p, c) =>
          p.blockedStatus != c.blockedStatus ||
          p.blockedItems != c.blockedItems,
      builder: (context, state) => _StockListView(
        status: state.blockedStatus,
        items: state.blockedItems,
        emptyMessage: l10n.stockBlockedEmpty,
        onRetry: () => context.read<StockCubit>().loadBlockedItems(),
      ),
    );
  }
}

/// Itens disponíveis (QRs) de um EPI, em ordem FEFO definida pelo backend.
/// Abre a partir da lista de EPIs porque a rota exige `epi_id` — uma aba
/// própria nasceria vazia e sem como se preencher.
class AvailableItemsSheet extends StatelessWidget {
  const AvailableItemsSheet({super.key, required this.epi});
  final Epi epi;

  static Future<void> show(BuildContext context, Epi epi) {
    final cubit = context.read<StockCubit>()..loadAvailableItems(epi.id);
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => BlocProvider.value(
        value: cubit,
        child: AvailableItemsSheet(epi: epi),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return FractionallySizedBox(
      heightFactor: 0.75,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(EpiSpacing.lg),
            child: Text(
              '${epi.name} · ${l10n.stockTabAvailable}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Expanded(
            child: BlocBuilder<StockCubit, StockState>(
              buildWhen: (p, c) =>
                  p.availableStatus != c.availableStatus ||
                  p.availableItems != c.availableItems,
              builder: (context, state) => _StockListView(
                status: state.availableStatus,
                items: state.availableItems,
                emptyMessage: l10n.stockAvailableEmpty,
                idleMessage: l10n.stockAvailableSelectEpi,
                onRetry: () =>
                    context.read<StockCubit>().loadAvailableItems(epi.id),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Filtros de conformidade (NT 146/2015): CA vencido e validade do fabricante
/// (próxima do vencimento / vencida). Rótulos em pt-BR seguindo o padrão dos
/// componentes do design system (ex.: EpiBadge).
class _ComplianceFilters extends StatelessWidget {
  const _ComplianceFilters();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StockCubit, StockState>(
      buildWhen: (p, c) =>
          p.compliance != c.compliance ||
          p.caExpiredCount != c.caExpiredCount ||
          p.manufacturerExpiringCount != c.manufacturerExpiringCount ||
          p.manufacturerExpiredCount != c.manufacturerExpiredCount,
      builder: (context, state) {
        final cubit = context.read<StockCubit>();
        Widget chip(String label, StockComplianceFilter value, int count) {
          final selected = state.compliance == value;
          return Padding(
            padding: const EdgeInsets.only(right: EpiSpacing.sm),
            child: FilterChip(
              label: Text(count > 0 ? '$label ($count)' : label),
              selected: selected,
              onSelected: (_) => cubit.setCompliance(
                selected ? StockComplianceFilter.none : value,
              ),
            ),
          );
        }

        return SizedBox(
          height: 48,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
            children: [
              chip('CA vencido', StockComplianceFilter.caExpired,
                  state.caExpiredCount),
              chip('Validade do fabricante próxima',
                  StockComplianceFilter.manufacturerExpiring,
                  state.manufacturerExpiringCount),
              chip('Validade do fabricante vencida',
                  StockComplianceFilter.manufacturerExpired,
                  state.manufacturerExpiredCount),
            ],
          ),
        );
      },
    );
  }
}

class _StockTile extends StatelessWidget {
  const _StockTile({required this.epi, required this.onMove});
  final Epi epi;
  final void Function(int delta) onMove;

  /// Saldo da UNIDADE — esta é a tela operacional. `null` só ocorre para perfil
  /// sem unidade resolvida; nesse caso não há saldo local a exibir.
  int? get _unitStock => epi.unitStockQuantity;

  double get _barValue {
    if (epi.minimumStock == 0) return 1.0;
    return ((_unitStock ?? 0) / (epi.minimumStock * 3)).clamp(0.0, 1.0);
  }

  Color get _barColor {
    if ((_unitStock ?? 0) == 0) return EpiColors.danger;
    // Criticidade é CORPORATIVA e vem pronta do backend — o cliente não compara
    // saldo da unidade com mínimo da empresa.
    if (epi.isCompanyStockCritical == true) return EpiColors.warning;
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
                // Abre os QRs disponíveis deste EPI. Botão próprio em vez de
                // reaproveitar o toque do card, que já abre a movimentação —
                // duas ações distintas não devem disputar o mesmo gesto.
                IconButton(
                  icon: const Icon(Icons.qr_code_2_rounded),
                  tooltip: AppLocalizations.of(context).stockTabAvailable,
                  visualDensity: VisualDensity.compact,
                  onPressed: () => AvailableItemsSheet.show(context, epi),
                ),
              ],
            ),
            const SizedBox(height: EpiSpacing.xs),
            Row(
              children: [
                Text(
                  '${_unitStock ?? '—'}',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: _barColor,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                Text(
                  ' ${AppLocalizations.of(context).stockUnitBalanceSuffix}'
                  ' · ${AppLocalizations.of(context).stockCompanyBalanceLabel}'
                  ' ${epi.companyStockQuantity ?? epi.stockQuantity}'
                  ' / ${AppLocalizations.of(context).stockMinimumShort}'
                  ' ${epi.minimumStock}',
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
            if (_manufacturerNote != null) ...[
              const SizedBox(height: EpiSpacing.xs),
              Row(
                children: [
                  Icon(
                    epi.isBlockedForDelivery
                        ? Icons.block_rounded
                        : Icons.schedule_rounded,
                    size: 14,
                    color: epi.isBlockedForDelivery
                        ? EpiColors.danger
                        : EpiColors.warning,
                  ),
                  const SizedBox(width: EpiSpacing.xs),
                  Expanded(
                    child: Text(
                      _manufacturerNote!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: epi.isBlockedForDelivery
                                ? EpiColors.danger
                                : EpiColors.warning,
                          ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Mensagem sobre a validade do fabricante (NT 146/2015), quando aplicável.
  String? get _manufacturerNote {
    final status = epi.manufacturerValidityStatus;
    if (status == 'expired') {
      return 'Validade do fabricante vencida — retirar do estoque (não entregar).';
    }
    if (status == 'expiring') {
      final days = epi.daysUntilManufacturerValidity;
      return 'Validade do fabricante próxima'
          '${days != null ? ' (em $days dia(s))' : ''} — priorizar entrega (PEPS).';
    }
    return null;
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
              contentPadding: const EdgeInsets.symmetric(
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
          color: selected ? color.withValues(alpha: 0.12) : Colors.transparent,
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
