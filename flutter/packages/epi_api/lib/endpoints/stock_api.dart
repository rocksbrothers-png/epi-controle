import 'package:dio/dio.dart';

class StockApi {
  const StockApi(this._dio);
  final Dio _dio;

  /// Lê uma data a partir de uma imagem (OCR), reaproveitado para capturar a
  /// validade do fabricante na conferência de recebimento. Recebe a imagem como
  /// data URL ou base64 e retorna 'YYYY-MM-DD' (ou '' se não identificada).
  Future<String> detectDateFromImage({
    required int actorUserId,
    required String imageData,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/stock/manufacture-date-ocr',
      data: {'actor_user_id': actorUserId, 'image_data': imageData},
    );
    return (res.data?['manufacture_date'] as String?)?.trim() ?? '';
  }

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
