"""'epi_manager' é apelido de 'user' — não um papel separado.

`core/roles.py` (`ROLE_ALIASES`) sempre normaliza 'epi_manager' (e as
variantes 'gestor_epi', 'gestor_de_epi', 'gestor', 'manager') para 'user'
antes de qualquer checagem de permissão — `normalize_role_name` roda em todo
lugar que resolve o `role` do ator (`modules/auth/service.py`). Por isso
`actor['role'] == 'epi_manager'` nunca acontece de fato em produção.

Apesar disso, o dict `PERMISSIONS` chegou a manter uma entrada
`PERMISSIONS['epi_manager']` separada e DIVERGENTE de `PERMISSIONS['user']`
(sem `deliveries:create`/`stock:adjust`, mas com `ppe_test:triage`,
`ppe_test:tech_review`, `epi_feedback:hseq_review` e `epi_feedback:create`).
Como a entrada nunca era alcançada, essas quatro capacidades — triagem e
revisão técnica de EPI em teste, revisão HSEQ e criação de feedback — não
pertenciam a nenhum papel atingível: rotas reais em
`modules/ppe_tests/routes.py` e `modules/feedback/routes.py` ficaram
inacessíveis para todo mundo. O mesmo bug se repetia em `static/app.js`
(`canSeeDestaques`, `ROLE_PERMISSIONS.user`).

Este teste fixa a consolidação: 'epi_manager' deixa de ser uma entrada
própria em `PERMISSIONS`, e 'user' (Gestor de EPI) passa a ter a união das
duas — restaurando as quatro capacidades que estavam órfãs.
"""

import os
import re

from core.permissions import (
    PERM_EPI_FEEDBACK_CREATE,
    PERM_EPI_FEEDBACK_HSEQ_REVIEW,
    PERM_PPE_TEST_TECH_REVIEW,
    PERM_PPE_TEST_TRIAGE,
    PERMISSIONS,
)
from core.roles import ROLE_ALIASES, normalize_role_name

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def test_epi_manager_is_not_a_separate_permissions_entry():
    """Uma entrada duplicada e divergente é o próprio bug: se alguém editar
    'user' sem saber que 'epi_manager' existe (ou vice-versa), as duas voltam
    a divergir e alguma capacidade fica órfã de novo."""
    assert 'epi_manager' not in PERMISSIONS


def test_epi_manager_and_its_variants_normalize_to_user():
    for alias in ('epi_manager', 'gestor_epi', 'gestor_de_epi', 'gestor', 'manager'):
        assert normalize_role_name(alias) == 'user', alias
    assert ROLE_ALIASES['epi_manager'] == 'user'


def test_user_has_the_previously_orphaned_capabilities():
    """As quatro permissões que só 'epi_manager' tinha, e que nenhum papel
    atingível possuía por causa disso."""
    perms = PERMISSIONS['user']
    assert PERM_PPE_TEST_TRIAGE in perms
    assert PERM_PPE_TEST_TECH_REVIEW in perms
    assert PERM_EPI_FEEDBACK_HSEQ_REVIEW in perms
    assert PERM_EPI_FEEDBACK_CREATE in perms


def test_no_role_check_in_the_legacy_web_uses_the_unreachable_alias():
    """`state.user.role` sempre chega normalizado como 'user' — uma checagem
    de role que compare com o literal 'epi_manager' nunca bate (foi o caso de
    `canSeeDestaques`, que escondia os destaques do Gestor de EPI)."""
    app_js = _read('static', 'app.js')
    assert "'epi_manager'" not in app_js
    assert '"epi_manager"' not in app_js


def test_diagnostic_role_permissions_table_matches_the_backend():
    """`ROLE_PERMISSIONS` no app.js é só uma tabela de diagnóstico (usada num
    console.warn de acesso negado) — não decide autorização real, que sempre
    lê `state.permissions` do backend. Mas uma tabela de diagnóstico
    desatualizada mente no log. Trava que o conjunto de 'user' bate com o
    backend, para as permissões restauradas por este commit."""
    app_js = _read('static', 'app.js')
    match = re.search(r"user:\s*\[([^\]]*)\]", app_js)
    assert match, 'ROLE_PERMISSIONS.user não encontrada'
    js_perms = set(re.findall(r"'([a-z_]+:[a-z_]+)'", match.group(1)))
    for perm in (
        PERM_PPE_TEST_TRIAGE, PERM_PPE_TEST_TECH_REVIEW,
        PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE,
    ):
        assert perm in js_perms, perm
