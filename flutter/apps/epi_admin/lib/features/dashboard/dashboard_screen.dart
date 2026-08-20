import 'package:epi_design/epi_design.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/dashboard_cubit.dart';
import '../../core/i18n/locale_provider.dart';
import '../../core/router/navigation_policy.dart';
import '../../core/router/routes.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key, this.localeProvider});

  /// Optional — passed by the router so the cubit can apply user locale
  /// preference received from the bootstrap response.
  final LocaleProvider? localeProvider;

  @override
  Widget build(BuildContext context) {
    // Papel e unidade operacional do ator NÃO são lidos aqui: o travamento de
    // CNPJ/Unidade vem em `scope.locked` na resposta de
    // `/api/dashboard/summary` (fatia 1.1D-C2). Deduzi-lo da sessão era
    // reimplementar autorização no cliente.
    return BlocProvider(
      create: (_) => DashboardCubit(localeProvider: localeProvider)..load(),
      child: const _DashboardBody(),
    );
  }
}

class _DashboardBody extends StatefulWidget {
  const _DashboardBody();

  @override
  State<_DashboardBody> createState() => _DashboardBodyState();
}

class _DashboardBodyState extends State<_DashboardBody> {
  bool _fabOpen = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final authState = context.watch<AuthCubit>().state;
    final moduleVisibility = authState is AuthAuthenticated
        ? authState.sessionContext.moduleVisibility
        : const <String, bool>{};
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.dashboardTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<DashboardCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: _ExpandableFab(
        isOpen: _fabOpen,
        onToggle: () => setState(() => _fabOpen = !_fabOpen),
        actions: [
          _FabAction(
            icon: Icons.qr_code_scanner_rounded,
            label: l10n.dashboardQuickScan,
            heroTag: 'fab-scan',
            onTap: () {
              setState(() => _fabOpen = false);
              context.push(Routes.qr);
            },
          ),
          // Atalhos de Devolução/Entrega: escondidos junto com o módulo
          // "entregas" — sem isto, o atalho ficaria visível apontando para
          // uma rota que o guarda de navegação vai recusar.
          if (isModuleLocationAccessible(Routes.returns, moduleVisibility))
            _FabAction(
              icon: Icons.assignment_return_outlined,
              label: l10n.dashboardQuickReturn,
              heroTag: 'fab-return',
              onTap: () {
                setState(() => _fabOpen = false);
                context.push(Routes.returns);
              },
            ),
          if (isModuleLocationAccessible(Routes.deliveries, moduleVisibility))
            _FabAction(
              icon: Icons.assignment_outlined,
              label: l10n.dashboardQuickDelivery,
              heroTag: 'fab-delivery',
              onTap: () {
                setState(() => _fabOpen = false);
                context.push(Routes.deliveries);
              },
            ),
        ],
      ),
      body: BlocBuilder<DashboardCubit, DashboardState>(
        builder: (ctx, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.error != null) {
            return _ErrorView(message: state.error!);
          }
          return _DashboardContent(state: state);
        },
      ),
    );
  }
}

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({required this.state});
  final DashboardState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.all(EpiSpacing.lg),
      children: [
        // Filtro em cascata Empresa → CNPJ → Unidade → Setor. Só aparece
        // quando a empresa tem CNPJs cadastrados (Multi-CNPJ provisionado).
        if (state.legalEntities.isNotEmpty) ...[
          _DashboardFilterBar(state: state),
          const SizedBox(height: EpiSpacing.md),
        ],
        // KPI grid
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: EpiSpacing.md,
          mainAxisSpacing: EpiSpacing.md,
          childAspectRatio: 1.6,
          children: [
            EpiKpiCard(
              label: l10n.dashboardDeliveriesToday,
              value: '${state.deliveriesToday}',
              icon: Icons.local_shipping_outlined,
              iconColor: EpiColors.info,
            ),
            EpiKpiCard(
              label: l10n.dashboardExpiringEpis,
              value: '${state.expiringEpis}',
              icon: Icons.warning_amber_rounded,
              iconColor: EpiColors.warning,
            ),
            // `criticalStock` vem CONTADO do servidor. Sem Unidade resolvida
            // ele é `null`, e o card mostra "—": exibir 0 afirmaria que
            // nenhum EPI está crítico, quando a pergunta nem foi feita.
            EpiKpiCard(
              label: l10n.dashboardCriticalStock,
              value: '${state.criticalStock ?? '—'}',
              icon: Icons.inventory_2_outlined,
              iconColor: EpiColors.danger,
            ),
            EpiKpiCard(
              label: l10n.dashboardPendingPurchases,
              value: '${state.pendingPurchases}',
              icon: Icons.shopping_cart_outlined,
              iconColor: EpiColors.brand,
            ),
          ],
        ),
        const SizedBox(height: EpiSpacing.xl),
        // Conformidade de estoque (item 2) — fonte única do backend.
        Text(
          l10n.dashboardComplianceTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: EpiSpacing.md),
        _ComplianceSection(compliance: state.compliance),
        const SizedBox(height: EpiSpacing.xl),
        // Weekly deliveries chart
        Text(
          l10n.dashboardWeeklyChartTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: EpiSpacing.md),
        const SizedBox(
          height: 160,
          child: _WeeklyChart(),
        ),
        const SizedBox(height: EpiSpacing.xl),
        // Alerts
        Text(
          l10n.dashboardAlertsTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: EpiSpacing.md),
        if (state.alerts.isEmpty)
          EpiEmptyState(
            icon: Icons.notifications_none_rounded,
            title: l10n.dashboardNoAlerts,
          )
        else
          ...state.alerts.map((a) => _AlertTile(alert: a)),
      ],
    );
  }
}

