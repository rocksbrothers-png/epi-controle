// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Portuguese (`pt`).
class AppLocalizationsPt extends AppLocalizations {
  AppLocalizationsPt([String locale = 'pt']) : super(locale);

  @override
  String get appName => 'EPI Controle';

  @override
  String get loading => 'Carregando...';

  @override
  String get save => 'Salvar';

  @override
  String get cancel => 'Cancelar';

  @override
  String get reportsExportPdf => 'Exportar PDF';

  @override
  String get feedbackForward => 'Encaminhar';

  @override
  String get feedbackReject => 'Rejeitar';

  @override
  String get feedbackApprove => 'Aprovar';

  @override
  String get feedbackJustification => 'Justificativa';

  @override
  String get feedbackRejectReason => 'Motivo da rejeição';

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
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Setor';

  @override
  String get employeeRoleLabel => 'Função';

  @override
  String get employeeUnitLabel => 'Unidade';

  @override
  String get employeeUnitLockedHint =>
      'Unidade definida pelo seu perfil de acesso.';

  @override
  String get employeeLegalEntityLabel => 'CNPJ';

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
  String get episSearchHint => 'Buscar por nome, CA brasileiro ou código';

  @override
  String get epiNameLabel => 'Nome do EPI';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA — Certificado de Aprovação';

  @override
  String get epiSectorLabel => 'Setor';

  @override
  String get epiSectionLabel => 'Seção do EPI';

  @override
  String get epiModelLabel => 'Modelo/referência';

  @override
  String get epiManufacturerLabel => 'Fabricante';

  @override
  String get epiSupplierLabel => 'Fornecedor';

  @override
  String get epiUnitMeasureLabel => 'Unidade de medida';

  @override
  String get epiValidityDateLabel => 'Data de validade';

  @override
  String get epiManufacturerValidityLabel => 'Validade (meses)';

  @override
  String get epiCaExpiryLabel => 'Validade do CA';

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
  String get purchaseOrdersTitle => 'Ordens de Compra';

  @override
  String get poApprove => 'Aprovar';

  @override
  String get poReceive => 'Receber';

  @override
  String get poQuantityReceived => 'Qtd. recebida';

  @override
  String get poReceiveNotes => 'Observação';

  @override
  String get poManufacturerValidity => 'Validade do fabricante';

  @override
  String get poManufacturerValidityHint => 'Informar data';

  @override
  String get poManufacturerValidityRequired =>
      'Informe a validade do fabricante de todos os EPIs recebidos.';

  @override
  String get poOcrDateNotFound =>
      'Não foi possível identificar a data. Tente novamente.';

  @override
  String get poOcrCameraFailed => 'Falha na leitura por câmera.';

  @override
  String get poPickDate => 'Selecionar data';

  @override
  String get poReadDateCamera => 'Ler data por câmera (OCR)';

  @override
  String get poCheck => 'Conferir';

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

  @override
  String get searchEmployeeHint => 'Buscar colaborador...';

  @override
  String get searchEpiHint => 'Buscar EPI...';

  @override
  String get fieldQuantity => 'Quantidade';

