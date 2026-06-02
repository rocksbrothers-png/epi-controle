import 'package:dio/dio.dart';
import '../models/portal_models.dart';

class PortalApi {
  const PortalApi(this._dio);
  final Dio _dio;

  Future<String> lookupEmployee({required String cpf}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employee-lookup',
      data: {'cpf': cpf},
    );
    return res.data?['token'] as String? ?? '';
  }

  Future<PortalAccess> getAccess({required String token}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employee-access',
      queryParameters: {'token': token},
    );
    return PortalAccess.fromJson(res.data ?? {});
  }

  Future<void> signDelivery({
    required String token,
    required int deliveryId,
    required String signatureData,
  }) async {
    await _dio.post<void>(
      '/api/employee-sign',
      data: {
        'token': token,
        'delivery_id': deliveryId,
        'signature_data': signatureData,
      },
    );
  }

  Future<void> signBatch({
    required String token,
    required List<int> deliveryIds,
    required String signatureData,
  }) async {
    await _dio.post<void>(
      '/api/employee-sign-batch',
      data: {
        'token': token,
        'delivery_ids': deliveryIds,
        'signature_data': signatureData,
      },
    );
  }

  Future<void> sendFeedback({
    required String token,
    required int deliveryId,
    required String comment,
    int rating = 5,
  }) async {
    await _dio.post<void>(
      '/api/employee-feedback',
      data: {
        'token': token,
        'delivery_id': deliveryId,
        'comment': comment,
        'rating': rating,
      },
    );
  }
}
