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

  /// Fonte ÚNICA de conformidade de estoque (item 2): a mesma base do Dashboard
  /// e da tela "Validade e Bloqueios". Retorna `summary` (contagens por
  /// categoria: ca_expired, ca_expiring, product_expired, product_expiring,
  /// missing_manufacture, missing_lot, admin_blocked) e `categories` (registros
  /// para o deep-link). A REGRA é do backend — o cliente só consome o contrato.
  /// GET /api/stock/compliance.
  Future<Map<String, dynamic>> getStockCompliance({
    required int actorUserId,
    int? companyId,
    int? unitId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/compliance',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (companyId != null) 'company_id': companyId,
        if (unitId != null) 'unit_id': unitId,
      },
    );
    return res.data ?? {};
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
