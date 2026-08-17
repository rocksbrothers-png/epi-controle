import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/settings_cubit.dart';
import '../../core/i18n/locale_provider.dart';
import '../../core/i18n/theme_mode_notifier.dart';
import '../../core/router/routes.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({
    super.key,
    required this.localeProvider,
    required this.themeNotifier,
  });

  final LocaleProvider localeProvider;
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    final authState = context.read<AuthCubit>().state;
    final isMaster = authState is AuthAuthenticated &&
        authState.sessionContext.role == 'master_admin';
    return BlocProvider(
      create: (_) => SettingsCubit()..init(isMaster: isMaster),
      child: _SettingsBody(
        localeProvider: localeProvider,
        themeNotifier: themeNotifier,
      ),
    );
  }
}

class _SettingsBody extends StatelessWidget {
  const _SettingsBody({
    required this.localeProvider,
    required this.themeNotifier,
  });

  final LocaleProvider localeProvider;
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: BlocConsumer<SettingsCubit, SettingsState>(
        listenWhen: (p, c) =>
            p.successMessage != c.successMessage || p.error != c.error,
        listener: (ctx, state) {
          if (state.successMessage != null) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(content: Text(AppLocalizations.of(ctx).settingsSaved)),
            );
          }
          if (state.error != null) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(
                content: Text(state.error!),
                backgroundColor: EpiColors.danger,
              ),
            );
          }
        },
        builder: (ctx, state) {
          final authState = ctx.watch<AuthCubit>().state;
          final canConfigureCompany = authState is AuthAuthenticated &&
              authState.permissions.contains('company_settings:view');
          return ListView(
            padding: const EdgeInsets.only(bottom: EpiSpacing.xl5),
            children: [
              if (canConfigureCompany) ...[
                _SectionHeader(label: l10n.myCompanyTitle),
                ListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
                  leading: const Icon(Icons.apartment_outlined),
                  title: Text(l10n.myCompanyTitle),
                  subtitle: Text(l10n.myCompanySubtitle),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(Routes.myCompany),
                ),
                const SizedBox(height: EpiSpacing.lg),
              ],
              _SectionHeader(label: l10n.settingsAppSection),
              _ThemeSelector(themeNotifier: themeNotifier),
              const Divider(height: 1),
              _LanguageSelector(localeProvider: localeProvider),
              const SizedBox(height: EpiSpacing.lg),
              const _SectionHeader(label: 'Assinatura'),
              ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
                leading: const Icon(Icons.receipt_long_outlined),
                title: const Text('Minha Assinatura'),
                subtitle: const Text('Plano, cobranças e cancelamento'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push(Routes.subscription),
              ),
              ListTile(
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
                leading: const Icon(Icons.history_rounded),
                title: const Text('Histórico Financeiro'),
                subtitle: const Text('Todas as cobranças e recibos'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push(Routes.invoices),
              ),
              const SizedBox(height: EpiSpacing.lg),
              const _SectionHeader(label: 'Regras'),
              if (state.isMaster && state.selectedCompanyId == null)
                const Padding(
                  padding: EdgeInsets.all(EpiSpacing.lg),
                  child: Text(
                    'Selecione uma empresa (na seção Ficha) para configurar as regras.',
                    style: TextStyle(color: EpiColors.textMuted),
                  ),
                )
              else ...[
                _ArchivalPolicyCard(
                  companyId: state.isMaster ? state.selectedCompanyId : null,
                ),
                const SizedBox(height: EpiSpacing.xl),
                _ModuleVisibilityCard(
                  companyId: state.isMaster ? state.selectedCompanyId : null,
                ),
              ],
              const SizedBox(height: EpiSpacing.lg),
              _SectionHeader(label: l10n.settingsFichaSection),
              if (state.isMaster) _CompanySelector(state: state),
              if (state.isLoading)
                const Padding(
                  padding: EdgeInsets.all(EpiSpacing.xl),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (state.isMaster && state.selectedCompanyId == null)
                const Padding(
                  padding: EdgeInsets.all(EpiSpacing.lg),
                  child: Text(
                    'Selecione uma empresa para configurar a Ficha.',
                    style: TextStyle(color: EpiColors.textMuted),
                  ),
                )
              else
                _FichaConfigForm(
                  config: state.config ?? const FichaConfig(),
                  isSaving: state.isSaving,
                ),
            ],
          );
        },
      ),
    );
  }
}

