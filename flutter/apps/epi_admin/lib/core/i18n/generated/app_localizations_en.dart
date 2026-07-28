// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

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
}

/// The translations for English, as used in the United States (`en_US`).
class AppLocalizationsEnUs extends AppLocalizationsEn {
  AppLocalizationsEnUs() : super('en_US');

  @override
  String get appName => 'EPI Control';

  @override
  String get loading => 'Loading...';

  @override
  String get save => 'Save';

  @override
  String get cancel => 'Cancel';

  @override
  String get reportsExportPdf => 'Export PDF';

  @override
  String get feedbackForward => 'Forward';

  @override
  String get feedbackReject => 'Reject';

  @override
  String get feedbackApprove => 'Approve';

  @override
  String get feedbackJustification => 'Justification';

  @override
  String get feedbackRejectReason => 'Rejection reason';

  @override
  String get confirm => 'Confirm';

  @override
  String get delete => 'Delete';

  @override
  String get edit => 'Edit';

  @override
  String get add => 'Add';

  @override
  String get search => 'Search';

  @override
  String get filter => 'Filter';

  @override
  String get export => 'Export';

  @override
  String get print => 'Print';

  @override
  String get close => 'Close';

  @override
  String get back => 'Back';

  @override
  String get next => 'Next';

  @override
  String get previous => 'Previous';

  @override
  String get finish => 'Finish';

  @override
  String get retry => 'Retry';

  @override
  String get refresh => 'Refresh';

  @override
  String get seeAll => 'See all';

  @override
  String get noResults => 'No results found';

  @override
  String get required => 'Required field';

  @override
  String get optional => 'Optional';

  @override
  String get navDashboard => 'Dashboard';

  @override
  String get navCompanies => 'Companies';

  @override
  String get navUsers => 'Users';

  @override
  String get navUnits => 'Units';

  @override
  String get navEmployees => 'Employees';

  @override
  String get navEpis => 'PPEs';

  @override
  String get navStock => 'Stock';

  @override
  String get navDeliveries => 'Deliveries';

  @override
  String get navReturns => 'Returns';

  @override
  String get navRecords => 'Records';

  @override
  String get navPurchases => 'Purchases';

  @override
  String get navReports => 'Reports';

  @override
  String get navSettings => 'Settings';

  @override
  String get navPortal => 'Portal';

  @override
  String get navFeedback => 'Feedback';

  @override
  String get loginTitle => 'Sign in';

  @override
  String get loginUsername => 'Username';

  @override
  String get loginPassword => 'Password';

  @override
  String get loginUsernameHint => 'Enter your username';

  @override
  String get loginPasswordHint => 'Enter your password';

  @override
  String get loginButton => 'Sign in';

  @override
  String get loginForgotPassword => 'Forgot password';

  @override
  String get loginShowPassword => 'Show password';

  @override
  String get loginHidePassword => 'Hide password';

  @override
  String get loginError => 'Incorrect username or password';

  @override
  String get loginErrorEmpty => 'Please enter username and password';

  @override
  String get loginBiometric => 'Biometrics';

  @override
  String get dashboardTitle => 'Dashboard';

  @override
  String get dashboardDeliveriesToday => 'Deliveries today';

  @override
  String get dashboardExpiringEpis => 'Expiring PPEs';

  @override
  String get dashboardCriticalStock => 'Critical stock';

  @override
  String get dashboardPendingPurchases => 'Pending purchases';

  @override
  String get dashboardQuickDelivery => 'New Delivery';

  @override
  String get dashboardQuickReturn => 'Return';

  @override
  String get dashboardQuickScan => 'QR Scan';

  @override
  String get dashboardAlertsTitle => 'Today\'s Alerts';

  @override
  String get dashboardNoAlerts => 'No alerts at this time';

  @override
  String get dashboardWeeklyChartTitle => 'Deliveries — last 7 days';

  @override
  String get dayMon => 'Mon';

  @override
  String get dayTue => 'Tue';

  @override
  String get dayWed => 'Wed';

  @override
  String get dayThu => 'Thu';

  @override
  String get dayFri => 'Fri';

  @override
  String get daySat => 'Sat';

  @override
  String get daySun => 'Sun';

  @override
  String get employeesTitle => 'Employees';

  @override
  String get employeesNew => 'New Employee';

  @override
  String get employeesSearchHint => 'Search by name, code or department';

