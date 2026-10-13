import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_admin/features/stock/domain/repositories/stock_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// EST-V3.5-R2 (F4) — fluxo Cubit→Repository da regularização de validade física.
///
/// O que estes testes protegem, em três frases:
///
/// - **a classificação é do backend** — o cubit repassa o `RegularizationResult`
///   sem reinterpretar, inclusive o bloqueio por vencimento (`blockedExpired`);
/// - **o ator vem da SESSÃO** — resolvido na camada de dados, nunca 0, mesmo sem
///   um `load()` anterior;
/// - **após regularizar, os fatos físicos são relidos** — o cubit chama `load()`
///   para que contadores, pendentes e elegibilidade reflitam o novo estado.
class _FakeRepo implements StockRepository {
  _FakeRepo(
    this.result, {
    this.actorUserId = 5,
    this.episSequence = const <List<Epi>>[],
  });

  final RegularizationResult result;
  final int actorUserId;

  /// Retornos sucessivos de `fetchStockEpis`: o 1º para o `load()` inicial, o 2º
  /// para o `load()` que a própria regularização dispara. Sequências diferentes
  /// provam que houve releitura, e não um estado cacheado.
  final List<List<Epi>> episSequence;

  int fetchCalls = 0;
  int regularizeCalls = 0;
  int? lastActorUserId;
  int? lastCompanyId;
  int? lastStockItemId;
  String? lastQrCode;
  String? lastPhysicalExpiryDate;
  String? lastEvidence;
  String? lastJustification;

  @override
  Future<int> currentActorUserId() async => actorUserId;

  @override
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) async {
    final list = episSequence.isEmpty
        ? const <Epi>[]
        : episSequence[fetchCalls < episSequence.length
              ? fetchCalls
              : episSequence.length - 1];
    fetchCalls++;
    return list;
  }

  @override
  Future<RegularizationResult> regularizeValidity({
    required int actorUserId,
    required int companyId,
    int stockItemId = 0,
    required String qrCode,
    required String physicalExpiryDate,
    required String evidence,
    required String justification,
  }) async {
    regularizeCalls++;
    lastActorUserId = actorUserId;
    lastCompanyId = companyId;
    lastStockItemId = stockItemId;
    lastQrCode = qrCode;
    lastPhysicalExpiryDate = physicalExpiryDate;
    lastEvidence = evidence;
    lastJustification = justification;
    return result;
  }

  // Métodos não exercidos aqui: lançar é melhor que devolver vazio, que passaria
  // despercebido se alguém escrevesse o caso errado contra este fake.
  @override
  // ignore: deprecated_member_use_from_same_package
  Future<StockSnapshot> fetchStock() => throw UnimplementedError();

  @override
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) => throw UnimplementedError();

  @override
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) =>
      throw UnimplementedError();

  @override
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  }) async {}
}

Epi _epi(int id, String name) => Epi(
  id: id,
  name: name,
  companyId: 3,
  unitScopeId: 10,
  unitStockQuantity: 4,
  companyStockQuantity: 9,
  minimumStock: 1,
);

RegularizationResult _result({
  required bool eligible,
  required bool blockedExpired,
  String status = 'in_stock',
  String validityStatus = 'valid',
  bool idempotent = false,
}) => RegularizationResult(
  status: status,
  validityStatus: validityStatus,
  physicalExpiryDate: '2030-01-01',
  eligible: eligible,
  blockedExpired: blockedExpired,
  idempotent: idempotent,
  message: 'backend',
);

void main() {
  group('StockCubit.regularizeValidity (EST-V3.5-R2)', () {
    test('repassa o resultado do backend e carimba os campos enviados',
        () async {
      final repo = _FakeRepo(
        _result(eligible: true, blockedExpired: false),
        episSequence: const [],
      );
      final cubit = StockCubit(repository: repo);
      await cubit.load();

      final result = await cubit.regularizeValidity(
        companyId: 3,
        qrCode: 'QR-123',
        physicalExpiryDate: '2030-01-01',
        evidence: 'NF 456 / foto etiqueta',
        justification: 'Etiqueta legível conferida no recebimento',
      );

      // A classificação é do backend — o cubit devolve o que recebeu.
      expect(result.eligible, isTrue);
      expect(result.blockedExpired, isFalse);
      expect(result.validityStatus, 'valid');
      // Os campos atravessam íntegros até o repositório.
      expect(repo.regularizeCalls, 1);
      expect(repo.lastCompanyId, 3);
      expect(repo.lastQrCode, 'QR-123');
      expect(repo.lastPhysicalExpiryDate, '2030-01-01');
      expect(repo.lastEvidence, 'NF 456 / foto etiqueta');
      expect(repo.lastJustification, 'Etiqueta legível conferida no recebimento');
      // Sem reforço de id: a identificação inequívoca é o QR.
      expect(repo.lastStockItemId, 0);
    });

    test('bloqueio por vencimento é repassado sem reinterpretação', () async {
      // Regularizar uma peça já vencida NÃO a torna elegível: o backend devolve
      // blocked_expired, e a UI deve exibir exatamente isso.
      final repo = _FakeRepo(
        _result(
          eligible: false,
          blockedExpired: true,
          status: 'blocked_expired',
          validityStatus: 'expired',
        ),
      );
      final cubit = StockCubit(repository: repo);
      await cubit.load();

      final result = await cubit.regularizeValidity(
        companyId: 3,
        qrCode: 'QR-VENC',
        physicalExpiryDate: '2000-01-01',
        evidence: 'documento',
        justification: 'validade comprovada já vencida',
      );

      expect(result.blockedExpired, isTrue);
      expect(result.eligible, isFalse);
      expect(result.status, 'blocked_expired');
    });

    test('após regularizar, relê os fatos físicos (load)', () async {
      // 1º load devolve 1 EPI; o load disparado pela regularização devolve 2.
      // Se o estado terminasse com 1, a releitura não teria acontecido.
      final repo = _FakeRepo(
        _result(eligible: true, blockedExpired: false),
        episSequence: [
          [_epi(1, 'Capacete')],
          [_epi(1, 'Capacete'), _epi(2, 'Luva')],
        ],
      );
      final cubit = StockCubit(repository: repo);
      await cubit.load();
      expect(cubit.state.epis, hasLength(1));

      await cubit.regularizeValidity(
        companyId: 3,
        qrCode: 'QR-1',
        physicalExpiryDate: '2030-01-01',
        evidence: 'ev',
        justification: 'just',
      );

      expect(repo.regularizeCalls, 1);
      expect(cubit.state.epis, hasLength(2), reason: 'load() correu de novo');
    });

    test('o ator é resolvido da sessão mesmo sem load() anterior', () async {
      // Sem load() antes, state.actorUserId é 0; _actor() resolve pela camada de
      // dados. Carimbar 0 faria o backend recusar — o mesmo defeito das consultas.
      final repo = _FakeRepo(
        _result(eligible: true, blockedExpired: false),
        actorUserId: 99,
      );
      final cubit = StockCubit(repository: repo);

      await cubit.regularizeValidity(
        companyId: 3,
        qrCode: 'QR-9',
        physicalExpiryDate: '2030-01-01',
        evidence: 'ev',
        justification: 'just',
      );

      expect(repo.lastActorUserId, 99);
    });
  });
}
