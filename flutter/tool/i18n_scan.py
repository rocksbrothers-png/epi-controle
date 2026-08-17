#!/usr/bin/env python3
"""Varredura de strings hardcoded voltadas ao usuário em apps/epi_admin/lib/features.

Emite uma linha `caminho|texto` por ocorrência, no formato que a allowlist usa.
Chamado por ``check_hardcoded_strings.sh``, que continua sendo o ponto de
entrada do CI.

Por que Python e não grep. A versão anterior fazia isto com dois `grep -rnoE`,
e cada um carregava um defeito que só apareceu quando o gate foi auditado:

1. A classe ``[A-Za-zÀ-ÿ]`` é um intervalo de COLAÇÃO. Sob ``C.UTF-8`` — o
   locale dos runners do GitHub — o grep aborta com "Invalid collation
   character"; como a chamada terminava em ``|| true``, o erro virava lista
   vazia e o gate passava **sem ter varrido nada**. Verde pelo motivo errado.
2. `grep` é orientado a linha. Um ``Text(`` quebrado em várias linhas — com o
   literal numa linha própria — nunca casava. Eram 17 literais invisíveis, dois
   deles já na allowlist, registrados por alguém que os viu a olho nu.

Os dois defeitos são da mesma família: análise de sintaxe feita com casamento
de texto orientado a linha e dependente de locale. Aqui o arquivo é lido
inteiro, em UTF-8 explícito, e as classes de caractere são Unicode por padrão.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Um literal de string simples, sem interpolação (`$`) e sem quebra de linha,
# contendo ao menos uma letra — número puro, símbolo ou string vazia não é
# texto voltado ao usuário.
_LITERAL = r"'(?P<texto>[^'$\n]*[^\W\d_][^'$\n]*)'"

PADROES = (
    # Text('literal') e Text(\n  'literal'  — o \s* cobre as duas formas.
    re.compile(r'Text\(\s*' + _LITERAL),
    # atributo: 'literal' (InputDecoration, EpiButton, Tooltip, ...).
    re.compile(r'(?:labelText|hintText|helperText|label|tooltip)\s*:\s*' + _LITERAL),
)

# Comentários não são interface. Varrer dentro deles produziria falso positivo
# em cada exemplo de código citado numa explicação — e foi assim que três
# varreduras anteriores neste repositório precisaram ser corrigidas.
_COMENTARIO_LINHA = re.compile(r'//[^\n]*')
_COMENTARIO_BLOCO = re.compile(r'/\*.*?\*/', re.S)


def _sem_comentarios(fonte: str) -> str:
    """Remove comentários preservando o número de linhas e as posições
    relativas — troca cada comentário por espaços, em vez de apagá-lo."""
    def _apagar(m: re.Match[str]) -> str:
        return re.sub(r'[^\n]', ' ', m.group(0))

    return _COMENTARIO_LINHA.sub(_apagar, _COMENTARIO_BLOCO.sub(_apagar, fonte))


def varrer(raiz: pathlib.Path, base: pathlib.Path) -> list[str]:
    achados: set[str] = set()
    for arquivo in sorted(raiz.rglob('*.dart')):
        fonte = _sem_comentarios(arquivo.read_text(encoding='utf-8'))
        relativo = arquivo.relative_to(base).as_posix()
        for padrao in PADROES:
            for m in padrao.finditer(fonte):
                achados.add(f"{relativo}|{m.group('texto')}")
    return sorted(achados)


def main() -> int:
    if len(sys.argv) != 3:
        print('uso: i18n_scan.py <dir-do-app> <subdir-varrido>', file=sys.stderr)
        return 2
    base = pathlib.Path(sys.argv[1])
    raiz = pathlib.Path(sys.argv[2])
    if not raiz.is_dir():
        print(f'diretório não encontrado: {raiz}', file=sys.stderr)
        return 2
    for linha in varrer(raiz, base):
        print(linha)
    return 0


if __name__ == '__main__':
    sys.exit(main())
