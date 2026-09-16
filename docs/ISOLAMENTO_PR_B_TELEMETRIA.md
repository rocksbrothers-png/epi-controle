# Isolamento entre Usuários em Computador Compartilhado — PR B: telemetria

Segunda das três fatias. Trata **só** `epi.analytics.master.events`. As
preferências pessoais (tema, densidade, sidebar, idioma) continuam intocadas e
são o PR C.

---

## 1) O defeito

`master_admin` A gera telemetria, sai, e o `master_admin` B seguinte a lê.

A proteção existente é por **papel**: `canAccessAnalytics() → isMasterRole()`.
Papel igual não é principal igual — e nada no módulo perguntava *de quem* era a
telemetria em disco.

---

## 2) Mapa do owner (levantado antes de decidir)

```
evento → pushEvent() → enqueue()/microtask → safeStorageRead/Write
       → localStorage['epi.analytics.master.events'] → getEventsForApi()
       → __EPI_ANALYTICS__.getEvents()
```

| Pergunta | Resposta medida |
|---|---|
| quem grava | `pushEvent()` → `safeStorageWrite()` |
| quem lê | `safeStorageRead()`, por `getEventsForApi()` |
| quem limpa | `clearAnalyticsStorage()`, só quando o papel **não** é master, ou `?ux_analytics_reset=1` |
| limite | `MAX_EVENTS = 100`; `MAX_BYTES = 28000` **declarado e nunca lido** |
| TTL | **nenhum** |
| inicialização | na carga do módulo, antes de qualquer decisão de sessão |
| relação com autenticação | nenhuma — só papel |
| relação com logout | **nenhuma**: `terminateSession()` não toca na chave |
| relação com troca de principal | **nenhuma** |
| endpoint no backend | **não existe** — `enqueueFlush` segue marcado "fase futura" |

### O achado que decidiu o contrato

**`__EPI_ANALYTICS__` é publicada e não tem um único consumidor no código
servido.** Nenhuma tela exibe, nenhum módulo chama `getEvents()`, nenhum
endpoint recebe. A busca cobriu todos os `.js` e `.html` servidos.

Escopo efetivo atual, portanto: **DEVICE**. Sobrevive a logout, a recarga, à
troca de identidade e ao fechamento do navegador.

---

## 3) A escolha de escopo

**Contrato escolhido: `SESSION` (B-A).** Eventos existem somente dentro da
sessão autenticada que os produziu, em RAM, e são descartados quando o principal
muda — inclusive **sem recarga**.

| Alternativa | Decisão | Por quê |
|---|---|---|
| **B-A SESSION** | **escolhida** | é o escopo mínimo que satisfaz o requisito, e o único que não deixa dado comportamental de uma pessoa no disco de um computador compartilhado |
| B-B USER | rejeitada | concede persistência entre sessões que **nenhum consumidor usa**, mantendo o dado em repouso sem contrapartida |
| B-C USER+TENANT | rejeitada | mesmo problema do B-B, e exige identidade de tenant que o módulo não tem |
| B-D servidor | rejeitada | **não existe owner server-side** de telemetria. Construí-lo para um consumidor inexistente é exatamente a infraestrutura que a autorização proíbe criar sem necessidade comprovada |

A única utilidade plausível hoje — um master inspecionar a própria atividade
pela API — continua atendida dentro da sessão.

### Por que NÃO foi acoplado ao `snapshotScopeId()` do PR A

A autorização pediu para provar equivalência semântica antes de reutilizar. Ela
**não existe**:

- o escopo de snapshot **precisa sobreviver ao F5** do mesmo usuário — restaurar
  filtros e rolagem depois de um refresh é comportamento existente da SPA, e a
  #343 F2 o preservou de propósito;
- a telemetria **não tem esse requisito**, porque não tem consumidor.

Acoplar imporia à telemetria a sobrevivência ao F5 sem razão, e criaria um dono
único para duas responsabilidades com motivos diferentes para mudar. A regra da
#343 continua valendo: uma responsabilidade funcional, um owner.

O que foi reutilizado é o **conceito**, não o código: "o dado pertence a um
principal; na troca, descarta".

---

## 4) O que mudou

| Onde | O quê |
|---|---|
| `resolveCurrentPrincipal()` | **novo** — responde *de quem* é a telemetria, separado de `canAccessAnalytics()`, que responde *que papel pode vê-la* |
| `lerEventos()` / `gravarEventos()` | substituem `safeStorageRead/Write`: operam em `analyticsState.eventos`, em RAM |
| `descartarSeTrocouPrincipal()` | **novo** — descarta a lista quando o principal muda, sem depender de recarga |
| `clearAnalyticsStorage()` | passa a rodar **incondicionalmente** na carga: purga do legado em disco |
| `MAX_BYTES` | **removido** — sem gravação não há teto de bytes, e já não era lido |

