/// Empresa terceirizada/prestadora — Cadastro Simplificado (ADR-0002).
///
/// NÃO é um tenant: não tem plano, login ou faturamento próprio — é uma
/// referência pequena, isolada por empresa (tenant), para a empresa externa
/// que empresta mão de obra (Terceirizada, Prestadora de Serviço, ou Outro).
/// Colaborador CLT nunca tem nenhuma referência a esta classe.
class OutsourcedCompany {
  const OutsourcedCompany({
    required this.id,
    required this.companyId,
    required this.legalName,
    this.tradeName = '',
    this.cnpj = '',
    this.companyKind = 'outsourced',
    this.epiResponsibility = 'Conforme Contrato',
    this.registrationMode = 'simplified',
    this.registrationStatus = 'pending_completion',
    this.status = 'Ativa',
    this.promotedAt = '',
    this.createdAt = '',
    this.unitId,
    this.localUnitLinkStatus,
    this.unitLinkId,
    this.originUnitName = '',
    this.linkedUnitsCount,
  });

  final int id;
  final int companyId;
  final String legalName;
  final String tradeName;
  final String cnpj;

  /// Unidade a que o cadastro está restrito. `null` = escopo de toda a
  /// empresa (tenant) — só quem tem permissão além do escopo de unidade
  /// (Administrador Geral etc.) pode deixar em branco; Administrador
  /// Local/Gestor de EPI são sempre forçados à própria unidade pelo backend
  /// (`resolve_outsourced_company_unit_id`), independentemente do que for
  /// enviado aqui.
  final int? unitId;

  // ── Vínculo da EMPRESA com a Unidade (ADR-0002 §12) ──────────────────────
  //
  // A empresa é única no tenant e pode ter vínculo com várias Unidades, cada
  // um com estado próprio — mesmo desenho de `employee_unit_links`, tabela
  // diferente (`outsourced_company_unit_links`).
  //
  // Duas assimetrias em relação ao colaborador que o cliente NÃO pode alisar:
  //
  // 1. O backend envia `local_status` aqui, e `local_unit_link_status` no
  //    colaborador. O nome Dart é o mesmo nos dois por conveniência de quem
  //    lê a UI; o mapeamento de JSON é que difere.
  // 2. "Não vinculada" NÃO chega como `'none'`. Chega como AUSÊNCIA do campo
  //    somada ao mascaramento dos dados operacionais — ver
  //    [isMaskedForLinking].

  /// `'active'` ou `'inactive'` quando o backend informou o vínculo desta
  /// Unidade; `null` quando não informou.
  ///
  /// `null` **não** significa "sem vínculo". A rota de busca só anota o
  /// estado para perfis escopados por Unidade (`admin`/`user`); para
  /// Administrador Geral, de Registro e Master os itens voltam sem anotação.
  /// Tratar `null` como "não vinculada" ofereceria "Vincular" para uma
  /// empresa já vinculada, e criaria a impressão de que ninguém a usa.
  final String? localUnitLinkStatus;

  /// Id da linha em `outsourced_company_unit_links`, quando anotada.
  final int? unitLinkId;

  /// Unidade que cadastrou a empresa primeiro — metadado histórico.
  ///
  /// Desde a extensão de compartilhamento por tenant ela "não concede nem
  /// restringe mais nada sozinha": quem autoriza é o vínculo explícito. Serve
  /// para a Unidade que está decidindo se vincula saber de onde veio o
  /// cadastro.
  final String originUnitName;

  /// Quantas Unidades mantêm vínculo ATIVO com esta empresa.
  ///
  /// O backend só envia este campo nos itens **mascarados** — os que a
  /// Unidade ainda não vinculou. É, portanto, o discriminador de fato entre
  /// "disponível para vincular" e "já vinculada"; ver [isMaskedForLinking].
  final int? linkedUnitsCount;

