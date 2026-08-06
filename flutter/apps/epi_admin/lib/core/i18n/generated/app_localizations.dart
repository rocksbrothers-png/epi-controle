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

  /// No description provided for @reportsExportPdf.
  ///
  /// In pt_BR, this message translates to:
  /// **'Exportar PDF'**
  String get reportsExportPdf;

  /// No description provided for @feedbackForward.
  ///
  /// In pt_BR, this message translates to:
  /// **'Encaminhar'**
  String get feedbackForward;

  /// No description provided for @feedbackReject.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rejeitar'**
  String get feedbackReject;

  /// No description provided for @feedbackApprove.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovar'**
  String get feedbackApprove;

  /// No description provided for @feedbackJustification.
  ///
  /// In pt_BR, this message translates to:
  /// **'Justificativa'**
  String get feedbackJustification;

  /// No description provided for @feedbackRejectReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Motivo da rejeição'**
  String get feedbackRejectReason;

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

  /// Rótulo do menu de avaliações/feedback
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

  /// No description provided for @employeeCpfLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CPF'**
  String get employeeCpfLabel;

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

  /// No description provided for @employeeUnitLockedHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade definida pelo seu perfil de acesso.'**
  String get employeeUnitLockedHint;

  /// No description provided for @employeeLegalEntityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get employeeLegalEntityLabel;

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

  /// No description provided for @epiSectorLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Setor'**
  String get epiSectorLabel;

  /// No description provided for @epiSectionLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Seção do EPI'**
  String get epiSectionLabel;

  /// No description provided for @epiModelLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Modelo/referência'**
  String get epiModelLabel;

  /// No description provided for @epiManufacturerLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fabricante'**
  String get epiManufacturerLabel;

  /// No description provided for @epiSupplierLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fornecedor'**
  String get epiSupplierLabel;

  /// No description provided for @epiUnitMeasureLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade de medida'**
  String get epiUnitMeasureLabel;

  /// No description provided for @epiValidityDateLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data de validade'**
  String get epiValidityDateLabel;

  /// No description provided for @epiManufacturerValidityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade (meses)'**
  String get epiManufacturerValidityLabel;

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

  /// No description provided for @purchaseOrdersTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ordens de Compra'**
  String get purchaseOrdersTitle;

  /// No description provided for @poApprove.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovar'**
  String get poApprove;

  /// No description provided for @poReceive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Receber'**
  String get poReceive;

  /// No description provided for @poQuantityReceived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Qtd. recebida'**
  String get poQuantityReceived;

  /// No description provided for @poReceiveNotes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observação'**
  String get poReceiveNotes;

  /// No description provided for @poManufacturerValidity.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade do fabricante'**
  String get poManufacturerValidity;

  /// No description provided for @poManufacturerValidityHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informar data'**
  String get poManufacturerValidityHint;

  /// No description provided for @poManufacturerValidityRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe a validade do fabricante de todos os EPIs recebidos.'**
  String get poManufacturerValidityRequired;

  /// No description provided for @poOcrDateNotFound.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível identificar a data. Tente novamente.'**
  String get poOcrDateNotFound;

  /// No description provided for @poOcrCameraFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falha na leitura por câmera.'**
  String get poOcrCameraFailed;

  /// No description provided for @poPickDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar data'**
  String get poPickDate;

  /// No description provided for @poReadDateCamera.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ler data por câmera (OCR)'**
  String get poReadDateCamera;

  /// No description provided for @poCheck.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conferir'**
  String get poCheck;

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

  /// No description provided for @suppliersTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fornecedores'**
  String get suppliersTitle;

  /// No description provided for @supplierNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo fornecedor'**
  String get supplierNew;

  /// No description provided for @supplierEdit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Editar fornecedor'**
  String get supplierEdit;

  /// No description provided for @supplierCnpjLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get supplierCnpjLabel;

  /// No description provided for @supplierPhoneLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Telefone'**
  String get supplierPhoneLabel;

  /// No description provided for @supplierPaymentTermsLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Condições de pagamento'**
  String get supplierPaymentTermsLabel;

  /// No description provided for @supplierIntegrationLevelLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nível de integração'**
  String get supplierIntegrationLevelLabel;

  /// No description provided for @supplierInactiveLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativo'**
  String get supplierInactiveLabel;

  /// No description provided for @supplierCatalogTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Catálogo do fornecedor'**
  String get supplierCatalogTitle;

  /// No description provided for @catalogNewProduct.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo produto'**
  String get catalogNewProduct;

  /// No description provided for @catalogSkuLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'SKU'**
  String get catalogSkuLabel;

  /// No description provided for @catalogDescriptionLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Descrição'**
  String get catalogDescriptionLabel;

  /// No description provided for @catalogLastPriceLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Último preço'**
  String get catalogLastPriceLabel;

  /// No description provided for @catalogLeadTimeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Prazo (dias)'**
  String get catalogLeadTimeLabel;

  /// No description provided for @quotesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cotações'**
  String get quotesTitle;

  /// No description provided for @quotesNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova cotação'**
  String get quotesNew;

  /// No description provided for @quotesSelectSuppliers.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione os fornecedores'**
  String get quotesSelectSuppliers;

  /// No description provided for @quoteSendEmail.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviar por e-mail'**
  String get quoteSendEmail;

  /// No description provided for @quoteSendPortal.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviar pelo portal'**
  String get quoteSendPortal;

  /// No description provided for @quoteAnswerAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registrar resposta'**
  String get quoteAnswerAction;

  /// No description provided for @quoteSelectWinner.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar vencedora'**
  String get quoteSelectWinner;

  /// No description provided for @quoteComparisonTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Comparação de cotações'**
  String get quoteComparisonTitle;

  /// No description provided for @quoteFreightLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Frete'**
  String get quoteFreightLabel;

  /// No description provided for @quoteUnitPriceLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preço unitário'**
  String get quoteUnitPriceLabel;

  /// No description provided for @quoteDeclinedLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recusado'**
  String get quoteDeclinedLabel;

  /// No description provided for @quoteBestPriceLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Melhor preço'**
  String get quoteBestPriceLabel;

  /// No description provided for @quoteBestLeadTimeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Melhor prazo'**
  String get quoteBestLeadTimeLabel;

  /// No description provided for @quoteCreatePo.
  ///
  /// In pt_BR, this message translates to:
  /// **'Gerar PO a partir da cotação vencedora?'**
  String get quoteCreatePo;

  /// No description provided for @poSupplierActionsTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fornecedor e entrega'**
  String get poSupplierActionsTitle;

  /// No description provided for @poSendToSupplier.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviar ao fornecedor'**
  String get poSendToSupplier;

  /// No description provided for @poPortalLinkAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviar link do portal'**
  String get poPortalLinkAction;

  /// No description provided for @poRegisterConfirmation.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registrar confirmação'**
  String get poRegisterConfirmation;

  /// No description provided for @poTrackingTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Acompanhamento'**
  String get poTrackingTitle;

  /// No description provided for @poDeliveryForecastLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Previsão de entrega'**
  String get poDeliveryForecastLabel;

  /// No description provided for @poCarrierLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Transportadora'**
  String get poCarrierLabel;

  /// No description provided for @poTrackingCodeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Código de rastreio'**
  String get poTrackingCodeLabel;

  /// No description provided for @commentLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Comentário'**
  String get commentLabel;

  /// No description provided for @actionSentSuccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Enviado com sucesso'**
  String get actionSentSuccess;

  /// No description provided for @myCompanyTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Minha Empresa'**
  String get myCompanyTitle;

  /// No description provided for @myCompanySubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Dados, identidade visual e domínio da sua empresa'**
  String get myCompanySubtitle;

  /// No description provided for @myCompanySaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurações da empresa salvas com sucesso.'**
  String get myCompanySaved;

  /// No description provided for @myCompanyLoadError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar os dados da empresa.'**
  String get myCompanyLoadError;

  /// No description provided for @myCompanyContractSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Contrato (somente leitura)'**
  String get myCompanyContractSection;

  /// No description provided for @myCompanyPlan.
  ///
  /// In pt_BR, this message translates to:
  /// **'Plano'**
  String get myCompanyPlan;

  /// No description provided for @myCompanyUserLimit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Limite de usuários'**
  String get myCompanyUserLimit;

  /// No description provided for @myCompanyLicense.
  ///
  /// In pt_BR, this message translates to:
  /// **'Licença'**
  String get myCompanyLicense;

  /// No description provided for @myCompanyRegistrationSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Dados cadastrais'**
  String get myCompanyRegistrationSection;

  /// No description provided for @myCompanyName.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome fantasia'**
  String get myCompanyName;

  /// No description provided for @myCompanyLegalName.
  ///
  /// In pt_BR, this message translates to:
  /// **'Razão social'**
  String get myCompanyLegalName;

  /// No description provided for @myCompanyCnpj.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get myCompanyCnpj;

  /// No description provided for @myCompanyStateRegistration.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inscrição estadual'**
  String get myCompanyStateRegistration;

  /// No description provided for @myCompanyMunicipalRegistration.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inscrição municipal'**
  String get myCompanyMunicipalRegistration;

  /// No description provided for @myCompanyAddress.
  ///
  /// In pt_BR, this message translates to:
  /// **'Endereço'**
  String get myCompanyAddress;

  /// No description provided for @myCompanyPhone.
  ///
  /// In pt_BR, this message translates to:
  /// **'Telefone'**
  String get myCompanyPhone;

  /// No description provided for @myCompanyWhatsapp.
  ///
  /// In pt_BR, this message translates to:
  /// **'WhatsApp'**
  String get myCompanyWhatsapp;

  /// No description provided for @myCompanyEmail.
  ///
  /// In pt_BR, this message translates to:
  /// **'E-mail institucional'**
  String get myCompanyEmail;

  /// No description provided for @myCompanyWebsite.
  ///
  /// In pt_BR, this message translates to:
  /// **'Website'**
  String get myCompanyWebsite;

  /// No description provided for @myCompanyIdentitySection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Identidade e tema'**
  String get myCompanyIdentitySection;

  /// No description provided for @myCompanyDisplayName.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome exibido no sistema'**
  String get myCompanyDisplayName;

  /// No description provided for @myCompanyInstitutionalMessage.
  ///
  /// In pt_BR, this message translates to:
  /// **'Mensagem institucional'**
  String get myCompanyInstitutionalMessage;

  /// No description provided for @myCompanyPrimaryColor.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cor principal (hex)'**
  String get myCompanyPrimaryColor;

  /// No description provided for @myCompanySecondaryColor.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cor secundária (hex)'**
  String get myCompanySecondaryColor;

  /// No description provided for @myCompanyPreferencesSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preferências'**
  String get myCompanyPreferencesSection;

  /// No description provided for @myCompanyTimezone.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fuso horário'**
  String get myCompanyTimezone;

  /// No description provided for @myCompanySave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar configurações da empresa'**
  String get myCompanySave;

  /// No description provided for @myCompanyDomainsSection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Domínios'**
  String get myCompanyDomainsSection;

  /// No description provided for @myCompanyDomainField.
  ///
  /// In pt_BR, this message translates to:
  /// **'Domínio'**
  String get myCompanyDomainField;

  /// No description provided for @myCompanyDomainTypePlatform.
  ///
  /// In pt_BR, this message translates to:
  /// **'Subdomínio da plataforma'**
  String get myCompanyDomainTypePlatform;

  /// No description provided for @myCompanyDomainTypeCustomSub.
  ///
  /// In pt_BR, this message translates to:
  /// **'Subdomínio personalizado'**
  String get myCompanyDomainTypeCustomSub;

  /// No description provided for @myCompanyDomainTypeCustom.
  ///
  /// In pt_BR, this message translates to:
  /// **'Domínio personalizado'**
  String get myCompanyDomainTypeCustom;

  /// No description provided for @myCompanyDomainAdd.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registrar domínio'**
  String get myCompanyDomainAdd;

  /// No description provided for @myCompanyDomainVerify.
  ///
  /// In pt_BR, this message translates to:
  /// **'Verificar'**
  String get myCompanyDomainVerify;

  /// No description provided for @myCompanyDomainDelete.
  ///
  /// In pt_BR, this message translates to:
  /// **'Remover'**
  String get myCompanyDomainDelete;

  /// No description provided for @myCompanyDomainPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get myCompanyDomainPending;

  /// No description provided for @myCompanyDomainVerified.
  ///
  /// In pt_BR, this message translates to:
  /// **'Verificado'**
  String get myCompanyDomainVerified;

  /// No description provided for @myCompanyDomainFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falhou'**
  String get myCompanyDomainFailed;

  /// No description provided for @myCompanyDomainPrimary.
  ///
  /// In pt_BR, this message translates to:
  /// **'Principal'**
  String get myCompanyDomainPrimary;

  /// No description provided for @myCompanyDomainCname.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aponte o CNAME para'**
  String get myCompanyDomainCname;

  /// No description provided for @myCompanyDomainTxt.
  ///
  /// In pt_BR, this message translates to:
  /// **'Crie o registro TXT'**
  String get myCompanyDomainTxt;

  /// No description provided for @myCompanyDomainToken.
  ///
  /// In pt_BR, this message translates to:
  /// **'Valor do TXT'**
  String get myCompanyDomainToken;

  /// No description provided for @handoverScanAgain.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova conferência'**
  String get handoverScanAgain;

  /// No description provided for @legalEntitiesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJs'**
  String get legalEntitiesTitle;

  /// No description provided for @legalEntitiesNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo CNPJ'**
  String get legalEntitiesNew;

  /// No description provided for @legalEntityLegalNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Razão social'**
  String get legalEntityLegalNameLabel;

  /// No description provided for @legalEntityTradeNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome fantasia'**
  String get legalEntityTradeNameLabel;

  /// No description provided for @legalEntityTypeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tipo'**
  String get legalEntityTypeLabel;

  /// No description provided for @legalEntityInactiveBadge.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativo'**
  String get legalEntityInactiveBadge;

  /// No description provided for @legalEntityDeactivate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Inativar CNPJ'**
  String get legalEntityDeactivate;

  /// No description provided for @legalEntityDeactivateHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'O histórico jurídico é preservado. O CNPJ deixa de ser usado em novas operações.'**
  String get legalEntityDeactivateHint;

  /// No description provided for @legalEntityShowInactive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Mostrar inativos'**
  String get legalEntityShowInactive;

  /// No description provided for @legalEntitiesEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum CNPJ cadastrado.'**
  String get legalEntitiesEmpty;

  /// No description provided for @legalEntityMunicipalityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Município'**
  String get legalEntityMunicipalityLabel;

  /// No description provided for @legalEntitiesImport.
  ///
  /// In pt_BR, this message translates to:
  /// **'Importar planilha'**
  String get legalEntitiesImport;

  /// No description provided for @legalEntitiesImportHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Copie as linhas da planilha (com a linha de cabeçalho) e cole abaixo. Aceita colunas em português ou inglês.'**
  String get legalEntitiesImportHint;

  /// No description provided for @legalEntitiesImportResult.
  ///
  /// In pt_BR, this message translates to:
  /// **'Importação concluída'**
  String get legalEntitiesImportResult;

  /// No description provided for @dashboardFilterLegalEntity.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get dashboardFilterLegalEntity;

  /// No description provided for @dashboardFilterUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get dashboardFilterUnit;

  /// No description provided for @dashboardFilterSector.
  ///
  /// In pt_BR, this message translates to:
  /// **'Setor'**
  String get dashboardFilterSector;

  /// No description provided for @dashboardFilterAll.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todos'**
  String get dashboardFilterAll;

  /// No description provided for @dashboardFilterClear.
  ///
  /// In pt_BR, this message translates to:
  /// **'Limpar filtros'**
  String get dashboardFilterClear;

  /// No description provided for @legalEntityTransferTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Transferir vínculo jurídico'**
  String get legalEntityTransferTitle;

  /// No description provided for @legalEntityTransferHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'O CNPJ é o vínculo do contrato de trabalho e não muda em transferência de unidade. Esta alteração é auditada e exige justificativa.'**
  String get legalEntityTransferHint;

  /// No description provided for @legalEntityTransferReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Justificativa'**
  String get legalEntityTransferReason;

  /// No description provided for @legalEntityTransferTarget.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo CNPJ'**
  String get legalEntityTransferTarget;

  /// No description provided for @legalEntityTransferAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Transferir'**
  String get legalEntityTransferAction;

  /// No description provided for @legalEntityTransferHistory.
  ///
  /// In pt_BR, this message translates to:
  /// **'Histórico de vínculo'**
  String get legalEntityTransferHistory;

  /// No description provided for @unitTransferTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Transferir de unidade'**
  String get unitTransferTitle;

  /// No description provided for @unitTransferHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Movimentação de unidade operacional — temporária ou definitiva. Gera vínculo auditável e não altera o CNPJ do colaborador.'**
  String get unitTransferHint;

  /// No description provided for @unitTransferTarget.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade destino'**
  String get unitTransferTarget;

  /// No description provided for @unitTransferType.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tipo de movimentação'**
  String get unitTransferType;

  /// No description provided for @unitTransferTypeTemporary.
  ///
  /// In pt_BR, this message translates to:
  /// **'Temporária'**
  String get unitTransferTypeTemporary;

  /// No description provided for @unitTransferTypeDefinitive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Definitiva'**
  String get unitTransferTypeDefinitive;

  /// No description provided for @unitTransferStartDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data início'**
  String get unitTransferStartDate;

  /// No description provided for @unitTransferEndDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data fim (opcional)'**
  String get unitTransferEndDate;

  /// No description provided for @unitTransferNotes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observação (opcional)'**
  String get unitTransferNotes;

  /// No description provided for @unitTransferAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Transferir'**
  String get unitTransferAction;

  /// No description provided for @myCompanyStockScope.
  ///
  /// In pt_BR, this message translates to:
  /// **'Consolidar saldos de estoque por'**
  String get myCompanyStockScope;

  /// No description provided for @myCompanyStockScopeHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Esta configuração altera apenas a visualização consolidada dos saldos. Entradas, reservas, saídas, entregas e demais movimentações permanecem vinculadas ao estoque de cada unidade.'**
  String get myCompanyStockScopeHint;

  /// No description provided for @myCompanyStockScopeUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get myCompanyStockScopeUnit;

  /// No description provided for @myCompanyStockScopeLegalEntity.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get myCompanyStockScopeLegalEntity;

  /// No description provided for @myCompanyStockScopeCompany.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresa'**
  String get myCompanyStockScopeCompany;

  /// No description provided for @navLegalEntities.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJs'**
  String get navLegalEntities;

  /// No description provided for @unitLegalEntityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ responsável'**
  String get unitLegalEntityLabel;

  /// No description provided for @unitLegalEntityHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pessoa jurídica que responde pelas operações e pelo estoque desta unidade.'**
  String get unitLegalEntityHint;

  /// No description provided for @employeeEmploymentTypeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tipo de Vínculo'**
  String get employeeEmploymentTypeLabel;

  /// No description provided for @employeeSourceCompanyLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresa de Origem'**
  String get employeeSourceCompanyLabel;

  /// No description provided for @employeeSourceCompanyHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome da empresa de origem do colaborador'**
  String get employeeSourceCompanyHint;

  /// No description provided for @employmentTypeClt.
  ///
  /// In pt_BR, this message translates to:
  /// **'CLT'**
  String get employmentTypeClt;

  /// No description provided for @employmentTypeOutsourced.
  ///
  /// In pt_BR, this message translates to:
  /// **'Terceirizado'**
  String get employmentTypeOutsourced;

  /// No description provided for @employmentTypeTemporary.
  ///
  /// In pt_BR, this message translates to:
  /// **'Temporário'**
  String get employmentTypeTemporary;

  /// No description provided for @employmentTypeServiceProvider.
  ///
  /// In pt_BR, this message translates to:
  /// **'Prestador de Serviço'**
  String get employmentTypeServiceProvider;

  /// No description provided for @employmentTypeApprentice.
  ///
  /// In pt_BR, this message translates to:
  /// **'Menor Aprendiz'**
  String get employmentTypeApprentice;

  /// No description provided for @employmentTypeTrainee.
  ///
  /// In pt_BR, this message translates to:
  /// **'Praticante'**
  String get employmentTypeTrainee;

  /// No description provided for @employmentTypeIntern.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estagiário'**
  String get employmentTypeIntern;

  /// No description provided for @navTerceirizados.
  ///
  /// In pt_BR, this message translates to:
  /// **'Terceirizados e Prestadores'**
  String get navTerceirizados;

  /// No description provided for @outsourcedCompaniesTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Terceirizados e Prestadores'**
  String get outsourcedCompaniesTitle;

  /// No description provided for @outsourcedCompaniesEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma empresa terceirizada cadastrada.'**
  String get outsourcedCompaniesEmpty;

  /// No description provided for @outsourcedCompaniesSearchHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar por nome ou CNPJ'**
  String get outsourcedCompaniesSearchHint;

  /// No description provided for @outsourcedCompanyNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova empresa'**
  String get outsourcedCompanyNew;

  /// No description provided for @outsourcedCompanyLegalNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Razão Social'**
  String get outsourcedCompanyLegalNameLabel;

  /// No description provided for @outsourcedCompanyTradeNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome Fantasia'**
  String get outsourcedCompanyTradeNameLabel;

  /// No description provided for @outsourcedCompanyCnpjLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get outsourcedCompanyCnpjLabel;

  /// No description provided for @outsourcedCompanyCnpjHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Opcional no Cadastro Simplificado'**
  String get outsourcedCompanyCnpjHint;

  /// No description provided for @outsourcedCompanyKindLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tipo da Empresa'**
  String get outsourcedCompanyKindLabel;

  /// No description provided for @outsourcedCompanyKindOutsourced.
  ///
  /// In pt_BR, this message translates to:
  /// **'Terceirizada'**
  String get outsourcedCompanyKindOutsourced;

  /// No description provided for @outsourcedCompanyKindServiceProvider.
  ///
  /// In pt_BR, this message translates to:
  /// **'Prestadora de Serviço'**
  String get outsourcedCompanyKindServiceProvider;

  /// No description provided for @outsourcedCompanyKindOther.
  ///
  /// In pt_BR, this message translates to:
  /// **'Outro'**
  String get outsourcedCompanyKindOther;

  /// No description provided for @outsourcedCompanyResponsibilityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Responsabilidade pelo Fornecimento de EPI'**
  String get outsourcedCompanyResponsibilityLabel;

  /// No description provided for @outsourcedCompanyUnitLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get outsourcedCompanyUnitLabel;

  /// No description provided for @outsourcedCompanyUnitAll.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as unidades (padrão)'**
  String get outsourcedCompanyUnitAll;

  /// No description provided for @outsourcedCompanyStatusLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Situação'**
  String get outsourcedCompanyStatusLabel;

  /// No description provided for @outsourcedCompanySave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar'**
  String get outsourcedCompanySave;

  /// No description provided for @outsourcedCompanyCancel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelar'**
  String get outsourcedCompanyCancel;

  /// No description provided for @outsourcedCompanyPromote.
  ///
  /// In pt_BR, this message translates to:
  /// **'Promover a Cadastro Padrão'**
  String get outsourcedCompanyPromote;

  /// No description provided for @outsourcedCompanyPromoteConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Promover ao Cadastro Padrão?'**
  String get outsourcedCompanyPromoteConfirmTitle;

  /// No description provided for @outsourcedCompanyPromoteConfirmBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.'**
  String get outsourcedCompanyPromoteConfirmBody;

  /// No description provided for @outsourcedCompanySimplifiedBadge.
  ///
  /// In pt_BR, this message translates to:
  /// **'Simplificado'**
  String get outsourcedCompanySimplifiedBadge;

  /// No description provided for @outsourcedCompanyStandardBadge.
  ///
  /// In pt_BR, this message translates to:
  /// **'Padrão'**
  String get outsourcedCompanyStandardBadge;

  /// No description provided for @outsourcedTabCompanies.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresas'**
  String get outsourcedTabCompanies;

  /// No description provided for @outsourcedTabEmployees.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cadastro de Colaboradores'**
  String get outsourcedTabEmployees;

  /// No description provided for @outsourcedTabReports.
  ///
  /// In pt_BR, this message translates to:
  /// **'Relatórios'**
  String get outsourcedTabReports;

  /// No description provided for @outsourcedShowActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ver ativos'**
  String get outsourcedShowActive;

  /// No description provided for @outsourcedShowArchived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ver arquivados'**
  String get outsourcedShowArchived;

  /// No description provided for @archive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar'**
  String get archive;

  /// No description provided for @restore.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desarquivar'**
  String get restore;

  /// No description provided for @archivedAt.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivado em'**
  String get archivedAt;

  /// No description provided for @archiveReasonLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Motivo do arquivamento (auditoria)'**
  String get archiveReasonLabel;

  /// No description provided for @outsourcedCompanyArchive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar empresa'**
  String get outsourcedCompanyArchive;

  /// No description provided for @outsourcedCompanyArchiveConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar esta empresa?'**
  String get outsourcedCompanyArchiveConfirmTitle;

  /// No description provided for @outsourcedCompanyRestore.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desarquivar'**
  String get outsourcedCompanyRestore;

  /// No description provided for @outsourcedCompanyRestoreConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desarquivar esta empresa?'**
  String get outsourcedCompanyRestoreConfirmTitle;

  /// No description provided for @outsourcedCompaniesArchivedEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma empresa terceirizada arquivada.'**
  String get outsourcedCompaniesArchivedEmpty;

  /// No description provided for @outsourcedEmployeeNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo colaborador'**
  String get outsourcedEmployeeNew;

  /// No description provided for @outsourcedEmployeesEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum colaborador terceirizado/prestador cadastrado.'**
  String get outsourcedEmployeesEmpty;

  /// No description provided for @outsourcedEmployeesArchivedEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum colaborador terceirizado/prestador arquivado.'**
  String get outsourcedEmployeesArchivedEmpty;

  /// No description provided for @outsourcedEmployeeCompanyLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresa terceirizada/prestadora'**
  String get outsourcedEmployeeCompanyLabel;

  /// No description provided for @outsourcedEmployeeOriginRegistrationLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Matrícula da empresa de origem'**
  String get outsourcedEmployeeOriginRegistrationLabel;

  /// No description provided for @outsourcedEmployeeBadgeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Crachá'**
  String get outsourcedEmployeeBadgeLabel;

  /// No description provided for @outsourcedEmployeeNotesLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observações'**
  String get outsourcedEmployeeNotesLabel;

  /// No description provided for @outsourcedEmployeeArchiveConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar este colaborador?'**
  String get outsourcedEmployeeArchiveConfirmTitle;

  /// No description provided for @outsourcedEmployeeRestoreConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desarquivar este colaborador?'**
  String get outsourcedEmployeeRestoreConfirmTitle;

  /// No description provided for @outsourcedReportsError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar o relatório.'**
  String get outsourcedReportsError;

  /// No description provided for @outsourcedReportsEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma empresa terceirizada/prestadora cadastrada.'**
  String get outsourcedReportsEmpty;

  /// No description provided for @outsourcedReportsActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ativos'**
  String get outsourcedReportsActive;

  /// No description provided for @outsourcedReportsArchived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivados'**
  String get outsourcedReportsArchived;

  /// No description provided for @moduleVisibilityTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Visibilidade por Módulo'**
  String get moduleVisibilityTitle;

  /// No description provided for @moduleVisibilityDescription.
  ///
  /// In pt_BR, this message translates to:
  /// **'Permissões padrão: cada perfil possui permissões padrão definidas pelo sistema. Personalizações: o Administrador Geral pode personalizar a visualização e a utilização dos módulos por perfil e por unidade, sem alterar a estrutura padrão do sistema.'**
  String get moduleVisibilityDescription;

  /// No description provided for @moduleVisibilityRoleLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Perfil'**
  String get moduleVisibilityRoleLabel;

  /// No description provided for @moduleVisibilityDefaultPanelTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Permissões padrão deste perfil'**
  String get moduleVisibilityDefaultPanelTitle;

  /// No description provided for @moduleVisibilityDefaultPanelHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estas permissões representam o comportamento padrão do sistema. As configurações abaixo permitem apenas personalizações realizadas pelo Administrador Geral.'**
  String get moduleVisibilityDefaultPanelHint;

  /// No description provided for @moduleVisibilityNoDefaultModules.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum módulo por padrão'**
  String get moduleVisibilityNoDefaultModules;

  /// No description provided for @moduleVisibilityUnitLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get moduleVisibilityUnitLabel;

  /// No description provided for @moduleVisibilityUnitHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Um módulo não marcado especificamente para esta Unidade herda o valor de \"Todas as unidades\".'**
  String get moduleVisibilityUnitHint;

  /// No description provided for @moduleVisibilityAllUnitsOption.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as unidades (padrão)'**
  String get moduleVisibilityAllUnitsOption;
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
