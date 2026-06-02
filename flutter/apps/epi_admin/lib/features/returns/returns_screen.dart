import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/bloc/devolutions_cubit.dart';
import '../../core/api/api_client.dart';
import 'new_return_screen.dart';

class ReturnsScreen extends StatelessWidget {
  const ReturnsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => DevolutionsCubit()..load(),
      child: const _ReturnsBody(),
    );
  }
}

class _ReturnsBody extends StatelessWidget {
  const _ReturnsBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.returnsTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<DevolutionsCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openNew(context),
        icon: const Icon(Icons.assignment_return_outlined),
        label: Text(l10n.returnNew),
      ),
      body: BlocBuilder<DevolutionsCubit, DevolutionsState>(
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
                    onPressed: () => ctx.read<DevolutionsCubit>().load(),
                  ),
                ],
              ),
            );
          }
          final items = state.devolutions;
          if (items.isEmpty) {
            return EpiEmptyState(
              title: l10n.noResults,
              icon: Icons.assignment_return_outlined,
            );
          }
          return RefreshIndicator(
            onRefresh: () => ctx.read<DevolutionsCubit>().load(),
            child: ListView.separated(
              padding: const EdgeInsets.only(
                top: EpiSpacing.sm,
                bottom: EpiSpacing.xl5,
              ),
              itemCount: items.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 1, indent: 16),
              itemBuilder: (_, i) => _DevolutionTile(devolution: items[i]),
            ),
          );
        },
      ),
    );
  }

  Future<void> _openNew(BuildContext context) async {
    final cubit = context.read<DevolutionsCubit>();
    final bootstrap = await _bootstrapData();
    if (!context.mounted) return;
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => BlocProvider.value(
          value: cubit,
          child: NewReturnScreen(
            employees: bootstrap.$1,
            epis: bootstrap.$2,
          ),
        ),
      ),
    );
    if (created == true) cubit.load();
  }

  Future<(List<Employee>, List<Epi>)> _bootstrapData() async {
    try {
      final b = await ApiClient.auth.bootstrap();
      return (
        b.employees.map(Employee.fromJson).toList(),
        b.epis.map(Epi.fromJson).toList(),
      );
    } on Exception {
      return (<Employee>[], <Epi>[]);
    }
  }
}

class _DevolutionTile extends StatelessWidget {
  const _DevolutionTile({required this.devolution});
  final Devolution devolution;

  static const _conditionLabels = <String, String>{
    'good': 'Bom estado',
    'damaged': 'Danificado',
    'lost': 'Extraviado',
  };

  static const _conditionColors = <String, Color>{
    'good': EpiColors.success,
    'damaged': EpiColors.warning,
    'lost': EpiColors.danger,
  };

  @override
  Widget build(BuildContext context) {
    final conditionLabel =
        _conditionLabels[devolution.condition] ?? devolution.condition;
    final conditionColor =
        _conditionColors[devolution.condition] ?? EpiColors.textMuted;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: EpiColors.border,
            child: const Icon(
              Icons.assignment_return_outlined,
              color: EpiColors.textMuted,
            ),
          ),
          const SizedBox(width: EpiSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  devolution.epiName,
                  style: Theme.of(context).textTheme.bodyLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  devolution.employeeName,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: EpiColors.textMuted),
                ),
                Text(
                  devolution.returnedDate,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: EpiColors.textMuted),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: conditionColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(EpiRadius.full),
              border: Border.all(color: conditionColor.withOpacity(0.4)),
            ),
            child: Text(
              conditionLabel,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: conditionColor,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
