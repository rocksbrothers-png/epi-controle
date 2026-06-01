"""Legacy entry point — delegado para app.py.

Mantido para compatibilidade com Dockerfile, scripts e testes existentes que
importam symbols deste módulo. O entry point canônico é app.py.

Para subir o servidor use: python app.py
"""
from app import *  # noqa: F401, F403
# Nomes privados não re-exportados por * — importados explicitamente para
# manter compatibilidade com testes e scripts que os acessam diretamente.
from app import (  # noqa: F401
    _ensure_ficha_periods_sequence_unique,
    _get_bootstrap_state,
    _safe_add_column,
    _set_bootstrap_state,
)

if __name__ == '__main__':
    from app import main
    main()
