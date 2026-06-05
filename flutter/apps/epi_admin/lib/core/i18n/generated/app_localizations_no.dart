// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Norwegian (`no`).
class AppLocalizationsNo extends AppLocalizations {
  AppLocalizationsNo([String locale = 'no']) : super(locale);

  @override
  String get appName => 'EPI Controle';

  @override
  String get loading => 'Carregando...';

  @override
  String get save => 'Salvar';

  @override
  String get cancel => 'Cancelar';

  @override
  String get confirm => 'Confirmar';

  @override
  String get delete => 'Excluir';

  @override
  String get edit => 'Editar';

  @override
  String get add => 'Adicionar';

  @override
  String get search => 'Buscar';

  @override
  String get filter => 'Filtrar';

  @override
  String get export => 'Exportar';

  @override
  String get print => 'Imprimir';

  @override
  String get close => 'Fechar';

  @override
  String get back => 'Voltar';

  @override
  String get next => 'Próximo';

  @override
  String get previous => 'Anterior';

  @override
  String get finish => 'Concluir';

  @override
  String get retry => 'Tentar novamente';

  @override
  String get refresh => 'Atualizar';

  @override
  String get seeAll => 'Ver todos';

  @override
  String get noResults => 'Nenhum resultado encontrado';

  @override
  String get required => 'Campo obrigatório';

  @override
  String get optional => 'Opcional';

  @override
  String get navDashboard => 'Dashboard';

  @override
  String get navCompanies => 'Empresas';

  @override
  String get navUsers => 'Usuários';

  @override
  String get navUnits => 'Unidades';

  @override
  String get navEmployees => 'Colaboradores';

  @override
  String get navEpis => 'EPIs';

  @override
  String get navStock => 'Estoque';

  @override
  String get navDeliveries => 'Entregas';

  @override
  String get navReturns => 'Devoluções';

  @override
  String get navRecords => 'Fichas';

  @override
  String get navPurchases => 'Compras';

  @override
  String get navReports => 'Relatórios';

  @override
  String get navSettings => 'Configurações';

  @override
  String get navPortal => 'Portal';

  @override
  String get navFeedback => 'Avaliações';

  @override
  String get loginTitle => 'Entrar';

  @override
  String get loginUsername => 'Usuário';

  @override
  String get loginPassword => 'Senha';

  @override
  String get loginUsernameHint => 'Informe seu usuário';

  @override
  String get loginPasswordHint => 'Informe sua senha';

  @override
  String get loginButton => 'Entrar';

  @override
  String get loginForgotPassword => 'Esqueci minha senha';

  @override
  String get loginShowPassword => 'Mostrar senha';

  @override
  String get loginHidePassword => 'Ocultar senha';

  @override
  String get loginError => 'Usuário ou senha incorretos';

  @override
  String get loginErrorEmpty => 'Preencha usuário e senha';

  @override
  String get loginBiometric => 'Biometria';

  @override
  String get dashboardTitle => 'Dashboard';

  @override
  String get dashboardDeliveriesToday => 'Entregas hoje';

  @override
  String get dashboardExpiringEpis => 'EPIs vencendo';

  @override
  String get dashboardCriticalStock => 'Estoque crítico';

  @override
  String get dashboardPendingPurchases => 'Compras pendentes';

  @override
  String get dashboardQuickDelivery => 'Nova Entrega';

  @override
  String get dashboardQuickReturn => 'Devolução';

  @override
  String get dashboardQuickScan => 'QR Scan';

  @override
  String get dashboardAlertsTitle => 'Alertas do Dia';

  @override
  String get dashboardNoAlerts => 'Nenhum alerta no momento';

  @override
  String get dashboardWeeklyChartTitle => 'Entregas — últimos 7 dias';

  @override
  String get dayMon => 'Seg';

  @override
  String get dayTue => 'Ter';

  @override
  String get dayWed => 'Qua';

  @override
  String get dayThu => 'Qui';

  @override
  String get dayFri => 'Sex';

  @override
  String get daySat => 'Sáb';

  @override
  String get daySun => 'Dom';

  @override
  String get employeesTitle => 'Colaboradores';

  @override
  String get employeesNew => 'Novo Colaborador';

  @override
  String get employeesSearchHint => 'Buscar por nome, matrícula ou setor';

