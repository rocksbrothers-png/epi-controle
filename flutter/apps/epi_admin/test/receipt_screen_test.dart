import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_design/epi_design.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/bloc/auth_state.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/session/session_context.dart';
import 'package:epi_admin/features/purchases/conference_purchase_request_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

class _Auth extends AuthCubit {
  _Auth({bool permission = true}) {
    emit(AuthAuthenticated(token: 'fixture', user: const {},
      sessionContext: SessionContext(userId: 1, companyId: 2, unitId: 10,
        role: 'admin', permissions: permission ? ['purchase_requests:update'] : [],
        tenantName: '', companySettings: const {})));
  }
}

class _Transport implements HttpClientAdapter {
  Object? quantity = 2;
  int posts = 0;
  int status = 200;
  Map<String, dynamic> response = {'ok': true, 'stock_entries': 0, 'qr_labels': []};
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream,
      Future<void>? cancelFuture) async {
    if (options.method == 'POST') posts++;
    final data = options.method == 'POST' ? response : {
      'item': {'company_id': 2, 'unit_id': 10},
      'items': [{'id': 7, 'status': 'received', 'epi_name': 'Capacete',
        'quantity_requested': 99, 'effective_receive_quantity': quantity}],
    };
    return ResponseBody.fromString(jsonEncode(data), options.method == 'POST' ? status : 200,
      headers: {Headers.contentTypeHeader: ['application/json']});
  }
  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const camera = MethodChannel('plugins.flutter.io/image_picker');
  const storage = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  late _Transport transport;
  late _Auth auth;
  late ValueNotifier<bool> visible;

  setUpAll(() async => ApiClient.init(baseUrl: 'http://receipt.invalid'));
  setUp(() {
    transport = _Transport();
    ApiClient.debugDio.httpClientAdapter = transport;
    auth = _Auth();
    visible = ValueNotifier(true);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storage, (_) async => null);
  });
  tearDown(() async {
    await auth.close();
    visible.dispose();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(camera, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storage, null);
  });

  Future<void> open(WidgetTester tester) async {
    await tester.pumpWidget(BlocProvider<AuthCubit>.value(value: auth,
      child: MaterialApp(locale: const Locale('pt', 'BR'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(builder: (context) => Scaffold(body: TextButton(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => ValueListenableBuilder<bool>(valueListenable: visible,
              builder: (_, show, __) => show
                ? const ConferencePurchaseRequestScreen(prId: 5) : const SizedBox()))),
          child: const Text('Open')))))));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
  }

  for (final quantity in [0, null, -2, 'invalid']) {
    testWidgets('invalid effective $quantity blocks HTTP; never requested 99', (tester) async {
      transport.quantity = quantity;
      await open(tester);
      expect(find.text('Capacete  (0)'), findsOneWidget);
      expect(find.textContaining('quantidade efetivamente recebida inválida'), findsOneWidget);
      expect(tester.widget<EpiButton>(find.byType(EpiButton)).onPressed, isNull);
      expect(find.textContaining('Linha 1 — Capacete (item #7)'), findsOneWidget);
      await tester.tap(find.byType(Switch));
      await tester.pumpAndSettle();
      expect(tester.widget<EpiButton>(find.byType(EpiButton)).onPressed, isNull);
      await tester.pumpAndSettle();
      expect(transport.posts, 0);
    });
  }

  testWidgets('permission denial disables direct conference submission', (tester) async {
    await auth.close();
    auth = _Auth(permission: false);
    await open(tester);
    expect(tester.widget<EpiButton>(find.byType(EpiButton)).onPressed, isNull);
    await tester.pumpAndSettle();
    expect(transport.posts, 0);
  });

  testWidgets('received selection with no persisted pieces never announces success', (tester) async {
    await open(tester);
    await tester.ensureVisible(find.text('Registrar Conferência'));
    await tester.tap(find.text('Registrar Conferência'));
    await tester.pumpAndSettle();
    expect(transport.posts, 1);
    expect(find.textContaining('Nenhuma peça efetivamente registrada'), findsOneWidget);
    expect(find.textContaining('peças efetivamente registradas no estoque.'), findsNothing);
  });

  testWidgets('all not received preserves conference with a neutral message', (tester) async {
    await open(tester);
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'Not delivered');
    await tester.ensureVisible(find.text('Registrar Conferência'));
    await tester.tap(find.text('Registrar Conferência'));
    await tester.pumpAndSettle();
    expect(transport.posts, 1);
    expect(find.text('Conferência salva sem entrada de peças no estoque.'), findsOneWidget);
    expect(find.textContaining('Nenhuma peça efetivamente registrada'), findsNothing);
  });

  testWidgets('partial receipt announces only server persisted pieces', (tester) async {
    transport.response = {'ok': true, 'stock_entries': 2, 'qr_labels': [
      {'stock_item_id': 1, 'qr_code_value': 'QR-1'},
      {'stock_item_id': 2, 'qr_code_value': 'QR-2'},
    ]};
    await open(tester);
    await tester.ensureVisible(find.text('Registrar Conferência'));
    await tester.tap(find.text('Registrar Conferência'));
    await tester.pumpAndSettle();
    expect(transport.posts, 1);
    expect(find.text('2 peças efetivamente registradas no estoque.'), findsOneWidget);
    expect(find.byType(ConferencePurchaseRequestScreen), findsNothing);
  });

  testWidgets('quantity changed on server presents the HTTP refusal clearly', (tester) async {
    transport.status = 400;
    transport.response = {'error': 'Quantidade efetivamente recebida inválida ou não positiva.'};
    await open(tester);
    await tester.ensureVisible(find.text('Registrar Conferência'));
    await tester.tap(find.text('Registrar Conferência'));
    await tester.pumpAndSettle();
    expect(find.text('Quantidade efetivamente recebida inválida ou não positiva.'), findsOneWidget);
    expect(find.byType(ConferencePurchaseRequestScreen), findsOneWidget);
  });

  testWidgets('date picker completion after screen disposal never updates state', (tester) async {
    await open(tester);
    await tester.tap(find.byIcon(Icons.event_rounded));
    await tester.pumpAndSettle();
    visible.value = false;
    await tester.pump();
    final dialogContext = tester.element(find.byType(DatePickerDialog));
    Navigator.of(dialogContext).pop(DateTime(2030));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('camera completion after disposal never reads image or updates state', (tester) async {
    final pending = Completer<String?>();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(camera, (_) => pending.future);
    await open(tester);
    await tester.tap(find.byIcon(Icons.photo_camera_rounded));
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    pending.complete('/does-not-exist.jpg');
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(transport.posts, 0);
  });

  testWidgets('camera error after disposal never displays a snackbar', (tester) async {
    final pending = Completer<String?>();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(camera, (_) => pending.future);
    await open(tester);
    await tester.tap(find.byIcon(Icons.photo_camera_rounded));
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    pending.completeError(PlatformException(code: 'camera'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(transport.posts, 0);
  });
}
