import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

import 'presentation/quotes_cubit.dart';
import 'quote_comparison_screen.dart';

/// Cotações (RFQ) de uma requisição de compra (Fase F3): criar por
/// fornecedor, enviar (e-mail/portal), registrar resposta manual e
/// selecionar a vencedora (que pré-preenche a PO no fluxo existente).
class QuotesScreen extends StatelessWidget {
  const QuotesScreen({super.key, required this.purchaseRequestId});
  final int purchaseRequestId;

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => QuotesCubit(purchaseRequestId)..load(),
      child: _QuotesBody(purchaseRequestId: purchaseRequestId),
    );
  }
}

class _QuotesBody extends StatelessWidget {
  const _QuotesBody({required this.purchaseRequestId});
  final int purchaseRequestId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('${l10n.quotesTitle} — #$purchaseRequestId'),
        actions: [
          BlocBuilder<QuotesCubit, QuotesState>(
            builder: (ctx, state) {
              final hasComparison =
                  ((state.comparison['suppliers'] as List?) ?? []).isNotEmpty;
              if (!hasComparison) return const SizedBox.shrink();
              return IconButton(
                icon: const Icon(Icons.table_chart_outlined),
                tooltip: l10n.quoteComparisonTitle,
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        QuoteComparisonScreen(comparison: state.comparison),
                  ),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<QuotesCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openNewQuote(context),
        icon: const Icon(Icons.add_rounded),
        label: Text(l10n.quotesNew),
      ),
      body: BlocConsumer<QuotesCubit, QuotesState>(
        listenWhen: (previous, current) =>
            current.error != null && previous.error != current.error,
        listener: (ctx, state) {
          ScaffoldMessenger.of(ctx).showSnackBar(
            SnackBar(content: Text(state.error!)),
          );
        },
        builder: (ctx, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          if (state.quotes.isEmpty) {
            return EpiEmptyState(
              title: l10n.noResults,
              icon: Icons.request_quote_outlined,
            );
          }
          return RefreshIndicator(
            onRefresh: () => ctx.read<QuotesCubit>().load(),
            child: ListView.separated(
              padding: const EdgeInsets.only(
                top: EpiSpacing.sm,
                bottom: EpiSpacing.xl5,
              ),
              itemCount: state.quotes.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 1, indent: 16),
              itemBuilder: (_, i) => _QuoteTile(quote: state.quotes[i]),
            ),
          );
        },
      ),
    );
  }

  Future<void> _openNewQuote(BuildContext context) async {
    final cubit = context.read<QuotesCubit>();
    final suppliers = await cubit.loadSuppliers();
    if (!context.mounted) return;
    final selected = await showDialog<List<int>>(
      context: context,
      builder: (_) => _SupplierPickerDialog(suppliers: suppliers),
    );
    if (selected == null || selected.isEmpty) return;
    await cubit.createQuotes(selected);
  }
}

class _QuoteTile extends StatelessWidget {
  const _QuoteTile({required this.quote});
  final Map<String, dynamic> quote;