// ── Section header ─────────────────────────────────────────────────────────

// ── Seletor de empresa (master_admin) ───────────────────────────────────────
// A Ficha é isolada por empresa. O master_admin, que não pertence a uma
// empresa, escolhe explicitamente qual tenant está administrando; um banner
// deixa a empresa ativa visível para evitar edição na empresa errada.
class _CompanySelector extends StatelessWidget {
  const _CompanySelector({required this.state});
  final SettingsState state;

  @override
  Widget build(BuildContext context) {
    final active = state.companies
        .where((c) => c.id == state.selectedCompanyId)
        .toList();
    final activeName = active.isNotEmpty ? active.first.name : null;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButtonFormField<int>(
            value: state.selectedCompanyId,
            decoration: const InputDecoration(
              labelText: 'Empresa',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: [
              for (final c in state.companies)
                DropdownMenuItem(value: c.id, child: Text(c.name)),
            ],
            onChanged: state.isSaving
                ? null
                : (v) {
                    if (v != null) {
                      context.read<SettingsCubit>().selectCompany(v);
                    }
                  },
          ),
          if (activeName != null) ...[
            const SizedBox(height: EpiSpacing.sm),
            Container(
              padding: const EdgeInsets.all(EpiSpacing.sm),
              decoration: BoxDecoration(
                color: EpiColors.brand.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.apartment_rounded,
                      size: 18, color: EpiColors.brand),
                  const SizedBox(width: EpiSpacing.sm),
                  Expanded(
                    child: Text(
                      'Administrando a empresa: $activeName',
                      style: const TextStyle(
                        color: EpiColors.brand,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: EpiSpacing.md),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.xl,
        EpiSpacing.lg,
        EpiSpacing.sm,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: EpiColors.brand,
              letterSpacing: 0.5,
            ),
      ),
    );
  }
}

// ── Theme selector ─────────────────────────────────────────────────────────

class _ThemeSelector extends StatelessWidget {
  const _ThemeSelector({required this.themeNotifier});
  final ThemeModeNotifier themeNotifier;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final options = [
      (mode: ThemeMode.light, label: l10n.settingsThemeLight),
      (mode: ThemeMode.dark, label: l10n.settingsThemeDark),
      (mode: ThemeMode.system, label: l10n.settingsThemeSystem),
    ];
    return ListenableBuilder(
      listenable: themeNotifier,
      builder: (context, _) {
        return ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
          ),
          title: Text(l10n.settingsTheme),
          trailing: SegmentedButton<ThemeMode>(
            segments: options
                .map((o) => ButtonSegment(
                      value: o.mode,
                      label: Text(o.label),
                    ))
                .toList(),
            selected: {themeNotifier.mode},
            onSelectionChanged: (s) => themeNotifier.setMode(s.first),
            showSelectedIcon: false,
          ),
        );
      },
    );
  }
}

// ── Language selector ──────────────────────────────────────────────────────

class _LanguageSelector extends StatelessWidget {
  const _LanguageSelector({required this.localeProvider});
  final LocaleProvider localeProvider;

