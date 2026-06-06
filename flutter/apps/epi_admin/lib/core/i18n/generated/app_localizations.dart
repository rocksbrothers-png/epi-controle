import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart' deferred as app_localizations_en;
import 'app_localizations_es.dart' deferred as app_localizations_es;
import 'app_localizations_fr.dart' deferred as app_localizations_fr;
import 'app_localizations_no.dart' deferred as app_localizations_no;
import 'app_localizations_pt.dart' deferred as app_localizations_pt;

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('en', 'US'),
    Locale('es'),
    Locale('es', 'ES'),
    Locale('fr'),
    Locale('fr', 'FR'),
    Locale('no'),
    Locale('no', 'NO'),
    Locale('pt'),
    Locale('pt', 'BR')
  ];

  /// Nome da aplicação
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI Controle'**
  String get appName;

  /// No description provided for @loading.
  ///
  /// In pt_BR, this message translates to:
  /// **'Carregando...'**
  String get loading;

  /// No description provided for @save.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelar'**
  String get cancel;

  /// No description provided for @confirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar'**
  String get confirm;

  /// No description provided for @delete.
  ///
  /// In pt_BR, this message translates to:
  /// **'Excluir'**
  String get delete;

  /// No description provided for @edit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Editar'**
  String get edit;

  /// No description provided for @add.
  ///
  /// In pt_BR, this message translates to:
  /// **'Adicionar'**
  String get add;

  /// No description provided for @search.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar'**
  String get search;

  /// No description provided for @filter.
  ///
  /// In pt_BR, this message translates to:
  /// **'Filtrar'**
  String get filter;

  /// No description provided for @export.
  ///
  /// In pt_BR, this message translates to:
  /// **'Exportar'**
  String get export;

  /// No description provided for @print.
  ///
  /// In pt_BR, this message translates to:
  /// **'Imprimir'**
  String get print;

  /// No description provided for @close.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fechar'**
  String get close;

  /// No description provided for @back.
  ///
  /// In pt_BR, this message translates to:
  /// **'Voltar'**
  String get back;

  /// No description provided for @next.
  ///
  /// In pt_BR, this message translates to:
  /// **'Próximo'**
  String get next;

  /// No description provided for @previous.
  ///
  /// In pt_BR, this message translates to:
  /// **'Anterior'**
  String get previous;

  /// No description provided for @finish.
  ///
  /// In pt_BR, this message translates to:
  /// **'Concluir'**
  String get finish;

  /// No description provided for @retry.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tentar novamente'**
  String get retry;

  /// No description provided for @refresh.
  ///
  /// In pt_BR, this message translates to:
  /// **'Atualizar'**
  String get refresh;

  /// No description provided for @seeAll.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ver todos'**
  String get seeAll;

  /// No description provided for @noResults.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum resultado encontrado'**
  String get noResults;

  /// No description provided for @required.
  ///
  /// In pt_BR, this message translates to:
  /// **'Campo obrigatório'**
  String get required;

  /// No description provided for @optional.
  ///
  /// In pt_BR, this message translates to:
  /// **'Opcional'**
  String get optional;

  /// No description provided for @navDashboard.
  ///
  /// In pt_BR, this message translates to:
  /// **'Dashboard'**
  String get navDashboard;

  /// No description provided for @navCompanies.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresas'**
  String get navCompanies;

  /// No description provided for @navUsers.
  ///
  /// In pt_BR, this message translates to:
  /// **'Usuários'**
  String get navUsers;

  /// No description provided for @navUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidades'**
  String get navUnits;

  /// No description provided for @navEmployees.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaboradores'**
  String get navEmployees;

  /// No description provided for @navEpis.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPIs'**
  String get navEpis;

  /// No description provided for @navStock.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque'**
  String get navStock;

  /// No description provided for @navDeliveries.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas'**
  String get navDeliveries;

  /// No description provided for @navReturns.
  ///
  /// In pt_BR, this message translates to:
  /// **'Devoluções'**
  String get navReturns;

  /// No description provided for @navRecords.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fichas'**
  String get navRecords;

  /// No description provided for @navPurchases.
  ///
  /// In pt_BR, this message translates to:
  /// **'Compras'**
  String get navPurchases;

  /// No description provided for @navReports.
  ///
  /// In pt_BR, this message translates to:
  /// **'Relatórios'**
  String get navReports;

  /// No description provided for @navSettings.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurações'**
  String get navSettings;

  /// No description provided for @navPortal.
  ///
  /// In pt_BR, this message translates to:
  /// **'Portal'**
  String get navPortal;

  /// Rótulo do menu de avaliações/feedback.
  ///
  /// In pt_BR, this message translates to:
  /// **'Avaliações'**
  String get navFeedback;

  /// No description provided for @loginTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrar'**
  String get loginTitle;

  /// No description provided for @loginUsername.
  ///
  /// In pt_BR, this message translates to:
  /// **'Usuário'**
  String get loginUsername;

  /// No description provided for @loginPassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Senha'**
  String get loginPassword;

  /// No description provided for @loginUsernameHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe seu usuário'**
  String get loginUsernameHint;

  /// No description provided for @loginPasswordHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe sua senha'**
  String get loginPasswordHint;

  /// No description provided for @loginButton.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrar'**
  String get loginButton;

  /// No description provided for @loginForgotPassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Esqueci minha senha'**
  String get loginForgotPassword;

  /// No description provided for @loginShowPassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Mostrar senha'**
  String get loginShowPassword;

  /// No description provided for @loginHidePassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ocultar senha'**
  String get loginHidePassword;

  /// No description provided for @loginError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Usuário ou senha incorretos'**
  String get loginError;

  /// No description provided for @loginErrorEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preencha usuário e senha'**
  String get loginErrorEmpty;

  /// Rótulo do botão de autenticação biométrica na tela de login
  ///
  /// In pt_BR, this message translates to:
  /// **'Biometria'**
  String get loginBiometric;

  /// No description provided for @dashboardTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Dashboard'**
  String get dashboardTitle;

  /// No description provided for @dashboardDeliveriesToday.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas hoje'**
  String get dashboardDeliveriesToday;

  /// No description provided for @dashboardExpiringEpis.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPIs vencendo'**
  String get dashboardExpiringEpis;

  /// No description provided for @dashboardCriticalStock.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque crítico'**
  String get dashboardCriticalStock;

  /// No description provided for @dashboardPendingPurchases.
  ///
  /// In pt_BR, this message translates to:
  /// **'Compras pendentes'**
  String get dashboardPendingPurchases;

  /// No description provided for @dashboardQuickDelivery.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova Entrega'**
  String get dashboardQuickDelivery;

  /// No description provided for @dashboardQuickReturn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Devolução'**
  String get dashboardQuickReturn;

  /// No description provided for @dashboardQuickScan.
  ///
  /// In pt_BR, this message translates to:
  /// **'QR Scan'**
  String get dashboardQuickScan;

  /// No description provided for @dashboardAlertsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Alertas do Dia'**
  String get dashboardAlertsTitle;

  /// No description provided for @dashboardNoAlerts.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum alerta no momento'**
  String get dashboardNoAlerts;

  /// Título do gráfico de entregas semanal no dashboard
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas — últimos 7 dias'**
  String get dashboardWeeklyChartTitle;

  /// Abreviação de segunda-feira
  ///
  /// In pt_BR, this message translates to:
  /// **'Seg'**
  String get dayMon;

  /// Abreviação de terça-feira
  ///
  /// In pt_BR, this message translates to:
  /// **'Ter'**
  String get dayTue;

  /// Abreviação de quarta-feira
  ///
  /// In pt_BR, this message translates to:
  /// **'Qua'**
  String get dayWed;

  /// Abreviação de quinta-feira
  ///
  /// In pt_BR, this message translates to:
  /// **'Qui'**
  String get dayThu;

  /// Abreviação de sexta-feira
  ///
  /// In pt_BR, this message translates to:
  /// **'Sex'**
  String get dayFri;

  /// Abreviação de sábado
  ///
  /// In pt_BR, this message translates to:
  /// **'Sáb'**
  String get daySat;

  /// Abreviação de domingo
  ///
  /// In pt_BR, this message translates to:
  /// **'Dom'**
  String get daySun;

  /// No description provided for @employeesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaboradores'**
  String get employeesTitle;

  /// No description provided for @employeesNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo Colaborador'**
  String get employeesNew;

  /// No description provided for @employeesSearchHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar por nome, matrícula ou setor'**
  String get employeesSearchHint;

  /// No description provided for @employeeNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome completo'**
  String get employeeNameLabel;

  /// No description provided for @employeeCodeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Matrícula'**
  String get employeeCodeLabel;

  /// No description provided for @employeeSectorLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Setor'**
  String get employeeSectorLabel;

  /// No description provided for @employeeRoleLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Função'**
  String get employeeRoleLabel;

  /// No description provided for @employeeUnitLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get employeeUnitLabel;

  /// No description provided for @employeeAdmissionLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Admissão'**
  String get employeeAdmissionLabel;

  /// No description provided for @employeeScheduleLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escala'**
  String get employeeScheduleLabel;

  /// No description provided for @employeeStatusActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ativo'**
  String get employeeStatusActive;

  /// No description provided for @employeeStatusInactive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativo'**
  String get employeeStatusInactive;

  /// No description provided for @employeeDeleteConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Excluir colaborador {name}?'**
  String employeeDeleteConfirm(String name);

  /// No description provided for @episTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPIs'**
  String get episTitle;

  /// No description provided for @episNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo EPI'**
  String get episNew;

  /// No description provided for @episSearchHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar por nome, CA ou código'**
  String get episSearchHint;

  /// No description provided for @epiNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome do EPI'**
  String get epiNameLabel;

  /// No description provided for @epiCodeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Código de compra'**
  String get epiCodeLabel;

  /// No description provided for @epiCaLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA'**
  String get epiCaLabel;

  /// No description provided for @epiCaExpiryLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vencimento CA'**
  String get epiCaExpiryLabel;

  /// No description provided for @epiValidityDaysLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade (dias)'**
  String get epiValidityDaysLabel;

  /// No description provided for @epiStockLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque atual'**
  String get epiStockLabel;

  /// No description provided for @epiMinStockLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo'**
  String get epiMinStockLabel;

  /// No description provided for @epiStatusValid.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA Válido'**
  String get epiStatusValid;

  /// No description provided for @epiStatusExpiring.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vencendo em {days} dias'**
  String epiStatusExpiring(int days);

  /// No description provided for @epiStatusExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA Vencido'**
  String get epiStatusExpired;

  /// No description provided for @epiStatusNoStock.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem estoque'**
  String get epiStatusNoStock;

  /// No description provided for @stockTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque'**
  String get stockTitle;

  /// No description provided for @stockScan.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escanear QR'**
  String get stockScan;

  /// No description provided for @stockMoveIn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrada'**
  String get stockMoveIn;

  /// No description provided for @stockMoveOut.
  ///
  /// In pt_BR, this message translates to:
  /// **'Saída'**
  String get stockMoveOut;

  /// No description provided for @stockBatch.
  ///
  /// In pt_BR, this message translates to:
  /// **'Operação em lote'**
  String get stockBatch;

  /// No description provided for @stockMinimumAlert.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo atingido'**
  String get stockMinimumAlert;

  /// No description provided for @stockCriticalAlert.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque crítico — {name}'**
  String stockCriticalAlert(String name);

  /// No description provided for @deliveriesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas'**
  String get deliveriesTitle;

  /// No description provided for @deliveryNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova Entrega'**
  String get deliveryNew;

  /// No description provided for @deliveryStep1.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaborador'**
  String get deliveryStep1;

  /// No description provided for @deliveryStep2.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI'**
  String get deliveryStep2;

  /// No description provided for @deliveryStep3.
  ///
  /// In pt_BR, this message translates to:
  /// **'Revisão'**
  String get deliveryStep3;

  /// No description provided for @deliveryStep4.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura'**
  String get deliveryStep4;

  /// No description provided for @deliveryConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar entrega'**
  String get deliveryConfirm;

  /// No description provided for @deliverySuccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrega registrada com sucesso'**
  String get deliverySuccess;

  /// No description provided for @deliveryOfflineQueued.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrega salva — será sincronizada quando houver conexão'**
  String get deliveryOfflineQueued;

  /// No description provided for @deliverySignatureRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura obrigatória'**
  String get deliverySignatureRequired;

  /// No description provided for @deliveryClearSignature.
  ///
  /// In pt_BR, this message translates to:
  /// **'Limpar assinatura'**
  String get deliveryClearSignature;

  /// No description provided for @returnsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Devoluções'**
  String get returnsTitle;

  /// No description provided for @returnNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova Devolução'**
  String get returnNew;

  /// No description provided for @returnStep1.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar EPI'**
  String get returnStep1;

  /// No description provided for @returnStep2.
  ///
  /// In pt_BR, this message translates to:
  /// **'Condição'**
  String get returnStep2;

  /// No description provided for @returnStep3.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar'**
  String get returnStep3;

  /// No description provided for @returnConditionGood.
  ///
  /// In pt_BR, this message translates to:
  /// **'Bom estado'**
  String get returnConditionGood;

  /// No description provided for @returnConditionDamaged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Danificado'**
  String get returnConditionDamaged;

  /// No description provided for @returnConditionLost.
  ///
  /// In pt_BR, this message translates to:
  /// **'Extraviado'**
  String get returnConditionLost;

  /// No description provided for @returnSuccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Devolução registrada com sucesso.'**
  String get returnSuccess;

  /// No description provided for @returnOfflineQueued.
  ///
  /// In pt_BR, this message translates to:
  /// **'Devolução salva — será sincronizada quando houver conexão.'**
  String get returnOfflineQueued;

  /// No description provided for @recordsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fichas'**
  String get recordsTitle;

  /// No description provided for @recordsPreview.
  ///
  /// In pt_BR, this message translates to:
  /// **'Visualizar ficha'**
  String get recordsPreview;

  /// No description provided for @recordsPrint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Imprimir ficha'**
  String get recordsPrint;

  /// No description provided for @recordsSearchHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar por funcionário, código ou unidade…'**
  String get recordsSearchHint;

  /// No description provided for @recordsStatusComplete.
  ///
  /// In pt_BR, this message translates to:
  /// **'Completo'**
  String get recordsStatusComplete;

  /// No description provided for @recordsStatusPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get recordsStatusPending;

  /// No description provided for @recordsStatusOverdue.
  ///
  /// In pt_BR, this message translates to:
  /// **'Atrasado'**
  String get recordsStatusOverdue;

  /// No description provided for @purchasesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Compras'**
  String get purchasesTitle;

  /// No description provided for @purchasesNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo Pedido'**
  String get purchasesNew;

  /// No description provided for @purchaseStatusDraft.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rascunho'**
  String get purchaseStatusDraft;

  /// No description provided for @purchaseStatusSent.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviado'**
  String get purchaseStatusSent;

  /// No description provided for @purchaseStatusPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando aprovação'**
  String get purchaseStatusPending;

  /// No description provided for @purchaseStatusApproved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovado'**
  String get purchaseStatusApproved;

  /// No description provided for @purchaseStatusRejected.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rejeitado'**
  String get purchaseStatusRejected;

  /// No description provided for @purchaseStatusOrdering.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em pedido'**
  String get purchaseStatusOrdering;

  /// No description provided for @purchaseStatusReceived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recebido'**
  String get purchaseStatusReceived;

  /// No description provided for @reportsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Relatórios'**
  String get reportsTitle;

  /// No description provided for @reportsGenerate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Gerar relatório'**
  String get reportsGenerate;

  /// No description provided for @reportsPeriod.
  ///
  /// In pt_BR, this message translates to:
  /// **'Período'**
  String get reportsPeriod;

  /// No description provided for @reportsExport.
  ///
  /// In pt_BR, this message translates to:
  /// **'Exportar'**
  String get reportsExport;

  /// No description provided for @reportsSummaryTab.
  ///
  /// In pt_BR, this message translates to:
  /// **'Resumo'**
  String get reportsSummaryTab;

  /// No description provided for @reportsRequestsTab.
  ///
  /// In pt_BR, this message translates to:
  /// **'Solicitações'**
  String get reportsRequestsTab;

  /// No description provided for @reportsTotalDeliveries.
  ///
  /// In pt_BR, this message translates to:
  /// **'Total de entregas'**
  String get reportsTotalDeliveries;

  /// No description provided for @reportsTopEpis.
  ///
  /// In pt_BR, this message translates to:
  /// **'Top EPIs entregues'**
  String get reportsTopEpis;

  /// No description provided for @reportsTopSectors.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas por setor'**
  String get reportsTopSectors;

  /// No description provided for @reportsRequestStatusPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando'**
  String get reportsRequestStatusPending;

  /// No description provided for @reportsRequestStatusProcessing.
  ///
  /// In pt_BR, this message translates to:
  /// **'Processando'**
  String get reportsRequestStatusProcessing;

  /// No description provided for @reportsRequestStatusCompleted.
  ///
  /// In pt_BR, this message translates to:
  /// **'Concluído'**
  String get reportsRequestStatusCompleted;

  /// No description provided for @reportsRequestStatusFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falhou'**
  String get reportsRequestStatusFailed;

  /// No description provided for @reportsAllUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as unidades'**
  String get reportsAllUnits;

  /// No description provided for @reportsRequestDialogTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Solicitar relatório'**
  String get reportsRequestDialogTitle;

  /// No description provided for @reportsRequestYear.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ano'**
  String get reportsRequestYear;

  /// No description provided for @reportsRequestMonth.
  ///
  /// In pt_BR, this message translates to:
  /// **'Mês'**
  String get reportsRequestMonth;

  /// No description provided for @reportsRequestNotes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observações (opcional)'**
  String get reportsRequestNotes;

  /// No description provided for @reportsRequestSubmit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Solicitar'**
  String get reportsRequestSubmit;

  /// No description provided for @reportsNoRequests.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma solicitação'**
  String get reportsNoRequests;

  /// No description provided for @reportsNoData.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum dado disponível'**
  String get reportsNoData;

  /// No description provided for @reportsRequestSuccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Solicitação enviada com sucesso.'**
  String get reportsRequestSuccess;

  /// No description provided for @companiesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresas'**
  String get companiesTitle;

  /// No description provided for @companiesSearchHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar por nome ou CNPJ'**
  String get companiesSearchHint;

  /// No description provided for @companyStatusActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ativo'**
  String get companyStatusActive;

  /// No description provided for @companyStatusInactive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativo'**
  String get companyStatusInactive;

  /// No description provided for @companyStatusSuspended.
  ///
  /// In pt_BR, this message translates to:
  /// **'Suspenso'**
  String get companyStatusSuspended;

  /// No description provided for @settingsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurações'**
  String get settingsTitle;

  /// No description provided for @settingsLanguage.
  ///
  /// In pt_BR, this message translates to:
  /// **'Idioma'**
  String get settingsLanguage;

  /// No description provided for @settingsLanguageUser.
  ///
  /// In pt_BR, this message translates to:
  /// **'Idioma do usuário'**
  String get settingsLanguageUser;

  /// No description provided for @settingsLanguageCompany.
  ///
  /// In pt_BR, this message translates to:
  /// **'Idioma da empresa'**
  String get settingsLanguageCompany;

  /// No description provided for @settingsTheme.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tema'**
  String get settingsTheme;

  /// No description provided for @settingsThemeLight.
  ///
  /// In pt_BR, this message translates to:
  /// **'Claro'**
  String get settingsThemeLight;

  /// No description provided for @settingsThemeDark.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escuro'**
  String get settingsThemeDark;

  /// No description provided for @settingsThemeSystem.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sistema'**
  String get settingsThemeSystem;

  /// No description provided for @settingsAppSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aplicativo'**
  String get settingsAppSection;

  /// No description provided for @settingsFichaSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ficha'**
  String get settingsFichaSection;

  /// No description provided for @settingsFichaTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Título da ficha'**
  String get settingsFichaTitle;

  /// No description provided for @settingsFichaDeclaration.
  ///
  /// In pt_BR, this message translates to:
  /// **'Declaração'**
  String get settingsFichaDeclaration;

  /// No description provided for @settingsFichaObservations.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observações'**
  String get settingsFichaObservations;

  /// No description provided for @settingsFichaTracking.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rastreabilidade'**
  String get settingsFichaTracking;

  /// No description provided for @settingsSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurações salvas com sucesso.'**
  String get settingsSaved;

  /// No description provided for @portalTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Portal do Colaborador'**
  String get portalTitle;

  /// No description provided for @portalScanQr.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escanear QR Code'**
  String get portalScanQr;

  /// No description provided for @portalEnterCpf.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe seu CPF'**
  String get portalEnterCpf;

  /// No description provided for @portalCpfHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ex: 000.000.000-00'**
  String get portalCpfHint;

  /// No description provided for @portalCpfVerify.
  ///
  /// In pt_BR, this message translates to:
  /// **'Acessar portal'**
  String get portalCpfVerify;

  /// No description provided for @portalHistory.
  ///
  /// In pt_BR, this message translates to:
  /// **'Meu histórico de EPIs'**
  String get portalHistory;

  /// No description provided for @portalSignature.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar assinatura'**
  String get portalSignature;

  /// No description provided for @portalSignatureInstruction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assine no espaço abaixo para confirmar o recebimento'**
  String get portalSignatureInstruction;

  /// No description provided for @portalDeliveries.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregas'**
  String get portalDeliveries;

  /// No description provided for @portalFichas.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fichas'**
  String get portalFichas;

  /// No description provided for @portalSignDelivery.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinar'**
  String get portalSignDelivery;

  /// No description provided for @portalSignAll.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinar todas'**
  String get portalSignAll;

  /// No description provided for @portalSigned.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinado'**
  String get portalSigned;

  /// No description provided for @portalUnsigned.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get portalUnsigned;

  /// No description provided for @portalSignSuccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura registrada com sucesso.'**
  String get portalSignSuccess;

  /// No description provided for @portalNoDeliveries.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma entrega encontrada'**
  String get portalNoDeliveries;

  /// No description provided for @portalQty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Qtd'**
  String get portalQty;

  /// No description provided for @errorGeneric.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ocorreu um erro. Tente novamente.'**
  String get errorGeneric;

  /// No description provided for @errorNetwork.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem conexão com a internet'**
  String get errorNetwork;

  /// No description provided for @errorUnauthorized.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sessão expirada. Faça login novamente.'**
  String get errorUnauthorized;

  /// No description provided for @errorNotFound.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registro não encontrado'**
  String get errorNotFound;

  /// No description provided for @errorServerError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Erro no servidor. Tente mais tarde.'**
  String get errorServerError;

  /// No description provided for @statusActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ativo'**
  String get statusActive;

  /// No description provided for @statusInactive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativo'**
  String get statusInactive;

  /// No description provided for @statusExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vencido'**
  String get statusExpired;

  /// No description provided for @statusExpiring.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vencendo'**
  String get statusExpiring;

  /// No description provided for @statusPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get statusPending;

  /// No description provided for @statusApproved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovado'**
  String get statusApproved;

  /// No description provided for @statusRejected.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rejeitado'**
  String get statusRejected;

  /// No description provided for @statusInReview.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em análise'**
  String get statusInReview;

  /// No description provided for @confirmDeleteTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar exclusão'**
  String get confirmDeleteTitle;

  /// No description provided for @confirmDeleteMessage.
  ///
  /// In pt_BR, this message translates to:
  /// **'Esta ação não pode ser desfeita.'**
  String get confirmDeleteMessage;

  /// No description provided for @confirmDeleteButton.
  ///
  /// In pt_BR, this message translates to:
  /// **'Excluir'**
  String get confirmDeleteButton;

  /// No description provided for @employeeContactTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Contatar colaborador'**
  String get employeeContactTitle;

  /// No description provided for @employeeContactWhatsapp.
  ///
  /// In pt_BR, this message translates to:
  /// **'WhatsApp'**
  String get employeeContactWhatsapp;

  /// No description provided for @employeeContactEmail.
  ///
  /// In pt_BR, this message translates to:
  /// **'E-mail'**
  String get employeeContactEmail;

  /// No description provided for @employeeContactPdf.
  ///
  /// In pt_BR, this message translates to:
  /// **'Baixar PDF'**
  String get employeeContactPdf;

  /// No description provided for @employeeContactLaunching.
  ///
  /// In pt_BR, this message translates to:
  /// **'Abrindo...'**
  String get employeeContactLaunching;

  /// No description provided for @employeeContactPdfDownloading.
  ///
  /// In pt_BR, this message translates to:
  /// **'Baixando PDF...'**
  String get employeeContactPdfDownloading;

  /// No description provided for @employeeContactErrorNoApp.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum app disponível para abrir este link'**
  String get employeeContactErrorNoApp;

  /// No description provided for @employeeContactErrorGeneric.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falha ao contatar colaborador. Tente novamente.'**
  String get employeeContactErrorGeneric;

  /// No description provided for @employeeContactPdfError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falha ao baixar o PDF. Tente novamente.'**
  String get employeeContactPdfError;

  /// No description provided for @offlineBanner.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem conexão — dados salvos localmente'**
  String get offlineBanner;

  /// No description provided for @syncingBanner.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sincronizando dados...'**
  String get syncingBanner;

  /// No description provided for @syncDone.
  ///
  /// In pt_BR, this message translates to:
  /// **'Dados sincronizados'**
  String get syncDone;

  /// No description provided for @searchEmployeeHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar colaborador...'**
  String get searchEmployeeHint;

  /// No description provided for @searchEpiHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar EPI...'**
  String get searchEpiHint;

  /// No description provided for @fieldQuantity.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade'**
  String get fieldQuantity;

  /// No description provided for @filterAll.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todos'**
  String get filterAll;

  /// No description provided for @deliveryStockAvailable.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque: {qty}'**
  String deliveryStockAvailable(int qty);

  /// No description provided for @deliveryDateLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data da entrega'**
  String get deliveryDateLabel;

  /// No description provided for @deliveryNextReplacement.
  ///
  /// In pt_BR, this message translates to:
  /// **'Próxima substituição'**
  String get deliveryNextReplacement;

  /// No description provided for @deliveryDateValue.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data: {date}'**
  String deliveryDateValue(String date);

  /// No description provided for @returnSelectDelivery.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar entrega para devolver'**
  String get returnSelectDelivery;

  /// No description provided for @returnDeliveredInfo.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entregue em {date} · Qtd: {qty}'**
  String returnDeliveredInfo(String date, int qty);

  /// No description provided for @returnConditionTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Condição do EPI'**
  String get returnConditionTitle;

  /// No description provided for @returnDestinationTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Destino'**
  String get returnDestinationTitle;

  /// No description provided for @returnDestDiscard.
  ///
  /// In pt_BR, this message translates to:
  /// **'Descarte'**
  String get returnDestDiscard;

  /// No description provided for @returnDestRepair.
  ///
  /// In pt_BR, this message translates to:
  /// **'Manutenção'**
  String get returnDestRepair;

  /// No description provided for @returnDestStock.
  ///
  /// In pt_BR, this message translates to:
  /// **'Retornar ao estoque'**
  String get returnDestStock;

  /// No description provided for @returnSubmit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registrar Devolução'**
  String get returnSubmit;

  /// No description provided for @returnDeliveryDateInfo.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrega: {date}'**
  String returnDeliveryDateInfo(String date);

  /// No description provided for @returnQuantityInfo.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade: {qty}'**
  String returnQuantityInfo(int qty);

  /// No description provided for @purchaseTitleLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Título da requisição'**
  String get purchaseTitleLabel;

  /// No description provided for @purchaseSelectUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione uma unidade'**
  String get purchaseSelectUnit;

  /// No description provided for @purchaseItemsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Itens da requisição'**
  String get purchaseItemsTitle;

  /// No description provided for @purchaseAddEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'Adicionar EPI'**
  String get purchaseAddEpi;

  /// No description provided for @purchaseNoItems.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum item adicionado'**
  String get purchaseNoItems;

  /// No description provided for @purchaseCreate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Criar Requisição'**
  String get purchaseCreate;

  /// No description provided for @purchaseAddAtLeastOne.
  ///
  /// In pt_BR, this message translates to:
  /// **'Adicione pelo menos um item'**
  String get purchaseAddAtLeastOne;

  /// No description provided for @purchaseQuantityColon.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade:'**
  String get purchaseQuantityColon;

  /// No description provided for @purchaseItemsCount.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count} itens'**
  String purchaseItemsCount(int count);

  /// No description provided for @purchaseStatusAwaiting.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando'**
  String get purchaseStatusAwaiting;

  /// No description provided for @purchaseStatusCorrection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Correção solicitada'**
  String get purchaseStatusCorrection;

  /// No description provided for @purchaseStatusAwaitingReceipt.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando recebimento'**
  String get purchaseStatusAwaitingReceipt;

  /// No description provided for @purchaseStatusCompleted.
  ///
  /// In pt_BR, this message translates to:
  /// **'Concluído'**
  String get purchaseStatusCompleted;

  /// No description provided for @purchaseStatusCancelled.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelado'**
  String get purchaseStatusCancelled;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return lookupAppLocalizations(locale);
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'es', 'fr', 'no', 'pt'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

