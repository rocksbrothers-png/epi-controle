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
  String get employeeUnitLockedHint => 'Unidade definida pelo seu perfil de acesso.';

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
  String get deliveryOfflineQueued => 'Entrega salva — será sincronizada quando houver conexão';

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
  String get returnOfflineQueued => 'Devolução salva — será sincronizada quando houver conexão.';

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
  String get poManufacturerValidityRequired => 'Informe a validade do fabricante de todos os EPIs recebidos.';

  @override
  String get poOcrDateNotFound => 'Não foi possível identificar a data. Tente novamente.';

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
  String get portalSignatureInstruction => 'Assine no espaço abaixo para confirmar o recebimento';

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
  String get employeeContactErrorNoApp => 'Nenhum app disponível para abrir este link';

  @override
  String get employeeContactErrorGeneric => 'Falha ao contatar colaborador. Tente novamente.';

  @override
  String get employeeContactPdfError => 'Falha ao baixar o PDF. Tente novamente.';

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
  String get myCompanySubtitle => 'Dados, identidade visual e domínio da sua empresa';

  @override
  String get myCompanySaved => 'Configurações da empresa salvas com sucesso.';

  @override
  String get myCompanyLoadError => 'Não foi possível carregar os dados da empresa.';

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
  String get epiArchiveBlockBody => 'Este EPI possui saldo disponível ou vínculos vivos. Ao confirmar, o saldo disponível será movido para Estoque Bloqueado (rastreável) e o EPI será arquivado.';

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
  String get handoverConfirmError => 'Não foi possível confirmar o recebimento.';

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
  String get legalEntityDeactivateHint => 'O histórico jurídico é preservado. O CNPJ deixa de ser usado em novas operações.';

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
  String get legalEntitiesImportColumnsHint => 'CNPJ\tRazão social\tNome fantasia\tTipo';

  @override
  String get legalEntitiesImport => 'Importar planilha';

  @override
  String get legalEntitiesImportHint => 'Copie as linhas da planilha (com a linha de cabeçalho) e cole abaixo. Aceita colunas em português ou inglês.';

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
  String get legalEntityTransferHint => 'O CNPJ é o vínculo do contrato de trabalho e não muda em transferência de unidade. Esta alteração é auditada e exige justificativa.';

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
  String get unitTransferHint => 'Movimentação de unidade operacional — temporária ou definitiva. Gera vínculo auditável e não altera o CNPJ do colaborador.';

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
  String get myCompanyStockScopeHint => 'Esta configuração altera apenas a visualização consolidada dos saldos. Entradas, reservas, saídas, entregas e demais movimentações permanecem vinculadas ao estoque de cada unidade.';

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
  String get unitLegalEntityHint => 'Pessoa jurídica que responde pelas operações e pelo estoque desta unidade.';

  @override
  String get employeeEmploymentTypeLabel => 'Tipo de Vínculo';

  @override
  String get employeeSourceCompanyLabel => 'Empresa de Origem';

  @override
  String get employeeSourceCompanyHint => 'Nome da empresa de origem do colaborador';

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
  String get outsourcedCompaniesEmpty => 'Nenhuma empresa terceirizada cadastrada.';

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
  String get outsourcedCompanyResponsibilityLabel => 'Responsabilidade pelo Fornecimento de EPI';

  @override
  String get outsourcedCompanyUnitLabel => 'Unidade';

  @override
  String get outsourcedCompanyUnitAll => 'Todas as unidades (padrão)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidade';

  @override
  String get outsourcedCompanyLinkHint => 'Buscar empresa já cadastrada no tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked => 'Já vinculadas a esta Unidade';

  @override
  String get outsourcedCompanyLinkSectionAvailable => 'Disponíveis para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidade';

  @override
  String get outsourcedCompanyLinkActivate => 'Reativar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get outsourcedCompanyLinkDeactivateReason => 'Motivo do arquivamento (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidade(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidade de origem';

  @override
  String get outsourcedCompanyLinkEmpty => 'Nenhuma empresa encontrada com esse termo.';

  @override
  String get outsourcedCompanyLinkNotInformed => 'Vínculo não informado para o seu perfil';

  @override
  String get outsourcedCompanyStatusLabel => 'Situação';

  @override
  String get outsourcedCompanySave => 'Salvar';

  @override
  String get outsourcedCompanyCancel => 'Cancelar';

  @override
  String get outsourcedCompanyPromote => 'Promover a Cadastro Padrão';

  @override
  String get outsourcedCompanyPromoteConfirmTitle => 'Promover ao Cadastro Padrão?';

  @override
  String get outsourcedCompanyPromoteConfirmBody => 'A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.';

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
  String get outsourcedCompanyRestoreConfirmTitle => 'Desarquivar esta empresa?';

  @override
  String get outsourcedCompaniesArchivedEmpty => 'Nenhuma empresa terceirizada arquivada.';

  @override
  String get outsourcedEmployeeNew => 'Novo colaborador';

  @override
  String get outsourcedEmployeesEmpty => 'Nenhum colaborador terceirizado/prestador cadastrado.';

  @override
  String get outsourcedEmployeesArchivedEmpty => 'Nenhum colaborador terceirizado/prestador arquivado.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Empresa terceirizada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel => 'Matrícula da empresa de origem';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Crachá';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observações';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle => 'Arquivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle => 'Desarquivar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular à minha unidade';

  @override
  String get employeeUnitLinkActivate => 'Reativar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivate => 'Arquivar nesta Unidade';

  @override
  String get employeeUnitLinkDeactivateReason => 'Motivo do arquivamento (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Arquivado nesta Unidade';

  @override
  String get employeeUnitLinkAbsent => 'Não vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidade';

  @override
  String get employeeUnitLinksEmpty => 'Este colaborador não tem vínculo com nenhuma Unidade que você pode consultar.';

  @override
  String get employeeUnitLinksError => 'Não foi possível carregar os vínculos.';

  @override
  String get outsourcedReportsError => 'Não foi possível carregar o relatório.';

  @override
  String get outsourcedReportsEmpty => 'Nenhuma empresa terceirizada/prestadora cadastrada.';

  @override
  String get outsourcedReportsActive => 'Ativos';

  @override
  String get outsourcedReportsArchived => 'Arquivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidade por Módulo';

  @override
  String get moduleVisibilityDescription => 'Permissões padrão: cada perfil possui permissões padrão definidas pelo sistema. Personalizações: o Administrador Geral pode personalizar a visualização e a utilização dos módulos por perfil e por unidade, sem alterar a estrutura padrão do sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle => 'Permissões padrão deste perfil';

  @override
  String get moduleVisibilityDefaultPanelHint => 'Estas permissões representam o comportamento padrão do sistema. As configurações abaixo permitem apenas personalizações realizadas pelo Administrador Geral.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Nenhum módulo por padrão';

  @override
  String get moduleVisibilityUnitLabel => 'Unidade';

  @override
  String get moduleVisibilityUnitHint => 'Um módulo não marcado especificamente para esta Unidade herda o valor de \"Todas as unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Todas as unidades (padrão)';

  @override
  String get stockTabAvailable => 'Disponíveis';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi => 'Selecione um EPI para ver os itens disponíveis';

  @override
  String get stockAvailableEmpty => 'Nenhum item disponível para este EPI nesta unidade';

  @override
  String get stockBlockedEmpty => 'Nenhum item bloqueado';

  @override
  String get stockNoOperationalUnit => 'Seu perfil não tem unidade operacional ativa. Fale com o administrador para liberar o acesso ao estoque.';

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
  String get deliveryEmployeeWithoutUnit => 'Colaborador sem Unidade operacional: não é possível registrar entrega.';

  @override
  String get deliveryQrOtherEpi => 'O código lido pertence a outro EPI.';

  @override
  String get stockUnitRequiredToMove => 'Selecione uma Unidade para movimentar o estoque.';

  @override
  String get stockAttentionSectionTitle => 'Estoque';

  @override
  String get stockAttentionCompanyTitle => 'Faixa de atenção — padrão da empresa';

  @override
  String get stockAttentionCompanyHelp => 'Aplica-se às Unidades que não definiram um percentual próprio. Não altera nenhuma Unidade já configurada.';

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
  String get stockAttentionRestored => 'Padrão da empresa removido. A empresa voltou ao padrão do sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Padrão do sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuração de estoque';

  @override
  String get stockConfigIntro => 'Defina estoque mínimo, faixa de atenção e monitoramento de alerta de um EPI em uma Unidade. Cada parâmetro é salvo separadamente.';

  @override
  String get stockConfigUnitLabel => 'Unidade a configurar';

  @override
  String get stockConfigSelectUnit => 'Selecione a Unidade para configurar os parâmetros.';

  @override
  String get stockConfigSelectEpi => 'Selecione o EPI para ver e editar os parâmetros desta Unidade.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError => 'Não foi possível carregar os EPIs desta Unidade.';

  @override
  String get stockConfigNoEpisInUnit => 'Nenhum EPI visível nesta Unidade.';

  @override
  String get stockConfigUnitBalance => 'Saldo na Unidade';

  @override
  String get stockConfigAttentionLimit => 'Limite da faixa de atenção';

  @override
  String get stockConfigUnderlyingStatus => 'Condição física';

  @override
  String get stockConfigDerivedUnavailable => 'Os valores calculados não puderam ser atualizados agora. Os parâmetros salvos acima estão corretos.';

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
  String get stockConfigMinimumHelp => 'Quantidade abaixo da qual o EPI é considerado crítico nesta Unidade. Vale só para esta Unidade.';

  @override
  String get stockConfigMinimumLabel => 'Estoque mínimo';

  @override
  String get stockConfigMinimumNegativeError => 'Informe um número inteiro maior ou igual a zero.';

  @override
  String get stockConfigMinimumSaved => 'Estoque mínimo salvo para esta Unidade.';

  @override
  String get stockConfigMinimumRestored => 'Estoque mínimo restaurado. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAttentionTitle => 'Faixa de atenção';

  @override
  String get stockConfigAttentionHelp => 'Percentual acima do mínimo em que o EPI já entra em atenção nesta Unidade. Independente do estoque mínimo.';

  @override
  String get stockConfigAttentionRangeError => 'O percentual deve estar entre 0 e 100.';

  @override
  String get stockConfigAttentionSaved => 'Faixa de atenção salva para esta Unidade.';

  @override
  String get stockConfigAttentionRestored => 'Faixa de atenção restaurada. A Unidade voltou a herdar o padrão da empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoramento de alerta';

  @override
  String get stockConfigAlertHelp => 'Desligar interrompe o alerta de estoque baixo e a reposição automática deste EPI nesta Unidade. Não altera saldo, mínimo nem percentual.';

  @override
  String get stockConfigAlertToggle => 'Monitorar o estoque deste EPI';

  @override
  String get stockConfigAlertPending => 'Alteração pendente. Clique em Salvar para aplicar.';

  @override
  String get stockConfigAlertDisableTitle => 'Desabilitar o alerta?';

  @override
  String get stockConfigAlertDisableBody => 'Este EPI deixará de gerar alerta de estoque baixo e reposição automática nesta Unidade. A condição física continuará sendo exibida.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desabilitar';

  @override
  String get stockConfigAlertSaved => 'Monitoramento de alerta salvo para esta Unidade.';

  @override
  String get stockConfigAlertRestored => 'Monitoramento restaurado. A Unidade voltou ao padrão do sistema.';

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
  String get stockAttentionLoadError => 'Não foi possível carregar o padrão da empresa.';

  @override
  String get unitSelectorLabel => 'Unidade';

  @override
  String get unitSelectorAllUnits => 'Todas as Unidades';

  @override
  String get unitSelectorLockedHint => 'Seu perfil opera numa Unidade fixa.';

  @override
  String get unitSelectorLoadError => 'Não foi possível carregar as Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned => 'Você não tem Unidade atribuída. Fale com o administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits => 'A empresa ainda não tem Unidades cadastradas.';

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
  String get settingsSelectCompanyFirst => 'Selecione uma empresa em Configurações para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPI';

  @override
  String get settingsFichaTileSubtitle => 'Título, declaração, observações e rastreabilidade';

  @override
  String get settingsStockTileSubtitle => 'Faixa de atenção padrão da empresa';

  @override
  String get settingsModulesTileSubtitle => 'Módulos visíveis por perfil e por Unidade';

  @override
  String get settingsArchivalTitle => 'Arquivamento e retenção';

  @override
  String get settingsArchivalSubtitle => 'Anos de preservação dos registros arquivados';

  @override
  String get settingsAppearanceTitle => 'Aparência e idioma';

  @override
  String get settingsAppearanceSubtitle => 'Tema da interface e idioma do aplicativo';

  @override
  String get settingsSubscriptionTileTitle => 'Minha Assinatura';

  @override
  String get settingsSubscriptionTileSubtitle => 'Plano, cobranças e cancelamento';

  @override
  String get settingsInvoicesTileTitle => 'Histórico Financeiro';

  @override
  String get settingsInvoicesTileSubtitle => 'Todas as cobranças e recibos';

  @override
  String get settingsNoPermission => 'Você não tem permissão para alterar esta configuração.';

  @override
  String get stockPhysicalValidityUnknown => 'Validade física desconhecida';

  @override
  String get stockNoPhysicalStock => 'Sem estoque físico';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validade física';

  @override
  String get stockRegularizeValiditySubtitle => 'Identifique a peça e informe a validade comprovada. A classificação é feita pelo sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR ou código da peça';

  @override
  String get stockRegularizeExpiryLabel => 'Validade física comprovada';

  @override
  String get stockRegularizeExpirySelect => 'Selecionar data';

  @override
  String get stockRegularizeEvidenceLabel => 'Evidência (documento ou registro verificável)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificativa';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete => 'Preencha a peça, a validade, a evidência e a justificativa.';

  @override
  String get stockRegularizeResultEligible => 'Validade regularizada. A peça está apta para entrega e reserva.';

  @override
  String get stockRegularizeResultBlocked => 'Validade regularizada. A peça está vencida e permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validade regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPIs distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(int valid, int expiring, int expired, int unknown) {
    return 'Peças físicas: válidas $valid, próximas $expiring, vencidas $expired, desconhecidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible => 'Item indisponível para entrega. Verifique validade física, status, reservas e saldo.';

  @override
  String get safetyTitle => 'Sikkerhetsbibliotek';

  @override
  String get safetyApproved => 'Godkjent verneutstyr';

  @override
  String get safetyRetry => 'Prøv igjen';

  @override
  String get safetyClose => 'Lukk';

  @override
  String get safetyCancel => 'Avbryt';

  @override
  String get safetyConfirm => 'Bekreft';

  @override
  String get safetyAccess => 'Fortsett';

  @override
  String get safetyPortalConfirm => 'Bekreft portaltilgang';

  @override
  String get safetyCpfLast => 'Tre siste CPF-sifre';

  @override
  String get safetyView => 'Vis';

  @override
  String get safetyFit => 'Tilpass';

  @override
  String get safetyZoomIn => 'Zoom inn';

  @override
  String get safetyZoomOut => 'Zoom ut';

  @override
  String get safetyNextPage => 'Neste side';

  @override
  String get safetyPreviousPage => 'Forrige side';

  @override
  String get safetyDocument => 'Dokument';

  @override
  String get safetyDetails => 'Detaljer';

  @override
  String get safetyRelatedDocuments => 'Tilknyttede dokumenter';

  @override
  String get safetyRelatedEpis => 'Tilknyttet verneutstyr';

  @override
  String get safetyRelatedEpi => 'Tilknyttet verneutstyr';

  @override
  String get safetyAllEpis => 'Alt verneutstyr';

  @override
  String get safetyAllCategories => 'Alle kategorier';

  @override
  String get safetyNoDocs => 'Ingen publiserte dokumenter for denne konteksten.';

  @override
  String get safetyNoRecords => 'Ingen publiserte, autoriserte oppføringer i denne konteksten.';

  @override
  String get safetyCatalogueNotice => 'Kataloggodkjenning angir ikke fysisk tilgjengelighet. CA-utløp er separat fra partiutløp.';

  @override
  String get safetyName => 'Verneutstyr';

  @override
  String get safetyManufacturer => 'Produsent';

  @override
  String get safetyModel => 'Modell/referanse';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'CA-utløp';

  @override
  String get safetyUsefulLife => 'Levetid (måneder)';

  @override
  String get safetyProtection => 'Beskyttelse';

  @override
  String get safetySection => 'Seksjon';

  @override
  String get safetyRecommendations => 'Anbefalinger/begrensninger';

  @override
  String get safetyUnknown => 'Ikke oppgitt';

  @override
  String get safetySearch => 'Søk';

  @override
  String get safetyViewEpi => 'Vis verneutstyr';

  @override
  String get safetyHistory => 'Historikk';

  @override
  String get safetyDocumentHistory => 'Dokumenthistorikk';

  @override
  String get safetyPublish => 'Publiser';

  @override
  String get safetyPublishVersion => 'Publiser versjon';

  @override
  String get safetyArchive => 'Arkiver dokument';

  @override
  String get safetyArchiveVersions => 'Arkiver dokument og versjoner';

  @override
  String get safetyReason => 'Begrunnelse kreves';

  @override
  String get safetyNew => 'Nytt dokument';

  @override
  String get safetyCreateNew => 'Opprett nytt dokument';

  @override
  String get safetyMetadata => 'Versjonsinformasjon';

  @override
  String get safetyEmptyAdmin => 'Ingen registrerte dokumenter.';

  @override
  String get safetyPrivateNotice => 'Private originaler, bevarte versjoner og historikk. Administrasjon begrenset til generell administrator og registeradministrator.';

  @override
  String get safetyAllowAdminDownloads => 'Tillat originalnedlasting for autoriserte administratorer';

  @override
  String get safetyPreviewOnlyNotice => 'Ansatte har alltid kun forhåndsvisning.';

  @override
  String get safetyPolicyReason => 'Endre administrativ nedlastingspolicy';

  @override
  String get safetySearchVersions => 'Søk i tittel eller versjon';

  @override
  String get safetyChooseFile => 'Velg fil';

  @override
  String get safetyFilePickerLabel => 'Sikkerhetsdokumenter';

  @override
  String get safetyUnitRequired => 'Velg minst én enhet';

  @override
  String get safetyAllUnits => 'Alle bedriftsenheter';

  @override
  String get safetyRequired => 'Påkrevd';

  @override
  String get safetyDocumentTitle => 'Tittel';

  @override
  String get safetyVersion => 'Versjon';

  @override
  String get safetyEffectiveDate => 'Gyldig fra (ÅÅÅÅ-MM-DD)';

  @override
  String get safetySectors => 'Kommaseparerte avdelinger (tomt = alle)';

  @override
  String get safetyActivities => 'Kommaseparerte aktiviteter/stillinger (tomt = alle)';

  @override
  String get safetyUpload => 'Registrer dokument eller versjon';

  @override
  String get safetyRendering => 'Genererer trygg forhåndsvisning…';

  @override
  String get safetyFileLimit => 'Velg en fil på opptil 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versjon $version · Gyldig fra $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Visningsenhet: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Forhåndsvisning utilgjengelig: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Opplasting avvist; forhåndsvisning utilgjengelig: $error';
  }

  @override
  String safetyVersionSummary(String version, String revision, String state, String date) {
    return 'Versjon $version / revisjon $revision · $state · Gyldig fra $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Ansvarlig $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Bruksmatrise for verneutstyr';

  @override
  String get safetyCategoryGlove => 'Hanskematrise';

  @override
  String get safetyCategoryCare => 'Veiledninger for rengjøring og vedlikehold';

  @override
  String get safetyCategoryUse => 'Bruksanvisninger for verneutstyr';

  @override
  String get safetyCategoryTechnical => 'Håndbøker og tekniske datablad';

  @override
  String get safetyCategoryOther => 'Andre sikkerhetsdokumenter';

  @override
  String get safetyStateDraft => 'Utkast';

  @override
  String get safetyStatePublished => 'Publisert';

  @override
  String get safetyStateSuperseded => 'Erstattet';

  @override
  String get safetyStateArchived => 'Arkivert';
  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linha $line — $item (item #$id): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';
  }
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


}

/// The translations for Norwegian, as used in Norway (`no_NO`).
class AppLocalizationsNoNo extends AppLocalizationsNo {
  AppLocalizationsNoNo(): super('no_NO');

  @override
  String get appName => 'EPI Kontroll';

  @override
  String get loading => 'Laster...';

  @override
  String get save => 'Lagre';

  @override
  String get cancel => 'Avbryt';

  @override
  String get reportsExportPdf => 'Eksporter PDF';

  @override
  String get feedbackForward => 'Videresend';

  @override
  String get feedbackReject => 'Avvis';

  @override
  String get feedbackApprove => 'Godkjenn';

  @override
  String get feedbackJustification => 'Begrunnelse';

  @override
  String get feedbackRejectReason => 'Avslagsgrunn';

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
  String get employeeCpfLabel => 'CPF';

  @override
  String get employeeSectorLabel => 'Avdeling';

  @override
  String get employeeRoleLabel => 'Stilling';

  @override
  String get employeeUnitLabel => 'Enhet';

  @override
  String get employeeUnitLockedHint => 'Enhet fastsatt av din tilgangsprofil.';

  @override
  String get employeeLegalEntityLabel => 'CNPJ';

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
  String get episSearchHint => 'Søk etter navn, CE-merking eller kode';

  @override
  String get epiNameLabel => 'PVU-navn';

  @override
  String get epiCodeLabel => 'Innkjøpskode';

  @override
  String get epiCaLabel => 'CE-nr.';

  @override
  String get epiSectorLabel => 'Sektor';

  @override
  String get epiSectionLabel => 'Verneutstyr-seksjon';

  @override
  String get epiModelLabel => 'Modell/referanse';

  @override
  String get epiManufacturerLabel => 'Produsent';

  @override
  String get epiSupplierLabel => 'Leverandør';

  @override
  String get epiUnitMeasureLabel => 'Måleenhet';

  @override
  String get epiValidityDateLabel => 'Gyldighetsdato';

  @override
  String get epiManufacturerValidityLabel => 'Gyldighet (måneder)';

  @override
  String get epiCaExpiryLabel => 'CE-merking utløper';

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
  String get deliveryOfflineQueued => 'Utlevering lagret — synkroniseres ved tilkobling';

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
  String get purchaseOrdersTitle => 'Innkjøpsordrer';

  @override
  String get poApprove => 'Godkjenn';

  @override
  String get poReceive => 'Motta';

  @override
  String get poQuantityReceived => 'Mottatt ant.';

  @override
  String get poReceiveNotes => 'Merknad';

  @override
  String get poManufacturerValidity => 'Produsentgyldighet';

  @override
  String get poManufacturerValidityHint => 'Angi dato';

  @override
  String get poManufacturerValidityRequired => 'Angi produsentgyldighet for alt mottatt verneutstyr.';

  @override
  String get poOcrDateNotFound => 'Kunne ikke lese datoen. Prøv igjen.';

  @override
  String get poOcrCameraFailed => 'Kameralesing mislyktes.';

  @override
  String get poPickDate => 'Velg dato';

  @override
  String get poReadDateCamera => 'Les dato med kamera (OCR)';

  @override
  String get poCheck => 'Kontroller';

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
  String get portalSignatureInstruction => 'Signer i feltet nedenfor for å bekrefte mottak';

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
  String get employeeContactErrorNoApp => 'Ingen app tilgjengelig for å åpne denne lenken';

  @override
  String get employeeContactErrorGeneric => 'Kunne ikke kontakte ansatt. Vennligst prøv igjen.';

  @override
  String get employeeContactPdfError => 'Kunne ikke laste ned PDF. Vennligst prøv igjen.';

  @override
  String get offlineBanner => 'Frakoblet — data lagret lokalt';

  @override
  String get syncingBanner => 'Synkroniserer data...';

  @override
  String get syncDone => 'Data synkronisert';

  @override
  String get searchEmployeeHint => 'Søk etter ansatt...';

  @override
  String get searchEpiHint => 'Søk etter PVU...';

  @override
  String get fieldQuantity => 'Antall';

  @override
  String get filterAll => 'Alle';

  @override
  String deliveryStockAvailable(int qty) {
    return 'Lager: $qty';
  }

  @override
  String get deliveryDateLabel => 'Leveringsdato';

  @override
  String get deliveryNextReplacement => 'Neste utskifting';

  @override
  String deliveryDateValue(String date) {
    return 'Dato: $date';
  }

  @override
  String get returnSelectDelivery => 'Velg levering som skal returneres';

  @override
  String returnDeliveredInfo(String date, int qty) {
    return 'Levert $date · Antall: $qty';
  }

  @override
  String get returnConditionTitle => 'PVU-tilstand';

  @override
  String get returnDestinationTitle => 'Destinasjon';

  @override
  String get returnDestDiscard => 'Kassering';

  @override
  String get returnDestRepair => 'Vedlikehold';

  @override
  String get returnDestStock => 'Tilbake til lager';

  @override
  String get returnSubmit => 'Registrer retur';

  @override
  String returnDeliveryDateInfo(String date) {
    return 'Levering: $date';
  }

  @override
  String returnQuantityInfo(int qty) {
    return 'Antall: $qty';
  }

  @override
  String get purchaseTitleLabel => 'Tittel på forespørsel';

  @override
  String get purchaseSelectUnit => 'Velg en enhet';

  @override
  String get purchaseItemsTitle => 'Forespørselens varer';

  @override
  String get purchaseAddEpi => 'Legg til PVU';

  @override
  String get purchaseNoItems => 'Ingen varer lagt til';

  @override
  String get purchaseCreate => 'Opprett forespørsel';

  @override
  String get purchaseAddAtLeastOne => 'Legg til minst én vare';

  @override
  String get purchaseQuantityColon => 'Antall:';

  @override
  String purchaseItemsCount(int count) {
    return '$count varer';
  }

  @override
  String get purchaseStatusAwaiting => 'Venter';

  @override
  String get purchaseStatusCorrection => 'Korrigering forespurt';

  @override
  String get purchaseStatusAwaitingReceipt => 'Venter på mottak';

  @override
  String get purchaseStatusCompleted => 'Fullført';

  @override
  String get purchaseStatusCancelled => 'Kansellert';

  @override
  String get suppliersTitle => 'Leverandører';

  @override
  String get supplierNew => 'Ny leverandør';

  @override
  String get supplierEdit => 'Rediger leverandør';

  @override
  String get supplierCnpjLabel => 'CNPJ (org.nr.)';

  @override
  String get supplierPhoneLabel => 'Telefon';

  @override
  String get supplierPaymentTermsLabel => 'Betalingsbetingelser';

  @override
  String get supplierIntegrationLevelLabel => 'Integrasjonsnivå';

  @override
  String get supplierInactiveLabel => 'Inaktiv';

  @override
  String get supplierCatalogTitle => 'Leverandørkatalog';

  @override
  String get catalogNewProduct => 'Nytt produkt';

  @override
  String get catalogSkuLabel => 'SKU';

  @override
  String get catalogDescriptionLabel => 'Beskrivelse';

  @override
  String get catalogLastPriceLabel => 'Siste pris';

  @override
  String get catalogLeadTimeLabel => 'Leveringstid (dager)';

  @override
  String get quotesTitle => 'Tilbud';

  @override
  String get quotesNew => 'Nytt tilbud';

  @override
  String get quotesSelectSuppliers => 'Velg leverandører';

  @override
  String get quoteSendEmail => 'Send på e-post';

  @override
  String get quoteSendPortal => 'Send via portal';

  @override
  String get quoteAnswerAction => 'Registrer svar';

  @override
  String get quoteSelectWinner => 'Velg vinner';

  @override
  String get quoteComparisonTitle => 'Tilbudssammenligning';

  @override
  String get quoteFreightLabel => 'Frakt';

  @override
  String get quoteUnitPriceLabel => 'Enhetspris';

  @override
  String get quoteDeclinedLabel => 'Avslått';

  @override
  String get quoteBestPriceLabel => 'Beste pris';

  @override
  String get quoteBestLeadTimeLabel => 'Beste leveringstid';

  @override
  String get quoteCreatePo => 'Opprette PO fra vinnertilbudet?';

  @override
  String get poSupplierActionsTitle => 'Leverandør og levering';

  @override
  String get poSendToSupplier => 'Send til leverandør';

  @override
  String get poPortalLinkAction => 'Send portallenke';

  @override
  String get poRegisterConfirmation => 'Registrer bekreftelse';

  @override
  String get poTrackingTitle => 'Sporing';

  @override
  String get poDeliveryForecastLabel => 'Forventet levering';

  @override
  String get poCarrierLabel => 'Transportør';

  @override
  String get poTrackingCodeLabel => 'Sporingskode';

  @override
  String get commentLabel => 'Kommentar';

  @override
  String get actionSentSuccess => 'Sendt vellykket';

  @override
  String get myCompanyTitle => 'Mitt Firma';

  @override
  String get myCompanySubtitle => 'Firmaets data, visuelle identitet og domene';

  @override
  String get myCompanySaved => 'Firmainnstillingene ble lagret.';

  @override
  String get myCompanyLoadError => 'Kunne ikke laste firmadata.';

  @override
  String get myCompanyContractSection => 'Kontrakt (skrivebeskyttet)';

  @override
  String get myCompanyPlan => 'Plan';

  @override
  String get myCompanyUserLimit => 'Brukergrense';

  @override
  String get myCompanyLicense => 'Lisens';

  @override
  String get myCompanyRegistrationSection => 'Registreringsdata';

  @override
  String get myCompanyName => 'Firmanavn';

  @override
  String get myCompanyLegalName => 'Juridisk navn';

  @override
  String get myCompanyCnpj => 'CNPJ';

  @override
  String get myCompanyStateRegistration => 'Statlig registrering';

  @override
  String get myCompanyMunicipalRegistration => 'Kommunal registrering';

  @override
  String get myCompanyAddress => 'Adresse';

  @override
  String get myCompanyPhone => 'Telefon';

  @override
  String get myCompanyWhatsapp => 'WhatsApp';

  @override
  String get myCompanyEmail => 'Firma-e-post';

  @override
  String get myCompanyWebsite => 'Nettsted';

  @override
  String get myCompanyIdentitySection => 'Identitet og tema';

  @override
  String get myCompanyDisplayName => 'Visningsnavn i systemet';

  @override
  String get myCompanyInstitutionalMessage => 'Institusjonell melding';

  @override
  String get myCompanyPrimaryColor => 'Primærfarge (hex)';

  @override
  String get myCompanySecondaryColor => 'Sekundærfarge (hex)';

  @override
  String get myCompanyPreferencesSection => 'Preferanser';

  @override
  String get myCompanyTimezone => 'Tidssone';

  @override
  String get myCompanySave => 'Lagre firmainnstillinger';

  @override
  String get myCompanyDomainsSection => 'Domener';

  @override
  String get myCompanyDomainField => 'Domene';

  @override
  String get myCompanyDomainTypePlatform => 'Plattformens underdomene';

  @override
  String get myCompanyDomainTypeCustomSub => 'Tilpasset underdomene';

  @override
  String get myCompanyDomainTypeCustom => 'Tilpasset domene';

  @override
  String get myCompanyDomainAdd => 'Registrer domene';

  @override
  String get myCompanyDomainVerify => 'Verifiser';

  @override
  String get myCompanyDomainDelete => 'Fjern';

  @override
  String get myCompanyDomainPending => 'Venter';

  @override
  String get myCompanyDomainVerified => 'Verifisert';

  @override
  String get myCompanyDomainFailed => 'Mislyktes';

  @override
  String get myCompanyDomainPrimary => 'Primær';

  @override
  String get myCompanyDomainCname => 'Pek CNAME til';

  @override
  String get myCompanyDomainTxt => 'Opprett TXT-oppføringen';

  @override
  String get myCompanyDomainToken => 'TXT-verdi';

  @override
  String get epiArchiveBlockTitle => 'Arkiver med lagersperring';

  @override
  String get epiArchiveBlockBody => 'Dette verneutstyret har tilgjengelig lager eller aktive koblinger. Ved bekreftelse flyttes tilgjengelig lager til Sperret lager (sporbart) og utstyret arkiveres.';

  @override
  String get epiArchiveBlockConfirm => 'Sperr lager og arkiver';

  @override
  String get epiArchiveReasonLabel => 'Årsak til arkivering (revisjon)';

  @override
  String get epiArchiveReasonRequired => 'Oppgi en årsak for å fortsette.';

  @override
  String get epiArchiveBlockableLabel => 'Lager som sperres';

  @override
  String get epiArchiveLiveLinksTitle => 'Aktive koblinger';

  @override
  String get epiArchiveAvailable => 'Tilgjengelig';

  @override
  String get epiArchiveInTransit => 'Under transport';

  @override
  String get epiArchiveInPossession => 'I bruk';

  @override
  String get epiArchivePendingRequests => 'Åpne forespørsler';

  @override
  String get epiArchivePendingPurchase => 'Åpne innkjøp';

  @override
  String get dashboardComplianceTitle => 'Lagersamsvar';

  @override
  String get dashboardComplianceAllOk => 'Lager i samsvar';

  @override
  String get complianceCaExpired => 'CA utløpt';

  @override
  String get complianceCaExpiring => 'CA utløper snart';

  @override
  String get complianceProductExpired => 'Produkt utløpt';

  @override
  String get complianceProductExpiring => 'Produkt utløper snart';

  @override
  String get complianceMissingManufacture => 'Uten produksjonsdato';

  @override
  String get complianceMissingLot => 'Uten parti';

  @override
  String get complianceAdminBlocked => 'Sperret';

  @override
  String get handoverTitle => 'Utleveringskontroll';

  @override
  String get handoverPrompt => 'Skann leverings-QR eller skriv inn koden.';

  @override
  String get handoverCodeLabel => 'Leveringskode';

  @override
  String get handoverLookupButton => 'Søk levering';

  @override
  String get handoverScanButton => 'Skann QR';

  @override
  String get handoverConfirmButton => 'Bekreft mottak';

  @override
  String get handoverConfirmedTitle => 'Mottak bekreftet';

  @override
  String get handoverAlreadyConfirmed => 'Denne leveringen er allerede bekreftet.';

  @override
  String get handoverNotFound => 'Ingen levering funnet for denne koden.';

  @override
  String get handoverConfirmError => 'Kunne ikke bekrefte mottak.';

  @override
  String get handoverEmployeeLabel => 'Ansatt';

  @override
  String get handoverEpiLabel => 'Verneutstyr';

  @override
  String get handoverQuantityLabel => 'Antall';

  @override
  String get handoverSectorLabel => 'Sektor';

  @override
  String get handoverRoleLabel => 'Rolle';

  @override
  String get handoverUnitLabel => 'Enhet';

  @override
  String get handoverDeliveryDateLabel => 'Leveringsdato';

  @override
  String get handoverReceiverNameLabel => 'Mottakerens navn (valgfritt)';

  @override
  String get handoverScanAgain => 'Ny kontroll';

  @override
  String get legalEntitiesTitle => 'CNPJ';

  @override
  String get legalEntitiesNew => 'Ny CNPJ';

  @override
  String get legalEntityLegalNameLabel => 'Juridisk navn';

  @override
  String get legalEntityTradeNameLabel => 'Handelsnavn';

  @override
  String get legalEntityTypeLabel => 'Type';

  @override
  String get legalEntityInactiveBadge => 'Inaktiv';

  @override
  String get legalEntityDeactivate => 'Deaktiver CNPJ';

  @override
  String get legalEntityDeactivateHint => 'Juridisk historikk bevares. CNPJ brukes ikke i nye operasjoner.';

  @override
  String get legalEntityShowInactive => 'Vis inaktive';

  @override
  String get legalEntitiesEmpty => 'Ingen CNPJ registrert.';

  @override
  String get legalEntityMunicipalityLabel => 'Kommune';

  @override
  String get legalEntityCnpjLabel => 'CNPJ (brasiliansk org.nr.)';

  @override
  String get legalEntityUfLabel => 'Delstat';

  @override
  String get legalEntitiesImportColumnsHint => 'Org.nr.\tJuridisk navn\tHandelsnavn\tType';

  @override
  String get legalEntitiesImport => 'Importer regneark';

  @override
  String get legalEntitiesImportHint => 'Kopier radene fra regnearket (med overskriftsraden) og lim inn nedenfor. Godtar kolonner på portugisisk eller engelsk.';

  @override
  String get legalEntitiesImportResult => 'Import fullført';

  @override
  String get dashboardFilterLegalEntity => 'CNPJ';

  @override
  String get dashboardFilterUnit => 'Enhet';

  @override
  String get dashboardFilterSector => 'Sektor';

  @override
  String get dashboardFilterAll => 'Alle';

  @override
  String get dashboardFilterClear => 'Tøm filtre';

  @override
  String get legalEntityTransferTitle => 'Overfør juridisk tilknytning';

  @override
  String get legalEntityTransferHint => 'CNPJ er tilknytningen til arbeidsavtalen og endres ikke ved enhetsoverføring. Endringen revideres og krever en begrunnelse.';

  @override
  String get legalEntityTransferReason => 'Begrunnelse';

  @override
  String get legalEntityTransferTarget => 'Ny CNPJ';

  @override
  String get legalEntityTransferAction => 'Overfør';

  @override
  String get legalEntityTransferHistory => 'Tilknytningshistorikk';

  @override
  String get unitTransferTitle => 'Overfør enhet';

  @override
  String get unitTransferHint => 'Bevegelse av driftsenhet — midlertidig eller permanent. Oppretter en sporbar hendelse og endrer ikke medarbeiderens CNPJ.';

  @override
  String get unitTransferTarget => 'Målenhet';

  @override
  String get unitTransferType => 'Bevegelsestype';

  @override
  String get unitTransferTypeTemporary => 'Midlertidig';

  @override
  String get unitTransferTypeDefinitive => 'Permanent';

  @override
  String get unitTransferStartDate => 'Startdato';

  @override
  String get unitTransferEndDate => 'Sluttdato (valgfritt)';

  @override
  String get unitTransferNotes => 'Merknad (valgfritt)';

  @override
  String get unitTransferAction => 'Overfør';

  @override
  String get myCompanyStockScope => 'Konsolider lagersaldo etter';

  @override
  String get myCompanyStockScopeHint => 'Denne innstillingen endrer bare den konsoliderte visningen av saldoer. Innganger, reservasjoner, uttak, utleveringer og andre bevegelser forblir knyttet til lageret i hver enhet.';

  @override
  String get myCompanyStockScopeUnit => 'Enhet';

  @override
  String get myCompanyStockScopeLegalEntity => 'CNPJ';

  @override
  String get myCompanyStockScopeCompany => 'Selskap';

  @override
  String get navLegalEntities => 'CNPJ';

  @override
  String get unitLegalEntityLabel => 'Ansvarlig CNPJ';

  @override
  String get unitLegalEntityHint => 'Juridisk enhet som er ansvarlig for driften og lageret til denne enheten.';

  @override
  String get employeeEmploymentTypeLabel => 'Ansettelsestype';

  @override
  String get employeeSourceCompanyLabel => 'Opprinnelsesselskap';

  @override
  String get employeeSourceCompanyHint => 'Navn på den ansattes opprinnelsesselskap';

  @override
  String get employmentTypeClt => 'CLT';

  @override
  String get employmentTypeOutsourced => 'Utkontraktert';

  @override
  String get employmentTypeTemporary => 'Midlertidig';

  @override
  String get employmentTypeServiceProvider => 'Tjenesteleverandør';

  @override
  String get employmentTypeApprentice => 'Ung lærling';

  @override
  String get employmentTypeTrainee => 'Hospitant';

  @override
  String get employmentTypeIntern => 'Praktikant';

  @override
  String get navTerceirizados => 'Underleverandører og Tjenesteytere';

  @override
  String get outsourcedCompaniesTitle => 'Underleverandører og Tjenesteytere';

  @override
  String get outsourcedCompaniesEmpty => 'Ingen underleverandør registrert.';

  @override
  String get outsourcedCompaniesSearchHint => 'Søk etter navn eller CNPJ';

  @override
  String get outsourcedCompanyNew => 'Nytt selskap';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Firmanavn';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Handelsnavn';

  @override
  String get outsourcedCompanyCnpjLabel => 'CNPJ';

  @override
  String get outsourcedCompanyCnpjHint => 'Valgfritt i Forenklet Registrering';

  @override
  String get outsourcedCompanyKindLabel => 'Selskapstype';

  @override
  String get outsourcedCompanyKindOutsourced => 'Underleverandør';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Tjenesteyter';

  @override
  String get outsourcedCompanyKindOther => 'Annet';

  @override
  String get outsourcedCompanyResponsibilityLabel => 'Ansvar for Levering av Verneutstyr';

  @override
  String get outsourcedCompanyUnitLabel => 'Enhet';

  @override
  String get outsourcedCompanyUnitAll => 'Alle enheter (standard)';

  @override
  String get outsourcedCompanyLinkTitle => 'Knytt selskap til denne enheten';

  @override
  String get outsourcedCompanyLinkHint => 'Søk etter selskap som allerede er registrert i tenanten…';

  @override
  String get outsourcedCompanyLinkSectionLinked => 'Allerede knyttet til denne enheten';

  @override
  String get outsourcedCompanyLinkSectionAvailable => 'Tilgjengelige for tilknytning';

  @override
  String get outsourcedCompanyLinkLink => 'Knytt til denne enheten';

  @override
  String get outsourcedCompanyLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivateReason => 'Årsak til arkivering (valgfritt):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Brukt av $count enhet(er)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Opprinnelsesenhet';

  @override
  String get outsourcedCompanyLinkEmpty => 'Fant ingen selskaper for dette søket.';

  @override
  String get outsourcedCompanyLinkNotInformed => 'Tilknytning ikke oppgitt for profilen din';

  @override
  String get outsourcedCompanyStatusLabel => 'Status';

  @override
  String get outsourcedCompanySave => 'Lagre';

  @override
  String get outsourcedCompanyCancel => 'Avbryt';

  @override
  String get outsourcedCompanyPromote => 'Oppgrader til Standard Registrering';

  @override
  String get outsourcedCompanyPromoteConfirmTitle => 'Oppgradere til Standard Registrering?';

  @override
  String get outsourcedCompanyPromoteConfirmBody => 'Selskapet vil bli behandlet som Standard Registrering. Et CNPJ kreves.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Forenklet';

  @override
  String get outsourcedCompanyStandardBadge => 'Standard';

  @override
  String get outsourcedTabCompanies => 'Selskaper';

  @override
  String get outsourcedTabEmployees => 'Registrering av Medarbeidere';

  @override
  String get outsourcedTabReports => 'Rapporter';

  @override
  String get outsourcedShowActive => 'Vis aktive';

  @override
  String get outsourcedShowArchived => 'Vis arkiverte';

  @override
  String get archive => 'Arkiver';

  @override
  String get restore => 'Gjenopprett';

  @override
  String get archivedAt => 'Arkivert den';

  @override
  String get archiveReasonLabel => 'Årsak til arkivering (revisjon)';

  @override
  String get outsourcedCompanyArchive => 'Arkiver selskap';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => 'Arkivere dette selskapet?';

  @override
  String get outsourcedCompanyRestore => 'Gjenopprett';

  @override
  String get outsourcedCompanyRestoreConfirmTitle => 'Gjenopprette dette selskapet?';

  @override
  String get outsourcedCompaniesArchivedEmpty => 'Ingen arkiverte innleide selskaper.';

  @override
  String get outsourcedEmployeeNew => 'Ny medarbeider';

  @override
  String get outsourcedEmployeesEmpty => 'Ingen innleide/tjenesteytende medarbeidere registrert.';

  @override
  String get outsourcedEmployeesArchivedEmpty => 'Ingen arkiverte innleide/tjenesteytende medarbeidere.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Innleid/tjenesteytende selskap';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel => 'Registreringsnummer hos opprinnelig arbeidsgiver';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Adgangskort';

  @override
  String get outsourcedEmployeeNotesLabel => 'Merknader';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle => 'Arkivere denne medarbeideren?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle => 'Gjenopprette denne medarbeideren?';

  @override
  String get employeeUnitLinkColumn => 'Lokal tilknytning';

  @override
  String get employeeUnitLink => 'Knytt til min enhet';

  @override
  String get employeeUnitLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivateReason => 'Årsak til arkivering (valgfritt):';

  @override
  String get employeeUnitLinkActive => 'Tilknyttet';

  @override
  String get employeeUnitLinkArchived => 'Arkivert i denne enheten';

  @override
  String get employeeUnitLinkAbsent => 'Ikke tilknyttet';

  @override
  String get employeeUnitLinksTitle => 'Tilknytninger per enhet';

  @override
  String get employeeUnitLinksEmpty => 'Denne medarbeideren har ingen tilknytning til noen enhet du kan se.';

  @override
  String get employeeUnitLinksError => 'Kunne ikke laste tilknytningene.';

  @override
  String get outsourcedReportsError => 'Kunne ikke laste rapporten.';

  @override
  String get outsourcedReportsEmpty => 'Ingen innleide/tjenesteytende selskaper registrert.';

  @override
  String get outsourcedReportsActive => 'Aktive';

  @override
  String get outsourcedReportsArchived => 'Arkiverte';

  @override
  String get moduleVisibilityTitle => 'Modulsynlighet';

  @override
  String get moduleVisibilityDescription => 'Standardtillatelser: hver rolle har standardtillatelser definert av systemet. Tilpasninger: Hovedadministratoren kan tilpasse synlighet og bruk av moduler per rolle og per enhet, uten å endre systemets standardstruktur.';

  @override
  String get moduleVisibilityRoleLabel => 'Rolle';

  @override
  String get moduleVisibilityDefaultPanelTitle => 'Standardtillatelser for denne rollen';

  @override
  String get moduleVisibilityDefaultPanelHint => 'Disse tillatelsene representerer systemets standardoppførsel. Innstillingene nedenfor tillater kun tilpasninger utført av Hovedadministratoren.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ingen moduler som standard';

  @override
  String get moduleVisibilityUnitLabel => 'Enhet';

  @override
  String get moduleVisibilityUnitHint => 'En modul som ikke er spesifikt satt for denne Enheten, arver verdien fra \"Alle enheter\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Alle enheter (standard)';

  @override
  String get stockTabAvailable => 'Tilgjengelige';

  @override
  String get stockTabBlocked => 'Blokkerte';

  @override
  String get stockAvailableSelectEpi => 'Velg et PVU for å se tilgjengelige varer';

  @override
  String get stockAvailableEmpty => 'Ingen tilgjengelige varer for dette PVU-et ved denne enheten';

  @override
  String get stockBlockedEmpty => 'Ingen blokkerte varer';

  @override
  String get stockNoOperationalUnit => 'Profilen din har ingen aktiv driftsenhet. Kontakt en administrator for å få tilgang til lageret.';

  @override
  String get stockItemLotLabel => 'Parti';

  @override
  String get stockStatusBlockedExpired => 'Utløpt';

  @override
  String get stockStatusBlockedDiscard => 'Venter på kassering';

  @override
  String get stockStatusBlockedReturn => 'Venter på retur til leverandør';

  @override
  String get stockStatusBlockedAnalysis => 'Til analyse';

  @override
  String get stockStatusBlockedRejected => 'Avvist';

  @override
  String get stockStatusBlockedArchived => 'Arkivert PVU';

  @override
  String get stockStatusUnknown => 'Ukjent status';

  @override
  String get stockUnitBalanceSuffix => 'ved denne enheten';

  @override
  String get stockCompanyBalanceLabel => 'selskap';

  @override
  String get stockMinimumShort => 'min';

  @override
  String get deliveryStepItem => 'Enhet';

  @override
  String get deliveryItemTitle => 'Velg den merkede enheten';

  @override
  String get deliveryItemEmpty => 'Ingen enhet tilgjengelig i denne Enheten.';

  @override
  String get deliveryItemScan => 'Skann QR for enheten';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Lager i Enheten: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit => 'Ansatt uten operativ Enhet: levering kan ikke registreres.';

  @override
  String get deliveryQrOtherEpi => 'Den skannede koden tilhører et annet verneutstyr.';

  @override
  String get stockUnitRequiredToMove => 'Velg en Enhet for å flytte lager.';

  @override
  String get stockAttentionSectionTitle => 'Lager';

  @override
  String get stockAttentionCompanyTitle => 'Varselintervall — selskapets standard';

  @override
  String get stockAttentionCompanyHelp => 'Gjelder enheter som ikke har angitt sin egen prosent. Endrer ingen enhet som allerede er konfigurert.';

  @override
  String get stockAttentionPercentageLabel => 'Prosent for varselintervall';

  @override
  String get stockAttentionOriginLabel => 'Kilde';

  @override
  String get stockAttentionOriginCompany => 'Angitt av selskapet';

  @override
  String get stockAttentionOriginSystem => 'Systemstandard';

  @override
  String get stockAttentionSave => 'Lagre selskapets standard';

  @override
  String get stockAttentionRestore => 'Gjenopprett systemstandard';

  @override
  String get stockAttentionSaved => 'Selskapets standard er lagret.';

  @override
  String get stockAttentionRestored => 'Selskapets standard er fjernet. Selskapet er tilbake på systemstandarden.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Systemstandard: $value %';
  }

  @override
  String get stockConfigTitle => 'Lagerkonfigurasjon';

  @override
  String get stockConfigIntro => 'Angi minimumslager, varselintervall og varselovervåking for ett verneutstyr i én enhet. Hver parameter lagres for seg.';

  @override
  String get stockConfigUnitLabel => 'Enhet som skal konfigureres';

  @override
  String get stockConfigSelectUnit => 'Velg enheten for å konfigurere parameterne.';

  @override
  String get stockConfigSelectEpi => 'Velg verneutstyret for å se og endre parameterne for denne enheten.';

  @override
  String get stockConfigEpiLabel => 'Verneutstyr';

  @override
  String get stockConfigEpisLoadError => 'Kunne ikke laste listen over verneutstyr for denne enheten.';

  @override
  String get stockConfigNoEpisInUnit => 'Ingen verneutstyr er synlig i denne enheten.';

  @override
  String get stockConfigUnitBalance => 'Saldo i enheten';

  @override
  String get stockConfigAttentionLimit => 'Grense for varselintervall';

  @override
  String get stockConfigUnderlyingStatus => 'Fysisk tilstand';

  @override
  String get stockConfigDerivedUnavailable => 'De beregnede verdiene kunne ikke oppdateres nå. Parameterne som er lagret over, er riktige.';

  @override
  String get stockConfigStatusCritical => 'Kritisk';

  @override
  String get stockConfigStatusNearMinimum => 'Nær minimum';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Varsel deaktivert';

  @override
  String get stockConfigMinimumTitle => 'Minimumslager';

  @override
  String get stockConfigMinimumHelp => 'Antall under hvilket verneutstyret regnes som kritisk i denne enheten. Gjelder bare denne enheten.';

  @override
  String get stockConfigMinimumLabel => 'Minimumslager';

  @override
  String get stockConfigMinimumNegativeError => 'Skriv inn et heltall lik eller større enn null.';

  @override
  String get stockConfigMinimumSaved => 'Minimumslager lagret for denne enheten.';

  @override
  String get stockConfigMinimumRestored => 'Minimumslager tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAttentionTitle => 'Varselintervall';

  @override
  String get stockConfigAttentionHelp => 'Prosent over minimum der verneutstyret allerede går i varsel i denne enheten. Uavhengig av minimumslageret.';

  @override
  String get stockConfigAttentionRangeError => 'Prosenten må være mellom 0 og 100.';

  @override
  String get stockConfigAttentionSaved => 'Varselintervall lagret for denne enheten.';

  @override
  String get stockConfigAttentionRestored => 'Varselintervall tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAlertTitle => 'Varselovervåking';

  @override
  String get stockConfigAlertHelp => 'Å slå den av stopper varsel om lavt lager og automatisk etterfylling for dette verneutstyret i denne enheten. Det endrer verken saldo, minimum eller prosent.';

  @override
  String get stockConfigAlertToggle => 'Overvåk lageret for dette verneutstyret';

  @override
  String get stockConfigAlertPending => 'Ulagret endring. Klikk Lagre for å bruke den.';

  @override
  String get stockConfigAlertDisableTitle => 'Deaktivere varselet?';

  @override
  String get stockConfigAlertDisableBody => 'Dette verneutstyret slutter å gi varsel om lavt lager og automatisk etterfylling i denne enheten. Den fysiske tilstanden vises fortsatt.';

  @override
  String get stockConfigAlertDisableConfirm => 'Deaktiver';

  @override
  String get stockConfigAlertSaved => 'Varselovervåking lagret for denne enheten.';

  @override
  String get stockConfigAlertRestored => 'Overvåking tilbakestilt. Enheten er tilbake på systemstandarden.';

  @override
  String get stockConfigOriginUnit => 'Angitt av denne enheten';

  @override
  String get stockConfigOriginCompany => 'Arvet fra selskapets standard';

  @override
  String get stockConfigOriginUnknown => 'Ikke oppgitt';

  @override
  String get stockConfigSave => 'Lagre';

  @override
  String get stockConfigRestore => 'Gjenopprett arv';

  @override
  String stockAttentionRangeError(int max) {
    return 'Oppgi en heltallsprosent mellom 0 og $max.';
  }

  @override
  String get stockAttentionLoadError => 'Kunne ikke laste selskapets standard.';

  @override
  String get unitSelectorLabel => 'Enhet';

  @override
  String get unitSelectorAllUnits => 'Alle enheter';

  @override
  String get unitSelectorLockedHint => 'Profilen din opererer i en fast enhet.';

  @override
  String get unitSelectorLoadError => 'Kunne ikke laste enhetene.';

  @override
  String get unitSelectorNoUnitsAssigned => 'Du har ingen enhet tildelt. Kontakt administratoren.';

  @override
  String get unitSelectorCompanyHasNoUnits => 'Selskapet har ennå ingen enheter registrert.';

  @override
  String get settingsSectionCompany => 'Selskap';

  @override
  String get settingsSectionOperation => 'Drift';

  @override
  String get settingsSectionSubscription => 'Abonnement';

  @override
  String get settingsCompanyLabel => 'Selskap';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Administrerer selskapet: $name';
  }

  @override
  String get settingsSelectCompanyFirst => 'Velg et selskap i Innstillinger for å fortsette.';

  @override
  String get settingsFichaTileTitle => 'PVU-skjema';

  @override
  String get settingsFichaTileSubtitle => 'Tittel, erklæring, merknader og sporbarhet';

  @override
  String get settingsStockTileSubtitle => 'Selskapets standard varselgrense';

  @override
  String get settingsModulesTileSubtitle => 'Moduler synlige per profil og per enhet';

  @override
  String get settingsArchivalTitle => 'Arkivering og oppbevaring';

  @override
  String get settingsArchivalSubtitle => 'År arkiverte poster bevares';

  @override
  String get settingsAppearanceTitle => 'Utseende og språk';

  @override
  String get settingsAppearanceSubtitle => 'Grensesnittstema og appspråk';

  @override
  String get settingsSubscriptionTileTitle => 'Mitt abonnement';

  @override
  String get settingsSubscriptionTileSubtitle => 'Abonnement, betalinger og oppsigelse';

  @override
  String get settingsInvoicesTileTitle => 'Betalingshistorikk';

  @override
  String get settingsInvoicesTileSubtitle => 'Alle betalinger og kvitteringer';

  @override
  String get settingsNoPermission => 'Du har ikke tillatelse til å endre denne innstillingen.';

  @override
  String get stockPhysicalValidityUnknown => 'Ukjent fysisk utløpsdato';

  @override
  String get stockNoPhysicalStock => 'Ingen fysisk beholdning';

  @override
  String get stockRegularizeValidityTitle => 'Regulariser fysisk gyldighet';

  @override
  String get stockRegularizeValiditySubtitle => 'Identifiser delen og oppgi dokumentert gyldighet. Klassifiseringen gjøres av systemet.';

  @override
  String get stockRegularizeQrLabel => 'QR eller delkode';

  @override
  String get stockRegularizeExpiryLabel => 'Dokumentert fysisk gyldighet';

  @override
  String get stockRegularizeExpirySelect => 'Velg dato';

  @override
  String get stockRegularizeEvidenceLabel => 'Dokumentasjon (dokument eller verifiserbar oppføring)';

  @override
  String get stockRegularizeJustificationLabel => 'Begrunnelse';

  @override
  String get stockRegularizeSubmit => 'Regulariser';

  @override
  String get stockRegularizeIncomplete => 'Fyll ut delen, gyldigheten, dokumentasjonen og begrunnelsen.';

  @override
  String get stockRegularizeResultEligible => 'Gyldighet regularisert. Delen er kvalifisert for utlevering og reservasjon.';

  @override
  String get stockRegularizeResultBlocked => 'Gyldighet regularisert. Delen er utløpt og forblir blokkert for utlevering.';

  @override
  String get stockRegularizeResultDone => 'Gyldighet regularisert.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — ulike verneutstyrstyper: $count';
  }

  @override
  String stockPhysicalPieceCounts(int valid, int expiring, int expired, int unknown) {
    return 'Fysiske enheter: gyldige $valid, utløper snart $expiring, utløpt $expired, ukjent $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible => 'Enheten kan ikke utleveres. Kontroller fysisk utløpsdato, status, reservasjoner og beholdning.';

  @override
  String get safetyTitle => 'Sikkerhetsbibliotek';

  @override
  String get safetyApproved => 'Godkjent verneutstyr';

  @override
  String get safetyRetry => 'Prøv igjen';

  @override
  String get safetyClose => 'Lukk';

  @override
  String get safetyCancel => 'Avbryt';

  @override
  String get safetyConfirm => 'Bekreft';

  @override
  String get safetyAccess => 'Fortsett';

  @override
  String get safetyPortalConfirm => 'Bekreft portaltilgang';

  @override
  String get safetyCpfLast => 'Tre siste CPF-sifre';

  @override
  String get safetyView => 'Vis';

  @override
  String get safetyFit => 'Tilpass';

  @override
  String get safetyZoomIn => 'Zoom inn';

  @override
  String get safetyZoomOut => 'Zoom ut';

  @override
  String get safetyNextPage => 'Neste side';

  @override
  String get safetyPreviousPage => 'Forrige side';

  @override
  String get safetyDocument => 'Dokument';

  @override
  String get safetyDetails => 'Detaljer';

  @override
  String get safetyRelatedDocuments => 'Tilknyttede dokumenter';

  @override
  String get safetyRelatedEpis => 'Tilknyttet verneutstyr';

  @override
  String get safetyRelatedEpi => 'Tilknyttet verneutstyr';

  @override
  String get safetyAllEpis => 'Alt verneutstyr';

  @override
  String get safetyAllCategories => 'Alle kategorier';

  @override
  String get safetyNoDocs => 'Ingen publiserte dokumenter for denne konteksten.';

  @override
  String get safetyNoRecords => 'Ingen publiserte, autoriserte oppføringer i denne konteksten.';

  @override
  String get safetyCatalogueNotice => 'Kataloggodkjenning angir ikke fysisk tilgjengelighet. CA-utløp er separat fra partiutløp.';

  @override
  String get safetyName => 'Verneutstyr';

  @override
  String get safetyManufacturer => 'Produsent';

  @override
  String get safetyModel => 'Modell/referanse';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'CA-utløp';

  @override
  String get safetyUsefulLife => 'Levetid (måneder)';

  @override
  String get safetyProtection => 'Beskyttelse';

  @override
  String get safetySection => 'Seksjon';

  @override
  String get safetyRecommendations => 'Anbefalinger/begrensninger';

  @override
  String get safetyUnknown => 'Ikke oppgitt';

  @override
  String get safetySearch => 'Søk';

  @override
  String get safetyViewEpi => 'Vis verneutstyr';

  @override
  String get safetyHistory => 'Historikk';

  @override
  String get safetyDocumentHistory => 'Dokumenthistorikk';

  @override
  String get safetyPublish => 'Publiser';

  @override
  String get safetyPublishVersion => 'Publiser versjon';

  @override
  String get safetyArchive => 'Arkiver dokument';

  @override
  String get safetyArchiveVersions => 'Arkiver dokument og versjoner';

  @override
  String get safetyReason => 'Begrunnelse kreves';

  @override
  String get safetyNew => 'Nytt dokument';

  @override
  String get safetyCreateNew => 'Opprett nytt dokument';

  @override
  String get safetyMetadata => 'Versjonsinformasjon';

  @override
  String get safetyEmptyAdmin => 'Ingen registrerte dokumenter.';

  @override
  String get safetyPrivateNotice => 'Private originaler, bevarte versjoner og historikk. Administrasjon begrenset til generell administrator og registeradministrator.';

  @override
  String get safetyAllowAdminDownloads => 'Tillat originalnedlasting for autoriserte administratorer';

  @override
  String get safetyPreviewOnlyNotice => 'Ansatte har alltid kun forhåndsvisning.';

  @override
  String get safetyPolicyReason => 'Endre administrativ nedlastingspolicy';

  @override
  String get safetySearchVersions => 'Søk i tittel eller versjon';

  @override
  String get safetyChooseFile => 'Velg fil';

  @override
  String get safetyFilePickerLabel => 'Sikkerhetsdokumenter';

  @override
  String get safetyUnitRequired => 'Velg minst én enhet';

  @override
  String get safetyAllUnits => 'Alle bedriftsenheter';

  @override
  String get safetyRequired => 'Påkrevd';

  @override
  String get safetyDocumentTitle => 'Tittel';

  @override
  String get safetyVersion => 'Versjon';

  @override
  String get safetyEffectiveDate => 'Gyldig fra (ÅÅÅÅ-MM-DD)';

  @override
  String get safetySectors => 'Kommaseparerte avdelinger (tomt = alle)';

  @override
  String get safetyActivities => 'Kommaseparerte aktiviteter/stillinger (tomt = alle)';

  @override
  String get safetyUpload => 'Registrer dokument eller versjon';

  @override
  String get safetyRendering => 'Genererer trygg forhåndsvisning…';

  @override
  String get safetyFileLimit => 'Velg en fil på opptil 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versjon $version · Gyldig fra $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Visningsenhet: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Forhåndsvisning utilgjengelig: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Opplasting avvist; forhåndsvisning utilgjengelig: $error';
  }

  @override
  String safetyVersionSummary(String version, String revision, String state, String date) {
    return 'Versjon $version / revisjon $revision · $state · Gyldig fra $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Ansvarlig $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Bruksmatrise for verneutstyr';

  @override
  String get safetyCategoryGlove => 'Hanskematrise';

  @override
  String get safetyCategoryCare => 'Veiledninger for rengjøring og vedlikehold';

  @override
  String get safetyCategoryUse => 'Bruksanvisninger for verneutstyr';

  @override
  String get safetyCategoryTechnical => 'Håndbøker og tekniske datablad';

  @override
  String get safetyCategoryOther => 'Andre sikkerhetsdokumenter';

  @override
  String get safetyStateDraft => 'Utkast';

  @override
  String get safetyStatePublished => 'Publisert';

  @override
  String get safetyStateSuperseded => 'Erstattet';

  @override
  String get safetyStateArchived => 'Arkivert';
  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linha $line — $item (item #$id): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';
  }
  @override
  String get prConfTitle => 'Mottakskonferanse';


  @override
  String get prConfIntro =>
      'Kryss av hver vare etter faktisk mottak. Oppgi produsentens fysiske holdbarhet og verifiserbart bevis; bruk «Del i partier» for ulike holdbarheter eller individuelle unntak. Enheter uten bevist holdbarhet blir SPERRET.';


  @override
  String get prConfReceivedYes => 'Mottatt';


  @override
  String get prConfReceivedNo => 'Ikke mottatt';


  @override
  String get prConfEvidence => 'Verifiserbart bevis';


  @override
  String get prConfEvidenceHint => 'Etikett / faktura / foto';


  @override
  String get prConfEvidenceRequired =>
      'Verifiserbart bevis er påkrevd når holdbarhet er satt.';


  @override
  String get prConfSplitLots => 'Del i partier';


  @override
  String get prConfSingleDate => 'Bruk én dato';


  @override
  String get prConfAddLot => 'Legg til parti';


  @override
  String get prConfAddException => 'Unntak (1 enhet)';


  @override
  String get prConfLotQty => 'Ant.';


  @override
  String get prConfLotCode => 'Identifikasjon';


  @override
  String get prConfRemoveLot => 'Fjern parti';


  @override
  String get prConfPreview => 'Forhåndsvisning — fysisk holdbarhet per enhet';


  @override
  String get prConfBlocked => 'UTEN holdbarhet → SPERRET';


  @override
  String get prConfExpired => 'utløpt';


  @override
  String get prConfPiece => 'enhet(er)';


  @override
  String get prConfSumMismatch =>
      'Summen av partimengdene stemmer ikke med mottatt antall.';


  @override
  String get prConfLotQtyPositive =>
      'Hvert parti trenger en mengde større enn null.';


  @override
  String get prConfNotes => 'Merknader om varer som ikke er mottatt';


  @override
  String get prConfNotesRequired =>
      'Oppgi merknader om varer som ikke er mottatt.';


  @override
  String get prConfSubmit => 'Registrer konferanse';


  @override
  String get prConfDone => 'Konferanse registrert.';


  @override
  String get prConfEmpty => 'Ingen vare kvalifisert for konferanse.';


  @override
  String get prConfInvalidQuantity =>
      'Faktisk mottatt mengde er ugyldig eller ikke positiv. Korriger mottaket før bekreftelse.';


  @override
  String get prConfNoPersistedPieces =>
      'Ingen enheter ble registrert, eller svaret er inkonsistent. Lagerføringen ble ikke bekreftet.';


  @override
  String prConfDoneQuantity(int count) {
    return '$count enheter faktisk registrert på lager.';
  }


  @override
  String get prConfNoStockEntry =>
      'Kontroll lagret uten at enheter er lagt til på lager.';


}
