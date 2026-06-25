import 'package:epi_design/epi_design.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../../core/bloc/dashboard_cubit.dart';
import '../../core/i18n/locale_provider.dart';
import '../../core/router/routes.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key, this.localeProvider});

  /// Optional — passed by the router so the cubit can apply user locale
  /// preference received from the bootstrap response.
  final LocaleProvider? localeProvider;

  @override
  Widget build(BuildContext context) {
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
          _FabAction(
            icon: Icons.assignment_return_outlined,
            label: l10n.dashboardQuickReturn,
            heroTag: 'fab-return',
            onTap: () {
              setState(() => _fabOpen = false);
              context.push(Routes.returns);
            },
          ),
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
            EpiKpiCard(
              label: l10n.dashboardCriticalStock,
              value: '${state.criticalStock}',
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
