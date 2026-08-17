import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Testes de contrato dos clientes `epi_api` (Sprint 2 do plano de migração).
///
/// Travam as **chaves de resposta** que cada cliente lê (`items`, `data`,
/// `deliveries`, `employee`, `epi`, ...) e o parsing dos modelos. Esta é a
/// classe de bug que já mordeu duas vezes em produção (Empresas: `items` vs
/// `companies` — #593; Entregas: endpoint inexistente). Um cliente que lê a
/// chave errada devolve **lista vazia silenciosamente** — aqui isso falha o CI.
///
/// Não há servidor real: um [HttpClientAdapter] falso devolve JSON canônico,
/// exercitando o caminho real de extração + desserialização de cada cliente.
class _StubAdapter implements HttpClientAdapter {
  _StubAdapter(this.body, {this.status = 200});
  final Object body;
  final int status;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// Dio que sempre responde [body] (JSON) com [status].
Dio _dioReturning(Object body, {int status = 200}) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test.local'));
  dio.httpClientAdapter = _StubAdapter(body, status: status);
  return dio;
}

void main() {
  group('CompaniesApi', () {
    test('lê a chave de topo `items`', () async {
      final api = CompaniesApi(_dioReturning({
        'items': [
          {'id': 1, 'name': 'Acme', 'license_status': 'active', 'active': true},
        ],
      }));
      final list = await api.getCompanies();
      expect(list, hasLength(1));
      expect(list.first.id, 1);
      expect(list.first.name, 'Acme');
      expect(list.first.isActive, isTrue);
    });

    test('chave errada (`companies`) → lista vazia (guarda do bug #593)', () async {
      final api = CompaniesApi(_dioReturning({
        'companies': [
          {'id': 1, 'name': 'Acme'},
        ],
      }));
      expect(await api.getCompanies(), isEmpty);
    });

    // O backend serializa `active` como inteiro 0/1 (coluna INTEGER). O cast
    // `as bool?` lançava _CastError e travava a tela de Empresas — inclusive o
    // diálogo "Nova empresa", que ficava no spinner após criar a tenant.
    test('parseia `active` como inteiro 0/1 (payload real do backend)', () async {
      final api = CompaniesApi(_dioReturning({
        'items': [
          {
            'id': 2,
            'name': 'DOF Brasil',
            'license_status': 'active',
            'active': 1,
            'plan_name': 'enterprise',
            'user_limit': 500,
            'user_count': 0,
          },
          {'id': 3, 'name': 'Inativa', 'license_status': 'active', 'active': 0},
        ],
      }));
      final list = await api.getCompanies();
      expect(list, hasLength(2));
      expect(list.first.isActive, isTrue);
      expect(list.first.userLimit, 500);
      expect(list.last.isActive, isFalse);
    });
  });

  group('DeliveriesApi', () {
    test('tolera `deliveries`', () async {
      final api = DeliveriesApi(_dioReturning({
        'deliveries': [
          {'id': 10, 'employee_name': 'João', 'epi_name': 'Capacete', 'quantity': 2},
        ],
      }));
      final list = await api.getDeliveries();
      expect(list, hasLength(1));
      expect(list.first.id, 10);
      expect(list.first.employeeName, 'João');
      expect(list.first.epiName, 'Capacete');
    });

    test('tolera `data`', () async {
      final api = DeliveriesApi(_dioReturning({
        'data': [
          {'id': 11, 'employee_name': 'Maria', 'epi_name': 'Luva', 'quantity': 1},
        ],
      }));
      final list = await api.getDeliveries();
      expect(list, hasLength(1));
      expect(list.first.id, 11);
    });
  });

  group('DevolutionsApi', () {
    test('getDevolutions lê `items`', () async {
      final api = DevolutionsApi(_dioReturning({
        'items': [
          {'id': 5, 'delivery_id': 3, 'employee_name': 'Ana', 'epi_name': 'Bota'},
        ],
      }));
      final list = await api.getDevolutions();
      expect(list, hasLength(1));
      expect(list.first.id, 5);
      expect(list.first.deliveryId, 3);
    });

    test('getOpenDeliveries lê `items`', () async {
      final api = DevolutionsApi(_dioReturning({
        'items': [
          {'id': 7, 'employee_id': 2, 'epi_id': 4, 'quantity': 3},
        ],
      }));
      final list = await api.getOpenDeliveries(employeeId: 2, epiId: 4);
      expect(list, hasLength(1));
      expect(list.first.id, 7);
      expect(list.first.quantity, 3);
    });
  });

  group('FeedbackApi.getFeedbacks (tolerante)', () {
    test('lê `items`', () async {
      final api = FeedbackApi(_dioReturning({
        'items': [
          {'id': 1, 'epi_name': 'Capacete', 'status': 'open'},
        ],
      }));
      expect(await api.getFeedbacks(), hasLength(1));
    });

    test('lê `feedbacks`', () async {
      final api = FeedbackApi(_dioReturning({
        'feedbacks': [
          {'id': 2, 'epi': 'Luva', 'status': 'closed'},
        ],
      }));
      final list = await api.getFeedbacks();
      expect(list, hasLength(1));
      expect(list.first.id, 2);
      expect(list.first.epiName, 'Luva');
    });
  });

  group('ReportsApi', () {
    test('getReportRequests lê `items`', () async {
      final api = ReportsApi(_dioReturning({
        'items': [
          {'id': 3, 'status': 'pending'},
        ],
      }));
      final list = await api.getReportRequests();
      expect(list, hasLength(1));
      expect(list.first.id, 3);
    });

    test('getReports parseia o dict de agregações', () async {
      final api = ReportsApi(_dioReturning({
        'total_quantity': 42,
        'by_unit': {'Matriz': 10},
        'deliveries': <dynamic>[],
      }));
      final data = await api.getReports();
      expect(data.totalQuantity, 42);
      expect(data.byUnit['Matriz'], 10);
    });
  });

  group('FichasApi.getFichas', () {
    test('lê `items`', () async {
      final api = FichasApi(_dioReturning({
        'items': [
          {'id': 9, 'employee_name': 'Carlos', 'status': 'open'},
        ],
      }));
      final list = await api.getFichas();
      expect(list, hasLength(1));
      expect(list.first.id, 9);
      expect(list.first.employeeName, 'Carlos');
    });
  });

  group('PurchasesApi', () {
    test('getPurchaseRequests lê `items`', () async {
      final api = PurchasesApi(_dioReturning({
        'items': [
          {'id': 4, 'title': 'Reposição', 'status': 'draft', 'items': <dynamic>[]},
        ],
      }));
      final list = await api.getPurchaseRequests();
      expect(list, hasLength(1));
      expect(list.first.id, 4);
      expect(list.first.title, 'Reposição');
    });

    test('getPurchaseDemands lê `items`', () async {
      final api = PurchasesApi(_dioReturning({
        'items': [
          {'epi_id': 8, 'epi_name': 'Óculos', 'minimum_stock': 5},
        ],
      }));
      final list = await api.getPurchaseDemands();
      expect(list, hasLength(1));
      expect(list.first.epiId, 8);
    });

    test('getPurchaseOrders lê `items`', () async {
      final api = PurchasesApi(_dioReturning({
        'items': [
          {'id': 1, 'status': 'pending_review'},
        ],
      }));
      final list = await api.getPurchaseOrders();
      expect(list, hasLength(1));
      expect(list.first['status'], 'pending_review');
    });

    test('getAuthorizedSuppliers lê `items`', () async {
      final api = PurchasesApi(_dioReturning({
        'items': [
          {'id': 2, 'name': 'Loja EPI', 'integration_level': 'email'},
        ],
      }));
      final list = await api.getAuthorizedSuppliers();
      expect(list, hasLength(1));
      expect(list.first['integration_level'], 'email');
    });

    test('createAuthorizedSupplier lê `item`', () async {
      final api = PurchasesApi(_dioReturning({
        'ok': true,
        'item': {'id': 5, 'name': 'Nova Loja'},
      }));
      final supplier =
          await api.createAuthorizedSupplier({'name': 'Nova Loja'});
      expect(supplier['id'], 5);
    });

    test('getSupplierProducts lê `items`', () async {
      final api = PurchasesApi(_dioReturning({
        'supplier': {'id': 2},
        'items': [
          {'id': 9, 'supplier_sku': 'SKU-1', 'last_price': 12.5},
        ],
      }));
      final list = await api.getSupplierProducts(2);
      expect(list, hasLength(1));
      expect(list.first['supplier_sku'], 'SKU-1');
    });

    test('getQuotesForRequest devolve items + comparison', () async {
      final api = PurchasesApi(_dioReturning({
        'items': [
          {'id': 3, 'status': 'answered', 'supplier_name': 'Loja'},
        ],
        'comparison': {
          'suppliers': [
            {'quote_id': 3, 'total_with_freight': 120.0},
          ],
        },
      }));
      final data = await api.getQuotesForRequest(100);
      expect((data['items'] as List), hasLength(1));
      expect(((data['comparison'] as Map)['suppliers'] as List), hasLength(1));
    });

    test('selectQuote devolve o po_draft', () async {
      final api = PurchasesApi(_dioReturning({
        'ok': true,
        'quote': {'id': 3, 'status': 'selected'},
        'po_draft': {'supplier': 'Loja', 'items': <dynamic>[]},
      }));
      final result = await api.selectQuote(3, {});
      expect((result['po_draft'] as Map)['supplier'], 'Loja');
    });

    test('getPurchaseOrderTracking lê `item`', () async {
      final api = PurchasesApi(_dioReturning({
        'item': {
          'purchase_order_id': 7,
          'sent_channel': 'portal',
          'confirmations': <dynamic>[],
        },
      }));
      final tracking = await api.getPurchaseOrderTracking(7);
      expect(tracking['sent_channel'], 'portal');
    });
  });

  group('EmployeesApi / EpisApi (extração de chave de objeto)', () {
    test('getEmployee lê `employee`', () async {
      final api = EmployeesApi(_dioReturning({
        'employee': {'id': 7, 'full_name': 'Jefferson'},
      }));
      final emp = await api.getEmployee(7, actorUserId: 1);
      expect(emp['id'], 7);
      expect(emp['full_name'], 'Jefferson');
    });

    test('getEpi lê `epi`', () async {
      final api = EpisApi(_dioReturning({
        'epi': {'id': 4, 'name': 'Capacete'},
      }));
      final epi = await api.getEpi(4, actorUserId: 1);
      expect(epi['id'], 4);
      expect(epi['name'], 'Capacete');
    });
  });

  group('PortalApi', () {
    test('lookupEmployee lê `token`', () async {
      final api = PortalApi(_dioReturning({'token': 'abc.def.ghi'}));
      expect(await api.lookupEmployee(cpf: '00000000000'), 'abc.def.ghi');
    });

    test('getAccess parseia PortalAccess', () async {
      final api = PortalApi(_dioReturning({
        'employee_name': 'Lucia',
        'unit_name': 'Base Norte',
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      }));
      final access = await api.getAccess(token: 't');
      expect(access.employeeName, 'Lucia');
      expect(access.unitName, 'Base Norte');
    });
  });

  group('SettingsApi.getFichaConfig', () {
    test('parseia FichaConfig', () async {
      final api = SettingsApi(_dioReturning({
        'titulo': 'Ficha de EPI',
        'rastreabilidade': true,
      }));
      final cfg = await api.getFichaConfig();
      expect(cfg.titulo, 'Ficha de EPI');
      expect(cfg.rastreabilidade, isTrue);
    });
  });

  group('UsersApi (passthrough de res.data)', () {
    test('createUser devolve o corpo da resposta', () async {
      final api = UsersApi(_dioReturning({'id': 99, 'username': 'novo'}));
      final created = await api.createUser({'username': 'novo'});
      expect(created['id'], 99);
      expect(created['username'], 'novo');
    });
  });

  group('Employee.fromJson (payload real do bootstrap)', () {
    // fetch_employees/bootstrap usam employee_id_code, role_name e
    // schedule_type; is_active/photo_url não existem no backend. As chaves
    // curtas antigas (code/role/schedule) deixavam esses campos sempre vazios.
    test('mapeia employee_id_code, role_name e schedule_type', () {
      final employee = Employee.fromJson(const {
        'id': 7,
        'name': 'Maria Souza',
        'employee_id_code': 'EMP-007',
        'sector': 'Operações',
        'role_name': 'Técnica de Segurança',
        'schedule_type': '12x36',
        'unit_name': 'Matriz',
        'admission_date': '2025-03-01',
      });
      expect(employee.code, 'EMP-007');
      expect(employee.role, 'Técnica de Segurança');
      expect(employee.schedule, '12x36');
      expect(employee.unitName, 'Matriz');
      expect(employee.isActive, isTrue); // backend não envia flag — assume ativo
    });

    test('prioriza current_unit_name e aceita active como 0/1', () {
      final employee = Employee.fromJson(const {
        'id': 8,
        'name': 'João Lima',
        'unit_name': 'Matriz',
        'current_unit_name': 'Base Norte',
        'active': 0,
      });
      expect(employee.unitName, 'Base Norte');
      expect(employee.isActive, isFalse);
    });

    test('mapeia tipo_vinculo e empresa_origem', () {
      final employee = Employee.fromJson(const {
        'id': 9,
        'name': 'Ana Paula',
        'tipo_vinculo': 'Estagiário',
        'empresa_origem': 'Instituto XYZ',
      });
      expect(employee.employmentType, 'Estagiário');
      expect(employee.sourceCompany, 'Instituto XYZ');
    });

    test('tipo_vinculo e empresa_origem ausentes ficam nulos', () {
      final employee = Employee.fromJson(const {'id': 10, 'name': 'Carlos'});
      expect(employee.employmentType, isNull);
      expect(employee.sourceCompany, isNull);
    });
  });
}
