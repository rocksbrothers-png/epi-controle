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
  });

  final int id;
  final int companyId;
  final String legalName;
  final String tradeName;
  final String cnpj;

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
      };
}
