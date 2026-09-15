# #343 PR1 — Caracterização comportamental e ownership

Data: 2026-09-14. Frente de DESIGN + TESTES. **Nenhuma linha de JavaScript ou
Python de produção foi alterada.**

Este documento existe para explicar os testes acrescentados em
`static/js/test/run-tests.js` (seção `PR1`, entre `MARCA_INICIO_PR1` e
`MARCA_FIM_PR1`) e para registrar as duas matrizes que eles sustentam.

## 1) O que este PR faz, e o que não faz

Transforma em teste reproduzível o que a auditoria mediu, e determina **por
comportamento** quem é o owner real de cada responsabilidade.

Não corrige o bootstrap, não remove guarda, não altera flag, não ativa módulo,
não remove módulo, não muda storage, fetch, navegação nem submit de produção.

## 2) Os dois modos de carga

| Modo | O que é | Para que serve |
|---|---|---|
| **Ordem servida** | Exatamente o que `_scripts.html` manda o navegador fazer, mais a injeção dinâmica de 42/43/44 que o `app.js` dispara. | Medir o que roda em produção hoje. |
| **Contrafactual** | A mesma carga, com o bloqueio neutralizado **pelo lado do host**: `ensureModuleBound` passa a derivar chave de outro namespace, e/ou a nav API é publicada antes do módulo que a consome. | Responder "o que apareceria SE o bloqueio saísse". |

O contrafactual **não altera nenhum byte dos módulos** — nem em disco, nem em
memória. O que muda é o ambiente em volta. Ele é pergunta de decisão, não
autorização de correção.

## 3) Limites declarados do harness

Registrados aqui porque afetam a leitura dos gates:

1. **Não é possível espionar chamada interna do `app.js`** substituindo a
   propriedade global correspondente. Num `vm`, funções declaradas no topo de
   um script resolvem referências do mesmo script pelo binding dele. Medido, não
   suposto: a pilha do gesto real mostra `dispatchEvent → bindMenuNavigation →
   navigateToView` com a versão original, mesmo após a troca. Por isso os gates
   de navegação usam o **efeito** como discriminador (`location.assign`, que só
   `navigateToView` produz), e não a chamada.
2. **O shim de DOM não interpreta `innerHTML`.** Onde um módulo monta controles
   por essa via, o fixture traz o nó equivalente com o **mesmo id** que o código
   de produção procura — o gate real fica exercitável, sem atalho que o contorne.
3. **`instanceof` contra construtores de elemento dá sempre falso.** Os
   construtores existem no contexto para não lançar `ReferenceError`; nenhum nó
   do shim herda deles. Mesma degradação que o harness da F5-B.1 já aceita.

## 4) Matriz de ownership

A coluna "ativa hoje?" é **remedida** pelo gate `PR1 Z-1` a cada execução, não
declarada. Se qualquer linha mudar de estado, o gate quebra.