/// Seção de conformidade de estoque (item 2). Mostra apenas as categorias com
/// contagem > 0 (chips coloridos por severidade). Quando tudo está zerado (ou o
/// backend não expõe o endpoint), exibe o estado "em conformidade".
class _ComplianceSection extends StatelessWidget {
  const _ComplianceSection({required this.compliance});
  final Map<String, int> compliance;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    int c(String k) => compliance[k] ?? 0;

    // (label, contagem, cor) — ordem por severidade.
    final items = <(String, int, Color)>[
      (l10n.complianceCaExpired, c('ca_expired'), EpiColors.danger),
      (l10n.complianceProductExpired, c('product_expired'), EpiColors.danger),
      (l10n.complianceAdminBlocked, c('admin_blocked'), EpiColors.danger),
      (l10n.complianceCaExpiring, c('ca_expiring'), EpiColors.warning),
      (l10n.complianceProductExpiring, c('product_expiring'), EpiColors.warning),
      (l10n.complianceMissingManufacture, c('missing_manufacture'), EpiColors.info),
      (l10n.complianceMissingLot, c('missing_lot'), EpiColors.info),
    ].where((e) => e.$2 > 0).toList();

    if (items.isEmpty) {
      return EpiCard(
        child: Row(
          children: [
            const Icon(Icons.verified_outlined,
                color: EpiColors.success, size: 20),
            const SizedBox(width: EpiSpacing.sm),
            Expanded(child: Text(l10n.dashboardComplianceAllOk)),
          ],
        ),
      );
    }

    return Wrap(
      spacing: EpiSpacing.sm,
      runSpacing: EpiSpacing.sm,
      children: [
        for (final it in items)
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: EpiSpacing.md, vertical: EpiSpacing.sm),
            decoration: BoxDecoration(
              color: it.$3.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(EpiRadius.sm),
              border: Border.all(color: it.$3.withValues(alpha: 0.5)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${it.$2}',
                  style: TextStyle(fontWeight: FontWeight.bold, color: it.$3),
                ),
                const SizedBox(width: EpiSpacing.xs),
                Text(it.$1),
              ],
            ),
          ),
      ],
    );
  }
}

