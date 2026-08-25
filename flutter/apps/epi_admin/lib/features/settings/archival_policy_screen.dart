import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import 'widgets/settings_page.dart';

/// Configurações → Arquivamento e retenção.
///
/// Retenção configurável por tenant (anos) para Unidades, EPIs e Colaboradores,
/// conforme a política interna da empresa (mínimo legal: 5 anos). A retenção
/// da Ficha de EPI (5 anos, NR-6) tem regra própria e não é alterada aqui.
class ArchivalPolicyScreen extends StatelessWidget {
  const ArchivalPolicyScreen({super.key, this.companyId});

  /// Empresa em edição, vinda de `?company_id=` (só o `master_admin`).
  final int? companyId;

  @override
  Widget build(BuildContext context) {
    return SettingsSubPage(
      title: AppLocalizations.of(context).settingsArchivalTitle,
      child: settingsCompanyMissing(context, companyId)
          ? const SettingsCompanyRequired()
          : _ArchivalPolicyForm(companyId: companyId),
    );
  }
}

class _ArchivalPolicyForm extends StatefulWidget {
  const _ArchivalPolicyForm({this.companyId});
  final int? companyId;

  @override
  State<_ArchivalPolicyForm> createState() => _ArchivalPolicyFormState();
}

class _ArchivalPolicyFormState extends State<_ArchivalPolicyForm> {
  final _unitsCtrl = TextEditingController(text: '5');
  final _episCtrl = TextEditingController(text: '5');
  final _employeesCtrl = TextEditingController(text: '5');
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_ArchivalPolicyForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.companyId != widget.companyId) _load();
  }

  @override
  void dispose() {
    _unitsCtrl.dispose();
    _episCtrl.dispose();
    _employeesCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final policy = await ApiClient.settings
          .getArchivalPolicy(companyId: widget.companyId);
      if (!mounted) return;
      setState(() {
        _unitsCtrl.text = '${policy['unit_retention_years'] ?? 5}';
        _episCtrl.text = '${policy['epi_retention_years'] ?? 5}';
        _employeesCtrl.text = '${policy['employee_retention_years'] ?? 5}';
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Não foi possível carregar a política de arquivamento.';
      });
    }
  }

  int? _parseYears(TextEditingController ctrl) {
    final value = int.tryParse(ctrl.text.trim());
    if (value == null || value < 5) return null;
    return value;
  }

  Future<void> _save() async {
    final units = _parseYears(_unitsCtrl);
    final epis = _parseYears(_episCtrl);
    final employees = _parseYears(_employeesCtrl);
    if (units == null || epis == null || employees == null) {
      setState(() => _error = 'Informe períodos válidos (mínimo 5 anos).');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ApiClient.settings.updateArchivalPolicy(
        actorUserId: ApiClient.actorUserId,
        unitRetentionYears: units,
        epiRetentionYears: epis,
        employeeRetentionYears: employees,
        companyId: widget.companyId,
      );
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Política de arquivamento salva com sucesso.'),
        ),
      );
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  Widget _yearsField(String label, TextEditingController ctrl, bool enabled) {
    return TextField(
      controller: ctrl,
      enabled: enabled,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(
        labelText: label,
        suffixText: 'anos',
        border: const OutlineInputBorder(),
        isDense: true,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = context.watch<AuthCubit>().state;
    final role = authState is AuthAuthenticated
        ? authState.sessionContext.role
        : '';
    final canEdit = role == 'master_admin' || role == 'general_admin';
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(EpiSpacing.lg),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Defina, conforme a política interna da empresa, por quantos anos '
            'os registros arquivados de cada item permanecem preservados antes '
            'de a exclusão definitiva ser habilitada (mínimo legal: 5 anos).',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: EpiColors.textMuted),
          ),
          const SizedBox(height: EpiSpacing.md),
          _yearsField('Unidades', _unitsCtrl, canEdit && !_saving),
          const SizedBox(height: EpiSpacing.md),
          _yearsField('EPIs', _episCtrl, canEdit && !_saving),
          const SizedBox(height: EpiSpacing.md),
          _yearsField('Colaboradores', _employeesCtrl, canEdit && !_saving),
          const SizedBox(height: EpiSpacing.md),
          Text(
            'Ficha de EPI: retenção fixa de 5 anos (NR-6) — regra própria, '
            'não alterada por esta política.',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: EpiColors.textMuted),
          ),
          if (_error != null) ...[
            const SizedBox(height: EpiSpacing.sm),
            Text(
              _error!,
              style: const TextStyle(color: EpiColors.danger, fontSize: 12),
            ),
          ],
          if (canEdit) ...[
            const SizedBox(height: EpiSpacing.md),
            EpiButton(
              label: 'Salvar política de arquivamento',
              onPressed: _saving ? null : _save,
              loading: _saving,
            ),
          ],
        ],
      ),
    );
  }
}