  @override
  String get employeeNameLabel => 'Full name';

  @override
  String get employeeCodeLabel => 'Employee ID';

  @override
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Department';

  @override
  String get employeeRoleLabel => 'Job title';

  @override
  String get employeeUnitLabel => 'Unit';

  @override
  String get employeeLegalEntityLabel => 'Tax ID (CNPJ)';

  @override
  String get employeeAdmissionLabel => 'Hire date';

  @override
  String get employeeScheduleLabel => 'Schedule';

  @override
  String get employeeStatusActive => 'Active';

  @override
  String get employeeStatusInactive => 'Inactive';

  @override
  String employeeDeleteConfirm(String name) {
    return 'Delete employee $name?';
  }

  @override
  String get episTitle => 'PPEs';

  @override
  String get episNew => 'New PPE';

  @override
  String get episSearchHint => 'Search by name, CE marking or code';

  @override
  String get epiNameLabel => 'PPE name';

  @override
  String get epiCodeLabel => 'Purchase code';

  @override
  String get epiCaLabel => 'CE No.';

  @override
  String get epiSectorLabel => 'Sector';

  @override
  String get epiSectionLabel => 'PPE section';

  @override
  String get epiModelLabel => 'Model/reference';

  @override
  String get epiManufacturerLabel => 'Manufacturer';

  @override
  String get epiSupplierLabel => 'Supplier';

  @override
  String get epiUnitMeasureLabel => 'Unit of measure';

  @override
  String get epiValidityDateLabel => 'Validity date';

  @override
  String get epiManufacturerValidityLabel => 'Validity (months)';

  @override
  String get epiCaExpiryLabel => 'CE marking expiry';

  @override
  String get epiValidityDaysLabel => 'Validity (days)';

  @override
  String get epiStockLabel => 'Current stock';

  @override
  String get epiMinStockLabel => 'Minimum stock';

  @override
  String get epiStatusValid => 'Valid';

  @override
  String epiStatusExpiring(int days) {
    return 'Expires in $days days';
  }

  @override
  String get epiStatusExpired => 'Expired';

  @override
  String get epiStatusNoStock => 'Out of stock';

  @override
  String get stockTitle => 'Stock';

  @override
  String get stockScan => 'Scan QR';

  @override
  String get stockMoveIn => 'Stock in';

  @override
  String get stockMoveOut => 'Stock out';

  @override
  String get stockBatch => 'Batch operation';

  @override
  String get stockMinimumAlert => 'Minimum stock reached';

  @override
  String stockCriticalAlert(String name) {
    return 'Critical stock — $name';
  }

  @override
  String get deliveriesTitle => 'Deliveries';

  @override
  String get deliveryNew => 'New Delivery';

  @override
  String get deliveryStep1 => 'Employee';

  @override
  String get deliveryStep2 => 'PPE';

  @override
  String get deliveryStep3 => 'Review';

  @override
  String get deliveryStep4 => 'Signature';

  @override
  String get deliveryConfirm => 'Confirm delivery';

  @override
  String get deliverySuccess => 'Delivery recorded successfully';

  @override
  String get deliveryOfflineQueued =>
      'Delivery saved — will sync when connected';

  @override
  String get deliverySignatureRequired => 'Signature required';

  @override
  String get deliveryClearSignature => 'Clear signature';

  @override
  String get returnsTitle => 'Returns';

  @override
  String get returnNew => 'New Return';

  @override
  String get returnStep1 => 'Select PPE';

  @override
  String get returnStep2 => 'Condition';

  @override
  String get returnStep3 => 'Confirm';

  @override
  String get returnConditionGood => 'Good condition';

  @override
  String get returnConditionDamaged => 'Damaged';

  @override
  String get returnConditionLost => 'Lost';

  @override
  String get returnSuccess => 'Return recorded successfully.';

  @override
  String get returnOfflineQueued => 'Return saved — will sync when connected.';

  @override
  String get recordsTitle => 'Records';

  @override
  String get recordsPreview => 'Preview record';

  @override
  String get recordsPrint => 'Print record';

  @override
  String get recordsSearchHint => 'Search by employee, code or unit…';

  @override
  String get recordsStatusComplete => 'Complete';

  @override
  String get recordsStatusPending => 'Pending';

  @override
  String get recordsStatusOverdue => 'Overdue';

