// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

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
}

/// The translations for Spanish Castilian, as used in Spain (`es_ES`).
class AppLocalizationsEsEs extends AppLocalizationsEs {
  AppLocalizationsEsEs() : super('es_ES');

  @override
  String get appName => 'Control de EPP';

  @override
  String get loading => 'Cargando...';

  @override
  String get save => 'Guardar';

  @override
  String get cancel => 'Cancelar';

  @override
  String get reportsExportPdf => 'Exportar PDF';

  @override
  String get feedbackForward => 'Derivar';

  @override
  String get feedbackReject => 'Rechazar';

  @override
  String get feedbackApprove => 'Aprobar';

  @override
  String get feedbackJustification => 'Justificación';

  @override
  String get feedbackRejectReason => 'Motivo del rechazo';

  @override
  String get confirm => 'Confirmar';

  @override
  String get delete => 'Eliminar';

  @override
  String get edit => 'Editar';

  @override
  String get add => 'Agregar';

  @override
  String get search => 'Buscar';

  @override
  String get filter => 'Filtrar';

  @override
  String get export => 'Exportar';

  @override
  String get print => 'Imprimir';

  @override
  String get close => 'Cerrar';

  @override
  String get back => 'Volver';

  @override
  String get next => 'Siguiente';

  @override
  String get previous => 'Anterior';

  @override
  String get finish => 'Finalizar';

  @override
  String get retry => 'Reintentar';

  @override
  String get refresh => 'Actualizar';

  @override
  String get seeAll => 'Ver todos';

  @override
  String get noResults => 'No se encontraron resultados';

  @override
  String get required => 'Campo obligatorio';

  @override
  String get optional => 'Opcional';

  @override
  String get navDashboard => 'Panel';

  @override
  String get navCompanies => 'Empresas';

  @override
  String get navUsers => 'Usuarios';

  @override
  String get navUnits => 'Unidades';

  @override
  String get navEmployees => 'Colaboradores';

  @override
  String get navEpis => 'EPPs';

  @override
  String get navStock => 'Inventario';

  @override
  String get navDeliveries => 'Entregas';

  @override
  String get navReturns => 'Devoluciones';

  @override
  String get navRecords => 'Fichas';

  @override
  String get navPurchases => 'Compras';

  @override
  String get navReports => 'Informes';

  @override
  String get navSettings => 'Configuración';

  @override
  String get navPortal => 'Portal';

  @override
  String get navFeedback => 'Comentarios';

  @override
  String get loginTitle => 'Iniciar sesión';

  @override
  String get loginUsername => 'Usuario';

  @override
  String get loginPassword => 'Contraseña';

  @override
  String get loginUsernameHint => 'Ingrese su usuario';

  @override
  String get loginPasswordHint => 'Ingrese su contraseña';

  @override
  String get loginButton => 'Iniciar sesión';

  @override
  String get loginForgotPassword => 'Olvidé mi contraseña';

  @override
  String get loginShowPassword => 'Mostrar contraseña';

  @override
  String get loginHidePassword => 'Ocultar contraseña';

  @override
  String get loginError => 'Usuario o contraseña incorrectos';

  @override
  String get loginErrorEmpty => 'Complete usuario y contraseña';

  @override
  String get loginBiometric => 'Biometría';

  @override
  String get dashboardTitle => 'Panel principal';

  @override
  String get dashboardDeliveriesToday => 'Entregas hoy';

  @override
  String get dashboardExpiringEpis => 'EPPs por vencer';

  @override
  String get dashboardCriticalStock => 'Stock crítico';

  @override
  String get dashboardPendingPurchases => 'Compras pendientes';

  @override
  String get dashboardQuickDelivery => 'Nueva Entrega';

  @override
  String get dashboardQuickReturn => 'Devolución';

  @override
  String get dashboardQuickScan => 'Escanear QR';

  @override
  String get dashboardAlertsTitle => 'Alertas del día';

  @override
  String get dashboardNoAlerts => 'Sin alertas en este momento';

  @override
  String get dashboardWeeklyChartTitle => 'Entregas — últimos 7 días';

  @override
  String get dayMon => 'Lun';

  @override
  String get dayTue => 'Mar';

  @override
  String get dayWed => 'Mié';

  @override
  String get dayThu => 'Jue';

  @override
  String get dayFri => 'Vie';

  @override
  String get daySat => 'Sáb';

