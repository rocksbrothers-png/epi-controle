/// Saldo por grade (tamanho) de um EPI numa unidade.
///
/// Vem de `fetch_epi_size_balance`, que agrupa `epi_stock_items` por
/// glove_size/size/uniform_size. O backend usa `'N/A'` como marcador de grade
/// ausente — o cliente não exibe esse marcador ao operador.
class EpiSizeBalance {
  const EpiSizeBalance({
    required this.quantity,
    this.gloveSize,
    this.size,
    this.uniformSize,
  });

  final int quantity;
  final String? gloveSize;
  final String? size;
  final String? uniformSize;

  /// Grade efetiva: a primeira preenchida, ignorando o `'N/A'` do backend.
  String? get displaySize {
    for (final valor in [gloveSize, size, uniformSize]) {
      final texto = valor?.trim();
      if (texto != null && texto.isNotEmpty && texto != 'N/A') return texto;
    }
    return null;
  }

  static String? _texto(Object? valor) {
    final texto = valor?.toString().trim();
    return (texto == null || texto.isEmpty) ? null : texto;
  }

  factory EpiSizeBalance.fromJson(Map<String, dynamic> json) => EpiSizeBalance(
        quantity: (json['quantity'] as num?)?.toInt() ?? 0,
        gloveSize: _texto(json['glove_size']),
        size: _texto(json['size']),
        uniformSize: _texto(json['uniform_size']),
      );
}

class Epi {
  const Epi({
    required this.id,
    required this.name,
    this.code,
    this.caNumber,
    this.caExpiryDate,
    this.manufacturerValidityDate,
    this.validityDays,
    this.stockQuantity = 0,
    this.minimumStock = 0,
    this.photoUrl,
    this.companyId,
    this.unitStockQuantity,
    this.companyStockQuantity,
    this.isCompanyStockCritical,
    this.unitScopeId,
    this.sizeBalances = const [],
    this.unitMinimumStock,
    this.minimumStockSource,
    this.effectiveAttentionPercentage,
    this.attentionPercentageSource,
    this.attentionLimit,
    this.stockAlertEnabled,
    this.alertSource,
    this.underlyingStatus,
    this.stockStatus,
    this.stockCondition,
  });

  final int id;
  final String name;
  final String? code;
  final String? caNumber;

  /// Validade do Certificado de Aprovação (CA). Relevante na compra/aquisição
  /// do EPI (NT 146/2015).
  final String? caExpiryDate;

  /// Validade do produto informada pelo fabricante. Relevante para o uso/entrega
  /// do EPI: após a aquisição com CA válido, é esta data — e não mais o CA — que
  /// rege se o EPI pode ser entregue ao trabalhador (NT 146/2015).
  final String? manufacturerValidityDate;

  final int? validityDays;
  final int stockQuantity;
  final int minimumStock;
  final String? photoUrl;

  /// Empresa dona do EPI. Vem de `/api/stock/epis`; ausente no bootstrap.
  final int? companyId;

  /// Saldo da **unidade** resolvida pelo servidor (`/api/stock/epis`).
  ///
  /// `null` quando não há unidade resolvida — perfil sem unidade fixa que não
  /// selecionou uma, ou payload que não carrega semântica de unidade (o
  /// bootstrap). `null` NÃO é zero: zero afirma "esta unidade não tem estoque",
  /// e null diz "não há unidade".
  final int? unitStockQuantity;

  /// Saldo **corporativo** — a soma sobre todas as unidades da empresa.
  final int? companyStockQuantity;

  /// Criticidade corporativa, calculada **no backend** comparando
  /// `companyStockQuantity` com `minimumStock`, ambos do mesmo escopo.
  ///
  /// O cliente não recalcula: `minimum_stock` vive em `epis`, na empresa, e
  /// compará-lo com o saldo de uma unidade marcaria como crítico todo EPI cujo
  /// estoque esteja distribuído. Mínimo por unidade é outra frente.
  final bool? isCompanyStockCritical;

  /// A unidade que o servidor usou para calcular `unitStockQuantity`.
  /// `null` exatamente quando `unitStockQuantity` é `null`.
  final int? unitScopeId;

  /// Grades por tamanho na unidade resolvida. Vazio quando não há unidade.
  final List<EpiSizeBalance> sizeBalances;

  // ── Classificação por Unidade (#271) ───────────────────────────────────────
  //
  // TODOS estes campos vêm calculados do backend, por
  // `classify_unit_epi_stock`. O cliente **não recalcula nenhum deles** — nem o
  // mínimo efetivo, nem o percentual, nem o limite da faixa, nem os status.
  //
  // São `null` JUNTOS quando não há unidade resolvida (bootstrap, ou perfil
  // livre sem seleção). `null` não é zero nem `normal`: é "a pergunta não se
  // aplica".

