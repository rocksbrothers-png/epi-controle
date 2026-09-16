# #343 PR 4 — Limpeza final da frente

Última fatia. Remove o que as fatias anteriores provaram redundante, e preserva
o que só existia dentro do código removido.

**Estado final:** um módulo `ux-phase4x` servido (`ux-phase42.js`, owner), quatro
removidos, quatro flags a menos, e um cleanup de resíduos que sobrevive aos
módulos que os criaram.

---

## 1) Código removido

| Arquivo | Linhas |
|---|---:|
| `static/ux-phase41.js` | 455 |
| `static/ux-phase43.js` | 653 |
| `static/ux-phase44.js` | 519 |
| `static/multitab-navigation.js` | 590 |
| `tests/test_phase41_stabilization.py` | 108 |
| `tests/test_phase43_hardening.py` | 103 |
| `tests/test_phase44_standardization.py` | 94 |

Total: **2 522 linhas de módulo e teste estrutural**, mais as referências abaixo.

### Referências removidas

| Onde | O quê |
|---|---|
| `static/views/_scripts.html` | as duas `<script>` servidas (phase41, multitab) |
| `static/index.html` | idem, regenerado por `scripts/build_index.py build` |
| `static/app.js` | os dois blocos de injeção dinâmica (phase43, phase44) |
| `static/app.js` | `rerunSafeSetups` da nav API — único consumidor era o multitab |
| `static/ux-analytics.js` | os dois ouvintes órfãos de `epi:action-*` |
| `static/navigation.js` | a dependência de `ux_multitab_navigation_enabled` |
| `static/views/_topbar.html` | `#phase41-activity-indicator` e a `<section id="multitab-nav-root">` inteira |
| `static/styles.css` | 4 blocos de regras (~200 linhas) dos quatro módulos |
| `static/app.js` | o sinal `viaMultitab` do evento `epi:viewchange` — produtor e guardas |
| `static/ux-analytics.js` | `#phase43-confirm` e `[data-phase44-confirm-yes]` do seletor de confirmação |

As quatro últimas linhas são achados da **busca residual** (seção 5), não do
inventário inicial. Cada uma passou pelo mesmo teste de exclusividade que a
seção 11 da autorização exige, e a prova está registrada ali.

Uma renomeação, causada pela remoção: `registerMultitabNavigationApi()` →
**`registerAppNavigationApi()`**. A função publica `__EPI_APP_NAV_API__` e
**permanece**, porque o `navigation-controls.js` consome essa API. O que saiu foi
o nome, que apontava para um módulo inexistente.

### Flags removidas

`ux_phase41_enabled`, `ux_phase43_enabled`, `ux_phase44_enabled`,
`ux_multitab_navigation_enabled` — de **três** registros, não um:

| Arquivo | Estruturas |
|---|---|
| `static/app.js` | `UX_FRONTEND_FLAGS`, `UX_FORCE_CLASSIC_FLAGS`, `FEATURE_FLAG_DEFINITIONS` |
| `static/js/core/feature-flags.js` | as mesmas três, **servidas** ao navegador |
| `static/error-monitor.js` | `UX_FLAG_STORAGE_KEYS` (usada pelo auto-rollback) |

A flag do phase42 permanece intacta.

### Ouvintes de `epi:action-*` — produtores e consumidores encontrados

| Arquivo | Papel |
|---|---|
| `static/ux-phase44.js` (linhas 392, 397) | **único produtor** — removido |
| `static/ux-phase44.js` (372, 377) | consumidor próprio — removido |
| `static/ux-analytics.js` (478, 481) | consumidor — **removido nesta fatia** |

Sem produtor, `flowFinish('generic_action', …)` nunca era chamado; e a métrica
que ele alimentava não media nada, porque `flowStart('generic_action')` não
existe em lugar nenhum (PR 2B). Nenhuma telemetria em uso foi perdida.

---

## 2) Código adicionado — o cleanup legado

**Onde:** `static/app.js`, junto de `safeStorageRemove()`, executado na avaliação
do arquivo.

**Por que este é o owner:** `app.js` sempre carrega, não depende de nenhuma das
flags removidas, e roda antes de qualquer decisão de produto. Os módulos faziam a
limpeza deles no mesmo ponto do ciclo — **fora do gate da flag**, justamente para
alcançar quem teve a flag ligada um dia e não tem mais. Remover os arquivos
removeria o único código capaz de alcançar o que eles já gravaram.

Não foi criado sistema novo: o repositório **não possui** mecanismo de
client-side migrations (o `data_migration` é importação server-side), e criar um
para quatro chaves seria a dívida que esta fatia existe para evitar.

### Chaves removidas

