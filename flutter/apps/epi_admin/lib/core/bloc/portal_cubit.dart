import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── Status ─────────────────────────────────────────────────────────────────

enum PortalStatus { initial, loading, loaded, signing, error }

// ── State ──────────────────────────────────────────────────────────────────

class PortalState extends Equatable {
  const PortalState({
    this.status = PortalStatus.initial,
    this.token,
    this.access,
    this.error,
    this.isSaving = false,
    this.signSuccess = false,
  });

  final PortalStatus status;
  final String? token;
  final PortalAccess? access;
  final String? error;
  final bool isSaving;
  final bool signSuccess;

  bool get isLoaded => status == PortalStatus.loaded;
  bool get isInitial => status == PortalStatus.initial;

  PortalState _copyWith({
    PortalStatus? status,
    String? token,
    PortalAccess? access,
    String? error,
    bool? isSaving,
    bool? signSuccess,
    bool clearError = false,
  }) =>
      PortalState(
        status: status ?? this.status,
        token: token ?? this.token,
        access: access ?? this.access,
        error: clearError ? null : (error ?? this.error),
        isSaving: isSaving ?? this.isSaving,
        signSuccess: signSuccess ?? this.signSuccess,
      );

  @override
  List<Object?> get props =>
      [status, token, access, error, isSaving, signSuccess];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class PortalCubit extends Cubit<PortalState> {
  PortalCubit() : super(const PortalState());

  Future<void> lookupByCpf(String cpf) async {
    if (cpf.trim().isEmpty) return;
    emit(state._copyWith(status: PortalStatus.loading, clearError: true));
    try {
      final token = await ApiClient.portal.lookupEmployee(cpf: cpf.trim());
      await _loadAccess(token);
    } on Exception catch (e) {
      emit(state._copyWith(
        status: PortalStatus.error,
        error: e.toString(),
      ));
    }
  }

  Future<void> loadFromToken(String token) async {
    emit(state._copyWith(status: PortalStatus.loading, clearError: true));
    await _loadAccess(token);
  }

  Future<void> _loadAccess(String token) async {
    try {
      final access = await ApiClient.portal.getAccess(token: token);
      emit(state._copyWith(
        status: PortalStatus.loaded,
        token: token,
        access: access,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(
        status: PortalStatus.error,
        error: e.toString(),
      ));
    }
  }

  Future<void> signDelivery(int deliveryId, String signatureData) async {
    final token = state.token;
    if (token == null) return;
    emit(state._copyWith(isSaving: true, clearError: true, signSuccess: false));
    try {
      await ApiClient.portal.signDelivery(
        token: token,
        deliveryId: deliveryId,
        signatureData: signatureData,
      );
      await _loadAccess(token);
      emit(state._copyWith(isSaving: false, signSuccess: true));
    } on Exception catch (e) {
      emit(state._copyWith(isSaving: false, error: e.toString()));
    }
  }

  Future<void> signBatch(List<int> deliveryIds, String signatureData) async {
    final token = state.token;
    if (token == null) return;
    emit(state._copyWith(isSaving: true, clearError: true, signSuccess: false));
    try {
      await ApiClient.portal.signBatch(
        token: token,
        deliveryIds: deliveryIds,
        signatureData: signatureData,
      );
      await _loadAccess(token);
      emit(state._copyWith(isSaving: false, signSuccess: true));
    } on Exception catch (e) {
      emit(state._copyWith(isSaving: false, error: e.toString()));
    }
  }

  void clearSignSuccess() => emit(state._copyWith(signSuccess: false));

  void reset() => emit(const PortalState());
}
