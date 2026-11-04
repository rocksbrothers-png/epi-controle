import 'dart:async';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/qr/qr_scanner_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class ScannerPort extends MobileScannerPlatform {
  final captures = StreamController<BarcodeCapture?>.broadcast();
  int toggles = 0;
  @override
  Stream<BarcodeCapture?> get barcodesStream => captures.stream;
  @override
  Stream<TorchState> get torchStateStream => const Stream.empty();
  @override
  Stream<double> get zoomScaleStateStream => const Stream.empty();
  @override
  Widget buildCameraView() => const ColoredBox(color: Colors.black);
  @override
  Future<MobileScannerViewAttributes> start(StartOptions options) async =>
      const MobileScannerViewAttributes(
        cameraDirection: CameraFacing.back,
        currentTorchMode: TorchState.off,
        size: Size(640, 480),
        numberOfCameras: 1,
      );
  @override
  Future<void> toggleTorch() async {
    toggles++;
  }

  @override
  Future<void> stop() async {}
  @override
  Future<void> pause() async {}
  @override
  Future<void> dispose() async {}
  @override
  Future<void> updateScanWindow(Rect? window) async {}
}

Future<void> settle(WidgetTester t) async {
  await t.pump(const Duration(milliseconds: 100));
  await t.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 30)),
  );
  await t.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const locales = [
    Locale('pt', 'BR'),
    Locale('en', 'US'),
    Locale('es', 'ES'),
    Locale('fr', 'FR'),
    Locale('no', 'NO'),
  ];
  for (var i = 0; i < locales.length; i++) {
    final target = locales[i];
    testWidgets(
      'QR ${target.toLanguageTag()} translates open result and preserves opaque code and picker',
      (t) async {
        final previous = MobileScannerPlatform.instance;
        final port = ScannerPort();
        MobileScannerPlatform.instance = port;
        addTearDown(() async {
          MobileScannerPlatform.instance = previous;
          await port.captures.close();
        });
        final locale = ValueNotifier(target);
        addTearDown(locale.dispose);
        String? picked;
        await t.runAsync(() => AppLocalizations.delegate.load(target));
        await t.pumpWidget(
          ValueListenableBuilder<Locale>(
            valueListenable: locale,
            builder: (context, loc, _) => MaterialApp(
              theme: EpiTheme.light,
              locale: loc,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              home: Scaffold(
                body: Builder(
                  builder: (context) => TextButton(
                    key: const Key('open-picker'),
                    onPressed: () async {
                      picked = await Navigator.of(context).push<String>(
                        MaterialPageRoute(
                          builder: (_) =>
                              const QrScannerScreen(returnResult: true),
                        ),
                      );
                    },
                    child: const Text('Synthetic launcher'),
                  ),
                ),
              ),
            ),
          ),
        );
        await settle(t);
        final nav = Navigator.of(
          t.element(find.byKey(const Key('open-picker'))),
        );
        nav.push(
          MaterialPageRoute<void>(builder: (_) => const QrScannerScreen()),
        );
        await settle(t);
        var l = (await t.runAsync(
          () => AppLocalizations.delegate.load(locale.value),
        ))!;
        expect(find.text(l.qrInstruction), findsOneWidget);
        await t.tap(find.byTooltip(l.qrTorchOn));
        await settle(t);
        expect(port.toggles, 1);
        expect(find.byTooltip(l.qrTorchOff), findsOneWidget);
        const code = '00041://literal?x=<keep>&name={value}';
        const capture = BarcodeCapture(
          barcodes: [Barcode(rawValue: code)],
        );
        var camera = t.widget<MobileScanner>(find.byType(MobileScanner));
        camera.onDetect!(capture);
        await settle(t);
        expect(find.text(l.qrDetected), findsOneWidget);
        expect(find.text(code), findsOneWidget);
        camera.onDetect!(capture);
        await settle(t);
        expect(find.text(code), findsOneWidget);
        locale.value = locales[(i + 1) % locales.length];
        await settle(t);
        l = (await t.runAsync(
          () => AppLocalizations.delegate.load(locale.value),
        ))!;
        expect(find.text(l.qrDetected), findsOneWidget);
        expect(find.text(l.qrScanAgain), findsOneWidget);
        expect(find.text(code), findsOneWidget);
        await t.tap(find.text(l.qrScanAgain));
        await settle(t);
        expect(find.text(code), findsNothing);
        camera = t.widget<MobileScanner>(find.byType(MobileScanner));
        camera.onDetect!(capture);
        await settle(t);
        expect(find.text(code), findsOneWidget);
        await t.tap(find.text(l.close));
        await settle(t);
        nav.pop();
        await settle(t);
        await t.tap(find.byKey(const Key('open-picker')));
        await settle(t);
        t.widget<MobileScanner>(find.byType(MobileScanner)).onDetect!(capture);
        await settle(t);
        expect(picked, code);
        expect(find.byType(QrScannerScreen), findsNothing);
        expect(t.takeException(), isNull);
        await t.pumpWidget(const SizedBox());
      },
    );
  }
}
