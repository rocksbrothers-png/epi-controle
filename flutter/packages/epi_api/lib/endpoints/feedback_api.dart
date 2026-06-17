import 'package:dio/dio.dart';
import '../models/feedback.dart';

class FeedbackApi {
  const FeedbackApi(this._dio);
  final Dio _dio;

  Future<List<FeedbackItem>> getFeedbacks({String? status}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/feedbacks',
      queryParameters: status != null ? {'status': status} : null,
    );
    final raw = res.data;
    final list =
        (raw?['items'] ?? raw?['data'] ?? raw?['feedbacks'] ?? <dynamic>[])
            as List;
    return list
        .cast<Map<String, dynamic>>()
        .map(FeedbackItem.fromJson)
        .toList();
  }

  Future<void> triage({
    required int feedbackId,
    required String action,
    String? notes,
  }) async {
    await _dio.post<void>('/api/feedbacks/triage', data: {
      'feedback_id': feedbackId,
      'action': action,
      if (notes != null) 'notes': notes,
    });
  }

  Future<void> managerValidate({
    required int feedbackId,
    String? notes,
  }) async {
    await _dio.post<void>('/api/feedbacks/manager-validate', data: {
      'feedback_id': feedbackId,
      if (notes != null) 'notes': notes,
    });
  }

  Future<void> close({
    required int feedbackId,
    String? notes,
  }) async {
    await _dio.post<void>('/api/feedbacks/close', data: {
      'feedback_id': feedbackId,
      if (notes != null) 'notes': notes,
    });
  }

  Future<void> forwardAdmin({
    required int feedbackId,
    String? notes,
  }) async {
    await _dio.post<void>('/api/feedbacks/forward-admin', data: {
      'feedback_id': feedbackId,
      if (notes != null) 'notes': notes,
    });
  }

  Future<void> managerReject({
    required int feedbackId,
    required String rejectionReason,
  }) async {
    await _dio.post<void>('/api/feedbacks/manager-reject', data: {
      'feedback_id': feedbackId,
      'rejection_reason': rejectionReason,
    });
  }
}
