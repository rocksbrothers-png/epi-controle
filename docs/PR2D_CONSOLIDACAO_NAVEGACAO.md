# #343 PR 2D — Consolidação: multitab × navegação principal

Última das quatro fatias. Escopo: **uma única responsabilidade** — a intenção de
navegação (clique no item do menu lateral).

**Nenhum arquivo de produção alterado.** Contém também as duas matrizes finais
do PR 2.

---

## 1) A pergunta do contrato, respondida

> Existe apenas uma autoridade capaz de decidir a navegação?

**SIM** — e medido, não presumido (`2D D-1`).

O clique no menu chega a `navigateToView`, e o número de listeners de clique
**em fase de captura no documento** é **zero**. Essa contagem não é um detalhe:
o `PR1 G-5` já tinha provado que captura + `stopImmediatePropagation()` é o
único mecanismo capaz de decidir por cima do owner. Contar esses listeners é,
portanto, contar autoridades.

`2D D-2` trava a resposta: entre todos os arquivos servidos, **só** o
`multitab-navigation.js` registra esse padrão — e ele sai no PR 4. Até lá, o
gate impede que o padrão seja copiado para um segundo lugar.

`2D D-3` faz o mesmo pela guarda de ativação redundante: a definição canônica
vive no owner, e a única cópia é a do multitab.

---

## 2) A capacidade candidata, medida

O PR 1 registrou que o exclusivo do multitab seria "abas com contexto
preservado", e previu absorvê-lo no contrato de navegação. A medição não
sustenta essa previsão.

No código, a capacidade é `captureViewContext`: uma varredura de **todo**
`input`/`select`/`textarea` com id dentro da view, guardada num objeto JS por
aba (`2D D-4`). O filtro é por **tipo** de campo — só `password` e `hidden`
ficam de fora. Não há noção de CPF, CNPJ, e-mail ou documento.

Isso importa porque o `app.js` tem política ativa e declarada em sentido
contrário. O comentário do `resetAppFormDrafts()` é explícito: depois de um
encerramento o rascunho "é de quem saiu", e `#employee-form` tem "CPF, nome,
e-mail e WhatsApp de um colaborador". O critério que o arquivo adota é **lista
de exclusão, nunca de inclusão** — "uma lista envelhece no primeiro elemento
novo, sem ninguém perceber".

`resetAppFormDrafts()` opera no **DOM**. O cache do multitab é um objeto JS que
ela não conhece. `2D D-6` mede exatamente isso: preencher, trocar de aba,
chamar a limpeza do app (DOM fica limpo) e pedir o contexto de volta por
Ctrl+Tab — o valor **retorna**.

O que hoje cobre o encerramento é a **recarga**: `terminateSession()` termina em
`location.reload()` e o heap morre junto com o cache. Isso é reforço de
ambiente, não a limpeza. Absorver o cache no owner da navegação faria a política
de limpeza passar a depender dele.

**Conclusão: nada absorvido.**

---

## 3) Uma correção a favor do módulo

A hipótese com que abri esta fatia estava **errada**, e o código me corrigiu.

Eu esperava que o cache brigasse com a política de limpeza em **qualquer** troca
de view. Não é o caso: `restoreViewContext` só roda com
`opts.restoreContext === true`, e o caminho do menu lateral **não passa esse
sinal**. O contrato F5-B está escrito no próprio arquivo: *"entrar pelo menu
lateral é reentrada no módulo e tem de chegar no estado inicial"*.

`2D D-5` registra isso como contrato: voltar pelo menu **não** restaura. A
restauração acontece só nos gestos explícitos da barra — clicar numa aba,
Ctrl+Tab, fechar aba e cair na vizinha, e `popstate`.

O gate precisou de cuidado para medir o que diz: esvaziar o campo **enquanto a
aba está fora de foco**, porque a view só fica escondida e o valor permaneceria
por inércia. Sem isso o teste não distinguiria "restaurou" de "ninguém apagou".

---

