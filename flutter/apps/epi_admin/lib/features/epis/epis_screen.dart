import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:epi_api/epi_api.dart';
import '../../core/bloc/epis_cubit.dart';
import '../../core/router/routes.dart';
import '../../core/utils/epi_status_utils.dart';
import 'epi_form_screen.dart';

class EpisScreen extends StatelessWidget {
  const EpisScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => EpisCubit()..load(),
      child: const _EpisBody(),
    );
  }
}

class _EpisBody extends StatefulWidget {
  const _EpisBody();

  @override
  State<_EpisBody> createState() => _EpisBodyState();
}

class _EpisBodyState extends State<_EpisBody> {
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
      floatingActionButton: FloatingActionButton(
        tooltip: l10n.episNew,
        onPressed: () {
          final cubit = context.read<EpisCubit>();
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => EpiFormScreen(cubit: cubit),
            ),
          );
        },
        child: const Icon(Icons.add_rounded),
      ),
      appBar: AppBar(
        title: Text(l10n.episTitle),
        actions: [
          BlocBuilder<EpisCubit, EpisState>(
            buildWhen: (prev, curr) => prev.filterCritical != curr.filterCritical,
            builder: (ctx, state) => IconButton(
              icon: Icon(
                Icons.inventory_2_outlined,
                color: state.filterCritical ? EpiColors.danger : null,
              ),
              tooltip: l10n.stockMinimumAlert,
              onPressed: () => context.read<EpisCubit>().toggleCriticalFilter(),
            ),
          ),
          BlocBuilder<EpisCubit, EpisState>(
            buildWhen: (prev, curr) => prev.showArchived != curr.showArchived,
            builder: (ctx, state) => IconButton(
              tooltip: state.showArchived ? 'Ver EPIs ativos' : 'Ver EPIs arquivados',
              icon: Icon(
                state.showArchived
                    ? Icons.shield_outlined
                    : Icons.archive_outlined,
              ),
              onPressed: () => context.read<EpisCubit>().toggleArchivedView(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<EpisCubit>().load(),
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
                            context.read<EpisCubit>().search('');
                          },
                        ),
                ),
              ),
              onChanged: (q) => context.read<EpisCubit>().search(q),
            ),
          ),
          Expanded(
            child: BlocBuilder<EpisCubit, EpisState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<EpisCubit>().load(),
                  );
                }
                if (state.showArchived) {
                  final archived = state.filteredArchived;
                  if (archived.isEmpty) {
                    return const EpiEmptyState(title: 'Nenhum EPI arquivado.');
                  }
                  return RefreshIndicator(
                    onRefresh: () => context.read<EpisCubit>().load(),
                    child: ListView.separated(
                      padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
                      itemCount: archived.length,
                      separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
                      itemBuilder: (_, i) => _ArchivedEpiTile(epi: archived[i]),
                    ),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(title: l10n.noResults);
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<EpisCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
                    itemCount: items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
                    itemBuilder: (_, i) => _EpiTile(epi: items[i]),
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

class _EpiTile extends StatelessWidget {
  const _EpiTile({required this.epi});
  final Epi epi;

  Future<void> _confirmArchive(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EpisCubit>();
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Arquivar EPI'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'O EPI "${epi.name}" será arquivado e deixará de receber novas '
              'operações (entregas, estoque, requisições e compras).\n\n'
              'Todo o histórico permanecerá preservado pelo período mínimo de '
              'retenção configurado (mínimo de 5 anos).',
            ),
            const SizedBox(height: EpiSpacing.md),
            TextField(
              controller: reasonCtrl,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Motivo do arquivamento (auditoria)',
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            style: TextButton.styleFrom(foregroundColor: EpiColors.danger),
            child: const Text('Arquivar'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.archiveEpi(epi.id, reason: reasonCtrl.text.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final badgeStatus = epiBadgeStatus(epi);
    final stockLabel = '${l10n.epiStockLabel}: ${epi.stockQuantity}';
    final caLabel = epi.caNumber != null ? 'CA ${epi.caNumber}' : null;
    final subtitle = [caLabel, stockLabel].whereType<String>().join(' • ');
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
        child: const Icon(Icons.shield_outlined, color: EpiColors.brand, size: 24),
      ),
      title: Text(epi.name),
      subtitle: Text(subtitle),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          EpiBadge(status: badgeStatus),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'archive') {
                _confirmArchive(context);
              } else if (value == 'edit') {
                final cubit = context.read<EpisCubit>();
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => EpiFormScreen(cubit: cubit, epiId: epi.id),
                  ),
                );
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem<String>(
                value: 'edit',
                child: Text(l10n.edit),
              ),
              const PopupMenuItem<String>(
                value: 'archive',
                child: Text(
                  'Arquivar',
                  style: TextStyle(color: EpiColors.danger),
                ),
              ),
            ],
          ),
        ],
      ),
      onTap: () {
        final path = Routes.epiDetail.replaceFirst(':id', '${epi.id}');
        context.push(path, extra: epi);
      },
    );
  }
}

class _ArchivedEpiTile extends StatelessWidget {
  const _ArchivedEpiTile({required this.epi});
  final Map<String, dynamic> epi;

  Future<void> _confirmRestore(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EpisCubit>();
    final name = epi['name'] as String? ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Desarquivar EPI'),
        content: Text(
          'O EPI "$name" será desarquivado e voltará a ficar ativo, podendo '
          'receber novas operações.\n\nTodo o histórico preservado permanece '
          'intacto.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            child: const Text('Desarquivar'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.restoreEpi(epi['id'] as int);
    }
  }

  String _subtitle() {
    final parts = <String>[];
    final ca = epi['ca'] as String? ?? '';
    if (ca.isNotEmpty) parts.add('CA $ca');
    final archivedAt = (epi['archived_at'] as String? ?? '').split('T').first;
    if (archivedAt.isNotEmpty) parts.add('Arquivado em $archivedAt');
    final reason = epi['archive_reason'] as String? ?? '';
    if (reason.isNotEmpty) parts.add(reason);
    final remaining = epi['retention_days_remaining'];
    if (remaining is num) {
      parts.add(remaining > 0
          ? 'Retenção restante: ${remaining.toInt()} dia(s)'
          : 'Retenção cumprida');
    }
    return parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final name = epi['name'] as String? ?? '';
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
        child: const Icon(
          Icons.archive_outlined,
          color: EpiColors.textMuted,
          size: 24,
        ),
      ),
      title: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        _subtitle(),
        style: Theme.of(context)
            .textTheme
            .bodySmall
            ?.copyWith(color: EpiColors.textMuted),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: TextButton.icon(
        onPressed: () => _confirmRestore(context),
        icon: const Icon(Icons.unarchive_outlined, size: 18),
        label: const Text('Desarquivar'),
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
          EpiButton(label: AppLocalizations.of(context).retry, onPressed: onRetry),
        ],
      ),
    );
  }
}
