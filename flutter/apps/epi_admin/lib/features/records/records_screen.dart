import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/bloc/fichas_cubit.dart';

class RecordsScreen extends StatelessWidget {
  const RecordsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => FichasCubit()..load(),
      child: const _RecordsBody(),
    );
  }
}

class _RecordsBody extends StatelessWidget {
  const _RecordsBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.recordsTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<FichasCubit>().load(),
          ),
        ],
      ),
      body: Column(
        children: [
          _SearchBar(),
          Expanded(
            child: BlocBuilder<FichasCubit, FichasState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<FichasCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(
                    title: l10n.noResults,
                    icon: Icons.folder_open_outlined,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<FichasCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm,
                      bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1, indent: 16),
                    itemBuilder: (_, i) => _FichaTile(period: items[i]),
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

class _SearchBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.sm,
        EpiSpacing.lg,
        EpiSpacing.xs,
      ),
      child: TextField(
        onChanged: context.read<FichasCubit>().search,
        decoration: const InputDecoration(
          hintText: 'Buscar por funcionário, código ou unidade…',
          prefixIcon: Icon(Icons.search_rounded),
          border: OutlineInputBorder(),
          isDense: true,
          contentPadding: EdgeInsets.symmetric(vertical: 10),
        ),
      ),
    );
  }
}

class _FichaTile extends StatelessWidget {
  const _FichaTile({required this.period});
  final FichaPeriod period;

  static const _statusColors = <String, Color>{
    'complete': EpiColors.success,
    'pending': EpiColors.warning,
    'overdue': EpiColors.danger,
  };

  static const _statusLabels = <String, String>{
    'complete': 'Completo',
    'pending': 'Pendente',
    'overdue': 'Atrasado',
  };

  Color get _color {
    if (period.isComplete) return EpiColors.success;
    if (period.hasPending) return EpiColors.warning;
    return _statusColors[period.status] ?? EpiColors.textMuted;
  }

  String get _label {
    if (period.isComplete) return 'Completo';
    if (period.hasPending) return 'Pendente';
    return _statusLabels[period.status] ?? period.status;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          EpiAvatar(name: period.employeeName, size: 40),
          const SizedBox(width: EpiSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  period.employeeName,
                  style: Theme.of(context).textTheme.bodyLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: EpiSpacing.xs),
                Row(
                  children: [
                    if (period.employeeCode != null) ...[
                      Text(
                        period.employeeCode!,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: EpiColors.textMuted),
                      ),
                      const SizedBox(width: EpiSpacing.sm),
                      Container(
                        width: 3,
                        height: 3,
                        decoration: const BoxDecoration(
                          color: EpiColors.textMuted,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: EpiSpacing.sm),
                    ],
                    Flexible(
                      child: Text(
                        period.unitName,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: EpiColors.textMuted),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    const Icon(
                      Icons.calendar_today_outlined,
                      size: 12,
                      color: EpiColors.textMuted,
                    ),
                    const SizedBox(width: 3),
                    Text(
                      period.periodLabel,
                      style: Theme.of(context)
                          .textTheme
                          .labelSmall
                          ?.copyWith(color: EpiColors.textMuted),
                    ),
                    if (period.hasPending) ...[
                      const SizedBox(width: EpiSpacing.sm),
                      Text(
                        '${period.pendingItems} pendente${period.pendingItems == 1 ? "" : "s"}',
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(color: EpiColors.warning),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: EpiSpacing.sm),
          _StatusBadge(label: _label, color: _color),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.sm,
        vertical: 3,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(EpiRadius.full),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
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
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 48, color: EpiColors.textMuted),
          const SizedBox(height: EpiSpacing.lg),
          Text(l10n.errorNetwork, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(label: l10n.retry, onPressed: onRetry),
        ],
      ),
    );
  }
}
