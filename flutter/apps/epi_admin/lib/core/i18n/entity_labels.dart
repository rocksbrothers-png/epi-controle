import 'generated/app_localizations.dart';

/// Display labels never change the canonical role or unit-type codes.
String appRoleLabel(String role, AppLocalizations l) => switch (role) {
  'master_admin' => l.roleMasterAdmin,
  'general_admin' => l.roleGeneralAdmin,
  'registry_admin' => l.roleRegistryAdmin,
  'admin' => l.roleLocalAdmin,
  'user' => l.rolePpeManager,
  'employee' => l.roleEmployee,
  'buyer' => l.roleBuyer,
  'approver' => l.roleApprover,
  'certification_readonly' => l.roleCertificationReadOnly,
  _ => role,
};

String appUnitTypeLabel(String type, AppLocalizations l) => switch (type) {
  'base' => l.unitTypeBase,
  'embarcacao' => l.unitTypeVessel,
  'plataforma' => l.unitTypePlatform,
  _ => type,
};

String appModuleLabel(String module, AppLocalizations l) => switch (module) {
  'dashboard' => l.navDashboard,
  'compras' => l.navPurchases,
  'estoque' => l.navStock,
  'entregas' => l.navDeliveries,
  'solicitacoes' => l.moduleRequests,
  'fichas' => l.navRecords,
  'relatorios' => l.navReports,
  'administracao' => l.moduleAdministration,
  'configuracoes' => l.navSettings,
  'terceirizados' => l.navTerceirizados,
  'terceirizados_colaboradores' => l.moduleEmployeeRegistration,
  _ => module,
};

String appReturnConditionLabel(String condition, AppLocalizations l) =>
    switch (condition) {
      'good' => l.returnConditionGood,
      'damaged' => l.returnConditionDamaged,
      'lost' => l.returnConditionLost,
      _ => condition,
    };

String appCompanyKindLabel(String kind, AppLocalizations l) => switch (kind) {
  'outsourced' => l.outsourcedCompanyKindOutsourced,
  'service_provider' => l.outsourcedCompanyKindServiceProvider,
  'other_contracted' => l.outsourcedCompanyKindOther,
  _ => kind,
};

/// Portuguese strings here are existing persisted values, never translated
/// payloads. Unknown tenant-provided values remain intact.
String appResponsibilityLabel(String value, AppLocalizations l) =>
    switch (value) {
      'Empresa Contratante' => l.responsibilityContracting,
      'Empresa Terceirizada' => l.responsibilityOutsourced,
      'Empresa Prestadora de Serviço' => l.responsibilityProvider,
      'Responsabilidade Compartilhada' => l.responsibilityShared,
      'Conforme Contrato' => l.responsibilityContract,
      'Não Definido' => l.responsibilityUndefined,
      _ => value,
    };
