import 'dart:convert';

import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:signature/signature.dart';
import '../../core/bloc/new_delivery_cubit.dart';

class NewDeliveryScreen extends StatelessWidget {
  const NewDeliveryScreen({
    super.key,
    required this.employees,
    required this.epis,
    required this.companyId,
  });

  final List<Employee> employees;
  final List<Epi> epis;
  final int companyId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => NewDeliveryCubit(),
      child: _NewDeliveryBody(
        employees: employees,
        epis: epis,
        companyId: companyId,
      ),
    );
  }
}

class _NewDeliveryBody extends StatelessWidget {
  const _NewDeliveryBody({
    required this.employees,
    required this.epis,
    required this.companyId,
  });

  final List<Employee> employees;
  final List<Epi> epis;
  final int companyId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<NewDeliveryCubit, NewDeliveryState>(
      builder: (ctx, state) {
        final stepTitles = [
          l10n.deliveryStep1,
          l10n.deliveryStep2,
          l10n.deliveryStep3,
          l10n.deliveryStep4,
        ];
        final stepIdx = DeliveryStep.values.indexOf(state.step);

        return Scaffold(
          appBar: AppBar(
            title: Text(l10n.deliveryNew),
            leading: stepIdx == 0
                ? null
                : IconButton(
                    icon: const Icon(Icons.arrow_back_rounded),
                    onPressed: () => ctx.read<NewDeliveryCubit>().goBack(),
                  ),
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(48),
              child: _StepIndicator(
                steps: stepTitles,
                current: stepIdx,
              ),
            ),
          ),
          body: BlocListener<NewDeliveryCubit, NewDeliveryState>(
            listenWhen: (p, c) =>
                p.successId != c.successId || p.error != c.error,
            listener: (ctx, state) {
              if (state.successId != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(l10n.deliverySuccess),
                    backgroundColor: EpiColors.success,
                  ),
                );
                Navigator.pop(context, true);
              }
              if (state.error != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(state.error!),
                    backgroundColor: EpiColors.danger,
                  ),
                );
              }
            },
            child: switch (state.step) {
              DeliveryStep.employee => _EmployeeStep(employees: employees),
              DeliveryStep.epi => _EpiStep(epis: epis),
              DeliveryStep.details => const _DetailsStep(),
              DeliveryStep.signature => _SignatureStep(companyId: companyId),
            },
          ),
        );
      },
    );
  }
}

