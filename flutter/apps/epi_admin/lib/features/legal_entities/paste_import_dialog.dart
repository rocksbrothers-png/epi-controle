import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/legal_entities_cubit.dart';

/// Divide uma linha respeitando aspas duplas (campos com vírgula dentro).
List<String> _splitLine(String line, String sep) {
  final out = <String>[];
  final buffer = StringBuffer();
  var inQuotes = false;
  for (var i = 0; i < line.length; i++) {
    final ch = line[i];
    if (ch == '"') {
      // "" dentro de campo entre aspas = aspas literal.
      if (inQuotes && i + 1 < line.length && line[i + 1] == '"') {
        buffer.write('"');
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch == sep && !inQuotes) {
      out.add(buffer.toString().trim());
      buffer.clear();
    } else {
      buffer.write(ch);
    }
  }
  out.add(buffer.toString().trim());
  return out;
}

/// Converte o texto colado em linhas `{cabeçalho: valor}`.
///
/// O separador é detectado pela primeira linha: colar do Excel produz TAB;
/// exportar CSV produz vírgula ou ponto e vírgula (padrão pt-BR).
List<Map<String, dynamic>> parsePastedTable(String raw) {
  final lines = raw
      .split(RegExp(r'\r\n|\r|\n'))
      .where((l) => l.trim().isNotEmpty)
      .toList();
  if (lines.length < 2) return const [];

  final header = lines.first;
  final sep = header.contains('\t')
      ? '\t'
      : (header.split(';').length > header.split(',').length ? ';' : ',');

  final columns = _splitLine(header, sep);
  final rows = <Map<String, dynamic>>[];
  for (final line in lines.skip(1)) {
    final values = _splitLine(line, sep);
    final row = <String, dynamic>{};
    for (var i = 0; i < columns.length; i++) {
      final key = columns[i].trim();
      if (key.isEmpty) continue;
      row[key] = i < values.length ? values[i] : '';
    }
    if (row.values.any((v) => '$v'.trim().isNotEmpty)) rows.add(row);
  }
  return rows;
}

/// Importação de planilha de CNPJs por **colagem**.
///
/// O usuário copia as linhas do Excel/Sheets (com o cabeçalho) e cola aqui. O
/// parsing é feito em Dart puro — sem dependência nativa de leitura de arquivo,
/// que exigiria configuração por plataforma e não poderia ser validada nos
/// builds Android/iOS deste repositório sem risco.
///
/// O mapeamento de cabeçalhos (português com/sem acento e inglês) e toda a
/// validação continuam no backend: aqui só transformamos texto em linhas.
class PasteImportDialog extends StatefulWidget {
  const PasteImportDialog({super.key});

  @override
  State<PasteImportDialog> createState() => _PasteImportDialogState();
}

class _PasteImportDialogState extends State<PasteImportDialog> {
  final _text = TextEditingController();
  bool _submitting = false;
  String? _summary;

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    final rows = parsePastedTable(_text.text);
    if (rows.isEmpty) return;
    setState(() => _submitting = true);
    final cubit = context.read<LegalEntitiesCubit>();
    final result = await cubit.importRows(rows);
    if (!mounted) return;

    final created = (result['created_ids'] as List?)?.length ?? 0;
    final updated = (result['updated_ids'] as List?)?.length ?? 0;
    final errors = (result['errors'] as List?) ?? const [];
    setState(() {
      _submitting = false;
      // Erros vêm por linha (1-based, como na planilha) para o operador
      // corrigir só o que falhou e reenviar.
      _summary = [
        '+$created / ~$updated',
        if (errors.isNotEmpty)
          errors
              .map((e) => 'linha ${(e as Map)['row']}: ${e['error']}')
              .join('\n'),
      ].join('\n');
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.legalEntitiesImport),
      content: SizedBox(
        width: 520,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l10n.legalEntitiesImportHint),
              const SizedBox(height: EpiSpacing.md),
              TextField(
                controller: _text,
                minLines: 6,
                maxLines: 12,
                decoration: InputDecoration(
                  border: const OutlineInputBorder(),
                  hintText: l10n.legalEntitiesImportColumnsHint,
                ),
              ),
              if (_summary != null) ...[
                const SizedBox(height: EpiSpacing.md),
                Text(
                  '${l10n.legalEntitiesImportResult}\n${_summary!}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(true),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: Text(l10n.legalEntitiesImport),
        ),
      ],
    );
  }
}
