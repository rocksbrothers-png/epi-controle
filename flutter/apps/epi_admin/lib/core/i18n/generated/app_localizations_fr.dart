// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

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
  String get episSearchHint => 'Buscar por nome, CA ou código';

  @override
  String get epiNameLabel => 'Nome do EPI';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA';

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
}

/// The translations for French, as used in France (`fr_FR`).
class AppLocalizationsFrFr extends AppLocalizationsFr {
  AppLocalizationsFrFr() : super('fr_FR');

  @override
  String get appName => 'Contrôle EPI';

  @override
  String get loading => 'Chargement...';

  @override
  String get save => 'Enregistrer';

  @override
  String get cancel => 'Annuler';

  @override
  String get reportsExportPdf => 'Exporter PDF';

  @override
  String get feedbackForward => 'Transmettre';

  @override
  String get feedbackReject => 'Rejeter';

  @override
  String get feedbackApprove => 'Approuver';

  @override
  String get feedbackJustification => 'Justification';

  @override
  String get feedbackRejectReason => 'Motif du rejet';

  @override
  String get confirm => 'Confirmer';

  @override
  String get delete => 'Supprimer';

  @override
  String get edit => 'Modifier';

  @override
  String get add => 'Ajouter';

  @override
  String get search => 'Rechercher';

  @override
  String get filter => 'Filtrer';

  @override
  String get export => 'Exporter';

  @override
  String get print => 'Imprimer';

  @override
  String get close => 'Fermer';

  @override
  String get back => 'Retour';

  @override
  String get next => 'Suivant';

  @override
  String get previous => 'Précédent';

  @override
  String get finish => 'Terminer';

  @override
  String get retry => 'Réessayer';

  @override
  String get refresh => 'Actualiser';

  @override
  String get seeAll => 'Voir tout';

  @override
  String get noResults => 'Aucun résultat trouvé';

  @override
  String get required => 'Champ obligatoire';

  @override
  String get optional => 'Optionnel';

  @override
  String get navDashboard => 'Tableau de bord';

  @override
  String get navCompanies => 'Entreprises';

  @override
  String get navUsers => 'Utilisateurs';

  @override
  String get navUnits => 'Unités';

  @override
  String get navEmployees => 'Collaborateurs';

  @override
  String get navEpis => 'EPI';

  @override
  String get navStock => 'Stock';

  @override
  String get navDeliveries => 'Remises';

  @override
  String get navReturns => 'Retours';

  @override
  String get navRecords => 'Fiches';

  @override
  String get navPurchases => 'Achats';

  @override
  String get navReports => 'Rapports';

  @override
  String get navSettings => 'Paramètres';

  @override
  String get navPortal => 'Portail';

  @override
  String get navFeedback => 'Commentaires';

  @override
  String get loginTitle => 'Connexion';

  @override
  String get loginUsername => 'Nom d\'utilisateur';

  @override
  String get loginPassword => 'Mot de passe';

  @override
  String get loginUsernameHint => 'Entrez votre nom d\'utilisateur';

  @override
  String get loginPasswordHint => 'Entrez votre mot de passe';

  @override
  String get loginButton => 'Se connecter';

  @override
  String get loginForgotPassword => 'Mot de passe oublié';

  @override
  String get loginShowPassword => 'Afficher le mot de passe';

  @override
  String get loginHidePassword => 'Masquer le mot de passe';

  @override
  String get loginError => 'Identifiant ou mot de passe incorrect';

  @override
  String get loginErrorEmpty =>
      'Veuillez saisir le nom d\'utilisateur et le mot de passe';

  @override
  String get loginBiometric => 'Biométrie';

  @override
  String get dashboardTitle => 'Tableau de bord';

  @override
  String get dashboardDeliveriesToday => 'Remises aujourd\'hui';

  @override
  String get dashboardExpiringEpis => 'EPI expirant';

  @override
  String get dashboardCriticalStock => 'Stock critique';

  @override
  String get dashboardPendingPurchases => 'Achats en attente';

  @override
  String get dashboardQuickDelivery => 'Nouvelle remise';

  @override
  String get dashboardQuickReturn => 'Retour';

  @override
  String get dashboardQuickScan => 'Scanner QR';

  @override
  String get dashboardAlertsTitle => 'Alertes du jour';

