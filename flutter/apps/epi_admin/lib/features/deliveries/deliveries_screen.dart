import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import '../../core/api/api_client.dart';
import 'new_delivery_screen.dart';

class DeliveriesScreen extends StatelessWidget {
  const DeliveriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.deliveriesTitle)),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openNew(context),
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.deliveryNew),
      ),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.local_shipping_outlined,
              size: 80,
              color: EpiColors.border,
            ),
            const SizedBox(height: EpiSpacing.lg),
            Text(
              'Histórico de entregas',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: EpiColors.textMuted,
                  ),
            ),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              'Registre uma nova entrega usando o botão abaixo',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: EpiColors.textMuted,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: EpiSpacing.xl2),
            EpiButton(
              label: l10n.deliveryNew,
              onPressed: () => _openNew(context),
              icon: Icons.add_rounded,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openNew(BuildContext context) async {
    final bootstrap = await _loadBootstrap();
    if (!context.mounted) return;
    await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => NewDeliveryScreen(
          employees: bootstrap.$1,
          epis: bootstrap.$2,
          companyId: bootstrap.$3,
        ),
      ),
    );
  }

  Future<(List<Employee>, List<Epi>, int)> _loadBootstrap() async {
    try {
      final b = await ApiClient.auth.bootstrap();
      final employees = b.employees.map(Employee.fromJson).toList();
      final epis = b.epis.map(Epi.fromJson).toList();
      final companyId = (b.units.isNotEmpty
              ? (b.units.first['company_id'] as int?) ?? 0
              : 0);
      return (employees, epis, companyId);
    } on Exception {
      return (<Employee>[], <Epi>[], 0);
    }
  }
}