  static const _statusColors = <String, Color>{
    'draft': EpiColors.textMuted,
    'sent': EpiColors.info,
    'answered': EpiColors.warning,
    'selected': EpiColors.success,
    'discarded': EpiColors.textMuted,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final status = '${quote['status'] ?? ''}';
    final color = _statusColors[status] ?? EpiColors.textMuted;
    final cubit = context.read<QuotesCubit>();
    return ListTile(
      leading: Icon(Icons.request_quote_outlined, color: color),
      title: Text('${quote['supplier_name'] ?? ''}',
          maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        [
          status,
          '${quote['channel'] ?? ''}',
          if ('${quote['answered_at'] ?? ''}'.isNotEmpty)
            '${quote['answered_at']}'.split('T').first,
        ].join(' · '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: PopupMenuButton<String>(
        onSelected: (action) => _onAction(context, cubit, action),
        itemBuilder: (_) => [
          if (status == 'draft' || status == 'sent') ...[
            PopupMenuItem(
                value: 'send_email', child: Text(l10n.quoteSendEmail)),
            PopupMenuItem(
                value: 'send_portal', child: Text(l10n.quoteSendPortal)),
            PopupMenuItem(
                value: 'answer', child: Text(l10n.quoteAnswerAction)),
          ],
          if (status == 'answered')
            PopupMenuItem(
                value: 'select', child: Text(l10n.quoteSelectWinner)),
        ],
      ),
      onTap: () => _showItems(context),
    );
  }

  Future<void> _onAction(
      BuildContext context, QuotesCubit cubit, String action) async {
    final l10n = AppLocalizations.of(context);
    final quoteId = quote['id'] as int;
    switch (action) {
      case 'send_email':
        {
          final ok = await cubit.sendQuote(quoteId, viaPortal: false);
          if (ok && context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(l10n.actionSentSuccess)));
          }
        }
      case 'send_portal':
        {
          final ok = await cubit.sendQuote(quoteId, viaPortal: true);
          if (ok && context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text(l10n.actionSentSuccess)));
          }
        }
      case 'answer':
        {
          await showDialog<void>(
            context: context,
            builder: (_) => BlocProvider.value(
              value: cubit,
              child: _AnswerQuoteDialog(quote: quote),
            ),
          );
        }
      case 'select':
        {
          final draft = await cubit.selectQuote(quoteId);
          if (draft == null || draft.isEmpty || !context.mounted) return;
          final create = await showDialog<bool>(
            context: context,
            builder: (dialogCtx) => AlertDialog(
              title: Text(l10n.quoteSelectWinner),
              content: Text(l10n.quoteCreatePo),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogCtx).pop(false),
                  child: Text(l10n.cancel),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(dialogCtx).pop(true),
                  child: Text(l10n.confirm),
                ),
              ],
            ),
          );
          if (create == true) {
            await cubit.createPurchaseOrderFromDraft(draft);
          }
        }
    }
  }

  void _showItems(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final items = ((quote['items'] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (_) => ListView.separated(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (_, i) {
          final item = items[i];
          final price = double.tryParse('${item['unit_price'] ?? 0}') ?? 0;
          final declined = '${item['declined'] ?? 0}' == '1' ||
              item['declined'] == true;
          return ListTile(
            dense: true,
            title: Text('${item['epi_name'] ?? ''}'),
            subtitle: Text(
              declined
                  ? l10n.quoteDeclinedLabel
                  : '${l10n.quoteUnitPriceLabel}: '
                      'R\$ ${price.toStringAsFixed(2)} · '
                      '${l10n.catalogLeadTimeLabel}: '
                      '${item['lead_time_days'] ?? 0}',
            ),
            trailing: Text('x${item['quantity_requested'] ?? 0}'),
          );
        },
      ),
    );
  }
}

class _SupplierPickerDialog extends StatefulWidget {
  const _SupplierPickerDialog({required this.suppliers});
  final List<Map<String, dynamic>> suppliers;

  @override
  State<_SupplierPickerDialog> createState() => _SupplierPickerDialogState();
}

class _SupplierPickerDialogState extends State<_SupplierPickerDialog> {
  final Set<int> _selected = {};

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final active = widget.suppliers
        .where((s) => '${s['active'] ?? 1}' == '1')
        .toList();
    return AlertDialog(
      title: Text(l10n.quotesSelectSuppliers),
      content: SizedBox(
        width: double.maxFinite,
        child: active.isEmpty
            ? Text(l10n.noResults)
            : ListView.builder(
                shrinkWrap: true,
                itemCount: active.length,
                itemBuilder: (_, i) {
                  final s = active[i];
                  final id = s['id'] as int;
                  return CheckboxListTile(
                    dense: true,
                    title: Text('${s['name'] ?? ''}'),
                    value: _selected.contains(id),
                    onChanged: (v) => setState(() =>
                        v == true ? _selected.add(id) : _selected.remove(id)),
                  );
                },
              ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _selected.isEmpty
              ? null
              : () => Navigator.of(context).pop(_selected.toList()),
          child: Text(l10n.confirm),
        ),
      ],
    );
  }
}