  @override
  String get daySun => 'Dom';

  @override
  String get employeesTitle => 'Colaboradores';

  @override
  String get employeesNew => 'Nuevo Colaborador';

  @override
  String get employeesSearchHint => 'Buscar por nombre, código o área';

  @override
  String get employeeNameLabel => 'Nombre completo';

  @override
  String get employeeCodeLabel => 'Matrícula';

  @override
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Área';

  @override
  String get employeeRoleLabel => 'Cargo';

  @override
  String get employeeUnitLabel => 'Unidad';

  @override
  String get employeeLegalEntityLabel => 'CNPJ';

  @override
  String get employeeAdmissionLabel => 'Fecha de ingreso';

  @override
  String get employeeScheduleLabel => 'Turno';

  @override
  String get employeeStatusActive => 'Activo';

  @override
  String get employeeStatusInactive => 'Inactivo';

  @override
  String employeeDeleteConfirm(String name) {
    return '¿Eliminar colaborador $name?';
  }

  @override
  String get episTitle => 'EPPs';

  @override
  String get episNew => 'Nuevo EPP';

  @override
  String get episSearchHint => 'Buscar por nombre, marcado CE o código';

  @override
  String get epiNameLabel => 'Nombre del EPP';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'N° CE';

  @override
  String get epiSectorLabel => 'Sector';

  @override
  String get epiSectionLabel => 'Sección de EPP';

  @override
  String get epiModelLabel => 'Modelo/referencia';

  @override
  String get epiManufacturerLabel => 'Fabricante';

  @override
  String get epiSupplierLabel => 'Proveedor';

  @override
  String get epiUnitMeasureLabel => 'Unidad de medida';

  @override
  String get epiValidityDateLabel => 'Fecha de validez';

  @override
  String get epiManufacturerValidityLabel => 'Validez (meses)';

  @override
  String get epiCaExpiryLabel => 'Vencimiento marcado CE';

  @override
  String get epiValidityDaysLabel => 'Vigencia (días)';

  @override
  String get epiStockLabel => 'Stock actual';

  @override
  String get epiMinStockLabel => 'Stock mínimo';

  @override
  String get epiStatusValid => 'Vigente';

  @override
  String epiStatusExpiring(int days) {
    return 'Vence en $days días';
  }

  @override
  String get epiStatusExpired => 'Vencido';

  @override
  String get epiStatusNoStock => 'Sin stock';

  @override
  String get stockTitle => 'Inventario';

  @override
  String get stockScan => 'Escanear QR';

  @override
  String get stockMoveIn => 'Entrada';

  @override
  String get stockMoveOut => 'Salida';

  @override
  String get stockBatch => 'Operación masiva';

  @override
  String get stockMinimumAlert => 'Stock mínimo alcanzado';

  @override
  String stockCriticalAlert(String name) {
    return 'Stock crítico — $name';
  }

  @override
  String get deliveriesTitle => 'Entregas';

  @override
  String get deliveryNew => 'Nueva Entrega';

  @override
  String get deliveryStep1 => 'Colaborador';

  @override
  String get deliveryStep2 => 'EPP';

  @override
  String get deliveryStep3 => 'Revisión';

  @override
  String get deliveryStep4 => 'Firma';

  @override
  String get deliveryConfirm => 'Confirmar entrega';

  @override
  String get deliverySuccess => 'Entrega registrada exitosamente';

  @override
  String get deliveryOfflineQueued =>
      'Entrega guardada — se sincronizará al conectarse';

  @override
  String get deliverySignatureRequired => 'Firma obligatoria';

  @override
  String get deliveryClearSignature => 'Borrar firma';

  @override
  String get returnsTitle => 'Devoluciones';

  @override
  String get returnNew => 'Nueva Devolución';

  @override
  String get returnStep1 => 'Seleccionar EPP';

  @override
  String get returnStep2 => 'Condición';

  @override
  String get returnStep3 => 'Confirmar';

  @override
  String get returnConditionGood => 'Buen estado';

  @override
  String get returnConditionDamaged => 'Dañado';

  @override
  String get returnConditionLost => 'Extraviado';

  @override
  String get returnSuccess => 'Devolución registrada con éxito.';

  @override
  String get returnOfflineQueued =>
      'Devolución guardada — se sincronizará cuando haya conexión.';

  @override
  String get recordsTitle => 'Fichas';

