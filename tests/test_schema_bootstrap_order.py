"""Ordem das migrações de bootstrap × dependências de chave estrangeira.

Existe por causa de um defeito real: `ensure_stock_reservations` e
`ensure_stock_replenishment_needs` rodavam **antes** de
`ensure_epi_operational_tables`, que é quem cria `epi_requests` e
`purchase_requests` — as tabelas que elas referenciam.

O SQLite aceita `FOREIGN KEY ... REFERENCES tabela_inexistente` no `CREATE
TABLE` (a resolução é adiada), então toda a suíte passava. O PostgreSQL recusa
na hora, e a criação de um banco **do zero** falhava inteira, deixando o
sistema sem subir. Só aparecia em instalação nova — nunca em banco já migrado.

O teste lê a ordem declarada em `init_db` porque é ela que decide a execução.
"""

import inspect
import re

from core import schema


def _bootstrap_order() -> list:
    """Nomes das funções `ensure_*` na ordem em que `init_db` as executa."""
    source = inspect.getsource(schema.init_db)
    block = source[source.index('_ensure_fns = ['):]
    block = block[:block.index(']')]
    # Ignora comentários: só o que está na lista conta como execução.
    lines = [line.split('#', 1)[0].strip() for line in block.splitlines()]
    return [name.rstrip(',') for name in lines if re.fullmatch(r'_?ensure_\w+,', name)]


def _referenced_tables(fn) -> set:
    """Tabelas citadas em `REFERENCES` dentro do SQL da função."""
    return {
        match.group(1)
        for match in re.finditer(r'REFERENCES\s+(\w+)\s*\(', inspect.getsource(fn))
    }


def _created_tables(fn) -> set:
    return {
        match.group(1)
        for match in re.finditer(
            r'CREATE TABLE IF NOT EXISTS\s+(\w+)', inspect.getsource(fn)
        )
    }


def test_new_stock_tables_run_after_their_foreign_key_targets():
    """Regressão direta: as duas tabelas do fluxo de estoque vêm depois."""
    order = _bootstrap_order()
    operational = order.index('ensure_epi_operational_tables')
    for name in ('ensure_stock_reservations', 'ensure_stock_replenishment_needs'):
        assert order.index(name) > operational, (
            f'{name} roda antes de ensure_epi_operational_tables. Ela referencia '
            'epi_requests/purchase_requests, criadas lá — no PostgreSQL a criação '
            'do banco do zero falha inteira.'
        )


def test_every_ensure_function_runs_after_the_tables_it_references():
    """Generaliza a regra em vez de fixar só o caso que quebrou.

    Para cada `ensure_*` da lista, toda tabela que ela referencia por FK e que
    é criada por alguma outra `ensure_*` precisa ter sido criada antes.
    Referências a tabelas criadas fora da lista (no script base de `init_db`)
    não entram — aquelas já existem quando a lista começa.
    """
    order = _bootstrap_order()
    functions = {name: getattr(schema, name.lstrip('_'), None) for name in order}
    creators = {}
    for position, name in enumerate(order):
        fn = functions.get(name)
        if fn is None:
            continue
        for table in _created_tables(fn):
            creators.setdefault(table, position)

    problems = []
    for position, name in enumerate(order):
        fn = functions.get(name)
        if fn is None:
            continue
        for table in _referenced_tables(fn):
            created_at = creators.get(table)
            if created_at is not None and created_at > position:
                problems.append(f'{name} referencia {table}, criada depois por {order[created_at]}')

    assert not problems, 'Dependência invertida no bootstrap: ' + '; '.join(problems)
