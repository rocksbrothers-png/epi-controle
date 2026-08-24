import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/unit_selector_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// Seletor de Unidade compartilhado — o cliente não decide permissão.
///
/// O que estes testes protegem: **o que o seletor oferece vem inteiro do
/// servidor.** Quais Unidades, se cabe "Todas", se o perfil é travado. Nada
/// aqui é derivado do tamanho da lista nem de um `if` de perfil, porque foi
/// assim que quatro telas do Flutter acabaram com quatro tratamentos
/// diferentes da mesma lista — e uma delas estreitando autorização no cliente.

class _FakeUnitsApi implements UnitsApi {
  _FakeUnitsApi({this.escopo, this.erro});

  final SelectableUnits? escopo;
  final Object? erro;
  int chamadas = 0;
  int? atorRecebido;

  @override
  Future<SelectableUnits> getSelectableUnits({required int actorUserId}) async {
    chamadas++;
    atorRecebido = actorUserId;
    if (erro != null) throw erro!;
    return escopo!;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError(
        '${invocation.memberName} não é usado pelo UnitSelectorCubit.',
      );
}

SelectableUnits _escopo({
  List<int> ids = const [10, 11],
  bool locked = false,
  int? unitId,
  String source = 'none',
  bool allowsAll = true,
  bool blocks = false,
}) =>
    SelectableUnits(
      units: [
        for (final id in ids) SelectableUnit(id: id, name: 'Unidade $id'),
      ],
      locked: locked,
      unitId: unitId,
      source: source,
      allowsAllUnits: allowsAll,
      blocksEverything: blocks,
    );

UnitSelectorCubit _cubit(
  _FakeUnitsApi api, {
  UnitSelectorPurpose purpose = UnitSelectorPurpose.read,
}) =>
    UnitSelectorCubit(actorUserId: 7, unitsApi: api, purpose: purpose);

void main() {
  group('a lista vem do servidor', () {
    test('carrega as Unidades e o contexto', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11, 12]));
      final cubit = _cubit(api);

      await cubit.load();

      expect(cubit.state.status, UnitSelectorStatus.ready);
      expect(cubit.state.scope.units.map((u) => u.id), [10, 11, 12]);
      expect(api.atorRecebido, 7);
    });

    test('falha ao carregar NÃO vira sem restrição', () async {
      final api = _FakeUnitsApi(erro: StateError('500'));
      final cubit = _cubit(api);

      await cubit.load();

      expect(cubit.state.status, UnitSelectorStatus.error);
      expect(cubit.state.scope.units, isEmpty,
          reason: 'sem escopo, nada pode ser oferecido');
      expect(cubit.state.canWrite, isFalse);
    });
  });

  group('"Todas" só quando o backend autoriza E o propósito permite', () {
    test('leitura com allows_all_units: oferece', () async {
      final api = _FakeUnitsApi(escopo: _escopo(allowsAll: true));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.read);
      await cubit.load();

      expect(cubit.offersAllUnits, isTrue);
    });

    test('leitura SEM allows_all_units: não oferece', () async {
      final api = _FakeUnitsApi(escopo: _escopo(allowsAll: false));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.read);
      await cubit.load();

      expect(cubit.offersAllUnits, isFalse,
          reason: 'quem decide é o backend, não o tamanho da lista');
    });

    test('escrita NUNCA oferece, mesmo com allows_all_units', () async {
      final api = _FakeUnitsApi(escopo: _escopo(allowsAll: true));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);
      await cubit.load();

      expect(cubit.offersAllUnits, isFalse,
          reason: 'não existe gravar configuração em todas as Unidades');
    });

    test('"Todas" não é derivado do tamanho da lista', () async {
      // Carteira de UMA Unidade com allows_all_units=false: lista não-vazia,
      // e ainda assim sem "Todas". Derivar de `units.length` erraria aqui.
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10], allowsAll: false));
      final cubit = _cubit(api);
      await cubit.load();

      expect(cubit.state.scope.units, hasLength(1));
      expect(cubit.offersAllUnits, isFalse);
    });
  });

  group('escrita é fail-closed sem Unidade específica', () {
    test('escrita com várias opções começa sem seleção e sem poder gravar',
        () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11], allowsAll: true));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);

      await cubit.load();

      expect(cubit.state.selectedUnitId, isNull);
      expect(cubit.state.canWrite, isFalse);
    });

    test('escolher uma Unidade libera a gravação', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11]));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);
      await cubit.load();

      cubit.select(11);

      expect(cubit.state.selectedUnitId, 11);
      expect(cubit.state.canWrite, isTrue);
    });

    test('em escrita não dá para voltar para "Todas"', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11]));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);
      await cubit.load();
      cubit.select(11);

      cubit.select(null);

      expect(cubit.state.selectedUnitId, 11,
          reason: 'a consolidação não pode governar uma escrita');
    });

    test('em leitura, "Todas" é escolha válida', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11]));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.read);
      await cubit.load();
      cubit.select(11);

      cubit.select(null);

      expect(cubit.state.selectedUnitId, isNull);
    });
  });

  group('pré-seleção', () {
    test('perfil travado já vem com a própria Unidade', () async {
      final api = _FakeUnitsApi(escopo: _escopo(
          ids: [11], locked: true, unitId: 11, source: 'actor', allowsAll: false));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);

      await cubit.load();

      expect(cubit.state.selectedUnitId, 11);
      expect(cubit.state.canWrite, isTrue,
          reason: 'perfil travado não tem o que escolher; travá-lo seria bug');
    });

    test('opção única é pré-selecionada', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10], allowsAll: false));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);

      await cubit.load();

      expect(cubit.state.selectedUnitId, 10);
    });

    test('opção única mas com "Todas" disponível não é pré-selecionada',
        () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10], allowsAll: true));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.read);

      await cubit.load();

      expect(cubit.state.selectedUnitId, isNull,
          reason: 'há duas opções reais: a Unidade e a consolidação');
    });
  });

  group('perfil travado não troca de Unidade', () {
    test('select é ignorado', () async {
      final api = _FakeUnitsApi(escopo: _escopo(
          ids: [11], locked: true, unitId: 11, source: 'actor', allowsAll: false));
      final cubit = _cubit(api);
      await cubit.load();

      cubit.select(10);
      cubit.select(null);

      expect(cubit.state.selectedUnitId, 11);
    });
  });

  group('carteira vazia não vira empresa inteira', () {
    test('blocks_everything bloqueia tudo', () async {
      final api = _FakeUnitsApi(escopo: _escopo(
          ids: [], source: 'purchase_scope', allowsAll: false, blocks: true));
      final cubit = _cubit(api);

      await cubit.load();

      expect(cubit.state.blocked, isTrue);
      expect(cubit.state.scope.units, isEmpty);
      expect(cubit.offersAllUnits, isFalse);
      expect(cubit.state.canWrite, isFalse);
    });

    test('empresa sem Unidades é estado DIFERENTE de carteira vazia', () async {
      final api = _FakeUnitsApi(escopo: _escopo(
          ids: [], source: 'none', allowsAll: true, blocks: false));
      final cubit = _cubit(api);

      await cubit.load();

      expect(cubit.state.scope.isEmpty, isTrue);
      expect(cubit.state.blocked, isFalse,
          reason: 'lista vazia pelos dois lados, mensagens diferentes');
    });
  });

  group('a escolha é validada contra o que o servidor ofereceu', () {
    test('Unidade fora da lista é ignorada', () async {
      final api = _FakeUnitsApi(escopo: _escopo(ids: [10, 11]));
      final cubit = _cubit(api, purpose: UnitSelectorPurpose.write);
      await cubit.load();

      cubit.select(99);

      expect(cubit.state.selectedUnitId, isNull,
          reason: 'o backend recusaria; exibir aqui seria estado inexistente');
    });
  });

  group('contrato do modelo', () {
    test('lê o payload do backend inteiro', () {
      final lido = SelectableUnits.fromJson({
        'units': [
          {'id': 10, 'name': 'Unidade A', 'legal_entity_id': 1},
        ],
        'locked': true,
        'unit_id': 10,
        'source': 'actor',
        'allows_all_units': false,
        'blocks_everything': false,
      });

      expect(lido.units.single.id, 10);
      expect(lido.units.single.name, 'Unidade A');
      expect(lido.units.single.legalEntityId, 1);
      expect(lido.locked, isTrue);
      expect(lido.unitId, 10);
      expect(lido.source, 'actor');
      expect(lido.allowsAllUnits, isFalse);
    });

    test('payload vazio não vira permissivo', () {
      final vazio = SelectableUnits.fromJson(const {});

      expect(vazio.units, isEmpty);
      expect(vazio.locked, isFalse);
      expect(vazio.allowsAllUnits, isFalse,
          reason: 'ausência do campo não pode virar "pode ver tudo"');
    });

    test('hasChoice distingue escolha real de opção única', () {
      expect(_escopo(ids: [10], allowsAll: false).hasChoice, isFalse);
      expect(_escopo(ids: [10], allowsAll: true).hasChoice, isTrue);
      expect(_escopo(ids: [10, 11], allowsAll: false).hasChoice, isTrue);
    });
  });
}
