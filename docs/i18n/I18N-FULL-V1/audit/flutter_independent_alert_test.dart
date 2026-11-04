import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:dio/dio.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/api/locale_header_interceptor.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/dashboard/alert_presentation.dart';
import 'package:epi_admin/features/dashboard/dashboard_screen.dart';

const locales=[Locale('pt','BR'),Locale('en','US'),Locale('es','ES'),Locale('fr','FR'),Locale('no','NO')];
const opaque='Luva <b>original</b> {count} ÆØ';
Map<String,dynamic> fixture()=>{'company_id':31,'unit_id':51,'epi_id':71,'type':'danger','category':'physical_unknown','title':'LEGACY TITLE','description':'COMPLETE LEGACY DESCRIPTION WITH SIZES','presentation':{'title_key':'operationalAlerts.physical_unknown.title','description_key':'operationalAlerts.physicalDescription','params':{'epi':opaque,'count':1234}}};
final evidence=<String,dynamic>{'cases':[]};
class Adapter implements HttpClientAdapter{
 final captured=<Map<String,dynamic>>[];
 @override Future<ResponseBody> fetch(RequestOptions o,Stream<Uint8List>? s,Future<void>? cancel)async{
  captured.add({'path':o.path,'headers':Map.of(o.headers),'query':Map.of(o.queryParameters),'data':o.data});
  return ResponseBody.fromString(jsonEncode({'scope':{'company_id':31,'unit_id':51,'locked':true},'alerts':[fixture()]}),200,headers:{Headers.contentTypeHeader:['application/json']});
 }
 @override void close({bool force=false}){}
}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 setUpAll(()async{await initializeDateFormatting();});
 tearDownAll((){File('/workspace/i18n-full-v1/audit/flutter-independent-results.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert(evidence));});
 test('independent plural, date, size, opaque values and complete fallback matrix',()async{
  for(final locale in locales){final l=await AppLocalizations.delegate.load(locale);
   for(final count in [0,1,2,1234,-1,0.5]){final item=fixture();(item['presentation']['params'] as Map)['count']=count;final before=jsonEncode(item);final actual=presentOperationalAlert(item,l);expect(actual.description,l.operationalAlertPhysicalDescription(count,NumberFormat.decimalPattern(l.localeName).format(count),opaque));expect(jsonEncode(item),before);}
   final stock=fixture()..['category']='stock'..['size_balances']=[{'glove_size':'M <tag>','size':'N/A','uniform_size':'42','quantity':1234},{'quantity':0}];stock['presentation']={'title_key':'operationalAlerts.stock.negative','description_key':'operationalAlerts.stock.description','params':{'epi':opaque,'company':'Empresa {stock}','unit':'Unidade 51','stock':-1,'minimum':0,'measure':'par'}};
   final stockBefore=jsonEncode(stock),stockText=presentOperationalAlert(stock,l);expect(stockText.title,l.operationalAlertStockNegative(opaque));expect(stockText.description,contains(l.operationalAlertSizeGlove('M <tag>')));expect(stockText.description,contains(l.operationalAlertSizeUnspecified));expect(stockText.description,contains('Empresa {stock}'));expect(jsonEncode(stock),stockBefore);
   final future=fixture();future['presentation']={'title_key':'operationalAlerts.manufacturer.expiringTitle','description_key':'operationalAlerts.manufacturer.expiringDescription','params':{'epi':opaque,'company':'Empresa original','date':'2027-01-02','stock':1,'measure':'unidade','days':3}};final text=presentOperationalAlert(future,l);expect(text.description,contains(DateFormat.yMd(l.localeName).format(DateTime(2027,1,2))));expect(text.description,contains(l.operationalAlertDays(3,'3')));expect(text.description,isNot(contains('{daysLabel}')));
   for(final metadata in [null,{},'invalid',{'title_key':'operationalAlerts.future','description_key':'operationalAlerts.physicalDescription','params':{'count':1,'epi':'X'}},{'title_key':'operationalAlerts.physical_unknown.title','description_key':'operationalAlerts.physicalDescription','params':{'count':'1','epi':'X'}}]){final item=fixture()..['presentation']=metadata;final before=jsonEncode(item);expect(presentOperationalAlert(item,l),(title:'LEGACY TITLE',description:'COMPLETE LEGACY DESCRIPTION WITH SIZES'));expect(jsonEncode(item),before);}
   evidence['cases'].add({'locale':locale.toString(),'pluralCases':6,'dateAndNestedDays':true,'sizesAndOpaqueNames':true,'fullFallbackCases':5,'dataUnchanged':true});
  }
 });
 test('interceptor changes only language header and reads current callback',()async{
  var current='pt-BR';final dio=Dio()..interceptors.add(LocaleHeaderInterceptor(()=>current));final adapter=Adapter();dio.httpClientAdapter=adapter;
  final payload={'company_id':31,'unit_id':51,'actor_user_id':91,'quantity':1234.56,'status':'confirmed'};final before=jsonEncode(payload);
  for(final tag in ['pt-BR','en-US','es-ES','fr-FR','no-NO']){current=tag;await dio.post('/local',data:payload,queryParameters:{'scope':'unchanged'},options:Options(headers:{'aCcEpT-LaNgUaGe':'old','Authorization':'Bearer synthetic','X-Probe':'original'}));final req=adapter.captured.last;expect((req['headers']as Map)['Accept-Language'],tag);expect((req['headers']as Map).keys.where((k)=>k.toString().toLowerCase()=='accept-language').length,1);expect((req['headers']as Map)['Authorization'],'Bearer synthetic');expect(req['query'],{'scope':'unchanged'});expect((req['data'] is String?jsonDecode(req['data']as String):req['data']),payload);expect(jsonEncode(payload),before);}
  evidence['localeInterceptorCanonicalBodyAndAuth']=true;
 });
 testWidgets('actual DashboardScreen renders all existing locale variants without refetching or mutating server scope',(tester)async{
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
  print('AUDIT widget init');final locale=ValueNotifier(locales.first);await ApiClient.init(baseUrl:'https://synthetic.local',localeTag:()=>locale.value.toLanguageTag());final adapter=Adapter();ApiClient.debugDio.httpClientAdapter=adapter;final auth=AuthCubit();print('AUDIT init done');
  tester.view.physicalSize=const Size(1000,1600);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:BlocProvider.value(value:auth,child:const DashboardScreen()))));await tester.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:30)));await tester.pumpAndSettle(const Duration(milliseconds:100),EnginePhase.sendSemanticsUpdate,const Duration(seconds:5));print('AUDIT first widget settled');
  final rendered=[];
  for(final value in locales){print('AUDIT locale '+value.toString());locale.value=value;await tester.pump();await tester.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:30)));await tester.pumpAndSettle();final l=AppLocalizations.of(tester.element(find.byType(DashboardScreen)));print('AUDIT delegate loaded');await tester.scrollUntilVisible(find.text(l.operationalAlertPhysicalUnknownTitle),300,scrollable:find.byType(Scrollable).first);await tester.pumpAndSettle();print('AUDIT scrolled');expect(find.text(l.operationalAlertPhysicalUnknownTitle),findsOneWidget);expect(find.text(l.operationalAlertPhysicalDescription(1234,NumberFormat.decimalPattern(l.localeName).format(1234),opaque)),findsOneWidget);expect(tester.takeException(),isNull);rendered.add(value.toString());}
  expect(adapter.captured.length,1);expect(adapter.captured.single['path'],'/api/dashboard/summary');expect(adapter.captured.single['query'],{'actor_user_id':0});evidence['realDashboardWidgetLocales']=rendered;evidence['localeChangeNoRefetch']=true;evidence['realRequests']=adapter.captured;
  print('AUDIT widget loops done');await tester.pumpWidget(const SizedBox());await auth.close();locale.dispose();
 });
}
