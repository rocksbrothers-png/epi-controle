// Real Flutter widgets, same synthetic fixture and viewport, before/after.
// Run from flutter/apps/epi_admin, setting I18N_EVIDENCE_DIR and FLUTTER_ROOT.
import 'dart:io';
import 'dart:ui' as ui;
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/companies_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/widgets/create_company_dialog.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'remaining-surfaces-baseline/create_company_dialog.dart';
import '../../../../flutter/apps/epi_admin/test/remaining_surfaces_i18n_test.dart' show SurfaceAdapter,settle;
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final font=FontLoader('Inter');
    for(final weight in ['Regular','Medium','SemiBold','Bold']) {font.addFont(Future.value(ByteData.sublistView(File('assets/fonts/Inter-$weight.ttf').readAsBytesSync())));}
    await font.load();
    final sdk=Platform.environment['FLUTTER_ROOT'];
    if(sdk!=null) {await(FontLoader('MaterialIcons')..addFont(Future.value(ByteData.sublistView(File('$sdk/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf').readAsBytesSync())))).load();}
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
    await ApiClient.init(baseUrl:'https://synthetic.local');
  });
  testWidgets('company dialog before/after French mobile real fonts no mutation',(t) async {
    final output=Platform.environment['I18N_EVIDENCE_DIR'];expect(output,isNotNull);
    final adapter=SurfaceAdapter();ApiClient.debugDio.httpClientAdapter=adapter;
    t.view.physicalSize=const Size(390,844);t.view.devicePixelRatio=1;
    addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
    final cubit=CompaniesCubit();addTearDown(cubit.close);
    for(final before in [true,false]) {
      final key=GlobalKey();
      await t.runAsync(()=>AppLocalizations.delegate.load(const Locale('fr','FR')));
      await t.pumpWidget(RepaintBoundary(key:key,child:MaterialApp(locale:const Locale('fr','FR'),theme:EpiTheme.light,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:Scaffold(body:Builder(builder:(context)=>TextButton(onPressed:()=>showDialog<void>(context:context,builder:(_)=>before?BaselineCreateCompanyDialog(cubit:cubit,actorUserId:71):CreateCompanyDialog(cubit:cubit,actorUserId:71)),child:const Text('open')))))));
      await settle(t);await t.tap(find.text('open'));await settle(t);
      await t.runAsync(() async {
        final shot=await(key.currentContext!.findRenderObject() as RenderRepaintBoundary).toImage(pixelRatio:1);
        final bytes=await shot.toByteData(format:ui.ImageByteFormat.png);
        Directory(output!).createSync(recursive:true);
        File('$output/company-${before?'before':'after'}-fr-mobile.png').writeAsBytesSync(bytes!.buffer.asUint8List());shot.dispose();
      });
      await t.pumpWidget(const SizedBox());await t.pumpAndSettle();
    }
    expect(adapter.calls,isEmpty);
  });
}