  @override
  String get filterAll => 'Todos';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Estoque: $qty';
  }

  @override
  String get deliveryDateLabel => 'Data da entrega';

  @override
  String get deliveryNextReplacement => 'Próxima substituição';

  @override
  String deliveryDateValue(String date) {
    return 'Data: $date';
  }

  @override
  String get returnSelectDelivery => 'Selecionar entrega para devolver';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Entregue em $date · Qtd: $qty';
  }

  @override
  String get returnConditionTitle => 'Condição do EPI';

  @override
  String get returnDestinationTitle => 'Destino';

  @override
  String get returnDestDiscard => 'Descarte';

  @override
  String get returnDestRepair => 'Manutenção';

  @override
  String get returnDestStock => 'Retornar ao estoque';

  @override
  String get returnSubmit => 'Registrar Devolução';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Entrega: $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Quantidade: $qty';
  }

  @override
  String get purchaseTitleLabel => 'Título da requisição';

  @override
  String get purchaseSelectUnit => 'Selecione uma unidade';

  @override
  String get purchaseItemsTitle => 'Itens da requisição';

  @override
  String get purchaseAddEpi => 'Adicionar EPI';

  @override
  String get purchaseNoItems => 'Nenhum item adicionado';

  @override
  String get purchaseCreate => 'Criar Requisição';

  @override
  String get purchaseAddAtLeastOne => 'Adicione pelo menos um item';

  @override
  String get purchaseQuantityColon => 'Quantidade:';

  @override
  String purchaseItemsCount(int count) {
    return '$count itens';
  }

  @override
  String get purchaseStatusAwaiting => 'Aguardando';

  @override
  String get purchaseStatusCorrection => 'Correção solicitada';

  @override
  String get purchaseStatusAwaitingReceipt => 'Aguardando recebimento';

  @override
  String get purchaseStatusCompleted => 'Concluído';

  @override
  String get purchaseStatusCancelled => 'Cancelado';

  @override
  String get suppliersTitle => 'Fornecedores';

  @override
  String get supplierNew => 'Novo fornecedor';

  @override
  String get supplierEdit => 'Editar fornecedor';

  @override
  String get supplierCnpjLabel => 'CNPJ';

  @override
  String get supplierPhoneLabel => 'Telefone';

  @override
  String get supplierPaymentTermsLabel => 'Condições de pagamento';

  @override
  String get supplierIntegrationLevelLabel => 'Nível de integração';

  @override
  String get supplierInactiveLabel => 'Inativo';

  @override
  String get supplierCatalogTitle => 'Catálogo do fornecedor';

  @override
  String get catalogNewProduct => 'Novo produto';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Descrição';

  @override
  String get catalogLastPriceLabel => 'Último preço';

  @override
  String get catalogLeadTimeLabel => 'Prazo (dias)';

  @override
  String get quotesTitle => 'Cotações';

  @override
  String get quotesNew => 'Nova cotação';

  @override
  String get quotesSelectSuppliers => 'Selecione os fornecedores';

  @override
  String get quoteSendEmail => 'Enviar por e-mail';

  @override
  String get quoteSendPortal => 'Enviar pelo portal';

  @override
  String get quoteAnswerAction => 'Registrar resposta';

  @override
  String get quoteSelectWinner => 'Selecionar vencedora';

  @override
  String get quoteComparisonTitle => 'Comparação de cotações';

  @override
  String get quoteFreightLabel => 'Frete';

  @override
  String get quoteUnitPriceLabel => 'Preço unitário';

  @override
  String get quoteDeclinedLabel => 'Recusado';

  @override
  String get quoteBestPriceLabel => 'Melhor preço';

  @override
  String get quoteBestLeadTimeLabel => 'Melhor prazo';

  @override
  String get quoteCreatePo => 'Gerar PO a partir da cotação vencedora?';

  @override
  String get poSupplierActionsTitle => 'Fornecedor e entrega';

  @override
  String get poSendToSupplier => 'Enviar ao fornecedor';

  @override
  String get poPortalLinkAction => 'Enviar link do portal';

  @override
  String get poRegisterConfirmation => 'Registrar confirmação';

  @override
  String get poTrackingTitle => 'Acompanhamento';

  @override
  String get poDeliveryForecastLabel => 'Previsão de entrega';

  @override
  String get poCarrierLabel => 'Transportadora';

  @override
  String get poTrackingCodeLabel => 'Código de rastreio';

  @override
  String get commentLabel => 'Comentário';

  @override
  String get actionSentSuccess => 'Enviado com sucesso';

  @override
  String get myCompanyTitle => 'Minha Empresa';

  @override
  String get myCompanySubtitle =>
      'Dados, identidade visual e domínio da sua empresa';

  @override
  String get myCompanySaved => 'Configurações da empresa salvas com sucesso.';

  @override
  String get myCompanyLoadError =>
      'Não foi possível carregar os dados da empresa.';

  @override
  String get myCompanyContractSection => 'Contrato (somente leitura)';

  @override
  String get myCompanyPlan => 'Plano';

  @override
  String get myCompanyUserLimit => 'Limite de usuários';

  @override
  String get myCompanyLicense => 'Licença';

  @override
  String get myCompanyRegistrationSection => 'Dados cadastrais';

  @override
  String get myCompanyName => 'Nome fantasia';

  @override
  String get myCompanyLegalName => 'Razão social';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'Inscrição estadual';

  @override
  String get myCompanyMunicipalRegistration => 'Inscrição municipal';

  @override
  String get myCompanyAddress => 'Endereço';

  @override
  String get myCompanyPhone => 'Telefone';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'E-mail institucional';

  @override
  String get myCompanyWebsite => 'Website';

  @override
  String get myCompanyIdentitySection => 'Identidade e tema';

  @override
  String get myCompanyDisplayName => 'Nome exibido no sistema';

  @override
  String get myCompanyInstitutionalMessage => 'Mensagem institucional';

  @override
  String get myCompanyPrimaryColor => 'Cor principal (hex)';

  @override
  String get myCompanySecondaryColor => 'Cor secundária (hex)';

  @override
  String get myCompanyPreferencesSection => 'Preferências';

  @override
  String get myCompanyTimezone => 'Fuso horário';

  @override
  String get myCompanySave => 'Salvar configurações da empresa';

  @override
  String get myCompanyDomainsSection => 'Domínios';

  @override
  String get myCompanyDomainField => 'Domínio';

  @override
  String get myCompanyDomainTypePlatform => 'Subdomínio da plataforma';

  @override
  String get myCompanyDomainTypeCustomSub => 'Subdomínio personalizado';

  @override
  String get myCompanyDomainTypeCustom => 'Domínio personalizado';

  @override
  String get myCompanyDomainAdd => 'Registrar domínio';

  @override
  String get myCompanyDomainVerify => 'Verificar';

  @override
  String get myCompanyDomainDelete => 'Remover';

  @override
  String get myCompanyDomainPending => 'Pendente';

  @override
  String get myCompanyDomainVerified => 'Verificado';

  @override
  String get myCompanyDomainFailed => 'Falhou';

  @override
  String get myCompanyDomainPrimary => 'Principal';

  @override
  String get myCompanyDomainCname => 'Aponte o CNAME para';

  @override
  String get myCompanyDomainTxt => 'Crie o registro TXT';

  @override
  String get myCompanyDomainToken => 'Valor do TXT';

  @override
  String get epiArchiveBlockTitle => 'Arquivar com bloqueio de saldo';

  @override
  String get epiArchiveBlockBody =>
      'Este EPI possui saldo disponível ou vínculos vivos. Ao confirmar, o saldo disponível será movido para Estoque Bloqueado (rastreável) e o EPI será arquivado.';

  @override
  String get epiArchiveBlockConfirm => 'Bloquear saldo e arquivar';

  @override
  String get epiArchiveReasonLabel => 'Motivo do arquivamento (auditoria)';

  @override
  String get epiArchiveReasonRequired => 'Informe o motivo para prosseguir.';

  @override
  String get epiArchiveBlockableLabel => 'Saldo a bloquear';

  @override
  String get epiArchiveLiveLinksTitle => 'Vínculos vivos';

  @override
  String get epiArchiveAvailable => 'Disponível';

  @override
  String get epiArchiveInTransit => 'Em trânsito';

  @override
  String get epiArchiveInPossession => 'Em posse';

  @override
  String get epiArchivePendingRequests => 'Requisições abertas';

  @override
  String get epiArchivePendingPurchase => 'Compras abertas';

  @override
  String get dashboardComplianceTitle => 'Conformidade de estoque';

  @override
  String get dashboardComplianceAllOk => 'Estoque em conformidade';

  @override
  String get complianceCaExpired => 'CA vencido';

  @override
  String get complianceCaExpiring => 'CA a vencer';

  @override
  String get complianceProductExpired => 'Produto vencido';

  @override
  String get complianceProductExpiring => 'Produto a vencer';

  @override
  String get complianceMissingManufacture => 'Sem fabricação';

  @override
  String get complianceMissingLot => 'Sem lote';

  @override
  String get complianceAdminBlocked => 'Bloqueado';

  @override
  String get handoverTitle => 'Conferência de entrega';

  @override
  String get handoverPrompt => 'Escaneie o QR da entrega ou informe o código.';

  @override
  String get handoverCodeLabel => 'Código da entrega';

  @override
  String get handoverLookupButton => 'Buscar entrega';

  @override
  String get handoverScanButton => 'Escanear QR';

  @override
  String get handoverConfirmButton => 'Confirmar recebimento';

  @override
  String get handoverConfirmedTitle => 'Recebimento confirmado';

  @override
  String get handoverAlreadyConfirmed => 'Esta entrega já foi confirmada.';

  @override
  String get handoverNotFound => 'Entrega não encontrada para este código.';

  @override
  String get handoverConfirmError =>
      'Não foi possível confirmar o recebimento.';

  @override
  String get handoverEmployeeLabel => 'Colaborador';

  @override
  String get handoverEpiLabel => 'EPI';

  @override
  String get handoverQuantityLabel => 'Quantidade';

  @override
  String get handoverSectorLabel => 'Setor';

  @override
  String get handoverRoleLabel => 'Função';

  @override
  String get handoverUnitLabel => 'Unidade';

  @override
  String get handoverDeliveryDateLabel => 'Data da entrega';

  @override
  String get handoverReceiverNameLabel => 'Nome de quem recebe (opcional)';

  @override
  String get handoverScanAgain => 'Nova conferência';

  @override
  String get legalEntitiesTitle => 'CNPJs';

  @override
  String get legalEntitiesNew => 'Novo CNPJ';

  @override
  String get legalEntityLegalNameLabel => 'Razão social';

  @override
  String get legalEntityTradeNameLabel => 'Nome fantasia';

  @override
  String get legalEntityTypeLabel => 'Tipo';

  @override
  String get legalEntityInactiveBadge => 'Inativo';

  @override
  String get legalEntityDeactivate => 'Inativar CNPJ';

  @override
  String get legalEntityDeactivateHint =>
      'O histórico jurídico é preservado. O CNPJ deixa de ser usado em novas operações.';

  @override
  String get legalEntityShowInactive => 'Mostrar inativos';

  @override
  String get legalEntitiesEmpty => 'Nenhum CNPJ cadastrado.';

  @override
  String get legalEntityMunicipalityLabel => 'Município';

  @override
  String get legalEntityCnpjLabel => 'CNPJ';

  @override
  String get legalEntityUfLabel => 'UF';

  @override
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRazão social\tNome fantasia\tTipo';

  @override
  String get legalEntitiesImport => 'Importar planilha';

  @override
  String get legalEntitiesImportHint =>
      'Copie as linhas da planilha (com a linha de cabeçalho) e cole abaixo. Aceita colunas em português ou inglês.';

  @override
  String get legalEntitiesImportResult => 'Importação concluída';

  @override
  String get dashboardFilterLegalEntity => 'CNPJ';

  @override
  String get dashboardFilterUnit => 'Unidade';

  @override
  String get dashboardFilterSector => 'Setor';

  @override
  String get dashboardFilterAll => 'Todos';

  @override
  String get dashboardFilterClear => 'Limpar filtros';

  @override
  String get legalEntityTransferTitle => 'Transferir vínculo jurídico';

  @override
  String get legalEntityTransferHint =>
      'O CNPJ é o vínculo do contrato de trabalho e não muda em transferência de unidade. Esta alteração é auditada e exige justificativa.';

  @override
  String get legalEntityTransferReason => 'Justificativa';

  @override
  String get legalEntityTransferTarget => 'Novo CNPJ';

  @override
  String get legalEntityTransferAction => 'Transferir';

  @override
  String get legalEntityTransferHistory => 'Histórico de vínculo';

  @override
  String get unitTransferTitle => 'Transferir de unidade';

  @override
  String get unitTransferHint =>
      'Movimentação de unidade operacional — temporária ou definitiva. Gera vínculo auditável e não altera o CNPJ do colaborador.';

  @override
  String get unitTransferTarget => 'Unidade destino';

  @override
  String get unitTransferType => 'Tipo de movimentação';

  @override
  String get unitTransferTypeTemporary => 'Temporária';

  @override
  String get unitTransferTypeDefinitive => 'Definitiva';

  @override
  String get unitTransferStartDate => 'Data início';

  @override
  String get unitTransferEndDate => 'Data fim (opcional)';

  @override
  String get unitTransferNotes => 'Observação (opcional)';

  @override
  String get unitTransferAction => 'Transferir';

  @override
  String get myCompanyStockScope => 'Consolidar saldos de estoque por';

  @override
  String get myCompanyStockScopeHint =>
      'Esta configuração altera apenas a visualização consolidada dos saldos. Entradas, reservas, saídas, entregas e demais movimentações permanecem vinculadas ao estoque de cada unidade.';

  @override
  String get myCompanyStockScopeUnit => 'Unidade';

  @override
  String get myCompanyStockScopeLegalEntity => 'CNPJ';

  @override
  String get myCompanyStockScopeCompany => 'Empresa';

  @override
  String get navLegalEntities => 'CNPJs';

  @override
  String get unitLegalEntityLabel => 'CNPJ responsável';

  @override
  String get unitLegalEntityHint =>
      'Pessoa jurídica que responde pelas operações e pelo estoque desta unidade.';

  @override
  String get employeeEmploymentTypeLabel => 'Tipo de Vínculo';

  @override
  String get employeeSourceCompanyLabel => 'Empresa de Origem';

  @override
  String get employeeSourceCompanyHint =>
      'Nome da empresa de origem do colaborador';

  @override
  String get employmentTypeClt => 'CLT';

  @override
  String get employmentTypeOutsourced => 'Terceirizado';

  @override
  String get employmentTypeTemporary => 'Temporário';

  @override
  String get employmentTypeServiceProvider => 'Prestador de Serviço';

  @override
  String get employmentTypeApprentice => 'Menor Aprendiz';

  @override
  String get employmentTypeTrainee => 'Praticante';

  @override
  String get employmentTypeIntern => 'Estagiário';

  @override
  String get navTerceirizados => 'Terceirizados e Prestadores';

  @override
  String get outsourcedCompaniesTitle => 'Terceirizados e Prestadores';

  @override
  String get outsourcedCompaniesEmpty =>
      'Nenhuma empresa terceirizada cadastrada.';

  @override
  String get outsourcedCompaniesSearchHint => 'Buscar por nome ou CNPJ';

  @override
  String get outsourcedCompanyNew => 'Nova empresa';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Razão Social';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Nome Fantasia';

  @override
  String get outsourcedCompanyCnpjLabel => 'CNPJ';

  @override
  String get outsourcedCompanyCnpjHint => 'Opcional no Cadastro Simplificado';

  @override
  String get outsourcedCompanyKindLabel => 'Tipo da Empresa';

  @override
  String get outsourcedCompanyKindOutsourced => 'Terceirizada';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Prestadora de Serviço';

  @override
  String get outsourcedCompanyKindOther => 'Outro';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'Responsabilidade pelo Fornecimento de EPI';

  @override
  String get outsourcedCompanyUnitLabel => 'Unidade';

  @override
  String get outsourcedCompanyUnitAll => 'Todas as unidades (padrão)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidade';

  @override
  String get outsourcedCompanyLinkHint =>
      'Buscar empresa já cadastrada no tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Já vinculadas a esta Unidade';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponíveis para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidade';

  @override
  String get outsourcedCompanyLinkActivate => 'Reativar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motivo do arquivamento (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidade(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidade de origem';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Nenhuma empresa encontrada com esse termo.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Vínculo não informado para o seu perfil';

  @override
  String get outsourcedCompanyStatusLabel => 'Situação';

  @override
  String get outsourcedCompanySave => 'Salvar';

  @override
  String get outsourcedCompanyCancel => 'Cancelar';

  @override
  String get outsourcedCompanyPromote => 'Promover a Cadastro Padrão';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Promover ao Cadastro Padrão?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplificado';

  @override
  String get outsourcedCompanyStandardBadge => 'Padrão';

  @override
  String get outsourcedTabCompanies => 'Empresas';

  @override
  String get outsourcedTabEmployees => 'Cadastro de Colaboradores';

  @override
  String get outsourcedTabReports => 'Relatórios';

  @override
  String get outsourcedShowActive => 'Ver ativos';

  @override
  String get outsourcedShowArchived => 'Ver arquivados';

  @override
  String get archive => 'Arquivar';

  @override
  String get restore => 'Desarquivar';

  @override
  String get archivedAt => 'Arquivado em';

  @override
  String get archiveReasonLabel => 'Motivo do arquivamento (auditoria)';

  @override
  String get outsourcedCompanyArchive => 'Arquivar empresa';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => 'Arquivar esta empresa?';

  @override
  String get outsourcedCompanyRestore => 'Desarquivar';

  @override
  String get outsourcedCompanyRestoreConfirmTitle =>
      'Desarquivar esta empresa?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'Nenhuma empresa terceirizada arquivada.';

  @override
  String get outsourcedEmployeeNew => 'Novo colaborador';

  @override
  String get outsourcedEmployeesEmpty =>
      'Nenhum colaborador terceirizado/prestador cadastrado.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'Nenhum colaborador terceirizado/prestador arquivado.';

  @override
  String get outsourcedEmployeeCompanyLabel =>
      'Empresa terceirizada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Matrícula da empresa de origem';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Crachá';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observações';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      'Arquivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      'Desarquivar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular à minha unidade';

  @override
  String get employeeUnitLinkActivate => 'Reativar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motivo do arquivamento (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Arquivado nesta Unidade';

  @override
  String get employeeUnitLinkAbsent => 'Não vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidade';

  @override
  String get employeeUnitLinksEmpty =>
      'Este colaborador não tem vínculo com nenhuma Unidade que você pode consultar.';

  @override
  String get employeeUnitLinksError => 'Não foi possível carregar os vínculos.';

  @override
  String get outsourcedReportsError => 'Não foi possível carregar o relatório.';

  @override
  String get outsourcedReportsEmpty =>
      'Nenhuma empresa terceirizada/prestadora cadastrada.';

  @override
  String get outsourcedReportsActive => 'Ativos';

  @override
  String get outsourcedReportsArchived => 'Arquivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidade por Módulo';

  @override
  String get moduleVisibilityDescription =>
      'Permissões padrão: cada perfil possui permissões padrão definidas pelo sistema. Personalizações: o Administrador Geral pode personalizar a visualização e a utilização dos módulos por perfil e por unidade, sem alterar a estrutura padrão do sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Permissões padrão deste perfil';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Estas permissões representam o comportamento padrão do sistema. As configurações abaixo permitem apenas personalizações realizadas pelo Administrador Geral.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Nenhum módulo por padrão';

  @override
  String get moduleVisibilityUnitLabel => 'Unidade';

  @override
  String get moduleVisibilityUnitHint =>
      'Um módulo não marcado especificamente para esta Unidade herda o valor de \"Todas as unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Todas as unidades (padrão)';

  @override
  String get stockTabAvailable => 'Disponíveis';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi =>
      'Selecione um EPI para ver os itens disponíveis';

  @override
  String get stockAvailableEmpty =>
      'Nenhum item disponível para este EPI nesta unidade';

  @override
  String get stockBlockedEmpty => 'Nenhum item bloqueado';

  @override
  String get stockNoOperationalUnit =>
      'Seu perfil não tem unidade operacional ativa. Fale com o administrador para liberar o acesso ao estoque.';

  @override
  String get stockItemLotLabel => 'Lote';

  @override
  String get stockStatusBlockedExpired => 'Vencido';

  @override
  String get stockStatusBlockedDiscard => 'Aguardando descarte';

  @override
  String get stockStatusBlockedReturn => 'Aguardando devolução ao fornecedor';

  @override
  String get stockStatusBlockedAnalysis => 'Em análise';

  @override
  String get stockStatusBlockedRejected => 'Reprovado';

  @override
  String get stockStatusBlockedArchived => 'EPI arquivado';

  @override
  String get stockStatusUnknown => 'Status não reconhecido';

  @override
  String get stockUnitBalanceSuffix => 'na unidade';

  @override
  String get stockCompanyBalanceLabel => 'empresa';

  @override
  String get stockMinimumShort => 'mín';

  @override
  String get deliveryStepItem => 'Item';

  @override
  String get deliveryItemTitle => 'Selecione a unidade etiquetada';

  @override
  String get deliveryItemEmpty => 'Nenhum item disponível nesta Unidade.';

  @override
  String get deliveryItemScan => 'Ler QR do item';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Estoque na Unidade: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Colaborador sem Unidade operacional: não é possível registrar entrega.';

  @override
  String get deliveryQrOtherEpi => 'O código lido pertence a outro EPI.';

  @override
  String get stockUnitRequiredToMove =>
      'Selecione uma Unidade para movimentar o estoque.';

  @override
  String get stockAttentionSectionTitle => 'Estoque';

  @override
  String get stockAttentionCompanyTitle =>
      'Faixa de atenção — padrão da empresa';

  @override
  String get stockAttentionCompanyHelp =>
      'Aplica-se às Unidades que não definiram um percentual próprio. Não altera nenhuma Unidade já configurada.';

  @override
  String get stockAttentionPercentageLabel => 'Percentual da faixa de atenção';

  @override
  String get stockAttentionOriginLabel => 'Origem';

  @override
  String get stockAttentionOriginCompany => 'Configurado pela empresa';

  @override
  String get stockAttentionOriginSystem => 'Padrão do sistema';

  @override
  String get stockAttentionSave => 'Salvar padrão da empresa';

  @override
  String get stockAttentionRestore => 'Restaurar padrão do sistema';

  @override
  String get stockAttentionSaved => 'Padrão da empresa salvo.';

  @override
  String get stockAttentionRestored =>
      'Padrão da empresa removido. A empresa voltou ao padrão do sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Padrão do sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuração de estoque';

  @override
  String get stockConfigIntro =>
      'Defina estoque mínimo, faixa de atenção e monitoramento de alerta de um EPI em uma Unidade. Cada parâmetro é salvo separadamente.';

  @override
  String get stockConfigUnitLabel => 'Unidade a configurar';

  @override
  String get stockConfigSelectUnit =>
      'Selecione a Unidade para configurar os parâmetros.';

  @override
  String get stockConfigSelectEpi =>
      'Selecione o EPI para ver e editar os parâmetros desta Unidade.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'Não foi possível carregar os EPIs desta Unidade.';

  @override
  String get stockConfigNoEpisInUnit => 'Nenhum EPI visível nesta Unidade.';

  @override
  String get stockConfigUnitBalance => 'Saldo na Unidade';

  @override
  String get stockConfigAttentionLimit => 'Limite da faixa de atenção';

  @override
  String get stockConfigUnderlyingStatus => 'Condição física';

  @override
  String get stockConfigDerivedUnavailable =>
      'Os valores calculados não puderam ser atualizados agora. Os parâmetros salvos acima estão corretos.';

  @override
  String get stockConfigStatusCritical => 'Crítico';

  @override
  String get stockConfigStatusNearMinimum => 'Próximo do mínimo';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alerta desabilitado';

  @override
  String get stockConfigMinimumTitle => 'Estoque mínimo';

  @override
  String get stockConfigMinimumHelp =>
      'Quantidade abaixo da qual o EPI é considerado crítico nesta Unidade. Vale só para esta Unidade.';

  @override
  String get stockConfigMinimumLabel => 'Estoque mínimo';

  @override
  String get stockConfigMinimumNegativeError =>
      'Informe um número inteiro maior ou igual a zero.';

  @override
  String get stockConfigMinimumSaved =>
      'Estoque mínimo salvo para esta Unidade.';

  @override
  String get stockConfigMinimumRestored =>
      'Estoque mínimo restaurado. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAttentionTitle => 'Faixa de atenção';

  @override
  String get stockConfigAttentionHelp =>
      'Percentual acima do mínimo em que o EPI já entra em atenção nesta Unidade. Independente do estoque mínimo.';

  @override
  String get stockConfigAttentionRangeError =>
      'O percentual deve estar entre 0 e 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Faixa de atenção salva para esta Unidade.';

  @override
  String get stockConfigAttentionRestored =>
      'Faixa de atenção restaurada. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoramento de alerta';

  @override
  String get stockConfigAlertHelp =>
      'Desligar interrompe o alerta de estoque baixo e a reposição automática deste EPI nesta Unidade. Não altera saldo, mínimo nem percentual.';

  @override
  String get stockConfigAlertToggle => 'Monitorar o estoque deste EPI';

  @override
  String get stockConfigAlertPending =>
      'Alteração pendente. Clique em Salvar para aplicar.';

  @override
  String get stockConfigAlertDisableTitle => 'Desabilitar o alerta?';

  @override
  String get stockConfigAlertDisableBody =>
      'Este EPI deixará de gerar alerta de estoque baixo e reposição automática nesta Unidade. A condição física continuará sendo exibida.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desabilitar';

  @override
  String get stockConfigAlertSaved =>
      'Monitoramento de alerta salvo para esta Unidade.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoramento restaurado. A Unidade voltou ao padrão do sistema.';

  @override
  String get stockConfigOriginUnit => 'Configurado por esta Unidade';

  @override
  String get stockConfigOriginCompany => 'Herdado do padrão da empresa';

  @override
  String get stockConfigOriginUnknown => 'Não informada';

  @override
  String get stockConfigSave => 'Salvar';

  @override
  String get stockConfigRestore => 'Restaurar herança';

  @override
  String stockAttentionRangeError(int max) {
    return 'Informe um percentual inteiro entre 0 e $max.';
  }

  @override
  String get stockAttentionLoadError =>
      'Não foi possível carregar o padrão da empresa.';

  @override
  String get unitSelectorLabel => 'Unidade';

  @override
  String get unitSelectorAllUnits => 'Todas as Unidades';

  @override
  String get unitSelectorLockedHint => 'Seu perfil opera numa Unidade fixa.';

  @override
  String get unitSelectorLoadError => 'Não foi possível carregar as Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'Você não tem Unidade atribuída. Fale com o administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'A empresa ainda não tem Unidades cadastradas.';

  @override
  String get settingsSectionCompany => 'Empresa';

  @override
  String get settingsSectionOperation => 'Operação';

  @override
  String get settingsSectionSubscription => 'Assinatura';

  @override
  String get settingsCompanyLabel => 'Empresa';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Administrando a empresa: $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Selecione uma empresa em Configurações para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPI';

  @override
  String get settingsFichaTileSubtitle =>
      'Título, declaração, observações e rastreabilidade';

  @override
  String get settingsStockTileSubtitle => 'Faixa de atenção padrão da empresa';

  @override
  String get settingsModulesTileSubtitle =>
      'Módulos visíveis por perfil e por Unidade';

  @override
  String get settingsArchivalTitle => 'Arquivamento e retenção';

  @override
  String get settingsArchivalSubtitle =>
      'Anos de preservação dos registros arquivados';

  @override
  String get settingsAppearanceTitle => 'Aparência e idioma';

  @override
  String get settingsAppearanceSubtitle =>
      'Tema da interface e idioma do aplicativo';

  @override
  String get settingsSubscriptionTileTitle => 'Minha Assinatura';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Plano, cobranças e cancelamento';

  @override
  String get settingsInvoicesTileTitle => 'Histórico Financeiro';

  @override
  String get settingsInvoicesTileSubtitle => 'Todas as cobranças e recibos';

  @override
  String get settingsNoPermission =>
      'Você não tem permissão para alterar esta configuração.';

  @override
  String get stockPhysicalValidityUnknown => 'Validade física desconhecida';

  @override
  String get stockNoPhysicalStock => 'Sem estoque físico';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validade física';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifique a peça e informe a validade comprovada. A classificação é feita pelo sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR ou código da peça';

  @override
  String get stockRegularizeExpiryLabel => 'Validade física comprovada';

  @override
  String get stockRegularizeExpirySelect => 'Selecionar data';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidência (documento ou registro verificável)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificativa';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete =>
      'Preencha a peça, a validade, a evidência e a justificativa.';

  @override
  String get stockRegularizeResultEligible =>
      'Validade regularizada. A peça está apta para entrega e reserva.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validade regularizada. A peça está vencida e permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validade regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPIs distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Peças físicas: válidas $valid, próximas $expiring, vencidas $expired, desconhecidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Item indisponível para entrega. Verifique validade física, status, reservas e saldo.';

  @override
  String get safetyTitle => 'Biblioteca de Segurança';

  @override
  String get safetyApproved => 'EPIs Aprovados';

  @override
  String get safetyRetry => 'Tentar novamente';

  @override
  String get safetyClose => 'Fechar';

  @override
  String get safetyCancel => 'Cancelar';

  @override
  String get safetyConfirm => 'Confirmar';

  @override
  String get safetyAccess => 'Acessar';

  @override
  String get safetyPortalConfirm => 'Confirmar acesso ao portal';

  @override
  String get safetyCpfLast => 'Três últimos dígitos do CPF';

  @override
  String get safetyView => 'Visualizar';

  @override
  String get safetyFit => 'Ajustar';

  @override
  String get safetyZoomIn => 'Aumentar zoom';

  @override
  String get safetyZoomOut => 'Diminuir zoom';

  @override
  String get safetyNextPage => 'Próxima página';

  @override
  String get safetyPreviousPage => 'Página anterior';

  @override
  String get safetyDocument => 'Documento';

  @override
  String get safetyDetails => 'Detalhes';

  @override
  String get safetyRelatedDocuments => 'Documentos associados';

  @override
  String get safetyRelatedEpis => 'EPIs relacionados';

  @override
  String get safetyRelatedEpi => 'EPI relacionado';

  @override
  String get safetyAllEpis => 'Todos os EPIs';

  @override
  String get safetyAllCategories => 'Todas as categorias';

  @override
  String get safetyNoDocs => 'Nenhum documento publicado para este contexto.';

  @override
  String get safetyNoRecords =>
      'Nenhum registro publicado e autorizado neste contexto.';

  @override
  String get safetyCatalogueNotice =>
      'Aprovação cadastral; não indica disponibilidade física. Validade do CA não é validade de lote.';

  @override
  String get safetyName => 'EPI';

  @override
  String get safetyManufacturer => 'Fabricante';

  @override
  String get safetyModel => 'Modelo/referência';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Validade do CA';

  @override
  String get safetyUsefulLife => 'Vida útil (meses)';

  @override
  String get safetyProtection => 'Proteção';

  @override
  String get safetySection => 'Seção';

  @override
  String get safetyRecommendations => 'Recomendações/restrições';

  @override
  String get safetyUnknown => 'Não informado';

  @override
  String get safetySearch => 'Pesquisar';

  @override
  String get safetyViewEpi => 'Ver EPI';

  @override
  String get safetyHistory => 'Histórico';

  @override
  String get safetyDocumentHistory => 'Histórico documental';

  @override
  String get safetyPublish => 'Publicar';

  @override
  String get safetyPublishVersion => 'Publicar versão';

  @override
  String get safetyArchive => 'Arquivar documento';

  @override
  String get safetyArchiveVersions => 'Arquivar documento e versões';

  @override
  String get safetyReason => 'Justificativa obrigatória';

  @override
  String get safetyNew => 'Novo documento';

  @override
  String get safetyCreateNew => 'Criar novo documento';

  @override
  String get safetyMetadata => 'Metadados da versão';

  @override
  String get safetyEmptyAdmin => 'Nenhum documento cadastrado.';

  @override
  String get safetyPrivateNotice =>
      'Originais privados; versões e histórico preservados. Gestão restrita ao Administrador Geral e ao Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads =>
      'Permitir download de originais aos administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice =>
      'Colaboradores sempre consultam somente a pré-visualização.';

  @override
  String get safetyPolicyReason =>
      'Alterar política de download administrativo';

  @override
  String get safetySearchVersions => 'Pesquisar título ou versão';

  @override
  String get safetyChooseFile => 'Selecionar arquivo';

  @override
  String get safetyFilePickerLabel => 'Documentos de SST';

  @override
  String get safetyUnitRequired => 'Selecione ao menos uma unidade';

  @override
  String get safetyAllUnits => 'Todas as unidades da empresa';

  @override
  String get safetyRequired => 'Obrigatório';

  @override
  String get safetyDocumentTitle => 'Título';

  @override
  String get safetyVersion => 'Versão';

  @override
  String get safetyEffectiveDate => 'Vigência (AAAA-MM-DD)';

  @override
  String get safetySectors => 'Setores separados por vírgula (vazio = todos)';

  @override
  String get safetyActivities =>
      'Atividades/funções separadas por vírgula (vazio = todas)';

  @override
  String get safetyUpload => 'Cadastrar ou versionar documento';

  @override
  String get safetyRendering => 'Gerando pré-visualização segura…';

  @override
  String get safetyFileLimit => 'Selecione um arquivo de até 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versão $version · Vigência $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unidade de consulta: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Pré-visualização indisponível: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Cadastro recusado; pré-visualização indisponível: $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Versão $version / revisão $revision · $state · Vigência $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsável $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matriz de Aplicação de EPIs';

  @override
  String get safetyCategoryGlove => 'Matriz de Seleção de Luvas';

  @override
  String get safetyCategoryCare => 'Guias de Higienização e Conservação';

  @override
  String get safetyCategoryUse => 'Instruções de Uso dos EPIs';

  @override
  String get safetyCategoryTechnical => 'Manuais e Fichas Técnicas';

  @override
  String get safetyCategoryOther => 'Outros Documentos de SST';

  @override
  String get safetyStateDraft => 'Rascunho';

  @override
  String get safetyStatePublished => 'Publicado';

  @override
  String get safetyStateSuperseded => 'Substituído';

  @override
  String get safetyStateArchived => 'Arquivado';

  @override
  String get prConfTitle => 'Conferência de Recebimento';

  @override
  String get prConfIntro =>
      'Marque cada item conforme o recebimento real. Informe a validade física do fabricante e a evidência verificável; use \"Separar em lotes\" para validades diferentes ou exceções individuais. Peças sem validade comprovada entram BLOQUEADAS.';

  @override
  String get prConfReceivedYes => 'Recebido';

  @override
  String get prConfReceivedNo => 'Não recebido';

  @override
  String get prConfEvidence => 'Evidência verificável';

  @override
  String get prConfEvidenceHint => 'Etiqueta / NF / foto';

  @override
  String get prConfEvidenceRequired =>
      'Evidência verificável é obrigatória quando há validade.';

  @override
  String get prConfSplitLots => 'Separar em lotes';

  @override
  String get prConfSingleDate => 'Usar data única';

  @override
  String get prConfAddLot => 'Adicionar lote';

  @override
  String get prConfAddException => 'Exceção (1 peça)';

  @override
  String get prConfLotQty => 'Qtd';

  @override
  String get prConfLotCode => 'Identificação';

  @override
  String get prConfRemoveLot => 'Remover lote';

  @override
  String get prConfPreview => 'Prévia — validade física por peça';

  @override
  String get prConfBlocked => 'SEM validade → BLOQUEADAS';

  @override
  String get prConfExpired => 'vencida';

  @override
  String get prConfPiece => 'peça(s)';

  @override
  String get prConfSumMismatch =>
      'A soma das quantidades dos lotes não confere com a quantidade recebida.';

  @override
  String get prConfLotQtyPositive =>
      'Cada lote precisa de quantidade maior que zero.';

  @override
  String get prConfNotes => 'Observações sobre itens não recebidos';

  @override
  String get prConfNotesRequired =>
      'Informe as observações sobre os itens não recebidos.';

  @override
  String get prConfSubmit => 'Registrar Conferência';

  @override
  String get prConfDone => 'Conferência registrada.';

  @override
  String get prConfEmpty => 'Nenhum item elegível para conferência.';

  @override
  String get prConfInvalidQuantity =>
      'Quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';

  @override
  String get prConfNoPersistedPieces =>
      'Nenhuma peça efetivamente registrada ou resposta inconsistente. A entrada em estoque não foi confirmada.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count peças efetivamente registradas no estoque.';
  }

  @override
  String get prConfNoStockEntry =>
      'Conferência salva sem entrada de peças no estoque.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linha $line — $item (item #$id): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Estoque próximo do mínimo: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Saldo negativo: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Estoque zerado: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Estoque abaixo do mínimo: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Estoque no limite mínimo: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - saldo atual de $stock $measure, mínimo $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'CA próximo do vencimento: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - vence em $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Validade do fabricante vencida: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Validade do fabricante próxima: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - validade do fabricante venceu em $date. Retire do estoque ($stock $measure): EPI vencido não pode ser entregue ao trabalhador.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - validade do fabricante vence em $date (em $daysLabel). Priorize a entrega deste lote ($stock $measure em estoque) antes do vencimento (PEPS).';
  }

  @override
  String get operationalAlertSizes => 'Tamanhos em estoque:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Luva:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Tam:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Unif:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'S/Tam';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'unidades',
      one: 'unidade',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'pares',
      one: 'par',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel dias',
      one: '$countLabel dia',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertPhysicalDescription(
    num count,
    String countLabel,
    String epi,
  ) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$epi: $countLabel peças físicas.',
      one: '$epi: $countLabel peça física.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Validade física desconhecida';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Lotes próximos do vencimento';

  @override
  String get passwordChangeTitle => 'Defina uma nova senha';

  @override
  String get passwordChangeIntro =>
      'Sua senha é temporária. Por segurança, defina uma nova senha para continuar.';

  @override
  String get passwordChangeCurrent => 'Senha atual (temporária)';

  @override
  String get passwordChangeNew => 'Nova senha';

  @override
  String get passwordChangeConfirm => 'Confirmar nova senha';

  @override
  String get passwordChangeSave => 'Salvar nova senha';

  @override
  String get passwordChangeLogout => 'Sair';

  @override
  String get passwordChangeCurrentRequired => 'Informe a senha atual';

  @override
  String get passwordChangeMinLength =>
      'A nova senha deve ter ao menos 6 caracteres';

  @override
  String get passwordChangeMustDiffer =>
      'A nova senha deve ser diferente da temporária';

  @override
  String get passwordChangeMismatch => 'As senhas não coincidem';

  @override
  String get passwordChangeFailed => 'Erro ao trocar a senha';

  @override
  String get poSupplierConfirmed => 'Confirmado';

  @override
  String get poSupplierDeliveryUpdated => 'Entrega atualizada';

  @override
  String get poSupplierRejected => 'Recusado';

  @override
  String get poSupplierIsoDateHint => 'AAAA-MM-DD';

  @override
  String get billingActive => 'Ativa';

  @override
  String get billingPending => 'Pendente';

  @override
  String get billingPaused => 'Pausada';

  @override
  String get billingCancelled => 'Cancelada';

  @override
  String get billingExpired => 'Expirada';

  @override
  String get billingAnnual => 'Anual';

  @override
  String get billingMonthly => 'Mensal';

  @override
  String get billingRecurringCard => 'Cartão (recorrente)';

  @override
  String get billingCard => 'Cartão';

  @override
  String get billingBoleto => 'Boleto';

  @override
  String get billingConfirmTitle => 'Tem certeza?';

  @override
  String get billingConfirmBody =>
      'Seu acesso continuará disponível até o final do período já pago.\nNenhuma nova cobrança será realizada.';

  @override
  String get billingConfirmCancel => 'Confirmar Cancelamento';

  @override
  String get billingCancelledNotice => 'Assinatura cancelada.';

  @override
  String billingCancelFailed(String detail) {
    return 'Não foi possível cancelar: $detail';
  }

  @override
  String get billingAmount => 'Valor';

  @override
  String get billingCycle => 'Periodicidade';

  @override
  String get billingMethod => 'Forma de pagamento';

  @override
  String get billingStarted => 'Data da contratação';

  @override
  String get billingNextPayment => 'Próxima cobrança';

  @override
  String get billingLastPayment => 'Última cobrança';

  @override
  String get billingCancelDate => 'Cancelada em';

  @override
  String get billingManualRenewal => 'Renovação manual';

  @override
  String get billingMpSubscriptionId => 'ID da assinatura (MP)';

  @override
  String get billingMpStatus => 'Status Mercado Pago';

  @override
  String get billingTenant => 'Tenant';

  @override
  String get billingCancelAction => 'Cancelar assinatura';

  @override
  String get billingCancelledBody =>
      'Assinatura cancelada. O acesso permanece ativo até o final do período já pago; nenhuma nova cobrança será realizada.';

  @override
  String get billingEmptyTitle => 'Nenhuma assinatura ativa';

  @override
  String get billingEmptyBody =>
      'Quando uma assinatura for contratada, os detalhes aparecerão aqui.';

  @override
  String get billingLoadFailed => 'Não foi possível carregar a assinatura.';

  @override
  String get billingInvoicePaid => 'Pago';

  @override
  String get billingInvoicePending => 'Pendente';

  @override
  String get billingInvoiceCancelled => 'Cancelado';

  @override
  String get billingInvoiceRefunded => 'Reembolsado';

  @override
  String get billingInvoiceFailed => 'Falhou';

  @override
  String get billingOpenReceipt => 'Abrir recibo';

  @override
  String get billingReceiptOpenFailed => 'Não foi possível abrir o recibo.';

  @override
  String get billingHistoryLoadFailed =>
      'Não foi possível carregar o histórico.';

  @override
  String get billingInvoicesEmptyTitle => 'Nenhuma cobrança encontrada';

  @override
  String get billingInvoicesEmptyBody =>
      'As cobranças da sua assinatura aparecerão aqui.';

  @override
  String get feedbackTitle => 'Avaliações de EPIs';

  @override
  String get feedbackLoadFailed => 'Erro ao carregar avaliações';

  @override
  String get feedbackEmpty => 'Nenhuma avaliação encontrada';

  @override
  String get feedbackValidate => 'Validar';

  @override
  String get feedbackStatusOpen => 'Aberto';

  @override
  String get feedbackStatusResolved => 'Resolvido';

  @override
  String get feedbackStatusClosed => 'Fechado';

  @override
  String get feedbackStatusReceived => 'Recebido';

  @override
  String get feedbackStatusManagerReview => 'Em Análise pelo Gestor de EPI';

  @override
  String get feedbackStatusAwaitingHseq => 'Aguardando HSEQ';

  @override
  String get feedbackStatusHseqCompleted => 'Análise HSEQ Concluída';

  @override
  String get feedbackStatusForwardedAdmin => 'Encaminhado para Administração';

  @override
  String get feedbackStatusAwaitingAdmin =>
      'Aguardando Aprovação Administrativa';

  @override
  String get feedbackStatusCorrectiveAction => 'Ação Corretiva Aberta';

  @override
  String get feedbackStatusMoreInformation => 'Solicitada Mais Informação';

  @override
  String get feedbackStatusEnded => 'Encerrado';

  @override
  String get feedbackStatusNotApproved => 'Reprovado';

  @override
  String get qrInstruction => 'Aponte para um código QR ou de barras';

  @override
  String get qrDetected => 'Código detectado';

  @override
  String get qrScanAgain => 'Escanear novamente';

  @override
  String get qrTorchOn => 'Ligar lanterna';

  @override
  String get qrTorchOff => 'Desligar lanterna';

  @override
  String get formNameLabel => 'Nome';

  @override
  String get formCityLabel => 'Cidade';

  @override
  String get formSaveFailed => 'Erro ao salvar';

  @override
  String formExample(String value) {
    return 'Ex: $value';
  }

  @override
  String get userNewTitle => 'Novo usuário';

  @override
  String get userTemporaryPassword => 'Senha temporária';

  @override
  String get userPasswordHint => 'Digite ou use o botão para gerar';

  @override
  String get userCopyPassword => 'Copiar senha';

  @override
  String get userGeneratePassword => 'Gerar senha segura';

  @override
  String get userPasswordCopied =>
      'Senha copiada para a área de transferência.';

  @override
  String get userEmployeeIdRequired => 'ID do Colaborador (obrigatório)';

  @override
  String get userIdentityRequired => 'Preencha usuário e nome completo';

  @override
  String userDeleteNamed(String name) {
    return 'Excluir usuário \"$name\"?';
  }

  @override
  String get unitNewTitle => 'Nova unidade';

  @override
  String get unitFieldsRequired => 'Preencha nome, cidade e empresa';

  @override
  String get archivalLoadFailed =>
      'Não foi possível carregar a política de arquivamento.';

  @override
  String get archivalInvalidPeriods =>
      'Informe períodos válidos (mínimo 5 anos).';

  @override
  String get archivalSaved => 'Política de arquivamento salva com sucesso.';

  @override
  String get archivalSave => 'Salvar política de arquivamento';

  @override
  String get archivalYearsSuffix => 'anos';

  @override
  String get archivalPolicyIntro =>
      'Defina, conforme a política interna da empresa, por quantos anos os registros arquivados de cada item permanecem preservados antes de a exclusão definitiva ser habilitada (mínimo legal: 5 anos).';

  @override
  String get archivalPpeRecordRule =>
      'Ficha de EPI: retenção fixa de 5 anos (NR-6) — regra própria, não alterada por esta política.';

  @override
  String get roleMasterAdmin => 'Administrador Master';

  @override
  String get roleGeneralAdmin => 'Administrador Geral';

  @override
  String get roleRegistryAdmin => 'Administrador de Registro';

  @override
  String get roleLocalAdmin => 'Administrador Local';

  @override
  String get rolePpeManager => 'Gestor de EPI';

  @override
  String get roleEmployee => 'Funcionário';

  @override
  String get roleBuyer => 'Comprador';

  @override
  String get roleApprover => 'Aprovador';

  @override
  String get roleCertificationReadOnly => 'Certificação (somente leitura)';

  @override
  String get unitNameHint => 'Ex: Plataforma P-40';

  @override
  String get unitTypeBase => 'Base';

  @override
  String get unitTypeVessel => 'Embarcação';

  @override
  String get unitTypePlatform => 'Plataforma';

  @override
  String get employeeShowActive => 'Ver colaboradores ativos';

  @override
  String get employeeShowArchived => 'Ver colaboradores arquivados';

  @override
  String get employeeArchivedEmpty => 'Nenhum colaborador arquivado.';

  @override
  String get employeeArchiveTitle => 'Arquivar Colaborador';

  @override
  String get employeeRestoreTitle => 'Desarquivar Colaborador';

  @override
  String employeeArchiveBody(String name) {
    return 'O colaborador \"$name\" será arquivado e deixará de receber novas operações (entregas, requisições e movimentações).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos).';
  }

  @override
  String employeeRestoreBody(String name) {
    return 'O colaborador \"$name\" será desarquivado e voltará a ficar ativo, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String get epiShowActive => 'Ver EPIs ativos';

  @override
  String get epiShowArchived => 'Ver EPIs arquivados';

  @override
  String get epiArchivedEmpty => 'Nenhum EPI arquivado.';

  @override
  String get epiArchiveTitle => 'Arquivar EPI';

  @override
  String get epiRestoreTitle => 'Desarquivar EPI';

  @override
  String epiArchiveBody(String name) {
    return 'O EPI \"$name\" será arquivado e deixará de receber novas operações (entregas, estoque, requisições e compras).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos).';
  }

  @override
  String epiRestoreBody(String name) {
    return 'O EPI \"$name\" será desarquivado e voltará a ficar ativo, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String unitArchivedTitle(String title) {
    return '$title · Arquivadas';
  }

  @override
  String get unitShowActive => 'Ver unidades ativas';

  @override
  String get unitShowArchived => 'Ver unidades arquivadas';

  @override
  String get unitArchivedEmpty => 'Nenhuma unidade arquivada.';

  @override
  String get unitArchiveTitle => 'Arquivar Unidade';

  @override
  String get unitRestoreTitle => 'Desarquivar Unidade';

  @override
  String unitArchiveBody(String name) {
    return 'A unidade \"$name\" será arquivada e deixará de receber novas operações.\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos) para consultas, relatórios e auditorias.';
  }

  @override
  String unitRestoreBody(String name) {
    return 'A unidade \"$name\" será desarquivada e voltará a ficar ativa, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String archivedOnDate(String date) {
    return 'Arquivado em $date';
  }

  @override
  String retentionRemainingDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Retenção restante: $countLabel dias',
      one: 'Retenção restante: $countLabel dia',
    );
    return '$_temp0';
  }

  @override
  String get retentionSatisfied => 'Retenção cumprida';

  @override
  String get employeeDetailsSection => 'Dados do colaborador';

  @override
  String get epiDaysRemaining => 'Dias restantes';

  @override
  String get epiIdentificationSection => 'Identificação';

  @override
  String recordsPendingCount(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel pendentes',
      one: '$countLabel pendente',
    );
    return '$_temp0';
  }

  @override
  String stockPpeCount(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel EPIs',
      one: '$countLabel EPI',
    );
    return '$_temp0';
  }

  @override
  String get stockManufacturerExpiring => 'Validade do fabricante próxima';

  @override
  String get stockManufacturerExpired => 'Validade do fabricante vencida';

  @override
  String get stockManufacturerExpiredNote =>
      'Validade do fabricante vencida — retirar do estoque (não entregar).';

  @override
  String get stockManufacturerExpiringNote =>
      'Validade do fabricante próxima — priorizar entrega (PEPS).';

  @override
  String stockManufacturerExpiringInNote(String days) {
    return 'Validade do fabricante próxima (em $days) — priorizar entrega (PEPS).';
  }

  @override
  String get moduleVisibilityLoadError =>
      'Não foi possível carregar a visualização de módulos.';

  @override
  String get moduleRequests => 'Solicitações';

  @override
  String get moduleAdministration => 'Administração';

  @override
  String importRowError(String row, String detail) {
    return 'Linha $row: $detail';
  }

  @override
  String get responsibilityContracting => 'Empresa Contratante';

  @override
  String get responsibilityOutsourced => 'Empresa Terceirizada';

  @override
  String get responsibilityProvider => 'Empresa Prestadora de Serviço';

  @override
  String get responsibilityShared => 'Responsabilidade Compartilhada';

  @override
  String get responsibilityContract => 'Conforme Contrato';

  @override
  String get responsibilityUndefined => 'Não Definido';

  @override
  String get purchaseCreated => 'Requisição criada com sucesso';

  @override
  String get criticalStockTitle => 'Estoque Crítico';

  @override
  String criticalStockBody(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel EPIs abaixo do estoque mínimo',
      one: '$countLabel EPI abaixo do estoque mínimo',
    );
    return '$_temp0';
  }

  @override
  String get companyNewTitle => 'Nova empresa';

  @override
  String get companyCnpjLength => 'CNPJ deve ter 14 dígitos';

  @override
  String get companyUserLimit => 'Limite de usuários';

  @override
  String companyMinimumUsers(int count) {
    return 'Mínimo de $count para este plano';
  }

  @override
  String companyOwnerOptional(String role) {
    return 'Owner ($role) — opcional';
  }

  @override
  String companyOwnerInviteHint(String role) {
    return 'Se informado, o Owner recebe por e-mail o convite com a chave de primeiro acesso. A senha nunca é conhecida pelo $role.';
  }

  @override
  String get companyOwnerName => 'Nome do Owner';

  @override
  String get companyOwnerEmail => 'E-mail do Owner (envia o convite)';

  @override
  String get companyPlanIndividual => 'Individual (1 usuário)';

  @override
  String get companyPlanStart => 'Start (até 10)';

  @override
  String get companyPlanBusiness => 'Business (11 a 25)';

  @override
  String get companyPlanCorporate => 'Corporate (26 a 100)';

  @override
  String get formValidNumber => 'Informe um número válido';

  @override
  String get formValidEmail => 'E-mail inválido';

  @override
  String get moduleEmployeeRegistration => 'Cadastro de Colaboradores';

  @override
  String unitArchivedOnDate(String date) {
    return 'Arquivada em $date';
  }
}

