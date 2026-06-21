import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/reports_cubit.dart';
import 'package:epi_admin/features/reports/domain/repositories/reports_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 7 — valida a migração do módulo reports para Cubit→Repository com um
/// repositório fake (sem ApiClient estático).
class _FakeReportsRepository implements ReportsRepository {
  _FakeReportsRepository({this.data, this.requests = const [], this.throwOnLoad = false});

  ReportData? data;
  List<ReportRequest> requests;
  bool throwOnLoad;
  Object? throwOnCreate;
  final List<String> calls = [];

  @override
  Future<ReportData> getReports({String? startDate, String? endDate}) async {
    calls.add('getReports:$startDate:$endDate');
    if (throwOnLoad) throw Exception('load failed');
    return data ??
        const ReportData(
          totalQuantity: 0,
          byUnit: {},
          bySector: {},
          byEpi: {},
          deliveries: [],
        );
  }

  @override
  Future<List<ReportRequest>> getReportRequests() async {
    calls.add('getRequests');
    return requests;
  }

  @override
  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes = '',
  }) async {
    calls.add('create:$unitId:$periodYear:$periodMonth');
    if (throwOnCreate != null) throw throwOnCreate!;
  }
}

ReportRequest _req(int id) => ReportRequest(
      id: id,
      status: 'pending',
      requesterName: 'Ana',
      createdAt: '2026-01-01',
    );

void main() {
  group('ReportsCubit (arquitetura Repository)', () {
    test('load() popula data e requests', () async {
      final repo = _FakeReportsRepository(
        data: const ReportData(
          totalQuantity: 42,
          byUnit: {'Matriz': 42},
          bySector: {},
          byEpi: {},
          deliveries: [],
        ),
        requests: [_req(1), _req(2)],
      );
      final cubit = ReportsCubit(repository: repo);

      await cubit.load();

      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.error, isNull);
      expect(cubit.state.data?.totalQuantity, 42);
      expect(cubit.state.requests.map((r) => r.id), [1, 2]);
    });

    test('load() captura erro', () async {
      final cubit = ReportsCubit(repository: _FakeReportsRepository(throwOnLoad: true));
      await cubit.load();
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isLoading, isFalse);
    });

    test('setDateRange() propaga as datas para getReports', () async {
      final repo = _FakeReportsRepository();
      final cubit = ReportsCubit(repository: repo);

      cubit.setDateRange('2026-01-01', '2026-01-31');
      expect(cubit.state.startDate, '2026-01-01');
      await cubit.load();

      expect(repo.calls, contains('getReports:2026-01-01:2026-01-31'));
    });

    test('requestReport() cria, recarrega requests e seta successMessage', () async {
      final repo = _FakeReportsRepository(requests: [_req(9)]);
      final cubit = ReportsCubit(repository: repo);

      await cubit.requestReport(unitId: 3, year: 2026, month: 2, notes: 'x');

      expect(repo.calls.first, 'create:3:2026:2');
      expect(repo.calls.last, 'getRequests');
      expect(cubit.state.isSubmitting, isFalse);
      expect(cubit.state.successMessage, isNotNull);
      expect(cubit.state.requests.map((r) => r.id), [9]);
    });

    test('requestReport() captura erro e limpa isSubmitting', () async {
      final repo = _FakeReportsRepository()..throwOnCreate = Exception('falhou');
      final cubit = ReportsCubit(repository: repo);

      await cubit.requestReport(unitId: 1);

      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isSubmitting, isFalse);
    });
  });
}
