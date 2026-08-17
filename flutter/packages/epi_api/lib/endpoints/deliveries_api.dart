import 'package:dio/dio.dart';
import '../models/delivery.dart';

/// Cliente HTTP manual para endpoints de entregas.
class DeliveriesApi {
  const DeliveriesApi(this._dio);
  final Dio _dio;

  Future<List<Delivery>> getDeliveries({int? limit}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/deliveries',
      queryParameters: limit != null ? {'limit': limit} : null,
    );
    final raw = res.data;
    final list =
        (raw?['data'] ?? raw?['deliveries'] ?? raw ?? []) as List;
    return list
        .cast<Map<String, dynamic>>()
        .map(Delivery.fromJson)
        .toList();
  }

  Future<int> createDelivery({
    required int companyId,
    required int employeeId,
    required int epiId,
    required int quantity,
    required String sector,
    required String roleName,
    required String deliveryDate,
    required String nextReplacementDate,
    required int stockItemId,
    required String stockQrCode,
    /// Identifica a **tentativa de entrega**, não a requisição HTTP: o reenvio
    /// da fila offline repete a mesma chave, e o backend devolve a entrega
    /// original em vez de recusar o item já entregue.
    String idempotencyKey = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/deliveries',
      data: {
        if (idempotencyKey.isNotEmpty) 'idempotency_key': idempotencyKey,
        'company_id': companyId,
        'employee_id': employeeId,
        'epi_id': epiId,
        'quantity': quantity,
        'sector': sector,
        'role_name': roleName,
        'delivery_date': deliveryDate,
        'next_replacement_date': nextReplacementDate,
        'stock_item_id': stockItemId,
        'stock_qr_code': stockQrCode,
      },
    );
    return (res.data?['id'] ?? 0) as int;
  }

  /// Item 4 — projeção SEGURA da entrega a partir do token opaco (QR da
  /// entrega). Não expõe dado pessoal direto; a REGRA (multi-tenant, projeção)
  /// é do backend. GET /api/deliveries/handover-lookup?code=…
  Future<Map<String, dynamic>> handoverLookup({
    required int actorUserId,
    required String code,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/deliveries/handover-lookup',
      queryParameters: {'actor_user_id': actorUserId, 'code': code},
    );
    return (res.data?['handover'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  /// Item 4 — confirma o recebimento pelo QR da entrega e fecha o ciclo no
  /// portal. IDEMPOTENTE no backend (não duplica entrega). Devolve o resultado
  /// bruto (`confirmed`, `already_confirmed`, `confirmed_at`).
  /// POST /api/deliveries/handover-confirm
  Future<Map<String, dynamic>> handoverConfirm({
    required int actorUserId,
    required String code,
    String signatureName = '',
    String signatureData = '',
    String signatureComment = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/deliveries/handover-confirm',
      data: {
        'actor_user_id': actorUserId,
        'code': code,
        if (signatureName.isNotEmpty) 'signature_name': signatureName,
        if (signatureData.isNotEmpty) 'signature_data': signatureData,
        if (signatureComment.isNotEmpty) 'signature_comment': signatureComment,
      },
    );
    return res.data ?? {};
  }
}