Mesmo caminho que a memória de uso do `ux-phase42.js` seguiu na #343 F5-B,
incluindo a remoção da constante de bytes.

### Legado sem dono

`epi.analytics.master.events` gravado por versão anterior **não tem dono
identificável**. Não é entregue a ninguém e não é atribuído ao primeiro master
que entrar: é purgado na carga. Só as duas chaves da própria telemetria —
`epi-theme`, sessão e tudo mais permanecem (gate `B-7`).

---

## 5) Gates

### B-0 — caracterização, escrita ANTES da correção

| Gate | O que mede | Nasceu |
|---|---|---|
| `B-0` | o harness monta o módulo servido e alcança a API | verde |
| `B-1` | master A produz evento → master B (carga nova) não o lê | **vermelho** |
| `B-2` | **controle**: a proteção por papel continua funcionando | verde |
| `B-3` | troca de principal **sem recarga** também isola | **vermelho** |
| `B-4` | nova sessão do próprio A — contrato medido, não presumido | **vermelho** (a telemetria sobrevivia) |
| `B-5` | legado sem identidade não é atribuído ao primeiro master | **vermelho** |
| `B-6` | storage malformado falha fechado | **vermelho** (`[1,2,3]` virava 3 "eventos") |

Os gates `B-1`, `B-3` e `B-4` **produzem o evento pelo caminho real do módulo**
(`api.track()` + espera da microtask). A primeira versão semeava o storage — e
media o que o teste escreveu, não o que a aplicação grava.

### Gates acrescentados pela verificação de sabotagem

A primeira rodada de sabotagem **não derrubou nada**: os gates estavam verdes por
um motivo diferente do alegado. Duas propriedades não estavam sendo medidas:

| Gate | O que faltava medir |
|---|---|
| `B-7` | a telemetria legada some do **disco**, não só da leitura — com tudo em RAM, "não é lida" passa a ser verdade mesmo com o dado ainda gravado lá |
| `B-8` | o módulo não grava telemetria em disco (estrutural, complementar ao `B-3`) |

### Sabotagens, depois da correção

| Sabotagem | Gate que ficou vermelho |
|---|---|
| α — telemetria volta para o disco | `B-3` |
| β — remove a purga incondicional do legado | `B-7` |
| γ — reintroduz `setItem` da chave de telemetria | `B-8` |

Três sabotagens, três gates distintos.

### Convertido

| Gate | De | Para |
|---|---|---|
| `test_analytics_and_phase42_buffers_remain_limited` | exigia `var MAX_BYTES = 28000;` | exige a **ausência** de `var MAX_BYTES`, com a mesma redação que a #343 F5-B usou para o `MAX_STORAGE_BYTES` do phase42 |

Um gate convertido, pelo mesmo motivo que o precedente: sem gravação em disco
não há teto de bytes a limitar. Nenhum gate foi removido ou enfraquecido.

### Contrato do PR A registrado

`ISOL A-10` — **gate apenas, nenhuma linha de produção do PR A tocada.** A
revisão pediu que `escopoDoEstadoConfere()` fosse registrada como owner único da
decisão de escopo. A implementação já era essa, mas nada impedia alguém de
reintroduzir a comparação em outro ponto: os gates do PR A verificam a ordem e o
uso, não a exclusividade. Sem este gate, o contrato era intenção, não trava.

### Resultado

| Suíte | Antes | Depois |
|---|---:|---:|
| Gates JS | 366 | **376** |
| pytest (corporate) | 3 825 | **3 825** |
| pytest (app) | 3 820 | **3 820** |

---

## 6) Comportamento antes/depois

| Cenário | Antes | Depois |
|---|---|---|
| master A → logout → master B | B lê os eventos de A | B não lê |
| master A → troca sem recarga → master B | B lê os eventos de A | B não lê |
| master A → admin B | já protegido (papel) | protegido |
| master A → nova sessão de A | eventos sobrevivem | eventos não sobrevivem (SESSION) |
| legado em disco | entregue ao primeiro master | purgado na carga |
| storage malformado | `[1,2,3]` virava 3 "eventos" | não há leitura de disco |
| telemetria em repouso no disco | permanente, sem TTL | **nenhuma** |

---

## 7) O que continua aberto

**PR C — preferências pessoais.** `epi-theme`, `epi-density`,
`epi-sidebar-collapsed` e `epi_language` continuam DEVICE e continuam vazando
entre usuários. Não foram tocadas aqui.

**`epi_tenant`** segue sem classificação de escopo, deliberadamente fora das
três fatias.