/// The translations for Portuguese, as used in Brazil (`pt_BR`).
class AppLocalizationsPtBr extends AppLocalizationsPt {
  AppLocalizationsPtBr() : super('pt_BR');

  @override
  String get appName => 'EPI Controle';

  @override
  String get loading => 'Carregando...';

  @override
  String get save => 'Salvar';

  @override
  String get cancel => 'Cancelar';

  @override
  String get reportsExportPdf => 'Exportar PDF';

  @override
  String get feedbackForward => 'Encaminhar';

  @override
  String get feedbackReject => 'Rejeitar';

  @override
  String get feedbackApprove => 'Aprovar';

  @override
  String get feedbackJustification => 'Justificativa';

  @override
  String get feedbackRejectReason => 'Motivo da rejeição';

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
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Setor';

  @override
  String get employeeRoleLabel => 'Função';

  @override
  String get employeeUnitLabel => 'Unidade';

  @override
  String get employeeUnitLockedHint =>
      'Unidade definida pelo seu perfil de acesso.';

  @override
  String get employeeLegalEntityLabel => 'CNPJ';

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
  String get episSearchHint => 'Buscar por nome, CA brasileiro ou código';

  @override
  String get epiNameLabel => 'Nome do EPI';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA — Certificado de Aprovação';

