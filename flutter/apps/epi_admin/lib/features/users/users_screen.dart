import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/users_cubit.dart';

class UsersScreen extends StatelessWidget {
  const UsersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => UsersCubit()..load(),
      child: const _UsersBody(),
    );
  }
}

class _UsersBody extends StatelessWidget {
  const _UsersBody();

  Future<void> _openCreate(BuildContext context) async {
    final cubit = context.read<UsersCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => const _UserFormDialog(),
    );
    if (saved == true && context.mounted) {
      cubit.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.navUsers),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<UsersCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _openCreate(context),
        child: const Icon(Icons.add),
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
              onChanged: context.read<UsersCubit>().search,
            ),
          ),
          Expanded(
            child: BlocBuilder<UsersCubit, UsersState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Padding(
                    padding: EdgeInsets.all(EpiSpacing.lg),
                    child: EpiSkeletonTable(rowCount: 8),
                  );
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<UsersCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(
                    title: l10n.noResults,
                    icon: Icons.people_outline_rounded,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<UsersCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm,
                      bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1, indent: 72),
                    itemBuilder: (_, i) => _UserTile(user: items[i]),
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

class _UserTile extends StatelessWidget {
  const _UserTile({required this.user});
  final Map<String, dynamic> user;

  Future<void> _openEdit(BuildContext context) async {
    final cubit = context.read<UsersCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => _UserFormDialog(user: user),
    );
    if (saved == true && context.mounted) {
      cubit.load();
    }
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final name = user['full_name'] as String? ?? user['username'] as String? ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.confirmDeleteTitle),
        content: Text('Excluir usuário "$name"?\n\n${l10n.confirmDeleteMessage}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: EpiColors.danger),
            child: Text(l10n.confirmDeleteButton),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<UsersCubit>().deleteUser(user['id'] as int);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final fullName = user['full_name'] as String? ?? '';
    final username = user['username'] as String? ?? '';
    final role = user['role'] as String? ?? '';
    final companyName = user['company_name'] as String? ?? '';

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: EpiAvatar(name: fullName.isNotEmpty ? fullName : username, size: 44),
      title: Text(
        fullName.isNotEmpty ? fullName : username,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (username.isNotEmpty)
            Text(
              username,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          if (companyName.isNotEmpty)
            Text(
              companyName,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
        ],
      ),
      isThreeLine: companyName.isNotEmpty && username.isNotEmpty,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (role.isNotEmpty)
            EpiBadge(status: EpiBadgeStatus.inReview, label: role),
          PopupMenuButton<String>(
            itemBuilder: (ctx) => [
              PopupMenuItem(value: 'edit', child: Text(l10n.edit)),
              PopupMenuItem(
                value: 'delete',
                child: Text(
                  l10n.delete,
                  style: const TextStyle(color: EpiColors.danger),
                ),
              ),
            ],
            onSelected: (action) {
              if (action == 'edit') {
                _openEdit(context);
              } else if (action == 'delete') {
                _confirmDelete(context);
              }
            },
          ),
        ],
      ),
    );
  }
}

// ── Create / Edit dialog ───────────────────────────────────────────────────

class _UserFormDialog extends StatefulWidget {
  const _UserFormDialog({this.user});
  final Map<String, dynamic>? user;

  @override
  State<_UserFormDialog> createState() => _UserFormDialogState();
}

class _UserFormDialogState extends State<_UserFormDialog> {
  final _usernameCtrl = TextEditingController();
  final _fullNameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _employeeIdCtrl = TextEditingController();

  String _role = 'general_admin';
  int? _companyId;
  List<Company> _companies = [];
  bool _loadingCompanies = true;
  bool _saving = false;
  String? _error;

  static const _roles = [
    'general_admin',
    'registry_admin',
    'admin',
    'user',
    'buyer',
    'approver',
    'employee',
  ];

  bool get _isEdit => widget.user != null;
  bool get _needsEmployee => _role == 'admin' || _role == 'user';

