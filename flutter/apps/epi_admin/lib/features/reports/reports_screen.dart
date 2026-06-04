import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/reports_cubit.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => ReportsCubit()..load(),
      child: const _ReportsBody(),
    );
  }
}

class _ReportsBody extends StatelessWidget {
  const _ReportsBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.reportsTitle),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: () => context.read<ReportsCubit>().load(),
            ),
          ],
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.reportsSummaryTab),
              Tab(text: l10n.reportsRequestsTab),
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () => _showRequestDialog(context),
          icon: const Icon(Icons.add_rounded),
          label: Text(l10n.reportsGenerate),
        ),
        body: BlocConsumer<ReportsCubit, ReportsState>(
          listenWhen: (p, c) =>
              p.successMessage != c.successMessage ||
              p.error != c.error,
          listener: (ctx, state) {
            if (state.successMessage != null) {
              ScaffoldMessenger.of(ctx).showSnackBar(
                SnackBar(
                  content: Text(AppLocalizations.of(ctx).reportsRequestSuccess),
                ),
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
            if (state.isLoading) {
              return const Center(child: CircularProgressIndicator());
            }
            if (state.data == null && state.error != null) {
              return _RetryView(
                onRetry: () => context.read<ReportsCubit>().load(),
              );
            }
            return TabBarView(
              children: [
                _SummaryTab(data: state.data),
                _RequestsTab(requests: state.requests),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _showRequestDialog(BuildContext context) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => BlocProvider.value(
        value: context.read<ReportsCubit>(),
        child: const _RequestDialog(),
      ),
    );
  }
}

// ── Summary tab ────────────────────────────────────────────────────────────

class _SummaryTab extends StatelessWidget {
  const _SummaryTab({required this.data});
  final ReportData? data;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (data == null) {
      return EpiEmptyState(
        title: l10n.reportsNoData,
        icon: Icons.bar_chart_outlined,
      );
    }
    final totalQty = data!.totalQuantity;
    final topEpis = data!.topEpis;
    final topSectors = data!.topSectors;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.lg,
        EpiSpacing.lg,
        EpiSpacing.xl5,
      ),
      children: [
        EpiKpiCard(
          label: l10n.reportsTotalDeliveries,
          value: totalQty.toString(),
          icon: Icons.inventory_outlined,
        ),
        const SizedBox(height: EpiSpacing.xl),
        if (topEpis.isNotEmpty) ...[
          Text(
            l10n.reportsTopEpis,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: EpiSpacing.md),
          SizedBox(
            height: 220,
            child: _HorizontalBarChart(entries: topEpis, color: EpiColors.brand),
          ),
          const SizedBox(height: EpiSpacing.xl),
        ],
        if (topSectors.isNotEmpty) ...[
          Text(
            l10n.reportsTopSectors,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: EpiSpacing.md),
          SizedBox(
            height: 220,
            child: _HorizontalBarChart(entries: topSectors, color: EpiColors.info),
          ),
        ],
      ],
    );
  }
}

