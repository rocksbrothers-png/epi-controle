import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/features/employees/domain/repositories/employees_repository.dart';
import 'package:epi_admin/features/employees/presentation/cubits/employees_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 3 — valida a nova arquitetura do módulo employees
/// (Cubit → UseCase → Repository) com um repositório fake. Possível justamente
/// porque o EmployeesCubit aceita injeção de [EmployeesRepository], deixando de
/// depender do ApiClient estático — o objetivo da migração arquitetural.
class _FakeEmployeesRepository implements EmployeesRepository {
  _FakeEmployeesRepository({this.employees = const [], this.throwOnFetch = false});

  List<Employee> employees;
  bool throwOnFetch;
  Object? throwOnWrite;
  final List<String> calls = [];

  @override
  Future<List<Employee>> fetchEmployees() async {
    calls.add('fetch');
    if (throwOnFetch) throw Exception('fetch failed');
    return employees;
  }

  @override
  Future<Map<String, dynamic>> fetchEmployee(int id) async {
    calls.add('get:$id');
    return const {};
  }

  @override
  Future<void> createEmployee(Map<String, dynamic> body) async {
    calls.add('create');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<void> updateEmployee(int id, Map<String, dynamic> body) async {
    calls.add('update:$id');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<void> deleteEmployee(int id) async {
    calls.add('delete:$id');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<void> archiveEmployee(int id, {String reason = ''}) async {
    calls.add('archive:$id');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<void> restoreEmployee(int id) async {
    calls.add('restore:$id');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<List<Map<String, dynamic>>> fetchArchivedEmployees() async {
    calls.add('archived');
    return const [];
  }
}

DioException _dioError(Object? data) => DioException(
      requestOptions: RequestOptions(path: '/api/employees'),
      response: Response(
        requestOptions: RequestOptions(path: '/api/employees'),
        data: data,
      ),
    );

void main() {
  group('EmployeesCubit (arquitetura Repository)', () {
    test('load() popula a lista pelo repositório', () async {
      final repo = _FakeEmployeesRepository(employees: const [
        Employee(id: 1, name: 'Ana'),
        Employee(id: 2, name: 'Bruno', sector: 'TI'),
      ]);
      final cubit = EmployeesCubit(repository: repo);

      await cubit.load();

      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.error, isNull);
      expect(cubit.state.employees.map((e) => e.id), [1, 2]);
      expect(repo.calls, ['fetch', 'archived']);
    });

    test('load() captura erro em estado de erro', () async {
      final cubit = EmployeesCubit(repository: _FakeEmployeesRepository(throwOnFetch: true));
      await cubit.load();
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.employees, isEmpty);
    });

    test('search() filtra por nome/setor sem nova chamada ao repositório', () async {
      final repo = _FakeEmployeesRepository(employees: const [
        Employee(id: 1, name: 'Ana', sector: 'RH'),
        Employee(id: 2, name: 'Bruno', sector: 'TI'),
      ]);
      final cubit = EmployeesCubit(repository: repo);
      await cubit.load();

      cubit.search('bru');
      expect(cubit.state.filtered.map((e) => e.id), [2]);

      cubit.search('rh');
      expect(cubit.state.filtered.map((e) => e.id), [1]);

      cubit.search('');
      expect(cubit.state.filtered.length, 2);
      expect(repo.calls, ['fetch', 'archived']); // search não recarrega
    });

    test('createEmployee() chama o repositório e recarrega', () async {
      final repo = _FakeEmployeesRepository(employees: const [Employee(id: 1, name: 'Ana')]);
      final cubit = EmployeesCubit(repository: repo);

      await cubit.createEmployee({'name': 'Novo'});

      expect(repo.calls, ['create', 'fetch', 'archived']);
      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.error, isNull);
    });

    test('updateEmployee()/archiveEmployee()/restoreEmployee() passam o id e recarregam', () async {
      final repo = _FakeEmployeesRepository(employees: const [Employee(id: 1, name: 'Ana')]);
      final cubit = EmployeesCubit(repository: repo);

      await cubit.updateEmployee(7, {'name': 'X'});
      expect(repo.calls, ['update:7', 'fetch', 'archived']);

      repo.calls.clear();
      await cubit.archiveEmployee(9, reason: 'Desligamento');
      expect(repo.calls, ['archive:9', 'fetch', 'archived']);

      repo.calls.clear();
      await cubit.restoreEmployee(9);
      expect(repo.calls, ['restore:9', 'fetch', 'archived']);
    });

    test('erro de escrita mapeia mensagem do envelope DioException', () async {
      final repo = _FakeEmployeesRepository()
        ..throwOnWrite = _dioError({'error': {'message': 'Nome obrigatório'}});
      final cubit = EmployeesCubit(repository: repo);

      await cubit.createEmployee({});

      expect(cubit.state.error, 'Nome obrigatório');
      expect(cubit.state.isLoading, isFalse);
    });
  });
}
