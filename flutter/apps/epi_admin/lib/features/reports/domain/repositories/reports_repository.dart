import 'package:epi_api/epi_api.dart';

/// Contrato de dados de Relatórios (domain). O Cubit depende desta abstração,
/// não do ApiClient — permite teste com repositório fake e troca de fonte.
abstract class ReportsRepository {
  Future<ReportData> getReports({String? startDate, String? endDate});
  Future<List<ReportRequest>> getReportRequests();
  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes,
  });
}
