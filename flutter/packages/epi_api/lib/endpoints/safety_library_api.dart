import 'dart:typed_data';
import 'package:dio/dio.dart';

/// Originals are absent from employee contracts. Each page revalidates context.
class SafetyLibraryApi {
  const SafetyLibraryApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> request(
    String action, {
    Map<String, dynamic> data = const {},
    String? token,
    String? cpfLast3,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/${token == null ? 'safety' : 'employee'}-library/$action',
      data: {
        ...data,
        if (token != null) 'token': token,
        if (token != null) 'cpf_last3': cpfLast3,
      },
      options: Options(receiveTimeout: const Duration(seconds: 110)),
    );
    return res.data ?? {};
  }

  Future<Uint8List> page({
    required Map<String, dynamic> data,
    String? token,
    String? cpfLast3,
    String action = 'page',
  }) async {
    final res = await _dio.post<List<int>>(
      '/api/${token == null ? 'safety' : 'employee'}-library/$action',
      data: {
        ...data,
        if (token != null) 'token': token,
        if (token != null) 'cpf_last3': cpfLast3,
      },
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(res.data ?? []);
  }
}