class _WeeklyChart extends StatelessWidget {
  const _WeeklyChart();

  static const _mockData = <double>[12, 8, 15, 6, 20, 18, 9];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final days = [
      l10n.dayMon,
      l10n.dayTue,
      l10n.dayWed,
      l10n.dayThu,
      l10n.dayFri,
      l10n.daySat,
      l10n.daySun,
    ];
    return BarChart(
      BarChartData(
        maxY: 25,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, _) {
                final idx = value.toInt();
                if (idx < 0 || idx >= days.length) return const SizedBox.shrink();
                return Text(
                  days[idx],
                  style: const TextStyle(fontSize: 11),
                );
              },
            ),
          ),
        ),
        barGroups: List.generate(
          7,
          (i) => BarChartGroupData(
            x: i,
            barRods: [
              BarChartRodData(
                toY: _mockData[i],
                color: EpiColors.brand,
                width: 18,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(4),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});
  final Map<String, dynamic> alert;

  @override
  Widget build(BuildContext context) {
    final title = alert['title'] as String? ?? alert['message'] as String? ?? '—';
    final description = alert['description'] as String?;
    // O backend (compute_alerts) classifica o alerta na chave 'type'
    // (danger/warning); mantém-se 'severity' como fallback de compatibilidade.
    final severity =
        alert['type'] as String? ?? alert['severity'] as String? ?? 'info';
    final color = switch (severity) {
      'danger' || 'critical' => EpiColors.danger,
      'warning' => EpiColors.warning,
      _ => EpiColors.info,
    };
    return Card(
      margin: const EdgeInsets.only(bottom: EpiSpacing.sm),
      child: ListTile(
        leading: Icon(Icons.circle, size: 10, color: color),
        title: Text(title),
        subtitle: (description != null && description.isNotEmpty)
            ? Text(description)
            : null,
        isThreeLine: description != null && description.isNotEmpty,
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message});
  final String message;

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
          EpiButton(
            label: AppLocalizations.of(context).retry,
            onPressed: () => context.read<DashboardCubit>().load(),
          ),
        ],
      ),
    );
  }
}

class _ExpandableFab extends StatelessWidget {
  const _ExpandableFab({
    required this.isOpen,
    required this.onToggle,
    required this.actions,
  });

  final bool isOpen;
  final VoidCallback onToggle;
  final List<_FabAction> actions;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        if (isOpen) ...[
          for (final action in actions) ...[
            action,
            const SizedBox(height: EpiSpacing.sm),
          ],
        ],
        FloatingActionButton(
          heroTag: 'fab-main',
          onPressed: onToggle,
          child: Icon(isOpen ? Icons.close_rounded : Icons.add_rounded),
        ),
      ],
    );
  }
}

class _FabAction extends StatelessWidget {
  const _FabAction({
    required this.icon,
    required this.label,
    required this.heroTag,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final String heroTag;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          elevation: 2,
          borderRadius: BorderRadius.circular(EpiRadius.sm),
          color: Theme.of(context).colorScheme.surface,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.md,
              vertical: EpiSpacing.sm,
            ),
            child: Text(label, style: Theme.of(context).textTheme.labelMedium),
          ),
        ),
        const SizedBox(width: EpiSpacing.sm),
        FloatingActionButton.small(
          heroTag: heroTag,
          onPressed: onTap,
          child: Icon(icon, size: 20),
        ),
      ],
    );
  }
}