| Chave | Origem |
|---|---|
| `epi:ux:phase41:context:v2` | contexto de formulário do phase41 |
| `epi:ux:phase41:scroll:v2` | posição de rolagem do phase41 |
| `epi:ux:phase43:state:v1` | estado do fluxo de entrega do phase43 |
| `epi.ux.phase44.filters.*` | filtros por view do phase44 (**prefixo**) |
| `ux_phase41_enabled` | a própria chave de flag |
| `ux_phase43_enabled` | idem |
| `ux_phase44_enabled` | idem |
| `ux_multitab_navigation_enabled` | idem |

As quatro últimas não estavam na lista original desta frente. Entraram porque
quem as apagava era o auto-rollback do `error-monitor.js`, que também deixou de
conhecê-las — sem esta inclusão, ficariam órfãs no disco para sempre.

O histórico do repositório foi verificado em 60 revisões: **não houve versão
anterior dessas chaves** além das listadas. O `multitab-navigation.js` não
gravava storage nenhum — o cache de abas dele era em memória (PR 2D).

### O que a rotina não faz, de propósito

Não limpa o storage inteiro, não varre por heurística, e **não toca no namespace
do phase42** — ele continua servido e já remove a própria chave legada. Migrar a
limpeza dele para cá duplicaria owner justamente na fatia que existe para
eliminar owners duplicados.

O prefixo é `'epi.ux.phase44.'`, **com o ponto final**: sem ele, um namespace
futuro como `epi.ux.phase440` entraria na varredura.

### Aposentadoria

A rotina **nasce temporária**, e carrega a versão `343-pr4` na marca
`APOSENTADORIA`, no comentário de cabeçalho do cleanup em `static/app.js`.

A primeira versão desta fatia declarava uma constante para essa versão. O CodeQL
apontou, corretamente, que nada a lia — e não podia ler, porque a decisão logo
abaixo é **não gravar marcador de "já limpei"**. Um identificador que ninguém
consome é dívida com aparência de mecanismo, exatamente o que esta fatia existe
para não criar; a versão passou para o comentário, que é onde ela sempre atuou.
O gate `PR4 L-5` trava as duas pontas: a marca precisa existir, e a constante não
pode voltar.

**Por quantas versões precisa sobreviver?** Até que não reste navegador com essas
chaves. Como não há como medir isso de fora, o critério proposto é o tempo: a
chave só existe em quem carregou a aplicação **antes** deste PR, e some na
primeira carga posterior. Então a rotina precisa sobreviver a **um intervalo
maior do que a maior lacuna plausível entre duas sessões do mesmo usuário**.

Critério concreto recomendado: **remover após 6 meses da data de deploy deste
PR**, o que cobre com folga usuários sazonais e quem só acessa em auditoria
anual — arredondando para o próximo ciclo de release depois disso.

**Decisão deliberada: sem marcador de "já limpei".** Um marcador seria ele
próprio uma chave nova, que precisaria de outra limpeza depois; e o custo que ele
evitaria é uma varredura de `localStorage.length` por carga, com a lista de
chaves exatas resolvida por `removeItem` direto. A varredura existe apenas para o
prefixo do phase44.

---

## 3) Testes

### Adicionados

| Gate | O que trava |
|---|---|
| `PR4 L-1` | todas as chaves legadas conhecidas são apagadas |
| `PR4 L-2` | dado alheio sobrevive; e o phase42 continua limpando o dele |
| `PR4 L-3` | idempotência — a segunda execução não quebra nem apaga a mais |
| `PR4 L-4` | sem `localStorage` (janela privativa), a inicialização não cai |
| `PR4 L-5` | a rotina não usa limpeza total, não afrouxa o prefixo, mantém a marca de aposentadoria e não reintroduz constante de versão sem leitor |
| `PR4 R-1` | os quatro arquivos não existem, não são servidos, não são injetados |
| `PR4 R-2` | as quatro flags não são declaradas nem lidas por arquivo servido |
| `PR4 R-3` | um owner de fetch, um de dropdown, zero interceptadores de navegação em captura |
| `PR4 R-4` | nenhum HTML servido nem o `styles.css` cita os quatro módulos; o que sobreviveu (`[data-confirm-action]`, a regra de transição das duas famílias restantes, `viaHistorico`) continua de pé |

`L-1`..`L-5` foram escritos e passaram **antes** de qualquer arquivo ser
removido, como o contrato desta frente exige.

### Convertidos

