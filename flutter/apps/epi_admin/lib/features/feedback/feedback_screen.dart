import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../../core/bloc/feedback_cubit.dart';

class FeedbackScreen extends StatelessWidget {
  const FeedbackScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => FeedbackCubit()..load(),
      child: const _FeedbackBody(),
    );
  }
}

class _FeedbackBody extends StatelessWidget {
  const _FeedbackBody();

  static const _filters = <(String?, String)>[
    (null, 'Todos'),
    ('open', 'Aberto'),
    ('in_review', 'Em análise'),
    ('resolved', 'Resolvido'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Avaliações de EPIs'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<FeedbackCubit>().load(),
          ),
        ],
      ),
      body: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _FilterBar(filters: _filters),
          Expanded(child: _FeedbackList()),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({required this.filters});

  final List<(String?, String)> filters;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<FeedbackCubit, FeedbackState>(
      buildWhen: (prev, curr) => prev.statusFilter != curr.statusFilter,
      builder: (ctx, state) {
        return SizedBox(
          height: 48,
          child: ListView(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.lg,
              vertical: EpiSpacing.sm,
            ),
            scrollDirection: Axis.horizontal,
            children: [
              for (final (value, label) in filters) ...[
                EpiChip(
                  label: label,
                  selected: state.statusFilter == value,
                  onTap: () =>
                      ctx.read<FeedbackCubit>().setFilter(value),
                ),
                const SizedBox(width: EpiSpacing.sm),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _FeedbackList extends StatelessWidget {
  const _FeedbackList();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<FeedbackCubit, FeedbackState>(
      builder: (ctx, state) {
        if (state.isLoading) {
          return ListView.separated(
            padding: const EdgeInsets.all(EpiSpacing.lg),
            itemCount: 6,
            separatorBuilder: (_, __) =>
                const SizedBox(height: EpiSpacing.md),
            itemBuilder: (_, __) => const EpiSkeletonCard(),
          );
        }

        if (state.error != null) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.wifi_off_rounded,
                  size: 48,
                  color: EpiColors.textMuted,
                ),
                const SizedBox(height: EpiSpacing.lg),
                Text(
                  'Erro ao carregar avaliações',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: EpiSpacing.xs),
                Text(
                  state.error!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: EpiColors.textMuted,
                      ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: EpiSpacing.xl),
                EpiButton(
                  label: 'Tentar novamente',
                  onPressed: () => ctx.read<FeedbackCubit>().load(),
                ),
              ],
            ),
          );
        }

        if (state.items.isEmpty) {
          return const EpiEmptyState(
            title: 'Nenhuma avaliação encontrada',
          );
        }

        return RefreshIndicator(
          onRefresh: () => ctx.read<FeedbackCubit>().load(),
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
            itemCount: state.items.length,
            separatorBuilder: (_, __) =>
                const Divider(height: 1, indent: 16),
            itemBuilder: (_, i) => _FeedbackCard(
              item: state.items[i],
            ),
          ),
        );
      },
    );
  }
}

class _FeedbackCard extends StatelessWidget {
  const _FeedbackCard({required this.item});

  final FeedbackItem item;

  EpiBadgeStatus _badgeStatus(String status) => switch (status) {
        'open' => EpiBadgeStatus.pending,
        'in_review' => EpiBadgeStatus.inReview,
        'resolved' => EpiBadgeStatus.approved,
        'closed' => EpiBadgeStatus.inactive,
        'rejected' => EpiBadgeStatus.rejected,
        _ => EpiBadgeStatus.pending,
      };

  String _statusLabel(String status) => switch (status) {
        'open' => 'Aberto',
        'in_review' => 'Em análise',
        'resolved' => 'Resolvido',
        'closed' => 'Fechado',
        'rejected' => 'Rejeitado',
        _ => status,
      };

  String _formatDate(String raw) {
    if (raw.isEmpty) return '';
    try {
      final dt = DateTime.parse(raw);
      return '${dt.day.toString().padLeft(2, '0')}/'
          '${dt.month.toString().padLeft(2, '0')}/'
          '${dt.year}';
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final cubit = context.read<FeedbackCubit>();
    final canValidate =
        item.status == 'in_review' || item.status == 'open';
    final canClose = item.status != 'closed' && item.status != 'rejected';

    final subtitleParts = <String>[
      if (item.employeeName != null) item.employeeName!,
      if (item.unitName != null) item.unitName!,
      if (item.createdAt.isNotEmpty) _formatDate(item.createdAt),
    ];

    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    item.epiName,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
                const SizedBox(width: EpiSpacing.sm),
                EpiBadge(
                  status: _badgeStatus(item.status),
                  label: _statusLabel(item.status),
                ),
              ],
            ),
            if (subtitleParts.isNotEmpty) ...[
              const SizedBox(height: EpiSpacing.xs),
              Text(
                subtitleParts.join(' • '),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: EpiColors.textMuted,
                    ),
              ),
            ],
            if (item.description != null &&
                item.description!.isNotEmpty) ...[
              const SizedBox(height: EpiSpacing.sm),
              Text(
                item.description!,
                style: Theme.of(context).textTheme.bodySmall,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            if (canValidate || canClose) ...[
              const SizedBox(height: EpiSpacing.md),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (canValidate)
                    TextButton.icon(
                      icon: const Icon(Icons.check_circle_outline, size: 16),
                      label: const Text('Validar'),
                      onPressed: () => cubit.validate(item.id),
                    ),
                  if (canValidate && canClose)
                    const SizedBox(width: EpiSpacing.sm),
                  if (canClose)
                    TextButton.icon(
                      icon: const Icon(Icons.lock_outline, size: 16),
                      label: const Text('Fechar'),
                      style: TextButton.styleFrom(
                        foregroundColor: EpiColors.textMuted,
                      ),
                      onPressed: () => cubit.closeFeedback(item.id),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
