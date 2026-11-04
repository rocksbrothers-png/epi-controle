// Reproducible copy of the independent probe; only the fixture import is made repository-relative.
import 'package:epi_admin/core/bloc/companies_cubit.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/features/employees/employees_screen.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../flutter/apps/epi_admin/test/archive_labels_i18n_test.dart' as fixtures;
import 'package:epi_admin/core/i18n/entity_labels.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/i18n/presentation_formatters.dart';
import 'package:epi_admin/core/notifications/notification_overlay.dart';
import 'package:epi_admin/core/notifications/notification_service.dart';
import 'package:epi_admin/core/widgets/create_company_dialog.dart';
import 'package:flutter/material.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeCompanies extends CompaniesCubit {
 final calls = <Map<String,dynamic>>[];
 @override Future<String?> create(Map<String,dynamic> data) async {calls.add(data);return 'Original server detail {unchanged}';}
}
Widget app(ValueNotifier<Locale> locale,Widget home,{bool overlay=false})=> ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:home,builder:overlay?(context,child)=>NotificationOverlay(child:child!):null));
Future<void> switchLocale(WidgetTester tester,ValueNotifier<Locale> value,Locale target) async {value.value=target;await tester.pump();await tester.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:40)));await tester.pump(const Duration(milliseconds:50));}
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 testWidgets('independent local stock metadata retraduz while raw notification stays original', (tester) async {
  final locale=ValueNotifier(const Locale('pt','BR'));addTearDown(locale.dispose);
  await tester.pumpWidget(app(locale,const Scaffold(body:Text('Host')),overlay:true));await tester.pumpAndSettle();
  const notification=AppNotification(title:'LEGACY title',body:'LEGACY body',data:{'code':'stock_below_min'},criticalStockCount:1234);
  NotificationService().simulateNotification(notification);await tester.pump();await tester.pump(const Duration(milliseconds:350));
  for(final target in [const Locale('fr','FR'),const Locale('no','NO'),const Locale('en','US')]) {
   await switchLocale(tester,locale,target);
   final l=AppLocalizations.of(tester.element(find.byType(NotificationOverlay)));
   expect(find.text(l.criticalStockTitle),findsOneWidget);expect(find.text(l.criticalStockBody(1234,formatDisplayCount(1234,l.localeName))),findsOneWidget);
   expect(notification.criticalStockCount,1234);expect(notification.data,{'code':'stock_below_min'});expect(notification.title,'LEGACY title');
  }
  await tester.pump(const Duration(seconds:6));await tester.pump(const Duration(milliseconds:350));
  const original=AppNotification(title:'Original remote title',body:'Original remote body {untouched}',data:{'criticalStockCount':1234});
  NotificationService().simulateNotification(original);await tester.pump();await tester.pump(const Duration(milliseconds:350));
  await switchLocale(tester,locale,const Locale('es','ES'));
  expect(find.text(original.title),findsOneWidget);expect(find.text(original.body),findsOneWidget);
  await tester.pump(const Duration(seconds:6));await tester.pump(const Duration(milliseconds:350));expect(tester.takeException(),isNull);await tester.pumpWidget(const SizedBox());
 });
 testWidgets('independent company validators retraduz and payload remains canonical', (tester) async {
  final originalOnError=FlutterError.onError;FlutterError.onError=(details){debugPrint(details.toString());originalOnError!(details);};addTearDown(()=>FlutterError.onError=originalOnError);tester.view.physicalSize=const Size(1200,1000);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  final locale=ValueNotifier(const Locale('pt','BR'));addTearDown(locale.dispose);final companies=FakeCompanies();addTearDown(companies.close);
  await tester.pumpWidget(app(locale,Builder(builder:(context)=>Scaffold(body:TextButton(key:const Key('open'),onPressed:()=>CreateCompanyDialog.show(context,companies,71),child:const Text('Open'))))));await tester.pumpAndSettle();await tester.tap(find.byKey(const Key('open')));await tester.pumpAndSettle();expect(tester.takeException(),isNull,reason:'initial PT dialog');
  await tester.tap(find.byType(FilledButton));await tester.pumpAndSettle();expect(find.text('Campo obrigatório'),findsWidgets);expect(tester.takeException(),isNull,reason:'PT validation');
  await switchLocale(tester,locale,const Locale('fr','FR'));await tester.pumpAndSettle();var l=AppLocalizations.of(tester.element(find.byType(CreateCompanyDialog)));expect(find.text(l.required),findsWidgets);expect(find.text('Campo obrigatório'),findsNothing);expect(tester.takeException(),isNull,reason:'FR validation');
  final fields=find.byType(TextFormField);await tester.enterText(fields.at(0),'Nome original {name}');await tester.enterText(fields.at(1),'Razão original');await tester.enterText(fields.at(2),'11222333000181');await tester.enterText(fields.at(4),'Dona original');await tester.enterText(fields.at(5),'owner@example.test');
  await tester.tap(find.byType(FilledButton));await tester.pumpAndSettle();expect(companies.calls.single,{'actor_user_id':71,'name':'Nome original {name}','legal_name':'Razão original','cnpj':'11222333000181','plan_name':'start','user_limit':1,'license_status':'active','active':1,'general_admin_email':'owner@example.test','general_admin_name':'Dona original'});
  expect(find.text('Original server detail {unchanged}'),findsOneWidget);expect(tester.takeException(),isNull,reason:'FR filled submit');
  await switchLocale(tester,locale,const Locale('no','NO'));await tester.pumpAndSettle();l=AppLocalizations.of(tester.element(find.byType(CreateCompanyDialog)));expect(find.text(l.companyNewTitle),findsOneWidget);expect(find.text(l.companyOwnerOptional(l.roleGeneralAdmin)),findsOneWidget);expect(find.text(l.companyOwnerInviteHint(l.roleMasterAdmin)),findsOneWidget);expect(find.text('Original server detail {unchanged}'),findsOneWidget);expect(companies.calls.length,1);expect(tester.widget<TextFormField>(fields.at(0)).controller!.text,'Nome original {name}');expect(tester.takeException(),isNull);await tester.pumpWidget(const SizedBox());
 });
 test('independent canonical labels preserve unknown user values and period malformed data',() async{
  for(final locale in [const Locale('pt','BR'),const Locale('en','US'),const Locale('es','ES'),const Locale('fr','FR'),const Locale('no','NO')]){
   final l=await AppLocalizations.delegate.load(locale);
   expect(appResponsibilityLabel('Unknown original {value}',l),'Unknown original {value}');expect(appReturnConditionLabel('unknown',l),'unknown');expect(appModuleLabel('unexpected_module',l),'unexpected_module');expect(appCompanyKindLabel('other_contracted',l),l.outsourcedCompanyKindOther);
   for(final invalid in ['bad','2026-00','2026-13','2026-5']){expect(formatDisplayPeriod(invalid,l.localeName),invalid);}
   expect(formatDisplayPeriod('2026-05-01',l.localeName),isNot(contains('Mai')));
  }
 });

 testWidgets('independent archive dialog mobile390 and larger text retains form over locale change', (tester) async {
  tester.view.physicalSize=const Size(390,844);tester.view.devicePixelRatio=1;addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
  await ApiClient.init(baseUrl:'https://synthetic.local');final adapter=fixtures.EmployeesAdapter();ApiClient.debugDio.httpClientAdapter=adapter;
  final auth=AuthCubit();addTearDown(auth.close);final locale=ValueNotifier(const Locale('pt','BR'));addTearDown(locale.dispose);
  await tester.pumpWidget(ValueListenableBuilder<Locale>(valueListenable:locale,builder:(context,value,child)=>MaterialApp(theme:EpiTheme.light,locale:value,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:BlocProvider.value(value:auth,child:const EmployeesScreen()),builder:(context,child)=>MediaQuery(data:MediaQuery.of(context).copyWith(textScaler:const TextScaler.linear(1.3)),child:child!))));
  await tester.pump();await tester.runAsync(()=>Future<void>.delayed(const Duration(milliseconds:40)));await tester.pumpAndSettle();expect(tester.takeException(),isNull,reason:'initial mobile list');
  await tester.tap(find.byType(PopupMenuButton<String>));await tester.pumpAndSettle();var l=AppLocalizations.of(tester.element(find.byType(EmployeesScreen)));await tester.tap(find.text(l.archive));await tester.pumpAndSettle();expect(tester.takeException(),isNull,reason:'PT mobile archive dialog');
  final field=find.descendant(of:find.byType(AlertDialog),matching:find.byType(TextField));await tester.enterText(field,'Original free reason');
  for(final target in [const Locale('fr','FR'),const Locale('no','NO')]){await switchLocale(tester,locale,target);await tester.pumpAndSettle();l=AppLocalizations.of(tester.element(find.byType(EmployeesScreen)));expect(find.text(l.employeeArchiveTitle),findsOneWidget);expect(tester.widget<TextField>(field).controller!.text,'Original free reason');expect(tester.takeException(),isNull,reason:'mobile archive '+target.toString());}
  await tester.tap(find.text(l.cancel));await tester.pumpAndSettle();expect(adapter.requests.every((request)=>request.method=='GET'),isTrue);await tester.pumpWidget(const SizedBox());
 });
}
