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
  String get employeeSectorLabel => 'Área';

  @override
  String get employeeRoleLabel => 'Cargo';

  @override
  String get employeeUnitLabel => 'Unidad';

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
  String get episSearchHint => 'Buscar por nombre, aprobación o código';

  @override
  String get epiNameLabel => 'Nombre del EPP';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'N° de aprobación';

  @override
  String get epiCaExpiryLabel => 'Vencimiento aprobación';

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
}
