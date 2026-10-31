import 'dart:io';
import 'dart:ui' as ui;
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/users/users_screen.dart';
import 'package:epi_admin/features/settings/archival_policy_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'forms-settings-baseline/users_screen.dart';
import 'forms-settings-baseline/archival_policy_screen.dart';
import '../../../../flutter/apps/epi_admin/test/forms_settings_i18n_test.dart' show FormsAdapter,TestAuth,session,settle;
void main(){
 TestWidgetsFlutterBinding.ensureInitialized();
 setUpAll(()async{
  final font=FontLoader('Inter');
  for(final weight in ['Regular','Medium','SemiBold','Bold']){font.addFont(Future.value(ByteData.sublistView(File('assets/fonts/Inter-$weight.ttf').readAsBytesSync())));}
  await font.load();
  await (FontLoader('MaterialIcons')..addFont(Future.value(ByteData.sublistView(File('/workspace/.cloud-setup/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf').readAsBytesSync())))).load();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),(call)async=>null);
  await ApiClient.init(baseUrl:'https://synthetic.local');await ApiClient.saveSessionContext(session('general_admin'));
 });
 testWidgets('real users and archival widgets before and after in French with synthetic reads',(t)async {
  final auth=TestAuth('general_admin');addTearDown(auth.close);final adapter=FormsAdapter();ApiClient.debugDio.httpClientAdapter=adapter;
  t.view.physicalSize=const Size(390,844);t.view.devicePixelRatio=1;addTearDown(t.view.resetPhysicalSize);addTearDown(t.view.resetDevicePixelRatio);
  await t.runAsync(()=>AppLocalizations.delegate.load(const Locale('fr','FR')));
  for(final users in [true,false]){for(final before in [true,false]){
    final key=GlobalKey();
    final Widget home=users?(before?const BaselineUsersScreen():const UsersScreen()):(before?const BaselineArchivalPolicyScreen(companyId:41):const ArchivalPolicyScreen(companyId:41));
    await t.pumpWidget(RepaintBoundary(key:key,child:MaterialApp(debugShowCheckedModeBanner:false,locale:const Locale('fr','FR'),theme:EpiTheme.light,localizationsDelegates:AppLocalizations.localizationsDelegates,supportedLocales:AppLocalizations.supportedLocales,home:BlocProvider<AuthCubit>.value(value:auth,child:home))));await settle(t);
    if(users){await t.tap(find.byType(FloatingActionButton));await settle(t);}
    expect(t.takeException(),isNull);
    final filename='${users?'users-form':'archival-policy'}-${before?'before':'after'}-fr-FR-mobile.png';
    await t.runAsync(()async{
      final screenshot=await(key.currentContext!.findRenderObject() as RenderRepaintBoundary).toImage(pixelRatio:1);
      final bytes=await screenshot.toByteData(format:ui.ImageByteFormat.png);
      File('/workspace/i18n-full-v1/evidence/'+filename).writeAsBytesSync(bytes!.buffer.asUint8List());screenshot.dispose();
    });
    await t.pumpWidget(const SizedBox());
  }}
  expect(adapter.writes,isEmpty);
 });
}
