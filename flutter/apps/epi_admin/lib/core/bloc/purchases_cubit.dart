import 'dart:async';

import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class PurchasesState extends Equatable {
  const PurchasesState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.successMessage,
    this.requests = const [],
    this.demands = const [],
    this.purchaseOrders = const [],
    this.statusFilter,
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  final String? successMessage;
  final List<PurchaseRequest> requests;
  final List<PurchaseDemand> demands;
  final List<Map<String, dynamic>> purchaseOrders;
  final String? statusFilter;

  List<PurchaseRequest> get filtered {
    if (statusFilter == null || statusFilter!.isEmpty) return requests;
    return requests.where((r) => r.status == statusFilter).toList();
  }

  PurchasesState _copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    String? successMessage,
    List<PurchaseRequest>? requests,
    List<PurchaseDemand>? demands,
    List<Map<String, dynamic>>? purchaseOrders,
    String? statusFilter,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      PurchasesState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        successMessage:
            clearSuccess ? null : (successMessage ?? this.successMessage),
        requests: requests ?? this.requests,
        demands: demands ?? this.demands,
        purchaseOrders: purchaseOrders ?? this.purchaseOrders,
        statusFilter: statusFilter ?? this.statusFilter,
      );

  @override
  List<Object?> get props => [
        isLoading,
        isSubmitting,
        error,
        successMessage,
        requests,
        demands,
        purchaseOrders,
        statusFilter,
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class PurchasesCubit extends Cubit<PurchasesState> {
  PurchasesCubit() : super(const PurchasesState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final reqs = await ApiClient.purchases.getPurchaseRequests();
      emit(state._copyWith(isLoading: false, requests: reqs));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<void> loadWithDemands() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final results = await Future.wait([
        ApiClient.purchases.getPurchaseRequests(),
        ApiClient.purchases.getPurchaseDemands(),
      ]);
      emit(state._copyWith(
        isLoading: false,
        requests: results[0] as List<PurchaseRequest>,
        demands: results[1] as List<PurchaseDemand>,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void filterByStatus(String? status) {
    emit(state._copyWith(statusFilter: status ?? ''));
  }

  Future<bool> createRequest({
    required int unitId,
    required List<PurchaseRequestItem> items,
    required String title,
    String notes = '',
  }) async {
    emit(state._copyWith(isSubmitting: true, clearError: true));
    try {
      await ApiClient.purchases.createPurchaseRequest(
        unitId: unitId,
        items: items.map((i) => i.toJson()).toList(),
        title: title,
        notes: notes,
      );
      emit(state._copyWith(
        isSubmitting: false,
        successMessage: 'Requisição criada com sucesso',
      ));
      unawaited(load());
      return true;
    } on Exception catch (e) {
      emit(state._copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  // ── Ordens de Compra (PO) ──────────────────────────────────────────────────

  Future<void> loadPurchaseOrders({String? status}) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final orders = await ApiClient.purchases.getPurchaseOrders(status: status);
      emit(state._copyWith(isLoading: false, purchaseOrders: orders));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<bool> createPurchaseOrder(Map<String, dynamic> body) async {
    return _poAction(() async {
      await ApiClient.purchases.createPurchaseOrder(_withActor(body));
    });
  }

  Future<bool> reviewPurchaseOrder(int id, Map<String, dynamic> body) =>
      _poAction(() => ApiClient.purchases.reviewPurchaseOrder(id, _withActor(body)));

  Future<bool> approvePurchaseOrder(int id, Map<String, dynamic> body) =>
      _poAction(() => ApiClient.purchases.approvePurchaseOrder(id, _withActor(body)));

  Future<bool> receivePurchaseOrder(int id, Map<String, dynamic> body) =>
      _poAction(() => ApiClient.purchases.receivePurchaseOrder(id, _withActor(body)));

  Future<bool> resubmitPurchaseOrder(int id, Map<String, dynamic> body) =>
      _poAction(() => ApiClient.purchases.resubmitPurchaseOrder(id, _withActor(body)));

  Map<String, dynamic> _withActor(Map<String, dynamic> body) =>
      {...body, 'actor_user_id': ApiClient.actorUserId};

  Future<bool> _poAction(Future<void> Function() action) async {
    emit(state._copyWith(isSubmitting: true, clearError: true));
    try {
      await action();
      emit(state._copyWith(isSubmitting: false, successMessage: 'OK'));
      unawaited(loadPurchaseOrders());
      return true;
    } on Exception catch (e) {
      emit(state._copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  void clearMessages() {
    emit(state._copyWith(clearError: true, clearSuccess: true));
  }
}