class _HorizontalBarChart extends StatelessWidget {
  const _HorizontalBarChart({required this.entries, required this.color});
  final List<MapEntry<String, int>> entries;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final maxVal = entries.isEmpty
        ? 1
        : entries.map((e) => e.value).reduce((a, b) => a > b ? a : b);
    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: (maxVal * 1.2).ceilToDouble(),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final label = entries[group.x].key;
              return BarTooltipItem(
                '$label\n${rod.toY.toInt()}',
                const TextStyle(color: Colors.white, fontSize: 12),
              );
            },
          ),
        ),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 36,
              getTitlesWidget: (value, meta) {
                final i = value.toInt();
                if (i < 0 || i >= entries.length) return const SizedBox();
                final label = entries[i].key;
                final short = label.length > 8 ? '${label.substring(0, 7)}…' : label;
                return SideTitleWidget(
                  axisSide: meta.axisSide,
                  child: Text(
                    short,
                    style: const TextStyle(fontSize: 9),
                    textAlign: TextAlign.center,
                  ),
                );
              },
            ),
          ),
          leftTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        barGroups: List.generate(
          entries.length,
          (i) => BarChartGroupData(
            x: i,
            barRods: [
              BarChartRodData(
                toY: entries[i].value.toDouble(),
                color: color,
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

// ── Requests tab ───────────────────────────────────────────────────────────

class _RequestsTab extends StatelessWidget {
  const _RequestsTab({required this.requests});
  final List<ReportRequest> requests;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (requests.isEmpty) {
      return EpiEmptyState(
        title: l10n.reportsNoRequests,
        icon: Icons.list_alt_outlined,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.only(
        top: EpiSpacing.sm,
        bottom: EpiSpacing.xl5,
      ),
      itemCount: requests.length,
      separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
      itemBuilder: (_, i) => _RequestTile(request: requests[i]),
    );
  }
}

class _RequestTile extends StatelessWidget {
  const _RequestTile({required this.request});
  final ReportRequest request;

  static const _statusColors = <String, Color>{
    'pending': EpiColors.warning,
    'processing': EpiColors.info,
    'completed': EpiColors.success,
    'failed': EpiColors.danger,
  };

  Color get _color => _statusColors[request.status] ?? EpiColors.textMuted;

  String _label(AppLocalizations l10n) => switch (request.status) {
        'pending' => l10n.reportsRequestStatusPending,
        'processing' => l10n.reportsRequestStatusProcessing,
        'completed' => l10n.reportsRequestStatusCompleted,
        'failed' => l10n.reportsRequestStatusFailed,
        _ => request.status,
      };

  String get _periodLabel {
    if (request.periodYear != null && request.periodMonth != null) {
      const months = [
        '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
      ];
      final m = request.periodMonth!;
      final month = (m >= 1 && m <= 12) ? months[m] : '$m';
      return '$month ${request.periodYear}';
    }
    return '';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  request.unitName ?? l10n.reportsAllUnits,
                  style: Theme.of(context).textTheme.bodyLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: EpiSpacing.xs),
                Row(
                  children: [
                    const Icon(
                      Icons.person_outline_rounded,
                      size: 13,
                      color: EpiColors.textMuted,
                    ),
                    const SizedBox(width: 3),
                    Text(
                      request.requesterName,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: EpiColors.textMuted),
                    ),
                    if (_periodLabel.isNotEmpty) ...[
                      const SizedBox(width: EpiSpacing.sm),
                      const Icon(
                        Icons.calendar_today_outlined,
                        size: 13,
                        color: EpiColors.textMuted,
                      ),
                      const SizedBox(width: 3),
                      Text(
                        _periodLabel,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: EpiColors.textMuted),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: EpiSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.sm,
              vertical: 3,
            ),
            decoration: BoxDecoration(
              color: _color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(EpiRadius.full),
              border: Border.all(color: _color.withValues(alpha: 0.4)),
            ),
            child: Text(
              _label(l10n),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: _color,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Request dialog ─────────────────────────────────────────────────────────

class _RequestDialog extends StatefulWidget {
  const _RequestDialog();

  @override
  State<_RequestDialog> createState() => _RequestDialogState();
}

class _RequestDialogState extends State<_RequestDialog> {
  final _notesController = TextEditingController();
  int? _selectedYear;
  int? _selectedMonth;

  static const _months = [
    (label: 'Janeiro', value: 1),
    (label: 'Fevereiro', value: 2),
    (label: 'Março', value: 3),
    (label: 'Abril', value: 4),
    (label: 'Maio', value: 5),
    (label: 'Junho', value: 6),
    (label: 'Julho', value: 7),
    (label: 'Agosto', value: 8),
    (label: 'Setembro', value: 9),
    (label: 'Outubro', value: 10),
    (label: 'Novembro', value: 11),
    (label: 'Dezembro', value: 12),
  ];

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _selectedYear = now.year;
    _selectedMonth = now.month;
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currentYear = DateTime.now().year;
    final years = List.generate(3, (i) => currentYear - i);
    return BlocBuilder<ReportsCubit, ReportsState>(
      builder: (ctx, state) {
        final l10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(l10n.reportsRequestDialogTitle),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<int>(
                  value: _selectedYear,
                  decoration: InputDecoration(labelText: l10n.reportsRequestYear),
                  items: years
                      .map((y) => DropdownMenuItem(
                            value: y,
                            child: Text('$y'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedYear = v),
                ),
                const SizedBox(height: EpiSpacing.md),
                DropdownButtonFormField<int>(
                  value: _selectedMonth,
                  decoration: InputDecoration(labelText: l10n.reportsRequestMonth),
                  items: _months
                      .map((m) => DropdownMenuItem(
                            value: m.value,
                            child: Text(m.label),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedMonth = v),
                ),
                const SizedBox(height: EpiSpacing.md),
                TextField(
                  controller: _notesController,
                  decoration: InputDecoration(
                    labelText: l10n.reportsRequestNotes,
                    border: const OutlineInputBorder(),
                  ),
                  maxLines: 2,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(l10n.cancel),
            ),
            EpiButton(
              label: l10n.reportsRequestSubmit,
              loading: state.isSubmitting,
              onPressed: state.isSubmitting
                  ? null
                  : () async {
                      await ctx.read<ReportsCubit>().requestReport(
                            year: _selectedYear,
                            month: _selectedMonth,
                            notes: _notesController.text,
                          );
                      if (ctx.mounted) Navigator.pop(ctx);
                    },
            ),
          ],
        );
      },
    );
  }
}

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
