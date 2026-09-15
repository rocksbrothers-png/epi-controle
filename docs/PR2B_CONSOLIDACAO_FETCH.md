# #343 PR 2B — Consolidação: phase44 (fetch) × error-monitor

Fatia 2 de 4 da consolidação de ownership. Escopo: **uma única
responsabilidade** — a instrumentação de requisições HTTP.

**Resultado: nenhum arquivo de produção alterado.** A capacidade candidata do
concorrente não se sustentou sob medição, do mesmo modo que no PR 2A — e por um
motivo diferente, que vale registrar.

---

## 1) O que foi investigado

Dois caminhos embrulham `fetch` neste código:

| | `error-monitor.js` | `ux-phase44.js` (`bindFetchFeedbackBridge`) |
|---|---|---|
| Roda hoje | **Sim**, sem flag nenhuma | **Não** (colisão de chave de guard + flag) |
| 2xx | zera o contador de falhas | dispara `epi:action-success` |
| 4xx | **não é instabilidade** | dispara `epi:action-error` |
| 5xx | registra instabilidade, alimenta o auto-rollback | dispara `epi:action-error` |
| erro de rede | registra e **re-lança** | dispara `epi:action-error` e re-lança |
| marca de idempotência | `__EPI_MONITORED_FETCH__` | `__EPI_PHASE44_FETCH_BRIDGED__` |

O owner foi preservado. A pergunta do PR 2 não é "o concorrente funciona?", e
sim: **qual capacidade é exclusiva dele, e ela é mesmo necessária?**

A resposta é uma só capacidade: **emitir `epi:action-success` /
`epi:action-error` por requisição**, carimbados com a view ativa no momento da
chamada.

---

## 2) Quem consome essa capacidade — medido, não deduzido

Fora do próprio phase44, há **um** consumidor no código de produção:
`static/ux-analytics.js`, que em `epi:action-*` chama
`flowFinish('generic_action', …)`.

Esse consumidor é **duplamente condicionado** (`PR2B B-6`):

1. a flag `ux_analytics_enabled` — `defaultValue: false`; e
2. o papel do usuário — `master_admin` / `administrador_master`.

Na carga padrão de produção o ouvinte **nem se registra**. O gate mede isso:
`contarListeners(document, 'epi:action-success') === 0` no app servido, e
`>= 1` apenas com `?ux_analytics=1` e usuário master.

E do outro lado: **nenhum arquivo de produção dispara esses eventos hoje**. O
único emissor é o bridge inerte do phase44. O gate não confia na leitura — mede
uma requisição real atravessando o owner e conta zero eventos emitidos.

Ou seja, a responsabilidade tem hoje **um consumidor órfão**, não um owner
concorrente.

---

## 3) Por que a capacidade não foi absorvida

Absorver significaria fazer o `error-monitor.js` — que roda em **toda**
requisição, sem flag — emitir `epi:action-*`. O que isso produziria está medido
no contrafactual (`PR2B B-7`), não suposto:

- **(a) A métrica não mede nada.** `flowFinish('generic_action', …)` calcula
  duração a partir de um `flowStart` correspondente. `flowStart('generic_action')`
  **não existe em lugar nenhum do código**. Toda ocorrência é gravada com
  `duration: 0`. O gate afirma os dois fatos: a duração medida é zero e a
  abertura do fluxo não existe no fonte.
- **(b) O rótulo é falso.** A requisição que geraria o evento é de
  infraestrutura — disparada pela própria carga da página, não por um gesto do
  usuário. O gate confirma que o boot já emite requisições próprias antes de
  qualquer interação.
- **(c) Ocupa lugar de evento real.** O analytics do master guarda no máximo
  `MAX_EVENTS = 100` eventos, com `events.shift()` ao estourar. Ruído de
  transporte deslocaria evento de negócio.

Há ainda uma divergência de significado que a absorção teria de resolver e que
ninguém pediu para resolver (`PR2B B-8`): para o owner, **4xx não é falha de
API** — é resposta legítima do servidor a um pedido incorreto, e por isso não
entra no snapshot de instabilidade. Para o bridge, todo `!response.ok` é erro de
ação. São duas definições distintas de "erro", e adotar a segunda mudaria o
comportamento do auto-rollback.