  @override
  String get dashboardNoAlerts => 'Aucune alerte pour le moment';

  @override
  String get dashboardWeeklyChartTitle => 'Remises — 7 derniers jours';

  @override
  String get dayMon => 'Lun';

  @override
  String get dayTue => 'Mar';

  @override
  String get dayWed => 'Mer';

  @override
  String get dayThu => 'Jeu';

  @override
  String get dayFri => 'Ven';

  @override
  String get daySat => 'Sam';

  @override
  String get daySun => 'Dim';

  @override
  String get employeesTitle => 'Collaborateurs';

  @override
  String get employeesNew => 'Nouveau collaborateur';

  @override
  String get employeesSearchHint => 'Rechercher par nom, code ou département';

  @override
  String get employeeNameLabel => 'Nom complet';

  @override
  String get employeeCodeLabel => 'Matricule';

  @override
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Département';

  @override
  String get employeeRoleLabel => 'Poste';

  @override
  String get employeeUnitLabel => 'Unité';

  @override
  String get employeeLegalEntityLabel => 'CNPJ';

  @override
  String get employeeAdmissionLabel => 'Date d\'embauche';

  @override
  String get employeeScheduleLabel => 'Planning';

  @override
  String get employeeStatusActive => 'Actif';

  @override
  String get employeeStatusInactive => 'Inactif';

  @override
  String employeeDeleteConfirm(String name) {
    return 'Supprimer le collaborateur $name ?';
  }

  @override
  String get episTitle => 'EPI';

  @override
  String get episNew => 'Nouvel EPI';

  @override
  String get episSearchHint => 'Rechercher par nom, marquage CE ou code';

  @override
  String get epiNameLabel => 'Nom de l\'EPI';

  @override
  String get epiCodeLabel => 'Code d\'achat';

  @override
  String get epiCaLabel => 'N° CE';

  @override
  String get epiSectorLabel => 'Secteur';

  @override
  String get epiSectionLabel => 'Section EPI';

  @override
  String get epiModelLabel => 'Modèle/référence';

  @override
  String get epiManufacturerLabel => 'Fabricant';

  @override
  String get epiSupplierLabel => 'Fournisseur';

  @override
  String get epiUnitMeasureLabel => 'Unité de mesure';

  @override
  String get epiValidityDateLabel => 'Date de validité';

  @override
  String get epiManufacturerValidityLabel => 'Validité (mois)';

  @override
  String get epiCaExpiryLabel => 'Expiration marquage CE';

  @override
  String get epiValidityDaysLabel => 'Validité (jours)';

  @override
  String get epiStockLabel => 'Stock actuel';

  @override
  String get epiMinStockLabel => 'Stock minimum';

  @override
  String get epiStatusValid => 'Valide';

  @override
  String epiStatusExpiring(int days) {
    return 'Expire dans $days jours';
  }

  @override
  String get epiStatusExpired => 'Expiré';

  @override
  String get epiStatusNoStock => 'Rupture de stock';

  @override
  String get stockTitle => 'Stock';

  @override
  String get stockScan => 'Scanner QR';

  @override
  String get stockMoveIn => 'Entrée';

  @override
  String get stockMoveOut => 'Sortie';

  @override
  String get stockBatch => 'Opération groupée';

  @override
  String get stockMinimumAlert => 'Stock minimum atteint';

  @override
  String stockCriticalAlert(String name) {
    return 'Stock critique — $name';
  }

  @override
  String get deliveriesTitle => 'Remises';

  @override
  String get deliveryNew => 'Nouvelle remise';

  @override
  String get deliveryStep1 => 'Collaborateur';

  @override
  String get deliveryStep2 => 'EPI';

  @override
  String get deliveryStep3 => 'Révision';

  @override
  String get deliveryStep4 => 'Signature';

  @override
  String get deliveryConfirm => 'Confirmer la remise';

  @override
  String get deliverySuccess => 'Remise enregistrée avec succès';

  @override
  String get deliveryOfflineQueued =>
      'Remise sauvegardée — sera synchronisée à la reconnexion';

  @override
  String get deliverySignatureRequired => 'Signature obligatoire';

  @override
  String get deliveryClearSignature => 'Effacer la signature';

  @override
  String get returnsTitle => 'Retours';

  @override
  String get returnNew => 'Nouveau retour';

