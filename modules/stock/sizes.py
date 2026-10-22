"""Normalização de tamanhos, sem dependência dos serviços de estoque."""

def normalize_item_size_value(value):
    normalized = str(value or '').strip()
    if not normalized:
        return ''
    lowered = normalized.lower()
    if lowered in {'n/a', 'na', 'selecione', 'selecione o tamanho', 'null', 'undefined'}:
        return ''
    return normalized


def resolve_item_size(glove_size, size, uniform_size):
    normalized_glove = normalize_item_size_value(glove_size)
    normalized_size = normalize_item_size_value(size)
    normalized_uniform = normalize_item_size_value(uniform_size)
    selected_size = normalized_glove or normalized_size or normalized_uniform or ''
    return {
        'selected_size': selected_size,
        'glove_size': normalized_glove or 'N/A',
        'size': selected_size or 'N/A',
        'uniform_size': normalized_uniform or 'N/A',
    }


def resolve_effective_size_fields(primary, fallback=None, *, fallback_prefix=''):
    primary = primary or {}
    fallback = fallback or {}
    primary_glove = normalize_item_size_value(primary.get('glove_size'))
    primary_size = normalize_item_size_value(primary.get('size'))
    primary_uniform = normalize_item_size_value(primary.get('uniform_size'))
    fallback_glove = normalize_item_size_value(fallback.get(f'{fallback_prefix}glove_size'))
    fallback_size = normalize_item_size_value(fallback.get(f'{fallback_prefix}size'))
    fallback_uniform = normalize_item_size_value(fallback.get(f'{fallback_prefix}uniform_size'))
    selected_size = (
        primary_glove or primary_size or primary_uniform
        or fallback_glove or fallback_size or fallback_uniform or ''
    )
    return {
        'selected_size': selected_size,
        'glove_size': primary_glove or fallback_glove or 'N/A',
        'size': primary_size or fallback_size or selected_size or 'N/A',
        'uniform_size': primary_uniform or fallback_uniform or 'N/A',
    }


def apply_effective_size_fields(target, primary, fallback=None, *, fallback_prefix=''):
    effective_size = resolve_effective_size_fields(primary, fallback, fallback_prefix=fallback_prefix)
    target['glove_size'] = effective_size['glove_size']
    target['size'] = effective_size['size']
    target['uniform_size'] = effective_size['uniform_size']
    return target
