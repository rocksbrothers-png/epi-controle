"""Quem enxerga a aba CNPJs.

A gestão de CNPJs é ato de cadastro societário: define matriz, filiais, SPEs e
sócias de Joint Venture da empresa. Isso pertence ao Administrador Geral e ao
Administrador de Registro — os dois perfis da cadeia hierárquica com mandato de
cadastro. Administrador Local e Gestor de EPI são perfis operacionais de
unidade: consomem o CNPJ (na entrega, na ficha, no cadastro de colaborador),
mas não o administram.

Os perfis operacionais continuam **lendo** os CNPJs normalmente — essa lista
chega pelo `/api/bootstrap`, que não passa por `legal_entities:view`. Por isso
retirar a permissão fecha a tela de gestão sem cegar nenhuma tela de operação;
os testes abaixo fixam as duas metades desse contrato.
"""


import os
import re

from core.permissions import (
    PERM_LEGAL_ENTITIES_CREATE,
    PERM_LEGAL_ENTITIES_DELETE,
    PERM_LEGAL_ENTITIES_UPDATE,
    PERM_LEGAL_ENTITIES_VIEW,
    PERMISSIONS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cadeia hierárquica da empresa + o Master, que opera a plataforma pelo fluxo
# de suporte (abre os CNPJs do cliente) e por isso fica de fora do recorte.
GESTAO_DE_CNPJ = {'general_admin', 'registry_admin', 'master_admin'}

# Perfis operacionais de unidade: usam o CNPJ, não o administram.
OPERACIONAIS = ('admin', 'user')


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _roles_with(permission):
    return {role for role, perms in PERMISSIONS.items() if permission in perms}


def test_only_registration_profiles_see_the_tab():
    assert _roles_with(PERM_LEGAL_ENTITIES_VIEW) == GESTAO_DE_CNPJ


def test_operational_profiles_lost_the_tab():
    """O caso reportado: o Gestor de EPI abria a aba CNPJs."""
    for role in OPERACIONAIS:
        assert PERM_LEGAL_ENTITIES_VIEW not in PERMISSIONS[role], role


def test_view_matches_who_can_actually_manage():
    """Ver a aba e poder agir nela andam juntos.

    Um perfil que abre a tela e esbarra em erro a cada botão é pior do que não
    ter a tela: parece falha do sistema, não falta de alçada.
    """
    for permission in (
        PERM_LEGAL_ENTITIES_CREATE,
        PERM_LEGAL_ENTITIES_UPDATE,
        PERM_LEGAL_ENTITIES_DELETE,
    ):
        assert _roles_with(permission) == _roles_with(PERM_LEGAL_ENTITIES_VIEW), permission


# ── a operação não pode ser afetada ───────────────────────────────────────────

def test_operational_profiles_keep_the_data_they_need():
    """Perfis operacionais seguem com as telas que *consomem* CNPJ."""
    for role in OPERACIONAIS:
        perms = PERMISSIONS[role]
        assert 'employees:view' in perms, role
        assert 'deliveries:view' in perms, role
        assert 'fichas:view' in perms, role


def test_bootstrap_still_serves_legal_entities_without_the_permission():
    """A lista de CNPJs do bootstrap não passa por `legal_entities:view`.

    É ela que alimenta o seletor de CNPJ no cadastro de colaborador e o
    vínculo mostrado na ficha. Se algum dia passar a exigir a permissão, os
    perfis operacionais perdem esses campos silenciosamente — este teste
    quebra antes disso.
    """
    source = _read('modules', 'auth', 'service.py')
    match = re.search(
        r"'legal_entities':\s*_safe_bootstrap_section\((.*?)\),\n", source, re.S
    )
    assert match, 'seção legal_entities do bootstrap não encontrada'
    assert 'PERM_LEGAL_ENTITIES_VIEW' not in match.group(1)
    assert 'authorize_action' not in match.group(1)


# ── front-ends ────────────────────────────────────────────────────────────────

def test_legacy_web_gates_the_tab_on_the_same_permission():
    app_js = _read('static', 'app.js')
    match = re.search(r"cnpjs:\s*'([^']+)'", app_js)
    assert match, 'VIEW_PERMISSIONS.cnpjs não encontrada'
    assert match.group(1) == PERM_LEGAL_ENTITIES_VIEW


def test_flutter_gates_the_route_on_the_same_permission():
    """O app não pode divergir do web: mesma permissão, mesma aba.

    Como o Flutter lê a permissão do backend, retirar `legal_entities:view` de
    um perfil já fecha a rota no app — desde que o mapa continue apontando para
    esta permissão, e não para uma cópia divergente.
    """
    source = _read(
        'flutter', 'apps', 'epi_admin', 'lib', 'core', 'router', 'route_permissions.dart'
    )
    match = re.search(r"Routes\.legalEntities:\s*'([^']+)'", source)
    assert match, 'rota legalEntities não encontrada em route_permissions.dart'
    assert match.group(1) == PERM_LEGAL_ENTITIES_VIEW


def test_flutter_nav_item_uses_the_same_permission_as_the_route():
    """Item de menu e guarda de rota precisam concordar.

    Divergir aqui produz o pior dos casos: o item aparece no menu e a rota
    barra na entrada.
    """
    shell = _read('flutter', 'apps', 'epi_admin', 'lib', 'core', 'shell', 'app_shell.dart')
    match = re.search(r'Routes\.legalEntities,[^\n]*?\'([a-z_]+:[a-z_]+)\'', shell)
    assert match, 'item de menu de CNPJs não encontrado em app_shell.dart'
    assert match.group(1) == PERM_LEGAL_ENTITIES_VIEW
