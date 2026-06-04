// Área de assinatura touch com exportação PNG e botões de limpar/confirmar.
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../atoms/epi_button.dart';

class EpiSignaturePad extends StatefulWidget {
  const EpiSignaturePad({
    super.key,
    required this.onSigned,
    this.onClear,
    this.height = 200,
  });

  final ValueChanged<Uint8List> onSigned;
  final VoidCallback?           onClear;
  final double                  height;

  @override
  State<EpiSignaturePad> createState() => _EpiSignaturePadState();
}

class _EpiSignaturePadState extends State<EpiSignaturePad> {
  final List<List<Offset>> _strokes = [];
  List<Offset>?            _current;
  bool                     _hasSig  = false;

  void _onPanStart(DragStartDetails d) {
    setState(() {
      _current = [d.localPosition];
      _strokes.add(_current!);
      _hasSig = true;
    });
  }

  void _onPanUpdate(DragUpdateDetails d) {
    setState(() => _current?.add(d.localPosition));
  }

  void _onPanEnd(DragEndDetails _) => setState(() => _current = null);

  void _clear() {
    setState(() {
      _strokes.clear();
      _hasSig = false;
    });
    widget.onClear?.call();
  }

  Future<void> _confirm(BuildContext context, Size size) async {
    final recorder = ui.PictureRecorder();
    final canvas   = Canvas(recorder);

    // Background
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..color = Colors.white,
    );

    // Strokes
    final paint = Paint()
      ..color       = EpiColors.textPrimary
      ..strokeWidth = 2.0
      ..strokeCap   = StrokeCap.round
      ..strokeJoin  = StrokeJoin.round
      ..style       = PaintingStyle.stroke;

    for (final stroke in _strokes) {
      if (stroke.isEmpty) continue;
      final path = Path()..moveTo(stroke.first.dx, stroke.first.dy);
      for (final pt in stroke.skip(1)) {
        path.lineTo(pt.dx, pt.dy);
      }
      canvas.drawPath(path, paint);
    }

    final picture = recorder.endRecording();
    final image   = await picture.toImage(size.width.toInt(), size.height.toInt());
    final bytes   = await image.toByteData(format: ui.ImageByteFormat.png);
    if (bytes != null) {
      widget.onSigned(bytes.buffer.asUint8List());
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final borderColor = _hasSig
        ? (isDark ? EpiColors.darkBorder : EpiColors.border)
        : EpiColors.brand.withValues(alpha: 0.4);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        LayoutBuilder(builder: (context, constraints) {
          final size = Size(constraints.maxWidth, widget.height);
          return GestureDetector(
            onPanStart:  _onPanStart,
            onPanUpdate: _onPanUpdate,
            onPanEnd:    _onPanEnd,
            child: Container(
              width:  size.width,
              height: size.height,
              decoration: BoxDecoration(
                color: isDark ? EpiColors.darkSurface : EpiColors.surface,
                borderRadius: BorderRadius.circular(EpiRadius.md),
                border: _hasSig
                    ? Border.all(color: borderColor)
                    : Border.all(
                        color: borderColor,
                        style: BorderStyle.solid,
                        strokeAlign: BorderSide.strokeAlignInside,
                      ),
              ),
              clipBehavior: Clip.antiAlias,
              child: Stack(
                children: [
                  CustomPaint(
                    size: size,
                    painter: _SignaturePainter(strokes: _strokes),
                  ),
                  if (!_hasSig)
                    Center(
                      child: Text(
                        'Assine aqui',
                        style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                              color: EpiColors.textMuted,
                            ),
                      ),
                    ),
                ],
              ),
            ),
          );
        }),
        const SizedBox(height: EpiSpacing.md),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            EpiButton(
              label: 'Limpar',
              onPressed: _hasSig ? _clear : null,
              variant: EpiButtonVariant.ghost,
              size: EpiButtonSize.sm,
            ),
            const SizedBox(width: EpiSpacing.sm),
            Builder(
              builder: (ctx) => EpiButton(
                label: 'Confirmar',
                onPressed: _hasSig
                    ? () {
                        final padBox = context.findRenderObject() as RenderBox?;
                        if (padBox != null) {
                          _confirm(
                            context,
                            Size(padBox.size.width, widget.height),
                          );
                        }
                      }
                    : null,
                variant: EpiButtonVariant.primary,
                size: EpiButtonSize.sm,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _SignaturePainter extends CustomPainter {
  const _SignaturePainter({required this.strokes});
  final List<List<Offset>> strokes;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color       = EpiColors.textPrimary
      ..strokeWidth = 2.0
      ..strokeCap   = StrokeCap.round
      ..strokeJoin  = StrokeJoin.round
      ..style       = PaintingStyle.stroke;

    for (final stroke in strokes) {
      if (stroke.isEmpty) continue;
      final path = Path()..moveTo(stroke.first.dx, stroke.first.dy);
      for (final pt in stroke.skip(1)) {
        path.lineTo(pt.dx, pt.dy);
      }
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(_SignaturePainter old) => old.strokes != strokes;
}