  @override
  void initState() {
    super.initState();
    if (_isEdit) {
      final u = widget.user!;
      _usernameCtrl.text = u['username'] as String? ?? '';
      _fullNameCtrl.text = u['full_name'] as String? ?? '';
      _role = u['role'] as String? ?? 'general_admin';
      _companyId = u['company_id'] as int?;
      if (u['linked_employee_id'] != null) {
        _employeeIdCtrl.text = u['linked_employee_id'].toString();
      }
    }
    _loadCompanies();
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _fullNameCtrl.dispose();
    _passwordCtrl.dispose();
    _employeeIdCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadCompanies() async {
    try {
      final companies = await ApiClient.companies.getCompanies();
      if (mounted) {
        setState(() {
          _companies = companies;
          _loadingCompanies = false;
          if (_companyId == null && companies.isNotEmpty) {
            _companyId = companies.first.id;
          }
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loadingCompanies = false);
    }
  }

  Future<void> _save() async {
    final username = _usernameCtrl.text.trim();
    final fullName = _fullNameCtrl.text.trim();
    if (username.isEmpty || fullName.isEmpty) {
      setState(() => _error = 'Preencha usuário e nome completo');
      return;
    }

    final body = <String, dynamic>{
      'username': username,
      'full_name': fullName,
      'role': _role,
      if (_companyId != null) 'company_id': _companyId,
    };

    if (!_isEdit && _passwordCtrl.text.isNotEmpty) {
      body['password'] = _passwordCtrl.text;
    }

    final empId = int.tryParse(_employeeIdCtrl.text.trim());
    if (empId != null) {
      body['linked_employee_id'] = empId;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final actorId = ApiClient.actorUserId;
      if (_isEdit) {
        await ApiClient.users.updateUser(
          widget.user!['id'] as int,
          {...body, 'actor_user_id': actorId},
        );
      } else {
        await ApiClient.users.createUser({...body, 'actor_user_id': actorId});
      }
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } on DioException catch (e) {
      final data = e.response?.data;
      final detail = data is Map ? data['detail']?.toString() : null;
      setState(() {
        _saving = false;
        _error = detail ?? 'Erro ao salvar';
      });
    } catch (e) {
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(_isEdit ? l10n.edit : 'Novo usuário'),
      content: SizedBox(
        width: 360,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpiInput(
                label: 'Nome de usuário',
                hint: 'Ex: joao.silva',
                controller: _usernameCtrl,
                enabled: !_saving,
              ),
              const SizedBox(height: EpiSpacing.md),
              EpiInput(
                label: 'Nome completo',
                hint: 'Ex: João Silva',
                controller: _fullNameCtrl,
                enabled: !_saving,
              ),
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<String>(
                value: _role,
                decoration: const InputDecoration(
                  labelText: 'Perfil',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: _roles
                    .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                    .toList(),
                onChanged: _saving
                    ? null
                    : (v) {
                        if (v != null) setState(() => _role = v);
                      },
              ),
              const SizedBox(height: EpiSpacing.md),
              if (_loadingCompanies)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(EpiSpacing.sm),
                    child: CircularProgressIndicator(),
                  ),
                )
              else
                DropdownButtonFormField<int>(
                  value: _companyId,
                  decoration: const InputDecoration(
                    labelText: 'Empresa',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: _companies
                      .map((c) => DropdownMenuItem(value: c.id, child: Text(c.name)))
                      .toList(),
                  onChanged: _saving ? null : (v) => setState(() => _companyId = v),
                ),
              if (_needsEmployee) ...[
                const SizedBox(height: EpiSpacing.md),
                EpiInput(
                  label: 'ID do Colaborador (obrigatório para perfis admin/user)',
                  hint: 'Ex: 42',
                  controller: _employeeIdCtrl,
                  keyboardType: TextInputType.number,
                  enabled: !_saving,
                ),
              ],
              if (!_isEdit) ...[
                const SizedBox(height: EpiSpacing.md),
                EpiInput(
                  label: 'Senha (opcional — gerada automaticamente se vazio)',
                  controller: _passwordCtrl,
                  obscureText: true,
                  enabled: !_saving,
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: EpiSpacing.md),
                Text(
                  _error!,
                  style: const TextStyle(color: EpiColors.danger, fontSize: 12),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        EpiButton(
          label: l10n.save,
          onPressed: _saving ? null : _save,
          loading: _saving,
        ),
      ],
    );
  }
}

// ── Retry view ─────────────────────────────────────────────────────────────

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
