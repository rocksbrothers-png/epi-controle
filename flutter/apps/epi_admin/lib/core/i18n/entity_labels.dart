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
