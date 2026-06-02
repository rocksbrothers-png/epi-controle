import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

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
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class NewDeliveryCubit extends Cubit<NewDeliveryState> {
  NewDeliveryCubit() : super(const NewDeliveryState());

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
    try {
      final id = await ApiClient.deliveries.createDelivery(
        companyId: companyId,
        employeeId: s.selectedEmployee!.id,
        epiId: s.selectedEpi!.id,
        quantity: s.quantity,
        sector: s.sector ?? s.selectedEmployee!.sector ?? '',
        roleName: s.roleName ?? s.selectedEmployee!.role ?? '',
        deliveryDate: s.deliveryDate!,
        nextReplacementDate: s.nextReplacementDate!,
        stockItemId: s.selectedEpi!.id,
        stockQrCode: s.selectedEpi!.code ?? s.selectedEpi!.id.toString(),
      );
      emit(state.copyWith(isSubmitting: false, successId: id));
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }
}
