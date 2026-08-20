import 'package:epi_admin/core/bloc/dashboard_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Dashboard depois da fatia 1.1D-C2: o painel **consome**
/// `GET /api/dashboard/summary` e não recomputa nada.
///
/// Antes ele baixava `/api/bootstrap` inteiro e refazia em Dart os KPIs, o
/// recorte por CNPJ/Unidade/Setor, a lista de setores e a dedução de perfil
/// travado. Estes testes travam a fronteira nova: o que o cubit ENVIA ao
/// servidor, e o fato de que tudo que ele mostra veio de volta de lá.

/// Servidor de mentira que registra o recorte pedido e devolve um payload fixo.
class _Servidor {
  _Servidor(this.resposta);

  final Map<String, dynamic> Function(int? cnpj, int? unidade, String? setor)
      resposta;

  final chamadas = <({int? legalEntityId, int? unitId, String? sector})>[];

  Future<DashboardSummary> carregar({
    int? legalEntityId,
    int? unitId,
    String? sector,
  }) async {
    chamadas.add((
      legalEntityId: legalEntityId,
      unitId: unitId,
      sector: sector,
    ));
    return DashboardSummary.fromJson(resposta(legalEntityId, unitId, sector));
  }
}

Map<String, dynamic> _payload({
  int? unitId,
  String unitScopeSource = 'none',
  bool locked = false,
  int? legalEntityId,
  String? sector,
  int? criticalStock,
  int? nearMinimumStock,
  int deliveriesToday = 0,
  List<Map<String, dynamic>> units = const [],
  List<Map<String, dynamic>> legalEntities = const [],
  List<String> sectors = const [],
}) =>
    {
      'scope': {
        'unit_id': unitId,
        'unit_scope_source': unitScopeSource,
        'locked': locked,
        'legal_entity_id': legalEntityId,
        'sector': sector,
      },
      'kpis': {
        'deliveries_today': deliveriesToday,
        'expiring_epis': 0,
        'critical_stock': criticalStock,
        'near_minimum_stock': nearMinimumStock,
        'pending_purchases': 0,
      },
      'filters': {
        'legal_entities': legalEntities,
        'units': units,
        'sectors': sectors,
      },
      'alerts': const [],
      'compliance': const {'summary': <String, int>{}},
    };

const _unidades = <Map<String, dynamic>>[
  {'id': 1, 'name': 'Matriz SP', 'legal_entity_id': 10},
  {'id': 2, 'name': 'Base Santos', 'legal_entity_id': 10},
  {'id': 3, 'name': 'Filial RJ', 'legal_entity_id': 20},
];

const _cnpjs = <Map<String, dynamic>>[
  {'id': 10, 'name': 'ACME SA'},
  {'id': 20, 'name': 'ACME Filial RJ'},
];

