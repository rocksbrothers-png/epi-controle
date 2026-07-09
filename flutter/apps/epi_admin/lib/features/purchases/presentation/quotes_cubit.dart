import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../data/datasources/purchases_remote_datasource.dart';
import '../data/repository_impl/purchases_repository_impl.dart';
import '../domain/repositories/purchases_repository.dart';

// ── State ──────────────────────────────────────────────────────────────────

class QuotesState extends Equatable {
  const QuotesState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.quotes = const [],
    this.comparison = const {},
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  final List<Map<String, dynamic>> quotes;
  final Map<String, dynamic> comparison;

  QuotesState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    List<Map<String, dynamic>>? quotes,
    Map<String, dynamic>? comparison,
    bool clearError = false,
  }) =>
      QuotesState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        quotes: quotes ?? this.quotes,
        comparison: comparison ?? this.comparison,
      );

  @override
  List<Object?> get props =>
      [isLoading, isSubmitting, error, quotes, comparison];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

/// Cotações (RFQ) de uma requisição de compra (Fase F3).
/// A comparação de preços/prazos vem pronta do backend — nada é recalculado.
class QuotesCubit extends Cubit<QuotesState> {
  QuotesCubit(this.purchaseRequestId, {PurchasesRepository? repository})
      : _repository = repository ??
            const PurchasesRepositoryImpl(ApiPurchasesRemoteDataSource()),
        super(const QuotesState());

  final int purchaseRequestId;
  final PurchasesRepository _repository;

  Future<void> load() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      final data = await _repository.getQuotesForRequest(purchaseRequestId);
      final items = ((data['items'] as List?) ?? [])
          .map((e) => (e as Map).cast<String, dynamic>())
          .toList();
      final comparison =
          ((data['comparison'] as Map?) ?? {}).cast<String, dynamic>();
      emit(state.copyWith(
          isLoading: false, quotes: items, comparison: comparison));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<bool> createQuotes(List<int> supplierIds) async {
    return _submit(() => _repository.createQuotesForRequest(
        purchaseRequestId, {'supplier_ids': supplierIds}));
  }

  Future<bool> sendQuote(int quoteId, {required bool viaPortal}) async {
    return _submit(() => viaPortal
        ? _repository.sendQuotePortalLink(quoteId, {})
        : _repository.sendQuote(quoteId, {}));
  }

  Future<bool> answerQuote(int quoteId, Map<String, dynamic> body) async {
    return _submit(() => _repository.answerQuote(quoteId, body));
  }

  /// Seleciona a vencedora e retorna o rascunho de PO pré-preenchido pelo
  /// backend (a criação da PO usa o fluxo/aprovação existentes).
  Future<Map<String, dynamic>?> selectQuote(int quoteId) async {
    emit(state.copyWith(isSubmitting: true, clearError: true));
    try {
      final result = await _repository.selectQuote(quoteId, {});
      emit(state.copyWith(isSubmitting: false));
      await load();
      return ((result['po_draft'] as Map?) ?? {}).cast<String, dynamic>();
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return null;
    }
  }

  Future<int?> createPurchaseOrderFromDraft(Map<String, dynamic> draft) async {
    emit(state.copyWith(isSubmitting: true, clearError: true));
    try {
      final id = await _repository.createPurchaseOrder(draft);
      emit(state.copyWith(isSubmitting: false));
      return id;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> loadSuppliers() async {
    try {
      return await _repository.getAuthorizedSuppliers();
    } on Exception {
      return const [];
    }
  }

  Future<bool> _submit(Future<dynamic> Function() action) async {
    emit(state.copyWith(isSubmitting: true, clearError: true));
    try {
      await action();
      emit(state.copyWith(isSubmitting: false));
      await load();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }
}
