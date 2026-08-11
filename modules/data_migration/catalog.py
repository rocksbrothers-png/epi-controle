"""Catálogo declarativo de entidades do Centro de Migração (ADR-0003 §2.1).

A decisão estruturante deste módulo: **não existem 20 importadores**. Existe
UM motor (parse → mapeia → valida → aplica → reverte) dirigido por
descritores declarativos. Adicionar uma entidade nova é adicionar um
``EntityDescriptor`` aqui — não escrever um pipeline.

Consequência de segurança (ADR-0003 §7): nome de tabela e de coluna vêm
SEMPRE deste catálogo, nunca do arquivo importado. É a allowlist que torna
injeção de SQL estruturalmente impossível no caminho de importação, mesmo
com um arquivo hostil.

``enabled=False`` marca entidade já modelada mas cujo writer ainda não foi
validado (roadmap do ADR-0003 §9). Ela aparece na UI como "em breve" — a
alternativa (expor importador não validado para dado trabalhista) seria
pior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    """Um campo do sistema que pode receber dado de uma coluna de origem.

    ``aliases`` alimenta o dicionário de sinônimos do motor de mapeamento
    (mapper.py) — é onde "Funcionário", "Employee" e "Colaborador" se
    encontram.
    """

    name: str
    label: str
    required: bool = False
    aliases: tuple[str, ...] = ()
    validator: str = ''  # chave em preview.VALIDATORS ('cpf', 'cnpj', 'date', 'int', 'ca')
    # Campo que guarda um ID mas cuja origem traz um *nome*. Nenhum export
    # legado tem o id interno deste sistema: a planilha diz "Produção", não
    # "3". ``(tabela, coluna_de_nome)`` diz ao motor como converter — e o que
    # não converter vira diagnóstico de referência inexistente, nunca um
    # INSERT que estoura no banco.
    resolves_to: tuple[str, str] = ()


@dataclass(frozen=True)
class EntityDescriptor:
    key: str
    label: str
    target_table: str
    fields: tuple[FieldSpec, ...]
    # Colunas que o banco exige (NOT NULL, sem DEFAULT) e que este cadastro
    # deliberadamente NÃO coleta, com o valor que o próprio sistema já grava
    # nesse caso. É uma decisão de domínio declarada e testada — não um
    # preenchimento automático para calar uma constraint. O teste de contrato
    # (tests/test_data_migration_contract.py) falha se aparecer uma coluna
    # obrigatória que não esteja nem nos `fields` nem aqui.
    column_defaults: tuple[tuple[str, object], ...] = ()
    # Normalizador de domínio compartilhado com o cadastro manual. Referência
    # tardia ("modulo:funcao") para não criar ciclo de import.
    normalizer: str = ''
    # Colunas que o NORMALIZADOR calcula a partir de outras — nunca vêm da
    # planilha e por isso não aparecem no assistente de mapeamento, mas
    # precisam ser gravadas. Sem isto o motor descartava o valor: só grava
    # colunas declaradas em `fields` (ver _writable_columns).
    #
    # O caso que motivou: `outsourced_companies.cnpj_normalized` é derivada de
    # `cnpj` e sustenta o índice único PARCIAL de deduplicação
    # (`WHERE cnpj_normalized <> ''`). Deixá-la vazia tirava a linha importada
    # de dentro do índice — o mesmo CNPJ podia entrar duas vezes (issue #169).
    derived_columns: tuple[str, ...] = ()
    # Identidade do registro para deduplicação e UPDATE. Nunca o ID interno
    # do sistema legado — CPF/matrícula/código é o que sobrevive à migração.
    natural_keys: tuple[str, ...] = ()
    enabled: bool = False
    phase: str = 'roadmap'

    def field_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.fields)

    def required_fields(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.fields if spec.required)

    def spec_for(self, name: str) -> FieldSpec | None:
        for spec in self.fields:
            if spec.name == name:
                return spec
        return None


# ── Entidades habilitadas na Fase 1 (ADR-0003 §9) ───────────────────────────

_COLABORADORES = EntityDescriptor(
    key='colaboradores',
    label='Colaboradores',
    target_table='employees',
    natural_keys=('cpf', 'employee_id_code'),
    enabled=True,
    phase='1',
    # `sector` e `schedule_type` são NOT NULL sem default em `employees`, mas
    # nenhum export legado os traz e o próprio sistema já grava string vazia
    # neles no Cadastro Simplificado (modules/employees/service.py §10.2).
    # A importação segue a MESMA convenção, explicitamente — em vez de
    # inventar "CLT"/"Integral", que seriam afirmações de negócio falsas
    # sobre a jornada e o setor de cada pessoa (ADR-0003 §12.3).
    column_defaults=(('sector', ''), ('schedule_type', '')),
    normalizer='modules.employees.service:normalize_employee_domain_fields',
    fields=(
        FieldSpec('name', 'Nome', required=True,
                  aliases=('nome', 'nome completo', 'funcionario', 'funcionário', 'empregado',
                           'colaborador', 'employee', 'employee name', 'full name', 'trabalhador')),
        FieldSpec('cpf', 'CPF', required=True, validator='cpf',
                  aliases=('cpf', 'documento', 'doc', 'national id', 'tax id', 'ssn')),
        # required=True porque `employees.employee_id_code` é NOT NULL sem default
        # e o cadastro manual também a exige. O índice único é POR TENANT
        # (uq_employees_company_employee_code), coerente com o índice de upsert
        # desta importação, que já era carregado com WHERE company_id (#168).
        FieldSpec('employee_id_code', 'Matrícula', required=True,
                  aliases=('matricula', 'matrícula', 'registro', 'registration',
                           'employee id', 'employee code', 'chapa', 'codigo', 'código')),
        # required=True porque `employees.unit_id` é NOT NULL no schema real:
        # colaborador sem unidade não existe neste sistema. Sem isto o preview
        # dizia "3 válidas, 0 problemas" e a gravação estourava depois.
        FieldSpec('unit_id', 'Unidade', required=True, resolves_to=('units', 'name'),
                  aliases=('unidade', 'department', 'departamento', 'setor de lotacao',
                           'lotacao', 'lotação', 'filial', 'base', 'site', 'local de trabalho')),
        FieldSpec('sector', 'Setor',
                  aliases=('setor', 'sector', 'area', 'área', 'departamento')),
        # required=True: NOT NULL sem default no banco e obrigatórios também no
        # cadastro manual (create_employee) — a paridade é intencional.
        FieldSpec('role_name', 'Função', required=True,
                  aliases=('funcao', 'função', 'cargo', 'role', 'job title', 'position', 'ocupacao')),
        FieldSpec('admission_date', 'Data de admissão', required=True, validator='date',
                  aliases=('admissao', 'admissão', 'data admissao', 'data de admissao',
                           'hire date', 'admission date', 'start date', 'data de inicio')),
        FieldSpec('email', 'E-mail',
                  aliases=('email', 'e-mail', 'mail', 'correio eletronico')),
        FieldSpec('whatsapp', 'Telefone',
                  aliases=('telefone', 'fone', 'celular', 'phone', 'mobile', 'whatsapp', 'contato')),
        FieldSpec('tipo_vinculo', 'Tipo de vínculo',
                  aliases=('vinculo', 'vínculo', 'tipo de vinculo', 'contract type',
                           'employment type', 'regime')),
        FieldSpec('empresa_origem', 'Empresa de origem',
                  aliases=('empresa origem', 'empresa', 'company', 'employer', 'prestadora',
                           'terceirizada', 'supplier')),
    ),
)

_UNIDADES = EntityDescriptor(
    key='unidades',
    label='Unidades',
    target_table='units',
    natural_keys=('name',),
    enabled=True,
    phase='1',
    # Mesma regra do cadastro manual: alias de `unit_type` (`navio`/
    # `embarcação` → `embarcacao`, etc.) via `normalize_unit_type`. `city`
    # não tem normalização em lugar nenhum do sistema hoje — não é
    # inventada aqui (issue #169).
    normalizer='modules.units.service:normalize_unit_domain_fields',
    fields=(
        FieldSpec('name', 'Nome da unidade', required=True,
                  aliases=('unidade', 'nome', 'nome da unidade', 'department', 'departamento',
                           'filial', 'site', 'base', 'location', 'local')),
        # required=True porque `units.unit_type` e `units.city` são NOT NULL sem
        # default no banco e NÃO têm valor determinístico honesto: "base" seria
        # afirmar que a unidade é terrestre, e cidade nenhuma se adivinha.
        # Exigir no preview é melhor do que inventar (ADR-0003 §12.3).
        FieldSpec('unit_type', 'Tipo', required=True,
                  aliases=('tipo', 'tipo de unidade', 'type', 'unit type', 'categoria')),
        FieldSpec('city', 'Cidade', required=True,
                  aliases=('cidade', 'city', 'municipio', 'município', 'localidade')),
        FieldSpec('notes', 'Observações',
                  aliases=('observacao', 'observação', 'observacoes', 'notes', 'obs', 'comentario')),
    ),
)

_EPIS = EntityDescriptor(
    key='epis',
    label='EPIs',
    target_table='epis',
    natural_keys=('purchase_code', 'name'),
    enabled=True,
    phase='1',
    # `create_epi` grava manufacture_date='' e validity_days=0 por conta própria
    # (parse_int_flexible(..., 0)). A importação segue o MESMO comportamento —
    # não é um valor inventado, é o que o cadastro do sistema já faz.
    column_defaults=(('manufacture_date', ''), ('validity_days', 0)),
    # CA só com dígitos e `ca_expiry`/`epi_validity_date` canonizadas para
    # ISO (`YYYY-MM-DD`) antes de gravar — comportamento NOVO, só da
    # importação (nenhum cadastro manual normaliza isto hoje): sem isto uma
    # data "dd/mm/yyyy" importada passava no preview como válida mas era
    # gravada como texto literal, e `epis.validity.parse_iso_date` a
    # ignorava em silêncio, quebrando o cálculo de vencimento/PEPS (issue
    # #169).
    normalizer='modules.epis.service:normalize_epi_domain_fields',
    fields=(
        FieldSpec('name', 'Descrição', required=True,
                  aliases=('epi', 'ppe', 'descricao', 'descrição', 'nome', 'item', 'produto',
                           'equipamento', 'material', 'description', 'product')),
        # Todos NOT NULL sem default no banco e exigidos por create_epi.
        FieldSpec('purchase_code', 'Código', required=True,
                  aliases=('codigo', 'código', 'code', 'sku', 'part number', 'codigo interno',
                           'referencia', 'referência', 'item code')),
        FieldSpec('ca', 'CA', required=True, validator='ca',
                  aliases=('ca', 'certificado', 'certificado de aprovacao',
                           'certificado de aprovação', 'certificate', 'approval')),
        FieldSpec('ca_expiry', 'Validade do CA', required=True, validator='date',
                  aliases=('validade ca', 'vencimento ca', 'ca expiry', 'validade do certificado',
                           'expiration', 'vencimento')),
        FieldSpec('epi_validity_date', 'Validade do EPI', required=True, validator='date',
                  aliases=('validade', 'validade do epi', 'epi validity', 'shelf life',
                           'data de validade', 'vencimento do epi')),
        FieldSpec('manufacturer', 'Fabricante',
                  aliases=('fabricante', 'manufacturer', 'marca', 'brand', 'maker')),
        FieldSpec('model_reference', 'Modelo',
                  aliases=('modelo', 'model', 'referencia', 'referência', 'model reference')),
        FieldSpec('supplier_company', 'Fornecedor',
                  aliases=('fornecedor', 'supplier', 'vendor', 'distribuidor')),
        FieldSpec('unit_measure', 'Unidade de medida', required=True,
                  aliases=('unidade de medida', 'um', 'unit', 'measure', 'uom', 'medida')),
        FieldSpec('epi_section', 'Categoria',
                  aliases=('categoria', 'category', 'grupo', 'group', 'classe', 'secao', 'seção')),
        FieldSpec('sector', 'Setor', required=True,
                  aliases=('setor', 'sector', 'area', 'área')),
    ),
)

_FORNECEDORES = EntityDescriptor(
    key='fornecedores',
    label='Fornecedores',
    target_table='outsourced_companies',
    natural_keys=('cnpj', 'legal_name'),
    enabled=True,
    phase='1',
    # Mesmas regras do cadastro manual: CNPJ canônico (formatado em `cnpj`,
    # só dígitos em `cnpj_normalized`) e os vocabulários controlados de
    # `company_kind` / `epi_responsibility` / `registration_mode` /
    # `registration_status`. Sem isto a importação gravava "Terceirizada" onde
    # o sistema usa "outsourced", e deixava `cnpj_normalized` vazio.
    normalizer='modules.outsourced_companies.service:normalize_outsourced_company_domain_fields',
    # `cnpj_normalized` não vem da planilha: o normalizador a deriva de `cnpj`.
    # É ela que sustenta o índice único parcial de deduplicação.
    derived_columns=('cnpj_normalized',),
    fields=(
        FieldSpec('legal_name', 'Razão social', required=True,
                  aliases=('razao social', 'razão social', 'fornecedor', 'empresa', 'supplier',
                           'vendor', 'company', 'legal name', 'nome')),
        FieldSpec('trade_name', 'Nome fantasia',
                  aliases=('nome fantasia', 'fantasia', 'trade name', 'apelido', 'nome comercial')),
        FieldSpec('cnpj', 'CNPJ', validator='cnpj',
                  aliases=('cnpj', 'documento', 'tax id', 'doc', 'registro')),
        FieldSpec('company_kind', 'Tipo da empresa',
                  aliases=('tipo', 'tipo de empresa', 'type', 'company kind', 'categoria')),
    ),
)


# ── Entidades modeladas, writer na fila (ADR-0003 §9) ───────────────────────
#
# O catálogo declarava 20 entidades. A auditoria da issue #172 verificou cada
# uma contra o schema PostgreSQL real e encontrou o seguinte:
#
#   • 10 apontavam para tabelas que NÃO EXISTEM — `delivery_signatures`,
#     `employee_positions`, `epi_categories`, `cost_centers`,
#     `epi_certificates`, `documents`, `manufacturers`, `employee_photos`,
#     `employee_roles`, `user_permissions`. Eram cartões de painel sem modelo
#     por trás.
#   • Vários desses dados JÁ SÃO IMPORTADOS hoje, como coluna de outra
#     entidade: função/cargo em `employees.role_name`, fabricante em
#     `epis.manufacturer`, CA em `epis.ca`, categoria e centro de custo como
#     texto, assinatura nas colunas `signature_*` da própria entrega.
#   • `demandas` (`stock_replenishment_needs`) é DERIVADA: o motor de estoque
#     mínimo a recalcula a partir do estoque atual. Importar produziria
#     números que o próprio motor contradiz no primeiro recálculo.
#
# Transformar qualquer um desses conceitos em tabela é decisão de produto e
# arquitetura, não trabalho de migração — e nenhum schema será criado só para
# manter a contagem de 20 no painel. O objetivo é suportar corretamente as
# entidades com modelo de domínio real e valor de migração.
#
# Sobram aqui as que têm tabela e ainda não têm writer. Cada uma segue
# bloqueada por um motivo próprio, registrado em #172.

def _roadmap(key: str, label: str, table: str, phase: str) -> EntityDescriptor:
    return EntityDescriptor(key=key, label=label, target_table=table, fields=(), phase=phase)


_ROADMAP_ENTITIES = (
    # Prioridade alta: é o registro legal que o cliente não consegue recriar.
    _roadmap('historico_entregas', 'Histórico de Entregas', 'deliveries', '4'),
    # Importável, mas como MOVIMENTO de ajuste — nunca como saldo, que é
    # derivado de `stock_movements`.
    _roadmap('estoque', 'Estoque', 'unit_epi_stock', '4'),
    # Baixo valor e sem UNIQUE de negócio: reavaliar antes de habilitar.
    _roadmap('solicitacoes', 'Solicitações', 'epi_requests', '4'),
    # Bloqueada: `password` é hash e `role` livre é escalada de privilégio.
    # Depende de definir senha temporária obrigatória e lista fechada de roles.
    _roadmap('usuarios', 'Usuários', 'users', '4'),
    # Bloqueada: importar empresa equivale a CRIAR TENANT, operação de Admin
    # Master. `name` e `cnpj` são UNIQUE globais.
    _roadmap('empresas', 'Empresas', 'companies', '4'),
)


ENTITIES: dict[str, EntityDescriptor] = {
    descriptor.key: descriptor
    for descriptor in (_COLABORADORES, _UNIDADES, _EPIS, _FORNECEDORES, *_ROADMAP_ENTITIES)
}


def get_entity(key: str) -> EntityDescriptor:
    descriptor = ENTITIES.get(str(key or '').strip())
    if descriptor is None:
        raise ValueError(f'Entidade de migração desconhecida: {key!r}.')
    return descriptor


def require_enabled_entity(key: str) -> EntityDescriptor:
    """Gate único para qualquer escrita: entidade de roadmap nunca chega ao
    writer, mesmo que a UI (ou um cliente hostil) tente."""
    descriptor = get_entity(key)
    if not descriptor.enabled:
        raise ValueError(
            f'A importação de "{descriptor.label}" ainda não está disponível '
            f'(prevista para a fase {descriptor.phase} do Centro de Migração).'
        )
    return descriptor


def list_entities() -> list[dict]:
    """Catálogo para o dashboard: os 20 cartões, com o que já está liberado."""
    return [
        {
            'key': descriptor.key,
            'label': descriptor.label,
            'enabled': descriptor.enabled,
            'phase': descriptor.phase,
            'fields': [
                {'name': spec.name, 'label': spec.label, 'required': spec.required}
                for spec in descriptor.fields
            ],
            'natural_keys': list(descriptor.natural_keys),
        }
        for descriptor in ENTITIES.values()
    ]
