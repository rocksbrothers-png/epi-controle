/// Resumo do Dashboard, já **recortado e calculado pelo servidor**
/// (`GET /api/dashboard/summary`, fatia 1.1D-B).
///
/// Substitui o que o `DashboardCubit` fazia baixando `/api/bootstrap` inteiro e
/// recomputando tudo em Dart: o recorte por CNPJ/Unidade/Setor, os quatro KPIs,
/// a dedução de perfil travado e a varredura de `bootstrap.employees` só para
/// preencher o dropdown de setores.
///
/// Nada aqui é recalculado no cliente. O modelo existe para **transportar** a
/// decisão do servidor até a tela.
library;

/// Contexto de Unidade resolvido pelo servidor.
class DashboardScope {
  const DashboardScope({
    this.unitId,
    this.unitScopeSource = 'none',
    this.locked = false,
    this.companyId,
    this.legalEntityId,
    this.sector,
  });

  /// Unidade efetiva. `null` quando o perfil é livre e não selecionou nenhuma.
  final int? unitId;

  /// Por que o recorte é o que é: `actor` (perfil travado, veio do vínculo do
  /// ator), `selected` (perfil livre escolheu) ou `none` (visão corporativa).
  final String unitScopeSource;

  /// Se o perfil é travado numa única Unidade.
  ///
  /// **Vem do servidor.** Antes o cliente deduzia com
  /// `role == 'admin' || role == 'user'` — autorização espelhada em Dart e em
  /// JS, que envelhece separada do backend.
  final bool locked;

  final int? companyId;
  final int? legalEntityId;
  final String? sector;

  factory DashboardScope.fromJson(Map<String, dynamic> json) => DashboardScope(
        unitId: (json['unit_id'] as num?)?.toInt(),
        unitScopeSource: json['unit_scope_source'] as String? ?? 'none',
        locked: json['locked'] as bool? ?? false,
        companyId: (json['company_id'] as num?)?.toInt(),
        legalEntityId: (json['legal_entity_id'] as num?)?.toInt(),
        sector: json['sector'] as String?,
      );
}

/// Os KPIs do painel.
///
/// `criticalStock` e `nearMinimumStock` são `null` — e não `0` — quando não há
/// Unidade resolvida. Zero afirmaria "nenhum EPI crítico"; `null` diz "a
/// pergunta não se aplica, porque nenhuma Unidade foi escolhida".
///
/// Os dois contam por `stock_status`, então **EPI com alerta desabilitado não
/// entra em nenhum deles** — nem mesmo quando `underlyingStatus` é `critical`.
class DashboardKpis {
  const DashboardKpis({
    this.deliveriesToday = 0,
    this.expiringEpis = 0,
    this.criticalStock,
    this.nearMinimumStock,
    this.pendingPurchases = 0,
  });

  final int deliveriesToday;
  final int expiringEpis;
  final int? criticalStock;
  final int? nearMinimumStock;
  final int pendingPurchases;

  factory DashboardKpis.fromJson(Map<String, dynamic> json) => DashboardKpis(
        deliveriesToday: (json['deliveries_today'] as num?)?.toInt() ?? 0,
        expiringEpis: (json['expiring_epis'] as num?)?.toInt() ?? 0,
        criticalStock: (json['critical_stock'] as num?)?.toInt(),
        nearMinimumStock: (json['near_minimum_stock'] as num?)?.toInt(),
        pendingPurchases: (json['pending_purchases'] as num?)?.toInt() ?? 0,
      );
}

/// Uma opção do filtro em cascata (CNPJ ou Unidade).
class DashboardFilterOption {
  const DashboardFilterOption({
    required this.id,
    required this.name,
    this.legalEntityId,
  });

  final int? id;
  final String name;

  /// Só para Unidades: o CNPJ a que ela pertence, que é o elo da cascata.
  final int? legalEntityId;

  factory DashboardFilterOption.fromJson(Map<String, dynamic> json) =>
      DashboardFilterOption(
        id: (json['id'] as num?)?.toInt(),
        name: json['name'] as String? ?? '',
        legalEntityId: (json['legal_entity_id'] as num?)?.toInt(),
      );
}

/// Fontes do filtro, **já escopadas por tenant, papel e contexto**.
///
/// Perfil travado recebe apenas o próprio CNPJ e a própria Unidade: a trava é
/// um fato da resposta, não uma regra reimplementada nos dois clientes.
class DashboardFilters {
  const DashboardFilters({
    this.legalEntities = const [],
    this.units = const [],
    this.sectors = const [],
  });

  final List<DashboardFilterOption> legalEntities;
  final List<DashboardFilterOption> units;
  final List<String> sectors;

  /// Unidades exibíveis para um CNPJ selecionado. Sem seleção, todas.
  List<DashboardFilterOption> unitsFor(int? legalEntityId) {
    if (legalEntityId == null) return units;
    return units
        .where((u) => u.legalEntityId == legalEntityId)
        .toList(growable: false);
  }

  static List<DashboardFilterOption> _opcoes(Object? bruto) =>
      ((bruto as List<dynamic>?) ?? const [])
          .map((e) => DashboardFilterOption.fromJson(e as Map<String, dynamic>))
          .toList(growable: false);

  factory DashboardFilters.fromJson(Map<String, dynamic> json) =>
      DashboardFilters(
        legalEntities: _opcoes(json['legal_entities']),
        units: _opcoes(json['units']),
        sectors: ((json['sectors'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(growable: false),
      );
}

class DashboardSummary {
  const DashboardSummary({
    this.scope = const DashboardScope(),
    this.kpis = const DashboardKpis(),
    this.filters = const DashboardFilters(),
    this.alerts = const [],
    this.compliance = const {},
  });

  final DashboardScope scope;
  final DashboardKpis kpis;
  final DashboardFilters filters;

  /// Alertas operacionais, com a regra do backend. Repassados sem interpretação.
  final List<Map<String, dynamic>> alerts;

  /// Resumo de conformidade de estoque por categoria.
  final Map<String, int> compliance;

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    final conformidade = json['compliance'];
    final resumo = conformidade is Map ? conformidade['summary'] : null;
    return DashboardSummary(
      scope: DashboardScope.fromJson(
        (json['scope'] as Map<String, dynamic>?) ?? const {},
      ),
      kpis: DashboardKpis.fromJson(
        (json['kpis'] as Map<String, dynamic>?) ?? const {},
      ),
      filters: DashboardFilters.fromJson(
        (json['filters'] as Map<String, dynamic>?) ?? const {},
      ),
      alerts: ((json['alerts'] as List<dynamic>?) ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(growable: false),
      compliance: resumo is Map
          ? resumo.map(
              (k, v) => MapEntry(
                '$k',
                v is int ? v : int.tryParse('$v') ?? 0,
              ),
            )
          : const {},
    );
  }
}
