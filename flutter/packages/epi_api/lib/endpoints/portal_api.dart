import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../models/portal_models.dart';
import '../models/contact_launch_result.dart';

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

  Future<ContactLaunchResult> contactLaunch({
    required int actorUserId,
    required int employeeId,
    required String channel,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employee-contact-launch',
      data: {
        'actor_user_id': actorUserId,
        'employee_id': employeeId,
        'channel': channel,
      },
    );
    return ContactLaunchResult.fromJson(res.data ?? {});
  }

  Future<Uint8List> downloadFichaPdf({
    required int actorUserId,
    required int employeeId,
  }) async {
    // Step 1: call contactLaunch with channel='whatsapp' to obtain access_link.
    final launch = await contactLaunch(
      actorUserId: actorUserId,
      employeeId: employeeId,
      channel: 'whatsapp',
    );

    // Step 2: extract the 'employee_token' query param from the access_link URL.
    final uri = Uri.tryParse(launch.accessLink);
    final token = uri?.queryParameters['employee_token'] ?? '';

    // Step 3: download PDF bytes.
    final res = await _dio.get<List<int>>(
      '/api/employee-access/pdf',
      queryParameters: {'token': token},
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(res.data ?? []);
  }
}
