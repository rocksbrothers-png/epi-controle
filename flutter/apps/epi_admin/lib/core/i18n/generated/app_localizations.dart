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
    Locale('pt', 'BR'),
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
  /// **'Buscar por nome, CA brasileiro ou código'**
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
  /// **'CA — Certificado de Aprovação'**
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
  /// **'Validade do CA'**
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

  /// No description provided for @epiArchiveBlockTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar com bloqueio de saldo'**
  String get epiArchiveBlockTitle;

  /// No description provided for @epiArchiveBlockBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'Este EPI possui saldo disponível ou vínculos vivos. Ao confirmar, o saldo disponível será movido para Estoque Bloqueado (rastreável) e o EPI será arquivado.'**
  String get epiArchiveBlockBody;

  /// No description provided for @epiArchiveBlockConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Bloquear saldo e arquivar'**
  String get epiArchiveBlockConfirm;

  /// No description provided for @epiArchiveReasonLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Motivo do arquivamento (auditoria)'**
  String get epiArchiveReasonLabel;

  /// No description provided for @epiArchiveReasonRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe o motivo para prosseguir.'**
  String get epiArchiveReasonRequired;

  /// No description provided for @epiArchiveBlockableLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Saldo a bloquear'**
  String get epiArchiveBlockableLabel;

  /// No description provided for @epiArchiveLiveLinksTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vínculos vivos'**
  String get epiArchiveLiveLinksTitle;

  /// No description provided for @epiArchiveAvailable.
  ///
  /// In pt_BR, this message translates to:
  /// **'Disponível'**
  String get epiArchiveAvailable;

  /// No description provided for @epiArchiveInTransit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em trânsito'**
  String get epiArchiveInTransit;

  /// No description provided for @epiArchiveInPossession.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em posse'**
  String get epiArchiveInPossession;

  /// No description provided for @epiArchivePendingRequests.
  ///
  /// In pt_BR, this message translates to:
  /// **'Requisições abertas'**
  String get epiArchivePendingRequests;

  /// No description provided for @epiArchivePendingPurchase.
  ///
  /// In pt_BR, this message translates to:
  /// **'Compras abertas'**
  String get epiArchivePendingPurchase;

  /// No description provided for @dashboardComplianceTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conformidade de estoque'**
  String get dashboardComplianceTitle;

  /// No description provided for @dashboardComplianceAllOk.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque em conformidade'**
  String get dashboardComplianceAllOk;

  /// No description provided for @complianceCaExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA vencido'**
  String get complianceCaExpired;

  /// No description provided for @complianceCaExpiring.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA a vencer'**
  String get complianceCaExpiring;

  /// No description provided for @complianceProductExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Produto vencido'**
  String get complianceProductExpired;

  /// No description provided for @complianceProductExpiring.
  ///
  /// In pt_BR, this message translates to:
  /// **'Produto a vencer'**
  String get complianceProductExpiring;

  /// No description provided for @complianceMissingManufacture.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem fabricação'**
  String get complianceMissingManufacture;

  /// No description provided for @complianceMissingLot.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem lote'**
  String get complianceMissingLot;

  /// No description provided for @complianceAdminBlocked.
  ///
  /// In pt_BR, this message translates to:
  /// **'Bloqueado'**
  String get complianceAdminBlocked;

  /// No description provided for @handoverTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conferência de entrega'**
  String get handoverTitle;

  /// No description provided for @handoverPrompt.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escaneie o QR da entrega ou informe o código.'**
  String get handoverPrompt;

  /// No description provided for @handoverCodeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Código da entrega'**
  String get handoverCodeLabel;

  /// No description provided for @handoverLookupButton.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar entrega'**
  String get handoverLookupButton;

  /// No description provided for @handoverScanButton.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escanear QR'**
  String get handoverScanButton;

  /// No description provided for @handoverConfirmButton.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar recebimento'**
  String get handoverConfirmButton;

  /// No description provided for @handoverConfirmedTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recebimento confirmado'**
  String get handoverConfirmedTitle;

  /// No description provided for @handoverAlreadyConfirmed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Esta entrega já foi confirmada.'**
  String get handoverAlreadyConfirmed;

  /// No description provided for @handoverNotFound.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrega não encontrada para este código.'**
  String get handoverNotFound;

  /// No description provided for @handoverConfirmError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível confirmar o recebimento.'**
  String get handoverConfirmError;

  /// No description provided for @handoverEmployeeLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaborador'**
  String get handoverEmployeeLabel;

  /// No description provided for @handoverEpiLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI'**
  String get handoverEpiLabel;

  /// No description provided for @handoverQuantityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade'**
  String get handoverQuantityLabel;

  /// No description provided for @handoverSectorLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Setor'**
  String get handoverSectorLabel;

  /// No description provided for @handoverRoleLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Função'**
  String get handoverRoleLabel;

  /// No description provided for @handoverUnitLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get handoverUnitLabel;

  /// No description provided for @handoverDeliveryDateLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data da entrega'**
  String get handoverDeliveryDateLabel;

  /// No description provided for @handoverReceiverNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome de quem recebe (opcional)'**
  String get handoverReceiverNameLabel;

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

  /// No description provided for @legalEntityCnpjLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ'**
  String get legalEntityCnpjLabel;

  /// No description provided for @legalEntityUfLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'UF'**
  String get legalEntityUfLabel;

  /// No description provided for @legalEntitiesImportColumnsHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'CNPJ\tRazão social\tNome fantasia\tTipo'**
  String get legalEntitiesImportColumnsHint;

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

  /// No description provided for @outsourcedCompanyLinkTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vincular empresa a esta Unidade'**
  String get outsourcedCompanyLinkTitle;

  /// No description provided for @outsourcedCompanyLinkHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Buscar empresa já cadastrada no tenant…'**
  String get outsourcedCompanyLinkHint;

  /// No description provided for @outsourcedCompanyLinkSectionLinked.
  ///
  /// In pt_BR, this message translates to:
  /// **'Já vinculadas a esta Unidade'**
  String get outsourcedCompanyLinkSectionLinked;

  /// No description provided for @outsourcedCompanyLinkSectionAvailable.
  ///
  /// In pt_BR, this message translates to:
  /// **'Disponíveis para vincular'**
  String get outsourcedCompanyLinkSectionAvailable;

  /// No description provided for @outsourcedCompanyLinkLink.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vincular a esta Unidade'**
  String get outsourcedCompanyLinkLink;

  /// No description provided for @outsourcedCompanyLinkActivate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Reativar nesta Unidade'**
  String get outsourcedCompanyLinkActivate;

  /// No description provided for @outsourcedCompanyLinkDeactivate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar nesta Unidade'**
  String get outsourcedCompanyLinkDeactivate;

  /// No description provided for @outsourcedCompanyLinkDeactivateReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Motivo do arquivamento (opcional):'**
  String get outsourcedCompanyLinkDeactivateReason;

  /// No description provided for @outsourcedCompanyLinkUsedByUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'Usada por {count} Unidade(s)'**
  String outsourcedCompanyLinkUsedByUnits(int count);

  /// No description provided for @outsourcedCompanyLinkOriginUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade de origem'**
  String get outsourcedCompanyLinkOriginUnit;

  /// No description provided for @outsourcedCompanyLinkEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma empresa encontrada com esse termo.'**
  String get outsourcedCompanyLinkEmpty;

  /// No description provided for @outsourcedCompanyLinkNotInformed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vínculo não informado para o seu perfil'**
  String get outsourcedCompanyLinkNotInformed;

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

  /// No description provided for @employeeUnitLinkColumn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vínculo local'**
  String get employeeUnitLinkColumn;

  /// No description provided for @employeeUnitLink.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vincular à minha unidade'**
  String get employeeUnitLink;

  /// No description provided for @employeeUnitLinkActivate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Reativar nesta Unidade'**
  String get employeeUnitLinkActivate;

  /// No description provided for @employeeUnitLinkDeactivate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar nesta Unidade'**
  String get employeeUnitLinkDeactivate;

  /// No description provided for @employeeUnitLinkDeactivateReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Motivo do arquivamento (opcional):'**
  String get employeeUnitLinkDeactivateReason;

  /// No description provided for @employeeUnitLinkActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vinculado'**
  String get employeeUnitLinkActive;

  /// No description provided for @employeeUnitLinkArchived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivado nesta Unidade'**
  String get employeeUnitLinkArchived;

  /// No description provided for @employeeUnitLinkAbsent.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não vinculado'**
  String get employeeUnitLinkAbsent;

  /// No description provided for @employeeUnitLinksTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vínculos por Unidade'**
  String get employeeUnitLinksTitle;

  /// No description provided for @employeeUnitLinksEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Este colaborador não tem vínculo com nenhuma Unidade que você pode consultar.'**
  String get employeeUnitLinksEmpty;

  /// No description provided for @employeeUnitLinksError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar os vínculos.'**
  String get employeeUnitLinksError;

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

  /// No description provided for @stockTabAvailable.
  ///
  /// In pt_BR, this message translates to:
  /// **'Disponíveis'**
  String get stockTabAvailable;

  /// No description provided for @stockTabBlocked.
  ///
  /// In pt_BR, this message translates to:
  /// **'Bloqueados'**
  String get stockTabBlocked;

  /// No description provided for @stockAvailableSelectEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione um EPI para ver os itens disponíveis'**
  String get stockAvailableSelectEpi;

  /// No description provided for @stockAvailableEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum item disponível para este EPI nesta unidade'**
  String get stockAvailableEmpty;

  /// No description provided for @stockBlockedEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum item bloqueado'**
  String get stockBlockedEmpty;

  /// No description provided for @stockNoOperationalUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Seu perfil não tem unidade operacional ativa. Fale com o administrador para liberar o acesso ao estoque.'**
  String get stockNoOperationalUnit;

  /// No description provided for @stockItemLotLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Lote'**
  String get stockItemLotLabel;

  /// No description provided for @stockStatusBlockedExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vencido'**
  String get stockStatusBlockedExpired;

  /// No description provided for @stockStatusBlockedDiscard.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando descarte'**
  String get stockStatusBlockedDiscard;

  /// No description provided for @stockStatusBlockedReturn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando devolução ao fornecedor'**
  String get stockStatusBlockedReturn;

  /// No description provided for @stockStatusBlockedAnalysis.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em análise'**
  String get stockStatusBlockedAnalysis;

  /// No description provided for @stockStatusBlockedRejected.
  ///
  /// In pt_BR, this message translates to:
  /// **'Reprovado'**
  String get stockStatusBlockedRejected;

  /// No description provided for @stockStatusBlockedArchived.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI arquivado'**
  String get stockStatusBlockedArchived;

  /// No description provided for @stockStatusUnknown.
  ///
  /// In pt_BR, this message translates to:
  /// **'Status não reconhecido'**
  String get stockStatusUnknown;

  /// No description provided for @stockUnitBalanceSuffix.
  ///
  /// In pt_BR, this message translates to:
  /// **'na unidade'**
  String get stockUnitBalanceSuffix;

  /// No description provided for @stockCompanyBalanceLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'empresa'**
  String get stockCompanyBalanceLabel;

  /// No description provided for @stockMinimumShort.
  ///
  /// In pt_BR, this message translates to:
  /// **'mín'**
  String get stockMinimumShort;

  /// No description provided for @deliveryStepItem.
  ///
  /// In pt_BR, this message translates to:
  /// **'Item'**
  String get deliveryStepItem;

  /// No description provided for @deliveryItemTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione a unidade etiquetada'**
  String get deliveryItemTitle;

  /// No description provided for @deliveryItemEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum item disponível nesta Unidade.'**
  String get deliveryItemEmpty;

  /// No description provided for @deliveryItemScan.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ler QR do item'**
  String get deliveryItemScan;

  /// Saldo do EPI na Unidade do colaborador que vai receber.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque na Unidade: {qty}'**
  String deliveryUnitStockAvailable(int qty);

  /// No description provided for @deliveryEmployeeWithoutUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaborador sem Unidade operacional: não é possível registrar entrega.'**
  String get deliveryEmployeeWithoutUnit;

  /// No description provided for @deliveryQrOtherEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'O código lido pertence a outro EPI.'**
  String get deliveryQrOtherEpi;

  /// No description provided for @stockUnitRequiredToMove.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione uma Unidade para movimentar o estoque.'**
  String get stockUnitRequiredToMove;

  /// No description provided for @stockAttentionSectionTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque'**
  String get stockAttentionSectionTitle;

  /// No description provided for @stockAttentionCompanyTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Faixa de atenção — padrão da empresa'**
  String get stockAttentionCompanyTitle;

  /// No description provided for @stockAttentionCompanyHelp.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aplica-se às Unidades que não definiram um percentual próprio. Não altera nenhuma Unidade já configurada.'**
  String get stockAttentionCompanyHelp;

  /// No description provided for @stockAttentionPercentageLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Percentual da faixa de atenção'**
  String get stockAttentionPercentageLabel;

  /// No description provided for @stockAttentionOriginLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Origem'**
  String get stockAttentionOriginLabel;

  /// No description provided for @stockAttentionOriginCompany.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurado pela empresa'**
  String get stockAttentionOriginCompany;

  /// No description provided for @stockAttentionOriginSystem.
  ///
  /// In pt_BR, this message translates to:
  /// **'Padrão do sistema'**
  String get stockAttentionOriginSystem;

  /// No description provided for @stockAttentionSave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar padrão da empresa'**
  String get stockAttentionSave;

  /// No description provided for @stockAttentionRestore.
  ///
  /// In pt_BR, this message translates to:
  /// **'Restaurar padrão do sistema'**
  String get stockAttentionRestore;

  /// No description provided for @stockAttentionSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Padrão da empresa salvo.'**
  String get stockAttentionSaved;

  /// No description provided for @stockAttentionRestored.
  ///
  /// In pt_BR, this message translates to:
  /// **'Padrão da empresa removido. A empresa voltou ao padrão do sistema.'**
  String get stockAttentionRestored;

  /// No description provided for @stockAttentionSystemDefaultHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Padrão do sistema: {value}%'**
  String stockAttentionSystemDefaultHint(int value);

  /// No description provided for @stockConfigTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configuração de estoque'**
  String get stockConfigTitle;

  /// No description provided for @stockConfigIntro.
  ///
  /// In pt_BR, this message translates to:
  /// **'Defina estoque mínimo, faixa de atenção e monitoramento de alerta de um EPI em uma Unidade. Cada parâmetro é salvo separadamente.'**
  String get stockConfigIntro;

  /// No description provided for @stockConfigUnitLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade a configurar'**
  String get stockConfigUnitLabel;

  /// No description provided for @stockConfigSelectUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione a Unidade para configurar os parâmetros.'**
  String get stockConfigSelectUnit;

  /// No description provided for @stockConfigSelectEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione o EPI para ver e editar os parâmetros desta Unidade.'**
  String get stockConfigSelectEpi;

  /// No description provided for @stockConfigEpiLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI'**
  String get stockConfigEpiLabel;

  /// No description provided for @stockConfigEpisLoadError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar os EPIs desta Unidade.'**
  String get stockConfigEpisLoadError;

  /// No description provided for @stockConfigNoEpisInUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum EPI visível nesta Unidade.'**
  String get stockConfigNoEpisInUnit;

  /// No description provided for @stockConfigUnitBalance.
  ///
  /// In pt_BR, this message translates to:
  /// **'Saldo na Unidade'**
  String get stockConfigUnitBalance;

  /// No description provided for @stockConfigAttentionLimit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Limite da faixa de atenção'**
  String get stockConfigAttentionLimit;

  /// No description provided for @stockConfigUnderlyingStatus.
  ///
  /// In pt_BR, this message translates to:
  /// **'Condição física'**
  String get stockConfigUnderlyingStatus;

  /// No description provided for @stockConfigDerivedUnavailable.
  ///
  /// In pt_BR, this message translates to:
  /// **'Os valores calculados não puderam ser atualizados agora. Os parâmetros salvos acima estão corretos.'**
  String get stockConfigDerivedUnavailable;

  /// No description provided for @stockConfigStatusCritical.
  ///
  /// In pt_BR, this message translates to:
  /// **'Crítico'**
  String get stockConfigStatusCritical;

  /// No description provided for @stockConfigStatusNearMinimum.
  ///
  /// In pt_BR, this message translates to:
  /// **'Próximo do mínimo'**
  String get stockConfigStatusNearMinimum;

  /// No description provided for @stockConfigStatusNormal.
  ///
  /// In pt_BR, this message translates to:
  /// **'Normal'**
  String get stockConfigStatusNormal;

  /// No description provided for @stockConfigStatusDisabled.
  ///
  /// In pt_BR, this message translates to:
  /// **'Alerta desabilitado'**
  String get stockConfigStatusDisabled;

  /// No description provided for @stockConfigMinimumTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo'**
  String get stockConfigMinimumTitle;

  /// No description provided for @stockConfigMinimumHelp.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade abaixo da qual o EPI é considerado crítico nesta Unidade. Vale só para esta Unidade.'**
  String get stockConfigMinimumHelp;

  /// No description provided for @stockConfigMinimumLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo'**
  String get stockConfigMinimumLabel;

  /// No description provided for @stockConfigMinimumNegativeError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe um número inteiro maior ou igual a zero.'**
  String get stockConfigMinimumNegativeError;

  /// No description provided for @stockConfigMinimumSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo salvo para esta Unidade.'**
  String get stockConfigMinimumSaved;

  /// No description provided for @stockConfigMinimumRestored.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque mínimo restaurado. A Unidade voltou a herdar o padrão da empresa.'**
  String get stockConfigMinimumRestored;

  /// No description provided for @stockConfigAttentionTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Faixa de atenção'**
  String get stockConfigAttentionTitle;

  /// No description provided for @stockConfigAttentionHelp.
  ///
  /// In pt_BR, this message translates to:
  /// **'Percentual acima do mínimo em que o EPI já entra em atenção nesta Unidade. Independente do estoque mínimo.'**
  String get stockConfigAttentionHelp;

  /// No description provided for @stockConfigAttentionRangeError.
  ///
  /// In pt_BR, this message translates to:
  /// **'O percentual deve estar entre 0 e 100.'**
  String get stockConfigAttentionRangeError;

  /// No description provided for @stockConfigAttentionSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Faixa de atenção salva para esta Unidade.'**
  String get stockConfigAttentionSaved;

  /// No description provided for @stockConfigAttentionRestored.
  ///
  /// In pt_BR, this message translates to:
  /// **'Faixa de atenção restaurada. A Unidade voltou a herdar o padrão da empresa.'**
  String get stockConfigAttentionRestored;

  /// No description provided for @stockConfigAlertTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Monitoramento de alerta'**
  String get stockConfigAlertTitle;

  /// No description provided for @stockConfigAlertHelp.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desligar interrompe o alerta de estoque baixo e a reposição automática deste EPI nesta Unidade. Não altera saldo, mínimo nem percentual.'**
  String get stockConfigAlertHelp;

  /// No description provided for @stockConfigAlertToggle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Monitorar o estoque deste EPI'**
  String get stockConfigAlertToggle;

  /// No description provided for @stockConfigAlertPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Alteração pendente. Clique em Salvar para aplicar.'**
  String get stockConfigAlertPending;

  /// No description provided for @stockConfigAlertDisableTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desabilitar o alerta?'**
  String get stockConfigAlertDisableTitle;

  /// No description provided for @stockConfigAlertDisableBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'Este EPI deixará de gerar alerta de estoque baixo e reposição automática nesta Unidade. A condição física continuará sendo exibida.'**
  String get stockConfigAlertDisableBody;

  /// No description provided for @stockConfigAlertDisableConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desabilitar'**
  String get stockConfigAlertDisableConfirm;

  /// No description provided for @stockConfigAlertSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Monitoramento de alerta salvo para esta Unidade.'**
  String get stockConfigAlertSaved;

  /// No description provided for @stockConfigAlertRestored.
  ///
  /// In pt_BR, this message translates to:
  /// **'Monitoramento restaurado. A Unidade voltou ao padrão do sistema.'**
  String get stockConfigAlertRestored;

  /// No description provided for @stockConfigOriginUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Configurado por esta Unidade'**
  String get stockConfigOriginUnit;

  /// No description provided for @stockConfigOriginCompany.
  ///
  /// In pt_BR, this message translates to:
  /// **'Herdado do padrão da empresa'**
  String get stockConfigOriginCompany;

  /// No description provided for @stockConfigOriginUnknown.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não informada'**
  String get stockConfigOriginUnknown;

  /// No description provided for @stockConfigSave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar'**
  String get stockConfigSave;

  /// No description provided for @stockConfigRestore.
  ///
  /// In pt_BR, this message translates to:
  /// **'Restaurar herança'**
  String get stockConfigRestore;

  /// No description provided for @stockAttentionRangeError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe um percentual inteiro entre 0 e {max}.'**
  String stockAttentionRangeError(int max);

  /// No description provided for @stockAttentionLoadError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar o padrão da empresa.'**
  String get stockAttentionLoadError;

  /// No description provided for @unitSelectorLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade'**
  String get unitSelectorLabel;

  /// No description provided for @unitSelectorAllUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as Unidades'**
  String get unitSelectorAllUnits;

  /// No description provided for @unitSelectorLockedHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Seu perfil opera numa Unidade fixa.'**
  String get unitSelectorLockedHint;

  /// No description provided for @unitSelectorLoadError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar as Unidades.'**
  String get unitSelectorLoadError;

  /// No description provided for @unitSelectorNoUnitsAssigned.
  ///
  /// In pt_BR, this message translates to:
  /// **'Você não tem Unidade atribuída. Fale com o administrador.'**
  String get unitSelectorNoUnitsAssigned;

  /// No description provided for @unitSelectorCompanyHasNoUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'A empresa ainda não tem Unidades cadastradas.'**
  String get unitSelectorCompanyHasNoUnits;

  /// No description provided for @settingsSectionCompany.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresa'**
  String get settingsSectionCompany;

  /// No description provided for @settingsSectionOperation.
  ///
  /// In pt_BR, this message translates to:
  /// **'Operação'**
  String get settingsSectionOperation;

  /// No description provided for @settingsSectionSubscription.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura'**
  String get settingsSectionSubscription;

  /// No description provided for @settingsCompanyLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Empresa'**
  String get settingsCompanyLabel;

  /// No description provided for @settingsCompanyScopeBanner.
  ///
  /// In pt_BR, this message translates to:
  /// **'Administrando a empresa: {name}'**
  String settingsCompanyScopeBanner(String name);

  /// No description provided for @settingsSelectCompanyFirst.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione uma empresa em Configurações para continuar.'**
  String get settingsSelectCompanyFirst;

  /// No description provided for @settingsFichaTileTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ficha de EPI'**
  String get settingsFichaTileTitle;

  /// No description provided for @settingsFichaTileSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Título, declaração, observações e rastreabilidade'**
  String get settingsFichaTileSubtitle;

  /// No description provided for @settingsStockTileSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Faixa de atenção padrão da empresa'**
  String get settingsStockTileSubtitle;

  /// No description provided for @settingsModulesTileSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Módulos visíveis por perfil e por Unidade'**
  String get settingsModulesTileSubtitle;

  /// No description provided for @settingsArchivalTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivamento e retenção'**
  String get settingsArchivalTitle;

  /// No description provided for @settingsArchivalSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Anos de preservação dos registros arquivados'**
  String get settingsArchivalSubtitle;

  /// No description provided for @settingsAppearanceTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aparência e idioma'**
  String get settingsAppearanceTitle;

  /// No description provided for @settingsAppearanceSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tema da interface e idioma do aplicativo'**
  String get settingsAppearanceSubtitle;

  /// No description provided for @settingsSubscriptionTileTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Minha Assinatura'**
  String get settingsSubscriptionTileTitle;

  /// No description provided for @settingsSubscriptionTileSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Plano, cobranças e cancelamento'**
  String get settingsSubscriptionTileSubtitle;

  /// No description provided for @settingsInvoicesTileTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Histórico Financeiro'**
  String get settingsInvoicesTileTitle;

  /// No description provided for @settingsInvoicesTileSubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as cobranças e recibos'**
  String get settingsInvoicesTileSubtitle;

  /// No description provided for @settingsNoPermission.
  ///
  /// In pt_BR, this message translates to:
  /// **'Você não tem permissão para alterar esta configuração.'**
  String get settingsNoPermission;

  /// No description provided for @stockPhysicalValidityUnknown.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade física desconhecida'**
  String get stockPhysicalValidityUnknown;

  /// No description provided for @stockNoPhysicalStock.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sem estoque físico'**
  String get stockNoPhysicalStock;

  /// No description provided for @stockRegularizeValidityTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Regularizar validade física'**
  String get stockRegularizeValidityTitle;

  /// No description provided for @stockRegularizeValiditySubtitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Identifique a peça e informe a validade comprovada. A classificação é feita pelo sistema.'**
  String get stockRegularizeValiditySubtitle;

  /// No description provided for @stockRegularizeQrLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'QR ou código da peça'**
  String get stockRegularizeQrLabel;

  /// No description provided for @stockRegularizeExpiryLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade física comprovada'**
  String get stockRegularizeExpiryLabel;

  /// No description provided for @stockRegularizeExpirySelect.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar data'**
  String get stockRegularizeExpirySelect;

  /// No description provided for @stockRegularizeEvidenceLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Evidência (documento ou registro verificável)'**
  String get stockRegularizeEvidenceLabel;

  /// No description provided for @stockRegularizeJustificationLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Justificativa'**
  String get stockRegularizeJustificationLabel;

  /// No description provided for @stockRegularizeSubmit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Regularizar'**
  String get stockRegularizeSubmit;

  /// No description provided for @stockRegularizeIncomplete.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preencha a peça, a validade, a evidência e a justificativa.'**
  String get stockRegularizeIncomplete;

  /// No description provided for @stockRegularizeResultEligible.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade regularizada. A peça está apta para entrega e reserva.'**
  String get stockRegularizeResultEligible;

  /// No description provided for @stockRegularizeResultBlocked.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade regularizada. A peça está vencida e permanece bloqueada para entrega.'**
  String get stockRegularizeResultBlocked;

  /// No description provided for @stockRegularizeResultDone.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade regularizada.'**
  String get stockRegularizeResultDone;

  /// Filter counts distinct PPE types; piece counts are provided separately by the backend.
  ///
  /// In pt_BR, this message translates to:
  /// **'{label} — EPIs distintos: {count}'**
  String stockComplianceEpiCount(String label, int count);

  /// No description provided for @stockPhysicalPieceCounts.
  ///
  /// In pt_BR, this message translates to:
  /// **'Peças físicas: válidas {valid}, próximas {expiring}, vencidas {expired}, desconhecidas {unknown}.'**
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  );

  /// No description provided for @deliveryPhysicalItemIneligible.
  ///
  /// In pt_BR, this message translates to:
  /// **'Item indisponível para entrega. Verifique validade física, status, reservas e saldo.'**
  String get deliveryPhysicalItemIneligible;

  /// No description provided for @safetyTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Biblioteca de Segurança'**
  String get safetyTitle;

  /// No description provided for @safetyApproved.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPIs Aprovados'**
  String get safetyApproved;

  /// No description provided for @safetyRetry.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tentar novamente'**
  String get safetyRetry;

  /// No description provided for @safetyClose.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fechar'**
  String get safetyClose;

  /// No description provided for @safetyCancel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelar'**
  String get safetyCancel;

  /// No description provided for @safetyConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar'**
  String get safetyConfirm;

  /// No description provided for @safetyAccess.
  ///
  /// In pt_BR, this message translates to:
  /// **'Acessar'**
  String get safetyAccess;

  /// No description provided for @safetyPortalConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar acesso ao portal'**
  String get safetyPortalConfirm;

  /// No description provided for @safetyCpfLast.
  ///
  /// In pt_BR, this message translates to:
  /// **'Três últimos dígitos do CPF'**
  String get safetyCpfLast;

  /// No description provided for @safetyView.
  ///
  /// In pt_BR, this message translates to:
  /// **'Visualizar'**
  String get safetyView;

  /// No description provided for @safetyFit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ajustar'**
  String get safetyFit;

  /// No description provided for @safetyZoomIn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aumentar zoom'**
  String get safetyZoomIn;

  /// No description provided for @safetyZoomOut.
  ///
  /// In pt_BR, this message translates to:
  /// **'Diminuir zoom'**
  String get safetyZoomOut;

  /// No description provided for @safetyNextPage.
  ///
  /// In pt_BR, this message translates to:
  /// **'Próxima página'**
  String get safetyNextPage;

  /// No description provided for @safetyPreviousPage.
  ///
  /// In pt_BR, this message translates to:
  /// **'Página anterior'**
  String get safetyPreviousPage;

  /// No description provided for @safetyDocument.
  ///
  /// In pt_BR, this message translates to:
  /// **'Documento'**
  String get safetyDocument;

  /// No description provided for @safetyDetails.
  ///
  /// In pt_BR, this message translates to:
  /// **'Detalhes'**
  String get safetyDetails;

  /// No description provided for @safetyRelatedDocuments.
  ///
  /// In pt_BR, this message translates to:
  /// **'Documentos associados'**
  String get safetyRelatedDocuments;

  /// No description provided for @safetyRelatedEpis.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPIs relacionados'**
  String get safetyRelatedEpis;

  /// No description provided for @safetyRelatedEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI relacionado'**
  String get safetyRelatedEpi;

  /// No description provided for @safetyAllEpis.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todos os EPIs'**
  String get safetyAllEpis;

  /// No description provided for @safetyAllCategories.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as categorias'**
  String get safetyAllCategories;

  /// No description provided for @safetyNoDocs.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum documento publicado para este contexto.'**
  String get safetyNoDocs;

  /// No description provided for @safetyNoRecords.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum registro publicado e autorizado neste contexto.'**
  String get safetyNoRecords;

  /// No description provided for @safetyCatalogueNotice.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovação cadastral; não indica disponibilidade física. Validade do CA não é validade de lote.'**
  String get safetyCatalogueNotice;

  /// No description provided for @safetyName.
  ///
  /// In pt_BR, this message translates to:
  /// **'EPI'**
  String get safetyName;

  /// No description provided for @safetyManufacturer.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fabricante'**
  String get safetyManufacturer;

  /// No description provided for @safetyModel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Modelo/referência'**
  String get safetyModel;

  /// No description provided for @safetyCa.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA'**
  String get safetyCa;

  /// No description provided for @safetyCaExpiry.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade do CA'**
  String get safetyCaExpiry;

  /// No description provided for @safetyUsefulLife.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vida útil (meses)'**
  String get safetyUsefulLife;

  /// No description provided for @safetyProtection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Proteção'**
  String get safetyProtection;

  /// No description provided for @safetySection.
  ///
  /// In pt_BR, this message translates to:
  /// **'Seção'**
  String get safetySection;

  /// No description provided for @safetyRecommendations.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recomendações/restrições'**
  String get safetyRecommendations;

  /// No description provided for @safetyUnknown.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não informado'**
  String get safetyUnknown;

  /// No description provided for @safetySearch.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pesquisar'**
  String get safetySearch;

  /// No description provided for @safetyViewEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ver EPI'**
  String get safetyViewEpi;

  /// No description provided for @safetyHistory.
  ///
  /// In pt_BR, this message translates to:
  /// **'Histórico'**
  String get safetyHistory;

  /// No description provided for @safetyDocumentHistory.
  ///
  /// In pt_BR, this message translates to:
  /// **'Histórico documental'**
  String get safetyDocumentHistory;

  /// No description provided for @safetyPublish.
  ///
  /// In pt_BR, this message translates to:
  /// **'Publicar'**
  String get safetyPublish;

  /// No description provided for @safetyPublishVersion.
  ///
  /// In pt_BR, this message translates to:
  /// **'Publicar versão'**
  String get safetyPublishVersion;

  /// No description provided for @safetyArchive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar documento'**
  String get safetyArchive;

  /// No description provided for @safetyArchiveVersions.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivar documento e versões'**
  String get safetyArchiveVersions;

  /// No description provided for @safetyReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Justificativa obrigatória'**
  String get safetyReason;

  /// No description provided for @safetyNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo documento'**
  String get safetyNew;

  /// No description provided for @safetyCreateNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Criar novo documento'**
  String get safetyCreateNew;

  /// No description provided for @safetyMetadata.
  ///
  /// In pt_BR, this message translates to:
  /// **'Metadados da versão'**
  String get safetyMetadata;

  /// No description provided for @safetyEmptyAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum documento cadastrado.'**
  String get safetyEmptyAdmin;

  /// No description provided for @safetyPrivateNotice.
  ///
  /// In pt_BR, this message translates to:
  /// **'Originais privados; versões e histórico preservados. Gestão restrita ao Administrador Geral e ao Administrador de Registro.'**
  String get safetyPrivateNotice;

  /// No description provided for @safetyAllowAdminDownloads.
  ///
  /// In pt_BR, this message translates to:
  /// **'Permitir download de originais aos administradores autorizados'**
  String get safetyAllowAdminDownloads;

  /// No description provided for @safetyPreviewOnlyNotice.
  ///
  /// In pt_BR, this message translates to:
  /// **'Colaboradores sempre consultam somente a pré-visualização.'**
  String get safetyPreviewOnlyNotice;

  /// No description provided for @safetyPolicyReason.
  ///
  /// In pt_BR, this message translates to:
  /// **'Alterar política de download administrativo'**
  String get safetyPolicyReason;

  /// No description provided for @safetySearchVersions.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pesquisar título ou versão'**
  String get safetySearchVersions;

  /// No description provided for @safetyChooseFile.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecionar arquivo'**
  String get safetyChooseFile;

  /// No description provided for @safetyFilePickerLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Documentos de SST'**
  String get safetyFilePickerLabel;

  /// No description provided for @safetyUnitRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione ao menos uma unidade'**
  String get safetyUnitRequired;

  /// No description provided for @safetyAllUnits.
  ///
  /// In pt_BR, this message translates to:
  /// **'Todas as unidades da empresa'**
  String get safetyAllUnits;

  /// No description provided for @safetyRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Obrigatório'**
  String get safetyRequired;

  /// No description provided for @safetyDocumentTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Título'**
  String get safetyDocumentTitle;

  /// No description provided for @safetyVersion.
  ///
  /// In pt_BR, this message translates to:
  /// **'Versão'**
  String get safetyVersion;

  /// No description provided for @safetyEffectiveDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Vigência (AAAA-MM-DD)'**
  String get safetyEffectiveDate;

  /// No description provided for @safetySectors.
  ///
  /// In pt_BR, this message translates to:
  /// **'Setores separados por vírgula (vazio = todos)'**
  String get safetySectors;

  /// No description provided for @safetyActivities.
  ///
  /// In pt_BR, this message translates to:
  /// **'Atividades/funções separadas por vírgula (vazio = todas)'**
  String get safetyActivities;

  /// No description provided for @safetyUpload.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cadastrar ou versionar documento'**
  String get safetyUpload;

  /// No description provided for @safetyRendering.
  ///
  /// In pt_BR, this message translates to:
  /// **'Gerando pré-visualização segura…'**
  String get safetyRendering;

  /// No description provided for @safetyFileLimit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Selecione um arquivo de até 20 MiB.'**
  String get safetyFileLimit;

  /// No description provided for @safetyVersionDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Versão {version} · Vigência {date}'**
  String safetyVersionDate(String version, String date);

  /// No description provided for @safetyUnit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unidade de consulta: {unit}'**
  String safetyUnit(String unit);

  /// No description provided for @safetyPreviewError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pré-visualização indisponível: {error}'**
  String safetyPreviewError(String error);

  /// No description provided for @safetyUploadError.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cadastro recusado; pré-visualização indisponível: {error}'**
  String safetyUploadError(String error);

  /// No description provided for @safetyVersionSummary.
  ///
  /// In pt_BR, this message translates to:
  /// **'Versão {version} / revisão {revision} · {state} · Vigência {date}'**
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  );

  /// No description provided for @safetyActorDetails.
  ///
  /// In pt_BR, this message translates to:
  /// **'Responsável {actor}\n{details}'**
  String safetyActorDetails(String actor, String details);

  /// No description provided for @safetyCategoryEpi.
  ///
  /// In pt_BR, this message translates to:
  /// **'Matriz de Aplicação de EPIs'**
  String get safetyCategoryEpi;

  /// No description provided for @safetyCategoryGlove.
  ///
  /// In pt_BR, this message translates to:
  /// **'Matriz de Seleção de Luvas'**
  String get safetyCategoryGlove;

  /// No description provided for @safetyCategoryCare.
  ///
  /// In pt_BR, this message translates to:
  /// **'Guias de Higienização e Conservação'**
  String get safetyCategoryCare;

  /// No description provided for @safetyCategoryUse.
  ///
  /// In pt_BR, this message translates to:
  /// **'Instruções de Uso dos EPIs'**
  String get safetyCategoryUse;

  /// No description provided for @safetyCategoryTechnical.
  ///
  /// In pt_BR, this message translates to:
  /// **'Manuais e Fichas Técnicas'**
  String get safetyCategoryTechnical;

  /// No description provided for @safetyCategoryOther.
  ///
  /// In pt_BR, this message translates to:
  /// **'Outros Documentos de SST'**
  String get safetyCategoryOther;

  /// No description provided for @safetyStateDraft.
  ///
  /// In pt_BR, this message translates to:
  /// **'Rascunho'**
  String get safetyStateDraft;

  /// No description provided for @safetyStatePublished.
  ///
  /// In pt_BR, this message translates to:
  /// **'Publicado'**
  String get safetyStatePublished;

  /// No description provided for @safetyStateSuperseded.
  ///
  /// In pt_BR, this message translates to:
  /// **'Substituído'**
  String get safetyStateSuperseded;

  /// No description provided for @safetyStateArchived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Arquivado'**
  String get safetyStateArchived;

  /// No description provided for @prConfTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conferência de Recebimento'**
  String get prConfTitle;

  /// No description provided for @prConfIntro.
  ///
  /// In pt_BR, this message translates to:
  /// **'Marque cada item conforme o recebimento real. Informe a validade física do fabricante e a evidência verificável; use \"Separar em lotes\" para validades diferentes ou exceções individuais. Peças sem validade comprovada entram BLOQUEADAS.'**
  String get prConfIntro;

  /// No description provided for @prConfReceivedYes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recebido'**
  String get prConfReceivedYes;

  /// No description provided for @prConfReceivedNo.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não recebido'**
  String get prConfReceivedNo;

  /// No description provided for @prConfEvidence.
  ///
  /// In pt_BR, this message translates to:
  /// **'Evidência verificável'**
  String get prConfEvidence;

  /// No description provided for @prConfEvidenceHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Etiqueta / NF / foto'**
  String get prConfEvidenceHint;

  /// No description provided for @prConfEvidenceRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Evidência verificável é obrigatória quando há validade.'**
  String get prConfEvidenceRequired;

  /// No description provided for @prConfSplitLots.
  ///
  /// In pt_BR, this message translates to:
  /// **'Separar em lotes'**
  String get prConfSplitLots;

  /// No description provided for @prConfSingleDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Usar data única'**
  String get prConfSingleDate;

  /// No description provided for @prConfAddLot.
  ///
  /// In pt_BR, this message translates to:
  /// **'Adicionar lote'**
  String get prConfAddLot;

  /// No description provided for @prConfAddException.
  ///
  /// In pt_BR, this message translates to:
  /// **'Exceção (1 peça)'**
  String get prConfAddException;

  /// No description provided for @prConfLotQty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Qtd'**
  String get prConfLotQty;

  /// No description provided for @prConfLotCode.
  ///
  /// In pt_BR, this message translates to:
  /// **'Identificação'**
  String get prConfLotCode;

  /// No description provided for @prConfRemoveLot.
  ///
  /// In pt_BR, this message translates to:
  /// **'Remover lote'**
  String get prConfRemoveLot;

  /// No description provided for @prConfPreview.
  ///
  /// In pt_BR, this message translates to:
  /// **'Prévia — validade física por peça'**
  String get prConfPreview;

  /// No description provided for @prConfBlocked.
  ///
  /// In pt_BR, this message translates to:
  /// **'SEM validade → BLOQUEADAS'**
  String get prConfBlocked;

  /// No description provided for @prConfExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'vencida'**
  String get prConfExpired;

  /// No description provided for @prConfPiece.
  ///
  /// In pt_BR, this message translates to:
  /// **'peça(s)'**
  String get prConfPiece;

  /// No description provided for @prConfSumMismatch.
  ///
  /// In pt_BR, this message translates to:
  /// **'A soma das quantidades dos lotes não confere com a quantidade recebida.'**
  String get prConfSumMismatch;

  /// No description provided for @prConfLotQtyPositive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cada lote precisa de quantidade maior que zero.'**
  String get prConfLotQtyPositive;

  /// No description provided for @prConfNotes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Observações sobre itens não recebidos'**
  String get prConfNotes;

  /// No description provided for @prConfNotesRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe as observações sobre os itens não recebidos.'**
  String get prConfNotesRequired;

  /// No description provided for @prConfSubmit.
  ///
  /// In pt_BR, this message translates to:
  /// **'Registrar Conferência'**
  String get prConfSubmit;

  /// No description provided for @prConfDone.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conferência registrada.'**
  String get prConfDone;

  /// No description provided for @prConfEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhum item elegível para conferência.'**
  String get prConfEmpty;

  /// No description provided for @prConfInvalidQuantity.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.'**
  String get prConfInvalidQuantity;

  /// No description provided for @prConfNoPersistedPieces.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma peça efetivamente registrada ou resposta inconsistente. A entrada em estoque não foi confirmada.'**
  String get prConfNoPersistedPieces;

  /// No description provided for @prConfDoneQuantity.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count} peças efetivamente registradas no estoque.'**
  String prConfDoneQuantity(int count);

  /// No description provided for @prConfNoStockEntry.
  ///
  /// In pt_BR, this message translates to:
  /// **'Conferência salva sem entrada de peças no estoque.'**
  String get prConfNoStockEntry;

  /// No description provided for @prConfInvalidQuantityLine.
  ///
  /// In pt_BR, this message translates to:
  /// **'Linha {line} — {item} (item #{id}): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.'**
  String prConfInvalidQuantityLine(int line, String item, String id);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque próximo do mínimo: {epi}'**
  String operationalAlertStockNearMinimum(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Saldo negativo: {epi}'**
  String operationalAlertStockNegative(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque zerado: {epi}'**
  String operationalAlertStockZero(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque abaixo do mínimo: {epi}'**
  String operationalAlertStockBelowMinimum(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Estoque no limite mínimo: {epi}'**
  String operationalAlertStockAtMinimum(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{company} / {unit} - saldo atual de {stock} {measure}, mínimo {minimum}.'**
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  );

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'CA próximo do vencimento: {epi}'**
  String operationalAlertCaTitle(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{company} - vence em {date}.'**
  String operationalAlertCaDescription(String company, String date);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade do fabricante vencida: {epi}'**
  String operationalAlertManufacturerExpiredTitle(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade do fabricante próxima: {epi}'**
  String operationalAlertManufacturerExpiringTitle(String epi);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{company} - validade do fabricante venceu em {date}. Retire do estoque ({stock} {measure}): EPI vencido não pode ser entregue ao trabalhador.'**
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  );

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{company} - validade do fabricante vence em {date} (em {daysLabel}). Priorize a entrega deste lote ({stock} {measure} em estoque) antes do vencimento (PEPS).'**
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  );

  /// No description provided for @operationalAlertSizes.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tamanhos em estoque:'**
  String get operationalAlertSizes;

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Luva:{value}'**
  String operationalAlertSizeGlove(String value);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tam:{value}'**
  String operationalAlertSizeSize(String value);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'Unif:{value}'**
  String operationalAlertSizeUniform(String value);

  /// No description provided for @operationalAlertSizeUnspecified.
  ///
  /// In pt_BR, this message translates to:
  /// **'S/Tam'**
  String get operationalAlertSizeUnspecified;

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count}'**
  String operationalAlertQuantity(String count);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count, plural, one{unidade} other{unidades}}'**
  String operationalAlertMeasureUnit(num count);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count, plural, one{par} other{pares}}'**
  String operationalAlertMeasurePair(num count);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count, plural, one{{countLabel} dia} other{{countLabel} dias}}'**
  String operationalAlertDays(num count, String countLabel);

  /// Operational alert presentation; canonical metadata and original names stay unchanged.
  ///
  /// In pt_BR, this message translates to:
  /// **'{count, plural, one{{epi}: {countLabel} peça física.} other{{epi}: {countLabel} peças físicas.}}'**
  String operationalAlertPhysicalDescription(
    num count,
    String countLabel,
    String epi,
  );

  /// No description provided for @operationalAlertPhysicalUnknownTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validade física desconhecida'**
  String get operationalAlertPhysicalUnknownTitle;

  /// No description provided for @operationalAlertPhysicalExpiringTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Lotes próximos do vencimento'**
  String get operationalAlertPhysicalExpiringTitle;

  /// No description provided for @passwordChangeTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Defina uma nova senha'**
  String get passwordChangeTitle;

  /// No description provided for @passwordChangeIntro.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sua senha é temporária. Por segurança, defina uma nova senha para continuar.'**
  String get passwordChangeIntro;

  /// No description provided for @passwordChangeCurrent.
  ///
  /// In pt_BR, this message translates to:
  /// **'Senha atual (temporária)'**
  String get passwordChangeCurrent;

  /// No description provided for @passwordChangeNew.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova senha'**
  String get passwordChangeNew;

  /// No description provided for @passwordChangeConfirm.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar nova senha'**
  String get passwordChangeConfirm;

  /// No description provided for @passwordChangeSave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar nova senha'**
  String get passwordChangeSave;

  /// No description provided for @passwordChangeLogout.
  ///
  /// In pt_BR, this message translates to:
  /// **'Sair'**
  String get passwordChangeLogout;

  /// No description provided for @passwordChangeCurrentRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe a senha atual'**
  String get passwordChangeCurrentRequired;

  /// No description provided for @passwordChangeMinLength.
  ///
  /// In pt_BR, this message translates to:
  /// **'A nova senha deve ter ao menos 6 caracteres'**
  String get passwordChangeMinLength;

  /// No description provided for @passwordChangeMustDiffer.
  ///
  /// In pt_BR, this message translates to:
  /// **'A nova senha deve ser diferente da temporária'**
  String get passwordChangeMustDiffer;

  /// No description provided for @passwordChangeMismatch.
  ///
  /// In pt_BR, this message translates to:
  /// **'As senhas não coincidem'**
  String get passwordChangeMismatch;

  /// No description provided for @passwordChangeFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Erro ao trocar a senha'**
  String get passwordChangeFailed;

  /// No description provided for @poSupplierConfirmed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmado'**
  String get poSupplierConfirmed;

  /// No description provided for @poSupplierDeliveryUpdated.
  ///
  /// In pt_BR, this message translates to:
  /// **'Entrega atualizada'**
  String get poSupplierDeliveryUpdated;

  /// No description provided for @poSupplierRejected.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recusado'**
  String get poSupplierRejected;

  /// No description provided for @poSupplierIsoDateHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'AAAA-MM-DD'**
  String get poSupplierIsoDateHint;

  /// No description provided for @billingActive.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ativa'**
  String get billingActive;

  /// No description provided for @billingPending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get billingPending;

  /// No description provided for @billingPaused.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pausada'**
  String get billingPaused;

  /// No description provided for @billingCancelled.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelada'**
  String get billingCancelled;

  /// No description provided for @billingExpired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Expirada'**
  String get billingExpired;

  /// No description provided for @billingAnnual.
  ///
  /// In pt_BR, this message translates to:
  /// **'Anual'**
  String get billingAnnual;

  /// No description provided for @billingMonthly.
  ///
  /// In pt_BR, this message translates to:
  /// **'Mensal'**
  String get billingMonthly;

  /// No description provided for @billingRecurringCard.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cartão (recorrente)'**
  String get billingRecurringCard;

  /// No description provided for @billingCard.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cartão'**
  String get billingCard;

  /// No description provided for @billingBoleto.
  ///
  /// In pt_BR, this message translates to:
  /// **'Boleto'**
  String get billingBoleto;

  /// No description provided for @billingConfirmTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tem certeza?'**
  String get billingConfirmTitle;

  /// No description provided for @billingConfirmBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'Seu acesso continuará disponível até o final do período já pago.\nNenhuma nova cobrança será realizada.'**
  String get billingConfirmBody;

  /// No description provided for @billingConfirmCancel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Confirmar Cancelamento'**
  String get billingConfirmCancel;

  /// No description provided for @billingCancelledNotice.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura cancelada.'**
  String get billingCancelledNotice;

  /// No description provided for @billingCancelFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível cancelar: {detail}'**
  String billingCancelFailed(String detail);

  /// No description provided for @billingAmount.
  ///
  /// In pt_BR, this message translates to:
  /// **'Valor'**
  String get billingAmount;

  /// No description provided for @billingCycle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Periodicidade'**
  String get billingCycle;

  /// No description provided for @billingMethod.
  ///
  /// In pt_BR, this message translates to:
  /// **'Forma de pagamento'**
  String get billingMethod;

  /// No description provided for @billingStarted.
  ///
  /// In pt_BR, this message translates to:
  /// **'Data da contratação'**
  String get billingStarted;

  /// No description provided for @billingNextPayment.
  ///
  /// In pt_BR, this message translates to:
  /// **'Próxima cobrança'**
  String get billingNextPayment;

  /// No description provided for @billingLastPayment.
  ///
  /// In pt_BR, this message translates to:
  /// **'Última cobrança'**
  String get billingLastPayment;

  /// No description provided for @billingCancelDate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelada em'**
  String get billingCancelDate;

  /// No description provided for @billingManualRenewal.
  ///
  /// In pt_BR, this message translates to:
  /// **'Renovação manual'**
  String get billingManualRenewal;

  /// No description provided for @billingMpSubscriptionId.
  ///
  /// In pt_BR, this message translates to:
  /// **'ID da assinatura (MP)'**
  String get billingMpSubscriptionId;

  /// No description provided for @billingMpStatus.
  ///
  /// In pt_BR, this message translates to:
  /// **'Status Mercado Pago'**
  String get billingMpStatus;

  /// No description provided for @billingTenant.
  ///
  /// In pt_BR, this message translates to:
  /// **'Tenant'**
  String get billingTenant;

  /// No description provided for @billingCancelAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelar assinatura'**
  String get billingCancelAction;

  /// No description provided for @billingCancelledBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'Assinatura cancelada. O acesso permanece ativo até o final do período já pago; nenhuma nova cobrança será realizada.'**
  String get billingCancelledBody;

  /// No description provided for @billingEmptyTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma assinatura ativa'**
  String get billingEmptyTitle;

  /// No description provided for @billingEmptyBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'Quando uma assinatura for contratada, os detalhes aparecerão aqui.'**
  String get billingEmptyBody;

  /// No description provided for @billingLoadFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar a assinatura.'**
  String get billingLoadFailed;

  /// No description provided for @billingInvoicePaid.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pago'**
  String get billingInvoicePaid;

  /// No description provided for @billingInvoicePending.
  ///
  /// In pt_BR, this message translates to:
  /// **'Pendente'**
  String get billingInvoicePending;

  /// No description provided for @billingInvoiceCancelled.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cancelado'**
  String get billingInvoiceCancelled;

  /// No description provided for @billingInvoiceRefunded.
  ///
  /// In pt_BR, this message translates to:
  /// **'Reembolsado'**
  String get billingInvoiceRefunded;

  /// No description provided for @billingInvoiceFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Falhou'**
  String get billingInvoiceFailed;

  /// No description provided for @billingOpenReceipt.
  ///
  /// In pt_BR, this message translates to:
  /// **'Abrir recibo'**
  String get billingOpenReceipt;

  /// No description provided for @billingReceiptOpenFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível abrir o recibo.'**
  String get billingReceiptOpenFailed;

  /// No description provided for @billingHistoryLoadFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar o histórico.'**
  String get billingHistoryLoadFailed;

  /// No description provided for @billingInvoicesEmptyTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma cobrança encontrada'**
  String get billingInvoicesEmptyTitle;

  /// No description provided for @billingInvoicesEmptyBody.
  ///
  /// In pt_BR, this message translates to:
  /// **'As cobranças da sua assinatura aparecerão aqui.'**
  String get billingInvoicesEmptyBody;

  /// No description provided for @feedbackTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Avaliações de EPIs'**
  String get feedbackTitle;

  /// No description provided for @feedbackLoadFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Erro ao carregar avaliações'**
  String get feedbackLoadFailed;

  /// No description provided for @feedbackEmpty.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nenhuma avaliação encontrada'**
  String get feedbackEmpty;

  /// No description provided for @feedbackValidate.
  ///
  /// In pt_BR, this message translates to:
  /// **'Validar'**
  String get feedbackValidate;

  /// No description provided for @feedbackStatusOpen.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aberto'**
  String get feedbackStatusOpen;

  /// No description provided for @feedbackStatusResolved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Resolvido'**
  String get feedbackStatusResolved;

  /// No description provided for @feedbackStatusClosed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Fechado'**
  String get feedbackStatusClosed;

  /// No description provided for @feedbackStatusReceived.
  ///
  /// In pt_BR, this message translates to:
  /// **'Recebido'**
  String get feedbackStatusReceived;

  /// No description provided for @feedbackStatusManagerReview.
  ///
  /// In pt_BR, this message translates to:
  /// **'Em Análise pelo Gestor de EPI'**
  String get feedbackStatusManagerReview;

  /// No description provided for @feedbackStatusAwaitingHseq.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando HSEQ'**
  String get feedbackStatusAwaitingHseq;

  /// No description provided for @feedbackStatusHseqCompleted.
  ///
  /// In pt_BR, this message translates to:
  /// **'Análise HSEQ Concluída'**
  String get feedbackStatusHseqCompleted;

  /// No description provided for @feedbackStatusForwardedAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Encaminhado para Administração'**
  String get feedbackStatusForwardedAdmin;

  /// No description provided for @feedbackStatusAwaitingAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aguardando Aprovação Administrativa'**
  String get feedbackStatusAwaitingAdmin;

  /// No description provided for @feedbackStatusCorrectiveAction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ação Corretiva Aberta'**
  String get feedbackStatusCorrectiveAction;

  /// No description provided for @feedbackStatusMoreInformation.
  ///
  /// In pt_BR, this message translates to:
  /// **'Solicitada Mais Informação'**
  String get feedbackStatusMoreInformation;

  /// No description provided for @feedbackStatusEnded.
  ///
  /// In pt_BR, this message translates to:
  /// **'Encerrado'**
  String get feedbackStatusEnded;

  /// No description provided for @feedbackStatusNotApproved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Reprovado'**
  String get feedbackStatusNotApproved;

  /// No description provided for @qrInstruction.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aponte para um código QR ou de barras'**
  String get qrInstruction;

  /// No description provided for @qrDetected.
  ///
  /// In pt_BR, this message translates to:
  /// **'Código detectado'**
  String get qrDetected;

  /// No description provided for @qrScanAgain.
  ///
  /// In pt_BR, this message translates to:
  /// **'Escanear novamente'**
  String get qrScanAgain;

  /// No description provided for @qrTorchOn.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ligar lanterna'**
  String get qrTorchOn;

  /// No description provided for @qrTorchOff.
  ///
  /// In pt_BR, this message translates to:
  /// **'Desligar lanterna'**
  String get qrTorchOff;

  /// No description provided for @formNameLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nome'**
  String get formNameLabel;

  /// No description provided for @formCityLabel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Cidade'**
  String get formCityLabel;

  /// No description provided for @formSaveFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Erro ao salvar'**
  String get formSaveFailed;

  /// No description provided for @formExample.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ex: {value}'**
  String formExample(String value);

  /// No description provided for @userNewTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Novo usuário'**
  String get userNewTitle;

  /// No description provided for @userTemporaryPassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Senha temporária'**
  String get userTemporaryPassword;

  /// No description provided for @userPasswordHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Digite ou use o botão para gerar'**
  String get userPasswordHint;

  /// No description provided for @userCopyPassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Copiar senha'**
  String get userCopyPassword;

  /// No description provided for @userGeneratePassword.
  ///
  /// In pt_BR, this message translates to:
  /// **'Gerar senha segura'**
  String get userGeneratePassword;

  /// No description provided for @userPasswordCopied.
  ///
  /// In pt_BR, this message translates to:
  /// **'Senha copiada para a área de transferência.'**
  String get userPasswordCopied;

  /// No description provided for @userEmployeeIdRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'ID do Colaborador (obrigatório)'**
  String get userEmployeeIdRequired;

  /// No description provided for @userIdentityRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preencha usuário e nome completo'**
  String get userIdentityRequired;

  /// No description provided for @userDeleteNamed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Excluir usuário \"{name}\"?'**
  String userDeleteNamed(String name);

  /// No description provided for @unitNewTitle.
  ///
  /// In pt_BR, this message translates to:
  /// **'Nova unidade'**
  String get unitNewTitle;

  /// No description provided for @unitFieldsRequired.
  ///
  /// In pt_BR, this message translates to:
  /// **'Preencha nome, cidade e empresa'**
  String get unitFieldsRequired;

  /// No description provided for @archivalLoadFailed.
  ///
  /// In pt_BR, this message translates to:
  /// **'Não foi possível carregar a política de arquivamento.'**
  String get archivalLoadFailed;

  /// No description provided for @archivalInvalidPeriods.
  ///
  /// In pt_BR, this message translates to:
  /// **'Informe períodos válidos (mínimo 5 anos).'**
  String get archivalInvalidPeriods;

  /// No description provided for @archivalSaved.
  ///
  /// In pt_BR, this message translates to:
  /// **'Política de arquivamento salva com sucesso.'**
  String get archivalSaved;

  /// No description provided for @archivalSave.
  ///
  /// In pt_BR, this message translates to:
  /// **'Salvar política de arquivamento'**
  String get archivalSave;

  /// No description provided for @archivalYearsSuffix.
  ///
  /// In pt_BR, this message translates to:
  /// **'anos'**
  String get archivalYearsSuffix;

  /// No description provided for @archivalPolicyIntro.
  ///
  /// In pt_BR, this message translates to:
  /// **'Defina, conforme a política interna da empresa, por quantos anos os registros arquivados de cada item permanecem preservados antes de a exclusão definitiva ser habilitada (mínimo legal: 5 anos).'**
  String get archivalPolicyIntro;

  /// No description provided for @archivalPpeRecordRule.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ficha de EPI: retenção fixa de 5 anos (NR-6) — regra própria, não alterada por esta política.'**
  String get archivalPpeRecordRule;

  /// No description provided for @roleMasterAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Administrador Master'**
  String get roleMasterAdmin;

  /// No description provided for @roleGeneralAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Administrador Geral'**
  String get roleGeneralAdmin;

  /// No description provided for @roleRegistryAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Administrador de Registro'**
  String get roleRegistryAdmin;

  /// No description provided for @roleLocalAdmin.
  ///
  /// In pt_BR, this message translates to:
  /// **'Administrador Local'**
  String get roleLocalAdmin;

  /// No description provided for @rolePpeManager.
  ///
  /// In pt_BR, this message translates to:
  /// **'Gestor de EPI'**
  String get rolePpeManager;

  /// No description provided for @roleEmployee.
  ///
  /// In pt_BR, this message translates to:
  /// **'Funcionário'**
  String get roleEmployee;

  /// No description provided for @roleBuyer.
  ///
  /// In pt_BR, this message translates to:
  /// **'Comprador'**
  String get roleBuyer;

  /// No description provided for @roleApprover.
  ///
  /// In pt_BR, this message translates to:
  /// **'Aprovador'**
  String get roleApprover;

  /// No description provided for @roleCertificationReadOnly.
  ///
  /// In pt_BR, this message translates to:
  /// **'Certificação (somente leitura)'**
  String get roleCertificationReadOnly;

  /// No description provided for @unitNameHint.
  ///
  /// In pt_BR, this message translates to:
  /// **'Ex: Plataforma P-40'**
  String get unitNameHint;

  /// No description provided for @unitTypeBase.
  ///
  /// In pt_BR, this message translates to:
  /// **'Base'**
  String get unitTypeBase;

  /// No description provided for @unitTypeVessel.
  ///
  /// In pt_BR, this message translates to:
  /// **'Embarcação'**
  String get unitTypeVessel;

  /// No description provided for @unitTypePlatform.
  ///
  /// In pt_BR, this message translates to:
  /// **'Plataforma'**
  String get unitTypePlatform;
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
              (dynamic _) => app_localizations_en.AppLocalizationsEnUs(),
            );
        }
        break;
      }
    case 'es':
      {
        switch (locale.countryCode) {
          case 'ES':
            return app_localizations_es.loadLibrary().then(
              (dynamic _) => app_localizations_es.AppLocalizationsEsEs(),
            );
        }
        break;
      }
    case 'fr':
      {
        switch (locale.countryCode) {
          case 'FR':
            return app_localizations_fr.loadLibrary().then(
              (dynamic _) => app_localizations_fr.AppLocalizationsFrFr(),
            );
        }
        break;
      }
    case 'no':
      {
        switch (locale.countryCode) {
          case 'NO':
            return app_localizations_no.loadLibrary().then(
              (dynamic _) => app_localizations_no.AppLocalizationsNoNo(),
            );
        }
        break;
      }
    case 'pt':
      {
        switch (locale.countryCode) {
          case 'BR':
            return app_localizations_pt.loadLibrary().then(
              (dynamic _) => app_localizations_pt.AppLocalizationsPtBr(),
            );
        }
        break;
      }
  }

  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return app_localizations_en.loadLibrary().then(
        (dynamic _) => app_localizations_en.AppLocalizationsEn(),
      );
    case 'es':
      return app_localizations_es.loadLibrary().then(
        (dynamic _) => app_localizations_es.AppLocalizationsEs(),
      );
    case 'fr':
      return app_localizations_fr.loadLibrary().then(
        (dynamic _) => app_localizations_fr.AppLocalizationsFr(),
      );
    case 'no':
      return app_localizations_no.loadLibrary().then(
        (dynamic _) => app_localizations_no.AppLocalizationsNo(),
      );
    case 'pt':
      return app_localizations_pt.loadLibrary().then(
        (dynamic _) => app_localizations_pt.AppLocalizationsPt(),
      );
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
