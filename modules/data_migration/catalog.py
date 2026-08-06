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
    fields=(
        FieldSpec('name', 'Nome', required=True,
                  aliases=('nome', 'nome completo', 'funcionario', 'funcionário', 'empregado',
                           'colaborador', 'employee', 'employee name', 'full name', 'trabalhador')),
        FieldSpec('cpf', 'CPF', required=True, validator='cpf',
                  aliases=('cpf', 'documento', 'doc', 'national id', 'tax id', 'ssn')),
        FieldSpec('employee_id_code', 'Matrícula',
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
        FieldSpec('role_name', 'Função',
                  aliases=('funcao', 'função', 'cargo', 'role', 'job title', 'position', 'ocupacao')),
        FieldSpec('admission_date', 'Data de admissão', validator='date',
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
    fields=(
        FieldSpec('name', 'Nome da unidade', required=True,
                  aliases=('unidade', 'nome', 'nome da unidade', 'department', 'departamento',
                           'filial', 'site', 'base', 'location', 'local')),
        FieldSpec('unit_type', 'Tipo',
                  aliases=('tipo', 'tipo de unidade', 'type', 'unit type', 'categoria')),
        FieldSpec('city', 'Cidade',
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
    fields=(
        FieldSpec('name', 'Descrição', required=True,
                  aliases=('epi', 'ppe', 'descricao', 'descrição', 'nome', 'item', 'produto',
                           'equipamento', 'material', 'description', 'product')),
        FieldSpec('purchase_code', 'Código',
                  aliases=('codigo', 'código', 'code', 'sku', 'part number', 'codigo interno',
                           'referencia', 'referência', 'item code')),
        FieldSpec('ca', 'CA', validator='ca',
                  aliases=('ca', 'certificado', 'certificado de aprovacao',
                           'certificado de aprovação', 'certificate', 'approval')),
        FieldSpec('ca_expiry', 'Validade do CA', validator='date',
                  aliases=('validade ca', 'vencimento ca', 'ca expiry', 'validade do certificado',
                           'expiration', 'vencimento')),
        FieldSpec('manufacturer', 'Fabricante',
                  aliases=('fabricante', 'manufacturer', 'marca', 'brand', 'maker')),
        FieldSpec('model_reference', 'Modelo',
                  aliases=('modelo', 'model', 'referencia', 'referência', 'model reference')),
        FieldSpec('supplier_company', 'Fornecedor',
                  aliases=('fornecedor', 'supplier', 'vendor', 'distribuidor')),
        FieldSpec('unit_measure', 'Unidade de medida',
                  aliases=('unidade de medida', 'um', 'unit', 'measure', 'uom', 'medida')),
        FieldSpec('epi_section', 'Categoria',
                  aliases=('categoria', 'category', 'grupo', 'group', 'classe', 'secao', 'seção')),
        FieldSpec('sector', 'Setor',
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

def _roadmap(key: str, label: str, table: str, phase: str) -> EntityDescriptor:
    return EntityDescriptor(key=key, label=label, target_table=table, fields=(), phase=phase)


_ROADMAP_ENTITIES = (
    _roadmap('estoque', 'Estoque', 'unit_epi_stock', '4'),
    _roadmap('empresas', 'Empresas', 'companies', '4'),
    _roadmap('centros_custo', 'Centros de Custo', 'cost_centers', '4'),
    _roadmap('funcoes', 'Funções', 'employee_roles', '4'),
    _roadmap('cargos', 'Cargos', 'employee_positions', '4'),
    _roadmap('fabricantes', 'Fabricantes', 'manufacturers', '4'),
    _roadmap('categorias', 'Categorias', 'epi_categories', '4'),
    _roadmap('certificados_ca', 'Certificados de Aprovação (CA)', 'epi_certificates', '4'),
    _roadmap('historico_entregas', 'Histórico de Entregas', 'deliveries', '4'),
    _roadmap('usuarios', 'Usuários', 'users', '4'),
    _roadmap('permissoes', 'Permissões', 'user_permissions', '4'),
    _roadmap('demandas', 'Demandas', 'stock_replenishment_needs', '4'),
    _roadmap('solicitacoes', 'Solicitações', 'epi_requests', '4'),
    _roadmap('assinaturas', 'Assinaturas', 'delivery_signatures', '7'),
    _roadmap('fotos', 'Fotos', 'employee_photos', '7'),
    _roadmap('documentos', 'Documentos', 'documents', '7'),
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