  @override
  String get purchasesTitle => 'Purchases';

  @override
  String get purchaseOrdersTitle => 'Purchase orders';

  @override
  String get poApprove => 'Approve';

  @override
  String get poReceive => 'Receive';

  @override
  String get poQuantityReceived => 'Qty received';

  @override
  String get poReceiveNotes => 'Notes';

  @override
  String get poManufacturerValidity => 'Manufacturer validity';

  @override
  String get poManufacturerValidityHint => 'Set date';

  @override
  String get poManufacturerValidityRequired =>
      'Enter the manufacturer validity for all received PPE.';

  @override
  String get poOcrDateNotFound => 'Could not read the date. Please try again.';

  @override
  String get poOcrCameraFailed => 'Camera reading failed.';

  @override
  String get poPickDate => 'Pick a date';

  @override
  String get poReadDateCamera => 'Read date with camera (OCR)';

  @override
  String get poCheck => 'Check';

  @override
  String get purchasesNew => 'New Request';

  @override
  String get purchaseStatusDraft => 'Draft';

  @override
  String get purchaseStatusSent => 'Sent';

  @override
  String get purchaseStatusPending => 'Awaiting approval';

  @override
  String get purchaseStatusApproved => 'Approved';

  @override
  String get purchaseStatusRejected => 'Rejected';

  @override
  String get purchaseStatusOrdering => 'Ordering';

  @override
  String get purchaseStatusReceived => 'Received';

  @override
  String get reportsTitle => 'Reports';

  @override
  String get reportsGenerate => 'Generate report';

  @override
  String get reportsPeriod => 'Period';

  @override
  String get reportsExport => 'Export';

  @override
  String get reportsSummaryTab => 'Summary';

  @override
  String get reportsRequestsTab => 'Requests';

  @override
  String get reportsTotalDeliveries => 'Total deliveries';

  @override
  String get reportsTopEpis => 'Top delivered PPEs';

  @override
  String get reportsTopSectors => 'Deliveries by sector';

  @override
  String get reportsRequestStatusPending => 'Pending';

  @override
  String get reportsRequestStatusProcessing => 'Processing';

  @override
  String get reportsRequestStatusCompleted => 'Completed';

  @override
  String get reportsRequestStatusFailed => 'Failed';

  @override
  String get reportsAllUnits => 'All units';

  @override
  String get reportsRequestDialogTitle => 'Request report';

  @override
  String get reportsRequestYear => 'Year';

  @override
  String get reportsRequestMonth => 'Month';

  @override
  String get reportsRequestNotes => 'Notes (optional)';

  @override
  String get reportsRequestSubmit => 'Request';

  @override
  String get reportsNoRequests => 'No requests';

  @override
  String get reportsNoData => 'No data available';

  @override
  String get reportsRequestSuccess => 'Request sent successfully.';

  @override
  String get companiesTitle => 'Companies';

  @override
  String get companiesSearchHint => 'Search by name or tax ID';

  @override
  String get companyStatusActive => 'Active';

  @override
  String get companyStatusInactive => 'Inactive';

  @override
  String get companyStatusSuspended => 'Suspended';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get settingsLanguage => 'Language';

  @override
  String get settingsLanguageUser => 'User language';

  @override
  String get settingsLanguageCompany => 'Company language';

  @override
  String get settingsTheme => 'Theme';

  @override
  String get settingsThemeLight => 'Light';

  @override
  String get settingsThemeDark => 'Dark';

  @override
  String get settingsThemeSystem => 'System';

  @override
  String get settingsAppSection => 'Application';

  @override
  String get settingsFichaSection => 'Record';

  @override
  String get settingsFichaTitle => 'Record title';

  @override
  String get settingsFichaDeclaration => 'Declaration';

  @override
  String get settingsFichaObservations => 'Observations';

  @override
  String get settingsFichaTracking => 'Traceability';

  @override
  String get settingsSaved => 'Settings saved successfully.';

  @override
  String get portalTitle => 'Employee Portal';

  @override
  String get portalScanQr => 'Scan QR Code';

  @override
  String get portalEnterCpf => 'Enter your ID';

  @override
  String get portalCpfHint => 'e.g. 000.000.000-00';

  @override
  String get portalCpfVerify => 'Access portal';

  @override
  String get portalHistory => 'My PPE history';