  @override
  String get employeeNameLabel => 'Nome completo';

  @override
  String get employeeCodeLabel => 'Matrícula';

  @override
  String get employeeSectorLabel => 'Setor';

  @override
  String get employeeRoleLabel => 'Função';

  @override
  String get employeeUnitLabel => 'Unidade';

  @override
  String get employeeAdmissionLabel => 'Admissão';

  @override
  String get employeeScheduleLabel => 'Escala';

  @override
  String get employeeStatusActive => 'Ativo';

  @override
  String get employeeStatusInactive => 'Inativo';

  @override
  String employeeDeleteConfirm(String name) {
    return 'Excluir colaborador $name?';
  }

  @override
  String get episTitle => 'EPIs';

  @override
  String get episNew => 'Novo EPI';

  @override
  String get episSearchHint => 'Buscar por nome, CA ou código';

  @override
  String get epiNameLabel => 'Nome do EPI';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA';

  @override
  String get epiCaExpiryLabel => 'Vencimento CA';

  @override
  String get epiValidityDaysLabel => 'Validade (dias)';

  @override
  String get epiStockLabel => 'Estoque atual';

  @override
  String get epiMinStockLabel => 'Estoque mínimo';

  @override
  String get epiStatusValid => 'CA Válido';

  @override
  String epiStatusExpiring(int days) {
    return 'Vencendo em $days dias';
  }

  @override
  String get epiStatusExpired => 'CA Vencido';

  @override
  String get epiStatusNoStock => 'Sem estoque';

  @override
  String get stockTitle => 'Estoque';

  @override
  String get stockScan => 'Escanear QR';

  @override
  String get stockMoveIn => 'Entrada';

  @override
  String get stockMoveOut => 'Saída';

  @override
  String get stockBatch => 'Operação em lote';

  @override
  String get stockMinimumAlert => 'Estoque mínimo atingido';

  @override
  String stockCriticalAlert(String name) {
    return 'Estoque crítico — $name';
  }

  @override
  String get deliveriesTitle => 'Entregas';

  @override
  String get deliveryNew => 'Nova Entrega';

  @override
  String get deliveryStep1 => 'Colaborador';

  @override
  String get deliveryStep2 => 'EPI';

  @override
  String get deliveryStep3 => 'Revisão';

  @override
  String get deliveryStep4 => 'Assinatura';

  @override
  String get deliveryConfirm => 'Confirmar entrega';

  @override
  String get deliverySuccess => 'Entrega registrada com sucesso';

  @override
  String get deliveryOfflineQueued =>
      'Entrega salva — será sincronizada quando houver conexão';

  @override
  String get deliverySignatureRequired => 'Assinatura obrigatória';

  @override
  String get deliveryClearSignature => 'Limpar assinatura';

  @override
  String get returnsTitle => 'Devoluções';

  @override
  String get returnNew => 'Nova Devolução';

  @override
  String get returnStep1 => 'Selecionar EPI';

  @override
  String get returnStep2 => 'Condição';

  @override
  String get returnStep3 => 'Confirmar';

  @override
  String get returnConditionGood => 'Bom estado';

  @override
  String get returnConditionDamaged => 'Danificado';

  @override
  String get returnConditionLost => 'Extraviado';

  @override
  String get returnSuccess => 'Devolução registrada com sucesso.';

  @override
  String get returnOfflineQueued =>
      'Devolução salva — será sincronizada quando houver conexão.';

  @override
  String get recordsTitle => 'Fichas';

  @override
  String get recordsPreview => 'Visualizar ficha';

  @override
  String get recordsPrint => 'Imprimir ficha';

  @override
  String get recordsSearchHint => 'Buscar por funcionário, código ou unidade…';

  @override
  String get recordsStatusComplete => 'Completo';

  @override
  String get recordsStatusPending => 'Pendente';

  @override
  String get recordsStatusOverdue => 'Atrasado';

  @override
  String get purchasesTitle => 'Compras';

  @override
  String get purchasesNew => 'Novo Pedido';

  @override
  String get purchaseStatusDraft => 'Rascunho';

  @override
  String get purchaseStatusSent => 'Enviado';

  @override
  String get purchaseStatusPending => 'Aguardando aprovação';