  static const _locales = [
    (tag: 'pt-BR', label: 'Português (BR)'),
    (tag: 'en-US', label: 'English (US)'),
    (tag: 'es-ES', label: 'Español'),
    (tag: 'fr-FR', label: 'Français'),
    (tag: 'no-NO', label: 'Norsk'),
  ];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListenableBuilder(
      listenable: localeProvider,
      builder: (context, _) {
        final current = '${localeProvider.locale.languageCode}-'
            '${localeProvider.locale.countryCode}';
        return ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.lg,
          ),
          title: Text(l10n.settingsLanguage),
          trailing: DropdownButton<String>(
            value: _locales.any((l) => l.tag == current) ? current : 'pt-BR',
            underline: const SizedBox(),
            items: _locales
                .map((l) => DropdownMenuItem(
                      value: l.tag,
                      child: Text(l.label),
                    ))
                .toList(),
            onChanged: (tag) {
              if (tag == null) return;
              final parts = tag.split('-');
              localeProvider.setLocale(
                Locale(parts[0], parts.length > 1 ? parts[1] : null),
              );
            },
          ),
        );
      },
    );
  }
}

// ── Ficha config form ──────────────────────────────────────────────────────

class _FichaConfigForm extends StatefulWidget {
  const _FichaConfigForm({required this.config, required this.isSaving});
  final FichaConfig config;
  final bool isSaving;

  @override
  State<_FichaConfigForm> createState() => _FichaConfigFormState();
}

class _FichaConfigFormState extends State<_FichaConfigForm> {
  late final TextEditingController _titulo;
  late final TextEditingController _declaracao;
  late final TextEditingController _observacoes;
  late final TextEditingController _rastreabilidade;

  @override
  void initState() {
    super.initState();
    _titulo = TextEditingController(text: widget.config.titulo);
    _declaracao = TextEditingController(text: widget.config.declaracao);
    _observacoes = TextEditingController(text: widget.config.observacoes);
    _rastreabilidade = TextEditingController(text: widget.config.rastreabilidade);
  }

  @override
  void didUpdateWidget(_FichaConfigForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.config != widget.config) {
      _titulo.text = widget.config.titulo;
      _declaracao.text = widget.config.declaracao;
      _observacoes.text = widget.config.observacoes;
      _rastreabilidade.text = widget.config.rastreabilidade;
    }
  }

  @override
  void dispose() {
    _titulo.dispose();
    _declaracao.dispose();
    _observacoes.dispose();
    _rastreabilidade.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _titulo,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaTitle,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _declaracao,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaDeclaration,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _observacoes,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaObservations,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.md),
          // Rótulo de rastreabilidade impresso no rodapé da ficha (texto
          // livre — o backend trata como String, não como liga/desliga).
          TextField(
            controller: _rastreabilidade,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaTracking,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          EpiButton(
            label: l10n.save,
            loading: widget.isSaving,
            fullWidth: true,
            onPressed: widget.isSaving ? null : _save,
          ),
          const SizedBox(height: EpiSpacing.xl),
        ],
      ),
    );
  }

  void _save() {
    context.read<SettingsCubit>().save(
          widget.config.copyWith(
            titulo: _titulo.text,
            declaracao: _declaracao.text,
            observacoes: _observacoes.text,
            rastreabilidade: _rastreabilidade.text,
          ),
        );
  }
}


// ── Regras → Política de Arquivamento ───────────────────────────────────────
// Retenção configurável por tenant (anos) para Unidades, EPIs e Colaboradores,
// conforme a política interna da empresa (mínimo legal: 5 anos). A retenção
// da Ficha de EPI (5 anos, NR-6) tem regra própria e não é alterada aqui.
class _ArchivalPolicyCard extends StatefulWidget {
  const _ArchivalPolicyCard({this.companyId});
  final int? companyId;

  @override
  State<_ArchivalPolicyCard> createState() => _ArchivalPolicyCardState();
}

class _ArchivalPolicyCardState extends State<_ArchivalPolicyCard> {
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
  void didUpdateWidget(_ArchivalPolicyCard oldWidget) {
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

// ── Regras → Visibilidade por Módulo (issue #148 / visibilidade por Unidade)
// ────────────────────────────────────────────────────────────────────────────
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
          Text(l10n.moduleVisibilityTitle, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: EpiSpacing.xs),
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
