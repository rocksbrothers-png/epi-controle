import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/feedback_cubit.dart';
import 'feedback_presentation.dart';

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

  static const _filters = <String?>[null, 'open', 'in_review', 'resolved'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context).feedbackTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: AppLocalizations.of(context).refresh,
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

  final List<String?> filters;

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
              for (final value in filters) ...[
                EpiChip(
                  label: value == null
                      ? AppLocalizations.of(ctx).filterAll
                      : feedbackStatusLabel(value, AppLocalizations.of(ctx)),
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
                  AppLocalizations.of(ctx).feedbackLoadFailed,
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
                  label: AppLocalizations.of(ctx).retry,
                  onPressed: () => ctx.read<FeedbackCubit>().load(),
                ),
              ],
            ),
          );
        }

        if (state.items.isEmpty) {
          return EpiEmptyState(
            title: AppLocalizations.of(ctx).feedbackEmpty,
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

  Future<void> _reject(BuildContext context, FeedbackCubit cubit) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => const _FeedbackReasonDialog(rejection: true),
    );
    if (reason != null && reason.isNotEmpty) {
      await cubit.reject(item.id, reason);
    }
  }

  /// Decisão administrativa (exige justificativa). `decision` é o valor do
  /// backend (ex.: aprovar_sugestao / reprovar_sugestao / encerrar).
  Future<void> _decide(BuildContext context, FeedbackCubit cubit, String decision) async {
    final justification = await showDialog<String>(
      context: context,
      builder: (_) => const _FeedbackReasonDialog(rejection: false),
    );
    if (justification != null && justification.isNotEmpty) {
      await cubit.adminDecision(item.id, decision, justification);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<FeedbackCubit>();
    // Ações do gestor disponíveis na fase de análise (status reais do backend).
    final canValidate =
        item.status == 'recebido' || item.status == 'em_analise_gestor';
    final canAdmin = item.status == 'aguardando_aprovacao_admin';
    const terminal = {'encerrado', 'aprovado', 'reprovado', 'closed', 'rejected'};
    final canClose = !terminal.contains(item.status);

    final subtitleParts = <String>[
      if (item.employeeName != null) item.employeeName!,
      if (item.unitName != null) item.unitName!,
      if (item.createdAt.isNotEmpty)
        formatFeedbackDate(item.createdAt, l10n.localeName),
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
                Flexible(
                  child: EpiBadge(
                    status: _badgeStatus(item.status),
                    label: feedbackStatusLabel(item.status, l10n),
                  ),
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
            if (canValidate || canAdmin || canClose) ...[
              const SizedBox(height: EpiSpacing.md),
              Wrap(
                alignment: WrapAlignment.end,
                spacing: EpiSpacing.sm,
                children: [
                  if (canValidate)
                    TextButton.icon(
                      icon: const Icon(Icons.check_circle_outline, size: 16),
                      label: Text(l10n.feedbackValidate),
                      onPressed: () => cubit.validate(item.id),
                    ),
                  if (canAdmin && item.type == 'sugestao')
                    TextButton.icon(
                      icon: const Icon(Icons.thumb_up_outlined, size: 16),
                      label: Text(l10n.feedbackApprove),
                      onPressed: () => _decide(context, cubit, 'aprovar_sugestao'),
                    ),
                  if (canAdmin && item.type == 'sugestao')
                    TextButton.icon(
                      icon: const Icon(Icons.thumb_down_outlined, size: 16),
                      label: Text(l10n.feedbackReject),
                      style: TextButton.styleFrom(
                        foregroundColor: EpiColors.danger,
                      ),
                      onPressed: () => _decide(context, cubit, 'reprovar_sugestao'),
                    ),
                  if (canAdmin && item.type != 'sugestao')
                    TextButton.icon(
                      icon: const Icon(Icons.task_alt_outlined, size: 16),
                      label: Text(l10n.close),
                      onPressed: () => _decide(context, cubit, 'encerrar'),
                    ),
                  if (canValidate)
                    TextButton.icon(
                      icon: const Icon(Icons.forward_outlined, size: 16),
                      label: Text(l10n.feedbackForward),
                      onPressed: () => cubit.forwardToAdmin(item.id),
                    ),
                  if (canValidate)
                    TextButton.icon(
                      icon: const Icon(Icons.cancel_outlined, size: 16),
                      label: Text(l10n.feedbackReject),
                      style: TextButton.styleFrom(
                        foregroundColor: EpiColors.danger,
                      ),
                      onPressed: () => _reject(context, cubit),
                    ),
                  if (canClose)
                    TextButton.icon(
                      icon: const Icon(Icons.lock_outline, size: 16),
                      label: Text(AppLocalizations.of(context).close),
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
/// Own the controller until the closing route has actually removed its fields.
class _FeedbackReasonDialog extends StatefulWidget {
  const _FeedbackReasonDialog({required this.rejection});

  final bool rejection;

  @override
  State<_FeedbackReasonDialog> createState() => _FeedbackReasonDialogState();
}

class _FeedbackReasonDialogState extends State<_FeedbackReasonDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(widget.rejection ? l.feedbackReject : l.confirm),
      content: TextField(
        controller: _controller,
        autofocus: true,
        decoration: InputDecoration(
          labelText: widget.rejection
              ? l.feedbackRejectReason
              : l.feedbackJustification,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.cancel),
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(_controller.text.trim()),
          child: Text(l.confirm),
        ),
      ],
    );
  }
}
