abstract final class Routes {
  static const login       = '/login';
  static const dashboard   = '/';
  static const employees   = '/employees';
  static const employeeDetail = '/employees/:id';
  static const epiDetail      = '/epis/:id';
  static const epis        = '/epis';
  static const stock       = '/stock';
  static const deliveries  = '/deliveries';
  static const deliveryNew = '/deliveries/new';
  static const returns     = '/returns';
  static const records     = '/records';
  static const purchases   = '/purchases';
  static const reports     = '/reports';
  static const settings    = '/settings';
  static const myCompany   = '/my-company';
  static const subscription = '/subscription';
  static const invoices    = '/invoices';
  static const companies   = '/companies';
  static const users       = '/users';
  static const units       = '/units';
  static const legalEntities = '/legal-entities';
  static const portal      = '/portal';
  static const qr          = '/qr';
  static const feedback     = '/feedback';

  /// Todas as rotas declaradas. Usado pelo teste que confere se o menu
  /// aponta apenas para rotas existentes.
  static const all = <String>[
    login,
    dashboard,
    employees,
    employeeDetail,
    epiDetail,
    epis,
    stock,
    deliveries,
    deliveryNew,
    returns,
    records,
    purchases,
    reports,
    settings,
    myCompany,
    subscription,
    invoices,
    companies,
    users,
    units,
    legalEntities,
    portal,
    qr,
    feedback,
  ];
}
