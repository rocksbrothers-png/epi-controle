import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class SettingsState extends Equatable {
  const SettingsState({
    this.isLoading = false,
    this.isSaving = false,
    this.error,
    this.config,
    this.successMessage,
    this.isMaster = false,
    this.companies = const [],
    this.selectedCompanyId,
  });

  final bool isLoading;
  final bool isSaving;
  final String? error;
  final FichaConfig? config;
  final String? successMessage;

  /// master_admin não tem empresa própria: precisa escolher a empresa cuja
  /// Ficha vai configurar (a Ficha é isolada por tenant).
  final bool isMaster;
  final List<Company> companies;
  final int? selectedCompanyId;

  SettingsState _copyWith({
    bool? isLoading,
    bool? isSaving,
    String? error,
    FichaConfig? config,
    String? successMessage,
    bool? isMaster,
    List<Company>? companies,
    int? selectedCompanyId,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      SettingsState(
        isLoading: isLoading ?? this.isLoading,
        isSaving: isSaving ?? this.isSaving,
        error: clearError ? null : (error ?? this.error),
        config: config ?? this.config,
        successMessage:
            clearSuccess ? null : (successMessage ?? this.successMessage),
        isMaster: isMaster ?? this.isMaster,
        companies: companies ?? this.companies,
        selectedCompanyId: selectedCompanyId ?? this.selectedCompanyId,
      );

  @override
  List<Object?> get props => [
        isLoading,
        isSaving,
        error,
        config,
        successMessage,
        isMaster,
        companies,
        selectedCompanyId,
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class SettingsCubit extends Cubit<SettingsState> {
  SettingsCubit() : super(const SettingsState());

  /// Ponto de entrada da tela. Para o master_admin carrega a lista de empresas
  /// e exige a seleção de uma antes de carregar a Ficha; para admins de
  /// empresa carrega direto a Ficha da própria empresa.
  Future<void> init({required bool isMaster}) async {
    if (!isMaster) {
      emit(state._copyWith(isMaster: false));
      await load();
      return;
    }
    emit(state._copyWith(isMaster: true, isLoading: true, clearError: true));
    try {
      final companies = await ApiClient.companies.getCompanies();
      final firstId = companies.isNotEmpty ? companies.first.id : null;
      emit(state._copyWith(companies: companies, selectedCompanyId: firstId));
      if (firstId != null) {
        await _loadFicha(companyId: firstId);
      } else {
        emit(state._copyWith(isLoading: false));
      }
    } catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<void> load() async => _loadFicha(companyId: null);

  Future<void> _loadFicha({required int? companyId}) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final config =
          await ApiClient.settings.getFichaConfig(companyId: companyId);
      emit(state._copyWith(isLoading: false, config: config));
    } catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// master_admin troca a empresa ativa → recarrega a Ficha do tenant.
  Future<void> selectCompany(int companyId) async {
    emit(state._copyWith(selectedCompanyId: companyId));
    await _loadFicha(companyId: companyId);
  }

  Future<void> save(FichaConfig config) async {
    emit(state._copyWith(isSaving: true, clearError: true, clearSuccess: true));
    try {
      await ApiClient.settings.updateFichaConfig(
        config,
        companyId: state.isMaster ? state.selectedCompanyId : null,
      );
      emit(state._copyWith(
        isSaving: false,
        config: config,
        successMessage: 'ok',
      ));
    } catch (e) {
      emit(state._copyWith(isSaving: false, error: e.toString()));
    }
  }
}