  @override
  String get portalSignature => 'Confirm signature';

  @override
  String get portalSignatureInstruction =>
      'Sign in the space below to confirm receipt';

  @override
  String get portalDeliveries => 'Deliveries';

  @override
  String get portalFichas => 'Records';

  @override
  String get portalSignDelivery => 'Sign';

  @override
  String get portalSignAll => 'Sign all';

  @override
  String get portalSigned => 'Signed';

  @override
  String get portalUnsigned => 'Pending';

  @override
  String get portalSignSuccess => 'Signature registered successfully.';

  @override
  String get portalNoDeliveries => 'No deliveries found';

  @override
  String get portalQty => 'Qty';

  @override
  String get errorGeneric => 'Something went wrong. Please try again.';

  @override
  String get errorNetwork => 'No internet connection';

  @override
  String get errorUnauthorized => 'Session expired. Please sign in again.';

  @override
  String get errorNotFound => 'Record not found';

  @override
  String get errorServerError => 'Server error. Please try again later.';

  @override
  String get statusActive => 'Active';

  @override
  String get statusInactive => 'Inactive';

  @override
  String get statusExpired => 'Expired';

  @override
  String get statusExpiring => 'Expiring';

  @override
  String get statusPending => 'Pending';

  @override
  String get statusApproved => 'Approved';

  @override
  String get statusRejected => 'Rejected';

  @override
  String get statusInReview => 'In review';

  @override
  String get confirmDeleteTitle => 'Confirm deletion';

  @override
  String get confirmDeleteMessage => 'This action cannot be undone.';

  @override
  String get confirmDeleteButton => 'Delete';

  @override
  String get employeeContactTitle => 'Contact employee';

  @override
  String get employeeContactWhatsapp => 'WhatsApp';

  @override
  String get employeeContactEmail => 'Email';

  @override
  String get employeeContactPdf => 'Download PDF';

  @override
  String get employeeContactLaunching => 'Opening...';

  @override
  String get employeeContactPdfDownloading => 'Downloading PDF...';

  @override
  String get employeeContactErrorNoApp => 'No app available to open this link';

  @override
  String get employeeContactErrorGeneric =>
      'Failed to contact employee. Please try again.';

  @override
  String get employeeContactPdfError =>
      'Failed to download PDF. Please try again.';

  @override
  String get offlineBanner => 'Offline — data saved locally';

  @override
  String get syncingBanner => 'Syncing data...';

  @override
  String get syncDone => 'Data synced';

  @override
  String get searchEmployeeHint => 'Search employee...';

  @override
  String get searchEpiHint => 'Search PPE...';

  @override
  String get fieldQuantity => 'Quantity';

