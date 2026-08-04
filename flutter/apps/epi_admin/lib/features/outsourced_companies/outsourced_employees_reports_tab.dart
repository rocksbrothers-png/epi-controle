import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';

/// Relatório de headcount por empresa terceirizada/prestadora (ativos vs.
/// arquivados, por tipo de vínculo) — ADR-0002 §10.4.
///
/// Consulta direta ao endpoint (sem cubit): tela só de leitura, sem estado
/// de edição a coordenar — o `FutureBuilder` já cobre loading/erro/dados.
class OutsourcedEmployeesReportsTab extends StatefulWidget {
  const OutsourcedEmployeesReportsTab({super.key});

  @override
  State<OutsourcedEmployeesReportsTab> createState() => _OutsourcedEmployeesReportsTabState();
}

class _OutsourcedEmployeesReportsTabState extends State<OutsourcedEmployeesReportsTab> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() => ApiClient.outsourcedCompanies
      .getOutsourcedEmployeesSummary(actorUserId: ApiClient.actorUserId);

  Future<void> _refresh() async {
    final future = _load();
    setState(() => _future = future);
    await future;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(l10n.outsourcedReportsError),
                  const SizedBox(height: EpiSpacing.md),
                  FilledButton(onPressed: _refresh, child: Text(l10n.retry)),
                ],
              ),
            );
          }
          final entries = snapshot.data ?? const [];
          if (entries.isEmpty) {
            return Center(child: Text(l10n.outsourcedReportsEmpty));
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(EpiSpacing.md),
              itemCount: entries.length,
              separatorBuilder: (_, __) => const SizedBox(height: EpiSpacing.sm),
              itemBuilder: (_, i) => _CompanyHeadcountCard(entry: entries[i]),
            ),
          );
        },
      ),
    );
  }
}

class _CompanyHeadcountCard extends StatelessWidget {
  const _CompanyHeadcountCard({required this.entry});
  final Map<String, dynamic> entry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final tradeName = '${entry['trade_name'] ?? ''}'.trim();
    final legalName = '${entry['legal_name'] ?? ''}'.trim();
    final name = tradeName.isNotEmpty ? tradeName : legalName;
    final activeCount = (entry['active_count'] as num?)?.toInt() ?? 0;
    final archivedCount = (entry['archived_count'] as num?)?.toInt() ?? 0;
    final byTipoVinculo = (entry['by_tipo_vinculo'] as Map?)?.cast<String, dynamic>() ?? const {};

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(name, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: EpiSpacing.sm),
            Wrap(
              spacing: EpiSpacing.sm,
              runSpacing: EpiSpacing.xs,
              children: [
                Chip(label: Text('${l10n.outsourcedReportsActive}: $activeCount')),
                Chip(label: Text('${l10n.outsourcedReportsArchived}: $archivedCount')),
              ],
            ),
            if (byTipoVinculo.isNotEmpty) ...[
              const SizedBox(height: EpiSpacing.sm),
              Wrap(
                spacing: EpiSpacing.sm,
                runSpacing: EpiSpacing.xs,
                children: [
                  for (final e in byTipoVinculo.entries)
                    Chip(
                      visualDensity: VisualDensity.compact,
                      label: Text('${e.key}: ${e.value}'),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
