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
  });

  final bool isLoading;
  final bool isSaving;
  final String? error;
  final FichaConfig? config;
  final String? successMessage;

  SettingsState _copyWith({
    bool? isLoading,
    bool? isSaving,
    String? error,
    FichaConfig? config,
    String? successMessage,
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
      );

  @override
  List<Object?> get props =>
      [isLoading, isSaving, error, config, successMessage];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class SettingsCubit extends Cubit<SettingsState> {
  SettingsCubit() : super(const SettingsState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final config = await ApiClient.settings.getFichaConfig();
      emit(state._copyWith(isLoading: false, config: config));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  Future<void> save(FichaConfig config) async {
    emit(state._copyWith(isSaving: true, clearError: true, clearSuccess: true));
    try {
      await ApiClient.settings.updateFichaConfig(config);
      emit(state._copyWith(
        isSaving: false,
        config: config,
        successMessage: 'ok',
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isSaving: false, error: e.toString()));
    }
  }
}