// ── Step Indicator ─────────────────────────────────────────────────────────

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({required this.steps, required this.current});
  final List<String> steps;
  final int current;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: Row(
        children: steps.asMap().entries.map((e) {
          final active = e.key == current;
          final done = e.key < current;
          final color = done || active ? EpiColors.brand : EpiColors.border;
          return Expanded(
            child: Column(
              children: [
                LinearProgressIndicator(
                  value: done ? 1 : (active ? 0.5 : 0),
                  color: EpiColors.brand,
                  backgroundColor: EpiColors.border,
                  minHeight: 3,
                ),
                const SizedBox(height: 4),
                Text(
                  e.value,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: color,
                        fontWeight:
                            active ? FontWeight.w700 : FontWeight.w400,
                      ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Step 1: Employee ────────────────────────────────────────────────────────

class _EmployeeStep extends StatefulWidget {
  const _EmployeeStep({required this.employees});
  final List<Employee> employees;

  @override
  State<_EmployeeStep> createState() => _EmployeeStepState();
}

class _EmployeeStepState extends State<_EmployeeStep> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<Employee> get _filtered {
    if (_query.isEmpty) return widget.employees;
    final q = _query.toLowerCase();
    return widget.employees
        .where((e) => e.name.toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          child: TextField(
            controller: _search,
            autofocus: true,
            decoration: const InputDecoration(
              hintText: 'Buscar colaborador...',
              prefixIcon: Icon(Icons.search_rounded),
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (q) => setState(() => _query = q),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: _filtered.length,
            itemBuilder: (_, i) {
              final emp = _filtered[i];
              return ListTile(
                leading: EpiAvatar(name: emp.name),
                title: Text(emp.name),
                subtitle: Text([emp.sector, emp.role]
                    .where((s) => s != null && s.isNotEmpty)
                    .join(' · ')),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () =>
                    context.read<NewDeliveryCubit>().selectEmployee(emp),
              );
            },
          ),
        ),
      ],
    );
  }
}

// ── Step 2: EPI ─────────────────────────────────────────────────────────────

class _EpiStep extends StatefulWidget {
  const _EpiStep({required this.epis});
  final List<Epi> epis;

  @override
  State<_EpiStep> createState() => _EpiStepState();
}

class _EpiStepState extends State<_EpiStep> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<Epi> get _filtered {
    if (_query.isEmpty) return widget.epis;
    final q = _query.toLowerCase();
    return widget.epis.where((e) => e.name.toLowerCase().contains(q)).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          child: BlocBuilder<NewDeliveryCubit, NewDeliveryState>(
            buildWhen: (p, c) => p.selectedEmployee != c.selectedEmployee,
            builder: (_, state) => Text(
              state.selectedEmployee?.name ?? '',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: EpiColors.textMuted,
                  ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
          child: TextField(
            controller: _search,
            autofocus: true,
            decoration: const InputDecoration(
              hintText: 'Buscar EPI...',
              prefixIcon: Icon(Icons.search_rounded),
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (q) => setState(() => _query = q),
          ),
        ),
        const SizedBox(height: EpiSpacing.sm),
        Expanded(
          child: ListView.builder(
            itemCount: _filtered.length,
            itemBuilder: (_, i) {
              final epi = _filtered[i];
              return ListTile(
                title: Text(epi.name),
                subtitle: Text('Estoque: ${epi.stockQuantity}'),
                trailing: epi.isCriticalStock
                    ? const EpiBadge(status: EpiBadgeStatus.critical)
                    : const Icon(Icons.chevron_right_rounded),
                onTap: epi.stockQuantity > 0
                    ? () => context.read<NewDeliveryCubit>().selectEpi(epi)
                    : null,
                enabled: epi.stockQuantity > 0,
              );
            },
          ),
        ),
      ],
    );
  }
}

// ── Step 3: Details ─────────────────────────────────────────────────────────

class _DetailsStep extends StatefulWidget {
  const _DetailsStep();

  @override
  State<_DetailsStep> createState() => _DetailsStepState();
}

class _DetailsStepState extends State<_DetailsStep> {
  final _qtyController = TextEditingController(text: '1');
  final _sectorController = TextEditingController();
  final _roleController = TextEditingController();
  DateTime _deliveryDate = DateTime.now();
  DateTime _nextReplacementDate =
      DateTime.now().add(const Duration(days: 365));

  bool _initialized = false;

  @override
  void dispose() {
    _qtyController.dispose();
    _sectorController.dispose();
    _roleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<NewDeliveryCubit, NewDeliveryState>(
      buildWhen: (p, c) =>
          !_initialized &&
          (p.selectedEmployee != c.selectedEmployee ||
              p.selectedEpi != c.selectedEpi),
      builder: (ctx, state) {
        if (!_initialized && state.selectedEmployee != null) {
          _sectorController.text = state.selectedEmployee!.sector ?? '';
          _roleController.text = state.selectedEmployee!.role ?? '';
          _initialized = true;
        }

        return ListView(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          children: [
            // Summary header
            Card(
              child: Padding(
                padding: const EdgeInsets.all(EpiSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(state.selectedEmployee?.name ?? '',
                        style: Theme.of(context).textTheme.titleSmall),
                    Text(state.selectedEpi?.name ?? '',
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(color: EpiColors.textMuted)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: EpiSpacing.lg),
            TextField(
              controller: _qtyController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Quantidade',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: EpiSpacing.lg),
            TextField(
              controller: _sectorController,
              decoration: const InputDecoration(
                labelText: 'Setor',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: EpiSpacing.lg),
            TextField(
              controller: _roleController,
              decoration: const InputDecoration(
                labelText: 'Função',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: EpiSpacing.lg),
            _DateField(
              label: 'Data da entrega',
              value: _deliveryDate,
              onChanged: (d) => setState(() => _deliveryDate = d),
            ),
            const SizedBox(height: EpiSpacing.lg),
            _DateField(
              label: 'Próxima substituição',
              value: _nextReplacementDate,
              onChanged: (d) => setState(() => _nextReplacementDate = d),
            ),
            const SizedBox(height: EpiSpacing.xl),
            EpiButton(
              label: AppLocalizations.of(context).next,
              onPressed: () {
                final qty = int.tryParse(_qtyController.text.trim()) ?? 1;
                ctx.read<NewDeliveryCubit>().setDetails(
                      quantity: qty,
                      deliveryDate:
                          _deliveryDate.toIso8601String().substring(0, 10),
                      nextReplacementDate: _nextReplacementDate
                          .toIso8601String()
                          .substring(0, 10),
                      sector: _sectorController.text.trim(),
                      roleName: _roleController.text.trim(),
                    );
                ctx.read<NewDeliveryCubit>().goToSignature();
              },
              fullWidth: true,
              size: EpiButtonSize.lg,
            ),
          ],
        );
      },
    );
  }
}

class _DateField extends StatelessWidget {
  const _DateField({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final DateTime value;
  final void Function(DateTime) onChanged;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: value,
          firstDate: DateTime(2020),
          lastDate: DateTime(2100),
        );
        if (picked != null) onChanged(picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
          suffixIcon: const Icon(Icons.calendar_today_outlined),
        ),
        child: Text(value.toIso8601String().substring(0, 10)),
      ),
    );
  }
}

// ── Step 4: Signature ───────────────────────────────────────────────────────

class _SignatureStep extends StatefulWidget {
  const _SignatureStep({required this.companyId});
  final int companyId;

  @override
  State<_SignatureStep> createState() => _SignatureStepState();
}

class _SignatureStepState extends State<_SignatureStep> {
  late final SignatureController _signatureController;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    _signatureController = SignatureController(
      penStrokeWidth: 2,
      penColor: Colors.black,
      exportBackgroundColor: Colors.white,
    );
    _signatureController.addListener(_onDraw);
  }

  void _onDraw() {
    if (_signatureController.isNotEmpty && !_dirty) {
      setState(() => _dirty = true);
    }
  }

  @override
  void dispose() {
    _signatureController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<NewDeliveryCubit, NewDeliveryState>(
      builder: (ctx, state) {
        return ListView(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          children: [
            // Delivery summary
            Card(
              child: Padding(
                padding: const EdgeInsets.all(EpiSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _SummaryRow(
                      icon: Icons.person_outline_rounded,
                      text: state.selectedEmployee?.name ?? '',
                    ),
                    _SummaryRow(
                      icon: Icons.shield_outlined,
                      text: state.selectedEpi?.name ?? '',
                    ),
                    _SummaryRow(
                      icon: Icons.inventory_2_outlined,
                      text: '${l10n.epiStockLabel}: ${state.quantity}',
                    ),
                    _SummaryRow(
                      icon: Icons.calendar_today_outlined,
                      text: 'Data: ${state.deliveryDate ?? ''}',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: EpiSpacing.xl),
            Text(l10n.deliveryStep4,
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: EpiSpacing.sm),
            Text(
              l10n.portalSignatureInstruction,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            ),
            const SizedBox(height: EpiSpacing.md),
            ClipRRect(
              borderRadius: BorderRadius.circular(EpiRadius.md),
              child: Container(
                decoration: BoxDecoration(
                  border: Border.all(
                    color: _dirty ? EpiColors.brand : EpiColors.border,
                    width: _dirty ? 2 : 1,
                  ),
                  borderRadius: BorderRadius.circular(EpiRadius.md),
                ),
                height: 200,
                child: Signature(
                  controller: _signatureController,
                  backgroundColor: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: EpiSpacing.sm),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () {
                  _signatureController.clear();
                  setState(() => _dirty = false);
                },
                icon: const Icon(Icons.clear_rounded, size: 16),
                label: Text(l10n.deliveryClearSignature),
              ),
            ),
            const SizedBox(height: EpiSpacing.xl),
            EpiButton(
              label: l10n.deliveryConfirm,
              onPressed: state.isSubmitting ? null : () => _submit(ctx),
              fullWidth: true,
              size: EpiButtonSize.lg,
              loading: state.isSubmitting,
              icon: Icons.check_circle_outline_rounded,
            ),
            const SizedBox(height: EpiSpacing.xl2),
          ],
        );
      },
    );
  }

  Future<void> _submit(BuildContext ctx) async {
    if (!_dirty || _signatureController.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:
              Text(AppLocalizations.of(context).deliverySignatureRequired),
          backgroundColor: EpiColors.danger,
        ),
      );
      return;
    }
    final pngBytes = await _signatureController.toPngBytes();
    if (pngBytes == null || !ctx.mounted) return;
    final signatureData = base64Encode(pngBytes);

    await ctx.read<NewDeliveryCubit>().submit(
          companyId: widget.companyId,
          signatureData: signatureData,
        );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon, size: 16, color: EpiColors.textMuted),
          const SizedBox(width: EpiSpacing.sm),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}
