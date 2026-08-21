import 'package:dio/dio.dart';

import '../models/epi.dart';
import '../models/stock_item.dart';

/// Itens de estoque bloqueados, agrupados pelas chaves de status do backend.
///
/// O backend devolve, junto dos itens, um mapa `statuses` com rótulos em
/// português. Guardamos apenas as CHAVES: o rótulo exibido vem do ARB, senão o
/// app falaria português nos outros quatro idiomas. As chaves desconhecidas
/// são preservadas para a UI poder mostrar algo em vez de esconder o item.
class BlockedStockItems {
  const BlockedStockItems({required this.items, required this.statusKeys});

  final List<StockItem> items;
  final List<String> statusKeys;
}

class StockApi {
  const StockApi(this._dio);
  final Dio _dio;

  /// Lê uma data a partir de uma imagem (OCR), reaproveitado para capturar a
  /// validade do fabricante na conferência de recebimento. Recebe a imagem como
  /// data URL ou base64 e retorna 'YYYY-MM-DD' (ou '' se não identificada).
  Future<String> detectDateFromImage({
    required int actorUserId,
    required String imageData,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/stock/manufacture-date-ocr',
      data: {'actor_user_id': actorUserId, 'image_data': imageData},
    );
    return (res.data?['manufacture_date'] as String?)?.trim() ?? '';
  }