  @override
  String get returnStep1 => 'Sélectionner l\'EPI';

  @override
  String get returnStep2 => 'État';

  @override
  String get returnStep3 => 'Confirmer';

  @override
  String get returnConditionGood => 'Bon état';

  @override
  String get returnConditionDamaged => 'Endommagé';

  @override
  String get returnConditionLost => 'Perdu';

  @override
  String get returnSuccess => 'Retour enregistré avec succès.';

  @override
  String get returnOfflineQueued =>
      'Retour sauvegardé — sera synchronisé lors de la reconnexion.';

  @override
  String get recordsTitle => 'Fiches';

  @override
  String get recordsPreview => 'Aperçu de la fiche';

  @override
  String get recordsPrint => 'Imprimer la fiche';

  @override
  String get recordsSearchHint => 'Rechercher par employé, code ou unité…';

  @override
  String get recordsStatusComplete => 'Complet';

  @override
  String get recordsStatusPending => 'En attente';

  @override
  String get recordsStatusOverdue => 'En retard';

  @override
  String get purchasesTitle => 'Achats';

  @override
  String get purchaseOrdersTitle => 'Bons de commande';

  @override
  String get poApprove => 'Approuver';

  @override
  String get poReceive => 'Recevoir';

  @override
  String get poQuantityReceived => 'Qté reçue';

  @override
  String get poReceiveNotes => 'Remarque';

  @override
  String get poManufacturerValidity => 'Validité du fabricant';

  @override
  String get poManufacturerValidityHint => 'Indiquer la date';

  @override
  String get poManufacturerValidityRequired =>
      'Indiquez la validité du fabricant de tous les EPI reçus.';

  @override
  String get poOcrDateNotFound => 'Impossible de lire la date. Réessayez.';

  @override
  String get poOcrCameraFailed => 'Échec de la lecture par caméra.';

  @override
  String get poPickDate => 'Sélectionner une date';

  @override
  String get poReadDateCamera => 'Lire la date par caméra (OCR)';

  @override
  String get poCheck => 'Vérifier';

  @override
  String get purchasesNew => 'Nouvelle commande';

  @override
  String get purchaseStatusDraft => 'Brouillon';

  @override
  String get purchaseStatusSent => 'Envoyé';

  @override
  String get purchaseStatusPending => 'En attente d\'approbation';

  @override
  String get purchaseStatusApproved => 'Approuvé';

  @override
  String get purchaseStatusRejected => 'Rejeté';

  @override
  String get purchaseStatusOrdering => 'En commande';

  @override
  String get purchaseStatusReceived => 'Reçu';

  @override
  String get reportsTitle => 'Rapports';

  @override
  String get reportsGenerate => 'Générer un rapport';

  @override
  String get reportsPeriod => 'Période';

  @override
  String get reportsExport => 'Exporter';

  @override
  String get reportsSummaryTab => 'Résumé';

  @override
  String get reportsRequestsTab => 'Demandes';

  @override
  String get reportsTotalDeliveries => 'Total des remises';

  @override
  String get reportsTopEpis => 'Top EPI remis';

  @override
  String get reportsTopSectors => 'Remises par département';

  @override
  String get reportsRequestStatusPending => 'En attente';

  @override
  String get reportsRequestStatusProcessing => 'En traitement';

  @override
  String get reportsRequestStatusCompleted => 'Terminé';

  @override
  String get reportsRequestStatusFailed => 'Échoué';

  @override
  String get reportsAllUnits => 'Toutes les unités';

  @override
  String get reportsRequestDialogTitle => 'Demander un rapport';

  @override
  String get reportsRequestYear => 'Année';

  @override
  String get reportsRequestMonth => 'Mois';

  @override
  String get reportsRequestNotes => 'Remarques (optionnel)';

  @override
  String get reportsRequestSubmit => 'Demander';

  @override
  String get reportsNoRequests => 'Aucune demande';

  @override
  String get reportsNoData => 'Aucune donnée disponible';

  @override
  String get reportsRequestSuccess => 'Demande envoyée avec succès.';

  @override
  String get companiesTitle => 'Entreprises';

  @override
  String get companiesSearchHint => 'Rechercher par nom ou numéro fiscal';

  @override
  String get companyStatusActive => 'Actif';

  @override
  String get companyStatusInactive => 'Inactif';