  @override
  String get recordsPreview => 'Ver ficha';

  @override
  String get recordsPrint => 'Imprimir ficha';

  @override
  String get recordsSearchHint => 'Buscar por empleado, código o unidad…';

  @override
  String get recordsStatusComplete => 'Completo';

  @override
  String get recordsStatusPending => 'Pendiente';

  @override
  String get recordsStatusOverdue => 'Atrasado';

  @override
  String get purchasesTitle => 'Compras';

  @override
  String get purchaseOrdersTitle => 'Órdenes de compra';

  @override
  String get poApprove => 'Aprobar';

  @override
  String get poReceive => 'Recibir';

  @override
  String get poQuantityReceived => 'Cant. recibida';

  @override
  String get poReceiveNotes => 'Observación';

  @override
  String get poManufacturerValidity => 'Validez del fabricante';

  @override
  String get poManufacturerValidityHint => 'Indicar fecha';

  @override
  String get poManufacturerValidityRequired =>
      'Indique la validez del fabricante de todos los EPI recibidos.';

  @override
  String get poOcrDateNotFound =>
      'No se pudo identificar la fecha. Inténtelo de nuevo.';

  @override
  String get poOcrCameraFailed => 'Error en la lectura por cámara.';

  @override
  String get poPickDate => 'Seleccionar fecha';

  @override
  String get poReadDateCamera => 'Leer fecha con la cámara (OCR)';

  @override
  String get poCheck => 'Verificar';

  @override
  String get purchasesNew => 'Nuevo Pedido';

  @override
  String get purchaseStatusDraft => 'Borrador';

  @override
  String get purchaseStatusSent => 'Enviado';

  @override
  String get purchaseStatusPending => 'En espera de aprobación';

  @override
  String get purchaseStatusApproved => 'Aprobado';

  @override
  String get purchaseStatusRejected => 'Rechazado';

  @override
  String get purchaseStatusOrdering => 'En pedido';

  @override
  String get purchaseStatusReceived => 'Recibido';

  @override
  String get reportsTitle => 'Informes';

  @override
  String get reportsGenerate => 'Generar informe';

  @override
  String get reportsPeriod => 'Período';

  @override
  String get reportsExport => 'Exportar';

  @override
  String get reportsSummaryTab => 'Resumen';

  @override
  String get reportsRequestsTab => 'Solicitudes';

  @override
  String get reportsTotalDeliveries => 'Total de entregas';

  @override
  String get reportsTopEpis => 'Top EPPs entregados';

  @override
  String get reportsTopSectors => 'Entregas por área';

  @override
  String get reportsRequestStatusPending => 'En espera';

  @override
  String get reportsRequestStatusProcessing => 'Procesando';

  @override
  String get reportsRequestStatusCompleted => 'Completado';

  @override
  String get reportsRequestStatusFailed => 'Falló';

  @override
  String get reportsAllUnits => 'Todas las unidades';

  @override
  String get reportsRequestDialogTitle => 'Solicitar informe';

  @override
  String get reportsRequestYear => 'Año';

  @override
  String get reportsRequestMonth => 'Mes';

  @override
  String get reportsRequestNotes => 'Observaciones (opcional)';

  @override
  String get reportsRequestSubmit => 'Solicitar';

  @override
  String get reportsNoRequests => 'Sin solicitudes';

  @override
  String get reportsNoData => 'Sin datos disponibles';

  @override
  String get reportsRequestSuccess => 'Solicitud enviada con éxito.';

  @override
  String get companiesTitle => 'Empresas';

  @override
  String get companiesSearchHint => 'Buscar por nombre o RUT';

  @override
  String get companyStatusActive => 'Activo';

  @override
  String get companyStatusInactive => 'Inactivo';

  @override
  String get companyStatusSuspended => 'Suspendido';

  @override
  String get settingsTitle => 'Configuración';

  @override
  String get settingsLanguage => 'Idioma';

  @override
  String get settingsLanguageUser => 'Idioma del usuario';

  @override
  String get settingsLanguageCompany => 'Idioma de la empresa';

  @override
  String get settingsTheme => 'Tema';

  @override
  String get settingsThemeLight => 'Claro';

  @override
  String get settingsThemeDark => 'Oscuro';

  @override
  String get settingsThemeSystem => 'Sistema';

  @override
  String get settingsAppSection => 'Aplicación';