/// Barra de filtros do dashboard: Empresa → CNPJ → Unidade → Setor.
///
/// A cascata é do SERVIDOR: cada troca reconsulta `/api/dashboard/summary`, que
/// devolve os KPIs já recortados e as opções válidas para o novo recorte. Antes
/// os KPIs eram recomputados no cliente sobre os dados crus do bootstrap.
class _DashboardFilterBar extends StatelessWidget {
  const _DashboardFilterBar({required this.state});
  final DashboardState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<DashboardCubit>();
    // Administrador Local / Gestor de EPI: CNPJ e Unidade ficam travados na
    // própria Unidade. A trava vem em `scope.locked`, decidida pelo backend —
    // o cliente não a deriva mais do papel da sessão. Sem opção "Todos", campo
    // desabilitado, e a lista mostra só a própria opção.
    final locked = state.isLocked;
    final lockedEntities = locked
        ? state.legalEntities
            .where((e) => e.id == state.selectedLegalEntityId)
            .toList(growable: false)
        : state.legalEntities;
    final lockedUnits = locked
        ? state.units
            .where((u) => u.id == state.selectedUnitId)
            .toList(growable: false)
        : state.availableUnits;
    // DropdownButtonFormField exige que `initialValue` combine com exatamente
    // um item da lista (ou seja null). Sem a própria unidade/CNPJ na lista
    // (ex.: unidade arquivada depois de vincular o usuário), cai pra null em
    // vez de violar essa regra — mesmo com o campo travado/desabilitado.
    final entityValue =
        (locked && lockedEntities.isEmpty) ? null : state.selectedLegalEntityId;
    final unitValue =
        (locked && lockedUnits.isEmpty) ? null : state.selectedUnitId;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.md),
        child: Wrap(
          spacing: EpiSpacing.md,
          runSpacing: EpiSpacing.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 260,
              child: DropdownButtonFormField<int?>(
                initialValue: entityValue,
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: l10n.dashboardFilterLegalEntity,
                ),
                items: [
                  if (!locked)
                    DropdownMenuItem<int?>(
                      child: Text(l10n.dashboardFilterAll),
                    ),
                  // O rótulo do CNPJ já vem pronto do servidor
                  // (`_rotulo_cnpj`): nome fantasia, razão social ou o próprio
                  // CNPJ, na ordem em que o usuário reconhece.
                  ...lockedEntities.map(
                    (e) => DropdownMenuItem<int?>(
                      value: e.id,
                      child: Text(e.name, overflow: TextOverflow.ellipsis),
                    ),
                  ),
                ],
                onChanged: locked ? null : cubit.selectLegalEntity,
              ),
            ),
            SizedBox(
              width: 200,
              child: DropdownButtonFormField<int?>(
                initialValue: unitValue,
                isExpanded: true,
                decoration: InputDecoration(labelText: l10n.dashboardFilterUnit),
                items: [
                  if (!locked)
                    DropdownMenuItem<int?>(
                      child: Text(l10n.dashboardFilterAll),
                    ),
                  ...lockedUnits.map(
                    (u) => DropdownMenuItem<int?>(
                      value: u.id,
                      child: Text(u.name, overflow: TextOverflow.ellipsis),
                    ),
                  ),
                ],
                onChanged: locked ? null : cubit.selectUnit,
              ),
            ),
            SizedBox(
              width: 180,
              child: DropdownButtonFormField<String?>(
                initialValue: state.selectedSector,
                isExpanded: true,
                decoration:
                    InputDecoration(labelText: l10n.dashboardFilterSector),
                items: [
                  DropdownMenuItem<String?>(
                    child: Text(l10n.dashboardFilterAll),
                  ),
                  ...state.sectors.map(
                    (s) => DropdownMenuItem<String?>(
                      value: s,
                      child: Text(s, overflow: TextOverflow.ellipsis),
                    ),
                  ),
                ],
                onChanged: cubit.selectSector,
              ),
            ),
            if (!locked && state.hasActiveFilter)
              TextButton.icon(
                onPressed: cubit.clearFilters,
                icon: const Icon(Icons.filter_alt_off_outlined),
                label: Text(l10n.dashboardFilterClear),
              ),
          ],
        ),
      ),
    );
  }
}
