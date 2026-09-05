"""Regra ÚNICA de "o certificador não escreve em produção".

Vive fora dos arquivos de teste porque três gates a consomem — os de #271
(`test_271_preflight.py`, `test_271b4_certificacao_de_superficies.py`) e os de
#313 (`test_313_certificador_autentica.py`). Duas cópias da mesma regra
divergem no primeiro ajuste feito num lado só, e aqui a divergência custaria
caro: um dos lados passaria a permitir uma escrita que o outro proíbe, e quem
lesse só um deles concluiria que produção está protegida.

A regra tem uma exceção, e ela é TIPADA, não uma licença: exatamente um
`POST` para a constante `ROTA_LOGIN` (que precisa valer `/api/login`), dentro
de `_login`, com `data=` só nele. Introduzida pela #313 para acabar com o JWT
de 8 horas renovado à mão.
"""

import ast


def escritas_indevidas(fonte: str) -> str:
    """'' quando o certificador só escreve no login. Caso contrário, o motivo.

    Devolve string em vez de levantar para que as fixtures de não-vacuidade da
    #313 possam afirmar QUAL mutação foi detectada — um matcher que reprova
    tudo por qualquer motivo não distingue "pegou a sabotagem" de "quebrou".
    """
    arvore = ast.parse(fonte)

    dentro_do_login = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == '_login':
            dentro_do_login = {filho for filho in ast.walk(no)}

    requests = [no for no in ast.walk(arvore)
                if isinstance(no, ast.Call)
                and getattr(no.func, 'attr', '') == 'Request']
    if not requests:
        return 'nenhuma `urllib.request.Request` encontrada — matcher quebrado'

    posts = []
    for chamada in requests:
        metodo = {k.arg: k.value for k in chamada.keywords}.get('method')
        if not isinstance(metodo, ast.Constant):
            return 'requisição sem `method=` literal'
        if metodo.value == 'GET':
            continue
        if metodo.value != 'POST':
            return f'método {metodo.value!r}: só GET, e POST no login'
        posts.append(chamada)

    if len(posts) > 1:
        return f'{len(posts)} requisições POST: só o login pode escrever'
    if not posts:
        return ''

    login = posts[0]
    if login not in dentro_do_login:
        return 'o POST não está dentro de `_login`'
    url = login.args[0] if login.args else None
    nomes = {n.id for n in ast.walk(url) if isinstance(n, ast.Name)} if url else set()
    if 'ROTA_LOGIN' not in nomes:
        return 'a URL do POST não vem da constante `ROTA_LOGIN`'
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(
                isinstance(alvo_, ast.Name) and alvo_.id == 'ROTA_LOGIN' for alvo_ in no.targets):
            if not (isinstance(no.value, ast.Constant) and no.value.value == '/api/login'):
                return f'ROTA_LOGIN não é /api/login: {ast.dump(no.value)[:60]}'
            break
    else:
        return 'constante `ROTA_LOGIN` não encontrada — matcher quebrado'

    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            if 'json' in {k.arg for k in no.keywords}:
                return 'chamada com `json=`: o certificador não escreve'
            if 'data' in {k.arg for k in no.keywords} and no is not login:
                return 'chamada com `data=` fora do login'
    return ''
