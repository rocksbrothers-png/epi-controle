from epi_backend.epi_scope import (
    SCOPE_GLOBAL,
    SCOPE_JOINT_VENTURE,
    SCOPE_UNIT,
    filter_epis_for_unit,
    is_epi_visible_for_unit,
    resolve_scope_type,
)


def test_resolve_scope_type_variants():
    assert resolve_scope_type(None, None) == SCOPE_GLOBAL
    assert resolve_scope_type(10, '') == SCOPE_UNIT
    assert resolve_scope_type(10, 'Petrobras-DOF') == SCOPE_JOINT_VENTURE


def test_global_unit_sees_global_and_its_unit_only():
    assert is_epi_visible_for_unit(
        epi_unit_id=None,
        epi_joint_venture_name='',
        target_unit_id=1,
        target_unit_joint_venture_name='',
    )
    assert is_epi_visible_for_unit(
        epi_unit_id=1,
        epi_joint_venture_name='',
        target_unit_id=1,
        target_unit_joint_venture_name='',
    )
    assert not is_epi_visible_for_unit(
        epi_unit_id=2,
        epi_joint_venture_name='',
        target_unit_id=1,
        target_unit_joint_venture_name='',
    )


def test_global_unit_hides_joint_venture_epis():
    assert not is_epi_visible_for_unit(
        epi_unit_id=1,
        epi_joint_venture_name='JV-X',
        target_unit_id=1,
        target_unit_joint_venture_name='',
    )


def test_unit_in_jv_sees_only_same_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=1,
        epi_joint_venture_name='JV-X',
        target_unit_id=1,
        target_unit_joint_venture_name='JV-X',
    )
    assert not is_epi_visible_for_unit(
        epi_unit_id=None,
        epi_joint_venture_name='',
        target_unit_id=1,
        target_unit_joint_venture_name='JV-X',
    )
    assert not is_epi_visible_for_unit(
        epi_unit_id=1,
        epi_joint_venture_name='JV-Y',
        target_unit_id=1,
        target_unit_joint_venture_name='JV-X',
    )


def test_other_unit_never_sees_foreign_jv():
    assert not is_epi_visible_for_unit(
        epi_unit_id=2,
        epi_joint_venture_name='JV-X',
        target_unit_id=1,
        target_unit_joint_venture_name='JV-X',
    )


def test_filter_epis_for_unit_respects_state_transition():
    epis = [
        {'id': 1, 'unit_id': None, 'active_joinventure': None},
        {'id': 2, 'unit_id': 1, 'active_joinventure': None},
        {'id': 3, 'unit_id': 1, 'active_joinventure': 'JV-X'},
    ]

    global_ids = [row['id'] for row in filter_epis_for_unit(epis, target_unit_id=1, target_unit_joint_venture_name='')]
    jv_ids = [row['id'] for row in filter_epis_for_unit(epis, target_unit_id=1, target_unit_joint_venture_name='JV-X')]

    assert global_ids == [1, 2]
    assert jv_ids == [3]
