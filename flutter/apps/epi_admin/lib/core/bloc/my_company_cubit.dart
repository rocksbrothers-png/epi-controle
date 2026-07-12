import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class MyCompanyState extends Equatable {
  const MyCompanyState({
    this.isLoading = false,
    this.isSaving = false,
    this.error,
    this.profile,
    this.domains = const [],
    this.saved = false,
  });

  final bool isLoading;
  final bool isSaving;
  final String? error;
  final MyCompanyProfile? profile;
  final List<TenantDomain> domains;
  final bool saved;

  MyCompanyState _copyWith({
    bool? isLoading,
    bool? isSaving,
    String? error,
    MyCompanyProfile? profile,
    List<TenantDomain>? domains,
    bool? saved,
    bool clearError = false,
  }) =>
      MyCompanyState(
        isLoading: isLoading ?? this.isLoading,
        isSaving: isSaving ?? this.isSaving,
        error: clearError ? null : (error ?? this.error),
        profile: profile ?? this.profile,
        domains: domains ?? this.domains,
        saved: saved ?? false,
      );

  @override
  List<Object?> get props =>
      [isLoading, isSaving, error, profile, domains, saved];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

/// Configuração da própria empresa pelo Administrador Geral (Owner).
/// Espelha `Configurações > Minha Empresa` do frontend web.
class MyCompanyCubit extends Cubit<MyCompanyState> {
  MyCompanyCubit() : super(const MyCompanyState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final profile = await ApiClient.myCompany.getMyCompany();
      final domains = await ApiClient.myCompany.getDomains();
      emit(state._copyWith(
        isLoading: false,
        profile: profile,
        domains: domains,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<void> save(Map<String, dynamic> fields) async {
    emit(state._copyWith(isSaving: true, clearError: true));
    try {
      final profile = await ApiClient.myCompany.updateMyCompany(fields);
      emit(state._copyWith(isSaving: false, profile: profile, saved: true));
    } on Exception catch (e) {
      emit(state._copyWith(isSaving: false, error: e.toString()));
    }
  }

  Future<void> registerDomain(String domain, String domainType) async {
    emit(state._copyWith(clearError: true));
    try {
      await ApiClient.myCompany
          .registerDomain(domain: domain, domainType: domainType);
      final domains = await ApiClient.myCompany.getDomains();
      emit(state._copyWith(domains: domains));
    } on Exception catch (e) {
      emit(state._copyWith(error: e.toString()));
    }
  }

  Future<void> verifyDomain(int id) async {
    emit(state._copyWith(clearError: true));
    try {
      await ApiClient.myCompany.verifyDomain(id);
      final domains = await ApiClient.myCompany.getDomains();
      emit(state._copyWith(domains: domains));
    } on Exception catch (e) {
      emit(state._copyWith(error: e.toString()));
    }
  }

  Future<void> deleteDomain(int id) async {
    emit(state._copyWith(clearError: true));
    try {
      await ApiClient.myCompany.deleteDomain(id);
      final domains = await ApiClient.myCompany.getDomains();
      emit(state._copyWith(domains: domains));
    } on Exception catch (e) {
      emit(state._copyWith(error: e.toString()));
    }
  }
}
