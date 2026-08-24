import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Estado do seletor de Unidade compartilhado.
///
/// **Este cubit não decide permissão.** Ele carrega o que
/// `GET /api/units/selectable` devolveu e guarda a escolha do usuário. Toda
/// pergunta de autorização — quais Unidades, se cabe "Todas", se o perfil é
/// travado — já veio respondida do servidor.

/// Para que o seletor está sendo usado. Muda o que pode ser escolhido.
enum UnitSelectorPurpose {
  /// Consultar. Perfil livre autorizado pode ver "Todas as Unidades": é uma
  /// visão consolidada, e consolidar leitura é legítimo.
  read,

  /// Configurar/gravar. "Todas" **não** é oferecida: não existe gravar
  /// configuração em todas as Unidades, e um botão Salvar com "Todas"
  /// selecionado deixaria dúvida entre gravar em todas, herdar, ou escolher
  /// alguma em silêncio. Sem Unidade específica, o chamador fica fail-closed.
  write,
}

enum UnitSelectorStatus { initial, loading, ready, error }

class UnitSelectorState extends Equatable {
  const UnitSelectorState({
    this.status = UnitSelectorStatus.initial,
    this.scope = SelectableUnits.empty,
    this.selectedUnitId,
    this.error,
  });

  final UnitSelectorStatus status;
  final SelectableUnits scope;

  /// Unidade escolhida. `null` significa coisas diferentes conforme o
  /// propósito: em leitura é a visão consolidada; em escrita é "ainda não
  /// escolheu", e o chamador não pode gravar.
  final int? selectedUnitId;

  final String? error;

  /// Pode-se gravar com o estado atual?
  ///
  /// Só com uma Unidade REAL selecionada. É a tradução, em uma linha, da
  /// regra de que "Todas" nunca governa uma escrita.
  bool get canWrite => selectedUnitId != null;

  /// O ator não enxerga Unidade nenhuma — carteira existente e vazia.
  bool get blocked => scope.blocksEverything;

  UnitSelectorState _copyWith({
    UnitSelectorStatus? status,
    SelectableUnits? scope,
    int? selectedUnitId,
    String? error,
    bool clearError = false,
    bool clearSelection = false,
  }) =>
      UnitSelectorState(
        status: status ?? this.status,
        scope: scope ?? this.scope,
        selectedUnitId:
            clearSelection ? null : (selectedUnitId ?? this.selectedUnitId),
        error: clearError ? null : (error ?? this.error),
      );

  @override
  List<Object?> get props => [status, scope, selectedUnitId, error];
}

class UnitSelectorCubit extends Cubit<UnitSelectorState> {
  UnitSelectorCubit({
    required this.actorUserId,
    required this.unitsApi,
    required this.purpose,
    this.preferredUnitId,
  }) : super(const UnitSelectorState());

  final int actorUserId;
  final UnitsApi unitsApi;
  final UnitSelectorPurpose purpose;

  /// Unidade que o chamador GOSTARIA de ver pré-selecionada — tipicamente um
  /// `?unit_id=` de deep link (#271-B2-a, ajuste 4).
  ///
  /// **É entrada não confiável e é tratada como tal.** Só vale depois de
  /// aparecer entre as Unidades que `GET /api/units/selectable` devolveu, e
  /// nunca para perfil travado, cuja Unidade é a do ator e ponto. Um valor que
  /// não passe nesse filtro é descartado em silêncio e o seletor fica no estado
  /// que teria sem ele — fail-closed, não "abre na Unidade pedida".
  ///
  /// Deixar essa validação aqui, e não em cada tela, é o mesmo motivo que fez o
  /// seletor existir: quem valida é quem tem a lista.
  final int? preferredUnitId;

  Future<void> load() async {
    emit(state._copyWith(
      status: UnitSelectorStatus.loading,
      clearError: true,
    ));
    try {
      final scope = await unitsApi.getSelectableUnits(actorUserId: actorUserId);
      emit(state._copyWith(
        status: UnitSelectorStatus.ready,
        scope: scope,
        selectedUnitId: _selecaoInicial(scope),
        clearSelection: _selecaoInicial(scope) == null,
      ));
    } on Object catch (e) {
      // Falha de carga NÃO vira "sem restrição". Sem escopo, nada é oferecido.
      emit(state._copyWith(
        status: UnitSelectorStatus.error,
        scope: SelectableUnits.empty,
        error: e.toString(),
        clearSelection: true,
      ));
    }
  }

  /// A escolha do usuário. `null` = "Todas", que só é alcançável em leitura.
  void select(int? unitId) {
    if (state.scope.locked) return;
    if (unitId == null) {
      if (purpose == UnitSelectorPurpose.write) return;
      emit(state._copyWith(clearSelection: true));
      return;
    }
    // Uma Unidade fora do que o servidor ofereceu não é escolhível. O backend
    // recusaria de novo, mas aceitar aqui exibiria um estado que não existe.
    if (!state.scope.units.any((u) => u.id == unitId)) return;
    emit(state._copyWith(selectedUnitId: unitId));
  }

  /// Pré-seleção, quando ela é obrigatória em vez de conveniência.
  ///
  /// - **perfil travado**: a Unidade do ator, sempre — inclusive por cima de
  ///   um [preferredUnitId], que para esse perfil não é uma preferência a
  ///   respeitar e sim uma tentativa de escolher;
  /// - **[preferredUnitId] validado**: a Unidade pedida, quando ela consta da
  ///   lista que o servidor ofereceu;
  /// - **uma opção só**: pré-seleciona, porque escolher entre uma coisa não é
  ///   escolha — e em escrita deixar `null` bloquearia quem não tem alternativa;
  /// - **escrita sem "Todas" e várias opções**: `null`, e o chamador fica
  ///   fail-closed até o usuário decidir;
  /// - **leitura**: `null`, que é a visão consolidada.
  int? _selecaoInicial(SelectableUnits scope) {
    if (scope.locked) return scope.unitId;
    final pedida = preferredUnitId;
    // A checagem é a mesma de `select`: pertencer a `scope.units`. O backend
    // recusaria de novo, mas aceitar aqui abriria a tela num escopo que o ator
    // não tem — e a tela de configuração passaria a LER parâmetros de uma
    // Unidade a partir de um parâmetro de URL.
    if (pedida != null && scope.units.any((u) => u.id == pedida)) {
      return pedida;
    }
    if (scope.units.length == 1 && !scope.allowsAllUnits) {
      return scope.units.first.id;
    }
    return null;
  }

  /// "Todas" aparece? Backend autoriza E o propósito permite.
  ///
  /// A conjunção importa: `allowsAllUnits` sozinho ofereceria consolidação
  /// numa tela de gravação.
  bool get offersAllUnits =>
      state.scope.allowsAllUnits && purpose == UnitSelectorPurpose.read;
}