  @override
  String get companyStatusSuspended => 'Suspendu';

  @override
  String get settingsTitle => 'Paramètres';

  @override
  String get settingsLanguage => 'Langue';

  @override
  String get settingsLanguageUser => 'Langue de l\'utilisateur';

  @override
  String get settingsLanguageCompany => 'Langue de l\'entreprise';

  @override
  String get settingsTheme => 'Thème';

  @override
  String get settingsThemeLight => 'Clair';

  @override
  String get settingsThemeDark => 'Sombre';

  @override
  String get settingsThemeSystem => 'Système';

  @override
  String get settingsAppSection => 'Application';

  @override
  String get settingsFichaSection => 'Fiche';

  @override
  String get settingsFichaTitle => 'Titre de la fiche';

  @override
  String get settingsFichaDeclaration => 'Déclaration';

  @override
  String get settingsFichaObservations => 'Observations';

  @override
  String get settingsFichaTracking => 'Traçabilité';

  @override
  String get settingsSaved => 'Paramètres enregistrés avec succès.';

  @override
  String get portalTitle => 'Portail collaborateur';

  @override
  String get portalScanQr => 'Scanner le QR Code';

  @override
  String get portalEnterCpf => 'Entrez votre identifiant';

  @override
  String get portalCpfHint => 'Ex : 000.000.000-00';

  @override
  String get portalCpfVerify => 'Accéder au portail';

  @override
  String get portalHistory => 'Mon historique EPI';

  @override
  String get portalSignature => 'Confirmer la signature';

  @override
  String get portalSignatureInstruction =>
      'Signez dans l\'espace ci-dessous pour confirmer la réception';

  @override
  String get portalDeliveries => 'Remises';

  @override
  String get portalFichas => 'Fiches';

  @override
  String get portalSignDelivery => 'Signer';

  @override
  String get portalSignAll => 'Tout signer';

  @override
  String get portalSigned => 'Signé';

  @override
  String get portalUnsigned => 'En attente';

  @override
  String get portalSignSuccess => 'Signature enregistrée avec succès.';

  @override
  String get portalNoDeliveries => 'Aucune remise trouvée';

  @override
  String get portalQty => 'Qté';

  @override
  String get errorGeneric => 'Une erreur est survenue. Veuillez réessayer.';

  @override
  String get errorNetwork => 'Pas de connexion internet';

  @override
  String get errorUnauthorized => 'Session expirée. Reconnectez-vous.';

  @override
  String get errorNotFound => 'Enregistrement non trouvé';

  @override
  String get errorServerError =>
      'Erreur serveur. Veuillez réessayer plus tard.';

  @override
  String get statusActive => 'Actif';

  @override
  String get statusInactive => 'Inactif';

  @override
  String get statusExpired => 'Expiré';

  @override
  String get statusExpiring => 'Expirant';

  @override
  String get statusPending => 'En attente';

  @override
  String get statusApproved => 'Approuvé';

  @override
  String get statusRejected => 'Rejeté';

  @override
  String get statusInReview => 'En cours d\'examen';

  @override
  String get confirmDeleteTitle => 'Confirmer la suppression';

  @override
  String get confirmDeleteMessage => 'Cette action ne peut pas être annulée.';

  @override
  String get confirmDeleteButton => 'Supprimer';

  @override
  String get employeeContactTitle => 'Contacter l\'employé';

  @override
  String get employeeContactWhatsapp => 'WhatsApp';

  @override
  String get employeeContactEmail => 'E-mail';

  @override
  String get employeeContactPdf => 'Télécharger PDF';

  @override
  String get employeeContactLaunching => 'Ouverture...';

  @override
  String get employeeContactPdfDownloading => 'Téléchargement du PDF...';

  @override
  String get employeeContactErrorNoApp =>
      'Aucune application disponible pour ouvrir ce lien';

  @override
  String get employeeContactErrorGeneric =>
      'Échec du contact. Veuillez réessayer.';

  @override
  String get employeeContactPdfError =>
      'Échec du téléchargement du PDF. Veuillez réessayer.';

  @override
  String get offlineBanner => 'Hors ligne — données sauvegardées localement';

  @override
  String get syncingBanner => 'Synchronisation en cours...';

  @override
  String get syncDone => 'Données synchronisées';

  @override
  String get searchEmployeeHint => 'Rechercher un employé...';

