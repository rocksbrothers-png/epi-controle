import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Padrão CORPORATIVO da faixa de atenção (#271-B2-b).
///
/// A lógica mora aqui, e não no widget, por dois motivos. O primeiro é
/// testabilidade: não há toolchain Dart no ambiente de desenvolvimento, então
/// o que estiver num `StatefulWidget` só é exercitado no CI. O segundo é que a
/// distinção que esta fatia protege — salvar 20% ≠ restaurar o padrão de 20% —
/// é comportamento, não pintura, e comportamento se prova com teste de unidade.

enum CompanyAttentionStatus { initial, loading, ready, saving, error }

class CompanyAttentionState extends Equatable {
  const CompanyAttentionState({
    this.status = CompanyAttentionStatus.initial,
    this.setting,
    this.error,
    this.savedFeedback,
  });

  final CompanyAttentionStatus status;

  /// `null` até a primeira leitura. Enquanto for `null` a tela não salva nada:
  /// sem os limites do servidor não há régua para validar contra.
  final CompanyAttentionSetting? setting;

  final String? error;

  /// Qual ação concluiu, para a tela dar a mensagem certa. `saved` e
  /// `restored` terminam com valores possivelmente idênticos e significam
  /// coisas opostas — dizer só "pronto" perderia a diferença justamente na
  /// hora em que o usuário precisa vê-la.
  final CompanyAttentionOutcome? savedFeedback;

  bool get isBusy =>
      status == CompanyAttentionStatus.loading ||
      status == CompanyAttentionStatus.saving;

  /// Restaurar só faz sentido quando existe configuração corporativa para
  /// apagar. O backend trata o caso vazio como no-op silencioso, mas oferecer
  /// um botão que não faz nada é pior do que desabilitá-lo.
  bool get canRestore => setting?.hasCompanyConfig ?? false;

  CompanyAttentionState _copyWith({
    CompanyAttentionStatus? status,
    CompanyAttentionSetting? setting,
    String? error,
    CompanyAttentionOutcome? savedFeedback,
    bool clearError = false,
    bool clearFeedback = false,
  }) =>
      CompanyAttentionState(
        status: status ?? this.status,
        setting: setting ?? this.setting,
        error: clearError ? null : (error ?? this.error),
        savedFeedback:
            clearFeedback ? null : (savedFeedback ?? this.savedFeedback),
      );

  @override
  List<Object?> get props => [status, setting, error, savedFeedback];
}

enum CompanyAttentionOutcome { saved, restored }

class CompanyAttentionCubit extends Cubit<CompanyAttentionState> {
  CompanyAttentionCubit({
    required this.actorUserId,
    required this.stockApi,
  }) : super(const CompanyAttentionState());

  final int actorUserId;
  final StockApi stockApi;

  /// Empresa em edição. `null` para admins de empresa (o backend força a
  /// própria); o id real para o `master_admin`.
  int? _companyId;

  /// Carrega o padrão da empresa.
  ///
  /// [companyId] só deve vir preenchido para o `master_admin`. Um master SEM
  /// empresa escolhida não chega aqui: a tela não monta o cartão. Se chegasse,
  /// o backend recusaria com 400 — em nenhum dos dois caminhos a empresa é
  /// adivinhada.
  Future<void> load({int? companyId}) async {
    _companyId = companyId;
    emit(state._copyWith(
      status: CompanyAttentionStatus.loading,
      clearError: true,
      clearFeedback: true,
    ));
    try {
      final setting = await stockApi.getCompanyAttentionPercentage(
        actorUserId: actorUserId,
        companyId: companyId,
      );
      emit(state._copyWith(
        status: CompanyAttentionStatus.ready,
        setting: setting,
      ));
    } on Object catch (e) {
      emit(state._copyWith(
        status: CompanyAttentionStatus.error,
        error: e.toString(),
      ));
    }
  }

  /// Grava um percentual. A empresa fica `company_configured`, mesmo que o
  /// valor coincida com o padrão do sistema.
  ///
  /// A validação local é conveniência para não gastar uma ida ao servidor com
  /// algo obviamente inválido; ela **não** é a régua. O teto e o padrão vêm de
  /// [CompanyAttentionSetting], que os leu do backend, e um erro do servidor é
  /// exibido como veio.
  Future<void> save(int percentage) async {
    final atual = state.setting;
    if (atual == null) return;
    if (percentage < 0 || percentage > atual.maxPercentage) {
      emit(state._copyWith(
        status: CompanyAttentionStatus.error,
        error: 'range',
        clearFeedback: true,
      ));
      return;
    }
    await _run(
      () => stockApi.setCompanyAttentionPercentage(
        actorUserId: actorUserId,
        attentionPercentage: percentage,
        companyId: _companyId,
      ),
      CompanyAttentionOutcome.saved,
    );
  }

  /// Apaga a configuração corporativa e devolve a empresa ao padrão do
  /// sistema.
  ///
  /// Não é `save(systemDefaultPercentage)`. Aquilo gravaria uma decisão; isto
  /// remove a decisão. A origem que volta do servidor é o que distingue as
  /// duas, e é ela que a tela mostra.
  Future<void> restoreSystemDefault() async {
    if (state.setting == null) return;
    await _run(
      () => stockApi.restoreCompanyAttentionPercentage(
        actorUserId: actorUserId,
        companyId: _companyId,
      ),
      CompanyAttentionOutcome.restored,
    );
  }

  Future<void> _run(
    Future<CompanyAttentionSetting> Function() acao,
    CompanyAttentionOutcome desfecho,
  ) async {
    final anterior = state.setting;
    emit(state._copyWith(
      status: CompanyAttentionStatus.saving,
      clearError: true,
      clearFeedback: true,
    ));
    try {
      final resposta = await acao();
      emit(state._copyWith(
        status: CompanyAttentionStatus.ready,
        // O POST devolve valor e origem, mas não repete os limites; sem o
        // merge o teto viraria 0 e a validação passaria a recusar tudo.
        setting: anterior == null
            ? resposta
            : resposta.mergeLimitsFrom(anterior),
        savedFeedback: desfecho,
      ));
    } on Object catch (e) {
      emit(state._copyWith(
        status: CompanyAttentionStatus.error,
        error: e.toString(),
      ));
    }
  }
}