  @override
  String get purchaseStatusApproved => 'Aprovado';

  @override
  String get purchaseStatusRejected => 'Rejeitado';

  @override
  String get purchaseStatusOrdering => 'Em pedido';

  @override
  String get purchaseStatusReceived => 'Recebido';

  @override
  String get reportsTitle => 'Relatórios';

  @override
  String get reportsGenerate => 'Gerar relatório';

  @override
  String get reportsPeriod => 'Período';

  @override
  String get reportsExport => 'Exportar';

  @override
  String get reportsSummaryTab => 'Resumo';

  @override
  String get reportsRequestsTab => 'Solicitações';

  @override
  String get reportsTotalDeliveries => 'Total de entregas';

  @override
  String get reportsTopEpis => 'Top EPIs entregues';

  @override
  String get reportsTopSectors => 'Entregas por setor';

  @override
  String get reportsRequestStatusPending => 'Aguardando';

  @override
  String get reportsRequestStatusProcessing => 'Processando';

  @override
  String get reportsRequestStatusCompleted => 'Concluído';

  @override
  String get reportsRequestStatusFailed => 'Falhou';

  @override
  String get reportsAllUnits => 'Todas as unidades';

  @override
  String get reportsRequestDialogTitle => 'Solicitar relatório';

  @override
  String get reportsRequestYear => 'Ano';

  @override
  String get reportsRequestMonth => 'Mês';

  @override
  String get reportsRequestNotes => 'Observações (opcional)';

  @override
  String get reportsRequestSubmit => 'Solicitar';

  @override
  String get reportsNoRequests => 'Nenhuma solicitação';

  @override
  String get reportsNoData => 'Nenhum dado disponível';

  @override
  String get reportsRequestSuccess => 'Solicitação enviada com sucesso.';

  @override
  String get companiesTitle => 'Empresas';

  @override
  String get companiesSearchHint => 'Buscar por nome ou CNPJ';

  @override
  String get companyStatusActive => 'Ativo';

  @override
  String get companyStatusInactive => 'Inativo';

  @override
  String get companyStatusSuspended => 'Suspenso';

  @override
  String get settingsTitle => 'Configurações';

  @override
  String get settingsLanguage => 'Idioma';

  @override
  String get settingsLanguageUser => 'Idioma do usuário';

  @override
  String get settingsLanguageCompany => 'Idioma da empresa';

  @override
  String get settingsTheme => 'Tema';

  @override
  String get settingsThemeLight => 'Claro';

  @override
  String get settingsThemeDark => 'Escuro';

  @override
  String get settingsThemeSystem => 'Sistema';

  @override
  String get settingsAppSection => 'Aplicativo';

  @override
  String get settingsFichaSection => 'Ficha';

  @override
  String get settingsFichaTitle => 'Título da ficha';

  @override
  String get settingsFichaDeclaration => 'Declaração';

  @override
  String get settingsFichaObservations => 'Observações';

  @override
  String get settingsFichaTracking => 'Rastreabilidade';

  @override
  String get settingsSaved => 'Configurações salvas com sucesso.';

  @override
  String get portalTitle => 'Portal do Colaborador';

  @override
  String get portalScanQr => 'Escanear QR Code';

  @override
  String get portalEnterCpf => 'Informe seu CPF';

  @override
  String get portalCpfHint => 'Ex: 000.000.000-00';

  @override
  String get portalCpfVerify => 'Acessar portal';

  @override
  String get portalHistory => 'Meu histórico de EPIs';

  @override
  String get portalSignature => 'Confirmar assinatura';

  @override
  String get portalSignatureInstruction =>
      'Assine no espaço abaixo para confirmar o recebimento';

  @override
  String get portalDeliveries => 'Entregas';

  @override
  String get portalFichas => 'Fichas';

  @override
  String get portalSignDelivery => 'Assinar';

  @override
  String get portalSignAll => 'Assinar todas';

  @override
  String get portalSigned => 'Assinado';

  @override
  String get portalUnsigned => 'Pendente';

  @override
  String get portalSignSuccess => 'Assinatura registrada com sucesso.';

  @override
  String get portalNoDeliveries => 'Nenhuma entrega encontrada';

  @override
  String get portalQty => 'Qtd';