  @override
  String get filterAll => 'All';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Stock: $qty';
  }

  @override
  String get deliveryDateLabel => 'Delivery date';

  @override
  String get deliveryNextReplacement => 'Next replacement';

  @override
  String deliveryDateValue(String date) {
    return 'Date: $date';
  }

  @override
  String get returnSelectDelivery => 'Select delivery to return';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Delivered on $date · Qty: $qty';
  }

  @override
  String get returnConditionTitle => 'PPE condition';

  @override
  String get returnDestinationTitle => 'Destination';

  @override
  String get returnDestDiscard => 'Discard';

  @override
  String get returnDestRepair => 'Maintenance';

  @override
  String get returnDestStock => 'Return to stock';

  @override
  String get returnSubmit => 'Register return';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Delivery: $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Quantity: $qty';
  }

  @override
  String get purchaseTitleLabel => 'Request title';

  @override
  String get purchaseSelectUnit => 'Select a unit';

  @override
  String get purchaseItemsTitle => 'Request items';

  @override
  String get purchaseAddEpi => 'Add PPE';

  @override
  String get purchaseNoItems => 'No items added';

  @override
  String get purchaseCreate => 'Create request';

  @override
  String get purchaseAddAtLeastOne => 'Add at least one item';

  @override
  String get purchaseQuantityColon => 'Quantity:';

  @override
  String purchaseItemsCount(int count) {
    return '$count items';
  }

  @override
  String get purchaseStatusAwaiting => 'Awaiting';

  @override
  String get purchaseStatusCorrection => 'Correction requested';

  @override
  String get purchaseStatusAwaitingReceipt => 'Awaiting receipt';

  @override
  String get purchaseStatusCompleted => 'Completed';

  @override
  String get purchaseStatusCancelled => 'Cancelled';

  @override
  String get suppliersTitle => 'Suppliers';

  @override
  String get supplierNew => 'New supplier';

  @override
  String get supplierEdit => 'Edit supplier';

  @override
  String get supplierCnpjLabel => 'CNPJ (tax ID)';

  @override
  String get supplierPhoneLabel => 'Phone';

  @override
  String get supplierPaymentTermsLabel => 'Payment terms';

  @override
  String get supplierIntegrationLevelLabel => 'Integration level';

  @override
  String get supplierInactiveLabel => 'Inactive';

  @override
  String get supplierCatalogTitle => 'Supplier catalog';

  @override
  String get catalogNewProduct => 'New product';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Description';

  @override
  String get catalogLastPriceLabel => 'Last price';

  @override
  String get catalogLeadTimeLabel => 'Lead time (days)';

  @override
  String get quotesTitle => 'Quotes';

  @override
  String get quotesNew => 'New quote';

  @override
  String get quotesSelectSuppliers => 'Select suppliers';

  @override
  String get quoteSendEmail => 'Send by email';

  @override
  String get quoteSendPortal => 'Send via portal';

  @override
  String get quoteAnswerAction => 'Record answer';

  @override
  String get quoteSelectWinner => 'Select winner';

  @override
  String get quoteComparisonTitle => 'Quote comparison';

  @override
  String get quoteFreightLabel => 'Freight';

  @override
  String get quoteUnitPriceLabel => 'Unit price';

  @override
  String get quoteDeclinedLabel => 'Declined';

  @override
  String get quoteBestPriceLabel => 'Best price';

  @override
  String get quoteBestLeadTimeLabel => 'Best lead time';

  @override
  String get quoteCreatePo => 'Create PO from the winning quote?';

  @override
  String get poSupplierActionsTitle => 'Supplier & delivery';

  @override
  String get poSendToSupplier => 'Send to supplier';

  @override
  String get poPortalLinkAction => 'Send portal link';

  @override
  String get poRegisterConfirmation => 'Record confirmation';

  @override
  String get poTrackingTitle => 'Tracking';

  @override
  String get poDeliveryForecastLabel => 'Delivery forecast';

  @override
  String get poCarrierLabel => 'Carrier';

  @override
  String get poTrackingCodeLabel => 'Tracking code';

  @override
  String get commentLabel => 'Comment';

  @override
  String get actionSentSuccess => 'Sent successfully';

  @override
  String get myCompanyTitle => 'My Company';

  @override
  String get myCompanySubtitle => 'Your company\'s data, branding and domain';

  @override
  String get myCompanySaved => 'Company settings saved successfully.';

  @override
  String get myCompanyLoadError => 'Could not load company data.';

  @override
  String get myCompanyContractSection => 'Contract (read-only)';

  @override
  String get myCompanyPlan => 'Plan';

  @override
  String get myCompanyUserLimit => 'User limit';

  @override
  String get myCompanyLicense => 'License';

  @override
  String get myCompanyRegistrationSection => 'Registration data';

  @override
  String get myCompanyName => 'Trade name';

  @override
  String get myCompanyLegalName => 'Legal name';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'State registration';

  @override
  String get myCompanyMunicipalRegistration => 'Municipal registration';

  @override
  String get myCompanyAddress => 'Address';

  @override
  String get myCompanyPhone => 'Phone';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'Company e-mail';

  @override
  String get myCompanyWebsite => 'Website';

  @override
  String get myCompanyIdentitySection => 'Branding and theme';

  @override
  String get myCompanyDisplayName => 'Display name in the system';

  @override
  String get myCompanyInstitutionalMessage => 'Institutional message';

  @override
  String get myCompanyPrimaryColor => 'Primary color (hex)';

  @override
  String get myCompanySecondaryColor => 'Secondary color (hex)';

  @override
  String get myCompanyPreferencesSection => 'Preferences';

  @override
  String get myCompanyTimezone => 'Time zone';

  @override
  String get myCompanySave => 'Save company settings';

  @override
  String get myCompanyDomainsSection => 'Domains';

  @override
  String get myCompanyDomainField => 'Domain';

  @override
  String get myCompanyDomainTypePlatform => 'Platform subdomain';

  @override
  String get myCompanyDomainTypeCustomSub => 'Custom subdomain';

  @override
  String get myCompanyDomainTypeCustom => 'Custom domain';

  @override
  String get myCompanyDomainAdd => 'Register domain';

  @override
  String get myCompanyDomainVerify => 'Verify';

  @override
  String get myCompanyDomainDelete => 'Remove';

  @override
  String get myCompanyDomainPending => 'Pending';

  @override
  String get myCompanyDomainVerified => 'Verified';

  @override
  String get myCompanyDomainFailed => 'Failed';

  @override
  String get myCompanyDomainPrimary => 'Primary';

  @override
  String get myCompanyDomainCname => 'Point the CNAME to';

  @override
  String get myCompanyDomainTxt => 'Create the TXT record';

  @override
  String get myCompanyDomainToken => 'TXT value';

  @override
  String get handoverScanAgain => 'New handover';

  @override
  String get legalEntitiesTitle => 'Tax IDs (CNPJ)';

  @override
  String get legalEntitiesNew => 'New tax ID';

  @override
  String get legalEntityLegalNameLabel => 'Legal name';

  @override
  String get legalEntityTradeNameLabel => 'Trade name';

  @override
  String get legalEntityTypeLabel => 'Type';

  @override
  String get legalEntityInactiveBadge => 'Inactive';

  @override
  String get legalEntityDeactivate => 'Deactivate tax ID';

  @override
  String get legalEntityDeactivateHint =>
      'Legal history is preserved. The tax ID stops being used in new operations.';

  @override
  String get legalEntityShowInactive => 'Show inactive';

  @override
  String get legalEntitiesEmpty => 'No tax IDs registered.';

  @override
  String get legalEntityMunicipalityLabel => 'Municipality';

  @override
  String get legalEntitiesImport => 'Import spreadsheet';

  @override
  String get legalEntitiesImportHint =>
      'Copy the spreadsheet rows (including the header row) and paste below. Accepts Portuguese or English columns.';

  @override
  String get legalEntitiesImportResult => 'Import finished';

  @override
  String get dashboardFilterLegalEntity => 'Tax ID (CNPJ)';

  @override
  String get dashboardFilterUnit => 'Unit';

  @override
  String get dashboardFilterSector => 'Sector';

  @override
  String get dashboardFilterAll => 'All';

  @override
  String get dashboardFilterClear => 'Clear filters';

  @override
  String get legalEntityTransferTitle => 'Transfer legal entity';

  @override
  String get legalEntityTransferHint =>
      'The tax ID is the employment contract link and does not change on unit transfers. This change is audited and requires a justification.';

  @override
  String get legalEntityTransferReason => 'Justification';

  @override
  String get legalEntityTransferTarget => 'New tax ID';

  @override
  String get legalEntityTransferAction => 'Transfer';

  @override
  String get legalEntityTransferHistory => 'Legal entity history';

  @override
  String get myCompanyStockScope => 'Consolidate stock balances by';

  @override
  String get myCompanyStockScopeHint =>
      'This setting only changes the consolidated view of balances. Receipts, reservations, issues, deliveries and all other movements stay tied to each unit’s own stock.';

  @override
  String get myCompanyStockScopeUnit => 'Unit';

  @override
  String get myCompanyStockScopeLegalEntity => 'Tax ID';

  @override
  String get myCompanyStockScopeCompany => 'Company';

  @override
  String get navLegalEntities => 'Tax IDs';

  @override
  String get unitLegalEntityLabel => 'Responsible tax ID';

  @override
  String get unitLegalEntityHint =>
      'Legal entity accountable for this unit’s operations and stock.';

  @override
  String get employeeEmploymentTypeLabel => 'Employment Type';

  @override
  String get employeeSourceCompanyLabel => 'Source Company';

  @override
  String get employeeSourceCompanyHint =>
      'Name of the employee\'s source company';

  @override
  String get employmentTypeClt => 'CLT (Payroll)';

  @override
  String get employmentTypeOutsourced => 'Outsourced';

  @override
  String get employmentTypeTemporary => 'Temporary';

  @override
  String get employmentTypeServiceProvider => 'Service Provider';

  @override
  String get employmentTypeApprentice => 'Young Apprentice';

  @override
  String get employmentTypeTrainee => 'Trainee';

  @override
  String get employmentTypeIntern => 'Intern';
}
