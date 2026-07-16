import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
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

  Future<void> _openCreate(BuildContext context) async {
    final cubit = context.read<UnitsCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => const _UnitFormDialog(),
    );
    if (saved == true && context.mounted) {
      cubit.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<UnitsCubit, UnitsState>(
      builder: (ctx, state) {
        return Scaffold(
          appBar: AppBar(
            title: Text(
              state.showArchived
                  ? '${l10n.navUnits} · Arquivadas'
                  : l10n.navUnits,
            ),
            actions: [
              IconButton(
                tooltip: state.showArchived
                    ? 'Ver unidades ativas'
                    : 'Ver unidades arquivadas',
                icon: Icon(
                  state.showArchived
                      ? Icons.location_on_outlined
                      : Icons.inventory_2_outlined,
                ),
                onPressed: () =>
                    context.read<UnitsCubit>().toggleArchivedView(),
              ),
              IconButton(
                icon: const Icon(Icons.refresh_rounded),
                onPressed: () => context.read<UnitsCubit>().load(),
              ),
            ],
          ),
          floatingActionButton: state.showArchived
              ? null
              : FloatingActionButton(
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
                  onChanged: context.read<UnitsCubit>().search,
                ),
              ),
              Expanded(
                child: Builder(
                  builder: (_) {
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
                    final items = state.showArchived
                        ? state.filteredArchived
                        : state.filtered;
                    if (items.isEmpty) {
                      return EpiEmptyState(
                        title: state.showArchived
                            ? 'Nenhuma unidade arquivada.'
                            : l10n.noResults,
                        icon: state.showArchived
                            ? Icons.inventory_2_outlined
                            : Icons.location_on_outlined,
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
                        itemBuilder: (_, i) => state.showArchived
                            ? _ArchivedUnitTile(unit: items[i])
                            : _UnitTile(unit: items[i]),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _UnitTile extends StatelessWidget {
  const _UnitTile({required this.unit});
  final Map<String, dynamic> unit;

  Future<void> _openEdit(BuildContext context) async {
    final cubit = context.read<UnitsCubit>();
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => _UnitFormDialog(unit: unit),
    );
    if (saved == true && context.mounted) {
      cubit.load();
    }
  }

  Future<void> _confirmArchive(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final name = unit['name'] as String? ?? '';
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Arquivar Unidade'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'A unidade "$name" será arquivada e deixará de receber novas '
              'operações.\n\nTodo o histórico permanecerá preservado pelo '
              'período mínimo de retenção configurado (mínimo de 5 anos) '
              'para consultas, relatórios e auditorias.',
            ),
            const SizedBox(height: EpiSpacing.md),
            EpiInput(
              label: 'Motivo do arquivamento (auditoria)',
              controller: reasonCtrl,
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: EpiColors.danger),
            child: const Text('Arquivar'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context
          .read<UnitsCubit>()
          .archiveUnit(unit['id'] as int, reason: reasonCtrl.text.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
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
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (type.isNotEmpty)
            EpiBadge(status: EpiBadgeStatus.inReview, label: type),
          PopupMenuButton<String>(
            itemBuilder: (ctx) => [
              PopupMenuItem(value: 'edit', child: Text(l10n.edit)),
              const PopupMenuItem(
                value: 'archive',
                child: Text(
                  'Arquivar',
                  style: TextStyle(color: EpiColors.danger),
                ),
              ),
            ],
            onSelected: (action) {
              if (action == 'edit') {
                _openEdit(context);
              } else if (action == 'archive') {
                _confirmArchive(context);
              }
            },
          ),
        ],
      ),
    );
  }
}

// ── Archived unit tile (Desarquivar) ────────────────────────────────────────

class _ArchivedUnitTile extends StatelessWidget {
  const _ArchivedUnitTile({required this.unit});
  final Map<String, dynamic> unit;

  Future<void> _confirmRestore(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final name = unit['name'] as String? ?? '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Desarquivar Unidade'),
        content: Text(
          'A unidade "$name" será desarquivada e voltará a ficar ativa, '
          'podendo receber novas operações.\n\nTodo o histórico preservado '
          'permanece intacto.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Desarquivar'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      context.read<UnitsCubit>().restoreUnit(unit['id'] as int);
    }
  }

  String _subtitle() {
    final parts = <String>[];
    final companyName = unit['company_name'] as String? ?? '';
    if (companyName.isNotEmpty) parts.add(companyName);
    final archivedAt = (unit['archived_at'] as String? ?? '').split('T').first;
    if (archivedAt.isNotEmpty) parts.add('Arquivada em $archivedAt');
    final reason = unit['archive_reason'] as String? ?? '';
    if (reason.isNotEmpty) parts.add(reason);
    final remaining = unit['retention_days_remaining'];
    if (remaining is num) {
      parts.add(remaining > 0
          ? 'Retenção restante: ${remaining.toInt()} dia(s)'
          : 'Retenção cumprida');
    }
    return parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final name = unit['name'] as String? ?? '';
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
          Icons.inventory_2_outlined,
          color: EpiColors.textMuted,
          size: 22,
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

// ── Create / Edit dialog ───────────────────────────────────────────────────

class _UnitFormDialog extends StatefulWidget {
  const _UnitFormDialog({this.unit});
  final Map<String, dynamic>? unit;

  @override
  State<_UnitFormDialog> createState() => _UnitFormDialogState();
}

class _UnitFormDialogState extends State<_UnitFormDialog> {
  final _nameCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  String _unitType = 'base';
  int? _companyId;
  List<Company> _companies = [];
  bool _loadingCompanies = true;
  bool _saving = false;
  String? _error;

  static const _unitTypes = ['base', 'embarcacao', 'plataforma'];

  bool get _isEdit => widget.unit != null;

  @override
  void initState() {
    super.initState();
    if (_isEdit) {
      final u = widget.unit!;
      _nameCtrl.text = u['name'] as String? ?? '';
      _cityCtrl.text = u['city'] as String? ?? '';
      _notesCtrl.text = u['notes'] as String? ?? '';
      _unitType = u['type'] as String? ?? 'base';
      _companyId = u['company_id'] as int?;
    }
    _loadCompanies();
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _cityCtrl.dispose();
    _notesCtrl.dispose();
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
    final name = _nameCtrl.text.trim();
    final city = _cityCtrl.text.trim();
    if (name.isEmpty || city.isEmpty || _companyId == null) {
      setState(() => _error = 'Preencha nome, cidade e empresa');
      return;
    }

    final body = <String, dynamic>{
      'company_id': _companyId,
      'name': name,
      'unit_type': _unitType,
      'city': city,
      if (_notesCtrl.text.trim().isNotEmpty) 'notes': _notesCtrl.text.trim(),
    };

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final actorId = ApiClient.actorUserId;
      if (_isEdit) {
        await ApiClient.units.updateUnit(
          widget.unit!['id'] as int,
          {...body, 'actor_user_id': actorId},
        );
      } else {
        await ApiClient.units.createUnit({...body, 'actor_user_id': actorId});
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
      title: Text(_isEdit ? l10n.edit : 'Nova unidade'),
      content: SizedBox(
        width: 360,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpiInput(
                label: 'Nome',
                hint: 'Ex: Plataforma P-40',
                controller: _nameCtrl,
                enabled: !_saving,
              ),
              const SizedBox(height: EpiSpacing.md),
              EpiInput(
                label: 'Cidade',
                hint: 'Ex: Macaé',
                controller: _cityCtrl,
                enabled: !_saving,
              ),
              const SizedBox(height: EpiSpacing.md),
              DropdownButtonFormField<String>(
                value: _unitType,
                decoration: const InputDecoration(
                  labelText: 'Tipo',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: _unitTypes
                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                    .toList(),
                onChanged: _saving
                    ? null
                    : (v) {
                        if (v != null) setState(() => _unitType = v);
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
              const SizedBox(height: EpiSpacing.md),
              EpiInput(
                label: 'Observações (opcional)',
                controller: _notesCtrl,
                maxLines: 2,
                enabled: !_saving,
              ),
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
