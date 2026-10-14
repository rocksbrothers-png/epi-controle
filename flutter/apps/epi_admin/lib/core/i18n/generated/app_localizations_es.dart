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
  String get safetyTitle => 'Biblioteca de Seguridad';

  @override
  String get safetyApproved => 'EPP Aprobados';

  @override
  String get safetyRetry => 'Intentar de nuevo';

  @override
  String get safetyClose => 'Cerrar';

  @override
  String get safetyCancel => 'Cancelar';

  @override
  String get safetyConfirm => 'Confirmar';

  @override
  String get safetyAccess => 'Acceder';

  @override
  String get safetyPortalConfirm => 'Confirmar acceso al portal';

  @override
  String get safetyCpfLast => 'Tres últimos dígitos del CPF';

  @override
  String get safetyView => 'Visualizar';

  @override
  String get safetyFit => 'Ajustar';

  @override
  String get safetyZoomIn => 'Ampliar';

  @override
  String get safetyZoomOut => 'Reducir';

  @override
  String get safetyNextPage => 'Página siguiente';

  @override
  String get safetyPreviousPage => 'Página anterior';

  @override
  String get safetyDocument => 'Documento';

  @override
  String get safetyDetails => 'Detalles';

  @override
  String get safetyRelatedDocuments => 'Documentos asociados';

  @override
  String get safetyRelatedEpis => 'EPP relacionados';

  @override
  String get safetyRelatedEpi => 'EPP relacionado';

  @override
  String get safetyAllEpis => 'Todos los EPP';

  @override
  String get safetyAllCategories => 'Todas las categorías';

  @override
  String get safetyNoDocs => 'No hay documentos publicados para este contexto.';

  @override
  String get safetyNoRecords => 'No hay registros publicados y autorizados en este contexto.';

  @override
  String get safetyCatalogueNotice => 'La aprobación del catálogo no indica disponibilidad física. El vencimiento del CA es distinto al del lote.';

  @override
  String get safetyName => 'EPP';

  @override
  String get safetyManufacturer => 'Fabricante';

  @override
  String get safetyModel => 'Modelo/referencia';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Vencimiento del CA';

  @override
  String get safetyUsefulLife => 'Vida útil (meses)';

  @override
  String get safetyProtection => 'Protección';

  @override
  String get safetySection => 'Sección';

  @override
  String get safetyRecommendations => 'Recomendaciones/restricciones';

  @override
  String get safetyUnknown => 'No informado';

  @override
  String get safetySearch => 'Buscar';

  @override
  String get safetyViewEpi => 'Ver EPP';

  @override
  String get safetyHistory => 'Historial';

  @override
  String get safetyDocumentHistory => 'Historial documental';

  @override
  String get safetyPublish => 'Publicar';

  @override
  String get safetyPublishVersion => 'Publicar versión';

  @override
  String get safetyArchive => 'Archivar documento';

  @override
  String get safetyArchiveVersions => 'Archivar documento y versiones';

  @override
  String get safetyReason => 'Justificación obligatoria';

  @override
  String get safetyNew => 'Nuevo documento';

  @override
  String get safetyCreateNew => 'Crear nuevo documento';

  @override
  String get safetyMetadata => 'Datos de la versión';

  @override
  String get safetyEmptyAdmin => 'No hay documentos registrados.';

  @override
  String get safetyPrivateNotice => 'Originales privados, versiones e historial conservados. Gestión restringida al Administrador General y al Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads => 'Permitir descargar originales a administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice => 'Los colaboradores solo pueden consultar la vista previa.';

  @override
  String get safetyPolicyReason => 'Cambiar política de descarga administrativa';

  @override
  String get safetySearchVersions => 'Buscar título o versión';

  @override
  String get safetyChooseFile => 'Seleccionar archivo';

  @override
  String get safetyFilePickerLabel => 'Documentos de SST';

  @override
  String get safetyUnitRequired => 'Seleccione al menos una unidad';

  @override
  String get safetyAllUnits => 'Todas las unidades de la empresa';

  @override
  String get safetyRequired => 'Obligatorio';

  @override
  String get safetyDocumentTitle => 'Título';

  @override
  String get safetyVersion => 'Versión';

  @override
  String get safetyEffectiveDate => 'Vigencia (AAAA-MM-DD)';

  @override
  String get safetySectors => 'Sectores separados por comas (vacío = todos)';

  @override
  String get safetyActivities => 'Actividades/funciones separadas por comas (vacío = todas)';

  @override
  String get safetyUpload => 'Registrar o versionar documento';

  @override
  String get safetyRendering => 'Generando vista previa segura…';

  @override
  String get safetyFileLimit => 'Seleccione un archivo de hasta 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versión $version · Vigencia $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unidad de consulta: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Vista previa no disponible: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Registro rechazado; vista previa no disponible: $error';
  }

  @override
  String safetyVersionSummary(String version, String revision, String state, String date) {
    return 'Versión $version / revisión $revision · $state · Vigencia $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsable $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matriz de Aplicación de EPP';

  @override
  String get safetyCategoryGlove => 'Matriz de Selección de Guantes';

  @override
  String get safetyCategoryCare => 'Guías de Higiene y Conservación';

  @override
  String get safetyCategoryUse => 'Instrucciones de Uso de EPP';

  @override
  String get safetyCategoryTechnical => 'Manuales y Fichas Técnicas';

  @override
  String get safetyCategoryOther => 'Otros Documentos de SST';

  @override
  String get safetyStateDraft => 'Borrador';

  @override
  String get safetyStatePublished => 'Publicado';

  @override
  String get safetyStateSuperseded => 'Sustituido';

  @override
  String get safetyStateArchived => 'Archivado';
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

/// The translations for Spanish Castilian, as used in Spain (`es_ES`).
class AppLocalizationsEsEs extends AppLocalizationsEs {
  AppLocalizationsEsEs(): super('es_ES');

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
  String get employeeUnitLockedHint => 'Unidad definida por su perfil de acceso.';

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
  String get deliveryOfflineQueued => 'Entrega guardada — se sincronizará al conectarse';

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
  String get returnOfflineQueued => 'Devolución guardada — se sincronizará cuando haya conexión.';

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
  String get poManufacturerValidityRequired => 'Indique la validez del fabricante de todos los EPI recibidos.';

  @override
  String get poOcrDateNotFound => 'No se pudo identificar la fecha. Inténtelo de nuevo.';

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
  String get portalSignatureInstruction => 'Firme en el espacio de abajo para confirmar la recepción';

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
  String get employeeContactErrorNoApp => 'No hay app disponible para abrir este enlace';

  @override
  String get employeeContactErrorGeneric => 'Error al contactar al colaborador. Inténtalo de nuevo.';

  @override
  String get employeeContactPdfError => 'Error al descargar el PDF. Inténtalo de nuevo.';

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
  String get myCompanySubtitle => 'Datos, identidad visual y dominio de su empresa';

  @override
  String get myCompanySaved => 'Configuración de la empresa guardada correctamente.';

  @override
  String get myCompanyLoadError => 'No se pudieron cargar los datos de la empresa.';

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
  String get epiArchiveBlockTitle => 'Archivar con bloqueo de stock';

  @override
  String get epiArchiveBlockBody => 'Este EPP tiene stock disponible o vínculos activos. Al confirmar, el stock disponible se mueve a Stock Bloqueado (rastreable) y el EPP se archiva.';

  @override
  String get epiArchiveBlockConfirm => 'Bloquear stock y archivar';

  @override
  String get epiArchiveReasonLabel => 'Motivo del archivo (auditoría)';

  @override
  String get epiArchiveReasonRequired => 'Indique el motivo para continuar.';

  @override
  String get epiArchiveBlockableLabel => 'Stock a bloquear';

  @override
  String get epiArchiveLiveLinksTitle => 'Vínculos activos';

  @override
  String get epiArchiveAvailable => 'Disponible';

  @override
  String get epiArchiveInTransit => 'En tránsito';

  @override
  String get epiArchiveInPossession => 'En posesión';

  @override
  String get epiArchivePendingRequests => 'Solicitudes abiertas';

  @override
  String get epiArchivePendingPurchase => 'Compras abiertas';

  @override
  String get dashboardComplianceTitle => 'Conformidad de stock';

  @override
  String get dashboardComplianceAllOk => 'Stock conforme';

  @override
  String get complianceCaExpired => 'CA vencido';

  @override
  String get complianceCaExpiring => 'CA por vencer';

  @override
  String get complianceProductExpired => 'Producto vencido';

  @override
  String get complianceProductExpiring => 'Producto por vencer';

  @override
  String get complianceMissingManufacture => 'Sin fabricación';

  @override
  String get complianceMissingLot => 'Sin lote';

  @override
  String get complianceAdminBlocked => 'Bloqueado';

  @override
  String get handoverTitle => 'Conferencia de entrega';

  @override
  String get handoverPrompt => 'Escanee el QR de la entrega o ingrese el código.';

  @override
  String get handoverCodeLabel => 'Código de entrega';

  @override
  String get handoverLookupButton => 'Buscar entrega';

  @override
  String get handoverScanButton => 'Escanear QR';

  @override
  String get handoverConfirmButton => 'Confirmar recepción';

  @override
  String get handoverConfirmedTitle => 'Recepción confirmada';

  @override
  String get handoverAlreadyConfirmed => 'Esta entrega ya fue confirmada.';

  @override
  String get handoverNotFound => 'No se encontró entrega para este código.';

  @override
  String get handoverConfirmError => 'No se pudo confirmar la recepción.';

  @override
  String get handoverEmployeeLabel => 'Colaborador';

  @override
  String get handoverEpiLabel => 'EPP';

  @override
  String get handoverQuantityLabel => 'Cantidad';

  @override
  String get handoverSectorLabel => 'Sector';

  @override
  String get handoverRoleLabel => 'Función';

  @override
  String get handoverUnitLabel => 'Unidad';

  @override
  String get handoverDeliveryDateLabel => 'Fecha de entrega';

  @override
  String get handoverReceiverNameLabel => 'Nombre de quien recibe (opcional)';

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
  String get legalEntityDeactivateHint => 'El historial jurídico se conserva. El CNPJ deja de usarse en nuevas operaciones.';

  @override
  String get legalEntityShowInactive => 'Mostrar inactivos';

  @override
  String get legalEntitiesEmpty => 'Ningún CNPJ registrado.';

  @override
  String get legalEntityMunicipalityLabel => 'Municipio';

  @override
  String get legalEntityCnpjLabel => 'CNPJ (ID fiscal brasileño)';

  @override
  String get legalEntityUfLabel => 'Estado';

  @override
  String get legalEntitiesImportColumnsHint => 'CNPJ\tRazón social\tNombre comercial\tTipo';

  @override
  String get legalEntitiesImport => 'Importar hoja de cálculo';

  @override
  String get legalEntitiesImportHint => 'Copie las filas de la hoja (incluida la de encabezado) y péguelas abajo. Acepta columnas en portugués o inglés.';

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
  String get legalEntityTransferHint => 'El CNPJ es el vínculo del contrato laboral y no cambia al transferir de unidad. Este cambio se audita y exige justificación.';

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
  String get unitTransferHint => 'Movimiento de unidad operativa — temporal o definitivo. Genera un registro auditable y no cambia el CNPJ del colaborador.';

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
  String get myCompanyStockScopeHint => 'Esta configuración solo cambia la vista consolidada de los saldos. Entradas, reservas, salidas, entregas y demás movimientos siguen vinculados al stock de cada unidad.';

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
  String get unitLegalEntityHint => 'Persona jurídica responsable de las operaciones y del stock de esta unidad.';

  @override
  String get employeeEmploymentTypeLabel => 'Tipo de Vínculo';

  @override
  String get employeeSourceCompanyLabel => 'Empresa de Origen';

  @override
  String get employeeSourceCompanyHint => 'Nombre de la empresa de origen del colaborador';

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
  String get outsourcedCompaniesEmpty => 'Ninguna empresa tercerizada registrada.';

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
  String get outsourcedCompanyCnpjHint => 'Opcional en el Registro Simplificado';

  @override
  String get outsourcedCompanyKindLabel => 'Tipo de Empresa';

  @override
  String get outsourcedCompanyKindOutsourced => 'Tercerizada';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Prestadora de Servicio';

  @override
  String get outsourcedCompanyKindOther => 'Otro';

  @override
  String get outsourcedCompanyResponsibilityLabel => 'Responsabilidad por el Suministro de EPP';

  @override
  String get outsourcedCompanyUnitLabel => 'Unidad';

  @override
  String get outsourcedCompanyUnitAll => 'Todas las unidades (predeterminado)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidad';

  @override
  String get outsourcedCompanyLinkHint => 'Buscar empresa ya registrada en el tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked => 'Ya vinculadas a esta Unidad';

  @override
  String get outsourcedCompanyLinkSectionAvailable => 'Disponibles para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidad';

  @override
  String get outsourcedCompanyLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivateReason => 'Motivo del archivado (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidad(es)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidad de origen';

  @override
  String get outsourcedCompanyLinkEmpty => 'No se encontró ninguna empresa con ese término.';

  @override
  String get outsourcedCompanyLinkNotInformed => 'Vínculo no informado para su perfil';

  @override
  String get outsourcedCompanyStatusLabel => 'Situación';

  @override
  String get outsourcedCompanySave => 'Guardar';

  @override
  String get outsourcedCompanyCancel => 'Cancelar';

  @override
  String get outsourcedCompanyPromote => 'Promover a Registro Estándar';

  @override
  String get outsourcedCompanyPromoteConfirmTitle => '¿Promover a Registro Estándar?';

  @override
  String get outsourcedCompanyPromoteConfirmBody => 'La empresa pasará a ser tratada como Registro Estándar. Se requiere un CNPJ.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplificado';

  @override
  String get outsourcedCompanyStandardBadge => 'Estándar';

  @override
  String get outsourcedTabCompanies => 'Empresas';

  @override
  String get outsourcedTabEmployees => 'Registro de Colaboradores';

  @override
  String get outsourcedTabReports => 'Informes';

  @override
  String get outsourcedShowActive => 'Ver activos';

  @override
  String get outsourcedShowArchived => 'Ver archivados';

  @override
  String get archive => 'Archivar';

  @override
  String get restore => 'Restaurar';

  @override
  String get archivedAt => 'Archivado el';

  @override
  String get archiveReasonLabel => 'Motivo del archivado (auditoría)';

  @override
  String get outsourcedCompanyArchive => 'Archivar empresa';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => '¿Archivar esta empresa?';

  @override
  String get outsourcedCompanyRestore => 'Restaurar';

  @override
  String get outsourcedCompanyRestoreConfirmTitle => '¿Restaurar esta empresa?';

  @override
  String get outsourcedCompaniesArchivedEmpty => 'No hay empresas subcontratadas archivadas.';

  @override
  String get outsourcedEmployeeNew => 'Nuevo colaborador';

  @override
  String get outsourcedEmployeesEmpty => 'No hay colaboradores subcontratados/prestadores registrados.';

  @override
  String get outsourcedEmployeesArchivedEmpty => 'No hay colaboradores subcontratados/prestadores archivados.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Empresa subcontratada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel => 'Matrícula de la empresa de origen';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Credencial';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observaciones';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle => '¿Archivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle => '¿Restaurar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular a mi unidad';

  @override
  String get employeeUnitLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivateReason => 'Motivo del archivado (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Archivado en esta Unidad';

  @override
  String get employeeUnitLinkAbsent => 'No vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidad';

  @override
  String get employeeUnitLinksEmpty => 'Este colaborador no tiene vínculo con ninguna Unidad que usted pueda consultar.';

  @override
  String get employeeUnitLinksError => 'No se pudieron cargar los vínculos.';

  @override
  String get outsourcedReportsError => 'No fue posible cargar el informe.';

  @override
  String get outsourcedReportsEmpty => 'No hay empresas subcontratadas/prestadoras registradas.';

  @override
  String get outsourcedReportsActive => 'Activos';

  @override
  String get outsourcedReportsArchived => 'Archivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidad de Módulos';

  @override
  String get moduleVisibilityDescription => 'Permisos predeterminados: cada perfil tiene permisos predeterminados definidos por el sistema. Personalizaciones: el Administrador General puede personalizar la visualización y el uso de los módulos por perfil y por unidad, sin alterar la estructura predeterminada del sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle => 'Permisos predeterminados de este perfil';

  @override
  String get moduleVisibilityDefaultPanelHint => 'Estos permisos representan el comportamiento predeterminado del sistema. Las configuraciones siguientes solo permiten personalizaciones realizadas por el Administrador General.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ningún módulo por defecto';

  @override
  String get moduleVisibilityUnitLabel => 'Unidad';

  @override
  String get moduleVisibilityUnitHint => 'Un módulo no marcado específicamente para esta Unidad hereda el valor de \"Todas las unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Todas las unidades (predeterminado)';

  @override
  String get stockTabAvailable => 'Disponibles';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi => 'Seleccione un EPI para ver los artículos disponibles';

  @override
  String get stockAvailableEmpty => 'No hay artículos disponibles para este EPI en esta unidad';

  @override
  String get stockBlockedEmpty => 'No hay artículos bloqueados';

  @override
  String get stockNoOperationalUnit => 'Su perfil no tiene una unidad operativa activa. Contacte al administrador para obtener acceso al inventario.';

  @override
  String get stockItemLotLabel => 'Lote';

  @override
  String get stockStatusBlockedExpired => 'Vencido';

  @override
  String get stockStatusBlockedDiscard => 'Pendiente de descarte';

  @override
  String get stockStatusBlockedReturn => 'Pendiente de devolución al proveedor';

  @override
  String get stockStatusBlockedAnalysis => 'En análisis';

  @override
  String get stockStatusBlockedRejected => 'Rechazado';

  @override
  String get stockStatusBlockedArchived => 'EPI archivado';

  @override
  String get stockStatusUnknown => 'Estado no reconocido';

  @override
  String get stockUnitBalanceSuffix => 'en la unidad';

  @override
  String get stockCompanyBalanceLabel => 'empresa';

  @override
  String get stockMinimumShort => 'mín';

  @override
  String get deliveryStepItem => 'Ítem';

  @override
  String get deliveryItemTitle => 'Seleccione la unidad etiquetada';

  @override
  String get deliveryItemEmpty => 'Ningún ítem disponible en esta Unidad.';

  @override
  String get deliveryItemScan => 'Leer QR del ítem';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Stock en la Unidad: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit => 'Colaborador sin Unidad operativa: no se puede registrar la entrega.';

  @override
  String get deliveryQrOtherEpi => 'El código leído pertenece a otro EPP.';

  @override
  String get stockUnitRequiredToMove => 'Seleccione una Unidad para mover el stock.';

  @override
  String get stockAttentionSectionTitle => 'Existencias';

  @override
  String get stockAttentionCompanyTitle => 'Franja de atención — valor por defecto de la empresa';

  @override
  String get stockAttentionCompanyHelp => 'Se aplica a las Unidades que no han definido su propio porcentaje. No modifica ninguna Unidad ya configurada.';

  @override
  String get stockAttentionPercentageLabel => 'Porcentaje de la franja de atención';

  @override
  String get stockAttentionOriginLabel => 'Origen';

  @override
  String get stockAttentionOriginCompany => 'Configurado por la empresa';

  @override
  String get stockAttentionOriginSystem => 'Valor por defecto del sistema';

  @override
  String get stockAttentionSave => 'Guardar valor de la empresa';

  @override
  String get stockAttentionRestore => 'Restaurar el valor del sistema';

  @override
  String get stockAttentionSaved => 'Valor por defecto de la empresa guardado.';

  @override
  String get stockAttentionRestored => 'Valor de la empresa eliminado. La empresa vuelve al valor del sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Valor del sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuración de existencias';

  @override
  String get stockConfigIntro => 'Define las existencias mínimas, la franja de atención y el monitoreo de alerta de un EPI en una Unidad. Cada parámetro se guarda por separado.';

  @override
  String get stockConfigUnitLabel => 'Unidad a configurar';

  @override
  String get stockConfigSelectUnit => 'Selecciona la Unidad para configurar sus parámetros.';

  @override
  String get stockConfigSelectEpi => 'Selecciona el EPI para ver y editar los parámetros de esta Unidad.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError => 'No se pudo cargar la lista de EPI de esta Unidad.';

  @override
  String get stockConfigNoEpisInUnit => 'Ningún EPI es visible en esta Unidad.';

  @override
  String get stockConfigUnitBalance => 'Saldo en la Unidad';

  @override
  String get stockConfigAttentionLimit => 'Límite de la franja de atención';

  @override
  String get stockConfigUnderlyingStatus => 'Condición física';

  @override
  String get stockConfigDerivedUnavailable => 'Los valores calculados no se pudieron actualizar ahora. Los parámetros guardados arriba son correctos.';

  @override
  String get stockConfigStatusCritical => 'Crítico';

  @override
  String get stockConfigStatusNearMinimum => 'Cerca del mínimo';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alerta desactivada';

  @override
  String get stockConfigMinimumTitle => 'Existencias mínimas';

  @override
  String get stockConfigMinimumHelp => 'Cantidad por debajo de la cual el EPI se considera crítico en esta Unidad. Solo vale para esta Unidad.';

  @override
  String get stockConfigMinimumLabel => 'Existencias mínimas';

  @override
  String get stockConfigMinimumNegativeError => 'Introduce un número entero igual o mayor que cero.';

  @override
  String get stockConfigMinimumSaved => 'Existencias mínimas guardadas para esta Unidad.';

  @override
  String get stockConfigMinimumRestored => 'Existencias mínimas restauradas. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAttentionTitle => 'Franja de atención';

  @override
  String get stockConfigAttentionHelp => 'Porcentaje por encima del mínimo en el que el EPI ya entra en atención en esta Unidad. Independiente de las existencias mínimas.';

  @override
  String get stockConfigAttentionRangeError => 'El porcentaje debe estar entre 0 y 100.';

  @override
  String get stockConfigAttentionSaved => 'Franja de atención guardada para esta Unidad.';

  @override
  String get stockConfigAttentionRestored => 'Franja de atención restaurada. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoreo de alerta';

  @override
  String get stockConfigAlertHelp => 'Desactivarlo detiene la alerta de existencias bajas y la reposición automática de este EPI en esta Unidad. No cambia el saldo, el mínimo ni el porcentaje.';

  @override
  String get stockConfigAlertToggle => 'Monitorear las existencias de este EPI';

  @override
  String get stockConfigAlertPending => 'Cambio pendiente. Pulsa Guardar para aplicarlo.';

  @override
  String get stockConfigAlertDisableTitle => '¿Desactivar la alerta?';

  @override
  String get stockConfigAlertDisableBody => 'Este EPI dejará de generar alertas de existencias bajas y reposición automática en esta Unidad. La condición física seguirá mostrándose.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desactivar';

  @override
  String get stockConfigAlertSaved => 'Monitoreo de alerta guardado para esta Unidad.';

  @override
  String get stockConfigAlertRestored => 'Monitoreo restaurado. La Unidad vuelve al valor del sistema.';

  @override
  String get stockConfigOriginUnit => 'Configurado por esta Unidad';

  @override
  String get stockConfigOriginCompany => 'Heredado del valor de la empresa';

  @override
  String get stockConfigOriginUnknown => 'No indicada';

  @override
  String get stockConfigSave => 'Guardar';

  @override
  String get stockConfigRestore => 'Restaurar la herencia';

  @override
  String stockAttentionRangeError(int max) {
    return 'Introduzca un porcentaje entero entre 0 y $max.';
  }

  @override
  String get stockAttentionLoadError => 'No se ha podido cargar el valor por defecto de la empresa.';

  @override
  String get unitSelectorLabel => 'Unidad';

  @override
  String get unitSelectorAllUnits => 'Todas las Unidades';

  @override
  String get unitSelectorLockedHint => 'Su perfil opera en una Unidad fija.';

  @override
  String get unitSelectorLoadError => 'No se han podido cargar las Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned => 'No tiene ninguna Unidad asignada. Hable con el administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits => 'La empresa aún no tiene Unidades registradas.';

  @override
  String get settingsSectionCompany => 'Empresa';

  @override
  String get settingsSectionOperation => 'Operación';

  @override
  String get settingsSectionSubscription => 'Suscripción';

  @override
  String get settingsCompanyLabel => 'Empresa';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Administrando la empresa: $name';
  }

  @override
  String get settingsSelectCompanyFirst => 'Seleccione una empresa en Configuración para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPP';

  @override
  String get settingsFichaTileSubtitle => 'Título, declaración, observaciones y trazabilidad';

  @override
  String get settingsStockTileSubtitle => 'Franja de atención predeterminada de la empresa';

  @override
  String get settingsModulesTileSubtitle => 'Módulos visibles por perfil y por Unidad';

  @override
  String get settingsArchivalTitle => 'Archivado y retención';

  @override
  String get settingsArchivalSubtitle => 'Años de conservación de los registros archivados';

  @override
  String get settingsAppearanceTitle => 'Apariencia e idioma';

  @override
  String get settingsAppearanceSubtitle => 'Tema de la interfaz e idioma de la aplicación';

  @override
  String get settingsSubscriptionTileTitle => 'Mi suscripción';

  @override
  String get settingsSubscriptionTileSubtitle => 'Plan, cobros y cancelación';

  @override
  String get settingsInvoicesTileTitle => 'Historial financiero';

  @override
  String get settingsInvoicesTileSubtitle => 'Todos los cobros y recibos';

  @override
  String get settingsNoPermission => 'No tiene permiso para modificar esta configuración.';

  @override
  String get stockPhysicalValidityUnknown => 'Caducidad física desconocida';

  @override
  String get stockNoPhysicalStock => 'Sin existencias físicas';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validez física';

  @override
  String get stockRegularizeValiditySubtitle => 'Identifique la pieza e indique la validez comprobada. La clasificación la realiza el sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR o código de la pieza';

  @override
  String get stockRegularizeExpiryLabel => 'Validez física comprobada';

  @override
  String get stockRegularizeExpirySelect => 'Seleccionar fecha';

  @override
  String get stockRegularizeEvidenceLabel => 'Evidencia (documento o registro verificable)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificación';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete => 'Complete la pieza, la validez, la evidencia y la justificación.';

  @override
  String get stockRegularizeResultEligible => 'Validez regularizada. La pieza está habilitada para entrega y reserva.';

  @override
  String get stockRegularizeResultBlocked => 'Validez regularizada. La pieza está vencida y permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validez regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPI distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(int valid, int expiring, int expired, int unknown) {
    return 'Unidades físicas: válidas $valid, próximas $expiring, caducadas $expired, desconocidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible => 'Unidad no disponible para entrega. Revise caducidad física, estado, reservas y saldo.';

  @override
  String get safetyTitle => 'Biblioteca de Seguridad';

  @override
  String get safetyApproved => 'EPP Aprobados';

  @override
  String get safetyRetry => 'Intentar de nuevo';

  @override
  String get safetyClose => 'Cerrar';

  @override
  String get safetyCancel => 'Cancelar';

  @override
  String get safetyConfirm => 'Confirmar';

  @override
  String get safetyAccess => 'Acceder';

  @override
  String get safetyPortalConfirm => 'Confirmar acceso al portal';

  @override
  String get safetyCpfLast => 'Tres últimos dígitos del CPF';

  @override
  String get safetyView => 'Visualizar';

  @override
  String get safetyFit => 'Ajustar';

  @override
  String get safetyZoomIn => 'Ampliar';

  @override
  String get safetyZoomOut => 'Reducir';

  @override
  String get safetyNextPage => 'Página siguiente';

  @override
  String get safetyPreviousPage => 'Página anterior';

  @override
  String get safetyDocument => 'Documento';

  @override
  String get safetyDetails => 'Detalles';

  @override
  String get safetyRelatedDocuments => 'Documentos asociados';

  @override
  String get safetyRelatedEpis => 'EPP relacionados';

  @override
  String get safetyRelatedEpi => 'EPP relacionado';

  @override
  String get safetyAllEpis => 'Todos los EPP';

  @override
  String get safetyAllCategories => 'Todas las categorías';

  @override
  String get safetyNoDocs => 'No hay documentos publicados para este contexto.';

  @override
  String get safetyNoRecords => 'No hay registros publicados y autorizados en este contexto.';

  @override
  String get safetyCatalogueNotice => 'La aprobación del catálogo no indica disponibilidad física. El vencimiento del CA es distinto al del lote.';

  @override
  String get safetyName => 'EPP';

  @override
  String get safetyManufacturer => 'Fabricante';

  @override
  String get safetyModel => 'Modelo/referencia';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Vencimiento del CA';

  @override
  String get safetyUsefulLife => 'Vida útil (meses)';

  @override
  String get safetyProtection => 'Protección';

  @override
  String get safetySection => 'Sección';

  @override
  String get safetyRecommendations => 'Recomendaciones/restricciones';

  @override
  String get safetyUnknown => 'No informado';

  @override
  String get safetySearch => 'Buscar';

  @override
  String get safetyViewEpi => 'Ver EPP';

  @override
  String get safetyHistory => 'Historial';

  @override
  String get safetyDocumentHistory => 'Historial documental';

  @override
  String get safetyPublish => 'Publicar';

  @override
  String get safetyPublishVersion => 'Publicar versión';

  @override
  String get safetyArchive => 'Archivar documento';

  @override
  String get safetyArchiveVersions => 'Archivar documento y versiones';

  @override
  String get safetyReason => 'Justificación obligatoria';

  @override
  String get safetyNew => 'Nuevo documento';

  @override
  String get safetyCreateNew => 'Crear nuevo documento';

  @override
  String get safetyMetadata => 'Datos de la versión';

  @override
  String get safetyEmptyAdmin => 'No hay documentos registrados.';

  @override
  String get safetyPrivateNotice => 'Originales privados, versiones e historial conservados. Gestión restringida al Administrador General y al Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads => 'Permitir descargar originales a administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice => 'Los colaboradores solo pueden consultar la vista previa.';

  @override
  String get safetyPolicyReason => 'Cambiar política de descarga administrativa';

  @override
  String get safetySearchVersions => 'Buscar título o versión';

  @override
  String get safetyChooseFile => 'Seleccionar archivo';

  @override
  String get safetyFilePickerLabel => 'Documentos de SST';

  @override
  String get safetyUnitRequired => 'Seleccione al menos una unidad';

  @override
  String get safetyAllUnits => 'Todas las unidades de la empresa';

  @override
  String get safetyRequired => 'Obligatorio';

  @override
  String get safetyDocumentTitle => 'Título';

  @override
  String get safetyVersion => 'Versión';

  @override
  String get safetyEffectiveDate => 'Vigencia (AAAA-MM-DD)';

  @override
  String get safetySectors => 'Sectores separados por comas (vacío = todos)';

  @override
  String get safetyActivities => 'Actividades/funciones separadas por comas (vacío = todas)';

  @override
  String get safetyUpload => 'Registrar o versionar documento';

  @override
  String get safetyRendering => 'Generando vista previa segura…';

  @override
  String get safetyFileLimit => 'Seleccione un archivo de hasta 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Versión $version · Vigencia $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unidad de consulta: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Vista previa no disponible: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Registro rechazado; vista previa no disponible: $error';
  }

  @override
  String safetyVersionSummary(String version, String revision, String state, String date) {
    return 'Versión $version / revisión $revision · $state · Vigencia $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsable $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matriz de Aplicación de EPP';

  @override
  String get safetyCategoryGlove => 'Matriz de Selección de Guantes';

  @override
  String get safetyCategoryCare => 'Guías de Higiene y Conservación';

  @override
  String get safetyCategoryUse => 'Instrucciones de Uso de EPP';

  @override
  String get safetyCategoryTechnical => 'Manuales y Fichas Técnicas';

  @override
  String get safetyCategoryOther => 'Otros Documentos de SST';

  @override
  String get safetyStateDraft => 'Borrador';

  @override
  String get safetyStatePublished => 'Publicado';

  @override
  String get safetyStateSuperseded => 'Sustituido';

  @override
  String get safetyStateArchived => 'Archivado';
  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linha $line — $item (item #$id): quantidade efetivamente recebida inválida ou não positiva. Corrija o recebimento antes de confirmar.';
  }
  @override
  String get prConfTitle => 'Conferencia de Recepción';


  @override
  String get prConfIntro =>
      'Marque cada ítem según la recepción real. Informe la validez física del fabricante y la evidencia verificable; use \"Separar en lotes\" para validades diferentes o excepciones individuales. Las piezas sin validez comprobada entran BLOQUEADAS.';


  @override
  String get prConfReceivedYes => 'Recibido';


  @override
  String get prConfReceivedNo => 'No recibido';


  @override
  String get prConfEvidence => 'Evidencia verificable';


  @override
  String get prConfEvidenceHint => 'Etiqueta / factura / foto';


  @override
  String get prConfEvidenceRequired =>
      'La evidencia verificable es obligatoria cuando hay validez.';


  @override
  String get prConfSplitLots => 'Separar en lotes';


  @override
  String get prConfSingleDate => 'Usar fecha única';


  @override
  String get prConfAddLot => 'Agregar lote';


  @override
  String get prConfAddException => 'Excepción (1 pieza)';


  @override
  String get prConfLotQty => 'Cant.';


  @override
  String get prConfLotCode => 'Identificación';


  @override
  String get prConfRemoveLot => 'Quitar lote';


  @override
  String get prConfPreview => 'Vista previa — validez física por pieza';


  @override
  String get prConfBlocked => 'SIN validez → BLOQUEADAS';


  @override
  String get prConfExpired => 'vencida';


  @override
  String get prConfPiece => 'pieza(s)';


  @override
  String get prConfSumMismatch =>
      'La suma de las cantidades de los lotes no coincide con la cantidad recibida.';


  @override
  String get prConfLotQtyPositive =>
      'Cada lote necesita una cantidad mayor que cero.';


  @override
  String get prConfNotes => 'Observaciones sobre ítems no recibidos';


  @override
  String get prConfNotesRequired =>
      'Informe las observaciones sobre los ítems no recibidos.';


  @override
  String get prConfSubmit => 'Registrar Conferencia';


  @override
  String get prConfDone => 'Conferencia registrada.';


  @override
  String get prConfEmpty => 'Ningún ítem elegible para conferencia.';


  @override
  String get prConfInvalidQuantity =>
      'La cantidad efectivamente recibida es inválida o no positiva. Corrija la recepción antes de confirmar.';


  @override
  String get prConfNoPersistedPieces =>
      'No se registraron piezas o la respuesta es inconsistente. No se confirmó la entrada al inventario.';


  @override
  String prConfDoneQuantity(int count) {
    return '$count piezas efectivamente registradas en el inventario.';
  }


  @override
  String get prConfNoStockEntry =>
      'Conferencia guardada sin entrada de piezas al inventario.';


}
