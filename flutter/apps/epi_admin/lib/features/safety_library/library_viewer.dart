import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';

class LibraryViewer extends StatefulWidget {
  const LibraryViewer({
    super.key,
    required this.document,
    this.token,
    this.cpfLast3,
  });
  final Map<String, dynamic> document;
  final String? token;
  final String? cpfLast3;
  @override
  State<LibraryViewer> createState() => _LibraryViewerState();
}

class _LibraryViewerState extends State<LibraryViewer> {
  Map<String, dynamic>? _manifest;
  Uint8List? _bytes;
  String? _error;
  int _part = 0, _page = 0, _generation = 0;
  final _transform = TransformationController();
  Map<String, dynamic> get _identity => {
    'document_id': widget.document['document_id'],
    'version_id': widget.document['id'],
  };
  @override
  void initState() {
    super.initState();
    _loadManifest();
  }

  @override
  void dispose() {
    _generation++;
    _transform.dispose();
    super.dispose();
  }

  Future<void> _loadManifest() async {
    try {
      final res = await ApiClient.safetyLibrary.request(
        'manifest',
        data: _identity,
        token: widget.token,
        cpfLast3: widget.cpfLast3,
      );
      if (!mounted) return;
      setState(
        () => _manifest = Map<String, dynamic>.from(res['preview'] as Map),
      );
      await _loadPage();
    } on Exception catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _loadPage() async {
    final generation = ++_generation;
    setState(() {
      _bytes = null;
      _error = null;
    });
    _transform.value = Matrix4.identity();
    try {
      final bytes = await ApiClient.safetyLibrary.page(
        data: {..._identity, 'part_index': _part, 'page_index': _page},
        token: widget.token,
        cpfLast3: widget.cpfLast3,
      );
      if (mounted && generation == _generation) setState(() => _bytes = bytes);
    } on Exception catch (e) {
      if (mounted && generation == _generation) {
        setState(() => _error = e.toString());
      }
    }
  }

  void _zoom(double factor) {
    final current = _transform.value.getMaxScaleOnAxis();
    final target = (current * factor).clamp(.5, 5.0);
    _transform.value = Matrix4.copy(_transform.value)
      ..scaleByDouble(target / current, target / current, 1, 1);
  }

  @override
  Widget build(BuildContext context) {
    final parts = (_manifest?['parts'] as List?) ?? [];
    final pages = parts.isEmpty ? [] : (parts[_part]['pages'] as List);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.document['title'] as String? ?? 'Documento'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(
              'Versão ${widget.document['version_label']} · Vigência ${widget.document['effective_date']}',
            ),
          ),
          for (final warning in (_manifest?['warnings'] as List?) ?? [])
            Padding(padding: const EdgeInsets.all(8), child: Text('$warning')),
          if (parts.isNotEmpty)
            Wrap(
              spacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                DropdownButton<int>(
                  value: _part,
                  items: [
                    for (final p in parts)
                      DropdownMenuItem(
                        value: p['index'] as int,
                        child: Text(p['name'] as String),
                      ),
                  ],
                  onChanged: (p) {
                    if (p != null) {
                      setState(() {
                        _part = p;
                        _page = 0;
                      });
                      _loadPage();
                    }
                  },
                ),
                IconButton(
                  tooltip: 'Página anterior',
                  icon: const Icon(Icons.chevron_left),
                  onPressed: _page > 0
                      ? () {
                          setState(() => _page--);
                          _loadPage();
                        }
                      : null,
                ),
                Text('${_page + 1} / ${pages.length}'),
                IconButton(
                  tooltip: 'Próxima página',
                  icon: const Icon(Icons.chevron_right),
                  onPressed: _page < pages.length - 1
                      ? () {
                          setState(() => _page++);
                          _loadPage();
                        }
                      : null,
                ),
                IconButton(
                  tooltip: 'Diminuir zoom',
                  icon: const Icon(Icons.zoom_out),
                  onPressed: () => _zoom(.8),
                ),
                IconButton(
                  tooltip: 'Aumentar zoom',
                  icon: const Icon(Icons.zoom_in),
                  onPressed: () => _zoom(1.25),
                ),
                TextButton(
                  onPressed: () => _transform.value = Matrix4.identity(),
                  child: const Text('Ajustar'),
                ),
              ],
            ),
          Expanded(
            child: _error != null
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Pré-visualização indisponível: $_error'),
                        TextButton(
                          onPressed: _manifest == null
                              ? _loadManifest
                              : _loadPage,
                          child: const Text('Tentar novamente'),
                        ),
                      ],
                    ),
                  )
                : _bytes == null
                ? const Center(child: CircularProgressIndicator())
                : InteractiveViewer(
                    transformationController: _transform,
                    minScale: .5,
                    maxScale: 5,
                    child: Center(
                      child: Image.memory(
                        _bytes!,
                        fit: BoxFit.contain,
                        gaplessPlayback: false,
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
