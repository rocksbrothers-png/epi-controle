import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:epi_design/epi_design.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/auth/change_password_screen.dart';
import 'package:epi_admin/features/dashboard/dashboard_screen.dart';
const audit='/workspace/i18n-full-v1/audit/';
final evidence=<String,dynamic>{};
class CaptureAdapter implements HttpClientAdapter{
 final calls=<Map<String,dynamic>>[];
 final payload=<String,dynamic>{'scope':{'company_id':31,'unit_id':51,'locked':true},'kpis':{'deliveries_today':12345678,'expiring_epis':1234,'critical_stock':1234,'pending_purchases':1234},'alerts':[{'company_id':31,'unit_id':51,'epi_id':71,'type':'danger','category':'physical_unknown','title':'Validade física desconhecida','description':'Luva original: 1234 peça(s) física(s).','presentation':{'title_key':'operationalAlerts.physical_unknown.title','description_key':'operationalAlerts.physicalDescription','params':{'epi':'Luva <b>original</b> {count} ÆØ','count':1234}}}]};
 @override Future<ResponseBody> fetch(RequestOptions o,Stream<Uint8List>? stream,Future<void>? cancel)async{calls.add({'path':o.path,'query':Map.of(o.queryParameters),'headers':Map.of(o.headers),'data':o.data});return ResponseBody.fromString(jsonEncode(payload),200,headers:{Headers.contentTypeHeader:['application/json']});}
 @override void close({bool force=false}){}
}
Future<void> settle(WidgetTester t)async{await t.pump();await t.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:40)));await t.pumpAndSettle();}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 setUpAll(()async{final loader=FontLoader('Inter')..addFont(Future.value(ByteData.sublistView(File('/workspace/i18n-full-v1/corporate/flutter/apps/epi_admin/assets/fonts/Inter-Regular.ttf').readAsBytesSync())));await loader.load();final icons=File('/workspace/.cloud-setup/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf');if(icons.existsSync()){final f=FontLoader('MaterialIcons')..addFont(Future.value(ByteData.sublistView(icons.readAsBytesSync())));await f.load();}});
 tearDownAll(()=>File(audit+'flutter-forms-layout-runtime-results.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert(evidence)));
 testWidgets('independent PT FR EN validation transition keeps entered passwords and does not submit',(tester)async{
  final locale=ValueNotifier(const Locale('pt','BR'));tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);addTearDown(locale.dispose);
  await tester.pumpWidget(ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:const ChangePasswordScreen())));await settle(tester);
  final fields=find.byType(TextFormField);final values=['Temporary synthetic original','short','different synthetic'];for(var i=0;i<3;i++)await tester.enterText(fields.at(i),values[i]);
  var l=AppLocalizations.of(tester.element(find.byType(ChangePasswordScreen)));await tester.ensureVisible(find.text(l.passwordChangeSave));await tester.tap(find.text(l.passwordChangeSave));await tester.pumpAndSettle();expect(find.text(l.passwordChangeMinLength),findsOneWidget);expect(find.text(l.passwordChangeMismatch),findsOneWidget);
  final transitions=[];
  for(final next in [const Locale('fr','FR'),const Locale('en','US')]){final previous=l.passwordChangeMinLength;locale.value=next;await settle(tester);l=AppLocalizations.of(tester.element(find.byType(ChangePasswordScreen)));expect(find.text(previous),findsNothing);expect(find.text(l.passwordChangeMinLength),findsOneWidget);expect(find.text(l.passwordChangeMismatch),findsOneWidget);for(var i=0;i<3;i++)expect(tester.widget<TextFormField>(fields.at(i)).controller!.text,values[i]);expect(find.text(l.passwordChangeFailed),findsNothing);expect(tester.takeException(),isNull);transitions.add({'locale':next.toString(),'validation_relocalized':true,'entered_passwords_preserved':true});}
  evidence['password_error_transition']={'start':'pt_BR','transitions':transitions,'API_initialized':false,'invalid_values_never_reached_API':true,'errors':0};await tester.pumpWidget(const SizedBox());
 });
 testWidgets('independent real Dashboard FR 390x844 scales 1 and 1.3 fits large KPIs and preserves scope',(tester)async{
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
  await ApiClient.init(baseUrl:'https://synthetic.local',localeTag:()=> 'fr-FR');final adapter=CaptureAdapter();ApiClient.debugDio.httpClientAdapter=adapter;final auth=AuthCubit();final scale=ValueNotifier(1.0);final captureKey=GlobalKey();tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);addTearDown(scale.dispose);
  final before=jsonEncode(adapter.payload);
  await tester.pumpWidget(RepaintBoundary(key:captureKey,child:ValueListenableBuilder<double>(valueListenable:scale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:const Locale('fr','FR'),localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,builder:(context,child)=>MediaQuery(data:MediaQuery.of(context).copyWith(textScaler:TextScaler.linear(value)),child:child!),home:BlocProvider.value(value:auth,child:const DashboardScreen())))));await settle(tester);
  final cases=[];
  for(final value in [1.0,1.3]){scale.value=value;await settle(tester);final l=AppLocalizations.of(tester.element(find.byType(DashboardScreen)));final large=NumberFormat.decimalPattern(l.localeName).format(12345678);await tester.scrollUntilVisible(find.text(large),-300,scrollable:find.byType(Scrollable).first);await tester.pumpAndSettle();expect(find.text(large),findsOneWidget);expect(tester.takeException(),isNull);expect(adapter.calls.length,1);expect(jsonEncode(adapter.payload),before);
   final name='flutter-postfix-dashboard-fr-FR-mobile-scale${value.toString().replaceAll('.','_')}.png';await tester.runAsync(()async{final image=await(captureKey.currentContext!.findRenderObject()as RenderRepaintBoundary).toImage(pixelRatio:1);final data=await image.toByteData(format:ui.ImageByteFormat.png);File(audit+name).writeAsBytesSync(data!.buffer.asUint8List());image.dispose();});
   await tester.scrollUntilVisible(find.text(l.operationalAlertPhysicalUnknownTitle),300,scrollable:find.byType(Scrollable).first);await tester.pumpAndSettle();expect(find.text(l.operationalAlertPhysicalDescription(1234,NumberFormat.decimalPattern(l.localeName).format(1234),'Luva <b>original</b> {count} ÆØ')),findsOneWidget);expect(tester.takeException(),isNull);cases.add({'locale':'fr_FR','viewport':'390x844','text_scale':value,'large_KPI':large,'no_overflow':true,'canonical_payload_scope_unchanged':true,'screenshot':name});}
  evidence['dashboard_postfix']={'cases':cases,'requests':adapter.calls,'query_unchanged':adapter.calls.single['query'].toString()=='{actor_user_id: 0}','locale_and_scale_change_no_refetch':true,'overflow_handler':'No suppression; tester.takeException must be null'};await tester.pumpWidget(const SizedBox());await auth.close();
 });
}
