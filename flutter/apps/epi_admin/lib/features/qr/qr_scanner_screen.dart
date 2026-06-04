import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class QrScannerScreen extends StatefulWidget {
  const QrScannerScreen({super.key});

  @override
  State<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends State<QrScannerScreen> {
  late final MobileScannerController _controller;
  bool _scanned = false;
  bool _torchOn = false;

  @override
  void initState() {
    super.initState();
    _controller = MobileScannerController(
      detectionSpeed: DetectionSpeed.noDuplicates,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(l10n.stockScan),
        actions: [
          IconButton(
            icon: Icon(_torchOn ? Icons.flash_on_rounded : Icons.flash_off_rounded),
            color: _torchOn ? Colors.amber : Colors.white,
            onPressed: () {
              setState(() => _torchOn = !_torchOn);
              _controller.toggleTorch();
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          const _ScanOverlay(),
          Positioned(
            bottom: 48,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                'Aponte para um código QR ou de barras',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white,
                    ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _onDetect(BarcodeCapture capture) {
    if (_scanned) return;
    final barcode = capture.barcodes.firstOrNull;
    if (barcode?.rawValue == null) return;
    setState(() => _scanned = true);
    _showResult(context, barcode!.rawValue!);
  }

  void _showResult(BuildContext context, String value) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(EpiRadius.lg)),
      ),
      builder: (_) => _ScanResultSheet(
        value: value,
        onScanAgain: () {
          Navigator.pop(context);
          setState(() => _scanned = false);
        },
      ),
    );
  }
}

class _ScanOverlay extends StatelessWidget {
  const _ScanOverlay();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _OverlayPainter(),
      child: const SizedBox.expand(),
    );
  }
}

class _OverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const frameSize = 240.0;
    final cx = size.width / 2;
    final cy = size.height / 2;
    final left = cx - frameSize / 2;
    final top = cy - frameSize / 2;
    final frameRect = Rect.fromLTWH(left, top, frameSize, frameSize);

    // Dark overlay
    final path = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height))
      ..addRRect(RRect.fromRectAndRadius(frameRect, const Radius.circular(16)))
      ..fillType = PathFillType.evenOdd;
    canvas.drawPath(
      path,
      Paint()..color = Colors.black.withValues(alpha: 0.6),
    );

    // Frame border
    const cornerLen = 24.0;
    final borderPaint = Paint()
      ..color = EpiColors.brand
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Corners
    void drawCorner(double x, double y, double dx, double dy) {
      canvas.drawLine(Offset(x, y + dy), Offset(x, y), borderPaint);
      canvas.drawLine(Offset(x, y), Offset(x + dx, y), borderPaint);
    }

    drawCorner(left, top, cornerLen, cornerLen);
    drawCorner(left + frameSize, top, -cornerLen, cornerLen);
    drawCorner(left, top + frameSize, cornerLen, -cornerLen);
    drawCorner(left + frameSize, top + frameSize, -cornerLen, -cornerLen);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ScanResultSheet extends StatelessWidget {
  const _ScanResultSheet({required this.value, required this.onScanAgain});
  final String value;
  final VoidCallback onScanAgain;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(EpiSpacing.xl2),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Center(
            child: Icon(
              Icons.check_circle_outline_rounded,
              size: 56,
              color: EpiColors.success,
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          Center(
            child: Text(
              'Código detectado',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          Container(
            padding: const EdgeInsets.all(EpiSpacing.md),
            decoration: BoxDecoration(
              color: EpiColors.surface,
              borderRadius: BorderRadius.circular(EpiRadius.sm),
              border: Border.all(color: EpiColors.border),
            ),
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontFamily: 'monospace',
                  ),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: EpiSpacing.xl2),
          EpiButton(
            label: 'Escanear novamente',
            onPressed: onScanAgain,
            variant: EpiButtonVariant.ghost,
            fullWidth: true,
          ),
          const SizedBox(height: EpiSpacing.md),
          EpiButton(
            label: 'Fechar',
            onPressed: () => Navigator.pop(context),
            fullWidth: true,
          ),
          const SizedBox(height: EpiSpacing.lg),
        ],
      ),
    );
  }
}
