import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato de estoque do `Epi` (#258, fatia 1.1B).
///
/// O defeito que motivou esta fatia: `/api/stock/epis` devolvia um único campo
/// `stock` que às vezes era o saldo da unidade e às vezes o total da empresa —
/// o fallback era por *truthiness*, então uma unidade com saldo 0 recebia o
/// número da empresa inteira. O mesmo campo mudava de significado conforme o
/// valor, e a Entrega de EPI lia esse campo.
///
/// A correção separa as duas grandezas em campos próprios. Estes testes travam
/// a separação no lado do cliente: se alguém reintroduzir um "saldo único", ou
/// voltar a tratar `null` como zero, eles quebram.

/// Payload como o backend monta hoje em `handle_get_stock_epis`.
Map<String, dynamic> _payload({
  required int companyStock,
  int? unitStock,
  int? unitScopeId,
  int minimumStock = 10,
  bool isCritical = false,
  List<Map<String, dynamic>> sizeBalances = const [],
}) =>
    {
      'id': 1,
      'name': 'Capacete',
      'company_id': 7,
      'stock': companyStock,
      'company_stock_quantity': companyStock,
      'unit_stock_quantity': unitStock,
      'unit_scope_id': unitScopeId,
      'minimum_stock': minimumStock,
      'is_company_stock_critical': isCritical,
      'size_balances': sizeBalances,
    };

void main() {
  group('saldo da unidade × saldo corporativo', () {
    test('unidade com estoque > 0 não se confunde com o corporativo', () {
      final epi = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 50, unitScopeId: 10),
      );
      expect(epi.unitStockQuantity, 50);
      expect(epi.companyStockQuantity, 200);
      expect(epi.unitScopeId, 10);
    });

    test('unidade com estoque 0 permanece 0 — não cai no total da empresa', () {
      // ESTE é o caso do defeito. Com o fallback antigo (`or`), zero era falsy
      // e o cliente recebia 200: a unidade parecia ter estoque que não tem, e
      // a Entrega de EPI liberaria a operação.
      final epi = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 0, unitScopeId: 10),
      );
      expect(epi.unitStockQuantity, 0);
      expect(epi.companyStockQuantity, 200);
      expect(epi.unitStockQuantity, isNot(equals(epi.companyStockQuantity)));
    });

    test('`stock` legado carrega o valor CORPORATIVO nos dois casos', () {
      // Um só significado para `stock`, sempre: enquanto os consumidores
      // legados não migram, ele é o total da empresa — nunca o da unidade.
      final comSaldo = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 50, unitScopeId: 10),
      );
      final semSaldo = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 0, unitScopeId: 10),
      );
      expect(comSaldo.stockQuantity, 200);
      expect(semSaldo.stockQuantity, 200);
      expect(comSaldo.stockQuantity, comSaldo.companyStockQuantity);
      expect(semSaldo.stockQuantity, semSaldo.companyStockQuantity);
    });

    test('sem unidade resolvida o saldo local é null, não zero', () {
      // Zero afirmaria "esta unidade não tem estoque". Não há unidade: a tela
      // precisa poder dizer isso, e não exibir um saldo que ninguém apurou.
      final epi = Epi.fromJson(_payload(companyStock: 200));
      expect(epi.unitStockQuantity, isNull);
      expect(epi.unitScopeId, isNull);
      expect(epi.companyStockQuantity, 200);
    });

    test('unit_scope_id é null exatamente quando o saldo local é null', () {
      // Coerência do par. As combinações incoerentes existem só como defeito:
      // um escopo sem saldo, ou um saldo sem escopo, não têm leitura possível.
      final semUnidade = Epi.fromJson(_payload(companyStock: 200));
      expect(semUnidade.unitStockQuantity == null,
          semUnidade.unitScopeId == null);

      final comUnidade = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 0, unitScopeId: 10),
      );
      expect(comUnidade.unitStockQuantity == null,
          comUnidade.unitScopeId == null);
    });

    test('payload incoerente não é reinterpretado pelo cliente', () {
      // Se o backend algum dia mandar escopo sem saldo, o cliente NÃO inventa
      // zero para "consertar": preserva o que chegou, e o defeito aparece em
      // vez de ficar escondido atrás de um número plausível.
      final epi = Epi.fromJson(
        _payload(companyStock: 200, unitScopeId: 10),
      );
      expect(epi.unitStockQuantity, isNull);
      expect(epi.unitScopeId, 10);
    });
  });

  group('criticidade é do backend', () {
    test('a flag corporativa vem pronta e não é recalculada', () {
      // Mínimo 100, quatro unidades com 50 cada: a empresa tem 200 e está
      // saudável. Recalcular contra o saldo local daria crítico nas quatro.
      final epi = Epi.fromJson(_payload(
        companyStock: 200,
        unitStock: 50,
        unitScopeId: 10,
        minimumStock: 100,
        isCritical: false,
      ));
      expect(epi.isCompanyStockCritical, isFalse);
      expect(epi.unitStockQuantity! <= epi.minimumStock, isTrue,
          reason: 'a comparação local daria crítico — por isso não se usa');
    });

    test('empresa realmente abaixo do mínimo chega marcada', () {
      final epi = Epi.fromJson(_payload(
        companyStock: 80,
        unitStock: 80,
        unitScopeId: 10,
        minimumStock: 100,
        isCritical: true,
      ));
      expect(epi.isCompanyStockCritical, isTrue);
    });

    test('payload sem a flag deixa a criticidade indefinida, não falsa', () {
      // Bootstrap e rotas antigas não mandam o campo. `null` diz "não sei";
      // `false` afirmaria "está saudável" sobre um EPI que ninguém avaliou.
      final epi = Epi.fromJson({'id': 1, 'name': 'Capacete', 'stock': 3});
      expect(epi.isCompanyStockCritical, isNull);
    });
  });

  group('grades por tamanho', () {
    test('as grades da unidade chegam parseadas', () {
      final epi = Epi.fromJson(_payload(
        companyStock: 200,
        unitStock: 50,
        unitScopeId: 10,
        sizeBalances: [
          {'quantity': 30, 'glove_size': '8'},
          {'quantity': 20, 'size': 'N/A', 'uniform_size': 'M'},
        ],
      ));
      expect(epi.sizeBalances, hasLength(2));
      expect(epi.sizeBalances.first.quantity, 30);
      expect(epi.sizeBalances.first.displaySize, '8');
      // 'N/A' é marcador de grade ausente no backend, não um tamanho.
      expect(epi.sizeBalances.last.displaySize, 'M');
    });

    test('sem unidade não há grades', () {
      expect(Epi.fromJson(_payload(companyStock: 200)).sizeBalances, isEmpty);
    });
  });

  group('compatibilidade com payloads antigos', () {
    test('bootstrap continua parseável, sem semântica de unidade', () {
      // Enquanto a fatia 1.1E não remove `bootstrap.epis`, outros consumidores
      // ainda o desserializam com este mesmo modelo.
      final epi = Epi.fromJson({
        'id': 3,
        'name': 'Luva',
        'stock': 12,
        'minimum_stock': 5,
      });
      expect(epi.stockQuantity, 12);
      expect(epi.unitStockQuantity, isNull);
      expect(epi.companyStockQuantity, isNull);
      expect(epi.unitScopeId, isNull);
      expect(epi.companyId, isNull);
    });

    test('copyWith preserva os campos do novo contrato', () {
      // A atualização otimista do movimento passa por aqui: se copyWith
      // perdesse `unitScopeId`, a operação seguinte iria para outra unidade.
      final epi = Epi.fromJson(
        _payload(companyStock: 200, unitStock: 50, unitScopeId: 10,
            isCritical: true),
      );
      final movido = epi.copyWith(unitStockQuantity: 47);
      expect(movido.unitStockQuantity, 47);
      expect(movido.unitScopeId, 10);
      expect(movido.companyId, 7);
      expect(movido.companyStockQuantity, 200);
      expect(movido.isCompanyStockCritical, isTrue);
    });
  });

  group('acessor corporativo do catálogo (1.1C)', () {
    test('usa company_stock_quantity quando o backend o envia', () {
      final epi = Epi.fromJson(
        _payload(companyStock: 250, unitStock: 3, unitScopeId: 10),
      );
      expect(epi.companyStock, 250);
      expect(epi.companyStock, isNot(epi.unitStockQuantity));
    });

    test('saldo corporativo 0 permanece 0', () {
      // Zero é saldo, não ausência: `??` cobre só null. Com `||` o catálogo
      // trocaria o zero da empresa por outro número.
      final epi = Epi.fromJson(_payload(companyStock: 0, unitStock: 40,
          unitScopeId: 10));
      expect(epi.companyStock, 0);
    });

    test('payload antigo cai no campo legado, que também é corporativo', () {
      // Bootstrap de backend anterior, ou /api/epis/{id}: só tem `stock`.
      final epi = Epi.fromJson({'id': 1, 'name': 'Capacete', 'stock': 77});
      expect(epi.companyStock, 77);
      expect(epi.companyStockQuantity, isNull);
    });

    test('nunca devolve o saldo da unidade', () {
      // O caso que quebraria o catálogo: empresa zerada, unidade com peças.
      // Se o acessor caísse na unidade, o catálogo esconderia a ruptura.
      final epi = Epi.fromJson(
        _payload(companyStock: 0, unitStock: 40, unitScopeId: 10),
      );
      expect(epi.companyStock, 0);
      expect(epi.unitStockQuantity, 40);
    });
  });
}
