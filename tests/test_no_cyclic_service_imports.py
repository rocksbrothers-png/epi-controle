"""Guarda de regressão para a issue #148 (CodeQL cyclic import).

O PR #147 (ADR-0002 §10.2/§10.3) e o PR #149 (§10.4) expuseram um ciclo de
import pré-existente e real (não falso-positivo) em duas frentes:

1. `core.schema` importava `modules.*` de dentro de `init_db()` (para
   provisionar o master admin inicial, tabelas comerciais/pagamento,
   backfill de estoque etc.) — isso tornava `core.schema`, que deveria ser
   a camada mais baixa do projeto, parte do mesmo SCC (strongly connected
   component) de praticamente todo módulo de domínio alcançável a partir de
   `modules.auth.service`. Corrigido movendo `init_db()` inteiro para
   `core.bootstrap` — uma camada de orquestração que fica ACIMA de
   `core.schema` e de `modules.*` e nunca é importada de volta por nenhum
   dos dois.
2. `modules.legal_entities.service` importava localmente
   `modules.employees.service.actor_operational_unit_id` dentro de
   `resolve_actor_legal_entity_ids`, fechando o ciclo
   employees -> units -> legal_entities -> employees. Corrigido movendo
   `actor_operational_unit_id` para `core.repository` (camada
   independente, sem dependência de nenhum módulo de domínio) e
   reexportando-o em `modules.employees.service` para não quebrar os ~15
   chamadores existentes.

Este teste constrói o grafo de imports do repositório inteiro via `ast`
(cobre `import`/`from` de topo de arquivo E locais/deferidos dentro de
função — os cyclic imports do CodeQL nesta issue eram todos via import
local) e verifica que nenhum SCC com mais de um módulo continua alcançável
a partir dos módulos citados na issue. Não usa `sys.modules`/import real
porque o objetivo é a ESTRUTURA declarada do grafo, não o comportamento em
runtime (que um import local bem colocado pode mascarar sem resolver a
causa raiz — exatamente o antipadrão que a issue pediu para evitar).
"""

import ast
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = ('core', 'modules', 'epi_backend')

# Módulos citados explicitamente na issue #148 (os dois ciclos) — a
# regressão a evitar é qualquer um destes voltar a fazer parte de um SCC.
#
# modules.auth.service fica de fora deste conjunto de propósito: ele faz
# parte de um ciclo PRÉ-EXISTENTE e não relacionado (modules.auth.service
# <-> modules.companies.service, fora do escopo desta issue — não é um dos
# alertas do CodeQL listados nela, e não foi introduzido nem agravado pelos
# PRs #147/#149). O envolvimento de modules.auth.service especificamente
# NESTA issue (core.schema -> modules.auth.service) já é coberto de forma
# precisa por test_core_schema_never_imports_domain_modules abaixo.
WATCHED_MODULES = (
    'core.schema',
    'core.archival',
    'core.bootstrap',
    'modules.employees.service',
    'modules.units.service',
    'modules.legal_entities.service',
    'modules.outsourced_companies.service',
)


def _module_name_for(path):
    rel = os.path.relpath(path, ROOT)
    rel = rel[:-3] if rel.endswith('.py') else rel
    return rel.replace(os.sep, '.')


def _resolve_relative(base_module, node_module, level):
    parts = base_module.split('.')
    if level > 0:
        parts = parts[:-level]
    if node_module:
        parts = parts + node_module.split('.')
    return '.'.join(parts)


def _build_import_graph():
    """{module: {module_importado, ...}} cobrindo imports de topo E locais."""
    edges = defaultdict(set)
    for pkg in PACKAGES:
        pkg_dir = os.path.join(ROOT, pkg)
        for dirpath, _dirnames, filenames in os.walk(pkg_dir):
            if '__pycache__' in dirpath:
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                path = os.path.join(dirpath, filename)
                module = _module_name_for(path)
                try:
                    with open(path, encoding='utf-8') as source_file:
                        source = source_file.read()
                    tree = ast.parse(source, filename=path)
                except SyntaxError:
                    continue

                def walk(node):
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, ast.Import):
                            for alias in child.names:
                                if alias.name.split('.')[0] in PACKAGES:
                                    edges[module].add(alias.name)
                        elif isinstance(child, ast.ImportFrom):
                            if child.level and child.level > 0:
                                target = _resolve_relative(module, child.module or '', child.level)
                            else:
                                target = child.module or ''
                            if target.split('.')[0] in PACKAGES:
                                edges[module].add(target)
                        walk(child)

                walk(tree)

    known = set(edges.keys())

    def nearest_known(target):
        parts = target.split('.')
        while parts:
            candidate = '.'.join(parts)
            if candidate in known:
                return candidate
            parts = parts[:-1]
        return None

    graph = defaultdict(set)
    for src, targets in edges.items():
        for target in targets:
            resolved = nearest_known(target)
            if resolved and resolved != src:
                graph[src].add(resolved)
    return graph


def _find_cycle(graph, start):
    """DFS simples: devolve um ciclo alcançável a partir de `start`, se existir."""
    stack = [(start, [start])]
    while stack:
        node, path = stack.pop()
        for nxt in graph.get(node, ()):
            if nxt == start and len(path) > 1:
                return path + [nxt]
            if nxt not in path:
                stack.append((nxt, path + [nxt]))
    return None


def test_no_cycle_reachable_from_watched_modules():
    graph = _build_import_graph()
    problems = []
    for module in WATCHED_MODULES:
        cycle = _find_cycle(graph, module)
        if cycle:
            problems.append(f"{module}: {' -> '.join(cycle)}")
    assert not problems, (
        'Ciclo de import (CodeQL cyclic import, issue #148) reintroduzido:\n' + '\n'.join(problems)
    )


def test_core_schema_never_imports_domain_modules():
    """Invariante estrutural do fix: core.schema é a camada mais baixa do
    projeto e nunca deve depender de modules.* (nem de topo, nem localmente
    dentro de função) — quem orquestra os dois é core.bootstrap."""
    graph = _build_import_graph()
    domain_imports = {t for t in graph.get('core.schema', set()) if t.startswith('modules.')}
    assert not domain_imports, (
        f'core.schema importa modules.* de volta: {sorted(domain_imports)} — '
        'isso reintroduz o ciclo da issue #148. Novos hooks de bootstrap/seed '
        'que precisem de modules.* pertencem a core.bootstrap, não a core.schema.'
    )


def test_legal_entities_service_never_imports_employees_service():
    """Invariante estrutural do segundo fix: legal_entities resolve a
    unidade operacional do ator via core.repository.actor_operational_unit_id
    (camada independente), nunca importando modules.employees.service de
    volta."""
    graph = _build_import_graph()
    assert 'modules.employees.service' not in graph.get('modules.legal_entities.service', set())


def test_actor_operational_unit_id_lives_in_core_repository():
    """Reexportado (não redefinido) em modules.employees.service, para que
    os ~15 chamadores existentes (`from modules.employees.service import
    actor_operational_unit_id`) continuem funcionando sem alteração."""
    from core.repository import actor_operational_unit_id as from_repository
    from modules.employees.service import actor_operational_unit_id as from_employees

    assert from_employees is from_repository


def test_init_db_lives_in_core_bootstrap_not_core_schema():
    import core.schema as schema
    from core.bootstrap import init_db

    assert callable(init_db)
    assert not hasattr(schema, 'init_db')
