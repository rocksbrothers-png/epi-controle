import 'package:epi_api/epi_api.dart';

import '../../../../core/api/api_client.dart';

abstract class ReportsRemoteDataSource {
  Future<ReportData> getReports({String? startDate, String? endDate});
  Future<List<ReportRequest>> getReportRequests();
  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes,
  });
}

/// Implementação sobre o `epi_api` (REST do backend Python).
class ApiReportsRemoteDataSource implements ReportsRemoteDataSource {
  const ApiReportsRemoteDataSource();

  @override
  Future<ReportData> getReports({String? startDate, String? endDate}) =>
      ApiClient.reports.getReports(startDate: startDate, endDate: endDate);

  @override
  Future<List<ReportRequest>> getReportRequests() =>
      ApiClient.reports.getReportRequests();

  @override
  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes = '',
  }) =>
      ApiClient.reports.createReportRequest(
        unitId: unitId,
        periodYear: periodYear,
        periodMonth: periodMonth,
        notes: notes,
      );
}
