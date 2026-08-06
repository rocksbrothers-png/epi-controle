"""Motor de mapeamento inteligente (ADR-0003 §2.3).

O pedido de produto chama isto de "IA de mapeamento". A decisão explícita do
ADR é **não** usar LLM aqui: migração de cadastro trabalhista/fiscal precisa
ser determinística, reproduzível e explicável. Um modelo que mapeia "CPF"
para "matrícula" em 1 de 100 execuções é inaceitável quando o resultado é
uma base de colaboradores.

O que o motor faz, em ordem, parando na primeira estratégia que resolve:

1. ``exact``    — nome normalizado da coluna == nome/alias do campo
2. ``synonym``  — dicionário curado PT/EN do descritor (catalog.FieldSpec.aliases)
3. ``contains`` — alias contido no cabeçalho (pega "Nome do Funcionário")
4. ``fuzzy``    — difflib acima do limiar, com score exposto

Toda sugestão volta com ``confidence`` e ``strategy``, então o usuário
sempre vê POR QUE o sistema propôs aquilo — e pode sobrescrever. Coluna não
resolvida sobe como ``unmapped`` para mapeamento manual (etapa 4 do
assistente).
"""

from __future__ import annotations

from difflib import SequenceMatcher

from modules.data_migration.catalog import EntityDescriptor
from modules.data_migration.sources import _normalize_header

# Abaixo disto o palpite é ruim demais para ser oferecido: melhor pedir
# mapeamento manual do que propor errado com ar de certeza.
FUZZY_THRESHOLD = 0.82

# Sinônimos que valem para QUALQUER entidade — os específicos moram no
# descritor de cada campo (catalog.py). Aqui ficam os termos estruturais que
# se repetem em todo export de ERP.
_GLOBAL_SYNONYMS: dict[str, tuple[str, ...]] = {
    'name': ('nome', 'descricao', 'description', 'denominacao', 'titulo'),
    'cpf': ('cpf', 'documento', 'doc'),
    'cnpj': ('cnpj',),
    'unit_id': ('unidade', 'department', 'departamento', 'filial', 'site', 'base', 'location'),
    'sector': ('setor', 'sector', 'area'),
    'role_name': ('funcao', 'cargo', 'role', 'position', 'job title'),
}


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _candidate_terms(descriptor: EntityDescriptor, field_name: str) -> list[str]:
    spec = descriptor.spec_for(field_name)
    terms = [field_name, spec.label if spec else field_name]
    if spec:
        terms.extend(spec.aliases)
    terms.extend(_GLOBAL_SYNONYMS.get(field_name, ()))
    return [_normalize_header(term) for term in terms if str(term or '').strip()]


