import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../data/datasources/purchases_remote_datasource.dart';
import '../data/repository_impl/purchases_repository_impl.dart';
import '../domain/repositories/purchases_repository.dart';

// ── State ──────────────────────────────────────────────────────────────────

class SuppliersState extends Equatable {
  const SuppliersState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.suppliers = const [],
    this.products = const [],
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  final List<Map<String, dynamic>> suppliers;
  final List<Map<String, dynamic>> products;

  SuppliersState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    List<Map<String, dynamic>>? suppliers,
    List<Map<String, dynamic>>? products,
    bool clearError = false,
  }) =>
      SuppliersState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        suppliers: suppliers ?? this.suppliers,
        products: products ?? this.products,
      );

  @override
  List<Object?> get props =>
      [isLoading, isSubmitting, error, suppliers, products];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

/// Fornecedores e catálogo (Fase F3). Sem regra de negócio local:
/// validações e unicidade de CNPJ/SKU são do backend.
class SuppliersCubit extends Cubit<SuppliersState> {
  SuppliersCubit({PurchasesRepository? repository})
      : _repository = repository ??
            const PurchasesRepositoryImpl(ApiPurchasesRemoteDataSource()),
        super(const SuppliersState());

  final PurchasesRepository _repository;

  Future<void> loadSuppliers() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      final items = await _repository.getAuthorizedSuppliers();
      emit(state.copyWith(isLoading: false, suppliers: items));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// Cria (POST) ou atualiza (PUT legado + PUT /procurement) um fornecedor.
  Future<bool> saveSupplier({
    int? supplierId,
    required Map<String, dynamic> legacyFields,
    required Map<String, dynamic> procurementFields,
  }) async {
    emit(state.copyWith(isSubmitting: true, clearError: true));
    try {
      if (supplierId == null) {
        await _repository
            .createAuthorizedSupplier({...legacyFields, ...procurementFields});
      } else {
        await _repository.updateAuthorizedSupplier(supplierId, legacyFields);
        await _repository.updateSupplierProcurement(
            supplierId, procurementFields);
      }
      emit(state.copyWith(isSubmitting: false));
      await loadSuppliers();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  Future<void> loadProducts(int supplierId) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      final items = await _repository.getSupplierProducts(supplierId);
      emit(state.copyWith(isLoading: false, products: items));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<bool> saveProduct(int supplierId, Map<String, dynamic> body) async {
    emit(state.copyWith(isSubmitting: true, clearError: true));
    try {
      await _repository.upsertSupplierProduct(supplierId, body);
      emit(state.copyWith(isSubmitting: false));
      await loadProducts(supplierId);
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  Future<void> deactivateProduct(int supplierId, int productId) async {
    try {
      await _repository.deactivateSupplierProduct(productId);
      await loadProducts(supplierId);
    } on Exception catch (e) {
      emit(state.copyWith(error: e.toString()));
    }
  }
}
