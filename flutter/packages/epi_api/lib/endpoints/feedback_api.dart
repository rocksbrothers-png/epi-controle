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

  // ── Pipeline avançado (HSEQ / admin / avaliação técnica) ───────────────────

  Future<void> hseqReview({required int feedbackId, required String hseqOpinion}) async {
    await _dio.post<void>('/api/feedbacks/hseq-review',
        data: {'feedback_id': feedbackId, 'hseq_opinion': hseqOpinion});
  }

  Future<void> adminDecision({
    required int feedbackId,
    required String decision,
    required String justification,
  }) async {
    await _dio.post<void>('/api/feedbacks/admin-decision', data: {
      'feedback_id': feedbackId,
      'decision': decision,
      'justification': justification,
    });
  }

  Future<void> setReassessment({required int feedbackId, required String period}) async {
    await _dio.post<void>('/api/avaliacoes/set-reassessment',
        data: {'feedback_id': feedbackId, 'period': period});
  }

  Future<void> acceptSuggestion({required int feedbackId}) async {
    await _dio.post<void>('/api/avaliacoes/accept-suggestion',
        data: {'feedback_id': feedbackId});
  }

  Future<void> preEvaluate({required int feedbackId, Map<String, dynamic>? extra}) async {
    await _dio.post<void>('/api/avaliacoes/pre-evaluate',
        data: {'feedback_id': feedbackId, ...?extra});
  }

  Future<void> adminEvaluate({
    required int feedbackId,
    required String techDecision,
    Map<String, dynamic>? extra,
  }) async {
    await _dio.post<void>('/api/avaliacoes/admin-evaluate',
        data: {'feedback_id': feedbackId, 'tech_decision': techDecision, ...?extra});
  }

  Future<void> computeStatus() async {
    await _dio.post<void>('/api/avaliacoes/compute-status', data: const {});
  }
}
