"""Despachante HTTP central para o EPI Controle.

Cada módulo registra seus handlers via router.register().
server_postgres.py chama router.dispatch() em do_GET/do_POST/do_PUT/do_DELETE.

Assinatura padrão dos handlers:
    handler_func(handler_obj, parsed, payload, match) -> response
onde:
  - handler_obj : instância EpiHandler (o 'self' do método HTTP)
  - parsed      : resultado de urlparse(self.path)
  - payload     : dict JSON do corpo (None para GET/DELETE)
  - match       : re.Match se a rota usou regex, None caso contrário
"""

import re


class Router:
    def __init__(self):
        # (method, path_or_pattern_str, compiled_pattern_or_None, handler)
        self._routes: list = []

    def register(self, method: str, path: str, handler, *, regex: bool = False):
        """Registra um handler para (method, path).

        Quando regex=True, path é compilado como padrão regex com re.match.
        """
        pattern = re.compile(path) if regex else None
        self._routes.append((method.upper(), path, pattern, handler))

    def dispatch(self, method: str, path: str, handler_obj, parsed, payload=None):
        """Tenta despachar a requisição ao handler registrado.

        Retorna o resultado do handler quando encontrado, ou None para que
        server_postgres.py continue com seu fallback existente.
        """
        for route_method, route_path, pattern, route_handler in self._routes:
            if route_method != method.upper():
                continue
            if pattern is not None:
                m = pattern.match(path)
                if m:
                    return route_handler(handler_obj, parsed, payload, m)
            else:
                if route_path == path:
                    return route_handler(handler_obj, parsed, payload, None)
        return None


# Instância global — importada por server_postgres.py e pelos módulos
router = Router()