## 4) Destino (`2D D-7`)

| Caminho | Papel | Absorveu | Destino |
|---|---|---|---|
| `app.js` (`bindMenuNavigation` → `navigateToView`) | OWNER | nada | **AINDA POSSUI RESPONSABILIDADE EXCLUSIVA** |
| `multitab-navigation.js` (`onMenuIntercept`) | CONCORRENTE | n/a — interceptador, não capacidade | **REMOVER NO PR 4** |
| `multitab-navigation.js` (`captureViewContext`/`restoreViewContext`) | CAPACIDADE CANDIDATA | nada | **REMOVER NO PR 4** |

**Inventário de flags: vazio.** Nada foi absorvido. `spa_navigation_enabled`
(do owner) e `ux_multitab_navigation_enabled` permanecem inalteradas.

---

## 5) Matrizes finais do PR 2

### A — Responsabilidade × owner (`2D D-8`)

| Responsabilidade | Owner antes | Concorrente | Owner depois | Absorvido | Fatia |
|---|---|---|---|---|---|
| Pré-condição de envio da entrega | `app.js` + backend | `ux-phase43.js` | inalterado | nada | 2A |
| Assistente e revisão do envio | `ux-phase42.js` | `ux-phase43.js` | inalterado | nada | 2A |
| Instrumentação de requisições HTTP | `error-monitor.js` | `ux-phase44.js` | inalterado | nada | 2B |
| Dropdown `[data-ui-dropdown]` | `app.js` | `ux-phase44.js` | **com devolução de foco** | **devolução de foco ao gatilho** | 2C |
| Intenção de navegação | `app.js` | `multitab-navigation.js` | inalterado | nada | 2D |
| Contexto de formulário por aba | nenhum | `multitab-navigation.js` | nenhum, deliberadamente | nada | 2D |

**Saldo do PR 2 inteiro: uma absorção, em seis responsabilidades.** O gate falha
se esse número mudar sem revisão. Todos os seis concorrentes ficam removíveis.

### B — Módulo × estado × flag × destino (`2D D-9`)

| Módulo | Inerte hoje | A flag liga? | Flag | Destino |
|---|---|---|---|---|
| `ux-phase42.js` | sim | **sim** | `ux_phase42_enabled` | MANTER — OWNER |
| `ux-phase41.js` | sim | não | `ux_phase41_enabled` | FORA DO ESCOPO DO PR 2 — PR 3/F5-C |
| `ux-phase43.js` | sim | não | `ux_phase43_enabled` | REMOVER NO PR 4 |
| `ux-phase44.js` | sim | não | `ux_phase44_enabled` | REMOVER NO PR 4 |
| `multitab-navigation.js` | sim | não | `ux_multitab_navigation_enabled` | REMOVER NO PR 4 |

A coluna "a flag liga?" é o resumo do PR 0 e do PR 1 numa medida só: **o
phase42 é o único que a flag consegue ligar**. Nos outros quatro a colisão de
chave de guard barra antes dela — e é por isso que "desligar a flag" nunca foi
resposta para nenhum deles. O gate falha se esse conjunto mudar.

---

## 6) Entregáveis

- `static/js/test/run-tests.js` — gates `2D D-1`..`D-9`, incluindo as duas
  matrizes finais.
- `PR1 Z-2` — multitab passa a `CONSOLIDADO SEM ABSORÇÃO — RESTO INERTE`, com a
  previsão do PR 1 corrigida e a correção a favor do módulo registrada.
  `exclusivo` segue `true`: a barra de abas com histórico próprio não tem outro
  dono, nunca rodou e nunca foi validada — decisão do PR 4.

## 7) O que este PR não fez

Não ativou flag, não corrigiu o `ensureModuleBound`, não removeu módulo, não
tocou em `capture`, `stopImmediatePropagation`, `navigateToView` nem na guarda
de redundância.

**Impacto comportamental esperado: zero.** Nenhum arquivo servido ao navegador
foi alterado.
