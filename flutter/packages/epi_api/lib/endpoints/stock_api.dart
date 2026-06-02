import 'package:dio/dio.dart';

class StockApi {
  const StockApi(this._dio);
  final Dio _dio;

  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType, // 'in' or 'out'
    required int quantity,
  }) async {
    await _dio.post<void>(
      '/api/stock/movements',
      data: {
        'actor_user_id': actorUserId,
        'company_id': companyId,
        'unit_id': unitId,
        'epi_id': epiId,
        'movement_type': movementType,
        'quantity': quantity,
        'label_measure': '',
        'label_printer_name': '',
        'label_print_format': '',
        'manufacture_date': '',
      },
    );
  }
}