  @override
  String get epiSectorLabel => 'Setor';

  @override
  String get epiSectionLabel => 'Seção do EPI';

  @override
  String get epiModelLabel => 'Modelo/referência';

  @override
  String get epiManufacturerLabel => 'Fabricante';

  @override
  String get epiSupplierLabel => 'Fornecedor';

  @override
  String get epiUnitMeasureLabel => 'Unidade de medida';

  @override
  String get epiValidityDateLabel => 'Data de validade';

  @override
  String get epiManufacturerValidityLabel => 'Validade (meses)';

  @override
  String get epiCaExpiryLabel => 'Validade do CA';

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
  String get purchaseOrdersTitle => 'Ordens de Compra';

  @override
  String get poApprove => 'Aprovar';

  @override
  String get poReceive => 'Receber';

  @override
  String get poQuantityReceived => 'Qtd. recebida';

  @override
  String get poReceiveNotes => 'Observação';

  @override
  String get poManufacturerValidity => 'Validade do fabricante';

  @override
  String get poManufacturerValidityHint => 'Informar data';

  @override
  String get poManufacturerValidityRequired =>
      'Informe a validade do fabricante de todos os EPIs recebidos.';

  @override
  String get poOcrDateNotFound =>
      'Não foi possível identificar a data. Tente novamente.';

