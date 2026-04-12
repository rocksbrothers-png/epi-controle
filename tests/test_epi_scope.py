"""Testes da regra de visibilidade de EPIs (C1+D1+E3 confirmada).

Regra:
- Fora de JV: GLOBAL + UNIT propria visiveis.
- Em JV X: UNIT propria + JV de X visiveis. GLOBAL oculto.
"""
from epi_backend.epi_scope import is_epi_visible_for_unit

UNIT_A = 1
UNIT_B = 2
JV_X = 'Alpha'
JV_Y = 'Beta'


# ---------- Unidade FORA de JV ----------

def test_global_visivel_fora_de_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=None, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=None,
    ) is True


def test_unit_propria_visivel_fora_de_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=None,
    ) is True


def test_unit_de_outra_unidade_invisivel():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_B, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=None,
    ) is False


def test_jv_invisivel_fora_de_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=JV_X,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=None,
    ) is False


# ---------- Unidade DENTRO de JV X ----------

def test_global_oculto_em_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=None, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=JV_X,
    ) is False


def test_unit_propria_visivel_em_jv():
    """UNIT da propria unidade continua visivel mesmo em JV (so GLOBAL some)."""
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=JV_X,
    ) is True


def test_unit_de_outra_unidade_invisivel_em_jv():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_B, epi_joint_venture_name=None,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=JV_X,
    ) is False


def test_jv_propria_visivel():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=JV_X,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=JV_X,
    ) is True


def test_jv_de_outra_jv_invisivel():
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=JV_Y,
        target_unit_id=UNIT_A, target_unit_joint_venture_name=JV_X,
    ) is False


def test_sem_target_unit_tudo_visivel():
    """Quando target_unit_id nao informado, tudo eh visivel."""
    assert is_epi_visible_for_unit(
        epi_unit_id=UNIT_A, epi_joint_venture_name=JV_X,
        target_unit_id=None, target_unit_joint_venture_name=JV_X,
    ) is True
