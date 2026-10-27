import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/feedback/feedback_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'feedback-baseline/feedback_screen.dart';
class Adapter implements HttpClientAdapter {
 int gets=0;
 @override Future<ResponseBody> fetch(RequestOptions options,Stream<Uint8List>? stream,Future<void>? cancel)async {
  expect(options.method,'GET');expect(options.path,'/api/feedbacks');gets++;
  return ResponseBody.fromString(jsonEncode({'items':[
   {'id':7,'epi_name':'Synthetic PPE','status':'aguardando_aprovacao_admin','type':'sugestao','created_at':'2026-04-18T23:00:00-03:00','employee_name':'Synthetic employee','unit_name':'Synthetic unit','description':'Original user text remains unchanged'},
   {'id':8,'epi_name':'Synthetic PPE 2','status':'recebido','created_at':'2026-04-17','description':'Original user text remains unchanged'}
  ]}),200,headers:{Headers.contentTypeHeader:['application/json']});
 }
 @override void close({bool force=false}){}
}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 setUpAll(()async{
  final loader=FontLoader('Inter');
  for(final name in ['Regular','Medium','SemiBold','Bold'])loader.addFont(Future.value(ByteData.sublistView(File('/workspace/i18n-full-v1/corporate/flutter/apps/epi_admin/assets/fonts/Inter-$name.ttf').readAsBytesSync())));
  await loader.load();
  final icons=FontLoader('MaterialIcons')..addFont(Future.value(ByteData.sublistView(File('/workspace/.cloud-setup/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf').readAsBytesSync())));await icons.load();
 });
 testWidgets('real feedback widget before and after with identical synthetic data',(tester)async{
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
  await ApiClient.init(baseUrl:'https://synthetic.local');final adapter=Adapter();ApiClient.debugDio.httpClientAdapter=adapter;
  await tester.runAsync(()=>AppLocalizations.delegate.load(const Locale('fr','FR')));
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final captures=[];
  for(final before in [true,false]){
   final key=GlobalKey();
   await tester.pumpWidget(RepaintBoundary(key:key,child:MaterialApp(debugShowCheckedModeBanner:false,theme:EpiTheme.light,locale:const Locale('fr','FR'),localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:before?const BaselineFeedbackScreen():const FeedbackScreen())));
   await tester.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:30)));await tester.pumpAndSettle();
   final errors=<String>[];for(var error=tester.takeException();error!=null;error=tester.takeException())errors.add(error.toString());
   if(!before)expect(errors,isEmpty);
   final filename='feedback-${before?'before':'after'}-fr-FR-mobile.png';
   await tester.runAsync(()async{final screenshot=await(key.currentContext!.findRenderObject()as RenderRepaintBoundary).toImage(pixelRatio:1);final png=await screenshot.toByteData(format:ui.ImageByteFormat.png);File('/workspace/i18n-full-v1/evidence/'+filename).writeAsBytesSync(png!.buffer.asUint8List());screenshot.dispose();});
   captures.add({'file':filename,'baselineWidget':before,'locale':'fr_FR','viewport':'390x844','errors':errors});
   await tester.pumpWidget(const SizedBox());
  }
  expect(adapter.gets,2);
  File('/workspace/i18n-full-v1/evidence/feedback-capture-results.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert({'source':'Real widgets with synthetic intercepted reads and locally loaded fonts','baseline':'c1faf3a3e58c05b2656a70ea67495d1ea451923a feedback widget; imports and class names adapted for harness','sameFixture':true,'writes':0,'captures':captures}));
 });
}
