import 'package:dio/dio.dart';
import '../models/subscription.dart';

/// Cliente dos endpoints autenticados de assinatura (`/api/subscriptions/*`).
///
/// O ator/empresa são resolvidos no backend a partir do Bearer token (anexado
/// pelo interceptor do Dio). Toda a lógica financeira vive no backend.
class SubscriptionsApi {
  const SubscriptionsApi(this._dio);
  final Dio _dio;

  /// Assinatura vigente da empresa do usuário autenticado (ou null).
  Future<Subscription?> getCurrent() async {
    final res =
        await _dio.get<Map<String, dynamic>>('/api/subscriptions/current');
    final data = res.data?['subscription'];
    if (data == null) return null;
    return Subscription.fromJson(data as Map<String, dynamic>);
  }

  /// Histórico de cobranças (PR 6).
  Future<List<Invoice>> listInvoices({
    String? status,
    String? method,
    int limit = 50,
    int offset = 0,
  }) async {
    final params = <String, String>{
      'limit': limit.toString(),
      'offset': offset.toString(),
    };
    if (status != null) params['status'] = status;
    if (method != null) params['method'] = method;
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/subscriptions/invoices',
      queryParameters: params,
    );
    final items = (res.data?['invoices'] as List?) ?? const [];
    return items
        .map((e) => Invoice.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Cancela a assinatura vigente. Acesso permanece até o fim do período pago.
  Future<Subscription?> cancel({String reason = ''}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/subscriptions/cancel',
      data: {'reason': reason},
    );
    final data = res.data?['subscription'];
    if (data == null) return null;
    return Subscription.fromJson(data as Map<String, dynamic>);
  }
}
