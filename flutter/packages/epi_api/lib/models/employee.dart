class Employee {
  const Employee({
    required this.id,
    required this.name,
    this.code,
    this.sector,
    this.role,
    this.unitId,
    this.unitName,
    this.admissionDate,
    this.schedule,
    this.photoUrl,
    this.isActive = true,
    this.legalEntityId,
    this.legalEntityCnpj,
    this.legalEntityName,
    this.employmentType,
    this.sourceCompany,
    this.localUnitLinkStatus,
    this.isLinkedToActorUnit = false,
  });

  final int id;
  final String name;
  final String? code;
  final String? sector;
  final String? role;

  /// Unidade operacional atual (`current_unit_id`) — reflete movimentação
  /// temporária ativa quando houver; senão, a unidade-base do cadastro.
  final int? unitId;
  final String? unitName;
  final String? admissionDate;
  final String? schedule;
  final String? photoUrl;
  final bool isActive;

  /// CNPJ (LegalEntity) ao qual o colaborador pertence juridicamente.
  ///
  /// É o vínculo do contrato de trabalho: **imutável após a admissão**. A
  /// unidade é apenas a lotação operacional e pode mudar por transferência sem
  /// afetar este vínculo. Alterá-lo exige o processo administrativo auditado
  /// (`LegalEntitiesApi.transferEmployeeLegalEntity`).
  final int? legalEntityId;
  final String? legalEntityCnpj;
  final String? legalEntityName;

  /// Tipo de vínculo (`tipo_vinculo`): `CLT`, `Terceirizado`, `Temporário`,
  /// `Prestador de Serviço`, `Menor Aprendiz`, `Praticante` ou `Estagiário`.
  ///
  /// Texto livre no backend, sem lista fechada validada no servidor — os
  /// valores acima são os que a UI oferece, espelhando o web legado.
  final String? employmentType;

  /// Empresa de origem (`empresa_origem`), preenchida só quando
  /// [employmentType] é diferente de `CLT`. O backend zera este campo
  /// automaticamente quando o vínculo volta a ser CLT.
  final String? sourceCompany;

  /// Estado do vínculo local com a Unidade em contexto (ADR-0002 §13).
  ///
  /// Vem PRONTO do backend em `local_unit_link_status`. **A UI não deduz este
  /// estado**: não compara [unitId] com a Unidade do ator, não infere pela
  /// empresa de origem, não adivinha. Reconstruir a regra no cliente cria uma
  /// segunda verdade sobre o mesmo fato — foi por isso que o trabalho de
  /// backend (PR C1) e o de consumo (PR C2) foram separados.
  ///
  /// Quatro estados, e os quatro são distintos:
  ///
  /// - `null` — vínculo local **não se aplica**: mão de obra própria, ou
  ///   nenhuma Unidade em contexto. Nenhuma ação por Unidade deve aparecer.
  /// - [kUnitLinkStatusNone] (`'none'`) — aplicável, mas **inexistente**
  ///   naquela Unidade. Cabe "Vincular".
  /// - [kUnitLinkStatusActive] (`'active'`) — vínculo **ativo**.
  /// - [kUnitLinkStatusInactive] (`'inactive'`) — **arquivado** naquela
  ///   Unidade. Cabe "Reativar", não "Vincular": arquivado ≠ inexistente, e
  ///   tratá-los como a mesma coisa perde a distinção que o backend faz.
  final String? localUnitLinkStatus;

  /// `true` só quando [localUnitLinkStatus] é [kUnitLinkStatusActive].
  ///
  /// Também derivado pelo backend (`is_linked_to_actor_unit`). Existe porque a
  /// pergunta "está vinculado?" é diferente de "qual é o estado?", e responder
  /// a primeira a partir da segunda no cliente é o começo da dedução local que
  /// esta camada existe para impedir.
  final bool isLinkedToActorUnit;

  factory Employee.fromJson(Map<String, dynamic> json) => Employee(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        // O backend (fetch_employees/bootstrap) usa employee_id_code,
        // role_name e schedule_type — os nomes curtos ficam como fallback.
        code: json['employee_id_code'] as String? ?? json['code'] as String?,
        sector: json['sector'] as String?,
        role: json['role_name'] as String? ?? json['role'] as String?,
        unitId: (json['current_unit_id'] as num?)?.toInt() ??
            (json['unit_id'] as num?)?.toInt(),
        unitName: json['current_unit_name'] as String? ??
            json['unit_name'] as String? ??
            json['unit'] as String?,
        admissionDate: json['admission_date'] as String?,
        schedule: json['schedule_type'] as String? ?? json['schedule'] as String?,
        photoUrl: json['photo_url'] as String?,
        // O backend não envia is_active/active para colaboradores (não há
        // essa coluna); aceita bool ou 0/1 e assume ativo quando ausente.
        isActive: switch (json['is_active'] ?? json['active']) {
          final bool b => b,
          final num n => n.toInt() == 1,
          _ => true,
        },
        // Ausentes enquanto o schema Multi-CNPJ não estiver provisionado.
        legalEntityId: (json['legal_entity_id'] as num?)?.toInt(),
        legalEntityCnpj: json['legal_entity_cnpj'] as String?,
        legalEntityName: json['legal_entity_name'] as String?,
        employmentType: json['tipo_vinculo'] as String?,
        sourceCompany: json['empresa_origem'] as String?,
        // Ausente é `null` (não se aplica), NÃO `'none'`. A rota que carrega
        // este campo é `GET /api/employees`; o payload de bootstrap não
        // resolve contexto de Unidade e por isso nunca o traz preenchido.
        localUnitLinkStatus: json['local_unit_link_status'] as String?,
        isLinkedToActorUnit: json['is_linked_to_actor_unit'] == true,
      );
}

/// Vínculo local aplicável, mas inexistente na Unidade em contexto.
const String kUnitLinkStatusNone = 'none';

/// Vínculo local ativo na Unidade em contexto.
const String kUnitLinkStatusActive = 'active';

/// Vínculo local arquivado na Unidade em contexto.
const String kUnitLinkStatusInactive = 'inactive';

/// Vínculos de mão de obra **contratada** — os que existem exclusivamente no
/// módulo Terceirizados e Prestadores.
///
/// Espelha `CONTRACTED_VINCULOS` em `modules/employees/service.py` e a lista
/// homônima em `static/js/views/outsourced-employees-view.js`. As três listas
/// têm de ser idênticas: divergir faz a tela sumir com quem o backend aceita,
/// ou oferecer ação para quem ele recusa.
///
/// Decidir "é contratado?" comparando contra um único valor (`!= 'CLT'`) dava
/// no mesmo enquanto CLT era o único vínculo próprio. Com Menor Aprendiz,
/// Praticante e Estagiário deixou de dar: a decisão sai desta lista, nunca de
/// uma comparação contra uma opção só.
const List<String> kContractedVinculos = <String>[
  'Terceirizado',
  'Prestador de Serviço',
  'Temporário',
];

/// `true` quando [tipoVinculo] é mão de obra contratada.
bool isContractedVinculo(String? tipoVinculo) =>
    kContractedVinculos.contains((tipoVinculo ?? '').trim());