### O padrão que já funciona

O mesmo `ux-analytics.js` acompanha o fluxo de entrega **corretamente**: o
`app.js` anuncia `epi:delivery-submit-start` / `-success` / `-error` na camada de
domínio, e o analytics abre e fecha o fluxo com `flowStart`/`flowFinish`. Esse
par tem emissor, tem duração real e tem significado.

A diferença não é de implementação, é de camada: **evento de negócio nasce onde
a regra de negócio está**, não no transporte. O bridge do phase44 tentou
sintetizar ação do usuário a partir de tráfego HTTP — e é por isso que o dado
sai vazio.

---

## 4) Contrato do owner, fixado por teste

O PR 1 caracterizou o owner; o PR 2B transforma isso em contrato positivo, para
que a remoção do concorrente no PR 4 não possa alterá-lo em silêncio:

| Gate | Contrato |
|---|---|
| `B-1` | Existe **uma** camada sobre o `fetch`, e ela é a do owner — contado por salto até o `fetch` base, não por marca privada |
| `B-2` | Três recargas do `error-monitor.js` não empilham camada |
| `B-3` | 200 devolve **a mesma instância** de resposta e não registra instabilidade |
| `B-4` | 5xx registra instabilidade **e ainda assim devolve** a resposta |
| `B-5` | Erro de rede registra e **re-lança o mesmo erro** |
| `B-8` | 4xx **não** é instabilidade de API |

`B-1` é deliberadamente contado por salto (`ctx.fetch → __EPI_FETCH_MONITOR_ORIGINAL__
→ fetch base`): é justamente a marca privada de cada dono que falha em enxergar
a do outro, defeito caracterizado em `PR1 E-3`.

---

## 5) Destino de cada caminho (`PR2B B-9`)

| Caminho | Papel | Absorveu | Destino |
|---|---|---|---|
| `error-monitor.js` (`monitoredFetch`) | OWNER | nada | **AINDA POSSUI RESPONSABILIDADE EXCLUSIVA** |
| `ux-phase44.js` (`bindFetchFeedbackBridge`) | CONCORRENTE | nada | **REMOVER NO PR 4** |
| `ux-analytics.js` (ouvintes `epi:action-*`) | CONSUMIDOR ÓRFÃO | não se aplica | **REMOVER NO PR 4** |

O destino vale para o **caminho do fetch**. O módulo `ux-phase44.js` inteiro
**não** sai nesta fatia: o eixo do dropdown continua aberto e é decidido no
PR 2C. A matriz `Z-2` registra isso explicitamente — `exclusivo: true` do
phase44 passa a se apoiar **só** no dropdown.

### Inventário de flags

**Vazio.** Nada foi absorvido, logo não há código novo atrás de flag nova. As
flags citadas (`ux_phase44_enabled`, `ux_analytics_enabled`) permanecem exatamente
como estavam; nenhuma foi lida, alterada ou ligada em produção. O gate `B-9`
falha se alguma linha da matriz passar a declarar absorção sem inventário.

---

## 6) Entregáveis

- `static/js/test/run-tests.js` — gates `PR2B B-1`..`B-9`; harness passa a expor
  o `fetch` base (adição só de teste) para contagem de camadas por salto.
- `PR1 E-3` — `decisaoFutura` revista: de "a instrumentação do 44 vai para o
  cliente canônico" para "não absorver nada; o caminho concorrente sai no PR 4".
  A caracterização do defeito continua válida e continua falhando quando o
  defeito for corrigido.
- `PR1 Z-1` — 12ª linha: o consumidor órfão do `ux-analytics`, para que a
  remoção do bridge no PR 4 não deixe ouvinte sem emissor.
- `PR1 Z-2` — gates `B-6`/`B-7`/`B-9` somados ao phase44, com o eixo do fetch
  marcado como encerrado.

## 7) O que este PR não fez

Não ativou flag, não corrigiu o `ensureModuleBound`, não removeu módulo, não
endureceu o `error-monitor.js` contra ser embrulhado por terceiros — essa
defesa só faria sentido contra um módulo que nunca roda, e o que resolve o
empilhamento de verdade é remover o caminho concorrente, no PR 4.

**Impacto comportamental esperado: zero.** Nenhum arquivo servido ao navegador
foi alterado.
