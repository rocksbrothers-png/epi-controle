// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Norwegian (`no`).
class AppLocalizationsNo extends AppLocalizations {
  AppLocalizationsNo([String locale = 'no']) : super(locale);

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
  String get employeeCpfLabel => 'Brasiliansk CPF';

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
  String get episSearchHint => 'Søk etter navn, brasiliansk CA eller kode';

  @override
  String get epiNameLabel => 'PVU-navn';

  @override
  String get epiCodeLabel => 'Innkjøpskode';

  @override
  String get epiCaLabel => 'CA — brasiliansk godkjenningssertifikat';

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
  String get epiCaExpiryLabel => 'Utløp for brasiliansk CA';

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
  String get epiStatusNoStock => 'Ikke på lager';

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
  String get returnOfflineQueued =>
      'Retur lagret — synkroniseres ved tilkobling.';

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
  String get poManufacturerValidityRequired =>
      'Angi produsentgyldighet for alt mottatt verneutstyr.';

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
  String get epiArchiveBlockBody =>
      'Dette verneutstyret har tilgjengelig lager eller aktive koblinger. Ved bekreftelse flyttes tilgjengelig lager til Sperret lager (sporbart) og utstyret arkiveres.';

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
  String get handoverAlreadyConfirmed =>
      'Denne leveringen er allerede bekreftet.';

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
  String get legalEntityDeactivateHint =>
      'Juridisk historikk bevares. CNPJ brukes ikke i nye operasjoner.';

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
  String get legalEntitiesImportColumnsHint =>
      'Org.nr.\tJuridisk navn\tHandelsnavn\tType';

  @override
  String get legalEntitiesImport => 'Importer regneark';

  @override
  String get legalEntitiesImportHint =>
      'Kopier radene fra regnearket (med overskriftsraden) og lim inn nedenfor. Godtar kolonner på portugisisk eller engelsk.';

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
  String get legalEntityTransferHint =>
      'CNPJ er tilknytningen til arbeidsavtalen og endres ikke ved enhetsoverføring. Endringen revideres og krever en begrunnelse.';

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
  String get unitTransferHint =>
      'Bevegelse av driftsenhet — midlertidig eller permanent. Oppretter en sporbar hendelse og endrer ikke medarbeiderens CNPJ.';

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
  String get myCompanyStockScopeHint =>
      'Denne innstillingen endrer bare den konsoliderte visningen av saldoer. Innganger, reservasjoner, uttak, utleveringer og andre bevegelser forblir knyttet til lageret i hver enhet.';

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
  String get unitLegalEntityHint =>
      'Juridisk enhet som er ansvarlig for driften og lageret til denne enheten.';

  @override
  String get employeeEmploymentTypeLabel => 'Ansettelsestype';

  @override
  String get employeeSourceCompanyLabel => 'Opprinnelsesselskap';

  @override
  String get employeeSourceCompanyHint =>
      'Navn på den ansattes opprinnelsesselskap';

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
  String get outsourcedCompanyResponsibilityLabel =>
      'Ansvar for Levering av Verneutstyr';

  @override
  String get outsourcedCompanyUnitLabel => 'Enhet';

  @override
  String get outsourcedCompanyUnitAll => 'Alle enheter (standard)';

  @override
  String get outsourcedCompanyLinkTitle => 'Knytt selskap til denne enheten';

  @override
  String get outsourcedCompanyLinkHint =>
      'Søk etter selskap som allerede er registrert i tenanten…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Allerede knyttet til denne enheten';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Tilgjengelige for tilknytning';

  @override
  String get outsourcedCompanyLinkLink => 'Knytt til denne enheten';

  @override
  String get outsourcedCompanyLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Årsak til arkivering (valgfritt):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Brukt av $count enhet(er)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Opprinnelsesenhet';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Fant ingen selskaper for dette søket.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Tilknytning ikke oppgitt for profilen din';

  @override
  String get outsourcedCompanyStatusLabel => 'Status';

  @override
  String get outsourcedCompanySave => 'Lagre';

  @override
  String get outsourcedCompanyCancel => 'Avbryt';

  @override
  String get outsourcedCompanyPromote => 'Oppgrader til Standard Registrering';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Oppgradere til Standard Registrering?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'Selskapet vil bli behandlet som Standard Registrering. Et CNPJ kreves.';

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
  String get outsourcedCompanyArchiveConfirmTitle =>
      'Arkivere dette selskapet?';

  @override
  String get outsourcedCompanyRestore => 'Gjenopprett';

  @override
  String get outsourcedCompanyRestoreConfirmTitle =>
      'Gjenopprette dette selskapet?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'Ingen arkiverte innleide selskaper.';

  @override
  String get outsourcedEmployeeNew => 'Ny medarbeider';

  @override
  String get outsourcedEmployeesEmpty =>
      'Ingen innleide/tjenesteytende medarbeidere registrert.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'Ingen arkiverte innleide/tjenesteytende medarbeidere.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Innleid/tjenesteytende selskap';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Registreringsnummer hos opprinnelig arbeidsgiver';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Adgangskort';

  @override
  String get outsourcedEmployeeNotesLabel => 'Merknader';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      'Arkivere denne medarbeideren?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      'Gjenopprette denne medarbeideren?';

  @override
  String get employeeUnitLinkColumn => 'Lokal tilknytning';

  @override
  String get employeeUnitLink => 'Knytt til min enhet';

  @override
  String get employeeUnitLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Årsak til arkivering (valgfritt):';

  @override
  String get employeeUnitLinkActive => 'Tilknyttet';

  @override
  String get employeeUnitLinkArchived => 'Arkivert i denne enheten';

  @override
  String get employeeUnitLinkAbsent => 'Ikke tilknyttet';

  @override
  String get employeeUnitLinksTitle => 'Tilknytninger per enhet';

  @override
  String get employeeUnitLinksEmpty =>
      'Denne medarbeideren har ingen tilknytning til noen enhet du kan se.';