| Gate | De | Para |
|---|---|---|
| `PR1 C-3` | caracterização de DEFEITO: a limpeza legada não era alcançada | contrato: a limpeza sobrevive aos módulos |
| `PR1 H-0` | três scripts injetados | um — só o phase42 |
| `PR1 Z-3` | ≥6 caracterizações de defeito registradas | registro vazio, com os cinco campos ainda exigidos de quem voltar a usá-lo |
| `PR2A A-5` | três gates de submit no contrafactual | os dois reais |
| `PR2B B-6` | consumidor órfão de `epi:action-*` | ausência de produtor **e** de consumidor |
| `PR2B B-9` | matriz de destino do concorrente | ausência de segundo wrapper de fetch |
| `PR2C C-5` | comparação de custo com o phase44 | par fixo de listeners do owner, com dois dropdowns no fixture |
| `PR2D D-3` | "só o multitab copia a guarda" | "ninguém copia a guarda" |
| `PR2D D-9` | matriz módulo × flag × destino | matriz módulo × estado × owner sobrevivente |
| `PR3 A-7` | comparação A/B/C do phase41 | a decisão foi executada e nada persiste campo |
| `#343 F5-B N3` | phase42 publica / phase43 consome | phase42 publica em RAM e não persiste |
| `feature-flags-rt` (3 gates) | flag do phase41 como cobaia | flag do phase42 |
| `test_abort_scopes_are_module_specific` | três módulos | o que sobrevive |
| `CHAVES_PROIBIDAS`, `LISTENERS_DE_VIEWCHANGE`, `ARQUIVOS_PAREADOS_F5B` | inventários com os quatro módulos | inventários do que existe |

### Removidos

44 gates JS cujo sujeito deixou de existir (contrafactuais de phase41, 42×43,
bridge de fetch, dropdown do phase44 e multitab), mais 3 arquivos de teste
estrutural em Python. Nenhum foi silenciado: todos tinham como única função
afirmar a presença ou o comportamento de código que não existe mais.

Um caso merece nota. O gate `#343 F5-B.1 G-B-2` parecia convertível — "troca real
de contexto continua fechando a UI transitória" soa como contrato do app. A
conversão falhou e o teste apanhou o erro: **`closeTransientUi()` era função do
próprio multitab**, não do `app.js`. Sem o módulo, o comportamento não existe, e
o gate virou remoção.

### Resultado

| Suíte | Antes | Depois |
|---|---:|---:|
| Gates JS | 396 | **356** |
| pytest (corporate) | 3 855 | **3 825** |
| pytest (app) | 3 850 | **3 820** |

A contagem cai porque 44 gates mediam código que não existe mais. Os contratos
que importam — owner único de submit, de fetch, de dropdown e de navegação;
devolução de foco no Escape; ausência de captura concorrente; não persistência de
rascunho; comportamento do phase42 — continuam todos protegidos, e ganharam
**quatro** gates de ausência que antes não existiam. A meta nunca foi recuperar
396: é a qualidade do contrato que conta, e ela subiu.

---

## 4) Matriz final

| Módulo | Estado anterior | Estado final | Owner sobrevivente |
|---|---|---|---|
| `ux-phase41.js` | inerte | **REMOVIDO** | nenhum — rascunho não é requisito (PR 3) |
| `ux-phase42.js` | ativo sob flag | **MANTIDO** | ele mesmo |
| `ux-phase43.js` | inerte/redundante | **REMOVIDO** | `app.js` + backend (regra de envio) |
| `ux-phase44.js` | inerte/redundante | **REMOVIDO** | `error-monitor.js` (fetch) + `app.js` (dropdown) |
| `multitab-navigation.js` | inerte/redundante | **REMOVIDO** | `app.js` — `bindMenuNavigation` → `navigateToView` |

---

## 5) Busca residual

Feita ao final, sobre o repositório inteiro, com os termos que a autorização
exigiu. Ela **não** foi uma formalidade: encontrou quatro resíduos reais que o
inventário inicial não tinha visto, e todos foram tratados nesta fatia.

### 5.1 O que a busca encontrou de novo

| Achado | Prova de exclusividade | Destino |
|---|---|---|
| `#phase41-activity-indicator` e `<section id="multitab-nav-root">` no `_topbar.html` (e no `index.html` gerado) | varredura dos 85 arquivos servidos: nenhum JS os procura; só o `styles.css` os estilizava | **removidos** |
| ~200 linhas de CSS em `static/styles.css` (4 blocos: phase41, phase43, phase44, multitab) | extraídos os 56 tokens de classe/keyframe/atributo dos blocos e buscados em todo o código servido — as **únicas** referências eram o DOM morto acima | **removidos** |
| o sinal `viaMultitab` no evento `epi:viewchange` | busca por produtor em todo o `static/`: **zero**. O produtor era `multitab-navigation.js`. O campo era sempre `false` e as duas guardas do `app.js`, ramos mortos | **removido do `app.js`** |
| `#phase43-confirm, [data-phase44-confirm-yes]` no seletor de confirmação do `ux-analytics.js` | os dois nós eram criados em runtime pelos módulos removidos e não existem em nenhum HTML servido; `[data-confirm-action]` é markup do app e continua | **seletor reduzido ao que sobrevive** |

