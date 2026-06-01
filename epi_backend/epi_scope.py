"""
epi_scope - Regra de visibilidade de EPIs (C1+D1+E3 CONFIRMADA)

Fora de JV: GLOBAL + UNIT propria visiveis.
Em JV X: UNIT propria + JV de X visiveis. GLOBAL oculto.
"""
from __future__ import annotations
from typing import Iterable, Mapping

SCOPE_GLOBAL = 'GLOBAL'
SCOPE_UNIT = 'UNIT'
SCOPE_JOINT_VENTURE = 'JOINT_VENTURE'
VALID_SCOPE_TYPES = {SCOPE_GLOBAL, SCOPE_UNIT, SCOPE_JOINT_VENTURE}


def normalize_joint_venture_name(value: object) -> str:
    return str(value or '').strip()


def _safe_int(value: object) -> int | None:
    if value in (None, '', 0, '0'):
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if not raw.isdigit():
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def resolve_scope_type(unit_id: object, joint_venture_name: object) -> str:
    if normalize_joint_venture_name(joint_venture_name):
        return SCOPE_JOINT_VENTURE
    if unit_id not in (None, '', 0, '0'):
        return SCOPE_UNIT
    return SCOPE_GLOBAL


def is_epi_visible_for_unit(
    epi_unit_id: object,
    epi_joint_venture_name: object,
    target_unit_id: object,
    target_unit_joint_venture_name: object,
) -> bool:
    """Return True when an EPI should appear for a specific unit context."""

    if target_unit_id in (None, '', 0, '0'):
        return True

    target_unit_id_normalized = _safe_int(target_unit_id)
    if target_unit_id_normalized is None:
        return False

    epi_scope = resolve_scope_type(epi_unit_id, epi_joint_venture_name)
    target_jv = normalize_joint_venture_name(target_unit_joint_venture_name).lower()
    epi_jv = normalize_joint_venture_name(epi_joint_venture_name).lower()

    if target_jv:
        if epi_scope == SCOPE_JOINT_VENTURE:
            return bool(epi_jv) and epi_jv == target_jv
        if epi_scope == SCOPE_UNIT:
            epi_unit_id_normalized = _safe_int(epi_unit_id)
            return epi_unit_id_normalized is not None and epi_unit_id_normalized == target_unit_id_normalized
        return False

    if epi_scope == SCOPE_GLOBAL:
        return True
    if epi_scope == SCOPE_UNIT:
        epi_unit_id_normalized = _safe_int(epi_unit_id)
        return epi_unit_id_normalized is not None and epi_unit_id_normalized == target_unit_id_normalized
    return False


def get_epi_effective_jv_name(epi: Mapping[str, object], get_unit_jv_fn=None) -> str:
    """Return the effective JV name for an EPI.

    When get_unit_jv_fn is provided it is called with the EPI's unit_id to
    look up the current period from unit_joint_venture_periods (source of
    truth). Falls back to epi['active_joinventure'] for legacy callers.
    """
    if get_unit_jv_fn is not None:
        unit_id = epi.get('unit_id')
        if unit_id not in (None, '', 0, '0'):
            return normalize_joint_venture_name(get_unit_jv_fn(unit_id))
    return normalize_joint_venture_name(epi.get('active_joinventure'))


def filter_epis_for_unit(
    epis: Iterable[Mapping[str, object]],
    *,
    target_unit_id: object,
    target_unit_joint_venture_name: object,
    get_epi_unit_jv_name=None,
) -> list[dict]:
    """Filter EPIs visible to a target unit.

    get_epi_unit_jv_name: optional callable(unit_id) -> str that reads from
    unit_joint_venture_periods. When provided it replaces epis.active_joinventure
    as source of truth for the EPI's JV context.
    """
    filtered = []
    for epi in epis:
        epi_jv = get_epi_effective_jv_name(epi, get_epi_unit_jv_name)
        if is_epi_visible_for_unit(
            epi_unit_id=epi.get('unit_id'),
            epi_joint_venture_name=epi_jv,
            target_unit_id=target_unit_id,
            target_unit_joint_venture_name=target_unit_joint_venture_name,
        ):
            filtered.append(dict(epi))
    return filtered
