import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:epi_api/epi_api.dart';
import '../../core/bloc/employees_cubit.dart';
import '../../core/router/routes.dart';

class EmployeesScreen extends StatelessWidget {
  const EmployeesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => EmployeesCubit()..load(),
      child: const _EmployeesBody(),
    );
  }
}

class _EmployeesBody extends StatefulWidget {
  const _EmployeesBody();

  @override
  State<_EmployeesBody> createState() => _EmployeesBodyState();
}

class _EmployeesBodyState extends State<_EmployeesBody> {
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
        title: Text(l10n.employeesTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<EmployeesCubit>().load(),
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
                hintText: l10n.employeesSearchHint,
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
                            context.read<EmployeesCubit>().search('');
                          },
                        ),
                ),
              ),
              onChanged: (q) => context.read<EmployeesCubit>().search(q),
            ),
          ),
          Expanded(
            child: BlocBuilder<EmployeesCubit, EmployeesState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<EmployeesCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(title: l10n.noResults);
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<EmployeesCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
                    itemCount: items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
                    itemBuilder: (_, i) => _EmployeeTile(employee: items[i]),
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

class _EmployeeTile extends StatelessWidget {
  const _EmployeeTile({required this.employee});
  final Employee employee;

  Future<void> _confirmDelete(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EmployeesCubit>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: Text(l10n.confirmDeleteTitle),
        content: Text(l10n.employeeDeleteConfirm(employee.name)),
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
      await cubit.deleteEmployee(employee.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final subtitle = [employee.code, employee.sector]
        .whereType<String>()
        .join(' • ');
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: EpiAvatar(name: employee.name, size: 44),
      title: Text(employee.name),
      subtitle: subtitle.isNotEmpty ? Text(subtitle) : null,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          EpiBadge(
            status: employee.isActive
                ? EpiBadgeStatus.active
                : EpiBadgeStatus.inactive,
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'delete') _confirmDelete(context);
            },
            itemBuilder: (_) => [
              PopupMenuItem<String>(
                value: 'delete',
                child: Text(AppLocalizations.of(context).delete),
              ),
            ],
          ),
        ],
      ),
      onTap: () {
        final path = Routes.employeeDetail.replaceFirst(':id', '${employee.id}');
        context.push(path, extra: employee);
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
