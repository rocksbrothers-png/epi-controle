warning: in the working copy of 'epi_backend/epi_scope.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/epi_backend/epi_scope.py b/epi_backend/epi_scope.py[m
[1mindex cbc4630..6d6c868 100644[m
[1m--- a/epi_backend/epi_scope.py[m
[1m+++ b/epi_backend/epi_scope.py[m
[36m@@ -1 +1,77 @@[m
[31m-fix(epi_scope): UNIT visivel em JV, so GLOBAL oculto (C1+D1+E3 #144)[m
[32m+[m[32mfrom __future__ import annotations[m
[32m+[m
[32m+[m[32mfrom typing import Iterable, Mapping[m
[32m+[m
[32m+[m[32mSCOPE_GLOBAL = 'GLOBAL'[m
[32m+[m[32mSCOPE_UNIT = 'UNIT'[m
[32m+[m[32mSCOPE_JOINT_VENTURE = 'JOINT_VENTURE'[m
[32m+[m[32mVALID_SCOPE_TYPES = {SCOPE_GLOBAL, SCOPE_UNIT, SCOPE_JOINT_VENTURE}[m
[32m+[m
[32m+[m
[32m+[m[32mdef normalize_joint_venture_name(value: object) -> str:[m
[32m+[m[32m    return str(value or '').strip()[m
[32m+[m
[32m+[m
[32m+[m[32mdef resolve_scope_type(unit_id: object, joint_venture_name: object) -> str:[m
[32m+[m[32m    if normalize_joint_venture_name(joint_venture_name):[m
[32m+[m[32m        return SCOPE_JOINT_VENTURE[m
[32m+[m[32m    if unit_id not in (None, '', 0, '0'):[m
[32m+[m[32m        return SCOPE_UNIT[m
[32m+[m[32m    return SCOPE_GLOBAL[m
[32m+[m
[32m+[m
[32m+[m[32mdef is_epi_visible_for_unit([m
[32m+[m[32m    *,[m
[32m+[m[32m    epi_unit_id: object,[m
[32m+[m[32m    epi_joint_venture_name: object,[m
[32m+[m[32m    target_unit_id: object,[m
[32m+[m[32m    target_unit_joint_venture_name: object,[m
[32m+[m[32m) -> bool:[m
[32m+[m[32m    """Return True when an EPI should appear for a specific unit context."""[m
[32m+[m
[32m+[m[32m    if target_unit_id in (None, '', 0, '0'):[m
[32m+[m[32m        return True[m
[32m+[m
[32m+[m[32m    target_unit_id = int(target_unit_id)[m
[32m+[m[32m    epi_scope = resolve_scope_type(epi_unit_id, epi_joint_venture_name)[m
[32m+[m[32m    target_jv = normalize_joint_venture_name(target_unit_joint_venture_name).lower()[m
[32m+[m[32m    epi_jv = normalize_joint_venture_name(epi_joint_venture_name).lower()[m
[32m+[m[32m    same_unit = epi_unit_id not in (None, '', 0, '0') and int(epi_unit_id) == target_unit_id[m
[32m+[m
[32m+[m[32m    if target_jv:[m
[32m+[m[32m        if epi_scope == SCOPE_GLOBAL:[m
[32m+[m[32m            return False[m
[32m+[m[32m        if epi_scope == SCOPE_UNIT:[m
[32m+[m[32m            return same_unit[m
[32m+[m[32m        return same_unit and epi_jv == target_jv[m
[32m+[m
[32m+[m[32m    if epi_scope == SCOPE_GLOBAL:[m
[32m+[m[32m        return True[m
[32m+[m[32m    if epi_scope == SCOPE_UNIT:[m
[32m+[m[32m        return same_unit[m
[32m+[m[32m    return False[m
[32m+[m
[32m+[m
[32m+[m[32mdef filter_epis_for_unit([m
[32m+[m[32m    epis: Iterable[Mapping[str, object]],[m
[32m+[m[32m    *,[m
[32m+[m[32m    target_unit_id: object,[m
[32m+[m[32m    target_unit_joint_venture_name: object,[m
[32m+[m[32m) -> list[dict]:[m
[32m+[m[32m    filtered = [][m
[32m+[m[32m    target_jv = normalize_joint_venture_name(target_unit_joint_venture_name).lower()[m
[32m+[m[32m    for epi in epis:[m
[32m+[m[32m        if target_jv:[m
[32m+[m[32m            same_unit = epi.get('unit_id') not in (None, '', 0, '0') and int(epi.get('unit_id')) == int(target_unit_id)[m
[32m+[m[32m            epi_jv = normalize_joint_venture_name(epi.get('active_joinventure')).lower()[m
[32m+[m[32m            if same_unit and epi_jv == target_jv:[m
[32m+[m[32m                filtered.append(dict(epi))[m
[32m+[m[32m            continue[m
[32m+[m[32m        if is_epi_visible_for_unit([m
[32m+[m[32m            epi_unit_id=epi.get('unit_id'),[m
[32m+[m[32m            epi_joint_venture_name=epi.get('active_joinventure'),[m
[32m+[m[32m            target_unit_id=target_unit_id,[m
[32m+[m[32m            target_unit_joint_venture_name=target_unit_joint_venture_name,[m
[32m+[m[32m        ):[m
[32m+[m[32m            filtered.append(dict(epi))[m
[32m+[m[32m    return filtered[m
