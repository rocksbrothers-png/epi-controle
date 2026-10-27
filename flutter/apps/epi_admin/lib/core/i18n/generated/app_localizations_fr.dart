// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

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
  String get employeeCpfLabel => 'CPF brésilien';

  @override
  String get employeeSectorLabel => 'Département';

  @override
  String get employeeRoleLabel => 'Poste';

  @override
  String get employeeUnitLabel => 'Unité';

  @override
  String get employeeUnitLockedHint =>
      'Unité définie par votre profil d\'accès.';

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
  String get episSearchHint => 'Rechercher par nom, CA brésilien ou code';

  @override
  String get epiNameLabel => 'Nom de l\'EPI';

  @override
  String get epiCodeLabel => 'Code d\'achat';

  @override
  String get epiCaLabel => 'CA — certificat d’approbation brésilien';

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
  String get epiCaExpiryLabel => 'Expiration du CA brésilien';

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
  String get epiArchiveBlockTitle => 'Archiver avec blocage du stock';

  @override
  String get epiArchiveBlockBody =>
      'Cet EPI a du stock disponible ou des liens actifs. En confirmant, le stock disponible est déplacé vers le Stock bloqué (traçable) et l\'EPI est archivé.';

  @override
  String get epiArchiveBlockConfirm => 'Bloquer le stock et archiver';

  @override
  String get epiArchiveReasonLabel => 'Motif d\'archivage (audit)';

  @override
  String get epiArchiveReasonRequired => 'Indiquez un motif pour continuer.';

  @override
  String get epiArchiveBlockableLabel => 'Stock à bloquer';

  @override
  String get epiArchiveLiveLinksTitle => 'Liens actifs';

  @override
  String get epiArchiveAvailable => 'Disponible';

  @override
  String get epiArchiveInTransit => 'En transit';

  @override
  String get epiArchiveInPossession => 'En possession';

  @override
  String get epiArchivePendingRequests => 'Demandes ouvertes';

  @override
  String get epiArchivePendingPurchase => 'Achats ouverts';

  @override
  String get dashboardComplianceTitle => 'Conformité du stock';

  @override
  String get dashboardComplianceAllOk => 'Stock conforme';

  @override
  String get complianceCaExpired => 'CA expiré';

  @override
  String get complianceCaExpiring => 'CA à expirer';

  @override
  String get complianceProductExpired => 'Produit expiré';

  @override
  String get complianceProductExpiring => 'Produit à expirer';

  @override
  String get complianceMissingManufacture => 'Sans fabrication';

  @override
  String get complianceMissingLot => 'Sans lot';

  @override
  String get complianceAdminBlocked => 'Bloqué';

  @override
  String get handoverTitle => 'Remise de livraison';

  @override
  String get handoverPrompt =>
      'Scannez le QR de livraison ou saisissez le code.';

  @override
  String get handoverCodeLabel => 'Code de livraison';

  @override
  String get handoverLookupButton => 'Rechercher la livraison';

  @override
  String get handoverScanButton => 'Scanner le QR';

  @override
  String get handoverConfirmButton => 'Confirmer la réception';

  @override
  String get handoverConfirmedTitle => 'Réception confirmée';

  @override
  String get handoverAlreadyConfirmed =>
      'Cette livraison a déjà été confirmée.';

  @override
  String get handoverNotFound => 'Aucune livraison trouvée pour ce code.';

  @override
  String get handoverConfirmError => 'Impossible de confirmer la réception.';

  @override
  String get handoverEmployeeLabel => 'Employé';

  @override
  String get handoverEpiLabel => 'EPI';

  @override
  String get handoverQuantityLabel => 'Quantité';

  @override
  String get handoverSectorLabel => 'Secteur';

  @override
  String get handoverRoleLabel => 'Fonction';

  @override
  String get handoverUnitLabel => 'Unité';

  @override
  String get handoverDeliveryDateLabel => 'Date de livraison';

  @override
  String get handoverReceiverNameLabel => 'Nom du destinataire (facultatif)';

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
  String get legalEntityCnpjLabel => 'CNPJ (identifiant fiscal brésilien)';

  @override
  String get legalEntityUfLabel => 'État';

  @override
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRaison sociale\tNom commercial\tType';

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
  String get outsourcedCompanyLinkTitle =>
      'Rattacher l\'entreprise à cette Unité';

  @override
  String get outsourcedCompanyLinkHint =>
      'Rechercher une entreprise déjà enregistrée dans le tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Déjà rattachées à cette Unité';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponibles au rattachement';

  @override
  String get outsourcedCompanyLinkLink => 'Rattacher à cette Unité';

  @override
  String get outsourcedCompanyLinkActivate => 'Réactiver dans cette Unité';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archiver dans cette Unité';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motif de l\'archivage (facultatif) :';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Utilisée par $count Unité(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unité d\'origine';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Aucune entreprise trouvée pour ce terme.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Rattachement non communiqué pour votre profil';

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
  String get employeeUnitLinkColumn => 'Lien local';

  @override
  String get employeeUnitLink => 'Rattacher à mon unité';

  @override
  String get employeeUnitLinkActivate => 'Réactiver dans cette Unité';

  @override
  String get employeeUnitLinkDeactivate => 'Archiver dans cette Unité';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motif de l\'archivage (facultatif) :';

  @override
  String get employeeUnitLinkActive => 'Rattaché';

  @override
  String get employeeUnitLinkArchived => 'Archivé dans cette Unité';

  @override
  String get employeeUnitLinkAbsent => 'Non rattaché';

  @override
  String get employeeUnitLinksTitle => 'Rattachements par Unité';

  @override
  String get employeeUnitLinksEmpty =>
      'Ce collaborateur n\'a de rattachement à aucune Unité que vous pouvez consulter.';

  @override
  String get employeeUnitLinksError =>
      'Impossible de charger les rattachements.';

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

  @override
  String get stockTabAvailable => 'Disponibles';

  @override
  String get stockTabBlocked => 'Bloqués';

  @override
  String get stockAvailableSelectEpi =>
      'Sélectionnez un EPI pour voir les articles disponibles';

  @override
  String get stockAvailableEmpty =>
      'Aucun article disponible pour cet EPI dans cette unité';

  @override
  String get stockBlockedEmpty => 'Aucun article bloqué';

  @override
  String get stockNoOperationalUnit =>
      'Votre profil n\'a pas d\'unité opérationnelle active. Contactez un administrateur pour accéder au stock.';

  @override
  String get stockItemLotLabel => 'Lot';

  @override
  String get stockStatusBlockedExpired => 'Périmé';

  @override
  String get stockStatusBlockedDiscard => 'En attente de mise au rebut';

  @override
  String get stockStatusBlockedReturn => 'En attente de retour au fournisseur';

  @override
  String get stockStatusBlockedAnalysis => 'En cours d\'analyse';

  @override
  String get stockStatusBlockedRejected => 'Refusé';

  @override
  String get stockStatusBlockedArchived => 'EPI archivé';

  @override
  String get stockStatusUnknown => 'Statut non reconnu';

  @override
  String get stockUnitBalanceSuffix => 'dans l\'unité';

  @override
  String get stockCompanyBalanceLabel => 'entreprise';

  @override
  String get stockMinimumShort => 'min';

  @override
  String get deliveryStepItem => 'Article';

  @override
  String get deliveryItemTitle => 'Sélectionnez l\'unité étiquetée';

  @override
  String get deliveryItemEmpty => 'Aucun article disponible dans cette Unité.';

  @override
  String get deliveryItemScan => 'Scanner le QR de l\'article';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Stock de l\'Unité : $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Collaborateur sans Unité opérationnelle : la remise ne peut pas être enregistrée.';

  @override
  String get deliveryQrOtherEpi => 'Le code scanné appartient à un autre EPI.';

  @override
  String get stockUnitRequiredToMove =>
      'Sélectionnez une Unité pour déplacer le stock.';

  @override
  String get stockAttentionSectionTitle => 'Stock';

  @override
  String get stockAttentionCompanyTitle =>
      'Plage d\'attention — valeur par défaut de l\'entreprise';

  @override
  String get stockAttentionCompanyHelp =>
      'S\'applique aux Unités qui n\'ont pas défini leur propre pourcentage. Ne modifie aucune Unité déjà configurée.';

  @override
  String get stockAttentionPercentageLabel =>
      'Pourcentage de la plage d\'attention';

  @override
  String get stockAttentionOriginLabel => 'Origine';

  @override
  String get stockAttentionOriginCompany => 'Défini par l\'entreprise';

  @override
  String get stockAttentionOriginSystem => 'Valeur par défaut du système';

  @override
  String get stockAttentionSave => 'Enregistrer la valeur de l\'entreprise';

  @override
  String get stockAttentionRestore => 'Rétablir la valeur du système';

  @override
  String get stockAttentionSaved =>
      'Valeur par défaut de l\'entreprise enregistrée.';

  @override
  String get stockAttentionRestored =>
      'Valeur de l\'entreprise supprimée. L\'entreprise revient à la valeur du système.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Valeur du système : $value %';
  }

  @override
  String get stockConfigTitle => 'Configuration du stock';

  @override
  String get stockConfigIntro =>
      'Définissez le stock minimum, la plage d’attention et la surveillance d’alerte d’un EPI dans une Unité. Chaque paramètre est enregistré séparément.';

  @override
  String get stockConfigUnitLabel => 'Unité à configurer';

  @override
  String get stockConfigSelectUnit =>
      'Sélectionnez l’Unité pour configurer ses paramètres.';

  @override
  String get stockConfigSelectEpi =>
      'Sélectionnez l’EPI pour voir et modifier les paramètres de cette Unité.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'Impossible de charger la liste des EPI de cette Unité.';

  @override
  String get stockConfigNoEpisInUnit =>
      'Aucun EPI n’est visible dans cette Unité.';

  @override
  String get stockConfigUnitBalance => 'Solde dans l’Unité';

  @override
  String get stockConfigAttentionLimit => 'Limite de la plage d’attention';

  @override
  String get stockConfigUnderlyingStatus => 'État physique';

  @override
  String get stockConfigDerivedUnavailable =>
      'Les valeurs calculées n’ont pas pu être actualisées maintenant. Les paramètres enregistrés ci-dessus sont corrects.';

  @override
  String get stockConfigStatusCritical => 'Critique';

  @override
  String get stockConfigStatusNearMinimum => 'Proche du minimum';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alerte désactivée';

  @override
  String get stockConfigMinimumTitle => 'Stock minimum';

  @override
  String get stockConfigMinimumHelp =>
      'Quantité en dessous de laquelle l’EPI est considéré comme critique dans cette Unité. Ne vaut que pour cette Unité.';

  @override
  String get stockConfigMinimumLabel => 'Stock minimum';

  @override
  String get stockConfigMinimumNegativeError =>
      'Saisissez un nombre entier supérieur ou égal à zéro.';

  @override
  String get stockConfigMinimumSaved =>
      'Stock minimum enregistré pour cette Unité.';

  @override
  String get stockConfigMinimumRestored =>
      'Stock minimum rétabli. L’Unité hérite de nouveau de la valeur de l’entreprise.';

  @override
  String get stockConfigAttentionTitle => 'Plage d’attention';

  @override
  String get stockConfigAttentionHelp =>
      'Pourcentage au-dessus du minimum à partir duquel l’EPI entre déjà en attention dans cette Unité. Indépendant du stock minimum.';

  @override
  String get stockConfigAttentionRangeError =>
      'Le pourcentage doit être compris entre 0 et 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Plage d’attention enregistrée pour cette Unité.';

  @override
  String get stockConfigAttentionRestored =>
      'Plage d’attention rétablie. L’Unité hérite de nouveau de la valeur de l’entreprise.';

  @override
  String get stockConfigAlertTitle => 'Surveillance d’alerte';

  @override
  String get stockConfigAlertHelp =>
      'La désactiver interrompt l’alerte de stock bas et le réapprovisionnement automatique de cet EPI dans cette Unité. Elle ne modifie ni le solde, ni le minimum, ni le pourcentage.';

  @override
  String get stockConfigAlertToggle => 'Surveiller le stock de cet EPI';

  @override
  String get stockConfigAlertPending =>
      'Modification en attente. Cliquez sur Enregistrer pour l’appliquer.';

  @override
  String get stockConfigAlertDisableTitle => 'Désactiver l’alerte ?';

  @override
  String get stockConfigAlertDisableBody =>
      'Cet EPI cessera de générer des alertes de stock bas et du réapprovisionnement automatique dans cette Unité. L’état physique restera affiché.';

  @override
  String get stockConfigAlertDisableConfirm => 'Désactiver';

  @override
  String get stockConfigAlertSaved =>
      'Surveillance d’alerte enregistrée pour cette Unité.';

  @override
  String get stockConfigAlertRestored =>
      'Surveillance rétablie. L’Unité revient à la valeur du système.';

  @override
  String get stockConfigOriginUnit => 'Défini par cette Unité';

  @override
  String get stockConfigOriginCompany => 'Hérité de la valeur de l’entreprise';

  @override
  String get stockConfigOriginUnknown => 'Non renseignée';

  @override
  String get stockConfigSave => 'Enregistrer';

  @override
  String get stockConfigRestore => 'Rétablir l’héritage';

  @override
  String stockAttentionRangeError(int max) {
    return 'Saisissez un pourcentage entier entre 0 et $max.';
  }

  @override
  String get stockAttentionLoadError =>
      'Impossible de charger la valeur par défaut de l\'entreprise.';

  @override
  String get unitSelectorLabel => 'Unité';

  @override
  String get unitSelectorAllUnits => 'Toutes les Unités';

  @override
  String get unitSelectorLockedHint =>
      'Votre profil opère dans une Unité fixe.';

  @override
  String get unitSelectorLoadError => 'Impossible de charger les Unités.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'Aucune Unité ne vous est attribuée. Contactez l\'administrateur.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'L\'entreprise n\'a encore aucune Unité enregistrée.';

  @override
  String get settingsSectionCompany => 'Entreprise';

  @override
  String get settingsSectionOperation => 'Exploitation';

  @override
  String get settingsSectionSubscription => 'Abonnement';

  @override
  String get settingsCompanyLabel => 'Entreprise';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Entreprise administrée : $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Sélectionnez une entreprise dans Paramètres pour continuer.';

  @override
  String get settingsFichaTileTitle => 'Fiche d\'EPI';

  @override
  String get settingsFichaTileSubtitle =>
      'Titre, déclaration, observations et traçabilité';

  @override
  String get settingsStockTileSubtitle =>
      'Seuil d\'alerte par défaut de l\'entreprise';

  @override
  String get settingsModulesTileSubtitle =>
      'Modules visibles par profil et par Unité';

  @override
  String get settingsArchivalTitle => 'Archivage et conservation';

  @override
  String get settingsArchivalSubtitle =>
      'Années de conservation des enregistrements archivés';

  @override
  String get settingsAppearanceTitle => 'Apparence et langue';

  @override
  String get settingsAppearanceSubtitle =>
      'Thème de l\'interface et langue de l\'application';

  @override
  String get settingsSubscriptionTileTitle => 'Mon abonnement';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Formule, facturation et résiliation';

  @override
  String get settingsInvoicesTileTitle => 'Historique financier';

  @override
  String get settingsInvoicesTileSubtitle =>
      'Toutes les factures et tous les reçus';

  @override
  String get settingsNoPermission =>
      'Vous n\'avez pas l\'autorisation de modifier ce paramètre.';

  @override
  String get stockPhysicalValidityUnknown => 'Expiration physique inconnue';

  @override
  String get stockNoPhysicalStock => 'Aucun stock physique';

  @override
  String get stockRegularizeValidityTitle => 'Régulariser la validité physique';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifiez la pièce et indiquez la validité justifiée. Le classement est effectué par le système.';

  @override
  String get stockRegularizeQrLabel => 'QR ou code de la pièce';

  @override
  String get stockRegularizeExpiryLabel => 'Validité physique justifiée';

  @override
  String get stockRegularizeExpirySelect => 'Sélectionner une date';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Preuve (document ou enregistrement vérifiable)';

  @override
  String get stockRegularizeJustificationLabel => 'Justification';

  @override
  String get stockRegularizeSubmit => 'Régulariser';

  @override
  String get stockRegularizeIncomplete =>
      'Renseignez la pièce, la validité, la preuve et la justification.';

  @override
  String get stockRegularizeResultEligible =>
      'Validité régularisée. La pièce est éligible à la remise et à la réservation.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validité régularisée. La pièce est expirée et reste bloquée pour la remise.';

  @override
  String get stockRegularizeResultDone => 'Validité régularisée.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPI distincts : $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Pièces physiques : valides $valid, proches $expiring, expirées $expired, inconnues $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Pièce indisponible pour remise. Vérifiez expiration physique, état, réservations et solde.';

  @override
  String get safetyTitle => 'Bibliothèque de sécurité';

  @override
  String get safetyApproved => 'EPI approuvés';

  @override
  String get safetyRetry => 'Réessayer';

  @override
  String get safetyClose => 'Fermer';

  @override
  String get safetyCancel => 'Annuler';

  @override
  String get safetyConfirm => 'Confirmer';

  @override
  String get safetyAccess => 'Accéder';

  @override
  String get safetyPortalConfirm => 'Confirmer l’accès au portail';

  @override
  String get safetyCpfLast => 'Trois derniers chiffres du CPF';

  @override
  String get safetyView => 'Consulter';

  @override
  String get safetyFit => 'Ajuster';

  @override
  String get safetyZoomIn => 'Agrandir';

  @override
  String get safetyZoomOut => 'Réduire';

  @override
  String get safetyNextPage => 'Page suivante';

  @override
  String get safetyPreviousPage => 'Page précédente';

  @override
  String get safetyDocument => 'Document';

  @override
  String get safetyDetails => 'Détails';

  @override
  String get safetyRelatedDocuments => 'Documents associés';

  @override
  String get safetyRelatedEpis => 'EPI associés';

  @override
  String get safetyRelatedEpi => 'EPI associé';

  @override
  String get safetyAllEpis => 'Tous les EPI';

  @override
  String get safetyAllCategories => 'Toutes les catégories';

  @override
  String get safetyNoDocs => 'Aucun document publié pour ce contexte.';

  @override
  String get safetyNoRecords =>
      'Aucun enregistrement publié et autorisé dans ce contexte.';

  @override
  String get safetyCatalogueNotice =>
      'L’approbation du catalogue ne garantit pas la disponibilité physique. La validité du CA est distincte de celle du lot.';

  @override
  String get safetyName => 'EPI';

  @override
  String get safetyManufacturer => 'Fabricant';

  @override
  String get safetyModel => 'Modèle/référence';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Validité du CA';

  @override
  String get safetyUsefulLife => 'Durée de vie (mois)';

  @override
  String get safetyProtection => 'Protection';

  @override
  String get safetySection => 'Section';

  @override
  String get safetyRecommendations => 'Recommandations/restrictions';

  @override
  String get safetyUnknown => 'Non renseigné';

  @override
  String get safetySearch => 'Rechercher';

  @override
  String get safetyViewEpi => 'Voir l’EPI';

  @override
  String get safetyHistory => 'Historique';

  @override
  String get safetyDocumentHistory => 'Historique du document';

  @override
  String get safetyPublish => 'Publier';

  @override
  String get safetyPublishVersion => 'Publier la version';

  @override
  String get safetyArchive => 'Archiver le document';

  @override
  String get safetyArchiveVersions => 'Archiver le document et ses versions';

  @override
  String get safetyReason => 'Justification obligatoire';

  @override
  String get safetyNew => 'Nouveau document';

  @override
  String get safetyCreateNew => 'Créer un document';

  @override
  String get safetyMetadata => 'Informations de version';

  @override
  String get safetyEmptyAdmin => 'Aucun document enregistré.';

  @override
  String get safetyPrivateNotice =>
      'Originaux privés, versions et historique conservés. Gestion réservée aux administrateurs général et de registre.';

  @override
  String get safetyAllowAdminDownloads =>
      'Autoriser le téléchargement des originaux aux administrateurs habilités';

  @override
  String get safetyPreviewOnlyNotice =>
      'Les collaborateurs accèdent uniquement à l’aperçu.';

  @override
  String get safetyPolicyReason =>
      'Modifier la politique de téléchargement administratif';

  @override
  String get safetySearchVersions => 'Rechercher un titre ou une version';

  @override
  String get safetyChooseFile => 'Choisir un fichier';

  @override
  String get safetyFilePickerLabel => 'Documents de sécurité';

  @override
  String get safetyUnitRequired => 'Sélectionnez au moins une unité';

  @override
  String get safetyAllUnits => 'Toutes les unités de l’entreprise';

  @override
  String get safetyRequired => 'Obligatoire';

  @override
  String get safetyDocumentTitle => 'Titre';

  @override
  String get safetyVersion => 'Version';

  @override
  String get safetyEffectiveDate => 'Entrée en vigueur (AAAA-MM-JJ)';

  @override
  String get safetySectors => 'Secteurs séparés par des virgules (vide = tous)';

  @override
  String get safetyActivities =>
      'Activités/fonctions séparées par des virgules (vide = toutes)';

  @override
  String get safetyUpload => 'Enregistrer ou versionner un document';

  @override
  String get safetyRendering => 'Création de l’aperçu sécurisé…';

  @override
  String get safetyFileLimit => 'Sélectionnez un fichier de 20 Mio maximum.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Version $version · Entrée en vigueur $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unité de consultation : $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Aperçu indisponible : $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Enregistrement refusé ; aperçu indisponible : $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Version $version / révision $revision · $state · Entrée en vigueur $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsable $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matrice d’application des EPI';

  @override
  String get safetyCategoryGlove => 'Matrice de sélection des gants';

  @override
  String get safetyCategoryCare => 'Guides de nettoyage et d’entretien';

  @override
  String get safetyCategoryUse => 'Instructions d’utilisation des EPI';

  @override
  String get safetyCategoryTechnical => 'Manuels et fiches techniques';

  @override
  String get safetyCategoryOther => 'Autres documents de sécurité';

  @override
  String get safetyStateDraft => 'Brouillon';

  @override
  String get safetyStatePublished => 'Publié';

  @override
  String get safetyStateSuperseded => 'Remplacé';

  @override
  String get safetyStateArchived => 'Archivé';

  @override
  String get prConfTitle => 'Conférence de Réception';

  @override
  String get prConfIntro =>
      'Cochez chaque article selon la réception réelle. Indiquez la validité physique du fabricant et la preuve vérifiable ; utilisez « Séparer en lots » pour des validités différentes ou des exceptions individuelles. Les pièces sans validité prouvée entrent BLOQUÉES.';

  @override
  String get prConfReceivedYes => 'Reçu';

  @override
  String get prConfReceivedNo => 'Non reçu';

  @override
  String get prConfEvidence => 'Preuve vérifiable';

  @override
  String get prConfEvidenceHint => 'Étiquette / facture / photo';

  @override
  String get prConfEvidenceRequired =>
      'La preuve vérifiable est obligatoire lorsqu\'une validité est saisie.';

  @override
  String get prConfSplitLots => 'Séparer en lots';

  @override
  String get prConfSingleDate => 'Utiliser une date unique';

  @override
  String get prConfAddLot => 'Ajouter un lot';

  @override
  String get prConfAddException => 'Exception (1 pièce)';

  @override
  String get prConfLotQty => 'Qté';

  @override
  String get prConfLotCode => 'Identification';

  @override
  String get prConfRemoveLot => 'Retirer le lot';

  @override
  String get prConfPreview => 'Aperçu — validité physique par pièce';

  @override
  String get prConfBlocked => 'SANS validité → BLOQUÉES';

  @override
  String get prConfExpired => 'expirée';

  @override
  String get prConfPiece => 'pièce(s)';

  @override
  String get prConfSumMismatch =>
      'La somme des quantités des lots ne correspond pas à la quantité reçue.';

  @override
  String get prConfLotQtyPositive =>
      'Chaque lot doit avoir une quantité supérieure à zéro.';

  @override
  String get prConfNotes => 'Observations sur les articles non reçus';

  @override
  String get prConfNotesRequired =>
      'Indiquez les observations sur les articles non reçus.';

  @override
  String get prConfSubmit => 'Enregistrer la Conférence';

  @override
  String get prConfDone => 'Conférence enregistrée.';

  @override
  String get prConfEmpty => 'Aucun article éligible à la conférence.';

  @override
  String get prConfInvalidQuantity =>
      'La quantité effectivement reçue est invalide ou non positive. Corrigez la réception avant de confirmer.';

  @override
  String get prConfNoPersistedPieces =>
      'Aucune pièce enregistrée ou réponse incohérente. L’entrée en stock n’a pas été confirmée.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count pièces effectivement enregistrées en stock.';
  }

  @override
  String get prConfNoStockEntry =>
      'Vérification enregistrée sans entrée de pièces en stock.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Ligne $line — $item (article #$id) : quantité effectivement reçue invalide ou non positive. Corrigez la réception avant de confirmer.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Stock proche du minimum : $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Solde de stock négatif : $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Rupture de stock : $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Stock inférieur au minimum : $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Stock au seuil minimum : $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - solde actuel de $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'CA brésilien proche de son expiration : $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - expire le $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Date de validité du fabricant dépassée : $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Date de validité du fabricant proche : $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - validité du fabricant expirée le $date. Retirer du stock ($stock $measure) : un EPI périmé ne peut pas être remis au salarié.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - validité du fabricant jusqu’au $date (dans $daysLabel). Donner la priorité à la remise de ce lot ($stock $measure en stock) avant expiration (PEPS).';
  }

  @override
  String get operationalAlertSizes => 'Tailles en stock :';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Gant : $value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Taille : $value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Tenue : $value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Taille non précisée';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'unités',
      one: 'unité',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'paires',
      one: 'paire',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel jours',
      one: '$countLabel jour',
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
      other: '$epi : $countLabel pièces physiques.',
      one: '$epi : $countLabel pièce physique.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Date de validité physique inconnue';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Lots proches de l’expiration';

  @override
  String get passwordChangeTitle => 'Définissez un nouveau mot de passe';

  @override
  String get passwordChangeIntro =>
      'Votre mot de passe est temporaire. Par sécurité, définissez un nouveau mot de passe pour continuer.';

  @override
  String get passwordChangeCurrent => 'Mot de passe actuel (temporaire)';

  @override
  String get passwordChangeNew => 'Nouveau mot de passe';

  @override
  String get passwordChangeConfirm => 'Confirmer le nouveau mot de passe';

  @override
  String get passwordChangeSave => 'Enregistrer le nouveau mot de passe';

  @override
  String get passwordChangeLogout => 'Se déconnecter';

  @override
  String get passwordChangeCurrentRequired =>
      'Saisissez votre mot de passe actuel';

  @override
  String get passwordChangeMinLength =>
      'Le nouveau mot de passe doit comporter au moins 6 caractères';

  @override
  String get passwordChangeMustDiffer =>
      'Le nouveau mot de passe doit être différent du mot de passe temporaire';

  @override
  String get passwordChangeMismatch => 'Les mots de passe ne correspondent pas';

  @override
  String get passwordChangeFailed => 'Impossible de modifier le mot de passe';

  @override
  String get poSupplierConfirmed => 'Confirmé';

  @override
  String get poSupplierDeliveryUpdated => 'Livraison mise à jour';

  @override
  String get poSupplierRejected => 'Refusé';

  @override
  String get poSupplierIsoDateHint => 'AAAA-MM-JJ';
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
  String get employeeCpfLabel => 'CPF brésilien';

  @override
  String get employeeSectorLabel => 'Département';

  @override
  String get employeeRoleLabel => 'Poste';

  @override
  String get employeeUnitLabel => 'Unité';

  @override
  String get employeeUnitLockedHint =>
      'Unité définie par votre profil d\'accès.';

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
  String get episSearchHint => 'Rechercher par nom, CA brésilien ou code';

  @override
  String get epiNameLabel => 'Nom de l\'EPI';

  @override
  String get epiCodeLabel => 'Code d\'achat';

  @override
  String get epiCaLabel => 'CA — certificat d’approbation brésilien';

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
  String get epiCaExpiryLabel => 'Expiration du CA brésilien';

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
  String get epiArchiveBlockTitle => 'Archiver avec blocage du stock';

  @override
  String get epiArchiveBlockBody =>
      'Cet EPI a du stock disponible ou des liens actifs. En confirmant, le stock disponible est déplacé vers le Stock bloqué (traçable) et l\'EPI est archivé.';

  @override
  String get epiArchiveBlockConfirm => 'Bloquer le stock et archiver';

  @override
  String get epiArchiveReasonLabel => 'Motif d\'archivage (audit)';

  @override
  String get epiArchiveReasonRequired => 'Indiquez un motif pour continuer.';

  @override
  String get epiArchiveBlockableLabel => 'Stock à bloquer';

  @override
  String get epiArchiveLiveLinksTitle => 'Liens actifs';

  @override
  String get epiArchiveAvailable => 'Disponible';

  @override
  String get epiArchiveInTransit => 'En transit';

  @override
  String get epiArchiveInPossession => 'En possession';

  @override
  String get epiArchivePendingRequests => 'Demandes ouvertes';

  @override
  String get epiArchivePendingPurchase => 'Achats ouverts';

  @override
  String get dashboardComplianceTitle => 'Conformité du stock';

  @override
  String get dashboardComplianceAllOk => 'Stock conforme';

  @override
  String get complianceCaExpired => 'CA expiré';

  @override
  String get complianceCaExpiring => 'CA à expirer';

  @override
  String get complianceProductExpired => 'Produit expiré';

  @override
  String get complianceProductExpiring => 'Produit à expirer';

  @override
  String get complianceMissingManufacture => 'Sans fabrication';

  @override
  String get complianceMissingLot => 'Sans lot';

  @override
  String get complianceAdminBlocked => 'Bloqué';

  @override
  String get handoverTitle => 'Remise de livraison';

  @override
  String get handoverPrompt =>
      'Scannez le QR de livraison ou saisissez le code.';

  @override
  String get handoverCodeLabel => 'Code de livraison';

  @override
  String get handoverLookupButton => 'Rechercher la livraison';

  @override
  String get handoverScanButton => 'Scanner le QR';

  @override
  String get handoverConfirmButton => 'Confirmer la réception';

  @override
  String get handoverConfirmedTitle => 'Réception confirmée';

  @override
  String get handoverAlreadyConfirmed =>
      'Cette livraison a déjà été confirmée.';

  @override
  String get handoverNotFound => 'Aucune livraison trouvée pour ce code.';

  @override
  String get handoverConfirmError => 'Impossible de confirmer la réception.';

  @override
  String get handoverEmployeeLabel => 'Employé';

  @override
  String get handoverEpiLabel => 'EPI';

  @override
  String get handoverQuantityLabel => 'Quantité';

  @override
  String get handoverSectorLabel => 'Secteur';

  @override
  String get handoverRoleLabel => 'Fonction';

  @override
  String get handoverUnitLabel => 'Unité';

  @override
  String get handoverDeliveryDateLabel => 'Date de livraison';

  @override
  String get handoverReceiverNameLabel => 'Nom du destinataire (facultatif)';

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
  String get legalEntityCnpjLabel => 'CNPJ (identifiant fiscal brésilien)';

  @override
  String get legalEntityUfLabel => 'État';

  @override
  String get legalEntitiesImportColumnsHint =>
      'CNPJ\tRaison sociale\tNom commercial\tType';

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
  String get outsourcedCompanyLinkTitle =>
      'Rattacher l\'entreprise à cette Unité';

  @override
  String get outsourcedCompanyLinkHint =>
      'Rechercher une entreprise déjà enregistrée dans le tenant…';

  @override
  String get outsourcedCompanyLinkSectionLinked =>
      'Déjà rattachées à cette Unité';

  @override
  String get outsourcedCompanyLinkSectionAvailable =>
      'Disponibles au rattachement';

  @override
  String get outsourcedCompanyLinkLink => 'Rattacher à cette Unité';

  @override
  String get outsourcedCompanyLinkActivate => 'Réactiver dans cette Unité';

  @override
  String get outsourcedCompanyLinkDeactivate => 'Archiver dans cette Unité';

  @override
  String get outsourcedCompanyLinkDeactivateReason =>
      'Motif de l\'archivage (facultatif) :';

  @override
  String outsourcedCompanyLinkUsedByUnits(int count) {
    return 'Utilisée par $count Unité(s)';
  }

  @override
  String get outsourcedCompanyLinkOriginUnit => 'Unité d\'origine';

  @override
  String get outsourcedCompanyLinkEmpty =>
      'Aucune entreprise trouvée pour ce terme.';

  @override
  String get outsourcedCompanyLinkNotInformed =>
      'Rattachement non communiqué pour votre profil';

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
  String get employeeUnitLinkColumn => 'Lien local';

  @override
  String get employeeUnitLink => 'Rattacher à mon unité';

  @override
  String get employeeUnitLinkActivate => 'Réactiver dans cette Unité';

  @override
  String get employeeUnitLinkDeactivate => 'Archiver dans cette Unité';

  @override
  String get employeeUnitLinkDeactivateReason =>
      'Motif de l\'archivage (facultatif) :';

  @override
  String get employeeUnitLinkActive => 'Rattaché';

  @override
  String get employeeUnitLinkArchived => 'Archivé dans cette Unité';

  @override
  String get employeeUnitLinkAbsent => 'Non rattaché';

  @override
  String get employeeUnitLinksTitle => 'Rattachements par Unité';

  @override
  String get employeeUnitLinksEmpty =>
      'Ce collaborateur n\'a de rattachement à aucune Unité que vous pouvez consulter.';

  @override
  String get employeeUnitLinksError =>
      'Impossible de charger les rattachements.';

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

  @override
  String get stockTabAvailable => 'Disponibles';

  @override
  String get stockTabBlocked => 'Bloqués';

  @override
  String get stockAvailableSelectEpi =>
      'Sélectionnez un EPI pour voir les articles disponibles';

  @override
  String get stockAvailableEmpty =>
      'Aucun article disponible pour cet EPI dans cette unité';

  @override
  String get stockBlockedEmpty => 'Aucun article bloqué';

  @override
  String get stockNoOperationalUnit =>
      'Votre profil n\'a pas d\'unité opérationnelle active. Contactez un administrateur pour accéder au stock.';

  @override
  String get stockItemLotLabel => 'Lot';

  @override
  String get stockStatusBlockedExpired => 'Périmé';

  @override
  String get stockStatusBlockedDiscard => 'En attente de mise au rebut';

  @override
  String get stockStatusBlockedReturn => 'En attente de retour au fournisseur';

  @override
  String get stockStatusBlockedAnalysis => 'En cours d\'analyse';

  @override
  String get stockStatusBlockedRejected => 'Refusé';

  @override
  String get stockStatusBlockedArchived => 'EPI archivé';

  @override
  String get stockStatusUnknown => 'Statut non reconnu';

  @override
  String get stockUnitBalanceSuffix => 'dans l\'unité';

  @override
  String get stockCompanyBalanceLabel => 'entreprise';

  @override
  String get stockMinimumShort => 'min';

  @override
  String get deliveryStepItem => 'Article';

  @override
  String get deliveryItemTitle => 'Sélectionnez l\'unité étiquetée';

  @override
  String get deliveryItemEmpty => 'Aucun article disponible dans cette Unité.';

  @override
  String get deliveryItemScan => 'Scanner le QR de l\'article';

  @override
  String deliveryUnitStockAvailable(int qty) {
    return 'Stock de l\'Unité : $qty';
  }

  @override
  String get deliveryEmployeeWithoutUnit =>
      'Collaborateur sans Unité opérationnelle : la remise ne peut pas être enregistrée.';

  @override
  String get deliveryQrOtherEpi => 'Le code scanné appartient à un autre EPI.';

  @override
  String get stockUnitRequiredToMove =>
      'Sélectionnez une Unité pour déplacer le stock.';

  @override
  String get stockAttentionSectionTitle => 'Stock';

  @override
  String get stockAttentionCompanyTitle =>
      'Plage d\'attention — valeur par défaut de l\'entreprise';

  @override
  String get stockAttentionCompanyHelp =>
      'S\'applique aux Unités qui n\'ont pas défini leur propre pourcentage. Ne modifie aucune Unité déjà configurée.';

  @override
  String get stockAttentionPercentageLabel =>
      'Pourcentage de la plage d\'attention';

  @override
  String get stockAttentionOriginLabel => 'Origine';

  @override
  String get stockAttentionOriginCompany => 'Défini par l\'entreprise';

  @override
  String get stockAttentionOriginSystem => 'Valeur par défaut du système';

  @override
  String get stockAttentionSave => 'Enregistrer la valeur de l\'entreprise';

  @override
  String get stockAttentionRestore => 'Rétablir la valeur du système';

  @override
  String get stockAttentionSaved =>
      'Valeur par défaut de l\'entreprise enregistrée.';

  @override
  String get stockAttentionRestored =>
      'Valeur de l\'entreprise supprimée. L\'entreprise revient à la valeur du système.';

  @override
  String stockAttentionSystemDefaultHint(int value) {
    return 'Valeur du système : $value %';
  }

  @override
  String get stockConfigTitle => 'Configuration du stock';

  @override
  String get stockConfigIntro =>
      'Définissez le stock minimum, la plage d’attention et la surveillance d’alerte d’un EPI dans une Unité. Chaque paramètre est enregistré séparément.';

  @override
  String get stockConfigUnitLabel => 'Unité à configurer';

  @override
  String get stockConfigSelectUnit =>
      'Sélectionnez l’Unité pour configurer ses paramètres.';

  @override
  String get stockConfigSelectEpi =>
      'Sélectionnez l’EPI pour voir et modifier les paramètres de cette Unité.';

  @override
  String get stockConfigEpiLabel => 'EPI';

  @override
  String get stockConfigEpisLoadError =>
      'Impossible de charger la liste des EPI de cette Unité.';

  @override
  String get stockConfigNoEpisInUnit =>
      'Aucun EPI n’est visible dans cette Unité.';

  @override
  String get stockConfigUnitBalance => 'Solde dans l’Unité';

  @override
  String get stockConfigAttentionLimit => 'Limite de la plage d’attention';

  @override
  String get stockConfigUnderlyingStatus => 'État physique';

  @override
  String get stockConfigDerivedUnavailable =>
      'Les valeurs calculées n’ont pas pu être actualisées maintenant. Les paramètres enregistrés ci-dessus sont corrects.';

  @override
  String get stockConfigStatusCritical => 'Critique';

  @override
  String get stockConfigStatusNearMinimum => 'Proche du minimum';

  @override
  String get stockConfigStatusNormal => 'Normal';

  @override
  String get stockConfigStatusDisabled => 'Alerte désactivée';

  @override
  String get stockConfigMinimumTitle => 'Stock minimum';

  @override
  String get stockConfigMinimumHelp =>
      'Quantité en dessous de laquelle l’EPI est considéré comme critique dans cette Unité. Ne vaut que pour cette Unité.';

  @override
  String get stockConfigMinimumLabel => 'Stock minimum';

  @override
  String get stockConfigMinimumNegativeError =>
      'Saisissez un nombre entier supérieur ou égal à zéro.';

  @override
  String get stockConfigMinimumSaved =>
      'Stock minimum enregistré pour cette Unité.';

  @override
  String get stockConfigMinimumRestored =>
      'Stock minimum rétabli. L’Unité hérite de nouveau de la valeur de l’entreprise.';

  @override
  String get stockConfigAttentionTitle => 'Plage d’attention';

  @override
  String get stockConfigAttentionHelp =>
      'Pourcentage au-dessus du minimum à partir duquel l’EPI entre déjà en attention dans cette Unité. Indépendant du stock minimum.';

  @override
  String get stockConfigAttentionRangeError =>
      'Le pourcentage doit être compris entre 0 et 100.';

  @override
  String get stockConfigAttentionSaved =>
      'Plage d’attention enregistrée pour cette Unité.';

  @override
  String get stockConfigAttentionRestored =>
      'Plage d’attention rétablie. L’Unité hérite de nouveau de la valeur de l’entreprise.';

  @override
  String get stockConfigAlertTitle => 'Surveillance d’alerte';

  @override
  String get stockConfigAlertHelp =>
      'La désactiver interrompt l’alerte de stock bas et le réapprovisionnement automatique de cet EPI dans cette Unité. Elle ne modifie ni le solde, ni le minimum, ni le pourcentage.';

  @override
  String get stockConfigAlertToggle => 'Surveiller le stock de cet EPI';

  @override
  String get stockConfigAlertPending =>
      'Modification en attente. Cliquez sur Enregistrer pour l’appliquer.';

  @override
  String get stockConfigAlertDisableTitle => 'Désactiver l’alerte ?';

  @override
  String get stockConfigAlertDisableBody =>
      'Cet EPI cessera de générer des alertes de stock bas et du réapprovisionnement automatique dans cette Unité. L’état physique restera affiché.';

  @override
  String get stockConfigAlertDisableConfirm => 'Désactiver';

  @override
  String get stockConfigAlertSaved =>
      'Surveillance d’alerte enregistrée pour cette Unité.';

  @override
  String get stockConfigAlertRestored =>
      'Surveillance rétablie. L’Unité revient à la valeur du système.';

  @override
  String get stockConfigOriginUnit => 'Défini par cette Unité';

  @override
  String get stockConfigOriginCompany => 'Hérité de la valeur de l’entreprise';

  @override
  String get stockConfigOriginUnknown => 'Non renseignée';

  @override
  String get stockConfigSave => 'Enregistrer';

  @override
  String get stockConfigRestore => 'Rétablir l’héritage';

  @override
  String stockAttentionRangeError(int max) {
    return 'Saisissez un pourcentage entier entre 0 et $max.';
  }

  @override
  String get stockAttentionLoadError =>
      'Impossible de charger la valeur par défaut de l\'entreprise.';

  @override
  String get unitSelectorLabel => 'Unité';

  @override
  String get unitSelectorAllUnits => 'Toutes les Unités';

  @override
  String get unitSelectorLockedHint =>
      'Votre profil opère dans une Unité fixe.';

  @override
  String get unitSelectorLoadError => 'Impossible de charger les Unités.';

  @override
  String get unitSelectorNoUnitsAssigned =>
      'Aucune Unité ne vous est attribuée. Contactez l\'administrateur.';

  @override
  String get unitSelectorCompanyHasNoUnits =>
      'L\'entreprise n\'a encore aucune Unité enregistrée.';

  @override
  String get settingsSectionCompany => 'Entreprise';

  @override
  String get settingsSectionOperation => 'Exploitation';

  @override
  String get settingsSectionSubscription => 'Abonnement';

  @override
  String get settingsCompanyLabel => 'Entreprise';

  @override
  String settingsCompanyScopeBanner(String name) {
    return 'Entreprise administrée : $name';
  }

  @override
  String get settingsSelectCompanyFirst =>
      'Sélectionnez une entreprise dans Paramètres pour continuer.';

  @override
  String get settingsFichaTileTitle => 'Fiche d\'EPI';

  @override
  String get settingsFichaTileSubtitle =>
      'Titre, déclaration, observations et traçabilité';

  @override
  String get settingsStockTileSubtitle =>
      'Seuil d\'alerte par défaut de l\'entreprise';

  @override
  String get settingsModulesTileSubtitle =>
      'Modules visibles par profil et par Unité';

  @override
  String get settingsArchivalTitle => 'Archivage et conservation';

  @override
  String get settingsArchivalSubtitle =>
      'Années de conservation des enregistrements archivés';

  @override
  String get settingsAppearanceTitle => 'Apparence et langue';

  @override
  String get settingsAppearanceSubtitle =>
      'Thème de l\'interface et langue de l\'application';

  @override
  String get settingsSubscriptionTileTitle => 'Mon abonnement';

  @override
  String get settingsSubscriptionTileSubtitle =>
      'Formule, facturation et résiliation';

  @override
  String get settingsInvoicesTileTitle => 'Historique financier';

  @override
  String get settingsInvoicesTileSubtitle =>
      'Toutes les factures et tous les reçus';

  @override
  String get settingsNoPermission =>
      'Vous n\'avez pas l\'autorisation de modifier ce paramètre.';

  @override
  String get stockPhysicalValidityUnknown => 'Expiration physique inconnue';

  @override
  String get stockNoPhysicalStock => 'Aucun stock physique';

  @override
  String get stockRegularizeValidityTitle => 'Régulariser la validité physique';

  @override
  String get stockRegularizeValiditySubtitle =>
      'Identifiez la pièce et indiquez la validité justifiée. Le classement est effectué par le système.';

  @override
  String get stockRegularizeQrLabel => 'QR ou code de la pièce';

  @override
  String get stockRegularizeExpiryLabel => 'Validité physique justifiée';

  @override
  String get stockRegularizeExpirySelect => 'Sélectionner une date';

  @override
  String get stockRegularizeEvidenceLabel =>
      'Preuve (document ou enregistrement vérifiable)';

  @override
  String get stockRegularizeJustificationLabel => 'Justification';

  @override
  String get stockRegularizeSubmit => 'Régulariser';

  @override
  String get stockRegularizeIncomplete =>
      'Renseignez la pièce, la validité, la preuve et la justification.';

  @override
  String get stockRegularizeResultEligible =>
      'Validité régularisée. La pièce est éligible à la remise et à la réservation.';

  @override
  String get stockRegularizeResultBlocked =>
      'Validité régularisée. La pièce est expirée et reste bloquée pour la remise.';

  @override
  String get stockRegularizeResultDone => 'Validité régularisée.';

  @override
  String stockComplianceEpiCount(String label, int count) {
    return '$label — EPI distincts : $count';
  }

  @override
  String stockPhysicalPieceCounts(
    int valid,
    int expiring,
    int expired,
    int unknown,
  ) {
    return 'Pièces physiques : valides $valid, proches $expiring, expirées $expired, inconnues $unknown.';
  }

  @override
  String get deliveryPhysicalItemIneligible =>
      'Pièce indisponible pour remise. Vérifiez expiration physique, état, réservations et solde.';

  @override
  String get safetyTitle => 'Bibliothèque de sécurité';

  @override
  String get safetyApproved => 'EPI approuvés';

  @override
  String get safetyRetry => 'Réessayer';

  @override
  String get safetyClose => 'Fermer';

  @override
  String get safetyCancel => 'Annuler';

  @override
  String get safetyConfirm => 'Confirmer';

  @override
  String get safetyAccess => 'Accéder';

  @override
  String get safetyPortalConfirm => 'Confirmer l’accès au portail';

  @override
  String get safetyCpfLast => 'Trois derniers chiffres du CPF';

  @override
  String get safetyView => 'Consulter';

  @override
  String get safetyFit => 'Ajuster';

  @override
  String get safetyZoomIn => 'Agrandir';

  @override
  String get safetyZoomOut => 'Réduire';

  @override
  String get safetyNextPage => 'Page suivante';

  @override
  String get safetyPreviousPage => 'Page précédente';

  @override
  String get safetyDocument => 'Document';

  @override
  String get safetyDetails => 'Détails';

  @override
  String get safetyRelatedDocuments => 'Documents associés';

  @override
  String get safetyRelatedEpis => 'EPI associés';

  @override
  String get safetyRelatedEpi => 'EPI associé';

  @override
  String get safetyAllEpis => 'Tous les EPI';

  @override
  String get safetyAllCategories => 'Toutes les catégories';

  @override
  String get safetyNoDocs => 'Aucun document publié pour ce contexte.';

  @override
  String get safetyNoRecords =>
      'Aucun enregistrement publié et autorisé dans ce contexte.';

  @override
  String get safetyCatalogueNotice =>
      'L’approbation du catalogue ne garantit pas la disponibilité physique. La validité du CA est distincte de celle du lot.';

  @override
  String get safetyName => 'EPI';

  @override
  String get safetyManufacturer => 'Fabricant';

  @override
  String get safetyModel => 'Modèle/référence';

  @override
  String get safetyCa => 'CA';

  @override
  String get safetyCaExpiry => 'Validité du CA';

  @override
  String get safetyUsefulLife => 'Durée de vie (mois)';

  @override
  String get safetyProtection => 'Protection';

  @override
  String get safetySection => 'Section';

  @override
  String get safetyRecommendations => 'Recommandations/restrictions';

  @override
  String get safetyUnknown => 'Non renseigné';

  @override
  String get safetySearch => 'Rechercher';

  @override
  String get safetyViewEpi => 'Voir l’EPI';

  @override
  String get safetyHistory => 'Historique';

  @override
  String get safetyDocumentHistory => 'Historique du document';

  @override
  String get safetyPublish => 'Publier';

  @override
  String get safetyPublishVersion => 'Publier la version';

  @override
  String get safetyArchive => 'Archiver le document';

  @override
  String get safetyArchiveVersions => 'Archiver le document et ses versions';

  @override
  String get safetyReason => 'Justification obligatoire';

  @override
  String get safetyNew => 'Nouveau document';

  @override
  String get safetyCreateNew => 'Créer un document';

  @override
  String get safetyMetadata => 'Informations de version';

  @override
  String get safetyEmptyAdmin => 'Aucun document enregistré.';

  @override
  String get safetyPrivateNotice =>
      'Originaux privés, versions et historique conservés. Gestion réservée aux administrateurs général et de registre.';

  @override
  String get safetyAllowAdminDownloads =>
      'Autoriser le téléchargement des originaux aux administrateurs habilités';

  @override
  String get safetyPreviewOnlyNotice =>
      'Les collaborateurs accèdent uniquement à l’aperçu.';

  @override
  String get safetyPolicyReason =>
      'Modifier la politique de téléchargement administratif';

  @override
  String get safetySearchVersions => 'Rechercher un titre ou une version';

  @override
  String get safetyChooseFile => 'Choisir un fichier';

  @override
  String get safetyFilePickerLabel => 'Documents de sécurité';

  @override
  String get safetyUnitRequired => 'Sélectionnez au moins une unité';

  @override
  String get safetyAllUnits => 'Toutes les unités de l’entreprise';

  @override
  String get safetyRequired => 'Obligatoire';

  @override
  String get safetyDocumentTitle => 'Titre';

  @override
  String get safetyVersion => 'Version';

  @override
  String get safetyEffectiveDate => 'Entrée en vigueur (AAAA-MM-JJ)';

  @override
  String get safetySectors => 'Secteurs séparés par des virgules (vide = tous)';

  @override
  String get safetyActivities =>
      'Activités/fonctions séparées par des virgules (vide = toutes)';

  @override
  String get safetyUpload => 'Enregistrer ou versionner un document';

  @override
  String get safetyRendering => 'Création de l’aperçu sécurisé…';

  @override
  String get safetyFileLimit => 'Sélectionnez un fichier de 20 Mio maximum.';

  @override
  String safetyVersionDate(String version, String date) {
    return 'Version $version · Entrée en vigueur $date';
  }

  @override
  String safetyUnit(String unit) {
    return 'Unité de consultation : $unit';
  }

  @override
  String safetyPreviewError(String error) {
    return 'Aperçu indisponible : $error';
  }

  @override
  String safetyUploadError(String error) {
    return 'Enregistrement refusé ; aperçu indisponible : $error';
  }

  @override
  String safetyVersionSummary(
    String version,
    String revision,
    String state,
    String date,
  ) {
    return 'Version $version / révision $revision · $state · Entrée en vigueur $date';
  }

  @override
  String safetyActorDetails(String actor, String details) {
    return 'Responsable $actor\n$details';
  }

  @override
  String get safetyCategoryEpi => 'Matrice d’application des EPI';

  @override
  String get safetyCategoryGlove => 'Matrice de sélection des gants';

  @override
  String get safetyCategoryCare => 'Guides de nettoyage et d’entretien';

  @override
  String get safetyCategoryUse => 'Instructions d’utilisation des EPI';

  @override
  String get safetyCategoryTechnical => 'Manuels et fiches techniques';

  @override
  String get safetyCategoryOther => 'Autres documents de sécurité';

  @override
  String get safetyStateDraft => 'Brouillon';

  @override
  String get safetyStatePublished => 'Publié';

  @override
  String get safetyStateSuperseded => 'Remplacé';

  @override
  String get safetyStateArchived => 'Archivé';

  @override
  String get prConfTitle => 'Conférence de Réception';

  @override
  String get prConfIntro =>
      'Cochez chaque article selon la réception réelle. Indiquez la validité physique du fabricant et la preuve vérifiable ; utilisez « Séparer en lots » pour des validités différentes ou des exceptions individuelles. Les pièces sans validité prouvée entrent BLOQUÉES.';

  @override
  String get prConfReceivedYes => 'Reçu';

  @override
  String get prConfReceivedNo => 'Non reçu';

  @override
  String get prConfEvidence => 'Preuve vérifiable';

  @override
  String get prConfEvidenceHint => 'Étiquette / facture / photo';

  @override
  String get prConfEvidenceRequired =>
      'La preuve vérifiable est obligatoire lorsqu\'une validité est saisie.';

  @override
  String get prConfSplitLots => 'Séparer en lots';

  @override
  String get prConfSingleDate => 'Utiliser une date unique';

  @override
  String get prConfAddLot => 'Ajouter un lot';

  @override
  String get prConfAddException => 'Exception (1 pièce)';

  @override
  String get prConfLotQty => 'Qté';

  @override
  String get prConfLotCode => 'Identification';

  @override
  String get prConfRemoveLot => 'Retirer le lot';

  @override
  String get prConfPreview => 'Aperçu — validité physique par pièce';

  @override
  String get prConfBlocked => 'SANS validité → BLOQUÉES';

  @override
  String get prConfExpired => 'expirée';

  @override
  String get prConfPiece => 'pièce(s)';

  @override
  String get prConfSumMismatch =>
      'La somme des quantités des lots ne correspond pas à la quantité reçue.';

  @override
  String get prConfLotQtyPositive =>
      'Chaque lot doit avoir une quantité supérieure à zéro.';

  @override
  String get prConfNotes => 'Observations sur les articles non reçus';

  @override
  String get prConfNotesRequired =>
      'Indiquez les observations sur les articles non reçus.';

  @override
  String get prConfSubmit => 'Enregistrer la Conférence';

  @override
  String get prConfDone => 'Conférence enregistrée.';

  @override
  String get prConfEmpty => 'Aucun article éligible à la conférence.';

  @override
  String get prConfInvalidQuantity =>
      'La quantité effectivement reçue est invalide ou non positive. Corrigez la réception avant de confirmer.';

  @override
  String get prConfNoPersistedPieces =>
      'Aucune pièce enregistrée ou réponse incohérente. L’entrée en stock n’a pas été confirmée.';

  @override
  String prConfDoneQuantity(int count) {
    return '$count pièces effectivement enregistrées en stock.';
  }

  @override
  String get prConfNoStockEntry =>
      'Vérification enregistrée sans entrée de pièces en stock.';

  @override
  String prConfInvalidQuantityLine(int line, String item, String id) {
    return 'Ligne $line — $item (article #$id) : quantité effectivement reçue invalide ou non positive. Corrigez la réception avant de confirmer.';
  }

  @override
  String operationalAlertStockNearMinimum(String epi) {
    return 'Stock proche du minimum : $epi';
  }

  @override
  String operationalAlertStockNegative(String epi) {
    return 'Solde de stock négatif : $epi';
  }

  @override
  String operationalAlertStockZero(String epi) {
    return 'Rupture de stock : $epi';
  }

  @override
  String operationalAlertStockBelowMinimum(String epi) {
    return 'Stock inférieur au minimum : $epi';
  }

  @override
  String operationalAlertStockAtMinimum(String epi) {
    return 'Stock au seuil minimum : $epi';
  }

  @override
  String operationalAlertStockDescription(
    String company,
    String unit,
    String stock,
    String measure,
    String minimum,
  ) {
    return '$company / $unit - solde actuel de $stock $measure, minimum $minimum.';
  }

  @override
  String operationalAlertCaTitle(String epi) {
    return 'CA brésilien proche de son expiration : $epi';
  }

  @override
  String operationalAlertCaDescription(String company, String date) {
    return '$company - expire le $date.';
  }

  @override
  String operationalAlertManufacturerExpiredTitle(String epi) {
    return 'Date de validité du fabricant dépassée : $epi';
  }

  @override
  String operationalAlertManufacturerExpiringTitle(String epi) {
    return 'Date de validité du fabricant proche : $epi';
  }

  @override
  String operationalAlertManufacturerExpiredDescription(
    String company,
    String date,
    String stock,
    String measure,
  ) {
    return '$company - validité du fabricant expirée le $date. Retirer du stock ($stock $measure) : un EPI périmé ne peut pas être remis au salarié.';
  }

  @override
  String operationalAlertManufacturerExpiringDescription(
    String company,
    String date,
    String daysLabel,
    String stock,
    String measure,
  ) {
    return '$company - validité du fabricant jusqu’au $date (dans $daysLabel). Donner la priorité à la remise de ce lot ($stock $measure en stock) avant expiration (PEPS).';
  }

  @override
  String get operationalAlertSizes => 'Tailles en stock :';

  @override
  String operationalAlertSizeGlove(String value) {
    return 'Gant : $value';
  }

  @override
  String operationalAlertSizeSize(String value) {
    return 'Taille : $value';
  }

  @override
  String operationalAlertSizeUniform(String value) {
    return 'Tenue : $value';
  }

  @override
  String get operationalAlertSizeUnspecified => 'Taille non précisée';

  @override
  String operationalAlertQuantity(String count) {
    return '$count';
  }

  @override
  String operationalAlertMeasureUnit(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'unités',
      one: 'unité',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertMeasurePair(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'paires',
      one: 'paire',
    );
    return '$_temp0';
  }

  @override
  String operationalAlertDays(num count, String countLabel) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countLabel jours',
      one: '$countLabel jour',
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
      other: '$epi : $countLabel pièces physiques.',
      one: '$epi : $countLabel pièce physique.',
    );
    return '$_temp0';
  }

  @override
  String get operationalAlertPhysicalUnknownTitle =>
      'Date de validité physique inconnue';

  @override
  String get operationalAlertPhysicalExpiringTitle =>
      'Lots proches de l’expiration';

  @override
  String get passwordChangeTitle => 'Définissez un nouveau mot de passe';

  @override
  String get passwordChangeIntro =>
      'Votre mot de passe est temporaire. Par sécurité, définissez un nouveau mot de passe pour continuer.';

  @override
  String get passwordChangeCurrent => 'Mot de passe actuel (temporaire)';

  @override
  String get passwordChangeNew => 'Nouveau mot de passe';

  @override
  String get passwordChangeConfirm => 'Confirmer le nouveau mot de passe';

  @override
  String get passwordChangeSave => 'Enregistrer le nouveau mot de passe';

  @override
  String get passwordChangeLogout => 'Se déconnecter';

  @override
  String get passwordChangeCurrentRequired =>
      'Saisissez votre mot de passe actuel';

  @override
  String get passwordChangeMinLength =>
      'Le nouveau mot de passe doit comporter au moins 6 caractères';

  @override
  String get passwordChangeMustDiffer =>
      'Le nouveau mot de passe doit être différent du mot de passe temporaire';

  @override
  String get passwordChangeMismatch => 'Les mots de passe ne correspondent pas';

  @override
  String get passwordChangeFailed => 'Impossible de modifier le mot de passe';

  @override
  String get poSupplierConfirmed => 'Confirmé';

  @override
  String get poSupplierDeliveryUpdated => 'Livraison mise à jour';

  @override
  String get poSupplierRejected => 'Refusé';

  @override
  String get poSupplierIsoDateHint => 'AAAA-MM-JJ';
}
