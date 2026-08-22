"""Detector de comparação `saldo × mínimo` em código de cliente (1.1D-C4).

Não é um módulo de teste (o nome não começa com `test_`): é a ferramenta que
os gates de JavaScript e de Dart compartilham.

Compartilhar é o ponto. Dois detectores separados divergem no primeiro ajuste
feito num lado só — que é exatamente o defeito que estes gates existem para
impedir no código de produção. A D-C3 enviou uma cópia só para JavaScript; a
varredura de Dart revelou uma falha nela (ver `_comparadores`), e corrigir em
dois lugares teria sido a mesma armadilha de novo.

A regra que os gates protegem::

    criticidade operacional = unit_stock_quantity <= unit_minimum_stock

Ela é decidida no SERVIDOR (`classify_unit_epi_stock`) e chega pronta em
`stock_status`. Qualquer cliente que a recalcule cria uma segunda fonte — foi
assim que a comparação errada se espalhou por sete consumidores (#271).
"""

import re

TERMOS_SALDO = ('stock', 'saldo', 'quantity', 'qty')
TERMOS_MINIMO = ('minim',)

# Marcador para a linha que compara DE PROPÓSITO — hoje só o teste de contrato
# que demonstra por que a comparação local está errada. Exigir o marcador
# explícito mantém o gate afiado: a exceção fica visível na linha, não numa
# lista de arquivos isentos que ninguém revisita.
MARCADOR_INTENCIONAL = 'gate:comparacao-intencional'


def sem_comentarios(texto):
    """Remove comentários de linha e de bloco.

    Os comentários destas fatias CITAM a comparação removida para explicá-la.
    Varrer com eles dentro reprovaria a própria correção — e o inverso também
    acontece: a âncora da #271 passou a casar com a prosa em vez do código e
    virou falso positivo silencioso.
    """
    sem_bloco = re.sub(r'/\*.*?\*/', '', texto, flags=re.DOTALL)
    return '\n'.join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith('//')
    )


def _comparadores(linha):
    """Posições de comparadores REAIS na linha, como (índice, operador).

    `=>` não é comparação: é a seta de função de Dart e de JavaScript. A
    versão anterior deste detector partia a linha em todo `>`, e por isso
    marcava `int? get nearMinimumStock => kpis.nearMinimumStock;` e cada
    getter de i18n `String get stockMinimumAlert => '...'` como violação.
    Sete falsos positivos numa varredura de Dart, num gate que só não
    quebrou o CI de JavaScript por sorte de nenhuma arrow function ter os
    dois termos.

    `->`, `<<`, `>>` e `==` também saem: nenhum compara grandezas.
    """
    encontrados = []
    i = 0
    while i < len(linha):
        par = linha[i:i + 2]
        if par in ('<=', '>='):
            encontrados.append((i, par))
            i += 2
            continue
        if par in ('=>', '->', '<<', '>>', '==', '!='):
            i += 2
            continue
        if linha[i] in '<>':
            encontrados.append((i, linha[i]))
        i += 1
    return encontrados


def comparacoes_saldo_por_minimo(codigo):
    """Linhas onde um lado da comparação fala de saldo e o outro de mínimo.

    Uma regex única não basta: `(epi.unitStockQuantity ?? 0) <= epi.minimumStock!`
    escapou de uma tentativa anterior. Aqui a linha é PARTIDA no comparador e
    cada lado é examinado separadamente, nos dois sentidos.
    """
    achados = []
    for numero, linha in enumerate(codigo.splitlines(), 1):
        if MARCADOR_INTENCIONAL in linha:
            continue
        baixa = linha.lower()
        for posicao, operador in _comparadores(baixa):
            esquerda = baixa[:posicao]
            direita = baixa[posicao + len(operador):]
            tem_saldo_esq = any(t in esquerda for t in TERMOS_SALDO)
            tem_min_esq = any(t in esquerda for t in TERMOS_MINIMO)
            tem_saldo_dir = any(t in direita for t in TERMOS_SALDO)
            tem_min_dir = any(t in direita for t in TERMOS_MINIMO)
            if (tem_saldo_esq and tem_min_dir) or (tem_min_esq and tem_saldo_dir):
                achados.append((numero, linha.strip()))
                break
    return achados


def varrer(caminho):
    """Comparações reais num arquivo, já sem comentários."""
    return comparacoes_saldo_por_minimo(sem_comentarios(caminho.read_text(encoding='utf-8')))
