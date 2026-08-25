import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import 'widgets/settings_page.dart';

/// Configurações → Visibilidade por Módulo.
///
/// Personalização, por perfil e por Unidade, dos módulos que cada perfil
/// enxerga — sobre as permissões padrão (imutáveis) do sistema.
class ModuleVisibilityScreen extends StatelessWidget {
  const ModuleVisibilityScreen({super.key, this.companyId});

  /// Empresa em edição, vinda de `?company_id=` (só o `master_admin`).
  final int? companyId;

  @override
  Widget build(BuildContext context) {
    return SettingsSubPage(
      title: AppLocalizations.of(context).moduleVisibilityTitle,
      child: settingsCompanyMissing(context, companyId)
          ? const SettingsCompanyRequired()
          : _ModuleVisibilityCard(companyId: companyId),
    );
  }
}

// ── Visibilidade por Módulo (issue #148 / visibilidade por Unidade) ─────────
// Cobre todos os módulos configuráveis (MODULE_KEYS em epi_backend/
// rule_engine.py), não só os dois opt-in de Terceirizados — module_visibility
// é a única fonte de verdade para tenant + perfil + unidade + módulo desde a
// evolução do backend (issue #148). Para os perfis com vínculo de unidade
// única (admin/user), um seletor de Unidade permite editar o bucket daquela
// Unidade em vez do bucket padrão "*"; um módulo ausente do bucket da
// Unidade herda o valor do bucket "*" do mesmo perfil — mesma regra de
// resolve_module_visibility() no backend. O antigo card separado de "Escopo
// por Unidade" (module_unit_scope, restrito aos dois módulos opt-in) foi
// retirado: o backend removeu suas rotas quando module_unit_scope deixou de
// existir como mecanismo paralelo.
const _kModuleVisibilityRoles = <(String value, String label)>[
  ('admin', 'Administrador Local'),
  ('user', 'Gestor de EPI'),
  ('general_admin', 'Administrador Geral'),
  ('registry_admin', 'Administrador de Registro'),
];

// Espelha MODULE_KEYS de epi_backend/rule_engine.py.
const _kModuleVisibilityModules = <(String value, String label)>[
  ('dashboard', 'Dashboard'),
  ('compras', 'Compras'),
  ('estoque', 'Estoque'),
  ('entregas', 'Entregas'),
  ('solicitacoes', 'Solicitações'),
  ('fichas', 'Fichas de EPI'),
  ('relatorios', 'Relatórios'),
  ('administracao', 'Administração'),
  ('configuracoes', 'Configurações'),
  ('terceirizados', 'Terceirizados e Prestadores'),
  ('terceirizados_colaboradores', 'Cadastro de Colaboradores'),
];

// Espelha _UNIT_SCOPED_ROLES de epi_backend/rule_engine.py: só admin
// (Administrador Local) e user (Gestor de EPI) têm vínculo de unidade
// única, então só eles fazem sentido com override por Unidade. É só
// controle de exibição do seletor — o backend valida de novo e é quem
// decide de fato (save_module_visibility rejeita unit_id para qualquer
// outro perfil).
const _kModuleVisibilityUnitScopedRoles = <String>{'admin', 'user'};

class _ModuleVisibilityCard extends StatefulWidget {
  const _ModuleVisibilityCard({this.companyId});
  final int? companyId;

  @override
  State<_ModuleVisibilityCard> createState() => _ModuleVisibilityCardState();
}

