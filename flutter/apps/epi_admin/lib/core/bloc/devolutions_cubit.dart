import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';
import '../database/sync_database.dart';

// ── State ──────────────────────────────────────────────────────────────────

class DevolutionsState extends Equatable {
  const DevolutionsState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.successMessage,
    this.offlineQueued = false,
    this.devolutions = const [],
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  /// Empty string '' is a sentinel meaning "use l10n.returnSuccess".
  final String? successMessage;
  final bool offlineQueued;
  final List<Devolution> devolutions;

  DevolutionsState _copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    String? successMessage,
    bool? offlineQueued,
    List<Devolution>? devolutions,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      DevolutionsState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        successMessage:
            clearSuccess ? null : (successMessage ?? this.successMessage),
        offlineQueued: offlineQueued ?? this.offlineQueued,
        devolutions: devolutions ?? this.devolutions,
      );

  @override
  List<Object?> get props =>
      [isLoading, isSubmitting, error, successMessage, offlineQueued, devolutions];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class DevolutionsCubit extends Cubit<DevolutionsState> {
  DevolutionsCubit() : super(const DevolutionsState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final items = await ApiClient.devolutions.getDevolutions();
      emit(state._copyWith(isLoading: false, devolutions: items));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<List<OpenDelivery>> fetchOpenDeliveries({
    required int employeeId,
    required int epiId,
  }) async {
    try {
      return await ApiClient.devolutions.getOpenDeliveries(
        employeeId: employeeId,
        epiId: epiId,
      );
    } on Exception {
      return [];
    }
  }

  Future<bool> createDevolution({
    required int deliveryId,
    required String returnedDate,
    required String condition,
    required String destination,
    required String signatureData,
    String? notes,
  }) async {
    emit(state._copyWith(isSubmitting: true, clearError: true));
    try {
      await ApiClient.devolutions.createDevolution(
        deliveryId: deliveryId,
        returnedDate: returnedDate,
        condition: condition,
        destination: destination,
        signatureData: signatureData,
        notes: notes,
      );
      // Empty string sentinel — UI maps to l10n.returnSuccess.
      emit(state._copyWith(isSubmitting: false, successMessage: ''));
      return true;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        await SyncDatabase.enqueue(
          opType: 'devolution_create',
          payload: {
            'delivery_id': deliveryId,
            'returned_date': returnedDate,
            'condition': condition,
            'destination': destination,
            'signature_data': signatureData,
            'notes': notes,
          },
        );
        emit(state._copyWith(isSubmitting: false, offlineQueued: true));
        return true;
      }
      emit(state._copyWith(isSubmitting: false, error: e.toString()));
      return false;
    } on Exception catch (e) {
      emit(state._copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  void clearMessages() {
    emit(state._copyWith(clearError: true, clearSuccess: true));
  }
}