  /// Mínimo efetivo NAQUELA unidade — pode diferir de [minimumStock], que é o
  /// padrão da empresa.
  final int? unitMinimumStock;

  /// `unit_configured` quando a unidade definiu o próprio mínimo;
  /// `company_default` quando ainda herda o padrão da empresa.
  final String? minimumStockSource;

  /// Percentual da faixa de atenção efetivo naquela unidade.
  final int? effectiveAttentionPercentage;

  /// `unit_configured` ou `company_default`, como acima.
  final String? attentionPercentageSource;

  /// Teto da faixa de atenção: `ceil(mínimo × (1 + pct/100))`, já arredondado
  /// pelo servidor. Usar este valor — reproduzir a fórmula em Dart traria de
  /// volta a divergência de arredondamento entre `Decimal` e `double`.
  final int? attentionLimit;

  /// Se a unidade mantém o monitoramento deste EPI ligado.
  final bool? stockAlertEnabled;

  /// `unit_configured` quando a unidade decidiu explicitamente (ligar OU
  /// desligar); `system_default` quando nunca configurou. **Não** é
  /// `company_default`: não existe liga/desliga corporativo.
  final String? alertSource;

  /// Condição FÍSICA do estoque: `normal` | `near_minimum` | `critical`.
  ///
  /// Continua dizendo a verdade mesmo com o monitoramento desligado. É
  /// **informativo**: serve para explicar ao operador que o EPI *estaria*
  /// crítico. Nunca pode ser usado para recolocar um EPI `disabled` em KPI,
  /// alerta ou automação — para isso existe [stockStatus].
  final String? underlyingStatus;

  /// Estado OPERACIONAL: `normal` | `near_minimum` | `critical` | `disabled`.
  ///
  /// É a severidade oficial e única. KPIs, alertas e reposição automática
  /// consomem este campo.
  final String? stockStatus;

  /// Condição descritiva do saldo: `negative` | `zero` | `below_minimum` |
  /// `at_minimum` | `above_minimum`.
  ///
  /// **Não é severidade.** Descreve onde o saldo está; quem decide o que fazer
  /// é [stockStatus]. Substitui a escala legada `critical/danger/warning` do
  /// Web, que era uma classificação concorrente.
  final String? stockCondition;

  /// Saldo corporativo para exibição no catálogo da empresa.
  ///
  /// **Não é fallback entre escopos.** Os dois lados são o MESMO número: pelo
  /// contrato da fatia 1.1B, `stock` (legado) carrega o valor corporativo, e
  /// `company_stock_quantity` é esse valor com nome que diz de que escopo ele
  /// é. `stock` some na 1.1E; até lá, payloads antigos (bootstrap de backends
  /// anteriores, `/api/epis/{id}`) só têm o campo legado.
  ///
  /// `unitStockQuantity` nunca entra aqui. Saldo de unidade e saldo corporativo
  /// são grandezas diferentes, e misturá-las é exatamente o defeito que a 1.1B
  /// removeu.
  int get companyStock => companyStockQuantity ?? stockQuantity;

  // `isCriticalStock` (saldo <= mínimo) foi REMOVIDO na fatia 1.1D-C2 e não
  // deve voltar em nenhuma forma.
  //
  // Ele comparava dois números de escopos diferentes: `stockQuantity` é o saldo
  // corporativo e `minimumStock` passou a ser apenas o padrão corporativo
  // herdado — o mínimo que vale para o operador é `unitMinimumStock`, daquela
  // Unidade. Pior: a criticidade deixou de ser uma comparação. Ela depende do
  // mínimo efetivo, da faixa de atenção e de o monitoramento estar ligado, e um
  // EPI com alerta desligado é `disabled`, nunca `critical` — nada disso cabe
  // num operador `<=`.
  //
  // Quem precisa da criticidade lê o que o backend já decidiu:
  //   • `stockStatus` / `underlyingStatus` — por Unidade (`/api/stock/epis`);
  //   • `isCompanyStockCritical` — corporativa (bootstrap, catálogo).

  /// 'expired' | 'expiring' | 'valid' | null (sem data) para uma data ISO.
  static String? _dateStatus(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return null;
    final date = DateTime.tryParse(dateStr);
    if (date == null) return null;
    final now = DateTime.now();
    if (date.isBefore(now)) return 'expired';
    if (date.isBefore(now.add(const Duration(days: 30)))) return 'expiring';
    return 'valid';
  }

