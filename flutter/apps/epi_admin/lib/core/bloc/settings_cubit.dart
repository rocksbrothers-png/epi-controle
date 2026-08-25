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

  /// Ponto de entrada da tela-hub de Configurações.
  ///
  /// Só o master_admin precisa de carga: ele não pertence a uma empresa e
  /// escolhe qual tenant está administrando. A escolha viaja para as subtelas
  /// em `?company_id=`, então o hub NÃO carrega mais a Ficha — quem carrega é
  /// a subtela que a edita, com a empresa já resolvida.
  Future<void> initCompanies({required bool isMaster}) async {
    if (!isMaster) {
      emit(state._copyWith(isMaster: false));
      return;
    }
    emit(state._copyWith(isMaster: true, isLoading: true, clearError: true));
    try {
      final companies = await ApiClient.companies.getCompanies();
      emit(state._copyWith(
        companies: companies,
        selectedCompanyId: companies.isNotEmpty ? companies.first.id : null,
        isLoading: false,
      ));
    } catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// Ponto de entrada da subtela da Ficha, com a empresa já resolvida pelo hub.
  ///
  /// `companyId` nulo para admins de empresa (o backend resolve a própria) e
  /// para o master_admin que ainda não escolheu — neste caso não há o que
  /// carregar, e a subtela mostra o aviso em vez do formulário.
  Future<void> initForCompany({
    required bool isMaster,
    required int? companyId,
  }) async {
    emit(state._copyWith(isMaster: isMaster, selectedCompanyId: companyId));
    if (isMaster && companyId == null) return;
    await _loadFicha(companyId: companyId);
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

  /// master_admin troca a empresa ativa no hub. Não recarrega nada aqui: cada
  /// subtela abre já com a empresa na query e carrega o que é dela.
  void selectCompany(int companyId) {
    emit(state._copyWith(selectedCompanyId: companyId));
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