Future<AppLocalizations> lookupAppLocalizations(Locale locale) {
  // Lookup logic when language+country codes are specified.
  switch (locale.languageCode) {
    case 'en':
      {
        switch (locale.countryCode) {
          case 'US':
            return app_localizations_en.loadLibrary().then(
                (dynamic _) => app_localizations_en.AppLocalizationsEnUs());
        }
        break;
      }
    case 'es':
      {
        switch (locale.countryCode) {
          case 'ES':
            return app_localizations_es.loadLibrary().then(
                (dynamic _) => app_localizations_es.AppLocalizationsEsEs());
        }
        break;
      }
    case 'fr':
      {
        switch (locale.countryCode) {
          case 'FR':
            return app_localizations_fr.loadLibrary().then(
                (dynamic _) => app_localizations_fr.AppLocalizationsFrFr());
        }
        break;
      }
    case 'no':
      {
        switch (locale.countryCode) {
          case 'NO':
            return app_localizations_no.loadLibrary().then(
                (dynamic _) => app_localizations_no.AppLocalizationsNoNo());
        }
        break;
      }
    case 'pt':
      {
        switch (locale.countryCode) {
          case 'BR':
            return app_localizations_pt.loadLibrary().then(
                (dynamic _) => app_localizations_pt.AppLocalizationsPtBr());
        }
        break;
      }
  }

  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return app_localizations_en
          .loadLibrary()
          .then((dynamic _) => app_localizations_en.AppLocalizationsEn());
    case 'es':
      return app_localizations_es
          .loadLibrary()
          .then((dynamic _) => app_localizations_es.AppLocalizationsEs());
    case 'fr':
      return app_localizations_fr
          .loadLibrary()
          .then((dynamic _) => app_localizations_fr.AppLocalizationsFr());
    case 'no':
      return app_localizations_no
          .loadLibrary()
          .then((dynamic _) => app_localizations_no.AppLocalizationsNo());
    case 'pt':
      return app_localizations_pt
          .loadLibrary()
          .then((dynamic _) => app_localizations_pt.AppLocalizationsPt());
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