class _ModuleVisibilityCardState extends State<_ModuleVisibilityCard> {
  String _role = _kModuleVisibilityRoles.first.$1;
  int? _unitId;
  // role -> bucket ("*" ou "<unit_id>") -> module -> bool
  Map<String, Map<String, Map<String, bool>>> _visibility = const {};
  // role -> module -> bool — padrão IMUTÁVEL do sistema (permissão técnica),
  // nunca a personalização salva. Usado só pelo painel "Permissões padrão
  // deste perfil"; a matriz de switches abaixo continua lendo _visibility.
  Map<String, Map<String, bool>> _defaultVisibility = const {};
  List<Map<String, dynamic>> _units = const [];
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_ModuleVisibilityCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.companyId != widget.companyId) _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await ApiClient.settings.getModuleVisibility(companyId: widget.companyId);
      final raw = (res['module_visibility'] as Map?)?.cast<String, dynamic>() ?? const {};
      final rawDefault = (res['default_module_visibility'] as Map?)?.cast<String, dynamic>() ?? const {};
      final bootstrap = await ApiClient.auth.bootstrap();
      if (!mounted) return;
      setState(() {
        _visibility = raw.map(
          (role, buckets) => MapEntry(
            role,
            ((buckets as Map?)?.cast<String, dynamic>() ?? const {}).map(
              (bucket, modules) => MapEntry(
                bucket,
                (modules as Map?)?.cast<String, dynamic>().map(
                      (k, v) => MapEntry(k, v == true),
                    ) ??
                    const {},
              ),
            ),
          ),
        );
        _defaultVisibility = rawDefault.map(
          (role, modules) => MapEntry(
            role,
            (modules as Map?)?.cast<String, dynamic>().map((k, v) => MapEntry(k, v == true)) ?? const {},
          ),
        );
        _units = bootstrap.units;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Não foi possível carregar a visualização de módulos.';
      });
    }
  }

  // Espelha resolve_module_visibility() em epi_backend/rule_engine.py: um
  // módulo ausente do bucket da Unidade herda do bucket "*"; ausente de
  // ambos, assume visível (regra padrão do sistema).
  bool _isVisible(String module) {
    final roleConfig = _visibility[_role] ?? const {};
    final base = roleConfig['*'] ?? const {};
    if (_unitId != null) {
      final bucket = roleConfig['$_unitId'] ?? const {};
      if (bucket.containsKey(module)) return bucket[module]!;
    }
    if (base.containsKey(module)) return base[module]!;
    return true;
  }

  Future<void> _toggle(String module, bool value) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ApiClient.settings.saveModuleVisibility(
        actorUserId: ApiClient.actorUserId,
        role: _role,
        modules: {module: value},
        unitId: _unitId,
        companyId: widget.companyId,
      );
      if (!mounted) return;
      final bucketKey = _unitId != null ? '$_unitId' : '*';
      setState(() {
        final roleConfig = Map<String, Map<String, bool>>.from(_visibility[_role] ?? const {});
        roleConfig[bucketKey] = {...(roleConfig[bucketKey] ?? const {}), module: value};
        _visibility = {..._visibility, _role: roleConfig};
        _saving = false;
      });
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final authState = context.watch<AuthCubit>().state;
    final role = authState is AuthAuthenticated ? authState.sessionContext.role : '';
    final canEdit = role == 'master_admin' || role == 'general_admin' || role == 'registry_admin';
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.all(EpiSpacing.lg),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final unitScoped = _kModuleVisibilityUnitScopedRoles.contains(_role);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // O título da seção agora é o da AppBar da subtela — repeti-lo
          // aqui só empurraria a explicação para baixo da dobra.
          Text(
            l10n.moduleVisibilityDescription,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
          ),
          const SizedBox(height: EpiSpacing.md),
          DropdownButtonFormField<String>(
            value: _role,
            decoration: InputDecoration(
              labelText: l10n.moduleVisibilityRoleLabel,
              border: const OutlineInputBorder(),
              isDense: true,
            ),
            items: _kModuleVisibilityRoles
                .map((r) => DropdownMenuItem(value: r.$1, child: Text(r.$2)))
                .toList(),
            onChanged: canEdit && !_saving
                ? (v) => setState(() {
                      _role = v ?? _role;
                      if (!_kModuleVisibilityUnitScopedRoles.contains(_role)) _unitId = null;
                    })
                : null,
          ),
          const SizedBox(height: EpiSpacing.sm),
          _DefaultPermissionsPanel(
            modules: _defaultVisibility[_role] ?? const {},
            moduleLabels: _kModuleVisibilityModules,
          ),
          if (unitScoped) ...[
            const SizedBox(height: EpiSpacing.sm),
            DropdownButtonFormField<int?>(
              value: _unitId,
              decoration: InputDecoration(
                labelText: l10n.moduleVisibilityUnitLabel,
                border: const OutlineInputBorder(),
                isDense: true,
              ),
              items: [
                DropdownMenuItem<int?>(
                  value: null,
                  child: Text(l10n.moduleVisibilityAllUnitsOption),
                ),
                for (final unit in _units)
                  DropdownMenuItem<int?>(
                    value: (unit['id'] as num).toInt(),
                    child: Text('${unit['name'] ?? ''}'),
                  ),
              ],
              onChanged: canEdit && !_saving ? (v) => setState(() => _unitId = v) : null,
            ),
            const SizedBox(height: EpiSpacing.xs),
            Text(
              l10n.moduleVisibilityUnitHint,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
            ),
          ],
          const SizedBox(height: EpiSpacing.sm),
          for (final module in _kModuleVisibilityModules)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(module.$2),
              value: _isVisible(module.$1),
              onChanged: canEdit && !_saving ? (v) => _toggle(module.$1, v) : null,
            ),
          if (_error != null) ...[
            const SizedBox(height: EpiSpacing.sm),
            Text(_error!, style: const TextStyle(color: EpiColors.danger, fontSize: 12)),
          ],
        ],
      ),
    );
  }
}

/// Painel "Permissões padrão deste perfil": mostra o padrão IMUTÁVEL do
/// sistema (`_ModuleVisibilityCardState._defaultVisibility`, nunca a
/// personalização salva pelo Administrador Geral) para o perfil
/// selecionado — deixa explícito que a matriz de switches abaixo é uma
/// PERSONALIZAÇÃO sobre esse padrão, não a definição do perfil.
class _DefaultPermissionsPanel extends StatelessWidget {
  const _DefaultPermissionsPanel({required this.modules, required this.moduleLabels});

  final Map<String, bool> modules;
  final List<(String value, String label)> moduleLabels;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final enabled = moduleLabels.where((m) => modules[m.$1] == true).toList();
    return Container(
      padding: const EdgeInsets.all(EpiSpacing.md),
      decoration: BoxDecoration(
        color: EpiColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: EpiColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.moduleVisibilityDefaultPanelTitle, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: EpiSpacing.xs),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: enabled.isEmpty
                ? [Chip(label: Text(l10n.moduleVisibilityNoDefaultModules))]
                : enabled
                    .map((m) => Chip(
                          avatar: const Icon(Icons.check, size: 16),
                          label: Text(m.$2),
                          backgroundColor: EpiColors.successSoft,
                        ))
                    .toList(),
          ),
          const SizedBox(height: EpiSpacing.xs),
          Text(
            l10n.moduleVisibilityDefaultPanelHint,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
          ),
        ],
      ),
    );
  }
}
