import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:epi_design/epi_design.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/i18n/presentation_formatters.dart';
import 'package:epi_admin/core/i18n/localized_epi_badge.dart';
import 'package:epi_admin/features/subscription/subscription_screen.dart';
import 'package:epi_admin/features/subscription/invoices_screen.dart';
const audit='/workspace/i18n-full-v1/audit/';
const tags=[Locale('pt','BR'),Locale('en','US'),Locale('es','ES'),Locale('fr','FR'),Locale('no','NO')];
const receipt='https://synthetic.local/receipt?original=00123&literal=A%2FB';
String lang='en-US';
final evidence=<String,dynamic>{};
Map<String,dynamic> sub()=>{'subscription_id':'Original-00123','plan_key':'corporate','payment_cycle':'annual','payment_method':'card','status':'active','mp_status':'authorized','amount':12345678.9,'currency':'BRL','created_at':'2026-01-02T23:00:00-11:00','next_payment_date':'2027-01-02','company_id':31,'tenant_id':'Original <tenant> {status}','preapproval_id':'MP-00123'};
class Adapter implements HttpClientAdapter{
 final calls=<Map<String,dynamic>>[];bool cancelled=false;
 @override Future<ResponseBody> fetch(RequestOptions o,Stream<Uint8List>? s,Future<void>? cancel)async{
  calls.add({'path':o.path,'method':o.method,'query':Map.of(o.queryParameters),'headers':Map.of(o.headers),'data':o.data is String?jsonDecode(o.data):o.data});
  if(o.path=='/api/subscriptions/cancel')cancelled=true;
  final item=sub();if(cancelled)item['status']='cancelled';
  final payload=o.path=='/api/subscriptions/invoices'?{'invoices':[{'subscription_id':'Original-00123','mp_payment_id':'000123','payment_method':'pix','amount':12345678.9,'currency':'BRL','status':'pending','created_at':'2026-01-02T23:00:00-11:00','receipt_url':receipt}]}:{'subscription':item};
  return ResponseBody.fromString(jsonEncode(payload),200,headers:{Headers.contentTypeHeader:['application/json']});
 }
 @override void close({bool force=false}){}
}
Future<void> settle(WidgetTester t)async{await t.pump();await t.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:40)));await t.pumpAndSettle();}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();final launches=<Map<String,dynamic>>[];late Adapter adapter;
 setUpAll(()async{
  await initializeDateFormatting();
  final font=FontLoader('Inter')..addFont(Future.value(ByteData.sublistView(File('/workspace/i18n-full-v1/corporate/flutter/apps/epi_admin/assets/fonts/Inter-Regular.ttf').readAsBytesSync())));await font.load();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>call.method=='read'&&((call.arguments as Map?)?['key']=='access_token')?'synthetic-access':null);
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.flutter.io/url_launcher'),(call)async{if(call.method=='launch')launches.add(Map<String,dynamic>.from(call.arguments as Map));return true;});
  await ApiClient.init(baseUrl:'https://synthetic.local',localeTag:()=>lang);
  for(final loc in tags)await AppLocalizations.delegate.load(loc);
 });
 setUp((){adapter=Adapter();ApiClient.debugDio.httpClientAdapter=adapter;launches.clear();lang='en-US';});
 tearDownAll(()=>File(audit+'flutter-billing-badges-runtime-results.json').writeAsStringSync(const JsonEncoder.withIndent('  ').convert(evidence)));
 test('money rounding and BRL identity, calendar prefix without timezone shift',(){
  final expected=2.675.toStringAsFixed(2);final cases=[];
  for(final loc in ['pt_BR','en_US','es_ES','fr_FR','no_NO']){final amount=formatDisplayMoney(2.675,'BRL',loc);expect(amount,contains('R\$'));expect(amount,isNot(contains('€')));expect(amount,contains(expected.replaceAll('.',loc=='en_US'?'.':',')));final iso='2026-01-02T23:00:00-11:00';expect(formatDisplayDate(iso,loc),formatDisplayDate('2026-01-02',loc));expect(formatDisplayDate('2026-02-31',loc),'2026-02-31');cases.add({'locale':loc,'money':amount,'old_toFixed2':expected,'calendar_date_preserved':true});}evidence['formatters']=cases;
 });
 testWidgets('invoice pending filter survives EN FR switch and receipt URL stays opaque',(tester)async{
  final locale=ValueNotifier(tags[1]);addTearDown(locale.dispose);tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:const InvoicesScreen())));await settle(tester);
  var l=AppLocalizations.of(tester.element(find.byType(InvoicesScreen)));final chip=find.byWidgetPredicate((w)=>w is ChoiceChip&&w.label is Text&&(w.label as Text).data==l.billingInvoicePending);await tester.tap(chip);await settle(tester);expect(adapter.calls.last['query']['status'],'pending');final count=adapter.calls.length;
  locale.value=tags[3];lang='fr-FR';await settle(tester);l=AppLocalizations.of(tester.element(find.byType(InvoicesScreen)));final selected=tester.widget<ChoiceChip>(find.byWidgetPredicate((w)=>w is ChoiceChip&&w.label is Text&&(w.label as Text).data==l.billingInvoicePending));expect(selected.selected,isTrue);expect(adapter.calls.length,count);await tester.tap(find.byTooltip(l.billingOpenReceipt));await settle(tester);expect(launches.single['url'],receipt);expect(launches.single['useWebView'],isFalse);expect(launches.single['useSafariVC'],isFalse);expect(tester.takeException(),isNull);expect(adapter.calls.every((x)=>x['method']=='GET'),isTrue);expect(adapter.calls.every((x)=>x['headers']['Authorization']=='Bearer synthetic-access'),isTrue);
  evidence['invoice']={'pending_filter_locale_switch_preserved':true,'locale_switch_no_refetch':true,'receipt_url':launches.single['url'],'external_launch':true,'zero_POST':true,'canonical_requests':adapter.calls,'no_overflow_390x844':true};await tester.pumpWidget(const SizedBox());
 });
 testWidgets('cancellation dialog follows locale and has zero POST until explicit confirm',(tester)async{
  final locale=ValueNotifier(tags[1]);addTearDown(locale.dispose);tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:const SubscriptionScreen())));await settle(tester);
  var l=AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));await tester.ensureVisible(find.text(l.billingCancelAction));await tester.tap(find.text(l.billingCancelAction));await settle(tester);expect(find.text(l.billingConfirmTitle),findsOneWidget);locale.value=tags[3];lang='fr-FR';await settle(tester);l=AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));expect(find.text(l.billingConfirmTitle),findsOneWidget);expect(adapter.calls.where((x)=>x['method']=='POST'),isEmpty);await tester.tap(find.text(l.back));await settle(tester);expect(adapter.calls.where((x)=>x['method']=='POST'),isEmpty);
  await tester.tap(find.text(l.billingCancelAction));await settle(tester);locale.value=tags[4];lang='no-NO';await settle(tester);l=AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));expect(find.text(l.billingConfirmTitle),findsOneWidget);expect(adapter.calls.where((x)=>x['method']=='POST'),isEmpty);await tester.tap(find.text(l.billingConfirmCancel));await settle(tester);final posts=adapter.calls.where((x)=>x['method']=='POST').toList();expect(posts,hasLength(1));expect(posts.single['path'],'/api/subscriptions/cancel');expect(posts.single['data'],{'reason':''});expect(posts.single['headers']['Authorization'],'Bearer synthetic-access');expect(find.text(l.billingCancelledNotice),findsOneWidget);locale.value=tags[3];lang='fr-FR';await settle(tester);l=AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));expect(find.text(l.billingCancelledNotice),findsOneWidget);expect(adapter.calls.where((x)=>x['method']=='POST'),hasLength(1));expect(tester.takeException(),isNull);
  evidence['cancel']={'dialog_locale_switch':true,'back_zero_POST':true,'exactly_one_POST_after_confirmation':true,'reason_empty':true,'success_snackbar_live_locale':true,'requests':adapter.calls};await tester.pumpWidget(const SizedBox());
 });
 testWidgets('both typed badge families keep status colors and update all five locales',(tester)async{
  final locale=ValueNotifier(tags.first),theme=ValueNotifier(EpiTheme.light);addTearDown(locale.dispose);addTearDown(theme.dispose);final capture=GlobalKey();tester.view.physicalSize=const Size(1000,1100);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final rows=Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Synthetic fixture: original PT defaults | localized wrapper'),for(final s in EpiBadgeStatus.values)Padding(padding:const EdgeInsets.all(4),child:Row(key:ValueKey('epi-${s.name}'),children:[SizedBox(width:130,child:Text(s.name)),SizedBox(width:260,child:Align(alignment:Alignment.centerLeft,child:EpiBadge(status:s))),LocalizedEpiBadge(status:s)])),for(final s in EpiStockStatus.values)Padding(padding:const EdgeInsets.all(4),child:Row(key:ValueKey('stock-${s.name}'),children:[SizedBox(width:130,child:Text('stock.${s.name}')),SizedBox(width:260,child:Align(alignment:Alignment.centerLeft,child:EpiStockBadge(status:s))),LocalizedEpiStockBadge(status:s)]))]);
  await tester.pumpWidget(RepaintBoundary(key:capture,child:ValueListenableBuilder<ThemeData>(valueListenable:theme,builder:(context,t,child)=>ValueListenableBuilder<Locale>(valueListenable:locale,child:rows,builder:(context,value,child)=>MaterialApp(theme:t,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:Scaffold(body:Padding(padding:const EdgeInsets.all(20),child:child)))))));await settle(tester);
  final cases=[];
  for(final dark in [false,true]){theme.value=dark?EpiTheme.dark:EpiTheme.light;for(final loc in tags){locale.value=loc;await settle(tester);final context=tester.element(find.byType(LocalizedEpiBadge).first);final l=AppLocalizations.of(context);final expected=[l.statusActive,l.statusInactive,l.statusExpired,l.statusExpiring,l.statusPending,l.statusApproved,l.statusRejected,l.statusInReview,l.epiStatusNoStock,l.stockConfigStatusCritical];for(var i=0;i<EpiBadgeStatus.values.length;i++){final s=EpiBadgeStatus.values[i];final row=find.byKey(ValueKey('epi-${s.name}'));final b=tester.widgetList<EpiBadge>(find.descendant(of:row,matching:find.byType(EpiBadge))).toList();expect(b,hasLength(2));expect(b.every((x)=>x.status==s),isTrue);expect(b.last.label,expected[i]);final c=tester.widgetList<Container>(find.descendant(of:row,matching:find.byType(Container))).toList();expect(c.first.decoration,c.last.decoration);}for(final s in EpiStockStatus.values){final row=find.byKey(ValueKey('stock-${s.name}'));final b=tester.widgetList<EpiStockBadge>(find.descendant(of:row,matching:find.byType(EpiStockBadge))).toList();expect(b,hasLength(2));expect(b.every((x)=>x.status==s),isTrue);final expectedStock={EpiStockStatus.normal:l.stockConfigStatusNormal,EpiStockStatus.nearMinimum:l.stockConfigStatusNearMinimum,EpiStockStatus.critical:l.stockConfigStatusCritical,EpiStockStatus.disabled:l.stockConfigStatusDisabled};expect(b.last.label,expectedStock[s]);final c=tester.widgetList<Container>(find.descendant(of:row,matching:find.byType(Container))).toList();expect(c.first.decoration,c.last.decoration);}expect(tester.takeException(),isNull);cases.add({'locale':loc.toString(),'theme':dark?'dark':'light','status_labels':14,'canonical_status_and_decoration_preserved':true});if(!dark&&loc==tags[3])await tester.runAsync(()async{final image=await(capture.currentContext!.findRenderObject()as RenderRepaintBoundary).toImage(pixelRatio:1);final bytes=await image.toByteData(format:ui.ImageByteFormat.png);File(audit+'flutter-badges-original-pt-vs-localized-fr.png').writeAsBytesSync(bytes!.buffer.asUint8List());image.dispose();});}}
  evidence['badges']={'cases':cases,'capture':'flutter-badges-original-pt-vs-localized-fr.png','same_statuses_original_defaults_vs_current_wrapper':true,'no_API':true};await tester.pumpWidget(const SizedBox());
 });
}
