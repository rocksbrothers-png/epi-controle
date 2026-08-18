import 'package:dio/dio.dart';

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
