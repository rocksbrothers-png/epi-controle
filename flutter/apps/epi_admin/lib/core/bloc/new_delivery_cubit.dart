import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../sync/offline_queue.dart';
import '../../features/deliveries/data/datasources/deliveries_remote_datasource.dart';
import '../../features/deliveries/data/repository_impl/deliveries_repository_impl.dart';
import '../../features/deliveries/domain/repositories/deliveries_repository.dart';

enum DeliveryStep { employee, epi, details, signature }

// ── State ──────────────────────────────────────────────────────────────────

class NewDeliveryState extends Equatable {
  const NewDeliveryState({
    this.step = DeliveryStep.employee,
    this.selectedEmployee,
    this.selectedEpi,
    this.quantity = 1,
    this.deliveryDate,
    this.nextReplacementDate,
    this.sector,
    this.roleName,
    this.isSubmitting = false,
    this.error,
    this.successId,
    this.offlineQueued = false,
  });

  final DeliveryStep step;
  final Employee? selectedEmployee;
  final Epi? selectedEpi;
  final int quantity;
  final String? deliveryDate;
  final String? nextReplacementDate;
  final String? sector;
  final String? roleName;
  final bool isSubmitting;
  final String? error;
  final int? successId;
  final bool offlineQueued;

  bool get canProceedFromEmployee => selectedEmployee != null;
  bool get canProceedFromEpi => selectedEpi != null;
  bool get canProceedFromDetails =>
      quantity > 0 &&
      deliveryDate != null &&
      nextReplacementDate != null &&
      (sector?.isNotEmpty ?? false) &&
      (roleName?.isNotEmpty ?? false);

  NewDeliveryState copyWith({
    DeliveryStep? step,
    Employee? selectedEmployee,
    Epi? selectedEpi,
    int? quantity,
    String? deliveryDate,
    String? nextReplacementDate,
    String? sector,
    String? roleName,
    bool? isSubmitting,
    String? error,
    int? successId,
    bool? offlineQueued,
    bool clearError = false,
  }) =>
      NewDeliveryState(
        step: step ?? this.step,
        selectedEmployee: selectedEmployee ?? this.selectedEmployee,
        selectedEpi: selectedEpi ?? this.selectedEpi,
        quantity: quantity ?? this.quantity,
        deliveryDate: deliveryDate ?? this.deliveryDate,
        nextReplacementDate: nextReplacementDate ?? this.nextReplacementDate,
        sector: sector ?? this.sector,
        roleName: roleName ?? this.roleName,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        successId: successId ?? this.successId,
        offlineQueued: offlineQueued ?? this.offlineQueued,
      );

  @override
  List<Object?> get props => [
        step,
        selectedEmployee,
        selectedEpi,
        quantity,
        deliveryDate,
        nextReplacementDate,
        sector,
        roleName,
        isSubmitting,
        error,
        successId,
        offlineQueued,
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class NewDeliveryCubit extends Cubit<NewDeliveryState> {
  NewDeliveryCubit({
    DeliveriesRepository? repository,
    OfflineQueue? offlineQueue,
  })  : _repository = repository ??
            const DeliveriesRepositoryImpl(ApiDeliveriesRemoteDataSource()),
        _offlineQueue = offlineQueue ?? const SyncDatabaseQueue(),
        super(const NewDeliveryState());

  final DeliveriesRepository _repository;
  final OfflineQueue _offlineQueue;

  void selectEmployee(Employee employee) {
    emit(state.copyWith(
      selectedEmployee: employee,
      sector: employee.sector,
      roleName: employee.role,
      step: DeliveryStep.epi,
    ));
  }

  void selectEpi(Epi epi) {
    emit(state.copyWith(selectedEpi: epi, step: DeliveryStep.details));
  }

  void setDetails({
    int? quantity,
    String? deliveryDate,
    String? nextReplacementDate,
    String? sector,
    String? roleName,
  }) {
    emit(state.copyWith(
      quantity: quantity,
      deliveryDate: deliveryDate,
      nextReplacementDate: nextReplacementDate,
      sector: sector,
      roleName: roleName,
    ));
  }

  void goToSignature() {
    emit(state.copyWith(step: DeliveryStep.signature));
  }

  void goBack() {
    final prev = switch (state.step) {
      DeliveryStep.epi => DeliveryStep.employee,
      DeliveryStep.details => DeliveryStep.epi,
      DeliveryStep.signature => DeliveryStep.details,
      DeliveryStep.employee => DeliveryStep.employee,
    };
    emit(state.copyWith(step: prev));
  }

  Future<bool> submit({
    required int companyId,
    required String signatureData,
  }) async {
    final s = state;
    if (s.selectedEmployee == null || s.selectedEpi == null) return false;

    emit(state.copyWith(isSubmitting: true, clearError: true));
    final sector    = s.sector ?? s.selectedEmployee!.sector ?? '';
    final roleName  = s.roleName ?? s.selectedEmployee!.role ?? '';
    final qrCode    = s.selectedEpi!.code ?? s.selectedEpi!.id.toString();
    final Map<String, dynamic> payload = {
      'company_id': companyId,
      'employee_id': s.selectedEmployee!.id,
      'epi_id': s.selectedEpi!.id,
      'quantity': s.quantity,
      'sector': sector,
      'role_name': roleName,
      'delivery_date': s.deliveryDate!,
      'next_replacement_date': s.nextReplacementDate!,
      'stock_item_id': s.selectedEpi!.id,
      'stock_qr_code': qrCode,
    };
    try {
      final id = await _repository.createDelivery(
        companyId: companyId,
        employeeId: s.selectedEmployee!.id,
        epiId: s.selectedEpi!.id,
        quantity: s.quantity,
        sector: sector,
        roleName: roleName,
        deliveryDate: s.deliveryDate!,
        nextReplacementDate: s.nextReplacementDate!,
        stockItemId: s.selectedEpi!.id,
        stockQrCode: qrCode,
      );
      emit(state.copyWith(isSubmitting: false, successId: id));
      return true;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        await _offlineQueue.enqueue(
          opType: 'delivery_create',
          payload: payload,
        );
        emit(state.copyWith(isSubmitting: false, offlineQueued: true));
        return true;
      }
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }
}
