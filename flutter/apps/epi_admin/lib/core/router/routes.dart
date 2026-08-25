abstract final class Routes {
  static const login       = '/login';
  static const changePassword = '/change-password';
  static const dashboard   = '/';
  static const employees   = '/employees';
  static const employeeDetail = '/employees/:id';
  static const epiDetail      = '/epis/:id';
  static const epis        = '/epis';
  static const stock       = '/stock';
  /// Configuração de estoque por Unidade + EPI (#271-B2-a). Subrota de
  /// `/stock` de propósito: herda o módulo estrutural `estoque` por
  /// `startsWith` em `requiredModuleFor`. A PERMISSÃO, essa não pode ser
  /// herdada — ver `route_permissions.dart`.
  static const stockConfig = '/stock/config';
  static const deliveries  = '/deliveries';
  static const deliveryNew = '/deliveries/new';
  static const handover    = '/deliveries/handover';
  static const returns     = '/returns';
  static const records     = '/records';
  static const purchases   = '/purchases';
  static const reports     = '/reports';
  static const settings    = '/settings';
  /// Subrotas de Configurações. São subrotas de `/settings` de
  /// propósito: `requiredPermissionFor` e `requiredModuleFor` casam por
  /// `startsWith` e já as cobrem com `settings:view` + módulo `configuracoes`
  /// — o mesmo piso do hub, que é o correto aqui (diferente de
  /// `/stock/config`, que precisa de um gate MAIS estrito que `/stock`).
  /// Cada subtela ainda faz a sua própria checagem: a URL direta não passa
  /// pelo hub.
  static const settingsAppearance = '/settings/appearance';
  static const settingsFicha      = '/settings/ficha';
  static const settingsStock      = '/settings/stock';
  static const settingsModules    = '/settings/modules';
  static const settingsArchival   = '/settings/archival';
  static const myCompany   = '/my-company';
  static const subscription = '/subscription';
  static const invoices    = '/invoices';
  static const companies   = '/companies';
  static const users       = '/users';
  static const units       = '/units';
  static const legalEntities = '/legal-entities';
  static const outsourcedCompanies = '/outsourced-companies';
  static const portal      = '/portal';
  static const qr          = '/qr';
  static const feedback     = '/feedback';

  /// Todas as rotas declaradas. Usado pelo teste que confere se o menu
  /// aponta apenas para rotas existentes.
  static const all = <String>[
    login,
    changePassword,
    dashboard,
    employees,
    employeeDetail,
    epiDetail,
    epis,
    stock,
    stockConfig,
    deliveries,
    deliveryNew,
    handover,
    returns,
    records,
    purchases,
    reports,
    settings,
    settingsAppearance,
    settingsFicha,
    settingsStock,
    settingsModules,
    settingsArchival,
    myCompany,
    subscription,
    invoices,
    companies,
    users,
    units,
    legalEntities,
    outsourcedCompanies,
    portal,
    qr,
    feedback,
  ];
}