  @override
  String get errorGeneric => 'Ocorreu um erro. Tente novamente.';

  @override
  String get errorNetwork => 'Sem conexão com a internet';

  @override
  String get errorUnauthorized => 'Sessão expirada. Faça login novamente.';

  @override
  String get errorNotFound => 'Registro não encontrado';

  @override
  String get errorServerError => 'Erro no servidor. Tente mais tarde.';

  @override
  String get statusActive => 'Ativo';

  @override
  String get statusInactive => 'Inativo';

  @override
  String get statusExpired => 'Vencido';

  @override
  String get statusExpiring => 'Vencendo';

  @override
  String get statusPending => 'Pendente';

  @override
  String get statusApproved => 'Aprovado';

  @override
  String get statusRejected => 'Rejeitado';

  @override
  String get statusInReview => 'Em análise';

  @override
  String get confirmDeleteTitle => 'Confirmar exclusão';

  @override
  String get confirmDeleteMessage => 'Esta ação não pode ser desfeita.';

  @override
  String get confirmDeleteButton => 'Excluir';

  @override
  String get employeeContactTitle => 'Contatar colaborador';

  @override
  String get employeeContactWhatsapp => 'WhatsApp';

  @override
  String get employeeContactEmail => 'E-mail';

  @override
  String get employeeContactPdf => 'Baixar PDF';

  @override
  String get employeeContactLaunching => 'Abrindo...';

  @override
  String get employeeContactPdfDownloading => 'Baixando PDF...';

  @override
  String get employeeContactErrorNoApp =>
      'Nenhum app disponível para abrir este link';

  @override
  String get employeeContactErrorGeneric =>
      'Falha ao contatar colaborador. Tente novamente.';

  @override
  String get employeeContactPdfError =>
      'Falha ao baixar o PDF. Tente novamente.';

  @override
  String get offlineBanner => 'Sem conexão — dados salvos localmente';

  @override
  String get syncingBanner => 'Sincronizando dados...';

  @override
  String get syncDone => 'Dados sincronizados';
}

/// The translations for Norwegian, as used in Norway (`no_NO`).
class AppLocalizationsNoNo extends AppLocalizationsNo {
  AppLocalizationsNoNo() : super('no_NO');

  @override
  String get appName => 'EPI Kontroll';

  @override
  String get loading => 'Laster...';

  @override
  String get save => 'Lagre';

  @override
  String get cancel => 'Avbryt';

  @override
  String get confirm => 'Bekreft';

  @override
  String get delete => 'Slett';

  @override
  String get edit => 'Rediger';

  @override
  String get add => 'Legg til';

  @override
  String get search => 'Søk';

  @override
  String get filter => 'Filtrer';

  @override
  String get export => 'Eksporter';

  @override
  String get print => 'Skriv ut';

  @override
  String get close => 'Lukk';

  @override
  String get back => 'Tilbake';

  @override
  String get next => 'Neste';

  @override
  String get previous => 'Forrige';

  @override
  String get finish => 'Fullfør';

  @override
  String get retry => 'Prøv igjen';

  @override
  String get refresh => 'Oppdater';

  @override
  String get seeAll => 'Se alle';

  @override
  String get noResults => 'Ingen resultater funnet';

  @override
  String get required => 'Obligatorisk felt';

  @override
  String get optional => 'Valgfritt';

  @override
  String get navDashboard => 'Oversikt';

  @override
  String get navCompanies => 'Selskaper';

  @override
  String get navUsers => 'Brukere';

  @override
  String get navUnits => 'Enheter';

  @override
  String get navEmployees => 'Ansatte';

  @override
  String get navEpis => 'PVU';

  @override
  String get navStock => 'Lager';

  @override
  String get navDeliveries => 'Utleveringer';

  @override
  String get navReturns => 'Returer';

  @override
  String get navRecords => 'Skjemaer';

  @override
  String get navPurchases => 'Innkjøp';

  @override
  String get navReports => 'Rapporter';

  @override
  String get navSettings => 'Innstillinger';

  @override
  String get navPortal => 'Portal';

  @override
  String get navFeedback => 'Tilbakemeldinger';

  @override
  String get loginTitle => 'Logg inn';

  @override
  String get loginUsername => 'Brukernavn';

  @override
  String get loginPassword => 'Passord';