  @override
  String get searchEpiHint => 'Rechercher un EPI...';

  @override
  String get fieldQuantity => 'Quantité';

  @override
  String get filterAll => 'Tous';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Stock : $qty';
  }

  @override
  String get deliveryDateLabel => 'Date de remise';

  @override
  String get deliveryNextReplacement => 'Prochain remplacement';

  @override
  String deliveryDateValue(String date) {
    return 'Date : $date';
  }

  @override
  String get returnSelectDelivery => 'Sélectionner la remise à retourner';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Remis le $date · Qté : $qty';
  }

  @override
  String get returnConditionTitle => 'État de l\'EPI';

  @override
  String get returnDestinationTitle => 'Destination';

  @override
  String get returnDestDiscard => 'Mise au rebut';

  @override
  String get returnDestRepair => 'Maintenance';

  @override
  String get returnDestStock => 'Retour au stock';

  @override
  String get returnSubmit => 'Enregistrer le retour';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Remise : $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Quantité : $qty';
  }

  @override
  String get purchaseTitleLabel => 'Titre de la demande';

  @override
  String get purchaseSelectUnit => 'Sélectionnez une unité';

  @override
  String get purchaseItemsTitle => 'Articles de la demande';

  @override
  String get purchaseAddEpi => 'Ajouter un EPI';

  @override
  String get purchaseNoItems => 'Aucun article ajouté';

  @override
  String get purchaseCreate => 'Créer la demande';

  @override
  String get purchaseAddAtLeastOne => 'Ajoutez au moins un article';

  @override
  String get purchaseQuantityColon => 'Quantité :';

  @override
  String purchaseItemsCount(int count) {
    return '$count articles';
  }

  @override
  String get purchaseStatusAwaiting => 'En attente';

  @override
  String get purchaseStatusCorrection => 'Correction demandée';

  @override
  String get purchaseStatusAwaitingReceipt => 'En attente de réception';

  @override
  String get purchaseStatusCompleted => 'Terminé';

  @override
  String get purchaseStatusCancelled => 'Annulé';

  @override
  String get suppliersTitle => 'Fournisseurs';

  @override
  String get supplierNew => 'Nouveau fournisseur';

  @override
  String get supplierEdit => 'Modifier le fournisseur';

  @override
  String get supplierCnpjLabel => 'CNPJ (ID fiscal)';

  @override
  String get supplierPhoneLabel => 'Téléphone';

  @override
  String get supplierPaymentTermsLabel => 'Conditions de paiement';

  @override
  String get supplierIntegrationLevelLabel => 'Niveau d\'intégration';

  @override
  String get supplierInactiveLabel => 'Inactif';

  @override
  String get supplierCatalogTitle => 'Catalogue du fournisseur';

  @override
  String get catalogNewProduct => 'Nouveau produit';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Description';

  @override
  String get catalogLastPriceLabel => 'Dernier prix';

  @override
  String get catalogLeadTimeLabel => 'Délai (jours)';

  @override
  String get quotesTitle => 'Devis';

  @override
  String get quotesNew => 'Nouveau devis';

  @override
  String get quotesSelectSuppliers => 'Sélectionnez les fournisseurs';

  @override
  String get quoteSendEmail => 'Envoyer par e-mail';

  @override
  String get quoteSendPortal => 'Envoyer via le portail';

  @override
  String get quoteAnswerAction => 'Enregistrer la réponse';

  @override
  String get quoteSelectWinner => 'Sélectionner le gagnant';

  @override
  String get quoteComparisonTitle => 'Comparaison des devis';

  @override
  String get quoteFreightLabel => 'Fret';

  @override
  String get quoteUnitPriceLabel => 'Prix unitaire';

  @override
  String get quoteDeclinedLabel => 'Refusé';

  @override
  String get quoteBestPriceLabel => 'Meilleur prix';

  @override
  String get quoteBestLeadTimeLabel => 'Meilleur délai';

  @override
  String get quoteCreatePo => 'Créer un BC à partir du devis gagnant ?';

  @override
  String get poSupplierActionsTitle => 'Fournisseur et livraison';

  @override
  String get poSendToSupplier => 'Envoyer au fournisseur';

  @override
  String get poPortalLinkAction => 'Envoyer le lien du portail';

  @override
  String get poRegisterConfirmation => 'Enregistrer la confirmation';

  @override
  String get poTrackingTitle => 'Suivi';

  @override
  String get poDeliveryForecastLabel => 'Prévision de livraison';

  @override
  String get poCarrierLabel => 'Transporteur';

  @override
  String get poTrackingCodeLabel => 'Code de suivi';

  @override
  String get commentLabel => 'Commentaire';

  @override
  String get actionSentSuccess => 'Envoyé avec succès';

  @override
  String get myCompanyTitle => 'Mon Entreprise';

  @override
  String get myCompanySubtitle =>
      'Données, identité visuelle et domaine de votre entreprise';

  @override
  String get myCompanySaved =>
      'Paramètres de l\'entreprise enregistrés avec succès.';

  @override
  String get myCompanyLoadError =>
      'Impossible de charger les données de l\'entreprise.';

  @override
  String get myCompanyContractSection => 'Contrat (lecture seule)';

  @override
  String get myCompanyPlan => 'Forfait';

  @override
  String get myCompanyUserLimit => 'Limite d\'utilisateurs';

  @override
  String get myCompanyLicense => 'Licence';

  @override
  String get myCompanyRegistrationSection => 'Données d\'enregistrement';

  @override
  String get myCompanyName => 'Nom commercial';

  @override
  String get myCompanyLegalName => 'Raison sociale';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'Immatriculation d\'État';

  @override
  String get myCompanyMunicipalRegistration => 'Immatriculation municipale';

  @override
  String get myCompanyAddress => 'Adresse';

  @override
  String get myCompanyPhone => 'Téléphone';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'E-mail institutionnel';

  @override
  String get myCompanyWebsite => 'Site web';

  @override
  String get myCompanyIdentitySection => 'Identité et thème';

  @override
  String get myCompanyDisplayName => 'Nom affiché dans le système';

  @override
  String get myCompanyInstitutionalMessage => 'Message institutionnel';

  @override
  String get myCompanyPrimaryColor => 'Couleur principale (hex)';

  @override
  String get myCompanySecondaryColor => 'Couleur secondaire (hex)';

  @override
  String get myCompanyPreferencesSection => 'Préférences';

  @override
  String get myCompanyTimezone => 'Fuseau horaire';

  @override
  String get myCompanySave => 'Enregistrer les paramètres de l\'entreprise';

  @override
  String get myCompanyDomainsSection => 'Domaines';

  @override
  String get myCompanyDomainField => 'Domaine';

  @override
  String get myCompanyDomainTypePlatform => 'Sous-domaine de la plateforme';

  @override
  String get myCompanyDomainTypeCustomSub => 'Sous-domaine personnalisé';

  @override
  String get myCompanyDomainTypeCustom => 'Domaine personnalisé';

  @override
  String get myCompanyDomainAdd => 'Enregistrer le domaine';

  @override
  String get myCompanyDomainVerify => 'Vérifier';

  @override
  String get myCompanyDomainDelete => 'Supprimer';

  @override
  String get myCompanyDomainPending => 'En attente';

  @override
  String get myCompanyDomainVerified => 'Vérifié';

  @override
  String get myCompanyDomainFailed => 'Échec';

  @override
  String get myCompanyDomainPrimary => 'Principal';

  @override
  String get myCompanyDomainCname => 'Pointez le CNAME vers';

  @override
  String get myCompanyDomainTxt => 'Créez l\'enregistrement TXT';

  @override
  String get myCompanyDomainToken => 'Valeur du TXT';

  @override
  String get handoverScanAgain => 'Nouvelle remise';

  @override
  String get legalEntitiesTitle => 'CNPJ';

  @override
  String get legalEntitiesNew => 'Nouveau CNPJ';

  @override
  String get legalEntityLegalNameLabel => 'Raison sociale';

  @override
  String get legalEntityTradeNameLabel => 'Nom commercial';

  @override
  String get legalEntityTypeLabel => 'Type';

  @override
  String get legalEntityInactiveBadge => 'Inactif';

  @override
  String get legalEntityDeactivate => 'Désactiver le CNPJ';

  @override
  String get legalEntityDeactivateHint =>
      'L\'historique juridique est conservé. Le CNPJ n\'est plus utilisé dans les nouvelles opérations.';

  @override
  String get legalEntityShowInactive => 'Afficher les inactifs';

  @override
  String get legalEntitiesEmpty => 'Aucun CNPJ enregistré.';

  @override
  String get legalEntityMunicipalityLabel => 'Municipalité';

  @override
  String get legalEntitiesImport => 'Importer une feuille';

  @override
  String get legalEntitiesImportHint =>
      'Copiez les lignes de la feuille (avec l\'en-tête) et collez ci-dessous. Accepte les colonnes en portugais ou en anglais.';

  @override
  String get legalEntitiesImportResult => 'Importation terminée';

  @override
  String get dashboardFilterLegalEntity => 'CNPJ';

  @override
  String get dashboardFilterUnit => 'Unité';

  @override
  String get dashboardFilterSector => 'Secteur';

  @override
  String get dashboardFilterAll => 'Tous';

  @override
  String get dashboardFilterClear => 'Effacer les filtres';

  @override
  String get legalEntityTransferTitle => 'Transférer le lien juridique';

  @override
  String get legalEntityTransferHint =>
      'Le CNPJ est le lien du contrat de travail et ne change pas lors d\'un transfert d\'unité. Ce changement est audité et exige une justification.';

  @override
  String get legalEntityTransferReason => 'Justification';

  @override
  String get legalEntityTransferTarget => 'Nouveau CNPJ';

  @override
  String get legalEntityTransferAction => 'Transférer';

  @override
  String get legalEntityTransferHistory => 'Historique du lien';

  @override
  String get unitTransferTitle => 'Transférer d\'unité';

  @override
  String get unitTransferHint =>
      'Mouvement d\'unité opérationnelle — temporaire ou définitif. Crée un enregistrement auditable et ne modifie pas le CNPJ du collaborateur.';

  @override
  String get unitTransferTarget => 'Unité de destination';

  @override
  String get unitTransferType => 'Type de mouvement';

  @override
  String get unitTransferTypeTemporary => 'Temporaire';

  @override
  String get unitTransferTypeDefinitive => 'Définitif';

  @override
  String get unitTransferStartDate => 'Date de début';

  @override
  String get unitTransferEndDate => 'Date de fin (optionnelle)';

  @override
  String get unitTransferNotes => 'Observation (optionnelle)';

  @override
  String get unitTransferAction => 'Transférer';

  @override
  String get myCompanyStockScope => 'Consolider les soldes de stock par';

  @override
  String get myCompanyStockScopeHint =>
      'Ce paramètre ne modifie que la vue consolidée des soldes. Entrées, réservations, sorties, livraisons et autres mouvements restent rattachés au stock de chaque unité.';

  @override
  String get myCompanyStockScopeUnit => 'Unité';

  @override
  String get myCompanyStockScopeLegalEntity => 'CNPJ';

  @override
  String get myCompanyStockScopeCompany => 'Entreprise';

  @override
  String get navLegalEntities => 'CNPJ';

  @override
  String get unitLegalEntityLabel => 'CNPJ responsable';

  @override
  String get unitLegalEntityHint =>
      'Personne morale responsable des opérations et du stock de cette unité.';

  @override
  String get employeeEmploymentTypeLabel => 'Type de Contrat';

  @override
  String get employeeSourceCompanyLabel => 'Entreprise d\'Origine';

  @override
  String get employeeSourceCompanyHint =>
      'Nom de l\'entreprise d\'origine de l\'employé';

  @override
  String get employmentTypeClt => 'CLT';

  @override
  String get employmentTypeOutsourced => 'Externalisé';

  @override
  String get employmentTypeTemporary => 'Temporaire';

  @override
  String get employmentTypeServiceProvider => 'Prestataire de Services';

  @override
  String get employmentTypeApprentice => 'Apprenti Mineur';

  @override
  String get employmentTypeTrainee => 'Stagiaire (pratique)';

  @override
  String get employmentTypeIntern => 'Stagiaire (scolaire)';

  @override
  String get navTerceirizados => 'Sous-traitants et Prestataires';

  @override
  String get outsourcedCompaniesTitle => 'Sous-traitants et Prestataires';

  @override
  String get outsourcedCompaniesEmpty =>
      'Aucune entreprise sous-traitante enregistrée.';

  @override
  String get outsourcedCompaniesSearchHint => 'Rechercher par nom ou CNPJ';

  @override
  String get outsourcedCompanyNew => 'Nouvelle entreprise';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Raison Sociale';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Nom Commercial';

  @override
  String get outsourcedCompanyCnpjLabel => 'CNPJ';

  @override
  String get outsourcedCompanyCnpjHint =>
      'Facultatif dans l\'Enregistrement Simplifié';

  @override
  String get outsourcedCompanyKindLabel => 'Type d\'Entreprise';

  @override
  String get outsourcedCompanyKindOutsourced => 'Sous-traitante';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Prestataire de Service';

  @override
  String get outsourcedCompanyKindOther => 'Autre';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'Responsabilité de la Fourniture d\'EPI';

  @override
  String get outsourcedCompanyUnitLabel => 'Unité';

  @override
  String get outsourcedCompanyUnitAll => 'Toutes les unités (par défaut)';

  @override
  String get outsourcedCompanyStatusLabel => 'Statut';

  @override
  String get outsourcedCompanySave => 'Enregistrer';

  @override
  String get outsourcedCompanyCancel => 'Annuler';

  @override
  String get outsourcedCompanyPromote =>
      'Promouvoir à l\'Enregistrement Standard';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Promouvoir à l\'Enregistrement Standard ?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'L\'entreprise sera traitée comme un Enregistrement Standard. Un CNPJ est requis.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplifié';

  @override
  String get outsourcedCompanyStandardBadge => 'Standard';

  @override
  String get outsourcedTabCompanies => 'Entreprises';

  @override
  String get outsourcedTabEmployees => 'Inscription des Collaborateurs';

  @override
  String get outsourcedTabReports => 'Rapports';

  @override
  String get outsourcedShowActive => 'Voir actifs';

  @override
  String get outsourcedShowArchived => 'Voir archivés';

  @override
  String get archive => 'Archiver';

  @override
  String get restore => 'Restaurer';

  @override
  String get archivedAt => 'Archivé le';

  @override
  String get archiveReasonLabel => 'Motif de l\'archivage (audit)';

  @override
  String get outsourcedCompanyArchive => 'Archiver l\'entreprise';

  @override
  String get outsourcedCompanyArchiveConfirmTitle =>
      'Archiver cette entreprise ?';

  @override
  String get outsourcedCompanyRestore => 'Restaurer';

  @override
  String get outsourcedCompanyRestoreConfirmTitle =>
      'Restaurer cette entreprise ?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'Aucune entreprise sous-traitante archivée.';

  @override
  String get outsourcedEmployeeNew => 'Nouveau collaborateur';

  @override
  String get outsourcedEmployeesEmpty =>
      'Aucun collaborateur sous-traitant/prestataire enregistré.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'Aucun collaborateur sous-traitant/prestataire archivé.';

  @override
  String get outsourcedEmployeeCompanyLabel =>
      'Entreprise sous-traitante/prestataire';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Matricule de l\'entreprise d\'origine';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Badge';

  @override
  String get outsourcedEmployeeNotesLabel => 'Remarques';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      'Archiver ce collaborateur ?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      'Restaurer ce collaborateur ?';

  @override
  String get outsourcedReportsError => 'Impossible de charger le rapport.';

  @override
  String get outsourcedReportsEmpty =>
      'Aucune entreprise sous-traitante/prestataire enregistrée.';

  @override
  String get outsourcedReportsActive => 'Actifs';

  @override
  String get outsourcedReportsArchived => 'Archivés';

  @override
  String get moduleVisibilityTitle => 'Visibilité des Modules';

  @override
  String get moduleVisibilityDescription =>
      'Permissions par défaut : chaque profil possède des permissions par défaut définies par le système. Personnalisations : l\'Administrateur Général peut personnaliser la visualisation et l\'utilisation des modules par profil et par unité, sans modifier la structure par défaut du système.';

  @override
  String get moduleVisibilityRoleLabel => 'Profil';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Permissions par défaut de ce profil';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Ces permissions représentent le comportement par défaut du système. Les paramètres ci-dessous ne permettent que des personnalisations effectuées par l\'Administrateur Général.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Aucun module par défaut';

  @override
  String get moduleVisibilityUnitLabel => 'Unité';

  @override
  String get moduleVisibilityUnitHint =>
      'Un module non défini spécifiquement pour cette Unité hérite de la valeur de \"Toutes les unités\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Toutes les unités (par défaut)';
}
