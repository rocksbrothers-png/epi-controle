/// Item físico de estoque — uma unidade rastreada por QR em `epi_stock_items`.
///
/// Um modelo só para `/api/stock/available-items` e `/api/stock/blocked-items`:
/// as duas rotas leem a MESMA linha, e a de bloqueados apenas acrescenta
/// colunas (`lot_code`, `unit_measure`, `unit_name`, `unit_id`, `updated_at`).
/// Dois DTOs quase iguais divergiriam no primeiro campo que o backend mudasse
/// de um lado só — por isso os extras são anuláveis em vez de virarem uma
/// segunda classe.
///
/// `/api/stock/lookup-qr` devolve exatamente esta linha e deve reusar o modelo.
class StockItem {
  const StockItem({
    required this.id,
    required this.epiId,
    required this.epiName,
    required this.status,
    this.qrCodeValue,
    this.gloveSize,
    this.size,
    this.uniformSize,
    this.manufactureDate,
    this.epiValidityDate,
    this.lotCode,
    this.unitMeasure,
    this.unitName,
    this.unitId,
    this.updatedAt,
  });

  final int id;
  final int epiId;
  final String epiName;

  /// Chave de status vinda do backend (`in_stock`, `blocked_expired`,
  /// `blocked_discard`, …). É **chave**, não rótulo: o texto exibido vem do
  /// ARB. O backend também envia rótulos em português no mapa `statuses`, e
  /// usá-los quebraria o app nos outros quatro idiomas.
  final String status;

  final String? qrCodeValue;

  /// Grade do item. Só uma das três costuma vir preenchida, conforme o tipo de
  /// EPI (luva, calçado/vestuário, uniforme).
  final String? gloveSize;
  final String? size;
  final String? uniformSize;

  final String? manufactureDate;
  final String? epiValidityDate;

  // ── Só em /api/stock/blocked-items ────────────────────────────────────────
  final String? lotCode;
  final String? unitMeasure;
  final String? unitName;
  final int? unitId;
  final String? updatedAt;

  /// Grade efetiva para exibição — a primeira preenchida entre as três.
  /// `null` quando o EPI não tem grade, e a UI omite o campo.
  String? get displaySize {
    for (final value in [gloveSize, size, uniformSize]) {
      final trimmed = value?.trim();
      if (trimmed != null && trimmed.isNotEmpty && trimmed != 'N/A') {
        return trimmed;
      }
    }
    return null;
  }

  static String? _text(Object? value) {
    final text = value?.toString().trim();
    return (text == null || text.isEmpty) ? null : text;
  }

  factory StockItem.fromJson(Map<String, dynamic> json) => StockItem(
        id: (json['id'] as num?)?.toInt() ?? 0,
        epiId: (json['epi_id'] as num?)?.toInt() ?? 0,
        epiName: _text(json['epi_name']) ?? '',
        // `in_stock` é o default do próprio backend quando a coluna está nula
        // (COALESCE(LOWER(esi.status), 'in_stock')). Repetido aqui só para o
        // parsing não produzir status vazio — não é regra de negócio nova.
        status: _text(json['status']) ?? 'in_stock',
        qrCodeValue: _text(json['qr_code_value']),
        gloveSize: _text(json['glove_size']),
        size: _text(json['size']),
        uniformSize: _text(json['uniform_size']),
        manufactureDate: _text(json['manufacture_date']),
        epiValidityDate: _text(json['epi_validity_date']),
        lotCode: _text(json['lot_code']),
        unitMeasure: _text(json['unit_measure']),
        unitName: _text(json['unit_name']),
        unitId: (json['unit_id'] as num?)?.toInt(),
        updatedAt: _text(json['updated_at']),
      );
}
