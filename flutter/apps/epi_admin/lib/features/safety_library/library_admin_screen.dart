import 'dart:convert';
import 'dart:math';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
import 'library_viewer.dart';

class LibraryAdminScreen extends StatefulWidget {
  const LibraryAdminScreen({super.key});
  @override
  State<LibraryAdminScreen> createState() => _LibraryAdminScreenState();
}

class _LibraryAdminScreenState extends State<LibraryAdminScreen> {
  List<Map<String, dynamic>>? _versions;
  Map<String, dynamic>? _options;
  String? _error;
  String _query = '', _category = '';
  bool _busy = false;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await Future.wait([
        ApiClient.safetyLibrary.request('documents'),
        ApiClient.safetyLibrary.request('options'),
      ]);
      if (mounted) {
        setState(() {
          _versions = (res[0]['items'] as List)
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
          _options = res[1];
          _error = null;
        });
      }
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<String?> _reason(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          maxLength: 2000,
          decoration: const InputDecoration(
            labelText: 'Justificativa obrigatória',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancelar'),
          ),
          TextButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                Navigator.pop(ctx, controller.text.trim());
              }
            },
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _action(String action, Map<String, dynamic> version) async {
    if (action == 'preview') {
      await Navigator.push(
        context,
        MaterialPageRoute<void>(
          builder: (_) => LibraryViewer(document: version),
        ),
      );
      return;
    }
    try {
      if (action == 'history') {
        final res = await ApiClient.safetyLibrary.request(
          'history',
          data: {'document_id': version['document_id']},
        );
        if (!mounted) return;
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Histórico documental'),
            content: SizedBox(
              width: 700,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    for (final e in res['items'] as List)
                      ListTile(
                        title: Text('${e['action']} · ${e['created_at']}'),
                        subtitle: Text(
                          'Ator ${e['actor_user_id'] ?? e['employee_id'] ?? ''}\n${e['details']}',
                        ),
                      ),
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
        return;
      }
      final reason = await _reason(
        action == 'publish'
            ? 'Publicar versão'
            : 'Arquivar documento e versões',
      );
      if (reason == null) return;
      await ApiClient.safetyLibrary.request(
        action,
        data: {
          'document_id': version['document_id'],
          'version_id': version['id'],
          'justification': reason,
        },
      );
      await _load();
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _upload() async {
    final metadata = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _DocumentForm(options: _options!, versions: _versions!),
    );
    if (metadata == null) return;
    final file = await openFile(
      acceptedTypeGroups: [
        const XTypeGroup(
          label: 'Documentos de SST',
          extensions: ['pdf', 'docx', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'],
          uniformTypeIdentifiers: [
            'com.adobe.pdf',
            'org.openxmlformats.wordprocessingml.document',
            'org.openxmlformats.spreadsheetml.sheet',
            'com.microsoft.excel.xls',
            'public.png',
            'public.jpeg',
          ],
          mimeTypes: [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'image/png',
            'image/jpeg',
          ],
        ),
      ],
    );
    if (file == null || !mounted) return;
    if (await file.length() > 20 * 1024 * 1024) {
      if (mounted)
        setState(() => _error = 'Selecione um arquivo de até 20 MiB.');
      return;
    }
    final bytes = await file.readAsBytes();
    if (!mounted) return;
    const mimes = {
      'pdf': 'application/pdf',
      'docx':
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xlsx':
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'xls': 'application/vnd.ms-excel',
      'png': 'image/png',
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
    };
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final random = Random.secure();
      final key = List.generate(
        24,
        (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
      ).join();
      await ApiClient.safetyLibrary.request(
        'upload',
        data: {
          ...metadata,
          'filename': file.name,
          'mime': mimes[file.name.split('.').last.toLowerCase()],
          'content_base64': base64Encode(bytes),
          'idempotency_key': key,
        },
      );
      await _load();
    } on Exception catch (e) {
      if (mounted) {
        setState(
          () => _error = 'Cadastro recusado; pré-visualização indisponível: $e',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_options == null) {
      return Center(
        child: _error == null
            ? const CircularProgressIndicator()
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!),
                  TextButton(
                    onPressed: _load,
                    child: const Text('Tentar novamente'),
                  ),
                ],
              ),
      );
    }
    final versions = _versions!.where(
      (d) =>
          ('${d['title']} ${d['version_label']}').toLowerCase().contains(
            _query,
          ) &&
          (_category.isEmpty || d['category'] == _category),
    );
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Biblioteca de Segurança',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        const Text(
          'Originais privados; versões e histórico preservados. Gestão restrita ao Administrador Geral e ao Administrador de Registro.',
        ),
        if (_error != null)
          Text(_error!, style: const TextStyle(color: Colors.red)),
        FilledButton.icon(
          onPressed: _busy ? null : _upload,
          icon: const Icon(Icons.upload_file),
          label: Text(
            _busy
                ? 'Gerando pré-visualização segura…'
                : 'Cadastrar ou versionar documento',
          ),
        ),
        SwitchListTile(
          title: const Text(
            'Permitir download de originais aos administradores autorizados',
          ),
          subtitle: const Text(
            'Colaboradores sempre consultam somente a pré-visualização.',
          ),
          value: _options!['allow_admin_original_download'] == true,
          onChanged: (allowed) async {
            final reason = await _reason(
              'Alterar política de download administrativo',
            );
            if (reason == null) return;
            try {
              await ApiClient.safetyLibrary.request(
                'policy',
                data: {
                  'allow_admin_original_download': allowed,
                  'justification': reason,
                },
              );
              await _load();
            } on Exception catch (e) {
              if (mounted) setState(() => _error = e.toString());
            }
          },
        ),
        TextField(
          decoration: const InputDecoration(
            labelText: 'Pesquisar título ou versão',
          ),
          onChanged: (v) => setState(() => _query = v.toLowerCase()),
        ),
        DropdownButton<String>(
          isExpanded: true,
          value: _category,
          items: [
            const DropdownMenuItem(
              value: '',
              child: Text('Todas as categorias'),
            ),
            for (final e in (_options!['categories'] as Map).entries)
              DropdownMenuItem(value: '${e.key}', child: Text('${e.value}')),
          ],
          onChanged: (v) => setState(() => _category = v ?? ''),
        ),
        for (final d in versions)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${d['title']}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    '${d['category_label']}\nVersão ${d['version_label']} / revisão ${d['revision']} · ${d['state_label']} · Vigência ${d['effective_date']}',
                  ),
                  Wrap(
                    children: [
                      TextButton(
                        onPressed: () => _action('preview', d),
                        child: const Text('Visualizar'),
                      ),
                      if (d['state'] == 'draft')
                        TextButton(
                          onPressed: () => _action('publish', d),
                          child: const Text('Publicar'),
                        ),
                      if (d['state'] != 'archived')
                        TextButton(
                          onPressed: () => _action('archive', d),
                          child: const Text('Arquivar documento'),
                        ),
                      TextButton(
                        onPressed: () => _action('history', d),
                        child: const Text('Histórico'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        if (_versions!.isEmpty) const Text('Nenhum documento cadastrado.'),
      ],
    );
  }
}

class _DocumentForm extends StatefulWidget {
  const _DocumentForm({required this.options, required this.versions});
  final Map<String, dynamic> options;
  final List<Map<String, dynamic>> versions;
  @override
  State<_DocumentForm> createState() => _DocumentFormState();
}

class _DocumentFormState extends State<_DocumentForm> {
  final _key = GlobalKey<FormState>();
  final _title = TextEditingController(),
      _version = TextEditingController(),
      _date = TextEditingController(),
      _sectors = TextEditingController(),
      _activities = TextEditingController();
  String _category = 'other_sst';
  int? _documentId;
  bool _all = false;
  final Set<int> _units = {}, _epis = {};
  @override
  void dispose() {
    for (final c in [_title, _version, _date, _sectors, _activities]) {
      c.dispose();
    }
    super.dispose();
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    bool required = true,
  }) => TextFormField(
    controller: controller,
    decoration: InputDecoration(labelText: label),
    validator: required
        ? (v) => v == null || v.trim().isEmpty ? 'Obrigatório' : null
        : null,
  );
  @override
  Widget build(BuildContext context) {
    final docs = {
      for (final v in widget.versions.where((v) => v['state'] != 'archived'))
        v['document_id']: v,
    };
    return AlertDialog(
      title: const Text('Metadados da versão'),
      content: SizedBox(
        width: 650,
        child: SingleChildScrollView(
          child: Form(
            key: _key,
            child: Column(
              children: [
                DropdownButton<int>(
                  isExpanded: true,
                  value: _documentId,
                  hint: const Text('Novo documento'),
                  items: [
                    for (final e in docs.entries)
                      DropdownMenuItem(
                        value: e.key as int,
                        child: Text('${e.value['title']}'),
                      ),
                  ],
                  onChanged: (v) => setState(() => _documentId = v),
                ),
                if (_documentId != null)
                  TextButton(
                    onPressed: () => setState(() => _documentId = null),
                    child: const Text('Criar novo documento'),
                  ),
                _field(_title, 'Título'),
                _field(_version, 'Versão'),
                _field(_date, 'Vigência (AAAA-MM-DD)'),
                DropdownButton<String>(
                  isExpanded: true,
                  value: _category,
                  items: [
                    for (final e
                        in (widget.options['categories'] as Map).entries)
                      DropdownMenuItem(
                        value: '${e.key}',
                        child: Text('${e.value}'),
                      ),
                  ],
                  onChanged: (v) => setState(() => _category = v!),
                ),
                SwitchListTile(
                  title: const Text('Todas as unidades da empresa'),
                  value: _all,
                  onChanged: (v) => setState(() => _all = v),
                ),
                if (!_all) ...[
                  const Text('Selecione ao menos uma unidade'),
                  for (final unit in widget.options['units'] as List)
                    CheckboxListTile(
                      title: Text('${unit['name']}'),
                      value: _units.contains(unit['id']),
                      onChanged: (v) => setState(
                        () => v == true
                            ? _units.add(unit['id'] as int)
                            : _units.remove(unit['id']),
                      ),
                    ),
                ],
                const Text('EPIs relacionados'),
                for (final epi in widget.options['epis'] as List)
                  CheckboxListTile(
                    title: Text('${epi['name']}'),
                    value: _epis.contains(epi['id']),
                    onChanged: (v) => setState(
                      () => v == true
                          ? _epis.add(epi['id'] as int)
                          : _epis.remove(epi['id']),
                    ),
                  ),
                _field(
                  _sectors,
                  'Setores separados por vírgula (vazio = todos)',
                  required: false,
                ),
                _field(
                  _activities,
                  'Atividades/funções separadas por vírgula (vazio = todas)',
                  required: false,
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () {
            if (!_key.currentState!.validate() || (!_all && _units.isEmpty)) {
              return;
            }
            Navigator.pop(context, <String, dynamic>{
              if (_documentId != null) 'document_id': _documentId,
              'title': _title.text.trim(),
              'version_label': _version.text.trim(),
              'effective_date': _date.text.trim(),
              'category': _category,
              'all_units': _all,
              'unit_ids': _all ? <int>[] : _units.toList(),
              'epi_ids': _epis.toList(),
              'sectors': _sectors.text
                  .split(',')
                  .map((v) => v.trim())
                  .where((v) => v.isNotEmpty)
                  .toList(),
              'activities': _activities.text
                  .split(',')
                  .map((v) => v.trim())
                  .where((v) => v.isNotEmpty)
                  .toList(),
            });
          },
          child: const Text('Selecionar arquivo'),
        ),
      ],
    );
  }
}
