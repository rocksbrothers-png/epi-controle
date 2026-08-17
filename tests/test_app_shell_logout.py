"""Saída da sessão pela AppBar (Lote 6 da paridade).

Último item dos 33 arquivos divergentes mapeados na auditoria. Pequeno, mas
não cosmético: sem o botão, a única forma de encerrar a sessão neste
repositório era limpar os dados do app — num sistema multi-tenant onde o
mesmo dispositivo pode ser usado por mais de um operador em campo.

O teste é estrutural porque o defeito interessante aqui não é visual: é um
botão de "Sair" que **não chama** `logout()`. Ele existiria, seria clicável, e
a sessão continuaria aberta.
"""

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SHELL = RAIZ / 'flutter/apps/epi_admin/lib/core/shell/app_shell.dart'
AUTH_CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/auth_cubit.dart'


def test_a_appbar_oferece_saida_da_sessao():
    shell = SHELL.read_text(encoding='utf-8')
    assert 'Icons.logout_rounded' in shell, \
        'sem o botão, só limpando os dados do app dá para encerrar a sessão'
    assert "tooltip: 'Sair'" in shell


def test_o_botao_realmente_encerra_a_sessao():
    # O ponto do teste: um botão de Sair que não chama logout() é pior do que
    # botão nenhum — o operador acredita ter saído e a sessão segue aberta.
    shell = SHELL.read_text(encoding='utf-8')
    assert 'context.read<AuthCubit>().logout()' in shell

    # E `logout()` precisa existir de fato no cubit.
    assert 'Future<void> logout()' in AUTH_CUBIT.read_text(encoding='utf-8')


def test_a_saida_fica_nas_actions_da_appbar():
    # Em `actions:` ela aparece em toda tela do shell. Fora dali, ficaria
    # presa a uma única tela e o operador não a acharia quando precisasse.
    shell = SHELL.read_text(encoding='utf-8')
    inicio = shell.index('actions:')
    fim = shell.index(']', inicio)
    assert 'Icons.logout_rounded' in shell[inicio:fim]
