import 'package:dio/dio.dart';
import '../models/report_data.dart';

class ReportsApi {
  const ReportsApi(this._dio);
  final Dio _dio;

  Future<ReportData> getReports({
    String? startDate,
    String? endDate,
    int? employeeId,
    int? epiId,
    int? unitId,
  }) async {
    final params = <String, String>{};
    if (startDate != null) params['start_date'] = startDate;
    if (endDate != null) params['end_date'] = endDate;
    if (employeeId != null) params['employee_id'] = employeeId.toString();
    if (epiId != null) params['epi_id'] = epiId.toString();
    if (unitId != null) params['unit_id'] = unitId.toString();
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/reports',
      queryParameters: params.isEmpty ? null : params,
    );
    return ReportData.fromJson(res.data ?? {});
  }

  Future<List<ReportRequest>> getReportRequests() async {
    final res =
        await _dio.get<Map<String, dynamic>>('/api/report-requests');
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => ReportRequest.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> createReportRequest({
    int? unitId,
    int? periodYear,
    int? periodMonth,
    String notes = '',
  }) async {
    await _dio.post<void>(
      '/api/report-requests',
      data: {
        if (unitId != null) 'unit_id': unitId,
        if (periodYear != null) 'period_year': periodYear,
        if (periodMonth != null) 'period_month': periodMonth,
        if (notes.isNotEmpty) 'notes': notes,
      },
    );
  }
}
