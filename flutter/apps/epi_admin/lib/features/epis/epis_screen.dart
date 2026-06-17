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

  Future<void> _confirmDelete(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EpisCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: Text(l10n.confirmDeleteTitle),
        content: Text('${epi.name}\n${l10n.confirmDeleteMessage}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await cubit.deleteEpi(epi.id);
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
              if (value == 'delete') _confirmDelete(context);
            },
            itemBuilder: (_) => [
              PopupMenuItem<String>(
                value: 'delete',
                child: Text(l10n.delete),
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