  @override
  String get loginUsernameHint => 'Skriv inn brukernavn';

  @override
  String get loginPasswordHint => 'Skriv inn passord';

  @override
  String get loginButton => 'Logg inn';

  @override
  String get loginForgotPassword => 'Glemt passord';

  @override
  String get loginShowPassword => 'Vis passord';

  @override
  String get loginHidePassword => 'Skjul passord';

  @override
  String get loginError => 'Feil brukernavn eller passord';

  @override
  String get loginErrorEmpty => 'Vennligst skriv inn brukernavn og passord';

  @override
  String get loginBiometric => 'Biometri';

  @override
  String get dashboardTitle => 'Oversikt';

  @override
  String get dashboardDeliveriesToday => 'Utleveringer i dag';

  @override
  String get dashboardExpiringEpis => 'Utløpende PVU';

  @override
  String get dashboardCriticalStock => 'Kritisk lager';

  @override
  String get dashboardPendingPurchases => 'Ventende innkjøp';

  @override
  String get dashboardQuickDelivery => 'Ny utlevering';

  @override
  String get dashboardQuickReturn => 'Retur';

  @override
  String get dashboardQuickScan => 'QR-skanning';

  @override
  String get dashboardAlertsTitle => 'Dagens varsler';

  @override
  String get dashboardNoAlerts => 'Ingen varsler for øyeblikket';

  @override
  String get dashboardWeeklyChartTitle => 'Utleveringer — siste 7 dager';

  @override
  String get dayMon => 'Man';

  @override
  String get dayTue => 'Tir';

  @override
  String get dayWed => 'Ons';

  @override
  String get dayThu => 'Tor';

  @override
  String get dayFri => 'Fre';

  @override
  String get daySat => 'Lør';

  @override
  String get daySun => 'Søn';

  @override
  String get employeesTitle => 'Ansatte';

  @override
  String get employeesNew => 'Ny ansatt';

  @override
  String get employeesSearchHint => 'Søk etter navn, kode eller avdeling';

  @override
  String get employeeNameLabel => 'Fullt navn';

  @override
  String get employeeCodeLabel => 'Ansatt-ID';

  @override
  String get employeeSectorLabel => 'Avdeling';

  @override
  String get employeeRoleLabel => 'Stilling';

  @override
  String get employeeUnitLabel => 'Enhet';

  @override
  String get employeeAdmissionLabel => 'Ansettelsesdato';

  @override
  String get employeeScheduleLabel => 'Arbeidsplan';

  @override
  String get employeeStatusActive => 'Aktiv';

  @override
  String get employeeStatusInactive => 'Inaktiv';

  @override
  String employeeDeleteConfirm(String name) {
    return 'Slett ansatt $name?';
  }

  @override
  String get episTitle => 'PVU';

  @override
  String get episNew => 'Nytt PVU';

  @override
  String get episSearchHint => 'Søk etter navn, godkjenningsnummer eller kode';

  @override
  String get epiNameLabel => 'PVU-navn';

  @override
  String get epiCodeLabel => 'Innkjøpskode';

  @override
  String get epiCaLabel => 'Godkjenningsnr.';

  @override
  String get epiCaExpiryLabel => 'Godkjenning utløper';

  @override
  String get epiValidityDaysLabel => 'Gyldighet (dager)';

  @override
  String get epiStockLabel => 'Nåværende lager';

  @override
  String get epiMinStockLabel => 'Minimumslager';

  @override
  String get epiStatusValid => 'Gyldig';

  @override
  String epiStatusExpiring(int days) {
    return 'Utløper om $days dager';
  }

  @override
  String get epiStatusExpired => 'Utløpt';

  @override
  String get epiStatusNoStock => 'Tomt lager';

  @override
  String get stockTitle => 'Lager';

  @override
  String get stockScan => 'Skann QR';

  @override
  String get stockMoveIn => 'Inn på lager';

  @override
  String get stockMoveOut => 'Ut av lager';

  @override
  String get stockBatch => 'Batchoperasjon';

  @override
  String get stockMinimumAlert => 'Minimumslager nådd';

  @override
  String stockCriticalAlert(String name) {
    return 'Kritisk lager — $name';
  }

  @override
  String get deliveriesTitle => 'Utleveringer';

