/// Os três parâmetros de estoque de um par `Unidade + EPI` (#271-B2-a).
///
/// Cada um é uma rota independente no backend e uma decisão independente do
/// usuário: gravar o mínimo não toca o percentual, e restaurar a herança de um
/// não restaura a do outro. São três tipos, e não um só com três campos, para
/// que uma resposta de `/api/stock/minimum` nunca possa ser atribuída ao bloco
/// da faixa de atenção por descuido de tipo.
///
/// **Nenhum deles é calculado no cliente.** O valor e a ORIGEM vêm prontos do
/// servidor. A origem é o que distingue "esta Unidade decidiu 20" de "esta
/// Unidade herdou 20" — mesmo número, estados opostos —, e deduzi-la a partir
/// da ação que o usuário acabou de executar perderia exatamente a distinção
/// que a fatia existe para preservar.
library;

/// Origem comum aos três parâmetros: a Unidade decidiu este valor.
const String kUnitEpiSourceUnit = 'unit_configured';

/// Origem do mínimo e do percentual quando a Unidade não decidiu: herda a
/// empresa.
const String kUnitEpiSourceCompany = 'company_default';

/// Origem do alerta quando a Unidade não decidiu. O alerta NÃO tem degrau
/// corporativo — pula direto para o padrão do sistema. Por isso o mínimo e o
/// percentual herdam `company_default` e ele herda `system_default`: são
/// hierarquias de altura diferente, e tratá-las como iguais mostraria uma
/// origem que não existe.
const String kUnitEpiSourceSystem = 'system_default';

/// Estoque mínimo daquele EPI naquela Unidade.
class UnitEpiMinimum {
  const UnitEpiMinimum({
    required this.unitId,
    required this.minimumStock,
    required this.source,
  });

  /// A Unidade que o servidor de fato usou. Para perfil travado ela pode
  /// DIFERIR da que o cliente mandou, porque `resolve_unit_scope` descarta o
  /// pedido e devolve a Unidade do ator. Conferir este campo contra o escopo
  /// corrente é como a tela descarta uma resposta que chegou tarde.
  final int unitId;

  final int minimumStock;
  final String source;

  /// A Unidade decidiu este valor — logo, há o que restaurar.
  bool get isUnitConfigured => source == kUnitEpiSourceUnit;

  factory UnitEpiMinimum.fromJson(Map<String, dynamic> json) => UnitEpiMinimum(
        unitId: (json['unit_id'] as num?)?.toInt() ?? 0,
        minimumStock: (json['minimum_stock'] as num?)?.toInt() ?? 0,
        source: (json['minimum_stock_source'] as String?) ?? '',
      );
}

/// Percentual da faixa de atenção daquele EPI naquela Unidade.
class UnitEpiAttention {
  const UnitEpiAttention({
    required this.unitId,
    required this.attentionPercentage,
    required this.source,
  });

  final int unitId;
  final int attentionPercentage;
  final String source;

  bool get isUnitConfigured => source == kUnitEpiSourceUnit;

  factory UnitEpiAttention.fromJson(Map<String, dynamic> json) =>
      UnitEpiAttention(
        unitId: (json['unit_id'] as num?)?.toInt() ?? 0,
        attentionPercentage:
            (json['attention_percentage'] as num?)?.toInt() ?? 0,
        source: (json['attention_percentage_source'] as String?) ?? '',
      );
}

/// Monitoramento de alerta daquele EPI naquela Unidade.
class UnitEpiAlert {
  const UnitEpiAlert({
    required this.unitId,
    required this.enabled,
    required this.source,
  });

  final int unitId;
  final bool enabled;
  final String source;

  bool get isUnitConfigured => source == kUnitEpiSourceUnit;

  factory UnitEpiAlert.fromJson(Map<String, dynamic> json) => UnitEpiAlert(
        unitId: (json['unit_id'] as num?)?.toInt() ?? 0,
        enabled: json['stock_alert_enabled'] == true,
        source: (json['alert_source'] as String?) ?? '',
      );
}
