// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

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
  String get employeeCpfLabel => 'Brazilian CPF';

  @override
  String get employeeSectorLabel => 'Department';

  @override
  String get employeeRoleLabel => 'Job title';

  @override
  String get employeeUnitLabel => 'Unit';

  @override
  String get employeeUnitLockedHint => 'Unit set by your access profile.';

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
  String get episSearchHint => 'Search by name, Brazilian CA or code';

  @override
  String get epiNameLabel => 'PPE name';

  @override
  String get epiCodeLabel => 'Purchase code';

  @override
  String get epiCaLabel => 'CA — Brazilian Approval Certificate';

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
  String get epiCaExpiryLabel => 'Brazilian CA expiry';

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
  String get epiArchiveBlockTitle => 'Archive with stock blocking';

  @override
  String get epiArchiveBlockBody =>
      'This PPE has available stock or active links. On confirming, the available stock is moved to Blocked Stock (traceable) and the PPE is archived.';

  @override
  String get epiArchiveBlockConfirm => 'Block stock and archive';

  @override
  String get epiArchiveReasonLabel => 'Archive reason (audit)';

  @override
  String get epiArchiveReasonRequired => 'Enter a reason to continue.';

  @override
  String get epiArchiveBlockableLabel => 'Stock to block';

  @override
  String get epiArchiveLiveLinksTitle => 'Active links';

  @override
  String get epiArchiveAvailable => 'Available';

  @override
  String get epiArchiveInTransit => 'In transit';

  @override
  String get epiArchiveInPossession => 'In possession';

  @override
  String get epiArchivePendingRequests => 'Open requests';

  @override
  String get epiArchivePendingPurchase => 'Open purchases';

  @override
  String get dashboardComplianceTitle => 'Stock compliance';

  @override
  String get dashboardComplianceAllOk => 'Stock is compliant';

  @override
  String get complianceCaExpired => 'CA expired';

  @override
  String get complianceCaExpiring => 'CA expiring';

  @override
  String get complianceProductExpired => 'Product expired';

  @override
  String get complianceProductExpiring => 'Product expiring';

  @override
  String get complianceMissingManufacture => 'No manufacture date';

  @override
  String get complianceMissingLot => 'No lot';

  @override
  String get complianceAdminBlocked => 'Blocked';

  @override
  String get handoverTitle => 'Delivery handover';

  @override
  String get handoverPrompt => 'Scan the delivery QR or enter the code.';

  @override
  String get handoverCodeLabel => 'Delivery code';

  @override
  String get handoverLookupButton => 'Look up delivery';

  @override
  String get handoverScanButton => 'Scan QR';

  @override
  String get handoverConfirmButton => 'Confirm receipt';

  @override
  String get handoverConfirmedTitle => 'Receipt confirmed';

  @override
  String get handoverAlreadyConfirmed => 'This delivery was already confirmed.';

  @override
  String get handoverNotFound => 'No delivery found for this code.';

  @override
  String get handoverConfirmError => 'Could not confirm receipt.';

  @override
  String get handoverEmployeeLabel => 'Employee';

  @override
  String get handoverEpiLabel => 'PPE';

  @override
  String get handoverQuantityLabel => 'Quantity';

  @override
  String get handoverSectorLabel => 'Sector';

  @override
  String get handoverRoleLabel => 'Role';

  @override
  String get handoverUnitLabel => 'Unit';

  @override
  String get handoverDeliveryDateLabel => 'Delivery date';

  @override
  String get handoverReceiverNameLabel => 'Receiver name (optional)';

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
  String get legalEntityCnpjLabel => 'CNPJ (Brazilian tax ID)';

  @override
  String get legalEntityUfLabel => 'State';

  @override
  String get legalEntitiesImportColumnsHint =>
      'Tax ID\tLegal name\tTrade name\tType';

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
  String get unitTransferTitle => 'Transfer unit';

  @override
  String get unitTransferHint =>
      'Operational unit movement — temporary or definitive. Creates an auditable record and does not change the employee\'s tax ID (CNPJ).';

  @override
  String get unitTransferTarget => 'Target unit';

  @override
  String get unitTransferType => 'Movement type';

  @override
  String get unitTransferTypeTemporary => 'Temporary';

  @override
  String get unitTransferTypeDefinitive => 'Definitive';

  @override
  String get unitTransferStartDate => 'Start date';

  @override
  String get unitTransferEndDate => 'End date (optional)';

  @override
  String get unitTransferNotes => 'Notes (optional)';

  @override
  String get unitTransferAction => 'Transfer';

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

  @override
  String get navTerceirizados => 'Outsourced & Contractors';

  @override
  String get outsourcedCompaniesTitle => 'Outsourced & Contractors';

  @override
  String get outsourcedCompaniesEmpty => 'No outsourced company registered.';

  @override
  String get outsourcedCompaniesSearchHint => 'Search by name or Tax ID';

  @override
  String get outsourcedCompanyNew => 'New company';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Legal Name';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Trade Name';

  @override
  String get outsourcedCompanyCnpjLabel => 'Tax ID';

  @override
  String get outsourcedCompanyCnpjHint =>
      'Optional in the Simplified Registration';

  @override
  String get outsourcedCompanyKindLabel => 'Company Type';

  @override
  String get outsourcedCompanyKindOutsourced => 'Outsourced';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Service Provider';

  @override
  String get outsourcedCompanyKindOther => 'Other';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'PPE Supply Responsibility';

  @override
  String get outsourcedCompanyUnitLabel => 'Unit';

  @override
  String get outsourcedCompanyUnitAll => 'All units (default)';

  @override
  String get outsourcedCompanyLinkTitle => 'Link company to this Unit';

  @override
  String get outsourcedCompanyLinkHint =>
      'Search a company already registered in the tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Already linked to this Unit';

  @override
  String get outsourcedCompanyLinkSectionAvailable => 'Available to link';

  @override
  String get outsourcedCompanyLinkLink => 'Link to this Unit';

  @override
  String get outsourcedCompanyLinkActivate => 'Reactivate in this Unit';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archive in this Unit';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Reason for archiving (optional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Used by $count Unit(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Origin Unit';

  @override
  String get outsourcedCompanyLinkEmpty => 'No company found for this term.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Link state not reported for your profile';

  @override
  String get outsourcedCompanyStatusLabel => 'Status';

  @override
  String get outsourcedCompanySave => 'Save';

  @override
  String get outsourcedCompanyCancel => 'Cancel';

  @override
  String get outsourcedCompanyPromote => 'Promote to Standard Registration';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Promote to Standard Registration?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'The company will be treated as a Standard Registration. A Tax ID is required.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplified';

  @override
  String get outsourcedCompanyStandardBadge => 'Standard';

  @override
  String get outsourcedTabCompanies => 'Companies';

  @override
  String get outsourcedTabEmployees => 'Employee Registration';

  @override
  String get outsourcedTabReports => 'Reports';

  @override
  String get outsourcedShowActive => 'Show active';

  @override
  String get outsourcedShowArchived => 'Show archived';

  @override
  String get archive => 'Archive';

  @override
  String get restore => 'Restore';

  @override
  String get archivedAt => 'Archived on';

  @override
  String get archiveReasonLabel => 'Archiving reason (audit)';

  @override
  String get outsourcedCompanyArchive => 'Archive company';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => 'Archive this company?';

  @override
  String get outsourcedCompanyRestore => 'Restore';

  @override
  String get outsourcedCompanyRestoreConfirmTitle => 'Restore this company?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'No archived outsourced companies.';

  @override
  String get outsourcedEmployeeNew => 'New employee';

  @override
  String get outsourcedEmployeesEmpty =>
      'No outsourced/contracted employees registered.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'No archived outsourced/contracted employees.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Outsourced/contracted company';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Origin company registration number';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Badge';

  @override
  String get outsourcedEmployeeNotesLabel => 'Notes';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle => 'Archive this employee?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle => 'Restore this employee?';

  @override
  String get employeeUnitLinkColumn => 'Local link';

  @override
  String get employeeUnitLink => 'Link to my unit';

  @override
  String get employeeUnitLinkActivate => 'Reactivate in this Unit';

  @override
  String get employeeUnitLinkDeactivate => 'Archive in this Unit';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Reason for archiving (optional):';

  @override
  String get employeeUnitLinkActive => 'Linked';

  @override
  String get employeeUnitLinkArchived => 'Archived in this Unit';

  @override
  String get employeeUnitLinkAbsent => 'Not linked';

  @override
  String get employeeUnitLinksTitle => 'Links by Unit';

  @override
  String get employeeUnitLinksEmpty =>
      'This employee has no link with any Unit you are allowed to see.';

  @override
  String get employeeUnitLinksError => 'Could not load the links.';

  @override
  String get outsourcedReportsError => 'Could not load the report.';

  @override
  String get outsourcedReportsEmpty =>
      'No outsourced/contracted companies registered.';

  @override
  String get outsourcedReportsActive => 'Active';

  @override
  String get outsourcedReportsArchived => 'Archived';

  @override
  String get moduleVisibilityTitle => 'Module Visibility';

  @override
  String get moduleVisibilityDescription =>
      'Default permissions: each role has default permissions defined by the system. Customizations: the General Admin can customize module visibility and usage per role and per unit, without changing the system\'s default structure.';

  @override
  String get moduleVisibilityRoleLabel => 'Role';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Default permissions for this role';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'These permissions represent the system\'s default behavior. The settings below only allow customizations made by the General Admin.';

  @override
  String get moduleVisibilityNoDefaultModules => 'No modules by default';

  @override
  String get moduleVisibilityUnitLabel => 'Unit';

  @override
  String get moduleVisibilityUnitHint =>
      'A module not specifically set for this Unit inherits the value from \"All units\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'All units (default)';

  @override
  String get stockTabAvailable => 'Available';

  @override
  String get stockTabBlocked => 'Blocked';

  @override
  String get stockAvailableSelectEpi => 'Select a PPE to see available items';

  @override
  String get stockAvailableEmpty =>
      'No items available for this PPE at this unit';

  @override
  String get stockBlockedEmpty => 'No blocked items';

  @override
  String get stockNoOperationalUnit =>
      'Your profile has no active operational unit. Contact an administrator to get stock access.';

  @override
  String get stockItemLotLabel => 'Lot';

  @override
  String get stockStatusBlockedExpired => 'Expired';

  @override
  String get stockStatusBlockedDiscard => 'Awaiting disposal';

  @override
  String get stockStatusBlockedReturn => 'Awaiting return to supplier';

  @override
  String get stockStatusBlockedAnalysis => 'Under analysis';

  @override
  String get stockStatusBlockedRejected => 'Rejected';

  @override
  String get stockStatusBlockedArchived => 'Archived PPE';

  @override
  String get stockStatusUnknown => 'Unrecognized status';

  @override
  String get stockUnitBalanceSuffix => 'at this unit';

  @override
  String get stockCompanyBalanceLabel => 'company';

  @override
  String get stockMinimumShort => 'min';

  @override
  String get deliveryStepItem => 'Item';

  @override
  String get deliveryItemTitle => 'Select the labelled unit';

  @override
  String get deliveryItemEmpty => 'No item available in this Unit.';

  @override
  String get deliveryItemScan => 'Scan item QR';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Unit stock: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Employee has no operational Unit: delivery cannot be recorded.';

  @override
  String get deliveryQrOtherEpi => 'The scanned code belongs to another PPE.';

  @override
  String get stockUnitRequiredToMove => 'Select a Unit to move stock.';

  @override
  String get stockAttentionSectionTitle => 'Stock';

  @override
  String get stockAttentionCompanyTitle => 'Attention range — company default';

  @override
  String get stockAttentionCompanyHelp =>
      'Applies to Units that have not set their own percentage. It does not change any Unit already configured.';

  @override
  String get stockAttentionPercentageLabel => 'Attention range percentage';

  @override
  String get stockAttentionOriginLabel => 'Source';

  @override
  String get stockAttentionOriginCompany => 'Set by the company';

  @override
  String get stockAttentionOriginSystem => 'System default';

  @override
  String get stockAttentionSave => 'Save company default';

  @override
  String get stockAttentionRestore => 'Restore system default';

  @override
  String get stockAttentionSaved => 'Company default saved.';

  @override
  String get stockAttentionRestored =>
      'Company default removed. The company is back on the system default.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'System default: $value%';
  }

  @override
  String get stockConfigTitle => 'Stock settings';

  @override
  String get stockConfigIntro =>
      'Set the minimum stock, attention range and alert monitoring of one PPE in one Unit. Each parameter is saved separately.';

  @override
  String get stockConfigUnitLabel => 'Unit to configure';

  @override
  String get stockConfigSelectUnit =>
      'Select the Unit to configure its parameters.';

  @override
  String get stockConfigSelectEpi =>
      'Select the PPE to view and edit this Unit’s parameters.';

  @override
  String get stockConfigEpiLabel => 'PPE';

  @override
  String get stockConfigEpisLoadError =>
      'Could not load the PPE list for this Unit.';

  @override
  String get stockConfigNoEpisInUnit => 'No PPE is visible in this Unit.';

  @override
  String get stockConfigUnitBalance => 'Unit balance';

  @override
  String get stockConfigAttentionLimit => 'Attention range limit';

  @override
  String get stockConfigUnderlyingStatus => 'Physical condition';

  @override
  String get stockConfigDerivedUnavailable =>
      'The calculated values could not be refreshed right now. The parameters saved above are correct.';

  @override
  String get stockConfigStatusCritical => 'Critical';

  @override
  String get stockConfigStatusNearMinimum => 'Near minimum';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alert disabled';

  @override
  String get stockConfigMinimumTitle => 'Minimum stock';

  @override
  String get stockConfigMinimumHelp =>
      'Quantity below which the PPE counts as critical in this Unit. Applies to this Unit only.';

  @override
  String get stockConfigMinimumLabel => 'Minimum stock';

  @override
  String get stockConfigMinimumNegativeError =>
      'Enter a whole number of zero or more.';

  @override
  String get stockConfigMinimumSaved => 'Minimum stock saved for this Unit.';

  @override
  String get stockConfigMinimumRestored =>
      'Minimum stock restored. The Unit inherits the company default again.';

  @override
  String get stockConfigAttentionTitle => 'Attention range';

  @override
  String get stockConfigAttentionHelp =>
      'Percentage above the minimum at which the PPE already enters attention in this Unit. Independent of the minimum stock.';

  @override
  String get stockConfigAttentionRangeError =>
      'The percentage must be between 0 and 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Attention range saved for this Unit.';

  @override
  String get stockConfigAttentionRestored =>
      'Attention range restored. The Unit inherits the company default again.';

  @override
  String get stockConfigAlertTitle => 'Alert monitoring';

  @override
  String get stockConfigAlertHelp =>
      'Turning this off stops low-stock alerts and automatic replenishment for this PPE in this Unit. It does not change balance, minimum or percentage.';

  @override
  String get stockConfigAlertToggle => 'Monitor this PPE’s stock';

  @override
  String get stockConfigAlertPending => 'Unsaved change. Click Save to apply.';

  @override
  String get stockConfigAlertDisableTitle => 'Disable the alert?';

  @override
  String get stockConfigAlertDisableBody =>
      'This PPE will stop generating low-stock alerts and automatic replenishment in this Unit. The physical condition will still be shown.';

  @override
  String get stockConfigAlertDisableConfirm => 'Disable';

  @override
  String get stockConfigAlertSaved => 'Alert monitoring saved for this Unit.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoring restored. The Unit is back on the system default.';

  @override
  String get stockConfigOriginUnit => 'Set by this Unit';

  @override
  String get stockConfigOriginCompany => 'Inherited from the company default';

  @override
  String get stockConfigOriginUnknown => 'Not reported';

  @override
  String get stockConfigSave => 'Save';

  @override
  String get stockConfigRestore => 'Restore inheritance';

  @override
  String stockAttentionRangeError(int max) {
    return 'Enter a whole percentage between 0 and $max.';
  }

  @override
  String get stockAttentionLoadError => 'Could not load the company default.';

  @override
  String get unitSelectorLabel => 'Unit';

  @override
  String get unitSelectorAllUnits => 'All Units';

  @override
  String get unitSelectorLockedHint => 'Your profile operates in a fixed Unit.';

  @override
  String get unitSelectorLoadError => 'Could not load the Units.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'You have no Unit assigned. Contact your administrator.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'The company has no Units registered yet.';

  @override
  String get settingsSectionCompany => 'Company';

  @override
  String get settingsSectionOperation => 'Operations';

  @override
  String get settingsSectionSubscription => 'Subscription';

  @override
  String get settingsCompanyLabel => 'Company';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Managing company: $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Select a company in Settings to continue.';

  @override
  String get settingsFichaTileTitle => 'PPE record';

  @override
  String get settingsFichaTileSubtitle =>
      'Title, declaration, notes and traceability';

  @override
  String get settingsStockTileSubtitle => 'Company default attention threshold';

  @override
  String get settingsModulesTileSubtitle =>
      'Modules visible per role and per Unit';

  @override
  String get settingsArchivalTitle => 'Archiving and retention';

  @override
  String get settingsArchivalSubtitle => 'Years archived records are preserved';

  @override
  String get settingsAppearanceTitle => 'Appearance and language';

  @override
  String get settingsAppearanceSubtitle => 'Interface theme and app language';

  @override
  String get settingsSubscriptionTileTitle => 'My subscription';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Plan, charges and cancellation';

  @override
  String get settingsInvoicesTileTitle => 'Billing history';

  @override
  String get settingsInvoicesTileSubtitle => 'All charges and receipts';

  @override
  String get settingsNoPermission =>
      'You do not have permission to change this setting.';

  @override
  String get stockPhysicalValidityUnknown => 'Unknown physical expiry';

  @override
  String get stockNoPhysicalStock => 'No physical stock';

  @override
  String get stockRegularizeValidityTitle => 'Regularize physical validity';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identify the piece and enter the verified expiry date. Classification is done by the system.';

  @override
  String get stockRegularizeQrLabel => 'QR or piece code';

  @override
  String get stockRegularizeExpiryLabel => 'Verified physical expiry date';

  @override
  String get stockRegularizeExpirySelect => 'Select date';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidence (document or verifiable record)';

  @override
  String get stockRegularizeJustificationLabel => 'Justification';

  @override
  String get stockRegularizeSubmit => 'Regularize';

  @override
  String get stockRegularizeIncomplete =>
      'Fill in the piece, the expiry date, the evidence and the justification.';

  @override
  String get stockRegularizeResultEligible =>
      'Validity regularized. The piece is eligible for delivery and reservation.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validity regularized. The piece is expired and remains blocked for delivery.';

  @override
  String get stockRegularizeResultDone => 'Validity regularized.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — distinct PPE types: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Physical pieces: valid $valid, expiring $expiring, expired $expired, unknown $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Item unavailable for delivery. Check physical expiry, status, reservations and balance.';

  @override
  String get safetyTitle => 'Safety Library';

  @override
  String get safetyApproved => 'Approved PPE';

  @override
  String get safetyRetry => 'Try again';

  @override
  String get safetyClose => 'Close';

  @override
  String get safetyCancel => 'Cancel';

  @override
  String get safetyConfirm => 'Confirm';

  @override
  String get safetyAccess => 'Continue';

  @override
  String get safetyPortalConfirm => 'Confirm portal access';

  @override
  String get safetyCpfLast => 'Last three CPF digits';

  @override
  String get safetyView => 'View';

  @override
  String get safetyFit => 'Fit page';

  @override
  String get safetyZoomIn => 'Zoom in';

  @override
  String get safetyZoomOut => 'Zoom out';

  @override
  String get safetyNextPage => 'Next page';

  @override
  String get safetyPreviousPage => 'Previous page';

  @override
  String get safetyDocument => 'Document';

  @override
  String get safetyDetails => 'Details';

  @override
  String get safetyRelatedDocuments => 'Related documents';

  @override
  String get safetyRelatedEpis => 'Related PPE';

  @override
  String get safetyRelatedEpi => 'Related PPE';

  @override
  String get safetyAllEpis => 'All PPE';

  @override
  String get safetyAllCategories => 'All categories';

  @override
  String get safetyNoDocs => 'No documents published for this context.';

  @override
  String get safetyNoRecords =>
      'No published, authorized records in this context.';

  @override
  String get safetyCatalogueNotice =>
      'Catalogue approval does not indicate physical availability. CA expiry is separate from batch expiry.';

  @override
  String get safetyName => 'PPE';

  @override
  String get safetyManufacturer => 'Manufacturer';

  @override
  String get safetyModel => 'Model/reference';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'CA expiry';

  @override
  String get safetyUsefulLife => 'Service life (months)';

  @override
  String get safetyProtection => 'Protection';

  @override
  String get safetySection => 'Section';

  @override
  String get safetyRecommendations => 'Recommendations/restrictions';

  @override
  String get safetyUnknown => 'Not provided';

  @override
  String get safetySearch => 'Search';

  @override
  String get safetyViewEpi => 'View PPE';

  @override
  String get safetyHistory => 'History';

  @override
  String get safetyDocumentHistory => 'Document history';

  @override
  String get safetyPublish => 'Publish';

  @override
  String get safetyPublishVersion => 'Publish version';

  @override
  String get safetyArchive => 'Archive document';

  @override
  String get safetyArchiveVersions => 'Archive document and versions';

  @override
  String get safetyReason => 'Required justification';

  @override
  String get safetyNew => 'New document';

  @override
  String get safetyCreateNew => 'Create new document';

  @override
  String get safetyMetadata => 'Version details';

  @override
  String get safetyEmptyAdmin => 'No documents registered.';

  @override
  String get safetyPrivateNotice =>
      'Private originals, preserved versions and history. Management restricted to General and Registry Administrators.';

  @override
  String get safetyAllowAdminDownloads =>
      'Allow original downloads for authorized administrators';

  @override
  String get safetyPreviewOnlyNotice =>
      'Employees always have preview-only access.';

  @override
  String get safetyPolicyReason => 'Change administrator download policy';

  @override
  String get safetySearchVersions => 'Search title or version';

  @override
  String get safetyChooseFile => 'Choose file';

  @override
  String get safetyFilePickerLabel => 'Safety documents';

  @override
  String get safetyUnitRequired => 'Select at least one unit';

  @override
  String get safetyAllUnits => 'All company units';

  @override
  String get safetyRequired => 'Required';

  @override
  String get safetyDocumentTitle => 'Title';

  @override
  String get safetyVersion => 'Version';

  @override
  String get safetyEffectiveDate => 'Effective date (YYYY-MM-DD)';

  @override
  String get safetySectors => 'Comma-separated sectors (empty = all)';

  @override
  String get safetyActivities =>
      'Comma-separated activities/roles (empty = all)';

  @override
  String get safetyUpload => 'Register or version document';

  @override
  String get safetyRendering => 'Generating safe preview…';

  @override
  String get safetyFileLimit => 'Select a file up to 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Version $version · Effective $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Viewing unit: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Preview unavailable: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Upload rejected; preview unavailable: $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Version $version / revision $revision · $state · Effective $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsible user $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'PPE Application Matrix';

  @override
  String get safetyCategoryGlove => 'Glove Selection Matrix';

  @override
  String get safetyCategoryCare => 'Cleaning and Care Guides';

  @override
  String get safetyCategoryUse => 'PPE Use Instructions';

  @override
  String get safetyCategoryTechnical => 'Manuals and Technical Sheets';

  @override
  String get safetyCategoryOther => 'Other Safety Documents';

  @override
  String get safetyStateDraft => 'Draft';

  @override
  String get safetyStatePublished => 'Published';

  @override
  String get safetyStateSuperseded => 'Superseded';

  @override
  String get safetyStateArchived => 'Archived';

  @override
  String get prConfTitle => 'Receipt Conference';

  @override
  String get prConfIntro =>
      'Tick each item as actually received. Enter the manufacturer physical validity and verifiable evidence; use \"Split into lots\" for different validities or individual exceptions. Pieces without proven validity enter BLOCKED.';

  @override
  String get prConfReceivedYes => 'Received';

  @override
  String get prConfReceivedNo => 'Not received';

  @override
  String get prConfEvidence => 'Verifiable evidence';

  @override
  String get prConfEvidenceHint => 'Label / invoice / photo';

  @override
  String get prConfEvidenceRequired =>
      'Verifiable evidence is required when a validity is set.';

  @override
  String get prConfSplitLots => 'Split into lots';

  @override
  String get prConfSingleDate => 'Use single date';

  @override
  String get prConfAddLot => 'Add lot';

  @override
  String get prConfAddException => 'Exception (1 piece)';

  @override
  String get prConfLotQty => 'Qty';

  @override
  String get prConfLotCode => 'Identification';

  @override
  String get prConfRemoveLot => 'Remove lot';

  @override
  String get prConfPreview => 'Preview — physical validity per piece';

  @override
  String get prConfBlocked => 'NO validity → BLOCKED';

  @override
  String get prConfExpired => 'expired';

  @override
  String get prConfPiece => 'piece(s)';

  @override
  String get prConfSumMismatch =>
      'The sum of lot quantities does not match the received quantity.';

  @override
  String get prConfLotQtyPositive =>
      'Each lot needs a quantity greater than zero.';

  @override
  String get prConfNotes => 'Notes about items not received';

  @override
  String get prConfNotesRequired => 'Enter the notes about items not received.';

  @override
  String get prConfSubmit => 'Register Conference';

  @override
  String get prConfDone => 'Conference registered.';

  @override
  String get prConfEmpty => 'No item eligible for conference.';

  @override
  String get prConfInvalidQuantity =>
      'Effective received quantity is invalid or non-positive. Correct the receipt before confirming.';

  @override
  String get prConfNoPersistedPieces =>
      'No pieces were actually recorded, or the response is inconsistent. Stock entry was not confirmed.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count pieces actually recorded in stock.';
  }

  @override
  String get prConfNoStockEntry =>
      'Conference saved without adding pieces to stock.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Line $line — $item (item #$id): effective received quantity is invalid or non-positive. Correct the receipt before confirming.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Stock approaching minimum: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Negative stock balance: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Out of stock: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Stock below minimum: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Stock at minimum: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - current balance: $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'Brazilian CA approaching expiry: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - expires on $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Manufacturer expiry date passed: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Manufacturer expiry date approaching: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - manufacturer expiry date: $date. Remove from stock ($stock $measure): expired PPE must not be issued to workers.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - manufacturer expiry date: $date (in $daysLabel). Prioritise issuing this batch ($stock $measure in stock) before expiry (FIFO).';
  }

  @override
  String get operationalAlertSizes => 'Sizes in stock:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Glove:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Size:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Uniform:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Unspecified size';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'units',
      one: 'unit',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'pairs',
      one: 'pair',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel days',
      one: '$countLabel day',
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
      other: '$epi: $countLabel physical items.',
      one: '$epi: $countLabel physical item.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Unknown physical expiry date';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Batches approaching expiry';
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
  String get employeeCpfLabel => 'Brazilian CPF';

  @override
  String get employeeSectorLabel => 'Department';

  @override
  String get employeeRoleLabel => 'Job title';

  @override
  String get employeeUnitLabel => 'Unit';

  @override
  String get employeeUnitLockedHint => 'Unit set by your access profile.';

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
  String get episSearchHint => 'Search by name, Brazilian CA or code';

  @override
  String get epiNameLabel => 'PPE name';

  @override
  String get epiCodeLabel => 'Purchase code';

  @override
  String get epiCaLabel => 'CA — Brazilian Approval Certificate';

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
  String get epiCaExpiryLabel => 'Brazilian CA expiry';

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
  String get epiArchiveBlockTitle => 'Archive with stock blocking';

  @override
  String get epiArchiveBlockBody =>
      'This PPE has available stock or active links. On confirming, the available stock is moved to Blocked Stock (traceable) and the PPE is archived.';

  @override
  String get epiArchiveBlockConfirm => 'Block stock and archive';

  @override
  String get epiArchiveReasonLabel => 'Archive reason (audit)';

  @override
  String get epiArchiveReasonRequired => 'Enter a reason to continue.';

  @override
  String get epiArchiveBlockableLabel => 'Stock to block';

  @override
  String get epiArchiveLiveLinksTitle => 'Active links';

  @override
  String get epiArchiveAvailable => 'Available';

  @override
  String get epiArchiveInTransit => 'In transit';

  @override
  String get epiArchiveInPossession => 'In possession';

  @override
  String get epiArchivePendingRequests => 'Open requests';

  @override
  String get epiArchivePendingPurchase => 'Open purchases';

  @override
  String get dashboardComplianceTitle => 'Stock compliance';

  @override
  String get dashboardComplianceAllOk => 'Stock is compliant';

  @override
  String get complianceCaExpired => 'CA expired';

  @override
  String get complianceCaExpiring => 'CA expiring';

  @override
  String get complianceProductExpired => 'Product expired';

  @override
  String get complianceProductExpiring => 'Product expiring';

  @override
  String get complianceMissingManufacture => 'No manufacture date';

  @override
  String get complianceMissingLot => 'No lot';

  @override
  String get complianceAdminBlocked => 'Blocked';

  @override
  String get handoverTitle => 'Delivery handover';

  @override
  String get handoverPrompt => 'Scan the delivery QR or enter the code.';

  @override
  String get handoverCodeLabel => 'Delivery code';

  @override
  String get handoverLookupButton => 'Look up delivery';

  @override
  String get handoverScanButton => 'Scan QR';

  @override
  String get handoverConfirmButton => 'Confirm receipt';

  @override
  String get handoverConfirmedTitle => 'Receipt confirmed';

  @override
  String get handoverAlreadyConfirmed => 'This delivery was already confirmed.';

  @override
  String get handoverNotFound => 'No delivery found for this code.';

  @override
  String get handoverConfirmError => 'Could not confirm receipt.';

  @override
  String get handoverEmployeeLabel => 'Employee';

  @override
  String get handoverEpiLabel => 'PPE';

  @override
  String get handoverQuantityLabel => 'Quantity';

  @override
  String get handoverSectorLabel => 'Sector';

  @override
  String get handoverRoleLabel => 'Role';

  @override
  String get handoverUnitLabel => 'Unit';

  @override
  String get handoverDeliveryDateLabel => 'Delivery date';

  @override
  String get handoverReceiverNameLabel => 'Receiver name (optional)';

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
  String get legalEntityCnpjLabel => 'CNPJ (Brazilian tax ID)';

  @override
  String get legalEntityUfLabel => 'State';

  @override
  String get legalEntitiesImportColumnsHint =>
      'Tax ID\tLegal name\tTrade name\tType';

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
  String get unitTransferTitle => 'Transfer unit';

  @override
  String get unitTransferHint =>
      'Operational unit movement — temporary or definitive. Creates an auditable record and does not change the employee\'s tax ID (CNPJ).';

  @override
  String get unitTransferTarget => 'Target unit';

  @override
  String get unitTransferType => 'Movement type';

  @override
  String get unitTransferTypeTemporary => 'Temporary';

  @override
  String get unitTransferTypeDefinitive => 'Definitive';

  @override
  String get unitTransferStartDate => 'Start date';

  @override
  String get unitTransferEndDate => 'End date (optional)';

  @override
  String get unitTransferNotes => 'Notes (optional)';

  @override
  String get unitTransferAction => 'Transfer';

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

  @override
  String get navTerceirizados => 'Outsourced & Contractors';

  @override
  String get outsourcedCompaniesTitle => 'Outsourced & Contractors';

  @override
  String get outsourcedCompaniesEmpty => 'No outsourced company registered.';

  @override
  String get outsourcedCompaniesSearchHint => 'Search by name or Tax ID';

  @override
  String get outsourcedCompanyNew => 'New company';

  @override
  String get outsourcedCompanyLegalNameLabel => 'Legal Name';

  @override
  String get outsourcedCompanyTradeNameLabel => 'Trade Name';

  @override
  String get outsourcedCompanyCnpjLabel => 'Tax ID';

  @override
  String get outsourcedCompanyCnpjHint =>
      'Optional in the Simplified Registration';

  @override
  String get outsourcedCompanyKindLabel => 'Company Type';

  @override
  String get outsourcedCompanyKindOutsourced => 'Outsourced';

  @override
  String get outsourcedCompanyKindServiceProvider => 'Service Provider';

  @override
  String get outsourcedCompanyKindOther => 'Other';

  @override
  String get outsourcedCompanyResponsibilityLabel =>
      'PPE Supply Responsibility';

  @override
  String get outsourcedCompanyUnitLabel => 'Unit';

  @override
  String get outsourcedCompanyUnitAll => 'All units (default)';

  @override
  String get outsourcedCompanyLinkTitle => 'Link company to this Unit';

  @override
  String get outsourcedCompanyLinkHint =>
      'Search a company already registered in the tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Already linked to this Unit';

  @override
  String get outsourcedCompanyLinkSectionAvailable => 'Available to link';

  @override
  String get outsourcedCompanyLinkLink => 'Link to this Unit';

  @override
  String get outsourcedCompanyLinkActivate => 'Reactivate in this Unit';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archive in this Unit';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Reason for archiving (optional):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Used by $count Unit(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Origin Unit';

  @override
  String get outsourcedCompanyLinkEmpty => 'No company found for this term.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Link state not reported for your profile';

  @override
  String get outsourcedCompanyStatusLabel => 'Status';

  @override
  String get outsourcedCompanySave => 'Save';

  @override
  String get outsourcedCompanyCancel => 'Cancel';

  @override
  String get outsourcedCompanyPromote => 'Promote to Standard Registration';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Promote to Standard Registration?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'The company will be treated as a Standard Registration. A Tax ID is required.';

  @override
  String get outsourcedCompanySimplifiedBadge => 'Simplified';

  @override
  String get outsourcedCompanyStandardBadge => 'Standard';

  @override
  String get outsourcedTabCompanies => 'Companies';

  @override
  String get outsourcedTabEmployees => 'Employee Registration';

  @override
  String get outsourcedTabReports => 'Reports';

  @override
  String get outsourcedShowActive => 'Show active';

  @override
  String get outsourcedShowArchived => 'Show archived';

  @override
  String get archive => 'Archive';

  @override
  String get restore => 'Restore';

  @override
  String get archivedAt => 'Archived on';

  @override
  String get archiveReasonLabel => 'Archiving reason (audit)';

  @override
  String get outsourcedCompanyArchive => 'Archive company';

  @override
  String get outsourcedCompanyArchiveConfirmTitle => 'Archive this company?';

  @override
  String get outsourcedCompanyRestore => 'Restore';

  @override
  String get outsourcedCompanyRestoreConfirmTitle => 'Restore this company?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'No archived outsourced companies.';

  @override
  String get outsourcedEmployeeNew => 'New employee';

  @override
  String get outsourcedEmployeesEmpty =>
      'No outsourced/contracted employees registered.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'No archived outsourced/contracted employees.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Outsourced/contracted company';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Origin company registration number';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Badge';

  @override
  String get outsourcedEmployeeNotesLabel => 'Notes';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle => 'Archive this employee?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle => 'Restore this employee?';

  @override
  String get employeeUnitLinkColumn => 'Local link';

  @override
  String get employeeUnitLink => 'Link to my unit';

  @override
  String get employeeUnitLinkActivate => 'Reactivate in this Unit';

  @override
  String get employeeUnitLinkDeactivate => 'Archive in this Unit';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Reason for archiving (optional):';

  @override
  String get employeeUnitLinkActive => 'Linked';

  @override
  String get employeeUnitLinkArchived => 'Archived in this Unit';

  @override
  String get employeeUnitLinkAbsent => 'Not linked';

  @override
  String get employeeUnitLinksTitle => 'Links by Unit';

  @override
  String get employeeUnitLinksEmpty =>
      'This employee has no link with any Unit you are allowed to see.';

  @override
  String get employeeUnitLinksError => 'Could not load the links.';

  @override
  String get outsourcedReportsError => 'Could not load the report.';

  @override
  String get outsourcedReportsEmpty =>
      'No outsourced/contracted companies registered.';

  @override
  String get outsourcedReportsActive => 'Active';

  @override
  String get outsourcedReportsArchived => 'Archived';

  @override
  String get moduleVisibilityTitle => 'Module Visibility';

  @override
  String get moduleVisibilityDescription =>
      'Default permissions: each role has default permissions defined by the system. Customizations: the General Admin can customize module visibility and usage per role and per unit, without changing the system\'s default structure.';

  @override
  String get moduleVisibilityRoleLabel => 'Role';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Default permissions for this role';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'These permissions represent the system\'s default behavior. The settings below only allow customizations made by the General Admin.';

  @override
  String get moduleVisibilityNoDefaultModules => 'No modules by default';

  @override
  String get moduleVisibilityUnitLabel => 'Unit';

  @override
  String get moduleVisibilityUnitHint =>
      'A module not specifically set for this Unit inherits the value from \"All units\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'All units (default)';

  @override
  String get stockTabAvailable => 'Available';

  @override
  String get stockTabBlocked => 'Blocked';

  @override
  String get stockAvailableSelectEpi => 'Select a PPE to see available items';

  @override
  String get stockAvailableEmpty =>
      'No items available for this PPE at this unit';

  @override
  String get stockBlockedEmpty => 'No blocked items';

  @override
  String get stockNoOperationalUnit =>
      'Your profile has no active operational unit. Contact an administrator to get stock access.';

  @override
  String get stockItemLotLabel => 'Lot';

  @override
  String get stockStatusBlockedExpired => 'Expired';

  @override
  String get stockStatusBlockedDiscard => 'Awaiting disposal';

  @override
  String get stockStatusBlockedReturn => 'Awaiting return to supplier';

  @override
  String get stockStatusBlockedAnalysis => 'Under analysis';

  @override
  String get stockStatusBlockedRejected => 'Rejected';

  @override
  String get stockStatusBlockedArchived => 'Archived PPE';

  @override
  String get stockStatusUnknown => 'Unrecognized status';

  @override
  String get stockUnitBalanceSuffix => 'at this unit';

  @override
  String get stockCompanyBalanceLabel => 'company';

  @override
  String get stockMinimumShort => 'min';

  @override
  String get deliveryStepItem => 'Item';

  @override
  String get deliveryItemTitle => 'Select the labelled unit';

  @override
  String get deliveryItemEmpty => 'No item available in this Unit.';

  @override
  String get deliveryItemScan => 'Scan item QR';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Unit stock: $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Employee has no operational Unit: delivery cannot be recorded.';

  @override
  String get deliveryQrOtherEpi => 'The scanned code belongs to another PPE.';

  @override
  String get stockUnitRequiredToMove => 'Select a Unit to move stock.';

  @override
  String get stockAttentionSectionTitle => 'Stock';

  @override
  String get stockAttentionCompanyTitle => 'Attention range — company default';

  @override
  String get stockAttentionCompanyHelp =>
      'Applies to Units that have not set their own percentage. It does not change any Unit already configured.';

  @override
  String get stockAttentionPercentageLabel => 'Attention range percentage';

  @override
  String get stockAttentionOriginLabel => 'Source';

  @override
  String get stockAttentionOriginCompany => 'Set by the company';

  @override
  String get stockAttentionOriginSystem => 'System default';

  @override
  String get stockAttentionSave => 'Save company default';

  @override
  String get stockAttentionRestore => 'Restore system default';

  @override
  String get stockAttentionSaved => 'Company default saved.';

  @override
  String get stockAttentionRestored =>
      'Company default removed. The company is back on the system default.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'System default: $value%';
  }

  @override
  String get stockConfigTitle => 'Stock settings';

  @override
  String get stockConfigIntro =>
      'Set the minimum stock, attention range and alert monitoring of one PPE in one Unit. Each parameter is saved separately.';

  @override
  String get stockConfigUnitLabel => 'Unit to configure';

  @override
  String get stockConfigSelectUnit =>
      'Select the Unit to configure its parameters.';

  @override
  String get stockConfigSelectEpi =>
      'Select the PPE to view and edit this Unit’s parameters.';

  @override
  String get stockConfigEpiLabel => 'PPE';

  @override
  String get stockConfigEpisLoadError =>
      'Could not load the PPE list for this Unit.';

  @override
  String get stockConfigNoEpisInUnit => 'No PPE is visible in this Unit.';

  @override
  String get stockConfigUnitBalance => 'Unit balance';

  @override
  String get stockConfigAttentionLimit => 'Attention range limit';

  @override
  String get stockConfigUnderlyingStatus => 'Physical condition';

  @override
  String get stockConfigDerivedUnavailable =>
      'The calculated values could not be refreshed right now. The parameters saved above are correct.';

  @override
  String get stockConfigStatusCritical => 'Critical';

  @override
  String get stockConfigStatusNearMinimum => 'Near minimum';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alert disabled';

  @override
  String get stockConfigMinimumTitle => 'Minimum stock';

  @override
  String get stockConfigMinimumHelp =>
      'Quantity below which the PPE counts as critical in this Unit. Applies to this Unit only.';

  @override
  String get stockConfigMinimumLabel => 'Minimum stock';

  @override
  String get stockConfigMinimumNegativeError =>
      'Enter a whole number of zero or more.';

  @override
  String get stockConfigMinimumSaved => 'Minimum stock saved for this Unit.';

  @override
  String get stockConfigMinimumRestored =>
      'Minimum stock restored. The Unit inherits the company default again.';

  @override
  String get stockConfigAttentionTitle => 'Attention range';

  @override
  String get stockConfigAttentionHelp =>
      'Percentage above the minimum at which the PPE already enters attention in this Unit. Independent of the minimum stock.';

  @override
  String get stockConfigAttentionRangeError =>
      'The percentage must be between 0 and 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Attention range saved for this Unit.';

  @override
  String get stockConfigAttentionRestored =>
      'Attention range restored. The Unit inherits the company default again.';

  @override
  String get stockConfigAlertTitle => 'Alert monitoring';

  @override
  String get stockConfigAlertHelp =>
      'Turning this off stops low-stock alerts and automatic replenishment for this PPE in this Unit. It does not change balance, minimum or percentage.';

  @override
  String get stockConfigAlertToggle => 'Monitor this PPE’s stock';

  @override
  String get stockConfigAlertPending => 'Unsaved change. Click Save to apply.';

  @override
  String get stockConfigAlertDisableTitle => 'Disable the alert?';

  @override
  String get stockConfigAlertDisableBody =>
      'This PPE will stop generating low-stock alerts and automatic replenishment in this Unit. The physical condition will still be shown.';

  @override
  String get stockConfigAlertDisableConfirm => 'Disable';

  @override
  String get stockConfigAlertSaved => 'Alert monitoring saved for this Unit.';

  @override
  String get stockConfigAlertRestored =>
      'Monitoring restored. The Unit is back on the system default.';

  @override
  String get stockConfigOriginUnit => 'Set by this Unit';

  @override
  String get stockConfigOriginCompany => 'Inherited from the company default';

  @override
  String get stockConfigOriginUnknown => 'Not reported';

  @override
  String get stockConfigSave => 'Save';

  @override
  String get stockConfigRestore => 'Restore inheritance';

  @override
  String stockAttentionRangeError(int max) {
    return 'Enter a whole percentage between 0 and $max.';
  }

  @override
  String get stockAttentionLoadError => 'Could not load the company default.';

  @override
  String get unitSelectorLabel => 'Unit';

  @override
  String get unitSelectorAllUnits => 'All Units';

  @override
  String get unitSelectorLockedHint => 'Your profile operates in a fixed Unit.';

  @override
  String get unitSelectorLoadError => 'Could not load the Units.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'You have no Unit assigned. Contact your administrator.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'The company has no Units registered yet.';

  @override
  String get settingsSectionCompany => 'Company';

  @override
  String get settingsSectionOperation => 'Operations';

  @override
  String get settingsSectionSubscription => 'Subscription';

  @override
  String get settingsCompanyLabel => 'Company';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Managing company: $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Select a company in Settings to continue.';

  @override
  String get settingsFichaTileTitle => 'PPE record';

  @override
  String get settingsFichaTileSubtitle =>
      'Title, declaration, notes and traceability';

  @override
  String get settingsStockTileSubtitle => 'Company default attention threshold';

  @override
  String get settingsModulesTileSubtitle =>
      'Modules visible per role and per Unit';

  @override
  String get settingsArchivalTitle => 'Archiving and retention';

  @override
  String get settingsArchivalSubtitle => 'Years archived records are preserved';

  @override
  String get settingsAppearanceTitle => 'Appearance and language';

  @override
  String get settingsAppearanceSubtitle => 'Interface theme and app language';

  @override
  String get settingsSubscriptionTileTitle => 'My subscription';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Plan, charges and cancellation';

  @override
  String get settingsInvoicesTileTitle => 'Billing history';

  @override
  String get settingsInvoicesTileSubtitle => 'All charges and receipts';

  @override
  String get settingsNoPermission =>
      'You do not have permission to change this setting.';

  @override
  String get stockPhysicalValidityUnknown => 'Unknown physical expiry';

  @override
  String get stockNoPhysicalStock => 'No physical stock';

  @override
  String get stockRegularizeValidityTitle => 'Regularize physical validity';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identify the piece and enter the verified expiry date. Classification is done by the system.';

  @override
  String get stockRegularizeQrLabel => 'QR or piece code';

  @override
  String get stockRegularizeExpiryLabel => 'Verified physical expiry date';

  @override
  String get stockRegularizeExpirySelect => 'Select date';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Evidence (document or verifiable record)';

  @override
  String get stockRegularizeJustificationLabel => 'Justification';

  @override
  String get stockRegularizeSubmit => 'Regularize';

  @override
  String get stockRegularizeIncomplete =>
      'Fill in the piece, the expiry date, the evidence and the justification.';

  @override
  String get stockRegularizeResultEligible =>
      'Validity regularized. The piece is eligible for delivery and reservation.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validity regularized. The piece is expired and remains blocked for delivery.';

  @override
  String get stockRegularizeResultDone => 'Validity regularized.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — distinct PPE types: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Physical pieces: valid $valid, expiring $expiring, expired $expired, unknown $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Item unavailable for delivery. Check physical expiry, status, reservations and balance.';

  @override
  String get safetyTitle => 'Safety Library';

  @override
  String get safetyApproved => 'Approved PPE';

  @override
  String get safetyRetry => 'Try again';

  @override
  String get safetyClose => 'Close';

  @override
  String get safetyCancel => 'Cancel';

  @override
  String get safetyConfirm => 'Confirm';

  @override
  String get safetyAccess => 'Continue';

  @override
  String get safetyPortalConfirm => 'Confirm portal access';

  @override
  String get safetyCpfLast => 'Last three CPF digits';

  @override
  String get safetyView => 'View';

  @override
  String get safetyFit => 'Fit page';

  @override
  String get safetyZoomIn => 'Zoom in';

  @override
  String get safetyZoomOut => 'Zoom out';

  @override
  String get safetyNextPage => 'Next page';

  @override
  String get safetyPreviousPage => 'Previous page';

  @override
  String get safetyDocument => 'Document';

  @override
  String get safetyDetails => 'Details';

  @override
  String get safetyRelatedDocuments => 'Related documents';

  @override
  String get safetyRelatedEpis => 'Related PPE';

  @override
  String get safetyRelatedEpi => 'Related PPE';

  @override
  String get safetyAllEpis => 'All PPE';

  @override
  String get safetyAllCategories => 'All categories';

  @override
  String get safetyNoDocs => 'No documents published for this context.';

  @override
  String get safetyNoRecords =>
      'No published, authorized records in this context.';

  @override
  String get safetyCatalogueNotice =>
      'Catalogue approval does not indicate physical availability. CA expiry is separate from batch expiry.';

  @override
  String get safetyName => 'PPE';

  @override
  String get safetyManufacturer => 'Manufacturer';

  @override
  String get safetyModel => 'Model/reference';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'CA expiry';

  @override
  String get safetyUsefulLife => 'Service life (months)';

  @override
  String get safetyProtection => 'Protection';

  @override
  String get safetySection => 'Section';

  @override
  String get safetyRecommendations => 'Recommendations/restrictions';

  @override
  String get safetyUnknown => 'Not provided';

  @override
  String get safetySearch => 'Search';

  @override
  String get safetyViewEpi => 'View PPE';

  @override
  String get safetyHistory => 'History';

  @override
  String get safetyDocumentHistory => 'Document history';

  @override
  String get safetyPublish => 'Publish';

  @override
  String get safetyPublishVersion => 'Publish version';

  @override
  String get safetyArchive => 'Archive document';

  @override
  String get safetyArchiveVersions => 'Archive document and versions';

  @override
  String get safetyReason => 'Required justification';

  @override
  String get safetyNew => 'New document';

  @override
  String get safetyCreateNew => 'Create new document';

  @override
  String get safetyMetadata => 'Version details';

  @override
  String get safetyEmptyAdmin => 'No documents registered.';

  @override
  String get safetyPrivateNotice =>
      'Private originals, preserved versions and history. Management restricted to General and Registry Administrators.';

  @override
  String get safetyAllowAdminDownloads =>
      'Allow original downloads for authorized administrators';

  @override
  String get safetyPreviewOnlyNotice =>
      'Employees always have preview-only access.';

  @override
  String get safetyPolicyReason => 'Change administrator download policy';

  @override
  String get safetySearchVersions => 'Search title or version';

  @override
  String get safetyChooseFile => 'Choose file';

  @override
  String get safetyFilePickerLabel => 'Safety documents';

  @override
  String get safetyUnitRequired => 'Select at least one unit';

  @override
  String get safetyAllUnits => 'All company units';

  @override
  String get safetyRequired => 'Required';

  @override
  String get safetyDocumentTitle => 'Title';

  @override
  String get safetyVersion => 'Version';

  @override
  String get safetyEffectiveDate => 'Effective date (YYYY-MM-DD)';

  @override
  String get safetySectors => 'Comma-separated sectors (empty = all)';

  @override
  String get safetyActivities =>
      'Comma-separated activities/roles (empty = all)';

  @override
  String get safetyUpload => 'Register or version document';

  @override
  String get safetyRendering => 'Generating safe preview…';

  @override
  String get safetyFileLimit => 'Select a file up to 20 MiB.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Version $version · Effective $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Viewing unit: $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Preview unavailable: $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Upload rejected; preview unavailable: $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Version $version / revision $revision · $state · Effective $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsible user $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'PPE Application Matrix';

  @override
  String get safetyCategoryGlove => 'Glove Selection Matrix';

  @override
  String get safetyCategoryCare => 'Cleaning and Care Guides';

  @override
  String get safetyCategoryUse => 'PPE Use Instructions';

  @override
  String get safetyCategoryTechnical => 'Manuals and Technical Sheets';

  @override
  String get safetyCategoryOther => 'Other Safety Documents';

  @override
  String get safetyStateDraft => 'Draft';

  @override
  String get safetyStatePublished => 'Published';

  @override
  String get safetyStateSuperseded => 'Superseded';

  @override
  String get safetyStateArchived => 'Archived';

  @override
  String get prConfTitle => 'Receipt Conference';

  @override
  String get prConfIntro =>
      'Tick each item as actually received. Enter the manufacturer physical validity and verifiable evidence; use \"Split into lots\" for different validities or individual exceptions. Pieces without proven validity enter BLOCKED.';

  @override
  String get prConfReceivedYes => 'Received';

  @override
  String get prConfReceivedNo => 'Not received';

  @override
  String get prConfEvidence => 'Verifiable evidence';

  @override
  String get prConfEvidenceHint => 'Label / invoice / photo';

  @override
  String get prConfEvidenceRequired =>
      'Verifiable evidence is required when a validity is set.';

  @override
  String get prConfSplitLots => 'Split into lots';

  @override
  String get prConfSingleDate => 'Use single date';

  @override
  String get prConfAddLot => 'Add lot';

  @override
  String get prConfAddException => 'Exception (1 piece)';

  @override
  String get prConfLotQty => 'Qty';

  @override
  String get prConfLotCode => 'Identification';

  @override
  String get prConfRemoveLot => 'Remove lot';

  @override
  String get prConfPreview => 'Preview — physical validity per piece';

  @override
  String get prConfBlocked => 'NO validity → BLOCKED';

  @override
  String get prConfExpired => 'expired';

  @override
  String get prConfPiece => 'piece(s)';

  @override
  String get prConfSumMismatch =>
      'The sum of lot quantities does not match the received quantity.';

  @override
  String get prConfLotQtyPositive =>
      'Each lot needs a quantity greater than zero.';

  @override
  String get prConfNotes => 'Notes about items not received';

  @override
  String get prConfNotesRequired => 'Enter the notes about items not received.';

  @override
  String get prConfSubmit => 'Register Conference';

  @override
  String get prConfDone => 'Conference registered.';

  @override
  String get prConfEmpty => 'No item eligible for conference.';

  @override
  String get prConfInvalidQuantity =>
      'Effective received quantity is invalid or non-positive. Correct the receipt before confirming.';

  @override
  String get prConfNoPersistedPieces =>
      'No pieces were actually recorded, or the response is inconsistent. Stock entry was not confirmed.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count pieces actually recorded in stock.';
  }

  @override
  String get prConfNoStockEntry =>
      'Conference saved without adding pieces to stock.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Line $line — $item (item #$id): effective received quantity is invalid or non-positive. Correct the receipt before confirming.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Stock approaching minimum: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Negative stock balance: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Out of stock: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Stock below minimum: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Stock at minimum: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - current balance: $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'Brazilian CA approaching expiry: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - expires on $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Manufacturer expiry date passed: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Manufacturer expiry date approaching: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - manufacturer expiry date: $date. Remove from stock ($stock $measure): expired PPE must not be issued to workers.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - manufacturer expiry date: $date (in $daysLabel). Prioritise issuing this batch ($stock $measure in stock) before expiry (FIFO).';
  }

  @override
  String get operationalAlertSizes => 'Sizes in stock:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Glove:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Size:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Uniform:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Unspecified size';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'units',
      one: 'unit',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'pairs',
      one: 'pair',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel days',
      one: '$countLabel day',
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
      other: '$epi: $countLabel physical items.',
      one: '$epi: $countLabel physical item.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Unknown physical expiry date';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Batches approaching expiry';
}
