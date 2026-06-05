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
  String get employeeSectorLabel => 'Département';

  @override
  String get employeeRoleLabel => 'Poste';

  @override
  String get employeeUnitLabel => 'Unité';

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
  String get episSearchHint =>
      'Rechercher par nom, numéro d\'approbation ou code';

  @override
  String get epiNameLabel => 'Nom de l\'EPI';

  @override
  String get epiCodeLabel => 'Code d\'achat';

  @override
  String get epiCaLabel => 'N° d\'approbation';

  @override
  String get epiCaExpiryLabel => 'Expiration approbation';

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
}
