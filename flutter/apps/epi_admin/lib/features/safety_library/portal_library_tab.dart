import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
import 'library_viewer.dart';

const epiLabels = <String, String>{
  'name': 'EPI',
  'manufacturer': 'Fabricante',
  'model_reference': 'Modelo/referência',
  'ca': 'CA',
  'ca_expiry': 'Validade do CA',
  'manufacturer_validity_months': 'Vida útil (meses)',
  'sector': 'Proteção',
  'epi_section': 'Seção',
  'manufacturer_recommendations': 'Recomendações/restrições',
};

class PortalLibraryTab extends StatefulWidget {
  const PortalLibraryTab({
    super.key,
    required this.token,
    required this.cpfLast3,
    this.approved = false,
  });
  final String token, cpfLast3;
  final bool approved;
  @override
  State<PortalLibraryTab> createState() => _PortalLibraryTabState();
}

class _PortalLibraryTabState extends State<PortalLibraryTab> {
  List<Map<String, dynamic>>? _items;
  List<Map<String, dynamic>> _epis = [];
  String _query = '',
      _category = '',
      _protection = '',
      _manufacturer = '',
      _section = '',
      _ca = '';
  int? _relatedEpi;
  String? _error;
  String _unitName = '';
  Future<void> _load() async {
    try {
      final results = await Future.wait([
        ApiClient.safetyLibrary.request(
          widget.approved ? 'approved-epis' : 'documents',
          token: widget.token,
          cpfLast3: widget.cpfLast3,
        ),
        ApiClient.safetyLibrary.request(
          'approved-epis',
          token: widget.token,
          cpfLast3: widget.cpfLast3,
        ),
      ]);
      if (mounted) {
        setState(() {
          _items = (results[0]['items'] as List)
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          _epis = (results[1]['items'] as List)
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          _error = null;
          _unitName =
              (results[0]['context'] as Map?)?['unit_name'] as String? ?? '';
        });
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _view(Map<String, dynamic> doc) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => LibraryViewer(
        document: doc,
        token: widget.token,
        cpfLast3: widget.cpfLast3,
      ),
    ),
  );
  Future<void> _detail(Map<String, dynamic> epi) async {
    List<Map<String, dynamic>> documents = [];
    Uint8List? photo;
    try {
      final res = await ApiClient.safetyLibrary.request(
        'documents',
        token: widget.token,
        cpfLast3: widget.cpfLast3,
      );
      documents = (res['items'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .where((d) => (d['epi_ids'] as List).contains(epi['id']))
          .toList();
      if (epi['has_photo'] == true) {
        photo = await ApiClient.safetyLibrary.page(
          action: 'photo',
          data: {'epi_id': epi['id']},
          token: widget.token,
          cpfLast3: widget.cpfLast3,
        );
      }
    } on Exception catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${epi['name']}'),
        content: SizedBox(
          width: 700,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final field in epiLabels.entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      '${field.value}: ${epi[field.key] ?? 'Não informado'}',
                    ),
                  ),
                if (photo != null)
                  SizedBox(
                    height: 240,
                    child: InteractiveViewer(child: Image.memory(photo)),
                  ),
                const Text('Documentos associados'),
                for (final d in documents)
                  ListTile(
                    title: Text('${d['title']}'),
                    subtitle: Text('Versão ${d['version_label']}'),
                    onTap: () => _view(d),
                  ),
                if (documents.isEmpty)
                  const Text('Nenhum documento publicado para este contexto.'),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Fechar'),
          ),
        ],
      ),
    );
  }

  Widget _filter(String label, ValueChanged<String> changed) => SizedBox(
    width: 210,
    child: TextField(
      decoration: InputDecoration(labelText: label),
      onChanged: (v) => setState(() => changed(v.toLowerCase())),
    ),
  );
  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            TextButton(onPressed: _load, child: const Text('Tentar novamente')),
          ],
        ),
      );
    }
    if (_items == null) return const Center(child: CircularProgressIndicator());
    final items = _items!.where((e) {
      final text = widget.approved
          ? '${e['name']}'
          : '${e['title']} ${e['version_label']} ${_epis.where((p) => (e['epi_ids'] as List).contains(p['id'])).map((p) => p['name']).join(' ')}';
      if (!text.toLowerCase().contains(_query)) return false;
      if (widget.approved) {
        return '${e['sector']}'.toLowerCase().contains(_protection) &&
            '${e['manufacturer']}'.toLowerCase().contains(_manufacturer) &&
            '${e['epi_section']}'.toLowerCase().contains(_section) &&
            '${e['ca']}'.toLowerCase().contains(_ca);
      }
      return (_category.isEmpty || e['category'] == _category) &&
          (_relatedEpi == null || (e['epi_ids'] as List).contains(_relatedEpi));
    }).toList();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          widget.approved ? 'EPIs Aprovados' : 'Biblioteca de Segurança',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        if (widget.approved)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'Aprovação cadastral; não indica disponibilidade física. Validade do CA não é validade de lote.',
            ),
          ),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: [
            _filter('Pesquisar', (v) => _query = v),
            Text('Unidade de consulta: $_unitName'),
            if (widget.approved) ...[
              _filter('Proteção', (v) => _protection = v),
              _filter('Fabricante', (v) => _manufacturer = v),
              _filter('Seção', (v) => _section = v),
              _filter('CA', (v) => _ca = v),
            ],
            if (!widget.approved) ...[
              DropdownButton<String>(
                value: _category,
                items: [
                  const DropdownMenuItem(
                    value: '',
                    child: Text('Todas as categorias'),
                  ),
                  for (final category
                      in _items!.map((e) => '${e['category']}').toSet())
                    DropdownMenuItem(
                      value: category,
                      child: Text(
                        '${_items!.firstWhere((e) => e['category'] == category)['category_label']}',
                      ),
                    ),
                ],
                onChanged: (v) => setState(() => _category = v ?? ''),
              ),
              DropdownButton<int>(
                value: _relatedEpi,
                hint: const Text('EPI relacionado'),
                items: [
                  for (final epi in _epis)
                    DropdownMenuItem(
                      value: epi['id'] as int,
                      child: Text('${epi['name']}'),
                    ),
                ],
                onChanged: (v) => setState(() => _relatedEpi = v),
              ),
              if (_relatedEpi != null)
                TextButton(
                  onPressed: () => setState(() => _relatedEpi = null),
                  child: const Text('Todos os EPIs'),
                ),
            ],
          ],
        ),
        const SizedBox(height: 16),
        if (items.isEmpty)
          const Text('Nenhum registro publicado e autorizado neste contexto.'),
        if (widget.approved && MediaQuery.sizeOf(context).width >= 900)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: [
                for (final label in epiLabels.values)
                  DataColumn(label: Text(label)),
                const DataColumn(label: Text('Detalhes')),
              ],
              rows: [
                for (final e in items)
                  DataRow(
                    cells: [
                      for (final key in epiLabels.keys)
                        DataCell(
                          SizedBox(
                            width: key == 'manufacturer_recommendations'
                                ? 240
                                : 140,
                            child: Text('${e[key] ?? 'Não informado'}'),
                          ),
                        ),
                      DataCell(
                        TextButton(
                          onPressed: () => _detail(e),
                          child: const Text('Ver EPI'),
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          )
        else
          for (final item in items)
            Card(
              child: ListTile(
                title: Text('${item[widget.approved ? 'name' : 'title']}'),
                subtitle: Text(
                  widget.approved
                      ? '${item['manufacturer'] ?? ''} · CA ${item['ca'] ?? ''}\n${item['sector'] ?? ''}'
                      : '${item['category_label']}\nVersão ${item['version_label']} · Vigência ${item['effective_date']}\n${_epis.where((p) => (item['epi_ids'] as List).contains(p['id'])).map((p) => p['name']).join(', ')}',
                ),
                trailing: const Icon(Icons.visibility_outlined),
                onTap: () => widget.approved ? _detail(item) : _view(item),
              ),
            ),
      ],
    );
  }
}