  @override
  String get employeeUnitLinksError => 'Kunne ikke laste tilknytningene.';

  @override
  String get outsourcedReportsError => 'Kunne ikke laste rapporten.';

  @override
  String get outsourcedReportsEmpty =>
      'Ingen innleide/tjenesteytende selskaper registrert.';

  @override
  String get outsourcedReportsActive => 'Aktive';

  @override
  String get outsourcedReportsArchived => 'Arkiverte';

  @override
  String get moduleVisibilityTitle => 'Modulsynlighet';

  @override
  String get moduleVisibilityDescription =>
      'Standardtillatelser: hver rolle har standardtillatelser definert av systemet. Tilpasninger: Hovedadministratoren kan tilpasse synlighet og bruk av moduler per rolle og per enhet, uten å endre systemets standardstruktur.';

  @override
  String get moduleVisibilityRoleLabel => 'Rolle';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Standardtillatelser for denne rollen';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Disse tillatelsene representerer systemets standardoppførsel. Innstillingene nedenfor tillater kun tilpasninger utført av Hovedadministratoren.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ingen moduler som standard';

  @override
  String get moduleVisibilityUnitLabel => 'Enhet';

  @override
  String get moduleVisibilityUnitHint =>
      'En modul som ikke er spesifikt satt for denne Enheten, arver verdien fra \"Alle enheter\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Alle enheter (standard)';

  @override
  String get stockTabAvailable => 'Tilgjengelige';

  @override
  String get stockTabBlocked => 'Blokkerte';

  @override
  String get stockAvailableSelectEpi =>
      'Velg et PVU for å se tilgjengelige varer';

  @override
  String get stockAvailableEmpty =>
      'Ingen tilgjengelige varer for dette PVU-et ved denne enheten';

  @override
  String get stockBlockedEmpty => 'Ingen blokkerte varer';

  @override
  String get stockNoOperationalUnit =>
      'Profilen din har ingen aktiv driftsenhet. Kontakt en administrator for å få tilgang til lageret.';

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
  String get deliveryEmployeeWithoutUnit =>
      'Ansatt uten operativ Enhet: levering kan ikke registreres.';

  @override
  String get deliveryQrOtherEpi =>
      'Den skannede koden tilhører et annet verneutstyr.';

  @override
  String get stockUnitRequiredToMove => 'Velg en Enhet for å flytte lager.';

  @override
  String get stockAttentionSectionTitle => 'Lager';

  @override
  String get stockAttentionCompanyTitle =>
      'Varselintervall — selskapets standard';

