import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:epi_api/epi_api.dart';

class EmployeeDetailScreen extends StatelessWidget {
  const EmployeeDetailScreen({super.key, required this.employee});
  final Employee employee;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(employee.name)),
      body: ListView(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        children: [
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: EpiAvatar(name: employee.name, imageUrl: employee.photoUrl, size: 88),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: Text(
              employee.name,
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
          ),
          if (employee.role != null) ...[
            const SizedBox(height: EpiSpacing.xs),
            Center(
              child: Text(
                employee.role!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: EpiColors.textMuted,
                ),
              ),
            ),
          ],
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: EpiBadge(
              status: employee.isActive
                  ? EpiBadgeStatus.active
                  : EpiBadgeStatus.inactive,
            ),
          ),
          const SizedBox(height: EpiSpacing.xl2),
          _DetailSection(
            title: 'Dados do colaborador',
            items: [
              if (employee.code != null)
                _DetailRow(label: l10n.employeeCodeLabel, value: employee.code!),
              if (employee.sector != null)
                _DetailRow(label: l10n.employeeSectorLabel, value: employee.sector!),
              if (employee.role != null)
                _DetailRow(label: l10n.employeeRoleLabel, value: employee.role!),
              if (employee.unitName != null)
                _DetailRow(label: l10n.employeeUnitLabel, value: employee.unitName!),
              if (employee.admissionDate != null)
                _DetailRow(
                  label: l10n.employeeAdmissionLabel,
                  value: employee.admissionDate!,
                ),
              if (employee.schedule != null)
                _DetailRow(label: l10n.employeeScheduleLabel, value: employee.schedule!),
            ],
          ),
        ],
      ),
    );
  }
}

class _DetailSection extends StatelessWidget {
  const _DetailSection({required this.title, required this.items});
  final String title;
  final List<Widget> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: EpiColors.textMuted,
              ),
        ),
        const SizedBox(height: EpiSpacing.sm),
        Card(
          margin: EdgeInsets.zero,
          child: Column(children: items),
        ),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}
