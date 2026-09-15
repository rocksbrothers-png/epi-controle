# #343 PR 2C — Consolidação: phase44 (dropdown) × app.js

Fatia 3 de 4. Escopo: **uma única responsabilidade** — o dropdown
`[data-ui-dropdown]`.

**Esta é a única fatia do PR 2 que absorve alguma coisa, e a única que altera
código de produção:** 17 linhas, em uma função, em um arquivo.

---

## 1) O saldo que o PR 1 já tinha medido

| Gesto | `app.js` (owner) | `ux-phase44.js` (concorrente) |
|---|---|---|
| Abrir / fechar pelo gatilho | igual (`F-1`, `F-2`) | igual |
| Exclusividade (um aberto por vez) | sim, por `closeInteractiveDropdowns()` antes de abrir | sim, por efeito colateral de um listener por instância (`F-3`) |
| Custo de listeners no documento | **1 clique + 1 teclado**, fixo | **1 clique por dropdown** (`F-3b`) |
| Escape | fecha **a partir de qualquer lugar do documento** (`F-4`) | só de dentro da própria raiz |
| Clique dentro de outro dropdown | não fecha o aberto | fecha (`F-5`) |
| **Foco após fechar pelo teclado** | **não devolve** | **devolve ao gatilho** |

O owner é melhor ou igual em tudo, exceto na última linha.

---

## 2) A capacidade absorvida, e por que ela é necessária

Fechar o painel o esconde. O foco do teclado estava **dentro** dele — num item
do menu — e passa a estar num nó invisível; o navegador o devolve ao `<body>`.
Quem navega por teclado ou leitor de tela perde o lugar na página e precisa
recomeçar a tabulação do topo.

O gate `2C C-1` reproduz exatamente esse gesto. Antes da mudança ele falhava
com a mensagem que descreve o defeito: o foco ficava em
`dropdown-acoes-item` — um nó dentro do painel já escondido.

Diferente das fatias 2A e 2B, aqui a capacidade candidata é real, tem
consequência observável para o usuário e não tem outro dono. Por isso foi
absorvida.

---

## 3) O que exatamente entrou no owner

No handler de `Escape` de `setupInteractiveDropdowns()`:

1. antes de fechar, resolve qual raiz `[data-ui-dropdown]` continha o foco;
2. fecha, como antes;
3. **só se aquela raiz estava aberta**, devolve o foco ao `[data-dropdown-trigger]` dela.

O limite é deliberado. Escape com o foco em outro lugar continua apenas
fechando, sem mexer no foco (`2C C-2`); Escape sem dropdown aberto não mexe em
nada (`2C C-3`). Mover o cursor de um campo que o usuário está preenchendo
seria comportamento **novo** — e comportamento novo não é absorção.

O que **não** foi absorvido, e por quê:

- **O listener por instância** (`F-3b`): é o mecanismo, não a capacidade. O
  owner obtém o mesmo resultado com um par fixo de listeners. `2C C-5` mede que
  a absorção não mudou esse custo.
- **Fechar o dropdown vizinho ao clicar dentro de outro** (`F-5`): com o owner
  nunca há dois abertos ao mesmo tempo, então o gesto não tem consequência
  visível. Mudá-lo seria comportamento novo. `2C C-6` trava o atual.

---

## 4) Não-regressão, medida

| Gate | Trava |
|---|---|
| `2C C-2` | Escape com foco fora: fecha, e **não** mexe no foco |
| `2C C-3` | Escape sem dropdown aberto: não rouba o foco |
| `2C C-4` | O mesmo Escape **continua** fechando o modal de assinatura — o ramo vem depois da devolução de foco no mesmo handler |
| `2C C-5` | Custo de listeners do owner inalterado: **+1 clique, +1 teclado**, com dois dropdowns no fixture |
| `2C C-6` | Exclusividade, clique fora e o caso fino de `F-5` seguem idênticos |
| `2C C-7` | No gesto que o concorrente cobria, os dois terminam igual — e o owner mantém o alcance que o concorrente não tem |

E a verificação que fecha o argumento: **rodando a suíte inteira com o `app.js`
anterior, falham exatamente três gates** — `C-1`, `C-4` e `C-7`, os que afirmam
a capacidade absorvida. Os outros 377 passam nas duas versões. A mudança move
exatamente o que deveria mover, e nada mais.

---

## 5) Destino (`2C C-8`)

| Caminho | Papel | Absorveu | Destino |
|---|---|---|---|
| `app.js` (`setupInteractiveDropdowns`) | OWNER | devolução de foco ao gatilho | **AINDA POSSUI RESPONSABILIDADE EXCLUSIVA** |
| `ux-phase44.js` (`createDropdown`) | CONCORRENTE | n/a — a capacidade foi para o owner | **REMOVER NO PR 4** |

### Inventário de flags

O código absorvido **não ganhou flag própria**. Ele vive dentro do handler do
owner, atrás do gate que já existia: `isHtmxAlpineProductionActive()`, isto é
`htmx_alpine_production_enabled` **e** `ux_tools_functional_enabled`. Flag nova
aqui só multiplicaria estados a validar. `2C C-8` falha se esse gate mudar.

`ux_phase44_enabled` permanece inalterada e o módulo segue inerte.

---

## 6) Situação do `ux-phase44.js` depois de 2B e 2C

Os dois eixos em que ele disputava responsabilidade estão fechados: o fetch
(nada a absorver, `2B`) e o dropdown (absorvido, `2C`). O módulo **não disputa
mais responsabilidade nenhuma**.

Na matriz `Z-2` ele passa a `CAPACIDADE ABSORVIDA — RESTO INERTE`, e
`exclusivo` continua **`true` de propósito**: o que resta no arquivo — cabeçalho
de view, barra de ação, contador de filtros, confirmação embutida, rolagem ao
topo — não tem outro dono, mas também nunca rodou e nunca foi validado. Decidir
se isso vira produto ou vai embora é decisão do PR 4, não uma disputa de
ownership, e marcá-lo como redundante agora seria afirmar mais do que os gates
provam.

---

## 7) Entregáveis

- `static/app.js` — devolução de foco no Escape (17 linhas).
- `static/index.html` — regenerado por `scripts/build_index.py build` (o
  cache-buster deriva do conteúdo).
- `static/js/test/run-tests.js` — gates `2C C-1`..`C-8`; harness passa a modelar
  `document.activeElement` e o painel do fixture ganha item focável (markup
  real). O limite do modelo de foco — global, um documento por vez — está
  declarado no próprio fixture.
- `PR1 F-4` — atualizado: a devolução de foco deixou de ser exclusividade do
  concorrente; a asserção permanece, medindo o concorrente, e alimenta `2C C-7`.
- `PR1 Z-2` — novo estado do phase44; vocabulário ganha
  `CAPACIDADE ABSORVIDA — RESTO INERTE`, com guarda exigindo gate do PR 2 que
  mostre a capacidade dentro do owner. Referências a gates do PR 2 passam à
  convenção `2A`/`2B`/`2C`, e a guarda de remoção acompanha.
- Dígitos `DIGESTO_PARIDADE_F4` e `DIGESTO_PARIDADE_F5B` recalculados nos dois
  repositórios — `static/app.js` e `run-tests.js` estão entre os arquivos pareados.

## 8) O que este PR não fez

Não ativou flag, não corrigiu o `ensureModuleBound`, não removeu módulo, não
mexeu no mecanismo de listeners do owner e não importou nenhuma outra diferença
do concorrente além da que `2C C-1` prova necessária.