def suggest_mapping(descriptor: EntityDescriptor, columns: list[str]) -> dict:
    """Propõe ``{coluna_de_origem: campo_do_sistema}`` para as colunas dadas.

    Devolve também o detalhamento por coluna (estratégia + score) e a lista
    de campos obrigatórios que ficaram sem origem — é o que a etapa 4 do
    assistente mostra ao usuário.
    """
    field_names = descriptor.field_names()
    terms_by_field = {name: _candidate_terms(descriptor, name) for name in field_names}

    details: list[dict] = []
    mapping: dict[str, str] = {}
    taken: set[str] = set()

    for column in columns:
        normalized = _normalize_header(column)
        best_field, best_score, best_strategy = '', 0.0, 'unmapped'

        # Avalia contra TODOS os campos, inclusive os já tomados. Se o melhor
        # destino de uma coluna já foi usado, ela fica sem mapeamento
        # automático — nunca é rebaixada para o segundo melhor palpite.
        # Sem isso, "Employee" (cujo melhor destino é `name`, já tomado por
        # "Funcionário") escorregava por fuzzy para `empresa_origem`, via o
        # alias "employer": Employee e Employer são conceitos OPOSTOS, e o
        # nome da pessoa acabaria gravado como empresa de origem.
        for field_name in field_names:
            terms = terms_by_field[field_name]

            if normalized and normalized in terms:
                best_field, best_score, best_strategy = field_name, 1.0, 'exact'
                break

            for term in terms:
                if not term:
                    continue
                if term == normalized:
                    score, strategy = 1.0, 'exact'
                elif normalized and (term in normalized or normalized in term):
                    # "nome do funcionario" contém "funcionario". Peso abaixo
                    # do exato para não vencer de um match perfeito.
                    longest, shortest = max(term, normalized, key=len), min(term, normalized, key=len)
                    score, strategy = 0.90 * (len(shortest) / max(len(longest), 1)), 'contains'
                else:
                    score, strategy = _similarity(normalized, term), 'fuzzy'
                    if score < FUZZY_THRESHOLD:
                        continue
                if score > best_score:
                    best_field, best_score, best_strategy = field_name, score, strategy
            if best_strategy == 'exact':
                break

        if best_field and best_field in taken:
            # Campo já preenchido por uma coluna anterior (mais bem
            # pontuada): esta sobe para decisão manual do usuário.
            details.append({
                'source_column': column,
                'target_field': '',
                'confidence': 0.0,
                'strategy': 'duplicate_target',
                'duplicate_of': best_field,
            })
            continue

        if best_field and best_score >= min(FUZZY_THRESHOLD, 0.5):
            mapping[column] = best_field
            taken.add(best_field)
        else:
            best_field, best_score, best_strategy = '', 0.0, 'unmapped'

        details.append({
            'source_column': column,
            'target_field': best_field,
            'confidence': round(float(best_score), 3),
            'strategy': best_strategy,
        })

    mapped_fields = set(mapping.values())
    return {
        'mapping': mapping,
        'details': details,
        'unmapped_columns': [item['source_column'] for item in details if not item['target_field']],
        'missing_required': [
            name for name in descriptor.required_fields() if name not in mapped_fields
        ],
    }


def normalize_manual_mapping(descriptor: EntityDescriptor, raw_mapping: dict, columns: list[str]) -> dict:
    """Valida o mapeamento vindo do cliente (etapa 4 do assistente).

    Rejeita campo fora do descritor: junto com a allowlist de tabela/coluna
    do catálogo, é o que impede um payload hostil de direcionar a escrita
    para uma coluna arbitrária (ADR-0003 §7).
    """
    valid_fields = set(descriptor.field_names())
    valid_columns = set(columns)
    mapping: dict[str, str] = {}
    seen_fields: set[str] = set()

    for source_column, target_field in (raw_mapping or {}).items():
        source_column = str(source_column or '').strip()
        target_field = str(target_field or '').strip()
        if not source_column or not target_field:
            continue
        if source_column not in valid_columns:
            raise ValueError(f'Coluna de origem inexistente no arquivo: {source_column!r}.')
        if target_field not in valid_fields:
            raise ValueError(
                f'Campo de destino inválido para {descriptor.label}: {target_field!r}.'
            )
        if target_field in seen_fields:
            raise ValueError(
                f'Campo {target_field!r} recebeu mais de uma coluna de origem.'
            )
        seen_fields.add(target_field)
        mapping[source_column] = target_field

    missing = [name for name in descriptor.required_fields() if name not in seen_fields]
    if missing:
        labels = ', '.join(
            (descriptor.spec_for(name).label if descriptor.spec_for(name) else name)
            for name in missing
        )
        raise ValueError(f'Campos obrigatórios sem coluna de origem: {labels}.')
    return mapping


def apply_mapping(mapping: dict, rows: list[dict]) -> list[dict]:
    """Traduz as linhas de origem para o vocabulário do sistema."""
    translated: list[dict] = []
    for row in rows:
        record: dict = {}
        for source_column, target_field in mapping.items():
            value = row.get(source_column)
            record[target_field] = '' if value is None else str(value).strip()
        translated.append(record)
    return translated