| Responsabilidade | Implementação candidata | Ativa hoje? | Teste comportamental | Equivalência | Owner recomendado |
|---|---|---|---|---|---|
| Instrumentação de requisições HTTP | `error-monitor.js` | **sim**, sem flag | `PR1 E-1`, `E-2` | — | **`error-monitor.js`** |
| Instrumentação de requisições HTTP | `ux-phase44.js` (`bindFetchFeedbackBridge`) | não | `PR1 E-3`, `E-4` | TOTAL, e empilha | `error-monitor.js` |
| Dropdown `[data-ui-dropdown]` | `app.js` (`setupInteractiveDropdowns`) | **sim**, sob 2 flags | `PR1 F-1`, `F-3`, `F-4`, `F-5` | — | **`app.js`** |
| Dropdown `[data-ui-dropdown]` | `ux-phase44.js` (`createDropdown`) | não | `PR1 F-2`, `F-3`, `F-3b`, `F-4`, `F-5` | **PARCIAL** | `app.js` |
| Intenção de navegação (clique de menu) | `app.js` (`bindMenuNavigation` → `navigateToView`) | **sim** | `PR1 G-1`, `G-2` | — | **`app.js`** |
| Intenção de navegação (clique de menu) | `multitab-navigation.js` | não | `PR1 G-3`, `G-4`, `G-5` | PARCIAL, e intercepta | `app.js` |
| Semântica de ativação redundante | `app.js` (`ativacaoRedundanteDeView`) | **sim** | `PR1 G-2` | — | **`app.js`** |
| Semântica de ativação redundante | `multitab-navigation.js` (cópia local) | não | `PR1 G-6` | TOTAL | `app.js` |
| Assistente e pré-condição de envio da entrega | `ux-phase42.js` | **sim**, sob flag | `PR1 B-1`..`B-5`, `D-1` | — | **`ux-phase42.js`** |
| Fluxo rápido de entrega | `ux-phase43.js` | não | `PR1 D-1`..`D-3`, `H-2` | PARCIAL | `ux-phase42.js` |
| Persistência/restauração de rascunho de formulário | `ux-phase41.js` | não | `PR1 C-1`..`C-6` | **implementação única** | nenhum |
| Limpeza de rascunho no encerramento | `app.js` (`resetAppFormDrafts`) | **sim**, sem flag | `PR1 C-6` | — | **`app.js`** |

### 4.1) Dropdown — por que PARCIAL e não TOTAL

O ponto decisivo deste PR. Os dois usam o mesmo contrato de atributos; isso,
sozinho, não prova duplicidade. Medido gesto por gesto:

**Equivalentes** (`F-1`, `F-2`, `F-3`, `F-5`)
- abrir e fechar pelo gatilho, com `aria-expanded` e `hidden` sincronizados;
- exclusividade entre dropdowns — **por mecanismos diferentes**: o `app.js`
  chama `closeInteractiveDropdowns()` explicitamente; o `phase44` registra um
  listener de clique no documento **por instância**, e o clique no gatilho
  vizinho cai como "clique fora" para todas as outras;
- fechar por clique fora do conjunto.

> A leitura do código sugeria que só o `app.js` mantinha exclusividade. O gate
> mostrou o contrário. É exatamente por isso que a classificação não pode sair
> de leitura.

**Diferentes** (`F-3b`, `F-4`, `F-5`)

| Dimensão | `app.js` | `ux-phase44.js` |
|---|---|---|
| Escape | fecha a partir do **documento** | só a partir da **raiz** do dropdown |
| Foco após Escape | não devolve | **devolve ao gatilho** |
| Clique dentro de OUTRO dropdown | mantém o primeiro aberto | fecha o primeiro |
| Custo | **um** listener de documento | **um por dropdown** |
| Gate de ativação | duas flags (`ux_htmx_prod` + `ux_tools_functional`) | a própria |

Há capacidade de cada lado que o outro não tem. **PARCIAL** — preserva-se o
owner atual e absorve-se apenas o que falta: a devolução de foco ao gatilho
no Escape.

### 4.2) phase43 — o que ele acrescenta ao phase42

Medido em `PR1 H-1` e `H-2`: com o `phase42` sozinho e a revisão marcada, uma
entrega **sem código lido** passa. Com o `phase43`, ela é barrada e o campo
faltante é nomeado. A exigência do `#delivery-stock-item-code` é **capacidade
exclusiva do 4.3** — é o que se absorve no owner, e é o motivo de a decisão não
ser "REMOVER".

## 5) Matriz de decisão por módulo

Fixada pelo gate `PR1 Z-2`, que exige ao menos três gates sustentando cada
decisão e recusa o vocabulário fora da lista.

