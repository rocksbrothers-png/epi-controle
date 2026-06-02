import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class ReportsState extends Equatable {
  const ReportsState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.data,
    this.requests = const [],
    this.startDate,
    this.endDate,
    this.successMessage,
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  final ReportData? data;
  final List<ReportRequest> requests;
  final String? startDate;
  final String? endDate;
  final String? successMessage;

  ReportsState _copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    ReportData? data,
    List<ReportRequest>? requests,
    String? startDate,
    String? endDate,
    String? successMessage,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      ReportsState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        data: data ?? this.data,
        requests: requests ?? this.requests,
        startDate: startDate ?? this.startDate,
        endDate: endDate ?? this.endDate,
        successMessage:
            clearSuccess ? null : (successMessage ?? this.successMessage),
      );

  @override
  List<Object?> get props => [
        isLoading,
        isSubmitting,
        error,
        data,
        requests,
        startDate,
        endDate,
        successMessage,
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class ReportsCubit extends Cubit<ReportsState> {
  ReportsCubit() : super(const ReportsState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final data = await ApiClient.reports.getReports(
        startDate: state.startDate,
        endDate: state.endDate,
      );
      final requests = await ApiClient.reports.getReportRequests();
      emit(state._copyWith(
        isLoading: false,
        data: data,
        requests: requests,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void setDateRange(String? start, String? end) {
    emit(state._copyWith(startDate: start, endDate: end));
  }

  Future<void> requestReport({
    int? unitId,
    int? year,
    int? month,
    String notes = '',
  }) async {
    emit(state._copyWith(isSubmitting: true, clearError: true));
    try {
      await ApiClient.reports.createReportRequest(
        unitId: unitId,
        periodYear: year,
        periodMonth: month,
        notes: notes,
      );
      final requests = await ApiClient.reports.getReportRequests();
      emit(state._copyWith(
        isSubmitting: false,
        requests: requests,
        successMessage: 'Solicitação enviada com sucesso.',
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isSubmitting: false, error: e.toString()));
    }
  }
}