  @override
  String get deliveryNew => 'Ny utlevering';

  @override
  String get deliveryStep1 => 'Ansatt';

  @override
  String get deliveryStep2 => 'PVU';

  @override
  String get deliveryStep3 => 'Gjennomgang';

  @override
  String get deliveryStep4 => 'Signatur';

  @override
  String get deliveryConfirm => 'Bekreft utlevering';

  @override
  String get deliverySuccess => 'Utlevering registrert';

  @override
  String get deliveryOfflineQueued =>
      'Utlevering lagret — synkroniseres ved tilkobling';

  @override
  String get deliverySignatureRequired => 'Signatur påkrevd';

  @override
  String get deliveryClearSignature => 'Fjern signatur';

  @override
  String get returnsTitle => 'Returer';

  @override
  String get returnNew => 'Ny retur';

  @override
  String get returnStep1 => 'Velg PVU';

  @override
  String get returnStep2 => 'Tilstand';

  @override
  String get returnStep3 => 'Bekreft';

  @override
  String get returnConditionGood => 'God stand';

  @override
  String get returnConditionDamaged => 'Skadet';

  @override
  String get returnConditionLost => 'Mistet';

  @override
  String get returnSuccess => 'Retur registrert.';

  @override
  String get returnOfflineQueued => 'Retur lagret — synkroniseres ved tilkobling.';

  @override
  String get recordsTitle => 'Skjemaer';

  @override
  String get recordsPreview => 'Forhåndsvis skjema';

  @override
  String get recordsPrint => 'Skriv ut skjema';

  @override
  String get recordsSearchHint => 'Søk etter ansatt, kode eller enhet…';

  @override
  String get recordsStatusComplete => 'Fullført';

  @override
  String get recordsStatusPending => 'Venter';

  @override
  String get recordsStatusOverdue => 'Forfalt';

  @override
  String get purchasesTitle => 'Innkjøp';

  @override
  String get purchasesNew => 'Ny bestilling';

  @override
  String get purchaseStatusDraft => 'Utkast';

  @override
  String get purchaseStatusSent => 'Sendt';

  @override
  String get purchaseStatusPending => 'Venter på godkjenning';

  @override
  String get purchaseStatusApproved => 'Godkjent';

  @override
  String get purchaseStatusRejected => 'Avvist';

  @override
  String get purchaseStatusOrdering => 'Bestilles';

  @override
  String get purchaseStatusReceived => 'Mottatt';

  @override
  String get reportsTitle => 'Rapporter';

  @override
  String get reportsGenerate => 'Generer rapport';

  @override
  String get reportsPeriod => 'Periode';

  @override
  String get reportsExport => 'Eksporter';

  @override
  String get reportsSummaryTab => 'Sammendrag';

  @override
  String get reportsRequestsTab => 'Forespørsler';

  @override
  String get reportsTotalDeliveries => 'Totale utleveringer';

  @override
  String get reportsTopEpis => 'Mest utleverte PVU';

  @override
  String get reportsTopSectors => 'Utleveringer per avdeling';

  @override
  String get reportsRequestStatusPending => 'Venter';

  @override
  String get reportsRequestStatusProcessing => 'Behandler';

  @override
  String get reportsRequestStatusCompleted => 'Fullført';

  @override
  String get reportsRequestStatusFailed => 'Mislyktes';

  @override
  String get reportsAllUnits => 'Alle enheter';

  @override
  String get reportsRequestDialogTitle => 'Be om rapport';

  @override
  String get reportsRequestYear => 'År';

  @override
  String get reportsRequestMonth => 'Måned';

  @override
  String get reportsRequestNotes => 'Merknader (valgfritt)';

  @override
  String get reportsRequestSubmit => 'Be om';

  @override
  String get reportsNoRequests => 'Ingen forespørsler';

  @override
  String get reportsNoData => 'Ingen data tilgjengelig';

  @override
  String get reportsRequestSuccess => 'Forespørsel sendt.';

  @override
  String get companiesTitle => 'Selskaper';

  @override
  String get companiesSearchHint => 'Søk etter navn eller organisasjonsnummer';

  @override
  String get companyStatusActive => 'Aktiv';

  @override
  String get companyStatusInactive => 'Inaktiv';

