import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/bloc/units_cubit.dart';

class UnitsScreen extends StatelessWidget {
  const UnitsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => UnitsCubit()..load(),
      child: const _UnitsBody(),
    );
  }
}

class _UnitsBody extends StatelessWidget {
  const _UnitsBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.navUnits),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<UnitsCubit>().load(),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              EpiSpacing.lg,
              EpiSpacing.sm,
              EpiSpacing.lg,
              EpiSpacing.xs,
            ),
            child: EpiSearchBar(
              hint: l10n.search,
              onChanged: context.read<UnitsCubit>().search,
            ),
          ),
          Expanded(
            child: BlocBuilder<UnitsCubit, UnitsState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Padding(
                    padding: EdgeInsets.all(EpiSpacing.lg),
                    child: EpiSkeletonTable(rowCount: 8),
                  );
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<UnitsCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(
                    title: l10n.noResults,
                    icon: Icons.location_on_outlined,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<UnitsCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm,
                      bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1, indent: 72),
                    itemBuilder: (_, i) => _UnitTile(unit: items[i]),
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

class _UnitTile extends StatelessWidget {
  const _UnitTile({required this.unit});
  final Map<String, dynamic> unit;

  @override
  Widget build(BuildContext context) {
    final name = unit['name'] as String? ?? '';
    final companyName = unit['company_name'] as String? ?? '';
    final type = unit['type'] as String? ?? '';

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
          borderRadius: BorderRadius.circular(EpiRadius.md),
        ),
        alignment: Alignment.center,
        child: const Icon(
          Icons.location_on_outlined,
          color: EpiColors.brand,
          size: 22,
        ),
      ),
      title: Text(
        name,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: companyName.isNotEmpty
          ? Text(
              companyName,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            )
          : null,
      trailing: type.isNotEmpty
          ? EpiBadge(status: EpiBadgeStatus.inReview, label: type)
          : null,
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
