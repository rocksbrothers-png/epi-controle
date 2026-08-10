"""Validação e preview do Centro de Migração (ADR-0003 §5).

Nada é gravado antes de o usuário ver este relatório. Cada diagnóstico
carrega o **número da linha** — sem isso o usuário não consegue corrigir a
planilha, e um preview que não permite corrigir não serve para nada.
"""

from __future__ import annotations

import re
from datetime import datetime

from modules.data_migration.catalog import EntityDescriptor

_DATE_FORMATS = ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S')
_TRUNCATE_TO = {'%Y-%m-%dT%H:%M:%S': 19}


def _digits(value: object) -> str:
    return re.sub(r'\D', '', str(value or ''))


def validate_cpf(value: object) -> bool:
    """Dígito verificador real — não basta ter 11 dígitos. Um CPF inválido
    importado vira colaborador que nunca assina ficha corretamente."""
    digits = _digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for length in (9, 10):
        total = sum(int(digits[index]) * (length + 1 - index) for index in range(length))
        check = (total * 10) % 11
        check = 0 if check == 10 else check
        if check != int(digits[length]):
            return False
    return True


def validate_cnpj(value: object) -> bool:
    digits = _digits(value)
    if len(digits) != 14 or digits == digits[0] * 14:
        return False
    for length, weights in (
        (12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
        (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
    ):
        total = sum(int(digits[index]) * weights[index] for index in range(length))
        check = total % 11
        check = 0 if check < 2 else 11 - check
        if check != int(digits[length]):
            return False
    return True


def parse_date_flexible(value: object) -> datetime | None:
    """Tenta cada formato aceito (``_DATE_FORMATS``) e devolve o ``datetime``
    correspondente, ou ``None`` se nenhum bater (vazio incluído).

    Fonte única do parsing de data flexível: ``validate_date`` (abaixo) só
    confirma o formato para o preview; ``modules.epis.service.
    normalize_epi_domain_fields`` reaproveita esta mesma função para gravar
    o valor canônico ISO na importação (issue #169). Duplicar o parsing
    criaria dois parsers que podem divergir sobre o que é uma data válida.
    """
    text = str(value or '').strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        # Formato com hora tolera sobra à direita: export JSON costuma trazer
        # "2024-03-01T08:30:00.000Z", que é uma data perfeitamente válida.
        candidate = text[:_TRUNCATE_TO[fmt]] if fmt in _TRUNCATE_TO else text
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def validate_date(value: object) -> bool:
    text = str(value or '').strip()
    if not text:
        return True
    return parse_date_flexible(text) is not None


def validate_ca(value: object) -> bool:
    """CA é numérico no MTE. Aceita vazio (nem todo EPI exige CA)."""
    text = str(value or '').strip()
    return not text or bool(re.fullmatch(r'\d{3,8}', _digits(text)))


def validate_int(value: object) -> bool:
    text = str(value or '').strip()
    return not text or bool(re.fullmatch(r'-?\d+', text))


VALIDATORS = {
    'cpf': (validate_cpf, 'CPF inválido'),
    'cnpj': (validate_cnpj, 'CNPJ inválido'),
    'date': (validate_date, 'Data inválida'),
    'ca': (validate_ca, 'CA inválido'),
    'int': (validate_int, 'Valor numérico inválido'),
}


def natural_key_of(descriptor: EntityDescriptor, record: dict) -> str:
    """Identidade do registro para dedupe/update. Usa a primeira chave
    natural preenchida — CPF primeiro, matrícula como alternativa."""
    for key in descriptor.natural_keys:
        value = str(record.get(key) or '').strip()
        if value:
            normalized = _digits(value) if key in ('cpf', 'cnpj') else value.casefold()
            return f'{key}:{normalized}'
    return ''


def build_preview(descriptor: EntityDescriptor, records: list[dict], *, existing_keys=None) -> dict:
    """Relatório completo do que aconteceria — sem gravar nada.

    ``existing_keys`` são as chaves naturais já presentes na base do tenant
    (o service resolve); permite separar "vai inserir" de "vai atualizar" e
    apontar duplicidade contra a base, não só dentro do arquivo.
    """
    existing_keys = set(existing_keys or ())
    diagnostics: list[dict] = []
    seen_keys: dict[str, int] = {}

    valid_rows = 0
    duplicate_in_file = 0
    duplicate_in_base = 0
    missing_required = 0
    invalid_values = 0
    no_identity = 0
    unresolved_reference = 0
    domain_rejected = 0

    for index, record in enumerate(records, start=1):
        row_ok = True

        # Referência que não resolveu (ADR-0003 §12.4). O diagnóstico mostra o
        # texto EXATO da planilha para o usuário poder corrigir a origem ou
        # cadastrar a unidade que falta antes de reexecutar.
        for name, detail in (record.get('__unresolved__') or {}).items():
            spec = descriptor.spec_for(name)
            label = spec.label if spec else name
            if detail.get('reason') == 'ambiguous':
                message = (
                    f'{label} "{detail.get("value")}" corresponde a '
                    f'{detail.get("matches")} cadastros nesta empresa. '
                    'Desfaça a ambiguidade ou informe o identificador.'
                )
            else:
                message = (
                    f'{label} "{detail.get("value")}" não existe nesta empresa. '
                    'Cadastre antes de importar ou corrija a planilha.'
                )
            diagnostics.append({
                'row': index,
                'level': 'error',
                'code': f'unresolved_{detail.get("reason", "unknown")}',
                'field': name,
                'source_value': detail.get('value'),
                'message': message,
            })
            unresolved_reference += 1
            row_ok = False

        # Regras de vínculo do domínio, as MESMAS do cadastro manual.
        domain_error = record.get('__domain_error__')
        if domain_error:
            diagnostics.append({
                'row': index,
                'level': 'error',
                'code': 'domain_rule',
                'field': '',
                'message': str(domain_error),
            })
            domain_rejected += 1
            row_ok = False

        for name in descriptor.required_fields():
            if not str(record.get(name) or '').strip():
                spec = descriptor.spec_for(name)
                diagnostics.append({
                    'row': index,
                    'level': 'error',
                    'code': 'missing_required',
                    'field': name,
                    'message': f'Campo obrigatório ausente: {spec.label if spec else name}.',
                })
                missing_required += 1
                row_ok = False

        for spec in descriptor.fields:
            if not spec.validator:
                continue
            validator, label = VALIDATORS.get(spec.validator, (None, ''))
            if validator is None:
                continue
            value = record.get(spec.name)
            if str(value or '').strip() and not validator(value):
                diagnostics.append({
                    'row': index,
                    'level': 'error',
                    'code': f'invalid_{spec.validator}',
                    'field': spec.name,
                    'message': f'{label} em {spec.label}: {str(value)[:60]!r}.',
                })
                invalid_values += 1
                row_ok = False

        key = natural_key_of(descriptor, record)
        if not key:
            diagnostics.append({
                'row': index,
                'level': 'error',
                'code': 'no_natural_key',
                'field': ', '.join(descriptor.natural_keys),
                'message': (
                    'Registro sem identificador: preencha ao menos '
                    f'{" ou ".join(descriptor.natural_keys)}.'
                ),
            })
            no_identity += 1
            row_ok = False
        else:
            if key in seen_keys:
                diagnostics.append({
                    'row': index,
                    'level': 'warning',
                    'code': 'duplicate_in_file',
                    'field': key.split(':', 1)[0],
                    'message': f'Registro duplicado no arquivo (também na linha {seen_keys[key]}).',
                })
                duplicate_in_file += 1
            else:
                seen_keys[key] = index
            if key in existing_keys:
                diagnostics.append({
                    'row': index,
                    'level': 'info',
                    'code': 'duplicate_in_base',
                    'field': key.split(':', 1)[0],
                    'message': 'Já existe na base — será atualizado ou ignorado conforme a estratégia.',
                })
                duplicate_in_base += 1

        if row_ok:
            valid_rows += 1

    return {
        'total_rows': len(records),
        'valid_rows': valid_rows,
        'invalid_rows': len(records) - valid_rows,
        'will_insert': sum(
            1 for key in seen_keys if key not in existing_keys
        ),
        'will_update': duplicate_in_base,
        'counters': {
            'duplicate_in_file': duplicate_in_file,
            'duplicate_in_base': duplicate_in_base,
            'missing_required': missing_required,
            'invalid_values': invalid_values,
            'no_natural_key': no_identity,
            'unresolved_reference': unresolved_reference,
            'domain_rule': domain_rejected,
        },
        'diagnostics': diagnostics,
        'blocking': any(item['level'] == 'error' for item in diagnostics),
    }