| Módulo | Necessário para funcionalidade atual? | Possui comportamento exclusivo? | Decisão recomendada |
|---|---|---|---|
| `ux-phase41.js` | não (inerte) | **sim** — nenhum outro persiste rascunho; o app tem política ANTI-persistência | **MANTER INERTE — FUNCIONALIDADE ÚNICA** |
| `ux-phase42.js` | **sim** quando a flag está ligada | **sim** — é o owner do assistente e do gate de envio | **MANTER — OWNER** |
| `ux-phase43.js` | não (inerte) | **sim** — exigência do código lido, confirmação por teclado, estado do envio | **ABSORVER CAPACIDADE NO OWNER** |
| `ux-phase44.js` | não (inerte) | **sim** — foco de volta ao gatilho, confirmação inline, contador de filtros | **ABSORVER CAPACIDADE NO OWNER** |
| `multitab-navigation.js` | não (inerte) | **sim** — abas com contexto preservado, sem owner algum hoje | **ABSORVER CAPACIDADE NO OWNER** |

**Nenhum módulo foi classificado `REMOVER — REDUNDANTE`.** Em todos os quatro
inertes sobrou capacidade que o owner atual não tem. Remoção é decisão do PR de
limpeza, e só depois da absorção. O gate `Z-2` recusa essa classificação sem
prova de ausência de capacidade exclusiva.

## 6) Caracterizações de defeito

Não há `skip` nem `xfail` permanente nesta seção. O mecanismo é
`caracterizaDefeito(nome, ficha, fn)`: cada uma **afirma o comportamento atual**
— portanto passa hoje — e declara cinco campos obrigatórios (`esperado`,
`atual`, `motivo`, `responsabilidade`, `decisaoFutura`). Quando o defeito for
corrigido, ela **falha**, que é o sinal desejado. O gate `PR1 Z-3` valida os
campos e imprime o inventário a cada execução.

| Gate | Responsabilidade | Defeito caracterizado |
|---|---|---|
| `PR1 C-1` | Persistência de rascunho | phase41 não inicializa, nem com a flag ligada |
| `PR1 C-2` | Governança de ativação | a flag do phase41 nunca chega a ser consultada |
| `PR1 C-3` | Migração/retenção em `localStorage` | a limpeza de chave legada da F5-B não é alcançada em 41, 43 e 44 |
| `PR1 C-6` | Isolamento de rascunho entre identidades | o contexto do phase41 sobrevive à limpeza do logout |
| `PR1 D-2` | Pré-condição de envio da entrega | satisfazer um gate não libera o outro |
| `PR1 E-3` | Instrumentação HTTP | o bridge do phase44 empilha sobre o do error-monitor |
| `PR1 G-4` | Autoridade de navegação | o multitab assume o clique do menu por interceptação |
| `PR1 G-6` | Ativação redundante | o multitab reimplementa a guarda em paralelo |

## 7) Testes estruturais caracterizados como legados

Renomeados com prefixo `test_legacy_structural_` e docstring explicando que
**exigem a presença da linha que causa o defeito** — e que devem falhar no dia
em que o bootstrap for corrigido:

- `tests/test_phase41_stabilization.py::test_legacy_structural_phase41_has_global_guard_and_iife`
- `tests/test_phase43_hardening.py::test_legacy_structural_phase43_uses_guard_and_fail_safe_init_gate`
- `tests/test_phase44_standardization.py::test_legacy_structural_phase44_guard_flag_and_classic_fallback_are_present`

Nenhum teste foi apagado. Os três arquivos ganharam docstring de módulo
declarando a natureza estrutural e apontando para os gates comportamentais
correspondentes.

## 8) O que este PR não conseguiu medir

Registrado por honestidade, e como entrada para o PR seguinte:

- **`phase43` com o resumo aberto passando no envio**: o painel é montado por
  `innerHTML` e o shim não o interpreta, então o caminho de sucesso do
  `phase43` não é exercitável aqui. O que se mede é o **bloqueio**, que é o
  comportamento em disputa com o `phase42`.
- **Hierarchy (`navigation.js`) e SPA**: fora do escopo desta rodada. Nenhum
  gate desta seção afirma nada sobre eles.
- **Ordem de chegada entre 42, 43 e 44**: são scripts assíncronos e o navegador
  não a garante. O harness modela "chegaram depois do resto"; nenhum gate desta
  seção depende dessa ordem.