  /// Fonte ÚNICA de conformidade de estoque (item 2): a mesma base do Dashboard
  /// e da tela "Validade e Bloqueios". Retorna `summary` (contagens por
  /// categoria: ca_expired, ca_expiring, product_expired, product_expiring,
  /// missing_manufacture, missing_lot, admin_blocked) e `categories` (registros
  /// para o deep-link). A REGRA é do backend — o cliente só consome o contrato.
  /// GET /api/stock/compliance.
  Future<Map<String, dynamic>> getStockCompliance({
    required int actorUserId,
    int? companyId,
    int? unitId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/compliance',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (companyId != null) 'company_id': companyId,
        if (unitId != null) 'unit_id': unitId,
      },
    );
    return res.data ?? {};
  }

  /// EPIs visíveis para a unidade do ator, com saldo da unidade E saldo
  /// corporativo em campos SEPARADOS.
  ///
  /// Fonte única de estoque (#258): substitui `bootstrap.epis`, que trazia
  /// apenas o total da empresa e envelhecia durante a sessão. Aqui a
  /// visibilidade GLOBAL/JV é reavaliada a cada consulta e os filtros são
  /// aplicados no servidor — o cliente não refaz nenhuma das duas coisas.
  ///
  /// Sem `company_id`/`unit_id`: o escopo vem do ator. `unitStockQuantity` é
  /// `null` quando não há unidade resolvida.
  Future<List<Epi>> fetchStockEpis({
    required int actorUserId,
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/epis',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (name != null && name.isNotEmpty) 'name': name,
        if (section != null && section.isNotEmpty) 'section': section,
        if (manufacturer != null && manufacturer.isNotEmpty)
          'manufacturer': manufacturer,
        if (ca != null && ca.isNotEmpty) 'ca': ca,
        if (protection != null && protection.isNotEmpty) 'protection': protection,
      },
    );
    final items = (res.data?['items'] as List<dynamic>?) ?? const [];
    return items.map((e) => Epi.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// QRs disponíveis de um EPI na unidade do ator, já em ordem FEFO (o lote que
  /// vence primeiro sai primeiro). A ordenação é do backend — o cliente não
  /// reordena, senão duplicaria a regra.
  ///
  /// **Não recebe `company_id` nem `unit_id`.** O backend deriva os dois do
  /// ator: para perfis de empresa o `company_id` do cliente é ignorado, e
  /// `admin`/`user` ficam presos à própria unidade operacional. Mandar esses
  /// campos daqui moveria autorização para a tela.
  /// GET /api/stock/available-items.
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/available-items',
      queryParameters: {'actor_user_id': actorUserId, 'epi_id': epiId},
    );
    final items = (res.data?['items'] as List<dynamic>?) ?? const [];
    return items
        .map((e) => StockItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // ── Escopo por Unidade do COLABORADOR (fluxo de entrega, #278) ───────────
  //
  // Os três métodos abaixo mandam `unit_id`, e os de cima não. A diferença não
  // é inconsistência: é de onde a Unidade vem em cada fluxo.
  //
  // Na tela de estoque, a Unidade é a do ATOR e o servidor a deriva sozinho —
  // mandá-la de lá moveria autorização para a tela. Na entrega, a Unidade é a
  // do COLABORADOR que vai receber o EPI (`current_unit_id`, já resolvido pelo
  // backend com movimentação temporária vigente). Ela pode ser diferente da do
  // ator — um Administrador Geral entrega para alguém de qualquer Unidade da
  // empresa —, então precisa ser transportada.
  //
  // Transportar não é decidir: `resolve_unit_scope` valida a Unidade contra a
  // empresa do ator e, para perfil travado, ignora o pedido e devolve a própria
  // Unidade. E a entrega revalida tudo de novo antes de baixar o item.

  /// EPIs com saldo NA UNIDADE informada, para o passo de EPI da entrega.
  ///
  /// `unitStockQuantity` vem preenchido porque a Unidade está resolvida. O
  /// saldo corporativo continua em campo separado e **não governa nada** aqui.
  Future<List<Epi>> fetchUnitStockEpis({
    required int actorUserId,
    required int unitId,
    String? name,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/epis',
      queryParameters: {
        'actor_user_id': actorUserId,
        'unit_id': unitId,
        if (name != null && name.isNotEmpty) 'name': name,
      },
    );
    final items = (res.data?['items'] as List<dynamic>?) ?? const [];
    return items.map((e) => Epi.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Itens físicos `in_stock` de um EPI NA UNIDADE informada, em ordem FEFO.
  ///
  /// É a lista de onde sai o `stock_item_id` REAL da entrega. Sem ela o cliente
  /// não tem como nomear a unidade etiquetada que está sendo entregue — e o
  /// backend, que exige uma linha de `epi_stock_items`, recusa.
  Future<List<StockItem>> fetchUnitAvailableItems({
    required int actorUserId,
    required int unitId,
    required int epiId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/available-items',
      queryParameters: {
        'actor_user_id': actorUserId,
        'unit_id': unitId,
        'epi_id': epiId,
      },
    );
    final items = (res.data?['items'] as List<dynamic>?) ?? const [];
    return items
        .map((e) => StockItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Resolve um QR lido no item físico correspondente DENTRO da Unidade.
  ///
  /// O backend só encontra o item se ele estiver naquela Unidade e naquela
  /// empresa (`lookup_stock_item_by_qr`), então um QR de outra Unidade não
  /// resolve — a recusa vem de lá, não de uma checagem da tela.
  /// GET /api/stock/lookup-qr.
  Future<StockItem> lookupQr({
    required int actorUserId,
    required int unitId,
    required String qrCode,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/lookup-qr',
      queryParameters: {
        'actor_user_id': actorUserId,
        'unit_id': unitId,
        'qr_code': qrCode,
      },
    );
    final item = res.data?['stock_item'];
    if (item is! Map<String, dynamic>) {
      throw StateError('QR sem item correspondente no estoque da Unidade.');
    }
    return StockItem.fromJson(item);
  }

  /// Itens bloqueados da empresa do ator (vencidos, aguardando descarte ou
  /// devolução, em análise, reprovados, de EPI arquivado).
  ///
  /// Mesma regra de escopo do método acima: nada de `company_id` a partir da
  /// UI. `admin`/`user` recebem apenas a própria unidade — a restrição é
  /// aplicada no servidor, não escondida na tela.
  /// GET /api/stock/blocked-items.
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/stock/blocked-items',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final items = (res.data?['items'] as List<dynamic>?) ?? const [];
    final statuses = (res.data?['statuses'] as Map<String, dynamic>?) ?? const {};
    return BlockedStockItems(
      items: items
          .map((e) => StockItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      statusKeys: statuses.keys.toList(),
    );
  }

  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType, // 'in' or 'out'
    required int quantity,
  }) async {
    await _dio.post<void>(
      '/api/stock/movements',
      data: {
        'actor_user_id': actorUserId,
        'company_id': companyId,
        'unit_id': unitId,
        'epi_id': epiId,
        'movement_type': movementType,
        'quantity': quantity,
        'label_measure': '',
        'label_printer_name': '',
        'label_print_format': '',
        'manufacture_date': '',
      },
    );
  }
}