  @override
  String get settingsFichaSection => 'Ficha';

  @override
  String get settingsFichaTitle => 'Título de la ficha';

  @override
  String get settingsFichaDeclaration => 'Declaración';

  @override
  String get settingsFichaObservations => 'Observaciones';

  @override
  String get settingsFichaTracking => 'Trazabilidad';

  @override
  String get settingsSaved => 'Configuración guardada con éxito.';

  @override
  String get portalTitle => 'Portal del Colaborador';

  @override
  String get portalScanQr => 'Escanear QR Code';

  @override
  String get portalEnterCpf => 'Ingrese su documento';

  @override
  String get portalCpfHint => 'Ej: 000.000.000-00';

  @override
  String get portalCpfVerify => 'Acceder al portal';

  @override
  String get portalHistory => 'Mi historial de EPPs';

  @override
  String get portalSignature => 'Confirmar firma';

  @override
  String get portalSignatureInstruction =>
      'Firme en el espacio de abajo para confirmar la recepción';

  @override
  String get portalDeliveries => 'Entregas';

  @override
  String get portalFichas => 'Fichas';

  @override
  String get portalSignDelivery => 'Firmar';

  @override
  String get portalSignAll => 'Firmar todas';

  @override
  String get portalSigned => 'Firmado';

  @override
  String get portalUnsigned => 'Pendiente';

  @override
  String get portalSignSuccess => 'Firma registrada con éxito.';

  @override
  String get portalNoDeliveries => 'No se encontraron entregas';

  @override
  String get portalQty => 'Cant';

  @override
  String get errorGeneric => 'Ocurrió un error. Intente nuevamente.';

  @override
  String get errorNetwork => 'Sin conexión a internet';

  @override
  String get errorUnauthorized => 'Sesión expirada. Inicie sesión nuevamente.';

  @override
  String get errorNotFound => 'Registro no encontrado';

  @override
  String get errorServerError => 'Error en el servidor. Intente más tarde.';

  @override
  String get statusActive => 'Activo';

  @override
  String get statusInactive => 'Inactivo';

  @override
  String get statusExpired => 'Vencido';

  @override
  String get statusExpiring => 'Por vencer';

  @override
  String get statusPending => 'Pendiente';

  @override
  String get statusApproved => 'Aprobado';

  @override
  String get statusRejected => 'Rechazado';

  @override
  String get statusInReview => 'En revisión';

  @override
  String get confirmDeleteTitle => 'Confirmar eliminación';

  @override
  String get confirmDeleteMessage => 'Esta acción no se puede deshacer.';

  @override
  String get confirmDeleteButton => 'Eliminar';

  @override
  String get employeeContactTitle => 'Contactar colaborador';

  @override
  String get employeeContactWhatsapp => 'WhatsApp';

  @override
  String get employeeContactEmail => 'Correo electrónico';

  @override
  String get employeeContactPdf => 'Descargar PDF';

  @override
  String get employeeContactLaunching => 'Abriendo...';

  @override
  String get employeeContactPdfDownloading => 'Descargando PDF...';

  @override
  String get employeeContactErrorNoApp =>
      'No hay app disponible para abrir este enlace';

  @override
  String get employeeContactErrorGeneric =>
      'Error al contactar al colaborador. Inténtalo de nuevo.';

  @override
  String get employeeContactPdfError =>
      'Error al descargar el PDF. Inténtalo de nuevo.';

  @override
  String get offlineBanner => 'Sin conexión — datos guardados localmente';

  @override
  String get syncingBanner => 'Sincronizando...';

  @override
  String get syncDone => 'Datos sincronizados';

  @override
  String get searchEmployeeHint => 'Buscar colaborador...';

  @override
  String get searchEpiHint => 'Buscar EPP...';

  @override
  String get fieldQuantity => 'Cantidad';

