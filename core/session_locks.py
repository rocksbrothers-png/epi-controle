"""Advisory lock de SESSÃO sobre uma conexão que volta a um pool (P0.1).

``pg_advisory_lock``/``pg_try_advisory_lock`` pertencem à SESSÃO do banco:
``ROLLBACK`` e ``COMMIT`` não os soltam, e eles são reentrantes (duas
aquisições exigem duas liberações). Uma conexão devolvida ao pool com o lock
ainda preso entrega o lock à próxima requisição que a reutilizar.

Esta classe acompanha o que se SABE sobre o lock e responde a uma pergunta:
a conexão pode voltar ao pool? Só quando há certeza de que nada ficou preso.
Em qualquer dúvida a conexão é DESCARTADA — fechar a sessão no servidor é a
única liberação garantida:

* a tentativa de aquisição levantou exceção (o servidor pode ter concedido o
  lock antes de a resposta se perder);
* o lock foi adquirido e ainda não foi liberado (inclui saída por exceção);
* a liberação levantou exceção, ou devolveu ``false`` (o servidor diz que
  esta sessão não detinha o lock — sinal de que aquisição e liberação caíram
  em sessões diferentes, como atrás de um pooler em modo transação).

Uma vez em dúvida, a dúvida não é desfeita por uma liberação posterior bem
sucedida: o lock é reentrante e a contagem real é desconhecida.
"""


def _first_value(row):
    if row is None:
        return None
    values = getattr(row, 'values', None)
    if callable(values):
        return next(iter(values()), None)
    return row[0]


class SessionAdvisoryLock:
    def __init__(self, connection, *, acquire_sql, release_sql, params):
        self._connection = connection
        self._acquire_sql = acquire_sql
        self._release_sql = release_sql
        self._params = tuple(params)
        self.held = 0
        self.uncertain = False

    def try_acquire(self):
        """True se o lock foi concedido. Exceção → estado incerto e relança."""
        try:
            row = self._connection.execute(self._acquire_sql, self._params).fetchone()
        except BaseException:
            self.uncertain = True
            raise
        acquired = bool(_first_value(row))
        if acquired:
            self.held += 1
        return acquired

    def release(self):
        """True se o servidor confirmou a liberação. Qualquer outra coisa → incerto."""
        try:
            row = self._connection.execute(self._release_sql, self._params).fetchone()
        except BaseException:
            self.uncertain = True
            raise
        released = bool(_first_value(row))
        if released and self.held > 0:
            self.held -= 1
        else:
            self.uncertain = True
        return released

    @property
    def must_discard(self):
        return self.uncertain or self.held > 0

    def finish(self):
        """Devolve a conexão ao pool — ou a descarta se algo pode ter ficado preso."""
        connection = self._connection
        if self.must_discard and hasattr(connection, 'discard'):
            connection.discard()
        else:
            connection.close()
