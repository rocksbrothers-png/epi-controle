// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

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
  String get employeeCpfLabel => 'CPF brasileño';

  @override
  String get employeeSectorLabel => 'Área';

  @override
  String get employeeRoleLabel => 'Cargo';

  @override
  String get employeeUnitLabel => 'Unidad';

  @override
  String get employeeUnitLockedHint =>
      'Unidad definida por su perfil de acceso.';

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
  String get episSearchHint => 'Buscar por nombre, CA brasileño o código';

  @override
  String get epiNameLabel => 'Nombre del EPP';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA — Certificado de Aprobación de Brasil';

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
  String get epiCaExpiryLabel => 'Vencimiento del CA brasileño';

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
  String get epiArchiveBlockTitle => 'Archivar con bloqueo de stock';

  @override
  String get epiArchiveBlockBody =>
      'Este EPP tiene stock disponible o vínculos activos. Al confirmar, el stock disponible se mueve a Stock Bloqueado (rastreable) y el EPP se archiva.';

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
  String get handoverPrompt =>
      'Escanee el QR de la entrega o ingrese el código.';

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
  String get legalEntityDeactivateHint =>
      'El historial jurídico se conserva. El CNPJ deja de usarse en nuevas operaciones.';

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
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRazón social\tNombre comercial\tTipo';

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
  String get outsourcedCompanyUnitLabel => 'Unidad';

  @override
  String get outsourcedCompanyUnitAll => 'Todas las unidades (predeterminado)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidad';

  @override
  String get outsourcedCompanyLinkHint =>
      'Buscar empresa ya registrada en el tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Ya vinculadas a esta Unidad';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponibles para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidad';

  @override
  String get outsourcedCompanyLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motivo del archivado (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidad(es)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidad de origen';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'No se encontró ninguna empresa con ese término.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Vínculo no informado para su perfil';

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
  String get outsourcedCompaniesArchivedEmpty =>
      'No hay empresas subcontratadas archivadas.';

  @override
  String get outsourcedEmployeeNew => 'Nuevo colaborador';

  @override
  String get outsourcedEmployeesEmpty =>
      'No hay colaboradores subcontratados/prestadores registrados.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'No hay colaboradores subcontratados/prestadores archivados.';

  @override
  String get outsourcedEmployeeCompanyLabel =>
      'Empresa subcontratada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Matrícula de la empresa de origen';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Credencial';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observaciones';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      '¿Archivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      '¿Restaurar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular a mi unidad';

  @override
  String get employeeUnitLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motivo del archivado (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Archivado en esta Unidad';

  @override
  String get employeeUnitLinkAbsent => 'No vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidad';

  @override
  String get employeeUnitLinksEmpty =>
      'Este colaborador no tiene vínculo con ninguna Unidad que usted pueda consultar.';

  @override
  String get employeeUnitLinksError => 'No se pudieron cargar los vínculos.';

  @override
  String get outsourcedReportsError => 'No fue posible cargar el informe.';

  @override
  String get outsourcedReportsEmpty =>
      'No hay empresas subcontratadas/prestadoras registradas.';

  @override
  String get outsourcedReportsActive => 'Activos';

  @override
  String get outsourcedReportsArchived => 'Archivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidad de Módulos';

  @override
  String get moduleVisibilityDescription =>
      'Permisos predeterminados: cada perfil tiene permisos predeterminados definidos por el sistema. Personalizaciones: el Administrador General puede personalizar la visualización y el uso de los módulos por perfil y por unidad, sin alterar la estructura predeterminada del sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Permisos predeterminados de este perfil';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Estos permisos representan el comportamiento predeterminado del sistema. Las configuraciones siguientes solo permiten personalizaciones realizadas por el Administrador General.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ningún módulo por defecto';

  @override
  String get moduleVisibilityUnitLabel => 'Unidad';

  @override
  String get moduleVisibilityUnitHint =>
      'Un módulo no marcado específicamente para esta Unidad hereda el valor de \"Todas las unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption =>
      'Todas las unidades (predeterminado)';

  @override
  String get stockTabAvailable => 'Disponibles';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi =>
      'Seleccione un EPI para ver los artículos disponibles';

  @override
  String get stockAvailableEmpty =>
      'No hay artículos disponibles para este EPI en esta unidad';

  @override
  String get stockBlockedEmpty => 'No hay artículos bloqueados';

  @override
  String get stockNoOperationalUnit =>
      'Su perfil no tiene una unidad operativa activa. Contacte al administrador para obtener acceso al inventario.';

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
  String get deliveryEmployeeWithoutUnit =>
      'Colaborador sin Unidad operativa: no se puede registrar la entrega.';

  @override
  String get deliveryQrOtherEpi => 'El código leído pertenece a otro EPP.';

  @override
  String get stockUnitRequiredToMove =>
      'Seleccione una Unidad para mover el stock.';

  @override
  String get stockAttentionSectionTitle => 'Existencias';

  @override
  String get stockAttentionCompanyTitle =>
      'Franja de atención — valor por defecto de la empresa';

  @override
  String get stockAttentionCompanyHelp =>
      'Se aplica a las Unidades que no han definido su propio porcentaje. No modifica ninguna Unidad ya configurada.';

  @override
  String get stockAttentionPercentageLabel =>
      'Porcentaje de la franja de atención';

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
  String get stockAttentionRestored =>
      'Valor de la empresa eliminado. La empresa vuelve al valor del sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Valor del sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuración de existencias';

  @override
  String get stockConfigIntro =>
      'Define las existencias mínimas, la franja de atención y el monitoreo de alerta de un EPI en una Unidad. Cada parámetro se guarda por separado.';

  @override
  String get stockConfigUnitLabel => 'Unidad a configurar';

  @override
  String get stockConfigSelectUnit =>
      'Selecciona la Unidad para configurar sus parámetros.';

  @override
  String get stockConfigSelectEpi =>
      'Selecciona el EPI para ver y editar los parámetros de esta Unidad.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'No se pudo cargar la lista de EPI de esta Unidad.';

  @override
  String get stockConfigNoEpisInUnit => 'Ningún EPI es visible en esta Unidad.';

  @override
  String get stockConfigUnitBalance => 'Saldo en la Unidad';

  @override
  String get stockConfigAttentionLimit => 'Límite de la franja de atención';

  @override
  String get stockConfigUnderlyingStatus => 'Condición física';

  @override
  String get stockConfigDerivedUnavailable =>
      'Los valores calculados no se pudieron actualizar ahora. Los parámetros guardados arriba son correctos.';

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
  String get stockConfigMinimumHelp =>
      'Cantidad por debajo de la cual el EPI se considera crítico en esta Unidad. Solo vale para esta Unidad.';

  @override
  String get stockConfigMinimumLabel => 'Existencias mínimas';

  @override
  String get stockConfigMinimumNegativeError =>
      'Introduce un número entero igual o mayor que cero.';

  @override
  String get stockConfigMinimumSaved =>
      'Existencias mínimas guardadas para esta Unidad.';

  @override
  String get stockConfigMinimumRestored =>
      'Existencias mínimas restauradas. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAttentionTitle => 'Franja de atención';

  @override
  String get stockConfigAttentionHelp =>
      'Porcentaje por encima del mínimo en el que el EPI ya entra en atención en esta Unidad. Independiente de las existencias mínimas.';

  @override
  String get stockConfigAttentionRangeError =>
      'El porcentaje debe estar entre 0 y 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Franja de atención guardada para esta Unidad.';

  @override
  String get stockConfigAttentionRestored =>
      'Franja de atención restaurada. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoreo de alerta';

  @override
  String get stockConfigAlertHelp =>
      'Desactivarlo detiene la alerta de existencias bajas y la reposición automática de este EPI en esta Unidad. No cambia el saldo, el mínimo ni el porcentaje.';

  @override
  String get stockConfigAlertToggle => 'Monitorear las existencias de este EPI';

  @override
  String get stockConfigAlertPending =>
      'Cambio pendiente. Pulsa Guardar para aplicarlo.';

  @override
  String get stockConfigAlertDisableTitle => '¿Desactivar la alerta?';

  @override
  String get stockConfigAlertDisableBody =>
      'Este EPI dejará de generar alertas de existencias bajas y reposición automática en esta Unidad. La condición física seguirá mostrándose.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desactivar';

  @override
  String get stockConfigAlertSaved =>
      'Monitoreo de alerta guardado para esta Unidad.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoreo restaurado. La Unidad vuelve al valor del sistema.';

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
  String get stockAttentionLoadError =>
      'No se ha podido cargar el valor por defecto de la empresa.';

  @override
  String get unitSelectorLabel => 'Unidad';

  @override
  String get unitSelectorAllUnits => 'Todas las Unidades';

  @override
  String get unitSelectorLockedHint => 'Su perfil opera en una Unidad fija.';

  @override
  String get unitSelectorLoadError => 'No se han podido cargar las Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'No tiene ninguna Unidad asignada. Hable con el administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'La empresa aún no tiene Unidades registradas.';

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
  String get settingsSelectCompanyFirst =>
      'Seleccione una empresa en Configuración para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPP';

  @override
  String get settingsFichaTileSubtitle =>
      'Título, declaración, observaciones y trazabilidad';

  @override
  String get settingsStockTileSubtitle =>
      'Franja de atención predeterminada de la empresa';

  @override
  String get settingsModulesTileSubtitle =>
      'Módulos visibles por perfil y por Unidad';

  @override
  String get settingsArchivalTitle => 'Archivado y retención';

  @override
  String get settingsArchivalSubtitle =>
      'Años de conservación de los registros archivados';

  @override
  String get settingsAppearanceTitle => 'Apariencia e idioma';

  @override
  String get settingsAppearanceSubtitle =>
      'Tema de la interfaz e idioma de la aplicación';

  @override
  String get settingsSubscriptionTileTitle => 'Mi suscripción';

  @override
  String get settingsSubscriptionTileSubtitle => 'Plan, cobros y cancelación';

  @override
  String get settingsInvoicesTileTitle => 'Historial financiero';

  @override
  String get settingsInvoicesTileSubtitle => 'Todos los cobros y recibos';

  @override
  String get settingsNoPermission =>
      'No tiene permiso para modificar esta configuración.';

  @override
  String get stockPhysicalValidityUnknown => 'Caducidad física desconocida';

  @override
  String get stockNoPhysicalStock => 'Sin existencias físicas';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validez física';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifique la pieza e indique la validez comprobada. La clasificación la realiza el sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR o código de la pieza';

  @override
  String get stockRegularizeExpiryLabel => 'Validez física comprobada';

  @override
  String get stockRegularizeExpirySelect => 'Seleccionar fecha';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidencia (documento o registro verificable)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificación';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete =>
      'Complete la pieza, la validez, la evidencia y la justificación.';

  @override
  String get stockRegularizeResultEligible =>
      'Validez regularizada. La pieza está habilitada para entrega y reserva.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validez regularizada. La pieza está vencida y permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validez regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPI distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Unidades físicas: válidas $valid, próximas $expiring, caducadas $expired, desconocidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Unidad no disponible para entrega. Revise caducidad física, estado, reservas y saldo.';

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
  String get safetyNoRecords =>
      'No hay registros publicados y autorizados en este contexto.';

  @override
  String get safetyCatalogueNotice =>
      'La aprobación del catálogo no indica disponibilidad física. El vencimiento del CA es distinto al del lote.';

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
  String get safetyPrivateNotice =>
      'Originales privados, versiones e historial conservados. Gestión restringida al Administrador General y al Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads =>
      'Permitir descargar originales a administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice =>
      'Los colaboradores solo pueden consultar la vista previa.';

  @override
  String get safetyPolicyReason =>
      'Cambiar política de descarga administrativa';

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
  String get safetyActivities =>
      'Actividades/funciones separadas por comas (vacío = todas)';

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
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
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

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Línea $line — $item (artículo #$id): cantidad efectivamente recibida inválida o no positiva. Corrija la recepción antes de confirmar.';
  }
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
  String get employeeCpfLabel => 'CPF brasileño';

  @override
  String get employeeSectorLabel => 'Área';

  @override
  String get employeeRoleLabel => 'Cargo';

  @override
  String get employeeUnitLabel => 'Unidad';

  @override
  String get employeeUnitLockedHint =>
      'Unidad definida por su perfil de acceso.';

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
  String get episSearchHint => 'Buscar por nombre, CA brasileño o código';

  @override
  String get epiNameLabel => 'Nombre del EPP';

  @override
  String get epiCodeLabel => 'Código de compra';

  @override
  String get epiCaLabel => 'CA — Certificado de Aprobación de Brasil';

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
  String get epiCaExpiryLabel => 'Vencimiento del CA brasileño';

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
  String get epiArchiveBlockTitle => 'Archivar con bloqueo de stock';

  @override
  String get epiArchiveBlockBody =>
      'Este EPP tiene stock disponible o vínculos activos. Al confirmar, el stock disponible se mueve a Stock Bloqueado (rastreable) y el EPP se archiva.';

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
  String get handoverPrompt =>
      'Escanee el QR de la entrega o ingrese el código.';

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
  String get legalEntityDeactivateHint =>
      'El historial jurídico se conserva. El CNPJ deja de usarse en nuevas operaciones.';

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
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRazón social\tNombre comercial\tTipo';

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
  String get outsourcedCompanyUnitLabel => 'Unidad';

  @override
  String get outsourcedCompanyUnitAll => 'Todas las unidades (predeterminado)';

  @override
  String get outsourcedCompanyLinkTitle => 'Vincular empresa a esta Unidad';

  @override
  String get outsourcedCompanyLinkHint =>
      'Buscar empresa ya registrada en el tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Ya vinculadas a esta Unidad';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponibles para vincular';

  @override
  String get outsourcedCompanyLinkLink => 'Vincular a esta Unidad';

  @override
  String get outsourcedCompanyLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motivo del archivado (opcional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Usada por $count Unidad(es)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unidad de origen';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'No se encontró ninguna empresa con ese término.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Vínculo no informado para su perfil';

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
  String get outsourcedCompaniesArchivedEmpty =>
      'No hay empresas subcontratadas archivadas.';

  @override
  String get outsourcedEmployeeNew => 'Nuevo colaborador';

  @override
  String get outsourcedEmployeesEmpty =>
      'No hay colaboradores subcontratados/prestadores registrados.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'No hay colaboradores subcontratados/prestadores archivados.';

  @override
  String get outsourcedEmployeeCompanyLabel =>
      'Empresa subcontratada/prestadora';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Matrícula de la empresa de origen';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Credencial';

  @override
  String get outsourcedEmployeeNotesLabel => 'Observaciones';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      '¿Archivar este colaborador?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      '¿Restaurar este colaborador?';

  @override
  String get employeeUnitLinkColumn => 'Vínculo local';

  @override
  String get employeeUnitLink => 'Vincular a mi unidad';

  @override
  String get employeeUnitLinkActivate => 'Reactivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivate => 'Archivar en esta Unidad';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motivo del archivado (opcional):';

  @override
  String get employeeUnitLinkActive => 'Vinculado';

  @override
  String get employeeUnitLinkArchived => 'Archivado en esta Unidad';

  @override
  String get employeeUnitLinkAbsent => 'No vinculado';

  @override
  String get employeeUnitLinksTitle => 'Vínculos por Unidad';

  @override
  String get employeeUnitLinksEmpty =>
      'Este colaborador no tiene vínculo con ninguna Unidad que usted pueda consultar.';

  @override
  String get employeeUnitLinksError => 'No se pudieron cargar los vínculos.';

  @override
  String get outsourcedReportsError => 'No fue posible cargar el informe.';

  @override
  String get outsourcedReportsEmpty =>
      'No hay empresas subcontratadas/prestadoras registradas.';

  @override
  String get outsourcedReportsActive => 'Activos';

  @override
  String get outsourcedReportsArchived => 'Archivados';

  @override
  String get moduleVisibilityTitle => 'Visibilidad de Módulos';

  @override
  String get moduleVisibilityDescription =>
      'Permisos predeterminados: cada perfil tiene permisos predeterminados definidos por el sistema. Personalizaciones: el Administrador General puede personalizar la visualización y el uso de los módulos por perfil y por unidad, sin alterar la estructura predeterminada del sistema.';

  @override
  String get moduleVisibilityRoleLabel => 'Perfil';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Permisos predeterminados de este perfil';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Estos permisos representan el comportamiento predeterminado del sistema. Las configuraciones siguientes solo permiten personalizaciones realizadas por el Administrador General.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ningún módulo por defecto';

  @override
  String get moduleVisibilityUnitLabel => 'Unidad';

  @override
  String get moduleVisibilityUnitHint =>
      'Un módulo no marcado específicamente para esta Unidad hereda el valor de \"Todas las unidades\".';

  @override
  String get moduleVisibilityAllUnitsOption =>
      'Todas las unidades (predeterminado)';

  @override
  String get stockTabAvailable => 'Disponibles';

  @override
  String get stockTabBlocked => 'Bloqueados';

  @override
  String get stockAvailableSelectEpi =>
      'Seleccione un EPI para ver los artículos disponibles';

  @override
  String get stockAvailableEmpty =>
      'No hay artículos disponibles para este EPI en esta unidad';

  @override
  String get stockBlockedEmpty => 'No hay artículos bloqueados';

  @override
  String get stockNoOperationalUnit =>
      'Su perfil no tiene una unidad operativa activa. Contacte al administrador para obtener acceso al inventario.';

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
  String get deliveryEmployeeWithoutUnit =>
      'Colaborador sin Unidad operativa: no se puede registrar la entrega.';

  @override
  String get deliveryQrOtherEpi => 'El código leído pertenece a otro EPP.';

  @override
  String get stockUnitRequiredToMove =>
      'Seleccione una Unidad para mover el stock.';

  @override
  String get stockAttentionSectionTitle => 'Existencias';

  @override
  String get stockAttentionCompanyTitle =>
      'Franja de atención — valor por defecto de la empresa';

  @override
  String get stockAttentionCompanyHelp =>
      'Se aplica a las Unidades que no han definido su propio porcentaje. No modifica ninguna Unidad ya configurada.';

  @override
  String get stockAttentionPercentageLabel =>
      'Porcentaje de la franja de atención';

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
  String get stockAttentionRestored =>
      'Valor de la empresa eliminado. La empresa vuelve al valor del sistema.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Valor del sistema: $value%';
  }

  @override
  String get stockConfigTitle => 'Configuración de existencias';

  @override
  String get stockConfigIntro =>
      'Define las existencias mínimas, la franja de atención y el monitoreo de alerta de un EPI en una Unidad. Cada parámetro se guarda por separado.';

  @override
  String get stockConfigUnitLabel => 'Unidad a configurar';

  @override
  String get stockConfigSelectUnit =>
      'Selecciona la Unidad para configurar sus parámetros.';

  @override
  String get stockConfigSelectEpi =>
      'Selecciona el EPI para ver y editar los parámetros de esta Unidad.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'No se pudo cargar la lista de EPI de esta Unidad.';

  @override
  String get stockConfigNoEpisInUnit => 'Ningún EPI es visible en esta Unidad.';

  @override
  String get stockConfigUnitBalance => 'Saldo en la Unidad';

  @override
  String get stockConfigAttentionLimit => 'Límite de la franja de atención';

  @override
  String get stockConfigUnderlyingStatus => 'Condición física';

  @override
  String get stockConfigDerivedUnavailable =>
      'Los valores calculados no se pudieron actualizar ahora. Los parámetros guardados arriba son correctos.';

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
  String get stockConfigMinimumHelp =>
      'Cantidad por debajo de la cual el EPI se considera crítico en esta Unidad. Solo vale para esta Unidad.';

  @override
  String get stockConfigMinimumLabel => 'Existencias mínimas';

  @override
  String get stockConfigMinimumNegativeError =>
      'Introduce un número entero igual o mayor que cero.';

  @override
  String get stockConfigMinimumSaved =>
      'Existencias mínimas guardadas para esta Unidad.';

  @override
  String get stockConfigMinimumRestored =>
      'Existencias mínimas restauradas. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAttentionTitle => 'Franja de atención';

  @override
  String get stockConfigAttentionHelp =>
      'Porcentaje por encima del mínimo en el que el EPI ya entra en atención en esta Unidad. Independiente de las existencias mínimas.';

  @override
  String get stockConfigAttentionRangeError =>
      'El porcentaje debe estar entre 0 y 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Franja de atención guardada para esta Unidad.';

  @override
  String get stockConfigAttentionRestored =>
      'Franja de atención restaurada. La Unidad vuelve a heredar el valor de la empresa.';

  @override
  String get stockConfigAlertTitle => 'Monitoreo de alerta';

  @override
  String get stockConfigAlertHelp =>
      'Desactivarlo detiene la alerta de existencias bajas y la reposición automática de este EPI en esta Unidad. No cambia el saldo, el mínimo ni el porcentaje.';

  @override
  String get stockConfigAlertToggle => 'Monitorear las existencias de este EPI';

  @override
  String get stockConfigAlertPending =>
      'Cambio pendiente. Pulsa Guardar para aplicarlo.';

  @override
  String get stockConfigAlertDisableTitle => '¿Desactivar la alerta?';

  @override
  String get stockConfigAlertDisableBody =>
      'Este EPI dejará de generar alertas de existencias bajas y reposición automática en esta Unidad. La condición física seguirá mostrándose.';

  @override
  String get stockConfigAlertDisableConfirm => 'Desactivar';

  @override
  String get stockConfigAlertSaved =>
      'Monitoreo de alerta guardado para esta Unidad.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoreo restaurado. La Unidad vuelve al valor del sistema.';

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
  String get stockAttentionLoadError =>
      'No se ha podido cargar el valor por defecto de la empresa.';

  @override
  String get unitSelectorLabel => 'Unidad';

  @override
  String get unitSelectorAllUnits => 'Todas las Unidades';

  @override
  String get unitSelectorLockedHint => 'Su perfil opera en una Unidad fija.';

  @override
  String get unitSelectorLoadError => 'No se han podido cargar las Unidades.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'No tiene ninguna Unidad asignada. Hable con el administrador.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'La empresa aún no tiene Unidades registradas.';

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
  String get settingsSelectCompanyFirst =>
      'Seleccione una empresa en Configuración para continuar.';

  @override
  String get settingsFichaTileTitle => 'Ficha de EPP';

  @override
  String get settingsFichaTileSubtitle =>
      'Título, declaración, observaciones y trazabilidad';

  @override
  String get settingsStockTileSubtitle =>
      'Franja de atención predeterminada de la empresa';

  @override
  String get settingsModulesTileSubtitle =>
      'Módulos visibles por perfil y por Unidad';

  @override
  String get settingsArchivalTitle => 'Archivado y retención';

  @override
  String get settingsArchivalSubtitle =>
      'Años de conservación de los registros archivados';

  @override
  String get settingsAppearanceTitle => 'Apariencia e idioma';

  @override
  String get settingsAppearanceSubtitle =>
      'Tema de la interfaz e idioma de la aplicación';

  @override
  String get settingsSubscriptionTileTitle => 'Mi suscripción';

  @override
  String get settingsSubscriptionTileSubtitle => 'Plan, cobros y cancelación';

  @override
  String get settingsInvoicesTileTitle => 'Historial financiero';

  @override
  String get settingsInvoicesTileSubtitle => 'Todos los cobros y recibos';

  @override
  String get settingsNoPermission =>
      'No tiene permiso para modificar esta configuración.';

  @override
  String get stockPhysicalValidityUnknown => 'Caducidad física desconocida';

  @override
  String get stockNoPhysicalStock => 'Sin existencias físicas';

  @override
  String get stockRegularizeValidityTitle => 'Regularizar validez física';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifique la pieza e indique la validez comprobada. La clasificación la realiza el sistema.';

  @override
  String get stockRegularizeQrLabel => 'QR o código de la pieza';

  @override
  String get stockRegularizeExpiryLabel => 'Validez física comprobada';

  @override
  String get stockRegularizeExpirySelect => 'Seleccionar fecha';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidencia (documento o registro verificable)';

  @override
  String get stockRegularizeJustificationLabel => 'Justificación';

  @override
  String get stockRegularizeSubmit => 'Regularizar';

  @override
  String get stockRegularizeIncomplete =>
      'Complete la pieza, la validez, la evidencia y la justificación.';

  @override
  String get stockRegularizeResultEligible =>
      'Validez regularizada. La pieza está habilitada para entrega y reserva.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validez regularizada. La pieza está vencida y permanece bloqueada para entrega.';

  @override
  String get stockRegularizeResultDone => 'Validez regularizada.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPI distintos: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Unidades físicas: válidas $valid, próximas $expiring, caducadas $expired, desconocidas $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Unidad no disponible para entrega. Revise caducidad física, estado, reservas y saldo.';

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
  String get safetyNoRecords =>
      'No hay registros publicados y autorizados en este contexto.';

  @override
  String get safetyCatalogueNotice =>
      'La aprobación del catálogo no indica disponibilidad física. El vencimiento del CA es distinto al del lote.';

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
  String get safetyPrivateNotice =>
      'Originales privados, versiones e historial conservados. Gestión restringida al Administrador General y al Administrador de Registro.';

  @override
  String get safetyAllowAdminDownloads =>
      'Permitir descargar originales a administradores autorizados';

  @override
  String get safetyPreviewOnlyNotice =>
      'Los colaboradores solo pueden consultar la vista previa.';

  @override
  String get safetyPolicyReason =>
      'Cambiar política de descarga administrativa';

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
  String get safetyActivities =>
      'Actividades/funciones separadas por comas (vacío = todas)';

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
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
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

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Línea $line — $item (artículo #$id): cantidad efectivamente recibida inválida o no positiva. Corrija la recepción antes de confirmar.';
  }
}
