import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:epi_api/epi_api.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/employees_cubit.dart';
import '../../core/router/routes.dart';
import 'employee_form_screen.dart';

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
    final authState = context.watch<AuthCubit>().state;
    // Administrador Local (admin) vê a lista mas não cadastra colaborador —
    // atribuição do Administrador de Registro/Geral (docs/PAPEIS_E_ATRIBUICOES.md
    // #3 vs #4). O backend já bloqueia sem employees:create; isto só evita
    // mostrar uma ação que falharia ao confirmar.
    final canCreate = authState is AuthAuthenticated &&
        authState.permissions.contains('employees:create');
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.employeesTitle),
        actions: [
          BlocBuilder<EmployeesCubit, EmployeesState>(
            buildWhen: (prev, curr) => prev.showArchived != curr.showArchived,
            builder: (ctx, state) => IconButton(
              tooltip: state.showArchived
                  ? 'Ver colaboradores ativos'
                  : 'Ver colaboradores arquivados',
              icon: Icon(
                state.showArchived
                    ? Icons.people_outline
                    : Icons.archive_outlined,
              ),
              onPressed: () =>
                  context.read<EmployeesCubit>().toggleArchivedView(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<EmployeesCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: canCreate
          ? FloatingActionButton(
              tooltip: l10n.employeesNew,
              onPressed: () {
                final cubit = context.read<EmployeesCubit>();
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => EmployeeFormScreen(cubit: cubit),
                  ),
                );
              },
              child: const Icon(Icons.add_rounded),
            )
          : null,
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
                if (state.showArchived) {
                  final archived = state.filteredArchived;
                  if (archived.isEmpty) {
                    return const EpiEmptyState(
                      title: 'Nenhum colaborador arquivado.',
                    );
                  }
                  return RefreshIndicator(
                    onRefresh: () => context.read<EmployeesCubit>().load(),
                    child: ListView.separated(
                      padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
                      itemCount: archived.length,
                      separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
                      itemBuilder: (_, i) =>
                          _ArchivedEmployeeTile(employee: archived[i]),
                    ),
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

  Future<void> _confirmArchive(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EmployeesCubit>();
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Arquivar Colaborador'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'O colaborador "${employee.name}" será arquivado e deixará de '
              'receber novas operações (entregas, requisições e movimentações).\n\n'
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
      await cubit.archiveEmployee(employee.id, reason: reasonCtrl.text.trim());
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
              if (value == 'archive') {
                _confirmArchive(context);
              } else if (value == 'edit') {
                final cubit = context.read<EmployeesCubit>();
                Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        EmployeeFormScreen(cubit: cubit, employeeId: employee.id),
                  ),
                );
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem<String>(
                value: 'edit',
                child: Text(AppLocalizations.of(context).edit),
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
        final path = Routes.employeeDetail.replaceFirst(':id', '${employee.id}');
        context.push(path, extra: employee);
      },
    );
  }
}

class _ArchivedEmployeeTile extends StatelessWidget {
  const _ArchivedEmployeeTile({required this.employee});
  final Map<String, dynamic> employee;

  Future<void> _confirmRestore(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<EmployeesCubit>();
    final name = employee['name'] as String? ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Desarquivar Colaborador'),
        content: Text(
          'O colaborador "$name" será desarquivado e voltará a ficar ativo, '
          'podendo receber novas operações.\n\nTodo o histórico preservado '
          'permanece intacto.',
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
      await cubit.restoreEmployee(employee['id'] as int);
    }
  }

  String _subtitle() {
    final parts = <String>[];
    final code = employee['employee_id_code'] as String? ?? '';
    if (code.isNotEmpty) parts.add(code);
    final unitName = employee['unit_name'] as String? ?? '';
    if (unitName.isNotEmpty) parts.add(unitName);
    final archivedAt =
        (employee['archived_at'] as String? ?? '').split('T').first;
    if (archivedAt.isNotEmpty) parts.add('Arquivado em $archivedAt');
    final reason = employee['archive_reason'] as String? ?? '';
    if (reason.isNotEmpty) parts.add(reason);
    final remaining = employee['retention_days_remaining'];
    if (remaining is num) {
      parts.add(remaining > 0
          ? 'Retenção restante: ${remaining.toInt()} dia(s)'
          : 'Retenção cumprida');
    }
    return parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final name = employee['name'] as String? ?? '';
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: EpiAvatar(name: name, size: 44),
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
