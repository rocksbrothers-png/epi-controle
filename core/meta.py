"""Funções de metadados da aplicação (app_meta key-value store)."""


def get_meta(connection, key):
    with connection.cursor() as cursor:
        cursor.execute('SELECT value FROM app_meta WHERE key = %s', (key,))
        row = cursor.fetchone()
        return row['value'] if row else None


def set_meta(connection, key, value):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO app_meta (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value
            ''',
            (key, value),
        )