  static int? _daysUntil(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return null;
    final date = DateTime.tryParse(dateStr);
    if (date == null) return null;
    return date.difference(DateTime.now()).inDays;
  }

  /// 'expired' | 'expiring' | 'valid' | null (no CA date)
  String? get caStatus => _dateStatus(caExpiryDate);

  int? get daysUntilCaExpiry => _daysUntil(caExpiryDate);

  /// 'expired' | 'expiring' | 'valid' | null (sem data do fabricante)
  String? get manufacturerValidityStatus =>
      _dateStatus(manufacturerValidityDate);

  int? get daysUntilManufacturerValidity =>
      _daysUntil(manufacturerValidityDate);

  /// True quando o EPI não pode ser entregue por validade do fabricante vencida
  /// (NT 146/2015). CA vencido NÃO impede a entrega.
  bool get isBlockedForDelivery => manufacturerValidityStatus == 'expired';

  Epi copyWith({int? stockQuantity, int? unitStockQuantity}) => Epi(
        id: id,
        name: name,
        code: code,
        caNumber: caNumber,
        caExpiryDate: caExpiryDate,
        manufacturerValidityDate: manufacturerValidityDate,
        validityDays: validityDays,
        stockQuantity: stockQuantity ?? this.stockQuantity,
        minimumStock: minimumStock,
        photoUrl: photoUrl,
        companyId: companyId,
        unitStockQuantity: unitStockQuantity ?? this.unitStockQuantity,
        companyStockQuantity: companyStockQuantity,
        isCompanyStockCritical: isCompanyStockCritical,
        unitScopeId: unitScopeId,
        sizeBalances: sizeBalances,
        unitMinimumStock: unitMinimumStock,
        minimumStockSource: minimumStockSource,
        effectiveAttentionPercentage: effectiveAttentionPercentage,
        attentionPercentageSource: attentionPercentageSource,
        attentionLimit: attentionLimit,
        stockAlertEnabled: stockAlertEnabled,
        alertSource: alertSource,
        underlyingStatus: underlyingStatus,
        stockStatus: stockStatus,
        stockCondition: stockCondition,
      );

  factory Epi.fromJson(Map<String, dynamic> json) => Epi(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        // Aceita as chaves canônicas do backend e as legadas (compat.).
        code: (json['purchase_code'] ?? json['code']) as String?,
        caNumber: (json['ca'] ?? json['ca_number']) as String?,
        caExpiryDate: (json['ca_expiry'] ?? json['ca_expiry_date']) as String?,
        manufacturerValidityDate: (json['epi_validity_date'] ??
            json['manufacturer_validity_date']) as String?,
        validityDays: (json['validity_days'] as num?)?.toInt(),
        stockQuantity:
            ((json['stock'] ?? json['stock_quantity']) as num?)?.toInt() ?? 0,
        minimumStock: (json['minimum_stock'] as num?)?.toInt() ?? 0,
        photoUrl: (json['epi_photo_data'] ?? json['photo_url']) as String?,
        // Campos do contrato de /api/stock/epis. Ausentes no bootstrap, e por
        // isso anuláveis: um payload sem semântica de unidade não deve produzir
        // zero, que seria lido como "unidade sem estoque".
        companyId: (json['company_id'] as num?)?.toInt(),
        unitStockQuantity: (json['unit_stock_quantity'] as num?)?.toInt(),
        companyStockQuantity: (json['company_stock_quantity'] as num?)?.toInt(),
        isCompanyStockCritical: json['is_company_stock_critical'] as bool?,
        unitScopeId: (json['unit_scope_id'] as num?)?.toInt(),
        sizeBalances: ((json['size_balances'] as List<dynamic>?) ?? const [])
            .map((e) => EpiSizeBalance.fromJson(e as Map<String, dynamic>))
            .toList(),
        // Classificação por Unidade (#271). Anuláveis pelo mesmo motivo dos
        // campos acima: o bootstrap não carrega semântica de unidade.
        unitMinimumStock: (json['unit_minimum_stock'] as num?)?.toInt(),
        minimumStockSource: json['minimum_stock_source'] as String?,
        effectiveAttentionPercentage:
            (json['effective_attention_percentage'] as num?)?.toInt(),
        attentionPercentageSource: json['attention_percentage_source'] as String?,
        attentionLimit: (json['attention_limit'] as num?)?.toInt(),
        stockAlertEnabled: json['stock_alert_enabled'] as bool?,
        alertSource: json['alert_source'] as String?,
        underlyingStatus: json['underlying_status'] as String?,
        stockStatus: json['stock_status'] as String?,
        stockCondition: json['stock_condition'] as String?,
      );
}
