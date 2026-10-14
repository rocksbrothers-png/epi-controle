import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/safety_library/library_viewer.dart';
import 'package:epi_admin/features/safety_library/portal_library_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  final fixturePath = Platform.environment['PORTAL_DOCS_HTTP_FIXTURE'];
  if (fixturePath == null) {
    TestWidgetsFlutterBinding.ensureInitialized();
    test('requires an explicitly isolated PostgreSQL HTTP fixture', () {},
        skip: 'Run Portal Docs V1 workflow or set PORTAL_DOCS_HTTP_FIXTURE');
    return;
  }
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  final fixture =
      jsonDecode(File(fixturePath).readAsStringSync()) as Map<String, dynamic>;
  final token = fixture['tenant']['tokens'][0] as String;
  final foreign = fixture['foreign']['tokens'][0] as String;
  final versions = (fixture['versions'] as List).cast<Map<String, dynamic>>();
  final capture = GlobalKey();
  setUpAll(() async {
    final font = Platform.environment['PORTAL_DOCS_TEST_FONT'];
    if (font != null) {
      final loader = FontLoader('AcceptanceFont')
        ..addFont(
            Future.value(ByteData.sublistView(File(font).readAsBytesSync())));
      await loader.load();
    }
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => call.method == 'readAll' ? <String, String>{} : null,
    );
    ApiClient.init(baseUrl: fixture['base_url'] as String);
  });
  Future<void> render(
    WidgetTester tester,
    Widget widget,
    Size size,
    TargetPlatform platform,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = size;
    await tester.pumpWidget(
      RepaintBoundary(
        key: capture,
        child: MaterialApp(
          key: UniqueKey(),
          locale: const Locale('pt', 'BR'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          theme: ThemeData(
              platform: platform,
              fontFamily: Platform.environment['PORTAL_DOCS_TEST_FONT'] == null
                  ? null
                  : 'AcceptanceFont'),
          home: widget,
        ),
      ),
    );
  }

  Future<void> until(WidgetTester tester, bool Function() condition) async {
    final deadline = DateTime.now().add(const Duration(seconds: 30));
    while (!condition() && DateTime.now().isBefore(deadline)) {
      await tester.pump(const Duration(milliseconds: 100));
      await Future<void>.delayed(const Duration(milliseconds: 50));
    }
    expect(
      condition(),
      true,
      reason: 'Real HTTP widget did not reach expected state',
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.takeException(), isNull);
  }

  Future<void> screenshot(WidgetTester tester, String name) async {
    final directory = Platform.environment['PORTAL_DOCS_SCREENSHOTS'];
    if (directory == null) return;
    await tester.pump(const Duration(milliseconds: 300));
    final boundary =
        capture.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 1);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    final path = File('$directory/$name.png');
    await path.parent.create(recursive: true);
    await path.writeAsBytes(bytes!.buffer.asUint8List());
    image.dispose();
  }

  List<int> imageBytes(WidgetTester tester) =>
      (tester.widget<Image>(find.byType(Image).first).image as MemoryImage)
          .bytes;
  for (final configuration in [
    ('desktop', const Size(1440, 1000), TargetPlatform.linux),
    ('android-layout', const Size(390, 844), TargetPlatform.android),
    ('ios-layout', const Size(390, 844), TargetPlatform.iOS),
  ]) {
    testWidgets(
        'real Office preview pages, sheets and zoom ${configuration.$1}', (
      tester,
    ) async {
      for (final doc in versions) {
        await render(
          tester,
          LibraryViewer(
            key: UniqueKey(),
            document: doc,
            token: token,
            cpfLast3: '123',
          ),
          configuration.$2,
          configuration.$3,
        );
        await until(tester, () => find.byType(Image).evaluate().isNotEmpty);
        expect(find.byType(InteractiveViewer), findsOneWidget);
        expect(find.byIcon(Icons.download), findsNothing);
        expect(find.byIcon(Icons.save), findsNothing);
        final first = List<int>.from(imageBytes(tester));
        await tester.tap(find.byIcon(Icons.zoom_in));
        await tester.pump();
        final view = tester.widget<InteractiveViewer>(
          find.byType(InteractiveViewer),
        );
        expect(view.transformationController!.value.getMaxScaleOnAxis(), 1.25);
        await screenshot(
          tester,
          '${configuration.$1}-${doc['title'].toString().split(' ').last}-zoom',
        );
        if (doc['title'].toString().endsWith('XLSX')) {
          await tester.tap(find.byType(DropdownButton<int>));
          await tester.pumpAndSettle();
          await tester.tap(find.text('ENG').last);
          await tester.pump();
          await until(
            tester,
            () =>
                find.byType(Image).evaluate().isNotEmpty &&
                !listEquals(imageBytes(tester), first),
          );
          expect(
            tester
                .widget<InteractiveViewer>(find.byType(InteractiveViewer))
                .transformationController!
                .value
                .getMaxScaleOnAxis(),
            1,
          );
          await screenshot(tester, '${configuration.$1}-XLSX-ENG');
        } else if (tester
                .widget<IconButton>(
                    find.widgetWithIcon(IconButton, Icons.chevron_right))
                .onPressed !=
            null) {
          await tester.tap(find.byIcon(Icons.chevron_right));
          await tester.pump();
          await until(
            tester,
            () =>
                find.byType(Image).evaluate().isNotEmpty &&
                !listEquals(imageBytes(tester), first),
          );
          expect(find.textContaining(RegExp(r'2 / \d+')), findsOneWidget);
          await screenshot(
            tester,
            '${configuration.$1}-${doc['title'].toString().split(' ').last}-page2',
          );
        }
      }
      await tester.pumpWidget(const SizedBox.shrink());
    });
  }
  for (final size in [const Size(1440, 1000), const Size(390, 844)]) {
    testWidgets('real approved catalogue, filters and library ${size.width}', (
      tester,
    ) async {
      await render(
        tester,
        Scaffold(
          body: PortalLibraryTab(
            key: UniqueKey(),
            token: token,
            cpfLast3: '123',
            approved: true,
          ),
        ),
        size,
        TargetPlatform.android,
      );
      await until(
        tester,
        () => find.text('Approved helmet 0').evaluate().isNotEmpty,
      );
      expect(
        find.byType(DataTable),
        size.width > 900 ? findsOneWidget : findsNothing,
      );
      await screenshot(tester, 'catalogue-${size.width.toInt()}');
      await tester.enterText(find.byType(TextField).first, 'no such EPI');
      await tester.pump();
      expect(find.text('Approved helmet 0'), findsNothing);
      await tester.enterText(find.byType(TextField).first, 'helmet');
      await tester.pump();
      expect(find.text('Approved helmet 0'), findsWidgets);
      final detail = size.width > 900
          ? find.text('Ver EPI').first
          : find.text('Approved helmet 0');
      await tester.ensureVisible(detail);
      await tester.tap(detail);
      await until(tester, () => find.byType(AlertDialog).evaluate().isNotEmpty);
      expect(
          find.descendant(
              of: find.byType(AlertDialog),
              matching: find.textContaining('Use correctly')),
          findsOneWidget);
      expect(find.text('Fixture isolada DOCX'), findsOneWidget);
      await screenshot(tester, 'epi-detail-${size.width.toInt()}');
      await tester.tap(find.text('Fechar'));
      await tester.pumpAndSettle();
      await render(
        tester,
        Scaffold(
          body: PortalLibraryTab(
            key: UniqueKey(),
            token: token,
            cpfLast3: '123',
          ),
        ),
        size,
        TargetPlatform.android,
      );
      await until(
        tester,
        () => find.text('Fixture isolada DOCX').evaluate().isNotEmpty,
      );
      await screenshot(tester, 'library-${size.width.toInt()}');
      for (final extension in ['XLSX', 'XLS', 'DOCX']) {
        await tester.enterText(find.byType(TextField).first, extension);
        await tester.pump();
        expect(find.text('Fixture isolada ' + extension), findsOneWidget);
      }
      await tester.tap(find.text('Fixture isolada DOCX'));
      await tester.pump();
      await until(tester, () => find.byType(Image).evaluate().isNotEmpty);
      expect(find.byType(LibraryViewer), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
    });
  }
  testWidgets('cross-tenant viewer receives denial and no rendered content', (
    tester,
  ) async {
    await render(
      tester,
      LibraryViewer(
        key: UniqueKey(),
        document: versions.first,
        token: foreign,
        cpfLast3: '123',
      ),
      const Size(390, 844),
      TargetPlatform.android,
    );
    await until(tester, () => find.textContaining('403').evaluate().isNotEmpty);
    expect(find.byType(Image), findsNothing);
    expect(find.byType(InteractiveViewer), findsNothing);
    await screenshot(tester, 'cross-tenant-denied');
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
