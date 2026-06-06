import 'dart:convert';

import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:signature/signature.dart';
import '../../core/bloc/devolutions_cubit.dart';

class NewReturnScreen extends StatefulWidget {
  const NewReturnScreen({
    super.key,
    required this.employees,
    required this.epis,
  });

  final List<Employee> employees;
  final List<Epi> epis;

  @override
  State<NewReturnScreen> createState() => _NewReturnScreenState();
}

class _NewReturnScreenState extends State<NewReturnScreen> {
  int _step = 0; // 0=employee, 1=epi+delivery, 2=details+signature
  Employee? _employee;
  Epi? _epi;
  OpenDelivery? _openDelivery;
  List<OpenDelivery> _openDeliveries = [];
  bool _loadingDeliveries = false;

  String _condition = 'good';
  String _destination = 'discard';
  final _notesController = TextEditingController();
  late final SignatureController _signatureController;
  bool _signatureDirty = false;

  final _employeeSearch = TextEditingController();
  final _epiSearch = TextEditingController();
  String _empQuery = '';
  String _epiQuery = '';

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
    if (_signatureController.isNotEmpty && !_signatureDirty) {
      setState(() => _signatureDirty = true);
    }
  }

  @override
  void dispose() {
    _notesController.dispose();
    _signatureController.dispose();
    _employeeSearch.dispose();
    _epiSearch.dispose();
    super.dispose();
  }

  List<Employee> get _filteredEmployees {
    if (_empQuery.isEmpty) return widget.employees;
    final q = _empQuery.toLowerCase();
    return widget.employees
        .where((e) => e.name.toLowerCase().contains(q))
        .toList();
  }

  List<Epi> get _filteredEpis {
    if (_epiQuery.isEmpty) return widget.epis;
    final q = _epiQuery.toLowerCase();
    return widget.epis.where((e) => e.name.toLowerCase().contains(q)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.returnNew),
        leading: _step == 0
            ? null
            : IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => setState(() => _step--),
              ),
      ),
      body: [
        _buildStep0(),
        _buildStep1(context),
        _buildStep2(context),
      ][_step],
    );
  }

  // ── Step 0: Select employee ──────────────────────────────────────────────

  Widget _buildStep0() {
    final l10n = AppLocalizations.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          child: TextField(
            controller: _employeeSearch,
            decoration: InputDecoration(
              hintText: l10n.searchEmployeeHint,
              prefixIcon: const Icon(Icons.search_rounded),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (q) => setState(() => _empQuery = q),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: _filteredEmployees.length,
            itemBuilder: (_, i) {
              final emp = _filteredEmployees[i];
              return ListTile(
                leading: EpiAvatar(name: emp.name),
                title: Text(emp.name),
                subtitle: Text(emp.sector ?? emp.role ?? ''),
                onTap: () => setState(() {
                  _employee = emp;
                  _step = 1;
                }),
              );
            },
          ),
        ),
      ],
    );
  }

  // ── Step 1: Select EPI + open delivery ──────────────────────────────────

  Widget _buildStep1(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(EpiSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _employee!.name,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: EpiSpacing.md),
              TextField(
                controller: _epiSearch,
                decoration: InputDecoration(
                  hintText: l10n.searchEpiHint,
                  prefixIcon: const Icon(Icons.search_rounded),
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                onChanged: (q) => setState(() => _epiQuery = q),
              ),
            ],
          ),
        ),
        if (_epi != null && _loadingDeliveries)
          const Padding(
            padding: EdgeInsets.all(EpiSpacing.lg),
            child: CircularProgressIndicator(),
          )
        else if (_epi != null && _openDeliveries.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.returnSelectDelivery,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: EpiSpacing.sm),
                ..._openDeliveries.map((d) => RadioListTile<OpenDelivery>(
                      title: Text(d.epiName),
                      subtitle: Text(
                          l10n.returnDeliveredInfo(d.deliveryDate, d.quantity)),
                      value: d,
                      groupValue: _openDelivery,
                      onChanged: (v) => setState(() => _openDelivery = v),
                    )),
                const SizedBox(height: EpiSpacing.lg),
                EpiButton(
                  label: l10n.next,
                  onPressed: _openDelivery == null
                      ? null
                      : () => setState(() => _step = 2),
                  fullWidth: true,
                ),
              ],
            ),
          )
        else
          Expanded(
            child: ListView.builder(
              itemCount: _filteredEpis.length,
              itemBuilder: (_, i) {
                final epi = _filteredEpis[i];
                return ListTile(
                  title: Text(epi.name),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => _selectEpi(context, epi),
                );
              },
            ),
          ),
      ],
    );
  }

  Future<void> _selectEpi(BuildContext context, Epi epi) async {
    setState(() {
      _epi = epi;
      _loadingDeliveries = true;
      _openDeliveries = [];
      _openDelivery = null;
    });
    final deliveries = await context
        .read<DevolutionsCubit>()
        .fetchOpenDeliveries(
          employeeId: _employee!.id,
          epiId: epi.id,
        );
    if (!mounted) return;
    setState(() {
      _openDeliveries = deliveries;
      _loadingDeliveries = false;
      if (deliveries.length == 1) _openDelivery = deliveries.first;
    });
  }

  // ── Step 2: Condition + destination + signature ─────────────────────────

  Widget _buildStep2(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocListener<DevolutionsCubit, DevolutionsState>(
      listenWhen: (p, c) =>
          p.successMessage != c.successMessage || p.error != c.error,
      listener: (ctx, state) {
        if (state.successMessage != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(state.successMessage!),
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
      child: ListView(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        children: [
          // Summary
          _SummaryCard(
            employee: _employee!,
            epi: _epi!,
            delivery: _openDelivery!,
          ),
          const SizedBox(height: EpiSpacing.xl),
          // Condition
          Text(l10n.returnConditionTitle,
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: EpiSpacing.sm),
          _ConditionSelector(
            value: _condition,
            onChange: (v) => setState(() => _condition = v),
          ),
          const SizedBox(height: EpiSpacing.lg),
          // Destination
          Text(l10n.returnDestinationTitle,
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: EpiSpacing.sm),
          _DestinationSelector(
            value: _destination,
            onChange: (v) => setState(() => _destination = v),
          ),
          const SizedBox(height: EpiSpacing.lg),
          // Notes
          TextFormField(
            controller: _notesController,
            decoration: InputDecoration(
              labelText: l10n.reportsRequestNotes,
              border: const OutlineInputBorder(),
            ),
            maxLines: 2,
          ),
          const SizedBox(height: EpiSpacing.xl),
          // Signature
          Text(l10n.deliveryStep4,
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: EpiSpacing.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(EpiRadius.md),
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: EpiColors.border),
                borderRadius: BorderRadius.circular(EpiRadius.md),
              ),
              height: 180,
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
                setState(() => _signatureDirty = false);
              },
              icon: const Icon(Icons.clear_rounded, size: 16),
              label: Text(l10n.deliveryClearSignature),
            ),
          ),
          const SizedBox(height: EpiSpacing.xl),
          BlocBuilder<DevolutionsCubit, DevolutionsState>(
            builder: (ctx, state) => EpiButton(
              label: l10n.returnSubmit,
              onPressed: state.isSubmitting ? null : () => _submit(ctx),
              fullWidth: true,
              size: EpiButtonSize.lg,
              loading: state.isSubmitting,
              icon: Icons.assignment_return_outlined,
            ),
          ),
          const SizedBox(height: EpiSpacing.xl2),
        ],
      ),
    );
  }

  Future<void> _submit(BuildContext ctx) async {
    if (!_signatureDirty || _signatureController.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).deliverySignatureRequired),
          backgroundColor: EpiColors.danger,
        ),
      );
      return;
    }
    final pngBytes = await _signatureController.toPngBytes();
    if (pngBytes == null) return;
    final signatureData = base64Encode(pngBytes);
    final today = DateTime.now().toIso8601String().substring(0, 10);

    if (!ctx.mounted) return;
    await ctx.read<DevolutionsCubit>().createDevolution(
          deliveryId: _openDelivery!.id,
          returnedDate: today,
          condition: _condition,
          destination: _destination,
          signatureData: signatureData,
          notes: _notesController.text.trim(),
        );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.employee,
    required this.epi,
    required this.delivery,
  });

  final Employee employee;
  final Epi epi;
  final OpenDelivery delivery;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Row(icon: Icons.person_outline_rounded, label: employee.name),
            _Row(icon: Icons.shield_outlined, label: epi.name),
            _Row(
              icon: Icons.calendar_today_outlined,
              label: l10n.returnDeliveryDateInfo(delivery.deliveryDate),
            ),
            _Row(
              icon: Icons.inventory_2_outlined,
              label: l10n.returnQuantityInfo(delivery.quantity),
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 18, color: EpiColors.textMuted),
          const SizedBox(width: EpiSpacing.sm),
          Expanded(
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class _ConditionSelector extends StatelessWidget {
  const _ConditionSelector({required this.value, required this.onChange});
  final String value;
  final void Function(String) onChange;

  static const _colors = <String, Color>{
    'good': EpiColors.success,
    'damaged': EpiColors.warning,
    'lost': EpiColors.danger,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final options = [
      (value: 'good', label: l10n.returnConditionGood, icon: Icons.check_circle_outline),
      (value: 'damaged', label: l10n.returnConditionDamaged, icon: Icons.warning_outlined),
      (value: 'lost', label: l10n.returnConditionLost, icon: Icons.search_off_rounded),
    ];
    return Row(
      children: options.map((opt) {
        final selected = value == opt.value;
        final color = _colors[opt.value] ?? EpiColors.textMuted;
        return Expanded(
          child: GestureDetector(
            onTap: () => onChange(opt.value),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              margin: const EdgeInsets.only(right: EpiSpacing.sm),
              padding: const EdgeInsets.symmetric(
                vertical: EpiSpacing.md,
                horizontal: EpiSpacing.sm,
              ),
              decoration: BoxDecoration(
                color: selected ? color.withValues(alpha: 0.12) : Colors.transparent,
                border: Border.all(
                  color: selected ? color : EpiColors.border,
                  width: selected ? 2 : 1,
                ),
                borderRadius: BorderRadius.circular(EpiRadius.md),
              ),
              child: Column(
                children: [
                  Icon(opt.icon,
                      color: selected ? color : EpiColors.textMuted, size: 20),
                  const SizedBox(height: 4),
                  Text(
                    opt.label,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: selected ? color : EpiColors.textMuted,
                          fontWeight: selected
                              ? FontWeight.w700
                              : FontWeight.w400,
                        ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _DestinationSelector extends StatelessWidget {
  const _DestinationSelector({required this.value, required this.onChange});
  final String value;
  final void Function(String) onChange;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final options = [
      (value: 'discard', label: l10n.returnDestDiscard),
      (value: 'repair', label: l10n.returnDestRepair),
      (value: 'stock', label: l10n.returnDestStock),
    ];
    return Column(
      children: options
          .map(
            (opt) => RadioListTile<String>(
              title: Text(opt.label),
              value: opt.value,
              groupValue: value,
              onChanged: (v) => onChange(v!),
              dense: true,
              contentPadding: EdgeInsets.zero,
            ),
          )
          .toList(),
    );
  }
}