Uma regra de CSS foi **editada, não removida**:
`body.ux-hierarchy-enabled …, body.spa-navigation-enabled …, .phase44-transition-pulse .view.active { animation-duration: .16s }`
perdeu só o terceiro seletor. As duas famílias que restaram continuam com a
transição encurtada — o gate `PR4 R-4` prova isso positivamente, para que a
remoção do seletor morto não leve junto o comportamento vivo.

### 5.2 Classificação de todas as ocorrências restantes

| Termo | Onde restou | Classificação |
|---|---|---|
| `phase41`, `phase43`, `phase44` | lista de chaves do cleanup em `app.js`; gates `PR4 L-*`/`R-*` e fixtures; comentários que explicam por que um trecho do owner existe (ex.: a devolução de foco do PR 2C); documentos | cleanup legado temporário / teste de ausência / histórica legítima |
| `multitab` | um comentário em `navigation.js` explicando o termo que saiu do `isEnabled()`; gates de ausência; documentos | histórica legítima / teste de ausência |
| `ux_phase41_enabled` e as três irmãs | lista de chaves do cleanup; gates `PR4 R-2`; `PHASE4_8` e `PHASE5_0` marcados como históricos, com as linhas tachadas | cleanup legado temporário / teste de ausência / histórica legítima |
| `epi:action-` | comentário do `ux-analytics.js` que registra por que os ouvintes saíram; gates `PR2B B-6`; documentos | histórica legítima / teste de ausência |
| `__EPI_PHASE41_BOUND__`, `__EPI_PHASE43_BOUND__`, `__EPI_PHASE44_BOUND__` | nenhuma em código servido; só nos documentos e no gate que prova a colisão de guarda que os módulos tinham | histórica legítima / teste de ausência |
| `epi:ux:phase41`, `epi:ux:phase43`, `epi.ux.phase44` | lista de chaves e prefixo do cleanup; fixture `STORAGE_LEGADO_DE_EXEMPLO` | cleanup legado temporário / teste |

**RESÍDUO INDEVIDO: nenhum.** Verificado por `PR4 R-1`..`R-4` na suíte JS, que
falham se qualquer um voltar.

### 5.3 Achados registrados para outra frente

Dois, e nenhum é resíduo dos quatro módulos.

**(a) `ux-phase42.js` — ponte em memória sem consumidor.** O owner que permanece
tem, em comentário e em código, uma ponte publicada "para o card de sugestão do
phase43", além de uma guarda de `viaMultitab`. Os dois consumidores saíram nesta
fatia. A autorização deste PR proíbe explicitamente reescrever, renomear ou
refatorar o `ux-phase42.js`, então **nada foi tocado ali** — nem o código, nem os
comentários, que hoje descrevem um consumidor que não existe. É a única
assimetria conhecida desta fatia, e está aqui declarada em vez de escondida: uma
frente autorizada a mexer no phase42 deve decidir se a ponte vira RAM interna ou
sai.

**(b) `static/navigation.js` — varredura de campos.** Atrás de
`ux_hierarchical_navigation_enabled`, que esta frente **nunca auditou**,
`captureContext()` faz a mesma varredura de `input[id], select[id], textarea[id]`
que o phase41 e o multitab faziam — **em memória, sem storage**. Não é resíduo
desta frente e não foi tocado, mas é a mesma forma que o PR 2D e o PR 3
analisaram, e merece a mesma pergunta numa frente própria.

O gate `PR3 A-7` foi corrigido por causa de (b): ele afirmava que a única
varredura de campos era a do phase41. Era falso, e o gate apanhou. Agora ele
trava o que a F5-C de fato decidiu — que nenhum arquivo servido **persista** campo
de formulário.

---

## 6) Critério de sucesso

| Item | Evidência |
|---|---|
| phase42 continua funcionando | `PR1 B-1`..`B-5`, `PR2A A-5`, `#343 F5-B N3` |
| quatro módulos não são servidos | `PR4 R-1` |
| quatro flags desapareceram | `PR4 R-2` |
| sem perda funcional | nenhum contrato comportamental foi removido sem owner que o substitua (seção 4) |
| sem owners concorrentes reintroduzidos | `PR4 R-3` |
| DOM e CSS mortos não voltam | `PR4 R-4` |
| resíduos limpos por código sobrevivente | `PR4 L-1` |
| dados não relacionados preservados | `PR4 L-2` |
| paridade entre repositórios | dígitos `DIGESTO_PARIDADE_F4` e `DIGESTO_PARIDADE_F5B` recalculados; arquivos tocados byte a byte idênticos |