  @override
  String get companyStatusSuspended => 'Suspendert';

  @override
  String get settingsTitle => 'Innstillinger';

  @override
  String get settingsLanguage => 'Språk';

  @override
  String get settingsLanguageUser => 'Brukerspråk';

  @override
  String get settingsLanguageCompany => 'Selskapsspråk';

  @override
  String get settingsTheme => 'Tema';

  @override
  String get settingsThemeLight => 'Lyst';

  @override
  String get settingsThemeDark => 'Mørkt';

  @override
  String get settingsThemeSystem => 'System';

  @override
  String get settingsAppSection => 'Applikasjon';

  @override
  String get settingsFichaSection => 'Skjema';

  @override
  String get settingsFichaTitle => 'Skjematittel';

  @override
  String get settingsFichaDeclaration => 'Erklæring';

  @override
  String get settingsFichaObservations => 'Merknader';

  @override
  String get settingsFichaTracking => 'Sporbarhet';

  @override
  String get settingsSaved => 'Innstillinger lagret.';

  @override
  String get portalTitle => 'Ansattportal';

  @override
  String get portalScanQr => 'Skann QR-kode';

  @override
  String get portalEnterCpf => 'Skriv inn din ID';

  @override
  String get portalCpfHint => 'Eks: 000.000.000-00';

  @override
  String get portalCpfVerify => 'Åpne portal';

  @override
  String get portalHistory => 'Min PVU-historikk';

  @override
  String get portalSignature => 'Bekreft signatur';

  @override
  String get portalSignatureInstruction =>
      'Signer i feltet nedenfor for å bekrefte mottak';

  @override
  String get portalDeliveries => 'Utleveringer';

  @override
  String get portalFichas => 'Skjemaer';

  @override
  String get portalSignDelivery => 'Signer';

  @override
  String get portalSignAll => 'Signer alle';

  @override
  String get portalSigned => 'Signert';

  @override
  String get portalUnsigned => 'Venter';

  @override
  String get portalSignSuccess => 'Signatur registrert.';

  @override
  String get portalNoDeliveries => 'Ingen utleveringer funnet';

  @override
  String get portalQty => 'Ant';

  @override
  String get errorGeneric => 'En feil oppstod. Prøv igjen.';

  @override
  String get errorNetwork => 'Ingen internettilkobling';

  @override
  String get errorUnauthorized => 'Sesjonen er utløpt. Logg inn på nytt.';

  @override
  String get errorNotFound => 'Post ikke funnet';

  @override
  String get errorServerError => 'Serverfeil. Prøv igjen senere.';

  @override
  String get statusActive => 'Aktiv';

  @override
  String get statusInactive => 'Inaktiv';

  @override
  String get statusExpired => 'Utløpt';

  @override
  String get statusExpiring => 'Utløper snart';

  @override
  String get statusPending => 'Venter';

  @override
  String get statusApproved => 'Godkjent';

  @override
  String get statusRejected => 'Avvist';

  @override
  String get statusInReview => 'Under vurdering';

  @override
  String get confirmDeleteTitle => 'Bekreft sletting';

  @override
  String get confirmDeleteMessage => 'Denne handlingen kan ikke angres.';

  @override
  String get confirmDeleteButton => 'Slett';

  @override
  String get employeeContactTitle => 'Kontakt ansatt';

  @override
  String get employeeContactWhatsapp => 'WhatsApp';

  @override
  String get employeeContactEmail => 'E-post';

  @override
  String get employeeContactPdf => 'Last ned PDF';

  @override
  String get employeeContactLaunching => 'Åpner...';

  @override
  String get employeeContactPdfDownloading => 'Laster ned PDF...';

  @override
  String get employeeContactErrorNoApp =>
      'Ingen app tilgjengelig for å åpne denne lenken';

  @override
  String get employeeContactErrorGeneric =>
      'Kunne ikke kontakte ansatt. Vennligst prøv igjen.';

  @override
  String get employeeContactPdfError =>
      'Kunne ikke laste ned PDF. Vennligst prøv igjen.';

  @override
  String get offlineBanner => 'Frakoblet — data lagret lokalt';

  @override
  String get syncingBanner => 'Synkroniserer data...';

  @override
  String get syncDone => 'Data synkronisert';
}