  @override
  String get stockAttentionCompanyHelp =>
      'Gjelder enheter som ikke har angitt sin egen prosent. Endrer ingen enhet som allerede er konfigurert.';

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
  String get stockAttentionRestored =>
      'Selskapets standard er fjernet. Selskapet er tilbake på systemstandarden.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Systemstandard: $value %';
  }

  @override
  String get stockConfigTitle => 'Lagerkonfigurasjon';

  @override
  String get stockConfigIntro =>
      'Angi minimumslager, varselintervall og varselovervåking for ett verneutstyr i én enhet. Hver parameter lagres for seg.';

  @override
  String get stockConfigUnitLabel => 'Enhet som skal konfigureres';

  @override
  String get stockConfigSelectUnit =>
      'Velg enheten for å konfigurere parameterne.';

  @override
  String get stockConfigSelectEpi =>
      'Velg verneutstyret for å se og endre parameterne for denne enheten.';

  @override
  String get stockConfigEpiLabel => 'Verneutstyr';

  @override
  String get stockConfigEpisLoadError =>
      'Kunne ikke laste listen over verneutstyr for denne enheten.';

  @override
  String get stockConfigNoEpisInUnit =>
      'Ingen verneutstyr er synlig i denne enheten.';

  @override
  String get stockConfigUnitBalance => 'Saldo i enheten';

  @override
  String get stockConfigAttentionLimit => 'Grense for varselintervall';

  @override
  String get stockConfigUnderlyingStatus => 'Fysisk tilstand';

  @override
  String get stockConfigDerivedUnavailable =>
      'De beregnede verdiene kunne ikke oppdateres nå. Parameterne som er lagret over, er riktige.';

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
  String get stockConfigMinimumHelp =>
      'Antall under hvilket verneutstyret regnes som kritisk i denne enheten. Gjelder bare denne enheten.';

  @override
  String get stockConfigMinimumLabel => 'Minimumslager';

  @override
  String get stockConfigMinimumNegativeError =>
      'Skriv inn et heltall lik eller større enn null.';

  @override
  String get stockConfigMinimumSaved =>
      'Minimumslager lagret for denne enheten.';

  @override
  String get stockConfigMinimumRestored =>
      'Minimumslager tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAttentionTitle => 'Varselintervall';

  @override
  String get stockConfigAttentionHelp =>
      'Prosent over minimum der verneutstyret allerede går i varsel i denne enheten. Uavhengig av minimumslageret.';

  @override
  String get stockConfigAttentionRangeError =>
      'Prosenten må være mellom 0 og 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Varselintervall lagret for denne enheten.';

  @override
  String get stockConfigAttentionRestored =>
      'Varselintervall tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAlertTitle => 'Varselovervåking';

  @override
  String get stockConfigAlertHelp =>
      'Å slå den av stopper varsel om lavt lager og automatisk etterfylling for dette verneutstyret i denne enheten. Det endrer verken saldo, minimum eller prosent.';

  @override
  String get stockConfigAlertToggle =>
      'Overvåk lageret for dette verneutstyret';

  @override
  String get stockConfigAlertPending =>
      'Ulagret endring. Klikk Lagre for å bruke den.';

  @override
  String get stockConfigAlertDisableTitle => 'Deaktivere varselet?';

  @override
  String get stockConfigAlertDisableBody =>
      'Dette verneutstyret slutter å gi varsel om lavt lager og automatisk etterfylling i denne enheten. Den fysiske tilstanden vises fortsatt.';

  @override
  String get stockConfigAlertDisableConfirm => 'Deaktiver';

  @override
  String get stockConfigAlertSaved =>
      'Varselovervåking lagret for denne enheten.';

  @override
  String get stockConfigAlertRestored =>
      'Overvåking tilbakestilt. Enheten er tilbake på systemstandarden.';

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
  String get unitSelectorNoUnitsAssigned =>
      'Du har ingen enhet tildelt. Kontakt administratoren.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'Selskapet har ennå ingen enheter registrert.';

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
  String get settingsSelectCompanyFirst =>
      'Velg et selskap i Innstillinger for å fortsette.';

  @override
  String get settingsFichaTileTitle => 'PVU-skjema';

  @override
  String get settingsFichaTileSubtitle =>
      'Tittel, erklæring, merknader og sporbarhet';

  @override
  String get settingsStockTileSubtitle => 'Selskapets standard varselgrense';

  @override
  String get settingsModulesTileSubtitle =>
      'Moduler synlige per profil og per enhet';

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
  String get settingsSubscriptionTileSubtitle =>
      'Abonnement, betalinger og oppsigelse';

  @override
  String get settingsInvoicesTileTitle => 'Betalingshistorikk';

  @override
  String get settingsInvoicesTileSubtitle => 'Alle betalinger og kvitteringer';

  @override
  String get settingsNoPermission =>
      'Du har ikke tillatelse til å endre denne innstillingen.';

  @override
  String get stockPhysicalValidityUnknown => 'Ukjent fysisk utløpsdato';

  @override
  String get stockNoPhysicalStock => 'Ingen fysisk beholdning';

  @override
  String get stockRegularizeValidityTitle => 'Regulariser fysisk gyldighet';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifiser delen og oppgi dokumentert gyldighet. Klassifiseringen gjøres av systemet.';

  @override
  String get stockRegularizeQrLabel => 'QR eller delkode';

  @override
  String get stockRegularizeExpiryLabel => 'Dokumentert fysisk gyldighet';

  @override
  String get stockRegularizeExpirySelect => 'Velg dato';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Dokumentasjon (dokument eller verifiserbar oppføring)';

  @override
  String get stockRegularizeJustificationLabel => 'Begrunnelse';

  @override
  String get stockRegularizeSubmit => 'Regulariser';

  @override
  String get stockRegularizeIncomplete =>
      'Fyll ut delen, gyldigheten, dokumentasjonen og begrunnelsen.';

  @override
  String get stockRegularizeResultEligible =>
      'Gyldighet regularisert. Delen er kvalifisert for utlevering og reservasjon.';

  @override
  String get stockRegularizeResultBlocked =>
      'Gyldighet regularisert. Delen er utløpt og forblir blokkert for utlevering.';

  @override
  String get stockRegularizeResultDone => 'Gyldighet regularisert.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — ulike verneutstyrstyper: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Fysiske enheter: gyldige $valid, utløper snart $expiring, utløpt $expired, ukjent $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Enheten kan ikke utleveres. Kontroller fysisk utløpsdato, status, reservasjoner og beholdning.';

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
  String get safetyNoDocs =>
      'Ingen publiserte dokumenter for denne konteksten.';

  @override
  String get safetyNoRecords =>
      'Ingen publiserte, autoriserte oppføringer i denne konteksten.';

  @override
  String get safetyCatalogueNotice =>
      'Kataloggodkjenning angir ikke fysisk tilgjengelighet. CA-utløp er separat fra partiutløp.';

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
  String get safetyPrivateNotice =>
      'Private originaler, bevarte versjoner og historikk. Administrasjon begrenset til generell administrator og registeradministrator.';

  @override
  String get safetyAllowAdminDownloads =>
      'Tillat originalnedlasting for autoriserte administratorer';

  @override
  String get safetyPreviewOnlyNotice =>
      'Ansatte har alltid kun forhåndsvisning.';

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
  String get safetyActivities =>
      'Kommaseparerte aktiviteter/stillinger (tomt = alle)';

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
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
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

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linje $line — $item (vare #$id): faktisk mottatt mengde er ugyldig eller ikke positiv. Korriger mottaket før bekreftelse.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Lagerbeholdning nær minimum: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Negativ lagerbeholdning: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Tomt på lager: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Lagerbeholdning under minimum: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Lagerbeholdning på minimum: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - gjeldende beholdning: $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'Brasiliansk CA nær utløpsdato: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - utløper $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Produsentens utløpsdato er passert: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Produsentens utløpsdato nærmer seg: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - produsentens utløpsdato var $date. Ta ut av lageret ($stock $measure): utløpt PVU kan ikke utleveres til ansatte.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - produsentens utløpsdato er $date (om $daysLabel). Prioriter utlevering fra dette partiet ($stock $measure på lager) før utløp (FIFO).';
  }

  @override
  String get operationalAlertSizes => 'Størrelser på lager:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Hanske:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Størrelse:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Arbeidstøy:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Uspesifisert størrelse';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'enheter',
      one: 'enhet',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'par',
      one: 'par',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel dager',
      one: '$countLabel dag',
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
      other: '$epi: $countLabel fysiske enheter.',
      one: '$epi: $countLabel fysisk enhet.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle => 'Ukjent fysisk utløpsdato';

  @override
  String get operationalAlertPhysicalExpiringTitle => 'Partier nær utløpsdato';

  @override
  String get passwordChangeTitle => 'Angi et nytt passord';

  @override
  String get passwordChangeIntro =>
      'Passordet ditt er midlertidig. Angi et nytt passord for å fortsette av sikkerhetshensyn.';

  @override
  String get passwordChangeCurrent => 'Gjeldende passord (midlertidig)';

  @override
  String get passwordChangeNew => 'Nytt passord';

  @override
  String get passwordChangeConfirm => 'Bekreft nytt passord';

  @override
  String get passwordChangeSave => 'Lagre nytt passord';

  @override
  String get passwordChangeLogout => 'Logg ut';

  @override
  String get passwordChangeCurrentRequired => 'Skriv inn gjeldende passord';

  @override
  String get passwordChangeMinLength =>
      'Det nye passordet må inneholde minst 6 tegn';

  @override
  String get passwordChangeMustDiffer =>
      'Det nye passordet må være forskjellig fra det midlertidige';

  @override
  String get passwordChangeMismatch => 'Passordene samsvarer ikke';

  @override
  String get passwordChangeFailed => 'Kunne ikke endre passordet';

  @override
  String get poSupplierConfirmed => 'Bekreftet';

  @override
  String get poSupplierDeliveryUpdated => 'Levering oppdatert';

  @override
  String get poSupplierRejected => 'Avslått';

  @override
  String get poSupplierIsoDateHint => 'YYYY-MM-DD';

  @override
  String get billingActive => 'Aktivt';

  @override
  String get billingPending => 'Venter';

  @override
  String get billingPaused => 'Satt på pause';

  @override
  String get billingCancelled => 'Avsluttet';

  @override
  String get billingExpired => 'Utløpt';

  @override
  String get billingAnnual => 'Årlig';

  @override
  String get billingMonthly => 'Månedlig';

  @override
  String get billingRecurringCard => 'Kort (gjentakende)';

  @override
  String get billingCard => 'Kort';

  @override
  String get billingBoleto => 'Boleto (brasiliansk betalingsblankett)';

  @override
  String get billingConfirmTitle => 'Er du sikker?';

  @override
  String get billingConfirmBody =>
      'Tilgangen din beholdes til slutten av perioden som allerede er betalt.\nDet foretas ingen nye belastninger.';

  @override
  String get billingConfirmCancel => 'Bekreft avslutning';

  @override
  String get billingCancelledNotice => 'Abonnementet er avsluttet.';

  @override
  String billingCancelFailed(String detail) {
    return 'Kunne ikke avslutte: $detail';
  }

  @override
  String get billingAmount => 'Beløp';

  @override
  String get billingCycle => 'Betalingsperiode';

  @override
  String get billingMethod => 'Betalingsmåte';

  @override
  String get billingStarted => 'Startdato for abonnementet';

  @override
  String get billingNextPayment => 'Neste betaling';

  @override
  String get billingLastPayment => 'Siste betaling';

  @override
  String get billingCancelDate => 'Avsluttet den';

  @override
  String get billingManualRenewal => 'Manuell fornyelse';

  @override
  String get billingMpSubscriptionId => 'Abonnements-ID (MP)';

  @override
  String get billingMpStatus => 'Mercado Pago-status';

  @override
  String get billingTenant => 'Tenant';

  @override
  String get billingCancelAction => 'Avslutt abonnement';

  @override
  String get billingCancelledBody =>
      'Abonnementet er avsluttet. Tilgangen beholdes til slutten av perioden som allerede er betalt. Det foretas ingen nye belastninger.';

  @override
  String get billingEmptyTitle => 'Ingen aktive abonnementer';

  @override
  String get billingEmptyBody =>
      'Abonnementsdetaljene vises her når et abonnement er bestilt.';

  @override
  String get billingLoadFailed => 'Kunne ikke laste abonnementet.';

  @override
  String get billingInvoicePaid => 'Betalt';

  @override
  String get billingInvoicePending => 'Venter';

  @override
  String get billingInvoiceCancelled => 'Kansellert';

  @override
  String get billingInvoiceRefunded => 'Refundert';

  @override
  String get billingInvoiceFailed => 'Mislyktes';

  @override
  String get billingOpenReceipt => 'Åpne kvittering';

  @override
  String get billingReceiptOpenFailed => 'Kunne ikke åpne kvitteringen.';

  @override
  String get billingHistoryLoadFailed =>
      'Kunne ikke laste betalingshistorikken.';

  @override
  String get billingInvoicesEmptyTitle => 'Fant ingen betalinger';

  @override
  String get billingInvoicesEmptyBody =>
      'Betalingene for abonnementet ditt vises her.';

  @override
  String get feedbackTitle => 'Vurderinger av verneutstyr';

  @override
  String get feedbackLoadFailed => 'Kunne ikke laste vurderingene';

  @override
  String get feedbackEmpty => 'Ingen vurderinger funnet';

  @override
  String get feedbackValidate => 'Valider';

  @override
  String get feedbackStatusOpen => 'Åpen';

  @override
  String get feedbackStatusResolved => 'Løst';

  @override
  String get feedbackStatusClosed => 'Lukket';

  @override
  String get feedbackStatusReceived => 'Mottatt';

  @override
  String get feedbackStatusManagerReview =>
      'Under vurdering hos ansvarlig for verneutstyr';

  @override
  String get feedbackStatusAwaitingHseq => 'Venter på HSEQ-vurdering';

  @override
  String get feedbackStatusHseqCompleted => 'HSEQ-vurdering fullført';

  @override
  String get feedbackStatusForwardedAdmin => 'Videresendt til administrasjonen';

  @override
  String get feedbackStatusAwaitingAdmin =>
      'Venter på administrativ godkjenning';

  @override
  String get feedbackStatusCorrectiveAction => 'Åpent korrigerende tiltak';

  @override
  String get feedbackStatusMoreInformation => 'Mer informasjon etterspurt';

  @override
  String get feedbackStatusEnded => 'Avsluttet';

  @override
  String get feedbackStatusNotApproved => 'Ikke godkjent';
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
  String get employeeCpfLabel => 'Brasiliansk CPF';

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
  String get episSearchHint => 'Søk etter navn, brasiliansk CA eller kode';

  @override
  String get epiNameLabel => 'PVU-navn';

  @override
  String get epiCodeLabel => 'Innkjøpskode';

  @override
  String get epiCaLabel => 'CA — brasiliansk godkjenningssertifikat';

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
  String get epiCaExpiryLabel => 'Utløp for brasiliansk CA';

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
  String get epiStatusNoStock => 'Ikke på lager';

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
  String get returnOfflineQueued =>
      'Retur lagret — synkroniseres ved tilkobling.';

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
  String get poManufacturerValidityRequired =>
      'Angi produsentgyldighet for alt mottatt verneutstyr.';

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
  String get epiArchiveBlockBody =>
      'Dette verneutstyret har tilgjengelig lager eller aktive koblinger. Ved bekreftelse flyttes tilgjengelig lager til Sperret lager (sporbart) og utstyret arkiveres.';

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
  String get handoverAlreadyConfirmed =>
      'Denne leveringen er allerede bekreftet.';

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
  String get legalEntityDeactivateHint =>
      'Juridisk historikk bevares. CNPJ brukes ikke i nye operasjoner.';

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
  String get legalEntitiesImportColumnsHint =>
      'Org.nr.\tJuridisk navn\tHandelsnavn\tType';

  @override
  String get legalEntitiesImport => 'Importer regneark';

  @override
  String get legalEntitiesImportHint =>
      'Kopier radene fra regnearket (med overskriftsraden) og lim inn nedenfor. Godtar kolonner på portugisisk eller engelsk.';

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
  String get legalEntityTransferHint =>
      'CNPJ er tilknytningen til arbeidsavtalen og endres ikke ved enhetsoverføring. Endringen revideres og krever en begrunnelse.';

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
  String get unitTransferHint =>
      'Bevegelse av driftsenhet — midlertidig eller permanent. Oppretter en sporbar hendelse og endrer ikke medarbeiderens CNPJ.';

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
  String get myCompanyStockScopeHint =>
      'Denne innstillingen endrer bare den konsoliderte visningen av saldoer. Innganger, reservasjoner, uttak, utleveringer og andre bevegelser forblir knyttet til lageret i hver enhet.';

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
  String get unitLegalEntityHint =>
      'Juridisk enhet som er ansvarlig for driften og lageret til denne enheten.';

  @override
  String get employeeEmploymentTypeLabel => 'Ansettelsestype';

  @override
  String get employeeSourceCompanyLabel => 'Opprinnelsesselskap';

  @override
  String get employeeSourceCompanyHint =>
      'Navn på den ansattes opprinnelsesselskap';

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
  String get outsourcedCompanyResponsibilityLabel =>
      'Ansvar for Levering av Verneutstyr';

  @override
  String get outsourcedCompanyUnitLabel => 'Enhet';

  @override
  String get outsourcedCompanyUnitAll => 'Alle enheter (standard)';

  @override
  String get outsourcedCompanyLinkTitle => 'Knytt selskap til denne enheten';

  @override
  String get outsourcedCompanyLinkHint =>
      'Søk etter selskap som allerede er registrert i tenanten…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Allerede knyttet til denne enheten';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Tilgjengelige for tilknytning';

  @override
  String get outsourcedCompanyLinkLink => 'Knytt til denne enheten';

  @override
  String get outsourcedCompanyLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Årsak til arkivering (valgfritt):';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Brukt av $count enhet(er)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Opprinnelsesenhet';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Fant ingen selskaper for dette søket.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Tilknytning ikke oppgitt for profilen din';

  @override
  String get outsourcedCompanyStatusLabel => 'Status';

  @override
  String get outsourcedCompanySave => 'Lagre';

  @override
  String get outsourcedCompanyCancel => 'Avbryt';

  @override
  String get outsourcedCompanyPromote => 'Oppgrader til Standard Registrering';

  @override
  String get outsourcedCompanyPromoteConfirmTitle =>
      'Oppgradere til Standard Registrering?';

  @override
  String get outsourcedCompanyPromoteConfirmBody =>
      'Selskapet vil bli behandlet som Standard Registrering. Et CNPJ kreves.';

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
  String get outsourcedCompanyArchiveConfirmTitle =>
      'Arkivere dette selskapet?';

  @override
  String get outsourcedCompanyRestore => 'Gjenopprett';

  @override
  String get outsourcedCompanyRestoreConfirmTitle =>
      'Gjenopprette dette selskapet?';

  @override
  String get outsourcedCompaniesArchivedEmpty =>
      'Ingen arkiverte innleide selskaper.';

  @override
  String get outsourcedEmployeeNew => 'Ny medarbeider';

  @override
  String get outsourcedEmployeesEmpty =>
      'Ingen innleide/tjenesteytende medarbeidere registrert.';

  @override
  String get outsourcedEmployeesArchivedEmpty =>
      'Ingen arkiverte innleide/tjenesteytende medarbeidere.';

  @override
  String get outsourcedEmployeeCompanyLabel => 'Innleid/tjenesteytende selskap';

  @override
  String get outsourcedEmployeeOriginRegistrationLabel =>
      'Registreringsnummer hos opprinnelig arbeidsgiver';

  @override
  String get outsourcedEmployeeBadgeLabel => 'Adgangskort';

  @override
  String get outsourcedEmployeeNotesLabel => 'Merknader';

  @override
  String get outsourcedEmployeeArchiveConfirmTitle =>
      'Arkivere denne medarbeideren?';

  @override
  String get outsourcedEmployeeRestoreConfirmTitle =>
      'Gjenopprette denne medarbeideren?';

  @override
  String get employeeUnitLinkColumn => 'Lokal tilknytning';

  @override
  String get employeeUnitLink => 'Knytt til min enhet';

  @override
  String get employeeUnitLinkActivate => 'Reaktiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivate => 'Arkiver i denne enheten';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Årsak til arkivering (valgfritt):';

  @override
  String get employeeUnitLinkActive => 'Tilknyttet';

  @override
  String get employeeUnitLinkArchived => 'Arkivert i denne enheten';

  @override
  String get employeeUnitLinkAbsent => 'Ikke tilknyttet';

  @override
  String get employeeUnitLinksTitle => 'Tilknytninger per enhet';

  @override
  String get employeeUnitLinksEmpty =>
      'Denne medarbeideren har ingen tilknytning til noen enhet du kan se.';

  @override
  String get employeeUnitLinksError => 'Kunne ikke laste tilknytningene.';

  @override
  String get outsourcedReportsError => 'Kunne ikke laste rapporten.';

  @override
  String get outsourcedReportsEmpty =>
      'Ingen innleide/tjenesteytende selskaper registrert.';

  @override
  String get outsourcedReportsActive => 'Aktive';

  @override
  String get outsourcedReportsArchived => 'Arkiverte';

  @override
  String get moduleVisibilityTitle => 'Modulsynlighet';

  @override
  String get moduleVisibilityDescription =>
      'Standardtillatelser: hver rolle har standardtillatelser definert av systemet. Tilpasninger: Hovedadministratoren kan tilpasse synlighet og bruk av moduler per rolle og per enhet, uten å endre systemets standardstruktur.';

  @override
  String get moduleVisibilityRoleLabel => 'Rolle';

  @override
  String get moduleVisibilityDefaultPanelTitle =>
      'Standardtillatelser for denne rollen';

  @override
  String get moduleVisibilityDefaultPanelHint =>
      'Disse tillatelsene representerer systemets standardoppførsel. Innstillingene nedenfor tillater kun tilpasninger utført av Hovedadministratoren.';

  @override
  String get moduleVisibilityNoDefaultModules => 'Ingen moduler som standard';

  @override
  String get moduleVisibilityUnitLabel => 'Enhet';

  @override
  String get moduleVisibilityUnitHint =>
      'En modul som ikke er spesifikt satt for denne Enheten, arver verdien fra \"Alle enheter\".';

  @override
  String get moduleVisibilityAllUnitsOption => 'Alle enheter (standard)';

  @override
  String get stockTabAvailable => 'Tilgjengelige';

  @override
  String get stockTabBlocked => 'Blokkerte';

  @override
  String get stockAvailableSelectEpi =>
      'Velg et PVU for å se tilgjengelige varer';

  @override
  String get stockAvailableEmpty =>
      'Ingen tilgjengelige varer for dette PVU-et ved denne enheten';

  @override
  String get stockBlockedEmpty => 'Ingen blokkerte varer';

  @override
  String get stockNoOperationalUnit =>
      'Profilen din har ingen aktiv driftsenhet. Kontakt en administrator for å få tilgang til lageret.';

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
  String get deliveryEmployeeWithoutUnit =>
      'Ansatt uten operativ Enhet: levering kan ikke registreres.';

  @override
  String get deliveryQrOtherEpi =>
      'Den skannede koden tilhører et annet verneutstyr.';

  @override
  String get stockUnitRequiredToMove => 'Velg en Enhet for å flytte lager.';

  @override
  String get stockAttentionSectionTitle => 'Lager';

  @override
  String get stockAttentionCompanyTitle =>
      'Varselintervall — selskapets standard';

  @override
  String get stockAttentionCompanyHelp =>
      'Gjelder enheter som ikke har angitt sin egen prosent. Endrer ingen enhet som allerede er konfigurert.';

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
  String get stockAttentionRestored =>
      'Selskapets standard er fjernet. Selskapet er tilbake på systemstandarden.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Systemstandard: $value %';
  }

  @override
  String get stockConfigTitle => 'Lagerkonfigurasjon';

  @override
  String get stockConfigIntro =>
      'Angi minimumslager, varselintervall og varselovervåking for ett verneutstyr i én enhet. Hver parameter lagres for seg.';

  @override
  String get stockConfigUnitLabel => 'Enhet som skal konfigureres';

  @override
  String get stockConfigSelectUnit =>
      'Velg enheten for å konfigurere parameterne.';

  @override
  String get stockConfigSelectEpi =>
      'Velg verneutstyret for å se og endre parameterne for denne enheten.';

  @override
  String get stockConfigEpiLabel => 'Verneutstyr';

  @override
  String get stockConfigEpisLoadError =>
      'Kunne ikke laste listen over verneutstyr for denne enheten.';

  @override
  String get stockConfigNoEpisInUnit =>
      'Ingen verneutstyr er synlig i denne enheten.';

  @override
  String get stockConfigUnitBalance => 'Saldo i enheten';

  @override
  String get stockConfigAttentionLimit => 'Grense for varselintervall';

  @override
  String get stockConfigUnderlyingStatus => 'Fysisk tilstand';

  @override
  String get stockConfigDerivedUnavailable =>
      'De beregnede verdiene kunne ikke oppdateres nå. Parameterne som er lagret over, er riktige.';

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
  String get stockConfigMinimumHelp =>
      'Antall under hvilket verneutstyret regnes som kritisk i denne enheten. Gjelder bare denne enheten.';

  @override
  String get stockConfigMinimumLabel => 'Minimumslager';

  @override
  String get stockConfigMinimumNegativeError =>
      'Skriv inn et heltall lik eller større enn null.';

  @override
  String get stockConfigMinimumSaved =>
      'Minimumslager lagret for denne enheten.';

  @override
  String get stockConfigMinimumRestored =>
      'Minimumslager tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAttentionTitle => 'Varselintervall';

  @override
  String get stockConfigAttentionHelp =>
      'Prosent over minimum der verneutstyret allerede går i varsel i denne enheten. Uavhengig av minimumslageret.';

  @override
  String get stockConfigAttentionRangeError =>
      'Prosenten må være mellom 0 og 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Varselintervall lagret for denne enheten.';

  @override
  String get stockConfigAttentionRestored =>
      'Varselintervall tilbakestilt. Enheten arver selskapets standard igjen.';

  @override
  String get stockConfigAlertTitle => 'Varselovervåking';

  @override
  String get stockConfigAlertHelp =>
      'Å slå den av stopper varsel om lavt lager og automatisk etterfylling for dette verneutstyret i denne enheten. Det endrer verken saldo, minimum eller prosent.';

  @override
  String get stockConfigAlertToggle =>
      'Overvåk lageret for dette verneutstyret';

  @override
  String get stockConfigAlertPending =>
      'Ulagret endring. Klikk Lagre for å bruke den.';

  @override
  String get stockConfigAlertDisableTitle => 'Deaktivere varselet?';

  @override
  String get stockConfigAlertDisableBody =>
      'Dette verneutstyret slutter å gi varsel om lavt lager og automatisk etterfylling i denne enheten. Den fysiske tilstanden vises fortsatt.';

  @override
  String get stockConfigAlertDisableConfirm => 'Deaktiver';

  @override
  String get stockConfigAlertSaved =>
      'Varselovervåking lagret for denne enheten.';

  @override
  String get stockConfigAlertRestored =>
      'Overvåking tilbakestilt. Enheten er tilbake på systemstandarden.';

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
  String get unitSelectorNoUnitsAssigned =>
      'Du har ingen enhet tildelt. Kontakt administratoren.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'Selskapet har ennå ingen enheter registrert.';

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
  String get settingsSelectCompanyFirst =>
      'Velg et selskap i Innstillinger for å fortsette.';

  @override
  String get settingsFichaTileTitle => 'PVU-skjema';

  @override
  String get settingsFichaTileSubtitle =>
      'Tittel, erklæring, merknader og sporbarhet';

  @override
  String get settingsStockTileSubtitle => 'Selskapets standard varselgrense';

  @override
  String get settingsModulesTileSubtitle =>
      'Moduler synlige per profil og per enhet';

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
  String get settingsSubscriptionTileSubtitle =>
      'Abonnement, betalinger og oppsigelse';

  @override
  String get settingsInvoicesTileTitle => 'Betalingshistorikk';

  @override
  String get settingsInvoicesTileSubtitle => 'Alle betalinger og kvitteringer';

  @override
  String get settingsNoPermission =>
      'Du har ikke tillatelse til å endre denne innstillingen.';

  @override
  String get stockPhysicalValidityUnknown => 'Ukjent fysisk utløpsdato';

  @override
  String get stockNoPhysicalStock => 'Ingen fysisk beholdning';

  @override
  String get stockRegularizeValidityTitle => 'Regulariser fysisk gyldighet';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifiser delen og oppgi dokumentert gyldighet. Klassifiseringen gjøres av systemet.';

  @override
  String get stockRegularizeQrLabel => 'QR eller delkode';

  @override
  String get stockRegularizeExpiryLabel => 'Dokumentert fysisk gyldighet';

  @override
  String get stockRegularizeExpirySelect => 'Velg dato';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Dokumentasjon (dokument eller verifiserbar oppføring)';

  @override
  String get stockRegularizeJustificationLabel => 'Begrunnelse';

  @override
  String get stockRegularizeSubmit => 'Regulariser';

  @override
  String get stockRegularizeIncomplete =>
      'Fyll ut delen, gyldigheten, dokumentasjonen og begrunnelsen.';

  @override
  String get stockRegularizeResultEligible =>
      'Gyldighet regularisert. Delen er kvalifisert for utlevering og reservasjon.';

  @override
  String get stockRegularizeResultBlocked =>
      'Gyldighet regularisert. Delen er utløpt og forblir blokkert for utlevering.';

  @override
  String get stockRegularizeResultDone => 'Gyldighet regularisert.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — ulike verneutstyrstyper: $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Fysiske enheter: gyldige $valid, utløper snart $expiring, utløpt $expired, ukjent $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Enheten kan ikke utleveres. Kontroller fysisk utløpsdato, status, reservasjoner og beholdning.';

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
  String get safetyNoDocs =>
      'Ingen publiserte dokumenter for denne konteksten.';

  @override
  String get safetyNoRecords =>
      'Ingen publiserte, autoriserte oppføringer i denne konteksten.';

  @override
  String get safetyCatalogueNotice =>
      'Kataloggodkjenning angir ikke fysisk tilgjengelighet. CA-utløp er separat fra partiutløp.';

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
  String get safetyPrivateNotice =>
      'Private originaler, bevarte versjoner og historikk. Administrasjon begrenset til generell administrator og registeradministrator.';

  @override
  String get safetyAllowAdminDownloads =>
      'Tillat originalnedlasting for autoriserte administratorer';

  @override
  String get safetyPreviewOnlyNotice =>
      'Ansatte har alltid kun forhåndsvisning.';

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
  String get safetyActivities =>
      'Kommaseparerte aktiviteter/stillinger (tomt = alle)';

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
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
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

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Linje $line — $item (vare #$id): faktisk mottatt mengde er ugyldig eller ikke positiv. Korriger mottaket før bekreftelse.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Lagerbeholdning nær minimum: $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Negativ lagerbeholdning: $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Tomt på lager: $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Lagerbeholdning under minimum: $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Lagerbeholdning på minimum: $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - gjeldende beholdning: $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'Brasiliansk CA nær utløpsdato: $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - utløper $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Produsentens utløpsdato er passert: $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Produsentens utløpsdato nærmer seg: $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - produsentens utløpsdato var $date. Ta ut av lageret ($stock $measure): utløpt PVU kan ikke utleveres til ansatte.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - produsentens utløpsdato er $date (om $daysLabel). Prioriter utlevering fra dette partiet ($stock $measure på lager) før utløp (FIFO).';
  }

  @override
  String get operationalAlertSizes => 'Størrelser på lager:';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Hanske:$value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Størrelse:$value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Arbeidstøy:$value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Uspesifisert størrelse';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'enheter',
      one: 'enhet',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'par',
      one: 'par',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel dager',
      one: '$countLabel dag',
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
      other: '$epi: $countLabel fysiske enheter.',
      one: '$epi: $countLabel fysisk enhet.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle => 'Ukjent fysisk utløpsdato';

  @override
  String get operationalAlertPhysicalExpiringTitle => 'Partier nær utløpsdato';

  @override
  String get passwordChangeTitle => 'Angi et nytt passord';

  @override
  String get passwordChangeIntro =>
      'Passordet ditt er midlertidig. Angi et nytt passord for å fortsette av sikkerhetshensyn.';

  @override
  String get passwordChangeCurrent => 'Gjeldende passord (midlertidig)';

  @override
  String get passwordChangeNew => 'Nytt passord';

  @override
  String get passwordChangeConfirm => 'Bekreft nytt passord';

  @override
  String get passwordChangeSave => 'Lagre nytt passord';

  @override
  String get passwordChangeLogout => 'Logg ut';

  @override
  String get passwordChangeCurrentRequired => 'Skriv inn gjeldende passord';

  @override
  String get passwordChangeMinLength =>
      'Det nye passordet må inneholde minst 6 tegn';

  @override
  String get passwordChangeMustDiffer =>
      'Det nye passordet må være forskjellig fra det midlertidige';

  @override
  String get passwordChangeMismatch => 'Passordene samsvarer ikke';

  @override
  String get passwordChangeFailed => 'Kunne ikke endre passordet';

  @override
  String get poSupplierConfirmed => 'Bekreftet';

  @override
  String get poSupplierDeliveryUpdated => 'Levering oppdatert';

  @override
  String get poSupplierRejected => 'Avslått';

  @override
  String get poSupplierIsoDateHint => 'YYYY-MM-DD';

  @override
  String get billingActive => 'Aktivt';

  @override
  String get billingPending => 'Venter';

  @override
  String get billingPaused => 'Satt på pause';

  @override
  String get billingCancelled => 'Avsluttet';

  @override
  String get billingExpired => 'Utløpt';

  @override
  String get billingAnnual => 'Årlig';

  @override
  String get billingMonthly => 'Månedlig';

  @override
  String get billingRecurringCard => 'Kort (gjentakende)';

  @override
  String get billingCard => 'Kort';

  @override
  String get billingBoleto => 'Boleto (brasiliansk betalingsblankett)';

  @override
  String get billingConfirmTitle => 'Er du sikker?';

  @override
  String get billingConfirmBody =>
      'Tilgangen din beholdes til slutten av perioden som allerede er betalt.\nDet foretas ingen nye belastninger.';

  @override
  String get billingConfirmCancel => 'Bekreft avslutning';

  @override
  String get billingCancelledNotice => 'Abonnementet er avsluttet.';

  @override
  String billingCancelFailed(String detail) {
    return 'Kunne ikke avslutte: $detail';
  }

  @override
  String get billingAmount => 'Beløp';

  @override
  String get billingCycle => 'Betalingsperiode';

  @override
  String get billingMethod => 'Betalingsmåte';

  @override
  String get billingStarted => 'Startdato for abonnementet';

  @override
  String get billingNextPayment => 'Neste betaling';

  @override
  String get billingLastPayment => 'Siste betaling';

  @override
  String get billingCancelDate => 'Avsluttet den';

  @override
  String get billingManualRenewal => 'Manuell fornyelse';

  @override
  String get billingMpSubscriptionId => 'Abonnements-ID (MP)';

  @override
  String get billingMpStatus => 'Mercado Pago-status';

  @override
  String get billingTenant => 'Tenant';

  @override
  String get billingCancelAction => 'Avslutt abonnement';

  @override
  String get billingCancelledBody =>
      'Abonnementet er avsluttet. Tilgangen beholdes til slutten av perioden som allerede er betalt. Det foretas ingen nye belastninger.';

  @override
  String get billingEmptyTitle => 'Ingen aktive abonnementer';

  @override
  String get billingEmptyBody =>
      'Abonnementsdetaljene vises her når et abonnement er bestilt.';

  @override
  String get billingLoadFailed => 'Kunne ikke laste abonnementet.';

  @override
  String get billingInvoicePaid => 'Betalt';

  @override
  String get billingInvoicePending => 'Venter';

  @override
  String get billingInvoiceCancelled => 'Kansellert';

  @override
  String get billingInvoiceRefunded => 'Refundert';

  @override
  String get billingInvoiceFailed => 'Mislyktes';

  @override
  String get billingOpenReceipt => 'Åpne kvittering';

  @override
  String get billingReceiptOpenFailed => 'Kunne ikke åpne kvitteringen.';

  @override
  String get billingHistoryLoadFailed =>
      'Kunne ikke laste betalingshistorikken.';

  @override
  String get billingInvoicesEmptyTitle => 'Fant ingen betalinger';

  @override
  String get billingInvoicesEmptyBody =>
      'Betalingene for abonnementet ditt vises her.';

  @override
  String get feedbackTitle => 'Vurderinger av verneutstyr';

  @override
  String get feedbackLoadFailed => 'Kunne ikke laste vurderingene';

  @override
  String get feedbackEmpty => 'Ingen vurderinger funnet';

  @override
  String get feedbackValidate => 'Valider';

  @override
  String get feedbackStatusOpen => 'Åpen';

  @override
  String get feedbackStatusResolved => 'Løst';

  @override
  String get feedbackStatusClosed => 'Lukket';

  @override
  String get feedbackStatusReceived => 'Mottatt';

  @override
  String get feedbackStatusManagerReview =>
      'Under vurdering hos ansvarlig for verneutstyr';

  @override
  String get feedbackStatusAwaitingHseq => 'Venter på HSEQ-vurdering';

  @override
  String get feedbackStatusHseqCompleted => 'HSEQ-vurdering fullført';

  @override
  String get feedbackStatusForwardedAdmin => 'Videresendt til administrasjonen';

  @override
  String get feedbackStatusAwaitingAdmin =>
      'Venter på administrativ godkjenning';

  @override
  String get feedbackStatusCorrectiveAction => 'Åpent korrigerende tiltak';

  @override
  String get feedbackStatusMoreInformation => 'Mer informasjon etterspurt';

  @override
  String get feedbackStatusEnded => 'Avsluttet';

  @override
  String get feedbackStatusNotApproved => 'Ikke godkjent';
}
