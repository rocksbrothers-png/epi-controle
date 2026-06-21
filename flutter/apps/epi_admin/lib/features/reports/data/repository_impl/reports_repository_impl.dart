import 'package:epi_api/epi_api.dart';

import '../../domain/repositories/reports_repository.dart';
import '../datasources/reports_remote_datasource.dart';

class ReportsRepositoryImpl implements ReportsRepository {
  const ReportsRepositoryImpl(this._remoteDataSource);

  final ReportsRemoteDataSource _remoteDataSource;

  @override
  Future<ReportData> getReports({String? startDate, String? endDate}) =>
      _remoteDataSource.getReports(startDate: startDate, endDate: endDate);

  @override
  Future<List<ReportRequest>> getReportRequests() =>
      _remoteDataSource.getReportRequests();

  @override
  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes = '',
  }) =>
      _remoteDataSource.createReportRequest(
        unitId: unitId,
        periodYear: periodYear,
        periodMonth: periodMonth,
        notes: notes,
      );
}
