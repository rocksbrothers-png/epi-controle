from __future__ import annotations

from typing import Iterable, Mapping

SCOPE_GLOBAL = 'GLOBAL'
SCOPE_UNIT = 'UNIT'
SCOPE_JOINT_VENTURE = 'JOINT_VENTURE'
VALID_SCOPE_TYPES = {SCOPE_GLOBAL, SCOPE_UNIT, SCOPE_JOINT_VENTURE}


def normalize_joint_venture_name(value: object) -> str:
    return str(value or '').strip()


def resolve_scope_type(unit_id: object, joint_venture_name: object) -> str:
    if normalize_joint_venture_name(joint_venture_name):
        return SCOPE_JOINT_VENTURE
    if unit_id not in (None, '', 0, '0'):
        return SCOPE_UNIT
    return SCOPE_GLOBAL


def is_epi_visible_for_unit(
    *,
    epi_unit_id: object,
    epi_joint_venture_name: object,
    target_unit_id: object,
    target_unit_joint_venture_name: object,
) -> bool:
    """Return True when an EPI should appear for a specific unit context.

    Rules:
    - Unit in GLOBAL mode: sees GLOBAL + its own UNIT EPIs.
    - Unit in JV mode: sees only EPIs scoped to this same active JV in this unit.
    """

    if target_unit_id in (None, '', 0, '0'):
        return True

    target_unit_id = int(target_unit_id)
    epi_scope = resolve_scope_type(epi_unit_id, epi_joint_venture_name)
    target_jv = normalize_joint_venture_name(target_unit_joint_venture_name).lower()
    epi_jv = normalize_joint_venture_name(epi_joint_venture_name).lower()

    if target_jv:
        return (
            epi_scope == SCOPE_JOINT_VENTURE
            and epi_unit_id not in (None, '', 0, '0')
            and int(epi_unit_id) == target_unit_id
            and epi_jv == target_jv
        )

    if epi_scope == SCOPE_GLOBAL:
        return True
    if epi_scope == SCOPE_UNIT:
        return epi_unit_id not in (None, '', 0, '0') and int(epi_unit_id) == target_unit_id
    return False


def filter_epis_for_unit(
    epis: Iterable[Mapping[str, object]],
    *,
    target_unit_id: object,
    target_unit_joint_venture_name: object,
) -> list[dict]:
    filtered = []
    for epi in epis:
        if is_epi_visible_for_unit(
            epi_unit_id=epi.get('unit_id'),
            epi_joint_venture_name=epi.get('active_joinventure'),
            target_unit_id=target_unit_id,
            target_unit_joint_venture_name=target_unit_joint_venture_name,
        ):
            filtered.append(dict(epi))
    return filtered
