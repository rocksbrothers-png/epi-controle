/// As Unidades que o ator pode ESCOLHER, com o contexto do seletor.
///
/// Contrato de `GET /api/units/selectable`. **O servidor decide, o cliente
/// desenha.** Nenhum campo aqui é recalculado no Flutter, e nenhum estado é
/// inferido do tamanho da lista.
///
/// Por que não `bootstrap.units`: aquela lista é recortada por TENANT e mais
/// nada — um perfil travado recebe dela todas as Unidades da empresa. Quem a
/// consome precisa estreitá-la sozinho, e estreitar autorização no cliente é
/// exatamente o que não pode acontecer.
class SelectableUnits {
  const SelectableUnits({
    required this.units,
    required this.locked,
    required this.unitId,
    required this.source,
    required this.allowsAllUnits,
    required this.blocksEverything,
  });

  static const empty = SelectableUnits(
    units: <SelectableUnit>[],
    locked: false,
    unitId: null,
    source: '',
    allowsAllUnits: false,
    blocksEverything: false,
  );

  final List<SelectableUnit> units;

  /// Perfil travado (`admin`/`user`): não escolhe Unidade.
  final bool locked;

  /// A Unidade do ator quando [locked]. `null` para perfil livre sem seleção.
  final int? unitId;

  /// `actor` | `selected` | `purchase_scope` | `none`.
  ///
  /// `purchase_scope` e `none` têm ambos [unitId] nulo e significam coisas
  /// opostas: o primeiro é "a carteira do Comprador", o segundo é "a empresa
  /// inteira". Nunca tratar os dois como "sem Unidade".
  final String source;

  /// Se a opção "Todas as Unidades" pode ser oferecida.
  ///
  /// **Vem do backend e não é derivada de `units.length`.** Uma carteira com
  /// uma Unidade só tem lista não-vazia e mesmo assim não oferece "Todas";
  /// derivar do tamanho reconstruiria a regra aqui.
  final bool allowsAllUnits;

  /// Carteira existente e VAZIA — o ator não enxerga Unidade nenhuma.
  ///
  /// Distingue "você não tem Unidade atribuída" de "a empresa não tem
  /// Unidades", que são lista vazia pelos dois lados e pedem mensagens
  /// diferentes.
  final bool blocksEverything;

  bool get isEmpty => units.isEmpty;

  /// Só há o que escolher quando há mais de uma opção real.
  bool get hasChoice => units.length > 1 || allowsAllUnits;

  factory SelectableUnits.fromJson(Map<String, dynamic> json) => SelectableUnits(
        units: ((json['units'] as List<dynamic>?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SelectableUnit.fromJson)
            .toList(),
        locked: json['locked'] == true,
        unitId: (json['unit_id'] as num?)?.toInt(),
        source: (json['source'] as String?) ?? '',
        allowsAllUnits: json['allows_all_units'] == true,
        blocksEverything: json['blocks_everything'] == true,
      );
}

class SelectableUnit {
  const SelectableUnit({
    required this.id,
    required this.name,
    this.legalEntityId,
  });

  final int id;
  final String name;
  final int? legalEntityId;

  factory SelectableUnit.fromJson(Map<String, dynamic> json) => SelectableUnit(
        id: (json['id'] as num?)?.toInt() ?? 0,
        name: (json['name'] as String?) ?? '',
        legalEntityId: (json['legal_entity_id'] as num?)?.toInt(),
      );
}