  @override
  String get poOcrCameraFailed => 'Falha na leitura por câmera.';

  @override
  String get poPickDate => 'Selecionar data';

  @override
  String get poReadDateCamera => 'Ler data por câmera (OCR)';

  @override
  String get poCheck => 'Conferir';

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

  @override
  String get searchEmployeeHint => 'Buscar colaborador...';

  @override
  String get searchEpiHint => 'Buscar EPI...';

  @override
  String get fieldQuantity => 'Quantidade';

  @override
  String get filterAll => 'Todos';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Estoque: $qty';
  }

  @override
  String get deliveryDateLabel => 'Data da entrega';

  @override
  String get deliveryNextReplacement => 'Próxima substituição';

  @override
  String deliveryDateValue(String date) {
    return 'Data: $date';
  }

  @override
  String get returnSelectDelivery => 'Selecionar entrega para devolver';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Entregue em $date · Qtd: $qty';
  }

  @override
  String get returnConditionTitle => 'Condição do EPI';

  @override
  String get returnDestinationTitle => 'Destino';

  @override
  String get returnDestDiscard => 'Descarte';

  @override
  String get returnDestRepair => 'Manutenção';

  @override
  String get returnDestStock => 'Retornar ao estoque';

  @override
  String get returnSubmit => 'Registrar Devolução';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Entrega: $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Quantidade: $qty';
  }

  @override
  String get purchaseTitleLabel => 'Título da requisição';

  @override
  String get purchaseSelectUnit => 'Selecione uma unidade';

  @override
  String get purchaseItemsTitle => 'Itens da requisição';

  @override
  String get purchaseAddEpi => 'Adicionar EPI';

  @override
  String get purchaseNoItems => 'Nenhum item adicionado';

  @override
  String get purchaseCreate => 'Criar Requisição';

  @override
  String get purchaseAddAtLeastOne => 'Adicione pelo menos um item';

  @override
  String get purchaseQuantityColon => 'Quantidade:';

  @override
  String purchaseItemsCount(int count) {
    return '$count itens';
  }

  @override
  String get purchaseStatusAwaiting => 'Aguardando';

  @override
  String get purchaseStatusCorrection => 'Correção solicitada';

  @override
  String get purchaseStatusAwaitingReceipt => 'Aguardando recebimento';

  @override
  String get purchaseStatusCompleted => 'Concluído';

  @override
  String get purchaseStatusCancelled => 'Cancelado';

  @override
  String get suppliersTitle => 'Fornecedores';

  @override
  String get supplierNew => 'Novo fornecedor';

  @override
  String get supplierEdit => 'Editar fornecedor';

  @override
  String get supplierCnpjLabel => 'CNPJ';

  @override
  String get supplierPhoneLabel => 'Telefone';

  @override
  String get supplierPaymentTermsLabel => 'Condições de pagamento';

  @override
  String get supplierIntegrationLevelLabel => 'Nível de integração';

  @override
  String get supplierInactiveLabel => 'Inativo';

  @override
  String get supplierCatalogTitle => 'Catálogo do fornecedor';

  @override
  String get catalogNewProduct => 'Novo produto';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Descrição';

  @override
  String get catalogLastPriceLabel => 'Último preço';

  @override
  String get catalogLeadTimeLabel => 'Prazo (dias)';

  @override
  String get quotesTitle => 'Cotações';

  @override
  String get quotesNew => 'Nova cotação';

  @override
  String get quotesSelectSuppliers => 'Selecione os fornecedores';

  @override
  String get quoteSendEmail => 'Enviar por e-mail';

  @override
  String get quoteSendPortal => 'Enviar pelo portal';

  @override
  String get quoteAnswerAction => 'Registrar resposta';

  @override
  String get quoteSelectWinner => 'Selecionar vencedora';

  @override
  String get quoteComparisonTitle => 'Comparação de cotações';

  @override
  String get quoteFreightLabel => 'Frete';

  @override
  String get quoteUnitPriceLabel => 'Preço unitário';

  @override
  String get quoteDeclinedLabel => 'Recusado';

  @override
  String get quoteBestPriceLabel => 'Melhor preço';

  @override
  String get quoteBestLeadTimeLabel => 'Melhor prazo';

  @override
  String get quoteCreatePo => 'Gerar PO a partir da cotação vencedora?';

  @override
  String get poSupplierActionsTitle => 'Fornecedor e entrega';

  @override
  String get poSendToSupplier => 'Enviar ao fornecedor';

  @override
  String get poPortalLinkAction => 'Enviar link do portal';

  @override
  String get poRegisterConfirmation => 'Registrar confirmação';

  @override
  String get poTrackingTitle => 'Acompanhamento';

  @override
  String get poDeliveryForecastLabel => 'Previsão de entrega';

  @override
  String get poCarrierLabel => 'Transportadora';

  @override
  String get poTrackingCodeLabel => 'Código de rastreio';

  @override
  String get commentLabel => 'Comentário';

  @override
  String get actionSentSuccess => 'Enviado com sucesso';

  @override
  String get myCompanyTitle => 'Minha Empresa';

  @override
  String get myCompanySubtitle =>
      'Dados, identidade visual e domínio da sua empresa';

  @override
  String get myCompanySaved => 'Configurações da empresa salvas com sucesso.';

  @override
  String get myCompanyLoadError =>
      'Não foi possível carregar os dados da empresa.';

  @override
  String get myCompanyContractSection => 'Contrato (somente leitura)';

  @override
  String get myCompanyPlan => 'Plano';

  @override
  String get myCompanyUserLimit => 'Limite de usuários';

  @override
  String get myCompanyLicense => 'Licença';

  @override
  String get myCompanyRegistrationSection => 'Dados cadastrais';

  @override
  String get myCompanyName => 'Nome fantasia';

  @override
  String get myCompanyLegalName => 'Razão social';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'Inscrição estadual';

  @override
  String get myCompanyMunicipalRegistration => 'Inscrição municipal';

  @override
  String get myCompanyAddress => 'Endereço';

  @override
  String get myCompanyPhone => 'Telefone';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'E-mail institucional';

  @override
  String get myCompanyWebsite => 'Website';

  @override
  String get myCompanyIdentitySection => 'Identidade e tema';

  @override
  String get myCompanyDisplayName => 'Nome exibido no sistema';

  @override
  String get myCompanyInstitutionalMessage => 'Mensagem institucional';

  @override
  String get myCompanyPrimaryColor => 'Cor principal (hex)';

  @override
  String get myCompanySecondaryColor => 'Cor secundária (hex)';

  @override
  String get myCompanyPreferencesSection => 'Preferências';

  @override
  String get myCompanyTimezone => 'Fuso horário';

  @override
  String get myCompanySave => 'Salvar configurações da empresa';

  @override
  String get myCompanyDomainsSection => 'Domínios';

  @override
  String get myCompanyDomainField => 'Domínio';

  @override
  String get myCompanyDomainTypePlatform => 'Subdomínio da plataforma';

  @override
  String get myCompanyDomainTypeCustomSub => 'Subdomínio personalizado';

  @override
  String get myCompanyDomainTypeCustom => 'Domínio personalizado';

  @override
  String get myCompanyDomainAdd => 'Registrar domínio';

  @override
  String get myCompanyDomainVerify => 'Verificar';

  @override
  String get myCompanyDomainDelete => 'Remover';

  @override
  String get myCompanyDomainPending => 'Pendente';

  @override
  String get myCompanyDomainVerified => 'Verificado';

  @override
  String get myCompanyDomainFailed => 'Falhou';

  @override
  String get myCompanyDomainPrimary => 'Principal';

  @override
  String get myCompanyDomainCname => 'Aponte o CNAME para';

  @override
  String get myCompanyDomainTxt => 'Crie o registro TXT';

  @override
  String get myCompanyDomainToken => 'Valor do TXT';

  @override
  String get epiArchiveBlockTitle => 'Arquivar com bloqueio de saldo';

  @override
  String get epiArchiveBlockBody =>
      'Este EPI possui saldo disponível ou vínculos vivos. Ao confirmar, o saldo disponível será movido para Estoque Bloqueado (rastreável) e o EPI será arquivado.';

  @override
  String get epiArchiveBlockConfirm => 'Bloquear saldo e arquivar';

  @override
  String get epiArchiveReasonLabel => 'Motivo do arquivamento (auditoria)';

  @override
  String get epiArchiveReasonRequired => 'Informe o motivo para prosseguir.';

  @override
  String get epiArchiveBlockableLabel => 'Saldo a bloquear';

  @override
  String get epiArchiveLiveLinksTitle => 'Vínculos vivos';

  @override
  String get epiArchiveAvailable => 'Disponível';

  @override
  String get epiArchiveInTransit => 'Em trânsito';

  @override
  String get epiArchiveInPossession => 'Em posse';

  @override
  String get epiArchivePendingRequests => 'Requisições abertas';

  @override
  String get epiArchivePendingPurchase => 'Compras abertas';

  @override
  String get dashboardComplianceTitle => 'Conformidade de estoque';

  @override
  String get dashboardComplianceAllOk => 'Estoque em conformidade';

  @override
  String get complianceCaExpired => 'CA vencido';

  @override
  String get complianceCaExpiring => 'CA a vencer';

  @override
  String get complianceProductExpired => 'Produto vencido';

  @override
  String get complianceProductExpiring => 'Produto a vencer';

  @override
  String get complianceMissingManufacture => 'Sem fabricação';

  @override
  String get complianceMissingLot => 'Sem lote';

  @override
  String get complianceAdminBlocked => 'Bloqueado';

  @override
  String get handoverTitle => 'Conferência de entrega';

  @override
  String get handoverPrompt => 'Escaneie o QR da entrega ou informe o código.';

  @override
  String get handoverCodeLabel => 'Código da entrega';

  @override
  String get handoverLookupButton => 'Buscar entrega';

  @override
  String get handoverScanButton => 'Escanear QR';

  @override
  String get handoverConfirmButton => 'Confirmar recebimento';

  @override
  String get handoverConfirmedTitle => 'Recebimento confirmado';

  @override
  String get handoverAlreadyConfirmed => 'Esta entrega já foi confirmada.';

  @override
  String get handoverNotFound => 'Entrega não encontrada para este código.';

  @override
  String get handoverConfirmError =>
      'Não foi possível confirmar o recebimento.';

  @override
  String get handoverEmployeeLabel => 'Colaborador';

  @override
  String get handoverEpiLabel => 'EPI';

  @override
  String get handoverQuantityLabel => 'Quantidade';

  @override
  String get handoverSectorLabel => 'Setor';

  @override
  String get handoverRoleLabel => 'Função';

  @override
  String get handoverUnitLabel => 'Unidade';

  @override
  String get handoverDeliveryDateLabel => 'Data da entrega';

  @override
  String get handoverReceiverNameLabel => 'Nome de quem recebe (opcional)';

  @override
  String get handoverScanAgain => 'Nova conferência';

  @override
  String get legalEntitiesTitle => 'CNPJs';

  @override
  String get legalEntitiesNew => 'Novo CNPJ';

  @override
  String get legalEntityLegalNameLabel => 'Razão social';

  @override
  String get legalEntityTradeNameLabel => 'Nome fantasia';

  @override
  String get legalEntityTypeLabel => 'Tipo';

  @override
  String get legalEntityInactiveBadge => 'Inativo';

  @override
  String get legalEntityDeactivate => 'Inativar CNPJ';

  @override
  String get legalEntityDeactivateHint =>
      'O histórico jurídico é preservado. O CNPJ deixa de ser usado em novas operações.';

  @override
  String get legalEntityShowInactive => 'Mostrar inativos';

  @override
  String get legalEntitiesEmpty => 'Nenhum CNPJ cadastrado.';

  @override
  String get legalEntityMunicipalityLabel => 'Município';

  @override
  String get legalEntityCnpjLabel => 'CNPJ';

  @override
  String get legalEntityUfLabel => 'UF';

  @override
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRazão social\tNome fantasia\tTipo';

  @override
  String get legalEntitiesImport => 'Importar planilha';

  @override
  String get legalEntitiesImportHint =>
      'Copie as linhas da planilha (com a linha de cabeçalho) e cole abaixo. Aceita colunas em português ou inglês.';

  @override
  String get legalEntitiesImportResult => 'Importação concluída';

  @override
  String get dashboardFilterLegalEntity => 'CNPJ';

  @override
  String get dashboardFilterUnit => 'Unidade';

  @override
  String get dashboardFilterSector => 'Setor';

  @override
  String get dashboardFilterAll => 'Todos';

  @override
  String get dashboardFilterClear => 'Limpar filtros';

  @override
  String get legalEntityTransferTitle => 'Transferir vínculo jurídico';

  @override
  String get legalEntityTransferHint =>
      'O CNPJ é o vínculo do contrato de trabalho e não muda em transferência de unidade. Esta alteração é auditada e exige justificativa.';

  @override
  String get legalEntityTransferReason => 'Justificativa';

  @override
  String get legalEntityTransferTarget => 'Novo CNPJ';

  @override
  String get legalEntityTransferAction => 'Transferir';

  @override
  String get legalEntityTransferHistory => 'Histórico de vínculo';

  @override
  String get unitTransferTitle => 'Transferir de unidade';

  @override
  String get unitTransferHint =>
      'Movimentação de unidade operacional — temporária ou definitiva. Gera vínculo auditável e não altera o CNPJ do colaborador.';

  @override
  String get unitTransferTarget => 'Unidade destino';

  @override
  String get unitTransferType => 'Tipo de movimentação';

  @override
  String get unitTransferTypeTemporary => 'Temporária';

  @override
  String get unitTransferTypeDefinitive => 'Definitiva';

  @override
  String get unitTransferStartDate => 'Data início';

  @override
  String get unitTransferEndDate => 'Data fim (opcional)';

  @override
  String get unitTransferNotes => 'Observação (opcional)';

  @override
  String get unitTransferAction => 'Transferir';

  @override
  String get myCompanyStockScope => 'Consolidar saldos de estoque por';

  @override
  String get myCompanyStockScopeHint =>
      'Esta configuração altera apenas a visualização consolidada dos saldos. Entradas, reservas, saídas, entregas e demais movimentações permanecem vinculadas ao estoque de cada unidade.';

  @override
  String get myCompanyStockScopeUnit => 'Unidade';

  @override
  String get myCompanyStockScopeLegalEntity => 'CNPJ';

  @override
  String get myCompanyStockScopeCompany => 'Empresa';

  @override
  String get navLegalEntities => 'CNPJs';

  @override
  String get unitLegalEntityLabel => 'CNPJ responsável';

  @override
  String get unitLegalEntityHint =>
      'Pessoa jurídica que responde pelas operações e pelo estoque desta unidade.';

  @override
  String get employeeEmploymentTypeLabel => 'Tipo de Vínculo';

  @override
  String get employeeSourceCompanyLabel => 'Empresa de Origem';

  @override
  String get employeeSourceCompanyHint =>
      'Nome da empresa de origem do colaborador';

  @override
  String get employmentTypeClt => 'CLT';

  @override
  String get employmentTypeOutsourced => 'Terceirizado';

  @override
  String get employmentTypeTemporary => 'Temporário';

  @override
  String get employmentTypeServiceProvider => 'Prestador de Serviço';

  @override
  String get employmentTypeApprentice => 'Menor Aprendiz';

  @override
  String get employmentTypeTrainee => 'Praticante';

  @override
  String get employmentTypeIntern => 'Estagiário';

  @override
  String get navTerceirizados => 'Terceirizados e Prestadores';

  @override
  String get outsourcedCompaniesTitle => 'Terceirizados e Prestadores';

  @override
  String get outsourcedCompaniesEmpty =>
      'Nenhuma empresa terceirizada cadastrada.';

  @override
  String get outsourcedCompaniesSearchHint => 'Buscar por nome ou CNPJ';

  @override
  String get outsourcedCompanyNew => 'Nova empresa';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Razão Social';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Nome Fantasia';

  @override
  String get outsourcedCompanyCnpjLabel => 'CNPJ';

  @override
  String get outsourcedCompanyCnpjHint => 'Opcional no Cadastro Simplificado';

  @override
  String get outsourcedCompanyKindLabel => 'Tipo da Empresa';

  @override
  String get outsourcedCompanyKindOutsourced => 'Terceirizada';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Prestadora de Serviço';

  @override
  String get outsourcedCompanyKindOther => 'Outro';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'Responsabilidade pelo Fornecimento de EPI';

  @override
  String get outsourcedCompanyUnitLabel => 'Unidade';

  @override
  String get outsourcedCompanyUnitAll => 'Todas as unidades (padrão)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidade';

  @override
  String get outsourcedCompanyLinkHint =>
      'Buscar empresa já cadastrada no tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Já vinculadas a esta Unidade';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponíveis para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidade';

  @override
  String get outsourcedCompanyLinkActivate => 'Reativar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motivo do arquivamento (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidade(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidade de origem';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Nenhuma empresa encontrada com esse termo.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Vínculo não informado para o seu perfil';

  @override
  String get outsourcedCompanyStatusLabel => 'Situação';

  @override
  String get outsourcedCompanySave => 'Salvar';

  @override
  String get outsourcedCompanyCancel => 'Cancelar';

  @override
  String get outsourcedCompanyPromote => 'Promover a Cadastro Padrão';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Promover ao Cadastro Padrão?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplificado';

  @override
  String get outsourcedCompanyStandardBadge => 'Padrão';

  @override
  String get outsourcedTabCompanies => 'Empresas';

  @override
  String get outsourcedTabEmployees => 'Cadastro de Colaboradores';

  @override
  String get outsourcedTabReports => 'Relatórios';

  @override
  String get outsourcedShowActive => 'Ver ativos';

  @override
  String get outsourcedShowArchived => 'Ver arquivados';

  @override
  String get archive => 'Arquivar';

  @override
  String get restore => 'Desarquivar';

  @override
  String get archivedAt => 'Arquivado em';

  @override
  String get archiveReasonLabel => 'Motivo do arquivamento (auditoria)';

  @override
  String get outsourcedCompanyArchive => 'Arquivar empresa';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => 'Arquivar esta empresa?';

  @override
  String get outsourcedCompanyRestore => 'Desarquivar';

  @override
  String get outsourcedCompanyRestoreConfirmTitle =>
      'Desarquivar esta empresa?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'Nenhuma empresa terceirizada arquivada.';

  @override
  String get outsourcedEmployeeNew => 'Novo colaborador';

  @override
  String get outsourcedEmployeesEmpty =>
      'Nenhum colaborador terceirizado/prestador cadastrado.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'Nenhum colaborador terceirizado/prestador arquivado.';

  @override
  String get outsourcedEmployeeCompanyLabel =>
      'Empresa terceirizada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Matrícula da empresa de origem';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Crachá';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observações';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      'Arquivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      'Desarquivar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular à minha unidade';

  @override
  String get employeeUnitLinkActivate => 'Reativar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motivo do arquivamento (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Arquivado nesta Unidade';

  @override
  String get employeeUnitLinkAbsent => 'Não vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidade';

  @override
  String get employeeUnitLinksEmpty =>
      'Este colaborador não tem vínculo com nenhuma Unidade que você pode consultar.';

  @override
  String get employeeUnitLinksError => 'Não foi possível carregar os vínculos.';

  @override
  String get outsourcedReportsError => 'Não foi possível carregar o relatório.';

  @override
  String get outsourcedReportsEmpty =>
      'Nenhuma empresa terceirizada/prestadora cadastrada.';

  @override
  String get outsourcedReportsActive => 'Ativos';

  @override
  String get outsourcedReportsArchived => 'Arquivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidade por Módulo';

  @override
  String get moduleVisibilityDescription =>
      'Permissões padrão: cada perfil possui permissões padrão definidas pelo sistema. Personalizações: o Administrador Geral pode personalizar a visualização e a utilização dos módulos por perfil e por unidade, sem alterar a estrutura padrão do sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Permissões padrão deste perfil';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Estas permissões representam o comportamento padrão do sistema. As configurações abaixo permitem apenas personalizações realizadas pelo Administrador Geral.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Nenhum módulo por padrão';

  @override
  String get moduleVisibilityUnitLabel => 'Unidade';

  @override
  String get moduleVisibilityUnitHint =>
      'Um módulo não marcado especificamente para esta Unidade herda o valor de \"Todas as unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Todas as unidades (padrão)';

  @override
  String get stockTabAvailable => 'Disponíveis';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi =>
      'Selecione um EPI para ver os itens disponíveis';

  @override
  String get stockAvailableEmpty =>
      'Nenhum item disponível para este EPI nesta unidade';

  @override
  String get stockBlockedEmpty => 'Nenhum item bloqueado';

  @override
  String get stockNoOperationalUnit =>
      'Seu perfil não tem unidade operacional ativa. Fale com o administrador para liberar o acesso ao estoque.';

  @override
  String get stockItemLotLabel => 'Lote';

  @override
  String get stockStatusBlockedExpired => 'Vencido';

  @override
  String get stockStatusBlockedDiscard => 'Aguardando descarte';

  @override
  String get stockStatusBlockedReturn => 'Aguardando devolução ao fornecedor';

  @override
  String get stockStatusBlockedAnalysis => 'Em análise';

  @override
  String get stockStatusBlockedRejected => 'Reprovado';

  @override
  String get stockStatusBlockedArchived => 'EPI arquivado';

  @override
  String get stockStatusUnknown => 'Status não reconhecido';

  @override
  String get stockUnitBalanceSuffix => 'na unidade';

  @override
  String get stockCompanyBalanceLabel => 'empresa';

  @override
  String get stockMinimumShort => 'mín';

  @override
  String get deliveryStepItem => 'Item';

  @override
  String get deliveryItemTitle => 'Selecione a unidade etiquetada';

  @override
  String get deliveryItemEmpty => 'Nenhum item disponível nesta Unidade.';

  @override
  String get deliveryItemScan => 'Ler QR do item';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Estoque na Unidade: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Colaborador sem Unidade operacional: não é possível registrar entrega.';

  @override
  String get deliveryQrOtherEpi => 'O código lido pertence a outro EPI.';

  @override
  String get stockUnitRequiredToMove =>
      'Selecione uma Unidade para movimentar o estoque.';

  @override
  String get stockAttentionSectionTitle => 'Estoque';

  @override
  String get stockAttentionCompanyTitle =>
      'Faixa de atenção — padrão da empresa';

  @override
  String get stockAttentionCompanyHelp =>
      'Aplica-se às Unidades que não definiram um percentual próprio. Não altera nenhuma Unidade já configurada.';

  @override
  String get stockAttentionPercentageLabel => 'Percentual da faixa de atenção';

  @override
  String get stockAttentionOriginLabel => 'Origem';

  @override
  String get stockAttentionOriginCompany => 'Configurado pela empresa';

  @override
  String get stockAttentionOriginSystem => 'Padrão do sistema';

  @override
  String get stockAttentionSave => 'Salvar padrão da empresa';

  @override
  String get stockAttentionRestore => 'Restaurar padrão do sistema';

  @override
  String get stockAttentionSaved => 'Padrão da empresa salvo.';

  @override
  String get stockAttentionRestored =>
      'Padrão da empresa removido. A empresa voltou ao padrão do sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Padrão do sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuração de estoque';

  @override
  String get stockConfigIntro =>
      'Defina estoque mínimo, faixa de atenção e monitoramento de alerta de um EPI em uma Unidade. Cada parâmetro é salvo separadamente.';

  @override
  String get stockConfigUnitLabel => 'Unidade a configurar';

  @override
  String get stockConfigSelectUnit =>
      'Selecione a Unidade para configurar os parâmetros.';

  @override
  String get stockConfigSelectEpi =>
      'Selecione o EPI para ver e editar os parâmetros desta Unidade.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'Não foi possível carregar os EPIs desta Unidade.';

  @override
  String get stockConfigNoEpisInUnit => 'Nenhum EPI visível nesta Unidade.';

  @override
  String get stockConfigUnitBalance => 'Saldo na Unidade';

  @override
  String get stockConfigAttentionLimit => 'Limite da faixa de atenção';

  @override
  String get stockConfigUnderlyingStatus => 'Condição física';

  @override
  String get stockConfigDerivedUnavailable =>
      'Os valores calculados não puderam ser atualizados agora. Os parâmetros salvos acima estão corretos.';

  @override
  String get stockConfigStatusCritical => 'Crítico';

  @override
  String get stockConfigStatusNearMinimum => 'Próximo do mínimo';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alerta desabilitado';

  @override
  String get stockConfigMinimumTitle => 'Estoque mínimo';

  @override
  String get stockConfigMinimumHelp =>
      'Quantidade abaixo da qual o EPI é considerado crítico nesta Unidade. Vale só para esta Unidade.';

  @override
  String get stockConfigMinimumLabel => 'Estoque mínimo';

  @override
  String get stockConfigMinimumNegativeError =>
      'Informe um número inteiro maior ou igual a zero.';

  @override
  String get stockConfigMinimumSaved =>
      'Estoque mínimo salvo para esta Unidade.';

  @override
  String get stockConfigMinimumRestored =>
      'Estoque mínimo restaurado. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAttentionTitle => 'Faixa de atenção';

  @override
  String get stockConfigAttentionHelp =>
      'Percentual acima do mínimo em que o EPI já entra em atenção nesta Unidade. Independente do estoque mínimo.';

  @override
  String get stockConfigAttentionRangeError =>
      'O percentual deve estar entre 0 e 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Faixa de atenção salva para esta Unidade.';

  @override
  String get stockConfigAttentionRestored =>
      'Faixa de atenção restaurada. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoramento de alerta';

  @override
  String get stockConfigAlertHelp =>
      'Desligar interrompe o alerta de estoque baixo e a reposição automática deste EPI nesta Unidade. Não altera saldo, mínimo nem percentual.';

  @override
  String get stockConfigAlertToggle => 'Monitorar o estoque deste EPI';

  @override
  String get stockConfigAlertPending =>
      'Alteração pendente. Clique em Salvar para aplicar.';

  @override
  String get stockConfigAlertDisableTitle => 'Desabilitar o alerta?';

  @override
  String get stockConfigAlertDisableBody =>
      'Este EPI deixará de gerar alerta de estoque baixo e reposição automática nesta Unidade. A condição física continuará sendo exibida.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desabilitar';

  @override
  String get stockConfigAlertSaved =>
      'Monitoramento de alerta salvo para esta Unidade.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoramento restaurado. A Unidade voltou ao padrão do sistema.';

  @override
  String get stockConfigOriginUnit => 'Configurado por esta Unidade';

  @override
  String get stockConfigOriginCompany => 'Herdado do padrão da empresa';

  @override
  String get stockConfigOriginUnknown => 'Não informada';

  @override
  String get stockConfigSave => 'Salvar';

  @override
  String get stockConfigRestore => 'Restaurar herança';

  @override
  String stockAttentionRangeError(int max) {
    return 'Informe um percentual inteiro entre 0 e $max.';
  }

  @override
  String get stockAttentionLoadError =>
      'Não foi possível carregar o padrão da empresa.';

  @override
  String get unitSelectorLabel => 'Unidade';

  @override
  String get unitSelectorAllUnits => 'Todas as Unidades';

  @override
  String get unitSelectorLockedHint => 'Seu perfil opera numa Unidade fixa.';

  @override
  String get unitSelectorLoadError => 'Não foi possível carregar as Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'Você não tem Unidade atribuída. Fale com o administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'A empresa ainda não tem Unidades cadastradas.';

  @override
  String get settingsSectionCompany => 'Empresa';

  @override
  String get settingsSectionOperation => 'Operação';

  @override
  String get settingsSectionSubscription => 'Assinatura';

  @override
  String get settingsCompanyLabel => 'Empresa';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Administrando a empresa: $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Selecione uma empresa em Configurações para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPI';

  @override
  String get settingsFichaTileSubtitle =>
      'Título, declaração, observações e rastreabilidade';

  @override
  String get settingsStockTileSubtitle => 'Faixa de atenção padrão da empresa';

  @override
  String get settingsModulesTileSubtitle =>
      'Módulos visíveis por perfil e por Unidade';

  @override
  String get settingsArchivalTitle => 'Arquivamento e retenção';

  @override
  String get settingsArchivalSubtitle =>
      'Anos de preservação dos registros arquivados';

  @override
  String get settingsAppearanceTitle => 'Aparência e idioma';

  @override
  String get settingsAppearanceSubtitle =>
      'Tema da interface e idioma do aplicativo';

  @override
  String get settingsSubscriptionTileTitle => 'Minha Assinatura';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Plano, cobranças e cancelamento';

  @override
  String get settingsInvoicesTileTitle => 'Histórico Financeiro';

  @override
  String get settingsInvoicesTileSubtitle => 'Todas as cobranças e recibos';

  @override
  String get settingsNoPermission =>
      'Você não tem permissão para alterar esta configuração.';

  @override
  String get stockPhysicalValidityUnknown => 'Validade física desconhecida';

  @override
  String get stockNoPhysicalStock => 'Sem estoque físico';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validade física';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifique a peça e informe a validade comprovada. A classificação é feita pelo sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR ou código da peça';

  @override
  String get stockRegularizeExpiryLabel => 'Validade física comprovada';

  @override
  String get stockRegularizeExpirySelect => 'Selecionar data';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidência (documento ou registro verificável)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificativa';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete =>
      'Preencha a peça, a validade, a evidência e a justificativa.';

  @override
  String get stockRegularizeResultEligible =>
      'Validade regularizada. A peça está apta para entrega e reserva.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validade regularizada. A peça está vencida e permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validade regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPIs distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Peças físicas: válidas $valid, próximas $expiring, vencidas $expired, desconhecidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Item indisponível para entrega. Verifique validade física, status, reservas e saldo.';

  @override
  String get safetyTitle => 'Biblioteca de Segurança';

  @override
  String get safetyApproved => 'EPIs Aprovados';

  @override
  String get safetyRetry => 'Tentar novamente';

  @override
  String get safetyClose => 'Fechar';

  @override
  String get safetyCancel => 'Cancelar';

  @override
  String get safetyConfirm => 'Confirmar';

  @override
  String get safetyAccess => 'Acessar';

  @override
  String get safetyPortalConfirm => 'Confirmar acesso ao portal';

  @override
  String get safetyCpfLast => 'Três últimos dígitos do CPF';

  @override
  String get safetyView => 'Visualizar';

  @override
  String get safetyFit => 'Ajustar';

  @override
  String get safetyZoomIn => 'Aumentar zoom';

  @override
  String get safetyZoomOut => 'Diminuir zoom';

  @override
  String get safetyNextPage => 'Próxima página';

  @override
  String get safetyPreviousPage => 'Página anterior';

  @override
  String get safetyDocument => 'Documento';

  @override
  String get safetyDetails => 'Detalhes';

  @override
  String get safetyRelatedDocuments => 'Documentos associados';

  @override
  String get safetyRelatedEpis => 'EPIs relacionados';

  @override
  String get safetyRelatedEpi => 'EPI relacionado';

  @override
  String get safetyAllEpis => 'Todos os EPIs';

  @override
  String get safetyAllCategories => 'Todas as categorias';

  @override
  String get safetyNoDocs => 'Nenhum documento publicado para este contexto.';

  @override
  String get safetyNoRecords =>
      'Nenhum registro publicado e autorizado neste contexto.';

  @override
  String get safetyCatalogueNotice =>
      'Aprovação cadastral; não indica disponibilidade física. Validade do CA não é validade de lote.';

  @override
  String get safetyName => 'EPI';

  @override
  String get safetyManufacturer => 'Fabricante';

  @override
  String get safetyModel => 'Modelo/referência';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Validade do CA';

  @override
  String get safetyUsefulLife => 'Vida útil (meses)';

  @override
  String get safetyProtection => 'Proteção';

  @override
  String get safetySection => 'Seção';

  @override
  String get safetyRecommendations => 'Recomendações/restrições';

  @override
  String get safetyUnknown => 'Não informado';

  @override
  String get safetySearch => 'Pesquisar';

  @override
  String get safetyViewEpi => 'Ver EPI';

  @override
  String get safetyHistory => 'Histórico';

  @override
  String get safetyDocumentHistory => 'Histórico documental';

  @override
  String get safetyPublish => 'Publicar';

  @override
  String get safetyPublishVersion => 'Publicar versão';

  @override
  String get safetyArchive => 'Arquivar documento';

  @override
  String get safetyArchiveVersions => 'Arquivar documento e versões';

  @override
  String get safetyReason => 'Justificativa obrigatória';

  @override
  String get safetyNew => 'Novo documento';

  @override
  String get safetyCreateNew => 'Criar novo documento';

  @override
  String get safetyMetadata => 'Metadados da versão';

  @override
  String get safetyEmptyAdmin => 'Nenhum documento cadastrado.';

  @override
  String get safetyPrivateNotice =>
      'Originais privados; versões e histórico preservados. Gestão restrita ao Administrador Geral e ao Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads =>
      'Permitir download de originais aos administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice =>
      'Colaboradores sempre consultam somente a pré-visualização.';

  @override
  String get safetyPolicyReason =>
      'Alterar política de download administrativo';

  @override
  String get safetySearchVersions => 'Pesquisar título ou versão';

  @override
  String get safetyChooseFile => 'Selecionar arquivo';

  @override
  String get safetyFilePickerLabel => 'Documentos de SST';

  @override
  String get safetyUnitRequired => 'Selecione ao menos uma unidade';

  @override
  String get safetyAllUnits => 'Todas as unidades da empresa';

  @override
  String get safetyRequired => 'Obrigatório';

  @override
  String get safetyDocumentTitle => 'Título';

  @override
  String get safetyVersion => 'Versão';

  @override
  String get safetyEffectiveDate => 'Vigência (AAAA-MM-DD)';

  @override
  String get safetySectors => 'Setores separados por vírgula (vazio = todos)';

  @override
  String get safetyActivities =>
      'Atividades/funções separadas por vírgula (vazio = todas)';

  @override
  String get safetyUpload => 'Cadastrar ou versionar documento';

  @override
  String get safetyRendering => 'Gerando pré-visualização segura…';

  @override
  String get safetyFileLimit => 'Selecione um arquivo de até 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versão $version · Vigência $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unidade de consulta: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Pré-visualização indisponível: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Cadastro recusado; pré-visualização indisponível: $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Versão $version / revisão $revision · $state · Vigência $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsável $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matriz de Aplicação de EPIs';

  @override
  String get safetyCategoryGlove => 'Matriz de Seleção de Luvas';

  @override
  String get safetyCategoryCare => 'Guias de Higienização e Conservação';

  @override
  String get safetyCategoryUse => 'Instruções de Uso dos EPIs';

  @override
  String get safetyCategoryTechnical => 'Manuais e Fichas Técnicas';

  @override
  String get safetyCategoryOther => 'Outros Documentos de SST';

  @override
  String get safetyStateDraft => 'Rascunho';

  @override
  String get safetyStatePublished => 'Publicado';

  @override
  String get safetyStateSuperseded => 'Substituído';

  @override
  String get safetyStateArchived => 'Arquivado';

  @override
  String get prConfTitle => 'Conferência de Recebimento';

  @override
  String get prConfIntro =>
      'Marque cada item conforme o recebimento real. Informe a validade física do fabricante e a evidência verificável; use \"Separar em lotes\" para validades diferentes ou exceções individuais. Peças sem validade comprovada entram BLOQUEADAS.';

  @override
  String get prConfReceivedYes => 'Recebido';

  @override
  String get prConfReceivedNo => 'Não recebido';

  @override
  String get prConfEvidence => 'Evidência verificável';

  @override
  String get prConfEvidenceHint => 'Etiqueta / NF / foto';

  @override
  String get prConfEvidenceRequired =>
      'Evidência verificável é obrigatória quando há validade.';

  @override
  String get prConfSplitLots => 'Separar em lotes';

  @override
  String get prConfSingleDate => 'Usar data única';

  @override
  String get prConfAddLot => 'Adicionar lote';

  @override
  String get prConfAddException => 'Exceção (1 peça)';

  @override
  String get prConfLotQty => 'Qtd';

  @override
  String get prConfLotCode => 'Identificação';

  @override
  String get prConfRemoveLot => 'Remover lote';

  @override
  String get prConfPreview => 'Prévia — validade física por peça';

  @override
  String get prConfBlocked => 'SEM validade → BLOQUEADAS';

  @override
  String get prConfExpired => 'vencida';

  @override
  String get prConfPiece => 'peça(s)';

  @override
  String get prConfSumMismatch =>
      'A soma das quantidades dos lotes não confere com a quantidade recebida.';

  @override
  String get prConfLotQtyPositive =>
      'Cada lote precisa de quantidade maior que zero.';

  @override
  String get prConfNotes => 'Observações sobre itens não recebidos';

  @override
  String get prConfNotesRequired =>
      'Informe as observações sobre os itens não recebidos.';

  @override
  String get prConfSubmit => 'Registrar Conferência';

  @override
  String get prConfDone => 'Conferência registrada.';

  @override
  String get prConfEmpty => 'Nenhum item elegível para conferência.';

  @override
  String get prConfInvalidQuantity =>
      'Quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';

  @override
  String get prConfNoPersistedPieces =>
      'Nenhuma peça efetivamente registrada ou resposta inconsistente. A entrada em estoque não foi confirmada.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count peças efetivamente registradas no estoque.';
  }

  @override
  String get prConfNoStockEntry =>
      'Conferência salva sem entrada de peças no estoque.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linha $line — $item (item #$id): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Estoque próximo do mínimo: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Saldo negativo: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Estoque zerado: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Estoque abaixo do mínimo: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Estoque no limite mínimo: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - saldo atual de $stock $measure, mínimo $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'CA próximo do vencimento: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - vence em $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Validade do fabricante vencida: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Validade do fabricante próxima: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - validade do fabricante venceu em $date. Retire do estoque ($stock $measure): EPI vencido não pode ser entregue ao trabalhador.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - validade do fabricante vence em $date (em $daysLabel). Priorize a entrega deste lote ($stock $measure em estoque) antes do vencimento (PEPS).';
  }

  @override
  String get operationalAlertSizes => 'Tamanhos em estoque:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Luva:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Tam:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Unif:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'S/Tam';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'unidades',
      one: 'unidade',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'pares',
      one: 'par',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel dias',
      one: '$countLabel dia',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertPhysicalDescription(
    num count,
    String countLabel,
    String epi,
  ) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$epi: $countLabel peças físicas.',
      one: '$epi: $countLabel peça física.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Validade física desconhecida';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Lotes próximos do vencimento';

  @override
  String get passwordChangeTitle => 'Defina uma nova senha';

  @override
  String get passwordChangeIntro =>
      'Sua senha é temporária. Por segurança, defina uma nova senha para continuar.';

  @override
  String get passwordChangeCurrent => 'Senha atual (temporária)';

  @override
  String get passwordChangeNew => 'Nova senha';

  @override
  String get passwordChangeConfirm => 'Confirmar nova senha';

  @override
  String get passwordChangeSave => 'Salvar nova senha';

  @override
  String get passwordChangeLogout => 'Sair';

  @override
  String get passwordChangeCurrentRequired => 'Informe a senha atual';

  @override
  String get passwordChangeMinLength =>
      'A nova senha deve ter ao menos 6 caracteres';

  @override
  String get passwordChangeMustDiffer =>
      'A nova senha deve ser diferente da temporária';

  @override
  String get passwordChangeMismatch => 'As senhas não coincidem';

  @override
  String get passwordChangeFailed => 'Erro ao trocar a senha';

  @override
  String get poSupplierConfirmed => 'Confirmado';

  @override
  String get poSupplierDeliveryUpdated => 'Entrega atualizada';

  @override
  String get poSupplierRejected => 'Recusado';

  @override
  String get poSupplierIsoDateHint => 'AAAA-MM-DD';

  @override
  String get billingActive => 'Ativa';

  @override
  String get billingPending => 'Pendente';

  @override
  String get billingPaused => 'Pausada';

  @override
  String get billingCancelled => 'Cancelada';

  @override
  String get billingExpired => 'Expirada';

  @override
  String get billingAnnual => 'Anual';

  @override
  String get billingMonthly => 'Mensal';

  @override
  String get billingRecurringCard => 'Cartão (recorrente)';

  @override
  String get billingCard => 'Cartão';

  @override
  String get billingBoleto => 'Boleto';

  @override
  String get billingConfirmTitle => 'Tem certeza?';

  @override
  String get billingConfirmBody =>
      'Seu acesso continuará disponível até o final do período já pago.\nNenhuma nova cobrança será realizada.';

  @override
  String get billingConfirmCancel => 'Confirmar Cancelamento';

  @override
  String get billingCancelledNotice => 'Assinatura cancelada.';

  @override
  String billingCancelFailed(String detail) {
    return 'Não foi possível cancelar: $detail';
  }

  @override
  String get billingAmount => 'Valor';

  @override
  String get billingCycle => 'Periodicidade';

  @override
  String get billingMethod => 'Forma de pagamento';

  @override
  String get billingStarted => 'Data da contratação';

  @override
  String get billingNextPayment => 'Próxima cobrança';

  @override
  String get billingLastPayment => 'Última cobrança';

  @override
  String get billingCancelDate => 'Cancelada em';

  @override
  String get billingManualRenewal => 'Renovação manual';

  @override
  String get billingMpSubscriptionId => 'ID da assinatura (MP)';

  @override
  String get billingMpStatus => 'Status Mercado Pago';

  @override
  String get billingTenant => 'Tenant';

  @override
  String get billingCancelAction => 'Cancelar assinatura';

  @override
  String get billingCancelledBody =>
      'Assinatura cancelada. O acesso permanece ativo até o final do período já pago; nenhuma nova cobrança será realizada.';

  @override
  String get billingEmptyTitle => 'Nenhuma assinatura ativa';

  @override
  String get billingEmptyBody =>
      'Quando uma assinatura for contratada, os detalhes aparecerão aqui.';

  @override
  String get billingLoadFailed => 'Não foi possível carregar a assinatura.';

  @override
  String get billingInvoicePaid => 'Pago';

  @override
  String get billingInvoicePending => 'Pendente';

  @override
  String get billingInvoiceCancelled => 'Cancelado';

  @override
  String get billingInvoiceRefunded => 'Reembolsado';

  @override
  String get billingInvoiceFailed => 'Falhou';

  @override
  String get billingOpenReceipt => 'Abrir recibo';

  @override
  String get billingReceiptOpenFailed => 'Não foi possível abrir o recibo.';

  @override
  String get billingHistoryLoadFailed =>
      'Não foi possível carregar o histórico.';

  @override
  String get billingInvoicesEmptyTitle => 'Nenhuma cobrança encontrada';

  @override
  String get billingInvoicesEmptyBody =>
      'As cobranças da sua assinatura aparecerão aqui.';

  @override
  String get feedbackTitle => 'Avaliações de EPIs';

  @override
  String get feedbackLoadFailed => 'Erro ao carregar avaliações';

  @override
  String get feedbackEmpty => 'Nenhuma avaliação encontrada';

  @override
  String get feedbackValidate => 'Validar';

  @override
  String get feedbackStatusOpen => 'Aberto';

  @override
  String get feedbackStatusResolved => 'Resolvido';

  @override
  String get feedbackStatusClosed => 'Fechado';

  @override
  String get feedbackStatusReceived => 'Recebido';

  @override
  String get feedbackStatusManagerReview => 'Em Análise pelo Gestor de EPI';

  @override
  String get feedbackStatusAwaitingHseq => 'Aguardando HSEQ';

  @override
  String get feedbackStatusHseqCompleted => 'Análise HSEQ Concluída';

  @override
  String get feedbackStatusForwardedAdmin => 'Encaminhado para Administração';

  @override
  String get feedbackStatusAwaitingAdmin =>
      'Aguardando Aprovação Administrativa';

  @override
  String get feedbackStatusCorrectiveAction => 'Ação Corretiva Aberta';

  @override
  String get feedbackStatusMoreInformation => 'Solicitada Mais Informação';

  @override
  String get feedbackStatusEnded => 'Encerrado';

  @override
  String get feedbackStatusNotApproved => 'Reprovado';

  @override
  String get qrInstruction => 'Aponte para um código QR ou de barras';

  @override
  String get qrDetected => 'Código detectado';

  @override
  String get qrScanAgain => 'Escanear novamente';

  @override
  String get qrTorchOn => 'Ligar lanterna';

  @override
  String get qrTorchOff => 'Desligar lanterna';

  @override
  String get formNameLabel => 'Nome';

  @override
  String get formCityLabel => 'Cidade';

  @override
  String get formSaveFailed => 'Erro ao salvar';

  @override
  String formExample(String value) {
    return 'Ex: $value';
  }

  @override
  String get userNewTitle => 'Novo usuário';

  @override
  String get userTemporaryPassword => 'Senha temporária';

  @override
  String get userPasswordHint => 'Digite ou use o botão para gerar';

  @override
  String get userCopyPassword => 'Copiar senha';

  @override
  String get userGeneratePassword => 'Gerar senha segura';

  @override
  String get userPasswordCopied =>
      'Senha copiada para a área de transferência.';

  @override
  String get userEmployeeIdRequired => 'ID do Colaborador (obrigatório)';

  @override
  String get userIdentityRequired => 'Preencha usuário e nome completo';

  @override
  String userDeleteNamed(String name) {
    return 'Excluir usuário \"$name\"?';
  }

  @override
  String get unitNewTitle => 'Nova unidade';

  @override
  String get unitFieldsRequired => 'Preencha nome, cidade e empresa';

  @override
  String get archivalLoadFailed =>
      'Não foi possível carregar a política de arquivamento.';

  @override
  String get archivalInvalidPeriods =>
      'Informe períodos válidos (mínimo 5 anos).';

  @override
  String get archivalSaved => 'Política de arquivamento salva com sucesso.';

  @override
  String get archivalSave => 'Salvar política de arquivamento';

  @override
  String get archivalYearsSuffix => 'anos';

  @override
  String get archivalPolicyIntro =>
      'Defina, conforme a política interna da empresa, por quantos anos os registros arquivados de cada item permanecem preservados antes de a exclusão definitiva ser habilitada (mínimo legal: 5 anos).';

  @override
  String get archivalPpeRecordRule =>
      'Ficha de EPI: retenção fixa de 5 anos (NR-6) — regra própria, não alterada por esta política.';

  @override
  String get roleMasterAdmin => 'Administrador Master';

  @override
  String get roleGeneralAdmin => 'Administrador Geral';

  @override
  String get roleRegistryAdmin => 'Administrador de Registro';

  @override
  String get roleLocalAdmin => 'Administrador Local';

  @override
  String get rolePpeManager => 'Gestor de EPI';

  @override
  String get roleEmployee => 'Funcionário';

  @override
  String get roleBuyer => 'Comprador';

  @override
  String get roleApprover => 'Aprovador';

  @override
  String get roleCertificationReadOnly => 'Certificação (somente leitura)';

  @override
  String get unitNameHint => 'Ex: Plataforma P-40';

  @override
  String get unitTypeBase => 'Base';

  @override
  String get unitTypeVessel => 'Embarcação';

  @override
  String get unitTypePlatform => 'Plataforma';

  @override
  String get employeeShowActive => 'Ver colaboradores ativos';

  @override
  String get employeeShowArchived => 'Ver colaboradores arquivados';

  @override
  String get employeeArchivedEmpty => 'Nenhum colaborador arquivado.';

  @override
  String get employeeArchiveTitle => 'Arquivar Colaborador';

  @override
  String get employeeRestoreTitle => 'Desarquivar Colaborador';

  @override
  String employeeArchiveBody(String name) {
    return 'O colaborador \"$name\" será arquivado e deixará de receber novas operações (entregas, requisições e movimentações).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos).';
  }

  @override
  String employeeRestoreBody(String name) {
    return 'O colaborador \"$name\" será desarquivado e voltará a ficar ativo, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String get epiShowActive => 'Ver EPIs ativos';

  @override
  String get epiShowArchived => 'Ver EPIs arquivados';

  @override
  String get epiArchivedEmpty => 'Nenhum EPI arquivado.';

  @override
  String get epiArchiveTitle => 'Arquivar EPI';

  @override
  String get epiRestoreTitle => 'Desarquivar EPI';

  @override
  String epiArchiveBody(String name) {
    return 'O EPI \"$name\" será arquivado e deixará de receber novas operações (entregas, estoque, requisições e compras).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos).';
  }

  @override
  String epiRestoreBody(String name) {
    return 'O EPI \"$name\" será desarquivado e voltará a ficar ativo, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String unitArchivedTitle(String title) {
    return '$title · Arquivadas';
  }

  @override
  String get unitShowActive => 'Ver unidades ativas';

  @override
  String get unitShowArchived => 'Ver unidades arquivadas';

  @override
  String get unitArchivedEmpty => 'Nenhuma unidade arquivada.';

  @override
  String get unitArchiveTitle => 'Arquivar Unidade';

  @override
  String get unitRestoreTitle => 'Desarquivar Unidade';

  @override
  String unitArchiveBody(String name) {
    return 'A unidade \"$name\" será arquivada e deixará de receber novas operações.\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos) para consultas, relatórios e auditorias.';
  }

  @override
  String unitRestoreBody(String name) {
    return 'A unidade \"$name\" será desarquivada e voltará a ficar ativa, podendo receber novas operações.\n\nTodo o histórico preservado permanece intacto.';
  }

  @override
  String archivedOnDate(String date) {
    return 'Arquivado em $date';
  }

  @override
  String retentionRemainingDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Retenção restante: $countLabel dias',
      one: 'Retenção restante: $countLabel dia',
    );
    return '$_temp0';
  }

  @override
  String get retentionSatisfied => 'Retenção cumprida';

  @override
  String get employeeDetailsSection => 'Dados do colaborador';

  @override
  String get epiDaysRemaining => 'Dias restantes';

  @override
  String get epiIdentificationSection => 'Identificação';

  @override
  String recordsPendingCount(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel pendentes',
      one: '$countLabel pendente',
    );
    return '$_temp0';
  }

  @override
  String stockPpeCount(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel EPIs',
      one: '$countLabel EPI',
    );
    return '$_temp0';
  }

  @override
  String get stockManufacturerExpiring => 'Validade do fabricante próxima';

  @override
  String get stockManufacturerExpired => 'Validade do fabricante vencida';

  @override
  String get stockManufacturerExpiredNote =>
      'Validade do fabricante vencida — retirar do estoque (não entregar).';

  @override
  String get stockManufacturerExpiringNote =>
      'Validade do fabricante próxima — priorizar entrega (PEPS).';

  @override
  String stockManufacturerExpiringInNote(String days) {
    return 'Validade do fabricante próxima (em $days) — priorizar entrega (PEPS).';
  }

  @override
  String get moduleVisibilityLoadError =>
      'Não foi possível carregar a visualização de módulos.';

  @override
  String get moduleRequests => 'Solicitações';

  @override
  String get moduleAdministration => 'Administração';

  @override
  String importRowError(String row, String detail) {
    return 'Linha $row: $detail';
  }

  @override
  String get responsibilityContracting => 'Empresa Contratante';

  @override
  String get responsibilityOutsourced => 'Empresa Terceirizada';

  @override
  String get responsibilityProvider => 'Empresa Prestadora de Serviço';

  @override
  String get responsibilityShared => 'Responsabilidade Compartilhada';

  @override
  String get responsibilityContract => 'Conforme Contrato';

  @override
  String get responsibilityUndefined => 'Não Definido';

  @override
  String get purchaseCreated => 'Requisição criada com sucesso';

  @override
  String get criticalStockTitle => 'Estoque Crítico';

  @override
  String criticalStockBody(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel EPIs abaixo do estoque mínimo',
      one: '$countLabel EPI abaixo do estoque mínimo',
    );
    return '$_temp0';
  }

  @override
  String get companyNewTitle => 'Nova empresa';

  @override
  String get companyCnpjLength => 'CNPJ deve ter 14 dígitos';

  @override
  String get companyUserLimit => 'Limite de usuários';

  @override
  String companyMinimumUsers(int count) {
    return 'Mínimo de $count para este plano';
  }

  @override
  String companyOwnerOptional(String role) {
    return 'Owner ($role) — opcional';
  }

  @override
  String companyOwnerInviteHint(String role) {
    return 'Se informado, o Owner recebe por e-mail o convite com a chave de primeiro acesso. A senha nunca é conhecida pelo $role.';
  }

  @override
  String get companyOwnerName => 'Nome do Owner';

  @override
  String get companyOwnerEmail => 'E-mail do Owner (envia o convite)';

  @override
  String get companyPlanIndividual => 'Individual (1 usuário)';

  @override
  String get companyPlanStart => 'Start (até 10)';

  @override
  String get companyPlanBusiness => 'Business (11 a 25)';

  @override
  String get companyPlanCorporate => 'Corporate (26 a 100)';

  @override
  String get formValidNumber => 'Informe um número válido';

  @override
  String get formValidEmail => 'E-mail inválido';

  @override
  String get moduleEmployeeRegistration => 'Cadastro de Colaboradores';

  @override
  String unitArchivedOnDate(String date) {
    return 'Arquivada em $date';
  }
}