void main() {
  group('DashboardState.availableUnits (cascata CNPJ → Unidade)', () {
    final filtros = DashboardFilters.fromJson(const {
      'units': _unidades,
      'legal_entities': _cnpjs,
    });

    test('sem CNPJ selecionado devolve todas as unidades', () {
      final state = DashboardState(filters: filtros);
      expect(state.availableUnits, hasLength(3));
    });

    test('com CNPJ selecionado devolve só as unidades daquele CNPJ', () {
      final state = DashboardState(
        filters: filtros,
        scope: const DashboardScope(legalEntityId: 10),
      );
      final nomes = state.availableUnits.map((u) => u.name).toList();
      expect(nomes, ['Matriz SP', 'Base Santos']);
      expect(nomes, isNot(contains('Filial RJ')));
    });

    test('CNPJ sem unidades devolve lista vazia', () {
      final state = DashboardState(
        filters: filtros,
        scope: const DashboardScope(legalEntityId: 99),
      );
      expect(state.availableUnits, isEmpty);
    });

    test('unidade sem legal_entity_id não aparece sob nenhum CNPJ', () {
      // Caso da janela de migração: unidade ainda sem vínculo.
      final state = DashboardState(
        filters: DashboardFilters.fromJson(const {
          'units': [
            {'id': 4, 'name': 'Sem CNPJ', 'legal_entity_id': null},
          ],
        }),
        scope: const DashboardScope(legalEntityId: 10),
      );
      expect(state.availableUnits, isEmpty);
    });
  });

  group('DashboardState.hasActiveFilter', () {
    test('falso sem nenhuma seleção', () {
      expect(const DashboardState().hasActiveFilter, isFalse);
    });

    test('verdadeiro com qualquer nível no escopo do servidor', () {
      expect(
        const DashboardState(scope: DashboardScope(legalEntityId: 10))
            .hasActiveFilter,
        isTrue,
      );
      expect(
        const DashboardState(scope: DashboardScope(unitId: 1)).hasActiveFilter,
        isTrue,
      );
      expect(
        const DashboardState(scope: DashboardScope(sector: 'Operação'))
            .hasActiveFilter,
        isTrue,
      );
    });
  });

  group('KPIs vêm do servidor — o cliente não conta EPIs', () {
    test('critical_stock é o número recebido, não uma contagem local',
        () async {
      final servidor = _Servidor((_, __, ___) => _payload(
            unitId: 2,
            unitScopeSource: 'selected',
            criticalStock: 5,
            nearMinimumStock: 3,
            deliveriesToday: 12,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.criticalStock, 5);
      expect(cubit.state.nearMinimumStock, 3);
      expect(cubit.state.deliveriesToday, 12);
      // Nenhuma lista de EPIs entrou no cubit: não há o que recontar.
      expect(servidor.chamadas, hasLength(1));
    });

    test('sem Unidade resolvida o KPI é null, e não 0', () async {
      // `0` afirmaria "nenhum EPI crítico". `null` diz "a pergunta não se
      // aplica: nenhuma Unidade foi escolhida".
      final servidor = _Servidor((_, __, ___) => _payload(
            criticalStock: null,
            nearMinimumStock: null,
            deliveriesToday: 4,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.criticalStock, isNull);
      expect(cubit.state.nearMinimumStock, isNull);
      expect(cubit.state.criticalStock, isNot(0));
      expect(cubit.state.deliveriesToday, 4);
    });

    test('zero recebido é preservado como zero', () async {
      final servidor = _Servidor((_, __, ___) => _payload(
            unitId: 2,
            unitScopeSource: 'selected',
            criticalStock: 0,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.criticalStock, 0);
      expect(cubit.state.criticalStock, isNotNull);
    });
  });

  group('cascata — o cliente pede, o servidor recorta', () {
    test('trocar de CNPJ pede sem unidade e sem setor', () async {
      final servidor = _Servidor((cnpj, unidade, setor) => _payload(
            legalEntityId: cnpj,
            unitId: unidade,
            sector: setor,
            units: _unidades,
            legalEntities: _cnpjs,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);
      await cubit.load();

      cubit.selectLegalEntity(20);
      await Future<void>.delayed(Duration.zero);

      // A unidade 2 pertence ao CNPJ 10; carregá-la junto do CNPJ 20 produziria
      // um recorte incoerente.
      expect(servidor.chamadas.last.legalEntityId, 20);
      expect(servidor.chamadas.last.unitId, isNull);
      expect(servidor.chamadas.last.sector, isNull);
      expect(cubit.state.selectedLegalEntityId, 20);
    });

    test('trocar de unidade preserva o CNPJ e limpa o setor', () async {
      final servidor = _Servidor((cnpj, unidade, setor) => _payload(
            legalEntityId: cnpj,
            unitId: unidade,
            sector: setor,
            unitScopeSource: unidade == null ? 'none' : 'selected',
            units: _unidades,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);
      await cubit.load();
      cubit.selectLegalEntity(10);
      await Future<void>.delayed(Duration.zero);

      cubit.selectUnit(2);
      await Future<void>.delayed(Duration.zero);

      expect(servidor.chamadas.last.legalEntityId, 10);
      expect(servidor.chamadas.last.unitId, 2);
      expect(servidor.chamadas.last.sector, isNull);
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.scope.unitScopeSource, 'selected');
    });

    test('selecionar setor preserva CNPJ e unidade', () async {
      final servidor = _Servidor((cnpj, unidade, setor) => _payload(
            legalEntityId: cnpj,
            unitId: unidade,
            sector: setor,
            units: _unidades,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);
      await cubit.load();
      cubit.selectLegalEntity(10);
      await Future<void>.delayed(Duration.zero);
      cubit.selectUnit(2);
      await Future<void>.delayed(Duration.zero);

      cubit.selectSector('Convés');
      await Future<void>.delayed(Duration.zero);

      expect(servidor.chamadas.last.legalEntityId, 10);
      expect(servidor.chamadas.last.unitId, 2);
      expect(servidor.chamadas.last.sector, 'Convés');
    });

    test('clearFilters pede o recorte vazio', () async {
      final servidor = _Servidor((cnpj, unidade, setor) => _payload(
            legalEntityId: cnpj,
            unitId: unidade,
            sector: setor,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);
      await cubit.load();
      cubit.selectLegalEntity(10);
      await Future<void>.delayed(Duration.zero);

      cubit.clearFilters();
      await Future<void>.delayed(Duration.zero);

      expect(servidor.chamadas.last.legalEntityId, isNull);
      expect(servidor.chamadas.last.unitId, isNull);
      expect(servidor.chamadas.last.sector, isNull);
      expect(cubit.state.hasActiveFilter, isFalse);
    });
  });

  group('perfil travado — a trava vem do servidor', () {
    // Achado no dashboard real (web): Gestor de EPI via "Todos" nos filtros e
    // os KPIs somavam a empresa inteira. A regra é do backend
    // (`resolve_unit_scope`); o cliente exibe `scope.locked` e a Unidade que
    // voltou, sem deduzir nada do papel da sessão.
    test('o escopo devolvido prevalece sobre o que o cliente pediu', () async {
      // Perfil travado na Unidade 2: o servidor ignora o pedido de CNPJ 20 /
      // Unidade 3 e devolve a Unidade do ator.
      final servidor = _Servidor((_, __, ___) => _payload(
            unitId: 2,
            unitScopeSource: 'actor',
            locked: true,
            legalEntityId: 10,
            criticalStock: 4,
            units: const [
              {'id': 2, 'name': 'Base Santos', 'legal_entity_id': 10},
            ],
            legalEntities: _cnpjs,
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);
      await cubit.load();

      expect(cubit.state.isLocked, isTrue);
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.selectedLegalEntityId, 10);
      expect(cubit.state.scope.unitScopeSource, 'actor');
      // Mesmo pedindo outro recorte, o estado continua o da própria Unidade.
      cubit.selectUnit(3);
      await Future<void>.delayed(Duration.zero);
      expect(cubit.state.selectedUnitId, 2);
      expect(cubit.state.isLocked, isTrue);
      // E a lista de Unidades já vem restrita à dele.
      expect(cubit.state.units.map((u) => u.id), [2]);
    });

    test('perfil livre não nasce travado', () async {
      final servidor = _Servidor((_, __, ___) => _payload(units: _unidades));
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.isLocked, isFalse);
      expect(cubit.state.selectedUnitId, isNull);
      expect(cubit.state.units, hasLength(3));
    });

    test('o cubit não recebe papel nem unidade do ator', () {
      // A assinatura é a garantia estrutural: sem `role` e sem
      // `operationalUnitId` não há como reimplementar a trava em Dart.
      expect(DashboardCubit().state.isLocked, isFalse);
    });
  });

  group('setores', () {
    test('vêm de filters.sectors, não de uma varredura de colaboradores',
        () async {
      final servidor = _Servidor((_, __, ___) => _payload(
            unitId: 2,
            unitScopeSource: 'selected',
            sectors: const ['Convés', 'Máquinas'],
          ));
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.sectors, ['Convés', 'Máquinas']);
    });

    test('lista vazia do servidor é lista vazia na tela', () async {
      final servidor = _Servidor((_, __, ___) => _payload());
      final cubit = DashboardCubit(loader: servidor.carregar);

      await cubit.load();

      expect(cubit.state.sectors, isEmpty);
    });
  });

  group('falha de rede', () {
    test('erro vira mensagem e some na consulta seguinte', () async {
      var falhar = true;
      final cubit = DashboardCubit(loader: ({
        int? legalEntityId,
        int? unitId,
        String? sector,
      }) async {
        if (falhar) throw Exception('sem rede');
        return DashboardSummary.fromJson(_payload(criticalStock: 1));
      });

      await cubit.load();
      expect(cubit.state.error, contains('sem rede'));
      expect(cubit.state.isLoading, isFalse);

      falhar = false;
      await cubit.load();
      expect(cubit.state.error, isNull);
      expect(cubit.state.criticalStock, 1);
    });
  });
}