  /// `true` quando este item veio MASCARADO: a Unidade do ator ainda não tem
  /// vínculo com a empresa, e o backend omitiu notas, contratos e
  /// colaboradores de outras Unidades, mantendo só o suficiente para decidir
  /// se vale reaproveitar o cadastro.
  ///
  /// A detecção é indireta — presença de [linkedUnitsCount] — porque o
  /// backend não manda um sinalizador explícito. Fica isolada aqui, num lugar
  /// só, em vez de espalhada pela UI: se o servidor passar a mandar um campo
  /// próprio, muda esta linha e nada mais.
  bool get isMaskedForLinking => linkedUnitsCount != null;

  /// Valor técnico estável (inglês) — `outsourced`, `service_provider` ou
  /// `other_contracted`. O rótulo em português vive só na UI, nunca é
  /// gravado na coluna (condição vinculante do ADR-0002).
  final String companyKind;

  /// `Empresa Contratante`, `Empresa Terceirizada`, `Empresa Prestadora de
  /// Serviço`, `Responsabilidade Compartilhada`, `Conforme Contrato` (default)
  /// ou `Não Definido`.
  final String epiResponsibility;

  /// `simplified` ou `standard`.
  final String registrationMode;

  /// `pending_completion`, `complete`, `inactive` ou `archived`.
  final String registrationStatus;

  final String status;

  /// Preenchido quando [registrationMode] passa de `simplified` para
  /// `standard` (ver [isSimplified]).
  final String promotedAt;

  final String createdAt;

  bool get isSimplified => registrationMode == 'simplified';

  /// Rótulo em português para [companyKind] — só para exibição, nunca
  /// enviado de volta ao backend.
  String get companyKindLabel => switch (companyKind) {
        'outsourced' => 'Terceirizada',
        'service_provider' => 'Prestadora de Serviço',
        _ => 'Outro',
      };

  /// Rótulo curto para seletores: nome fantasia (ou razão social) + CNPJ.
  String get displayLabel {
    final name = tradeName.trim().isNotEmpty ? tradeName.trim() : legalName.trim();
    return cnpj.trim().isEmpty ? name : '$name — $cnpj';
  }

  static String _asString(Object? value) => value?.toString() ?? '';

  factory OutsourcedCompany.fromJson(Map<String, dynamic> json) => OutsourcedCompany(
        id: (json['id'] as num).toInt(),
        companyId: (json['company_id'] as num?)?.toInt() ?? 0,
        legalName: _asString(json['legal_name']),
        tradeName: _asString(json['trade_name']),
        cnpj: _asString(json['cnpj']),
        companyKind: _asString(json['company_kind']).isEmpty
            ? 'outsourced'
            : _asString(json['company_kind']),
        epiResponsibility: _asString(json['epi_responsibility']).isEmpty
            ? 'Conforme Contrato'
            : _asString(json['epi_responsibility']),
        registrationMode: _asString(json['registration_mode']).isEmpty
            ? 'simplified'
            : _asString(json['registration_mode']),
        registrationStatus: _asString(json['registration_status']).isEmpty
            ? 'pending_completion'
            : _asString(json['registration_status']),
        status: _asString(json['status']).isEmpty ? 'Ativa' : _asString(json['status']),
        promotedAt: _asString(json['promoted_at']),
        createdAt: _asString(json['created_at']),
        unitId: (json['unit_id'] as num?)?.toInt(),
        // `local_status` — nome do backend para empresa; ver a nota de
        // assimetria acima. Ausente permanece `null` (não informado), nunca
        // normalizado para 'none'.
        localUnitLinkStatus: json['local_status'] as String?,
        unitLinkId: (json['unit_link_id'] as num?)?.toInt(),
        originUnitName: _asString(json['origin_unit_name']),
        linkedUnitsCount: (json['linked_units_count'] as num?)?.toInt(),
      );

  /// Corpo aceito por POST/PUT `/api/outsourced-companies`.
  Map<String, dynamic> toJson() => {
        'legal_name': legalName,
        'trade_name': tradeName,
        'cnpj': cnpj,
        'company_kind': companyKind,
        'epi_responsibility': epiResponsibility,
        'registration_mode': registrationMode,
        'status': status,
        if (unitId != null) 'unit_id': unitId,
      };
}