  @override
  String get filterAll => 'Todos';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Stock: $qty';
  }

  @override
  String get deliveryDateLabel => 'Fecha de entrega';

  @override
  String get deliveryNextReplacement => 'Próxima sustitución';

  @override
  String deliveryDateValue(String date) {
    return 'Fecha: $date';
  }

  @override
  String get returnSelectDelivery => 'Seleccionar entrega a devolver';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Entregado el $date · Cant.: $qty';
  }

  @override
  String get returnConditionTitle => 'Condición del EPP';

  @override
  String get returnDestinationTitle => 'Destino';

  @override
  String get returnDestDiscard => 'Desecho';

  @override
  String get returnDestRepair => 'Mantenimiento';

  @override
  String get returnDestStock => 'Devolver al stock';

  @override
  String get returnSubmit => 'Registrar devolución';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Entrega: $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Cantidad: $qty';
  }

  @override
  String get purchaseTitleLabel => 'Título de la solicitud';

  @override
  String get purchaseSelectUnit => 'Seleccione una unidad';

  @override
  String get purchaseItemsTitle => 'Artículos de la solicitud';

  @override
  String get purchaseAddEpi => 'Agregar EPP';

  @override
  String get purchaseNoItems => 'Ningún artículo agregado';

  @override
  String get purchaseCreate => 'Crear solicitud';

  @override
  String get purchaseAddAtLeastOne => 'Agregue al menos un artículo';

  @override
  String get purchaseQuantityColon => 'Cantidad:';

  @override
  String purchaseItemsCount(int count) {
    return '$count artículos';
  }

  @override
  String get purchaseStatusAwaiting => 'En espera';

  @override
  String get purchaseStatusCorrection => 'Corrección solicitada';

  @override
  String get purchaseStatusAwaitingReceipt => 'Esperando recepción';

  @override
  String get purchaseStatusCompleted => 'Completado';

  @override
  String get purchaseStatusCancelled => 'Cancelado';

  @override
  String get suppliersTitle => 'Proveedores';

  @override
  String get supplierNew => 'Nuevo proveedor';

  @override
  String get supplierEdit => 'Editar proveedor';

  @override
  String get supplierCnpjLabel => 'CNPJ (ID fiscal)';

  @override
  String get supplierPhoneLabel => 'Teléfono';

  @override
  String get supplierPaymentTermsLabel => 'Condiciones de pago';

  @override
  String get supplierIntegrationLevelLabel => 'Nivel de integración';

  @override
  String get supplierInactiveLabel => 'Inactivo';

  @override
  String get supplierCatalogTitle => 'Catálogo del proveedor';

  @override
  String get catalogNewProduct => 'Nuevo producto';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Descripción';

  @override
  String get catalogLastPriceLabel => 'Último precio';

  @override
  String get catalogLeadTimeLabel => 'Plazo (días)';

  @override
  String get quotesTitle => 'Cotizaciones';

  @override
  String get quotesNew => 'Nueva cotización';

  @override
  String get quotesSelectSuppliers => 'Seleccione los proveedores';

  @override
  String get quoteSendEmail => 'Enviar por correo';

  @override
  String get quoteSendPortal => 'Enviar por el portal';

  @override
  String get quoteAnswerAction => 'Registrar respuesta';

  @override
  String get quoteSelectWinner => 'Seleccionar ganadora';

  @override
  String get quoteComparisonTitle => 'Comparación de cotizaciones';

  @override
  String get quoteFreightLabel => 'Flete';

  @override
  String get quoteUnitPriceLabel => 'Precio unitario';

  @override
  String get quoteDeclinedLabel => 'Rechazado';

  @override
  String get quoteBestPriceLabel => 'Mejor precio';

  @override
  String get quoteBestLeadTimeLabel => 'Mejor plazo';

  @override
  String get quoteCreatePo => '¿Generar PO desde la cotización ganadora?';

  @override
  String get poSupplierActionsTitle => 'Proveedor y entrega';

  @override
  String get poSendToSupplier => 'Enviar al proveedor';

  @override
  String get poPortalLinkAction => 'Enviar enlace del portal';

  @override
  String get poRegisterConfirmation => 'Registrar confirmación';

  @override
  String get poTrackingTitle => 'Seguimiento';

  @override
  String get poDeliveryForecastLabel => 'Previsión de entrega';

  @override
  String get poCarrierLabel => 'Transportista';

  @override
  String get poTrackingCodeLabel => 'Código de seguimiento';

  @override
  String get commentLabel => 'Comentario';

  @override
  String get actionSentSuccess => 'Enviado con éxito';

  @override
  String get myCompanyTitle => 'Mi Empresa';

  @override
  String get myCompanySubtitle =>
      'Datos, identidad visual y dominio de su empresa';

  @override
  String get myCompanySaved =>
      'Configuración de la empresa guardada correctamente.';

  @override
  String get myCompanyLoadError =>
      'No se pudieron cargar los datos de la empresa.';

  @override
  String get myCompanyContractSection => 'Contrato (solo lectura)';

  @override
  String get myCompanyPlan => 'Plan';

  @override
  String get myCompanyUserLimit => 'Límite de usuarios';

  @override
  String get myCompanyLicense => 'Licencia';

  @override
  String get myCompanyRegistrationSection => 'Datos de registro';

  @override
  String get myCompanyName => 'Nombre comercial';

  @override
  String get myCompanyLegalName => 'Razón social';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'Registro estatal';

  @override
  String get myCompanyMunicipalRegistration => 'Registro municipal';

  @override
  String get myCompanyAddress => 'Dirección';

  @override
  String get myCompanyPhone => 'Teléfono';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'Correo institucional';

  @override
  String get myCompanyWebsite => 'Sitio web';

  @override
  String get myCompanyIdentitySection => 'Identidad y tema';

  @override
  String get myCompanyDisplayName => 'Nombre mostrado en el sistema';

  @override
  String get myCompanyInstitutionalMessage => 'Mensaje institucional';

  @override
  String get myCompanyPrimaryColor => 'Color principal (hex)';

  @override
  String get myCompanySecondaryColor => 'Color secundario (hex)';

  @override
  String get myCompanyPreferencesSection => 'Preferencias';

  @override
  String get myCompanyTimezone => 'Zona horaria';

  @override
  String get myCompanySave => 'Guardar configuración de la empresa';

  @override
  String get myCompanyDomainsSection => 'Dominios';

  @override
  String get myCompanyDomainField => 'Dominio';

  @override
  String get myCompanyDomainTypePlatform => 'Subdominio de la plataforma';

  @override
  String get myCompanyDomainTypeCustomSub => 'Subdominio personalizado';

  @override
  String get myCompanyDomainTypeCustom => 'Dominio personalizado';

  @override
  String get myCompanyDomainAdd => 'Registrar dominio';

  @override
  String get myCompanyDomainVerify => 'Verificar';

  @override
  String get myCompanyDomainDelete => 'Eliminar';

  @override
  String get myCompanyDomainPending => 'Pendiente';

  @override
  String get myCompanyDomainVerified => 'Verificado';

  @override
  String get myCompanyDomainFailed => 'Falló';

  @override
  String get myCompanyDomainPrimary => 'Principal';

  @override
  String get myCompanyDomainCname => 'Apunte el CNAME a';

  @override
  String get myCompanyDomainTxt => 'Cree el registro TXT';

  @override
  String get myCompanyDomainToken => 'Valor del TXT';

  @override
  String get handoverScanAgain => 'Nueva conferencia';

  @override
  String get legalEntitiesTitle => 'CNPJ';

  @override
  String get legalEntitiesNew => 'Nuevo CNPJ';

  @override
  String get legalEntityLegalNameLabel => 'Razón social';

  @override
  String get legalEntityTradeNameLabel => 'Nombre comercial';

  @override
  String get legalEntityTypeLabel => 'Tipo';

  @override
  String get legalEntityInactiveBadge => 'Inactivo';

  @override
  String get legalEntityDeactivate => 'Desactivar CNPJ';

  @override
  String get legalEntityDeactivateHint =>
      'El historial jurídico se conserva. El CNPJ deja de usarse en nuevas operaciones.';

  @override
  String get legalEntityShowInactive => 'Mostrar inactivos';

  @override
  String get legalEntitiesEmpty => 'Ningún CNPJ registrado.';

  @override
  String get legalEntityMunicipalityLabel => 'Municipio';

  @override
  String get legalEntitiesImport => 'Importar hoja de cálculo';

  @override
  String get legalEntitiesImportHint =>
      'Copie las filas de la hoja (incluida la de encabezado) y péguelas abajo. Acepta columnas en portugués o inglés.';

  @override
  String get legalEntitiesImportResult => 'Importación finalizada';

  @override
  String get dashboardFilterLegalEntity => 'CNPJ';

  @override
  String get dashboardFilterUnit => 'Unidad';

  @override
  String get dashboardFilterSector => 'Sector';

  @override
  String get dashboardFilterAll => 'Todos';

  @override
  String get dashboardFilterClear => 'Limpiar filtros';

  @override
  String get legalEntityTransferTitle => 'Transferir vínculo jurídico';

  @override
  String get legalEntityTransferHint =>
      'El CNPJ es el vínculo del contrato laboral y no cambia al transferir de unidad. Este cambio se audita y exige justificación.';

  @override
  String get legalEntityTransferReason => 'Justificación';

  @override
  String get legalEntityTransferTarget => 'Nuevo CNPJ';

  @override
  String get legalEntityTransferAction => 'Transferir';

  @override
  String get legalEntityTransferHistory => 'Historial de vínculo';

  @override
  String get unitTransferTitle => 'Transferir de unidad';

  @override
  String get unitTransferHint =>
      'Movimiento de unidad operativa — temporal o definitivo. Genera un registro auditable y no cambia el CNPJ del colaborador.';

  @override
  String get unitTransferTarget => 'Unidad destino';

  @override
  String get unitTransferType => 'Tipo de movimiento';

  @override
  String get unitTransferTypeTemporary => 'Temporal';

  @override
  String get unitTransferTypeDefinitive => 'Definitivo';

  @override
  String get unitTransferStartDate => 'Fecha de inicio';

  @override
  String get unitTransferEndDate => 'Fecha de fin (opcional)';

  @override
  String get unitTransferNotes => 'Observación (opcional)';

  @override
  String get unitTransferAction => 'Transferir';

  @override
  String get myCompanyStockScope => 'Consolidar saldos de stock por';

  @override
  String get myCompanyStockScopeHint =>
      'Esta configuración solo cambia la vista consolidada de los saldos. Entradas, reservas, salidas, entregas y demás movimientos siguen vinculados al stock de cada unidad.';

  @override
  String get myCompanyStockScopeUnit => 'Unidad';

  @override
  String get myCompanyStockScopeLegalEntity => 'CNPJ';

  @override
  String get myCompanyStockScopeCompany => 'Empresa';

  @override
  String get navLegalEntities => 'CNPJ';

  @override
  String get unitLegalEntityLabel => 'CNPJ responsable';

  @override
  String get unitLegalEntityHint =>
      'Persona jurídica responsable de las operaciones y del stock de esta unidad.';

  @override
  String get employeeEmploymentTypeLabel => 'Tipo de Vínculo';

  @override
  String get employeeSourceCompanyLabel => 'Empresa de Origen';

  @override
  String get employeeSourceCompanyHint =>
      'Nombre de la empresa de origen del colaborador';

  @override
  String get employmentTypeClt => 'CLT';

  @override
  String get employmentTypeOutsourced => 'Tercerizado';

  @override
  String get employmentTypeTemporary => 'Temporal';

  @override
  String get employmentTypeServiceProvider => 'Prestador de Servicio';

  @override
  String get employmentTypeApprentice => 'Aprendiz Menor';

  @override
  String get employmentTypeTrainee => 'Practicante';

  @override
  String get employmentTypeIntern => 'Becario';

  @override
  String get navTerceirizados => 'Tercerizados y Prestadores';

  @override
  String get outsourcedCompaniesTitle => 'Tercerizados y Prestadores';

  @override
  String get outsourcedCompaniesEmpty =>
      'Ninguna empresa tercerizada registrada.';

  @override
  String get outsourcedCompaniesSearchHint => 'Buscar por nombre o CNPJ';

  @override
  String get outsourcedCompanyNew => 'Nueva empresa';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Razón Social';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Nombre Fantasía';

  @override
  String get outsourcedCompanyCnpjLabel => 'CNPJ';

  @override
  String get outsourcedCompanyCnpjHint =>
      'Opcional en el Registro Simplificado';

  @override
  String get outsourcedCompanyKindLabel => 'Tipo de Empresa';

  @override
  String get outsourcedCompanyKindOutsourced => 'Tercerizada';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Prestadora de Servicio';

  @override
  String get outsourcedCompanyKindOther => 'Otro';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'Responsabilidad por el Suministro de EPP';

  @override
  String get outsourcedCompanyStatusLabel => 'Situación';

  @override
  String get outsourcedCompanySave => 'Guardar';

  @override
  String get outsourcedCompanyCancel => 'Cancelar';

  @override
  String get outsourcedCompanyPromote => 'Promover a Registro Estándar';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      '¿Promover a Registro Estándar?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'La empresa pasará a ser tratada como Registro Estándar. Se requiere un CNPJ.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplificado';

  @override
  String get outsourcedCompanyStandardBadge => 'Estándar';
}
