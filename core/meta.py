"""Funções de metadados da aplicação (app_meta key-value store)."""
from epi_backend.db import row_to_dict


def get_meta(connection, key):
    row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (key,)).fetchone()
    if row is None:
        return None
    item = row_to_dict(row)
    return item['value'] if item else None


def set_meta(connection, key, value):
    connection.execute(
        '''
        INSERT INTO app_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT (key)
        DO UPDATE SET value = excluded.value
        ''',
        (key, value),
    )
