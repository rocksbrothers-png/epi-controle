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
    """Return True when an EPI should appear for a specific unit context.

    Rules (C1+D1+E3 confirmed):
    - Unit NOT in JV: sees GLOBAL + its own UNIT EPIs.
    - Unit IN JV X: sees its own UNIT EPIs + EPIs scoped to JV X.
      GLOBAL is hidden. Other JVs are hidden.
    """
    if target_unit_id in (None, '', 0, '0'):
        return True

    target_unit_id_normalized = _safe_int(target_unit_id)
    if target_unit_id_normalized is None:
        return False
    epi_scope = resolve_scope_type(epi_unit_id, epi_joint_venture_name)
    target_jv = normalize_joint_venture_name(target_unit_joint_venture_name).lower()
    epi_jv = normalize_joint_venture_name(epi_joint_venture_name).lower()

    if target_jv:
        # Unidade em JV ativa
        if epi_scope == SCOPE_JOINT_VENTURE:
            # JV deve respeitar a JV ativa da unidade alvo. O vínculo de unidade
            # do cadastro do EPI não restringe a visibilidade quando a JV é a mesma.
            return bool(epi_jv) and epi_jv == target_jv
        if epi_scope == SCOPE_UNIT:
            epi_unit_id_normalized = _safe_int(epi_unit_id)
            return epi_unit_id_normalized is not None and epi_unit_id_normalized == target_unit_id_normalized
        # GLOBAL oculto em JV
        return False

    # Fora de JV
    if epi_scope == SCOPE_GLOBAL:
        return True
    if epi_scope == SCOPE_UNIT:
        epi_unit_id_normalized = _safe_int(epi_unit_id)
        return epi_unit_id_normalized is not None and epi_unit_id_normalized == target_unit_id_normalized
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