class _AnswerQuoteDialog extends StatefulWidget {
  const _AnswerQuoteDialog({required this.quote});
  final Map<String, dynamic> quote;

  @override
  State<_AnswerQuoteDialog> createState() => _AnswerQuoteDialogState();
}

class _AnswerQuoteDialogState extends State<_AnswerQuoteDialog> {
  late final List<Map<String, dynamic>> _items;
  late final List<TextEditingController> _prices;
  late final List<TextEditingController> _leads;
  late final List<bool> _declined;
  final _freight = TextEditingController();

  @override
  void initState() {
    super.initState();
    _items = ((widget.quote['items'] as List?) ?? [])
        .map((e) => (e as Map).cast<String, dynamic>())
        .toList();
    _prices = _items
        .map((i) => TextEditingController(
            text: '${i['unit_price'] ?? ''}' == '0' ||
                    '${i['unit_price'] ?? ''}' == '0.0'
                ? ''
                : '${i['unit_price'] ?? ''}'))
        .toList();
    _leads = _items
        .map((i) => TextEditingController(
            text: '${i['lead_time_days'] ?? ''}' == '0'
                ? ''
                : '${i['lead_time_days'] ?? ''}'))
        .toList();
    _declined = _items
        .map((i) => '${i['declined'] ?? 0}' == '1' || i['declined'] == true)
        .toList();
  }

  @override
  void dispose() {
    for (final c in _prices) {
      c.dispose();
    }
    for (final c in _leads) {
      c.dispose();
    }
    _freight.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.quoteAnswerAction),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (var i = 0; i < _items.length; i++) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${_items[i]['epi_name'] ?? ''} '
                    '(x${_items[i]['quantity_requested'] ?? 0})',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
                const SizedBox(height: EpiSpacing.xs),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _prices[i],
                        enabled: !_declined[i],
                        decoration: InputDecoration(
                            labelText: l10n.quoteUnitPriceLabel),
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                      ),
                    ),
                    const SizedBox(width: EpiSpacing.sm),
                    Expanded(
                      child: TextField(
                        controller: _leads[i],
                        enabled: !_declined[i],
                        decoration: InputDecoration(
                            labelText: l10n.catalogLeadTimeLabel),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    Checkbox(
                      value: _declined[i],
                      onChanged: (v) =>
                          setState(() => _declined[i] = v ?? false),
                    ),
                  ],
                ),
                const SizedBox(height: EpiSpacing.md),
              ],
              TextField(
                controller: _freight,
                decoration:
                    InputDecoration(labelText: l10n.quoteFreightLabel),
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        BlocBuilder<QuotesCubit, QuotesState>(
          builder: (ctx, state) => FilledButton(
            onPressed: state.isSubmitting ? null : () => _save(ctx),
            child: Text(l10n.save),
          ),
        ),
      ],
    );
  }

  Future<void> _save(BuildContext context) async {
    final body = {
      'freight_value':
          double.tryParse(_freight.text.replaceAll(',', '.')) ?? 0,
      'items': [
        for (var i = 0; i < _items.length; i++)
          {
            'quote_item_id': _items[i]['id'],
            'unit_price':
                double.tryParse(_prices[i].text.replaceAll(',', '.')) ?? 0,
            'lead_time_days': int.tryParse(_leads[i].text) ?? 0,
            'declined': _declined[i],
          },
      ],
    };
    final ok = await context
        .read<QuotesCubit>()
        .answerQuote(widget.quote['id'] as int, body);
    if (ok && mounted) Navigator.of(context).pop();
  }
}
