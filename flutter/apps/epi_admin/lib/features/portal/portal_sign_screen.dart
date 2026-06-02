import 'dart:convert';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:signature/signature.dart';
import '../../core/bloc/portal_cubit.dart';

class PortalSignScreen extends StatefulWidget {
  const PortalSignScreen({
    super.key,
    required this.title,
    required this.onSign,
  });

  final String title;
  final Future<void> Function(String signatureData) onSign;

  @override
  State<PortalSignScreen> createState() => _PortalSignScreenState();
}

class _PortalSignScreenState extends State<PortalSignScreen> {
  late final SignatureController _controller;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    _controller = SignatureController(
      penStrokeWidth: 2.5,
      penColor: EpiColors.textPrimary,
      exportBackgroundColor: Colors.white,
    );
    _controller.addListener(_onDraw);
  }

  void _onDraw() {
    if (_controller.isNotEmpty && !_dirty) {
      setState(() => _dirty = true);
    }
  }

  @override
  void dispose() {
    _controller.removeListener(_onDraw);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final isSaving = context.select((PortalCubit c) => c.state.isSaving);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        actions: [
          if (_dirty)
            TextButton(
              onPressed: () {
                _controller.clear();
                setState(() => _dirty = false);
              },
              child: Text(l10n.deliveryClearSignature),
            ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              EpiSpacing.lg,
              EpiSpacing.lg,
              EpiSpacing.lg,
              EpiSpacing.sm,
            ),
            child: Text(
              l10n.portalSignatureInstruction,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: EpiColors.textMuted),
              textAlign: TextAlign.center,
            ),
          ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
              decoration: BoxDecoration(
                border: Border.all(
                  color: _dirty ? EpiColors.brand : EpiColors.border,
                  width: _dirty ? 2 : 1,
                ),
                borderRadius: BorderRadius.circular(EpiRadius.md),
                color: Colors.white,
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(EpiRadius.md),
                child: Signature(
                  controller: _controller,
                  backgroundColor: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              EpiSpacing.lg,
              0,
              EpiSpacing.lg,
              EpiSpacing.xl,
            ),
            child: EpiButton(
              label: l10n.portalSignature,
              loading: isSaving,
              fullWidth: true,
              icon: Icons.check_rounded,
              onPressed: (_dirty && !isSaving) ? () => _submit(context) : null,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit(BuildContext context) async {
    final bytes = await _controller.toPngBytes();
    if (bytes == null) return;
    final signatureData = base64Encode(bytes);
    await widget.onSign(signatureData);
    if (context.mounted) Navigator.of(context).pop();
  }
}
