# Fase 5.0 — Ativação Controlada (Go Live Progressivo)

Data: 2026-04-24. Revisado em 2026-09-14 (correção factual — ver seção 10).

> **Revisão factual — auditoria de execução dos módulos UX.**
> A matriz original desta seção marcava "Pronto para produção: SIM" para 4.1, 4.3 e
> 4.4. A auditoria mediu a execução real dos módulos e concluiu que quatro dos cinco
> **não chegam a inicializar**: não é que estejam prontos e desligados — eles retornam
> antes de ler a própria flag. A matriz abaixo substitui a coluna binária por estados
> de maturidade. Ver a seção 10 para a evidência.

## 1) Matriz de maturidade por módulo

Estados, em ordem. Um módulo só alcança um estado se alcançou todos os anteriores:

1. **implementado** — o código existe no repositório.
2. **testado estruturalmente** — há teste que verifica a presença de texto/símbolos no arquivo.
3. **testado comportamentalmente** — há teste que EXECUTA o módulo na ordem de carga
   de produção e observa efeito (listener registrado, DOM alterado, storage escrito).
4. **habilitável** — ligar a flag produz efeito observável em produção.
5. **aprovado para produção** — decisão humana registrada, após 3 e 4.

| Fase | Flag (querystring) | Maturidade alcançada | Habilitável hoje? | Observação |
|---|---|---|---|---|
| 4.1 | `ux_phase41_enabled` (`ux_phase41=1`) | 2 — testado estruturalmente | **NÃO** | Inerte: colisão de chave de guarda. A flag nunca é lida. |
| 4.2 | `ux_phase42_enabled` (`ux_phase42=1`) | 3 — testado comportamentalmente (parcial) | SIM | Único módulo que inicializa. Registra 13 listeners com a flag ligada. |
| 4.3 | `ux_phase43_enabled` (`ux_phase43=1`) | 2 — testado estruturalmente | **NÃO** | Inerte: mesma colisão. Depende funcionalmente da 4.2 sem declarar a dependência. |
| 4.4 | `ux_phase44_enabled` (`ux_phase44=1`) | 2 — testado estruturalmente | **NÃO** | Inerte: mesma colisão. |
| Hierarchy | `ux_hierarchical_navigation_enabled` (`ux_hierarchy=1`) | não auditado nesta rodada | não verificado | Fora do escopo da auditoria. O "SIM" anterior não foi confirmado nem refutado. |
| SPA | `spa_navigation_enabled` (`ux_spa_navigation=1`) | não auditado nesta rodada | não verificado | Idem. |
| Tabs | `ux_multitab_navigation_enabled` (`ux_multitab=1`) | 2 — testado estruturalmente | **NÃO** | Inerte por outro motivo: consome `__EPI_APP_NAV_API__` antes de ela ser publicada. |

Nenhum módulo está no estado 5. Este documento não aprova nenhum para produção.

## 2) Estratégia de rollout progressivo

### Fase 1 (interna)
- Ativar apenas via querystring para usuários-chave.
- Confirmar login, troca de telas, e console limpo.

### Fase 2 (teste real)
- Ativar manualmente via `localStorage` para piloto restrito.
- Exemplo:
  - `localStorage.setItem('ux_phase44_enabled', '1')`
  - `localStorage.setItem('ux_multitab_navigation_enabled', '1')`

### Fase 3 (parcial)
- Ativar para grupos controlados por perfil/time de operação.
- Coletar snapshot de monitoramento por tela e por API.

### Fase 4 (produção total)
- Somente após janela estável (sem erro crítico regressivo).
- Considerar `default ON` em janela planejada com rollback pronto.

## 3) Controle central de flags

- Resolver único: `getFeatureFlagResolution`.
- Precedência: **querystring > localStorage > default**.
- Exposição central segura: `window.__EPI_FEATURE_FLAGS__` (somente leitura).

## 4) Monitoramento operacional

`error-monitor.js` passa a expor `window.__EPI_MONITORING__.getSnapshot()` com:
- `errorsByModule` (contador por tela/módulo ativo);
- `unstableApis` (contador por endpoint/status);
- `criticalFailures` (buffer circular de falhas críticas).

## 5) Fallback obrigatório

Se houver instabilidade:
1. Remover querystring de ativação.
2. Zerar flags de piloto no `localStorage`.
3. Hard refresh.
4. Confirmar login e navegação no modo clássico (flags OFF).

## 6) Evidência objetiva desta rodada

- Sintaxe JavaScript validada.
- Suíte `pytest` completa aprovada.
- Nenhuma flag alterada para default ON.
- Sem criação de nova feature funcional de negócio.

> **O que essa evidência prova, e o que não prova.**
> Ela prova que o código compila e que as asserções existentes passam. Ela **não**
> prova que os módulos executam: a auditoria encontrou a suíte inteira verde
> (319 testes JS + 60 testes Python nos arquivos relacionados) com quatro dos cinco
> módulos inertes. CI verde e teste estrutural verde não são validação
> comportamental, e nenhum dos dois autoriza ativação. Ver seção 10.

## 7) Riscos remanescentes

1. Regressão combinatória em uso simultâneo de SPA + Hierarchy + Tabs.
2. Necessidade de validação manual final de console em browser real com extensões desabilitadas.
3. Dependência de disciplina operacional para desligamento rápido por flag em incidente.

## 8) Recomendação

> **Revisada pela auditoria.** A recomendação original ("Pronto para ativação
> controlada da Fase 5.0") pressupunha que ligar a flag produzisse efeito. Para 4.1,
> 4.3, 4.4 e Tabs isso não acontece.

**Não ativar 4.1, 4.3, 4.4 nem Tabs.** Ligar a flag não produz efeito hoje, e a
correção que a faria produzir efeito precisa ser precedida pela consolidação de
ownership — ver seção 10.

**4.2 permanece habilitável** sob rollout faseado, com gate de estabilidade
(console limpo + navegação + operações críticas). Continua sem aprovação para
default ON.

## 9) Fase 5.0-A — Hardening final aplicado

### Riscos eliminados
- Interceptação duplicada/agressiva de `fetch` **dentro do `error-monitor.js`**
  (marca de idempotência `__EPI_MONITORED_FETCH__` e original preservado em
  `__EPI_FETCH_MONITOR_ORIGINAL__`). A auditoria registra que essa proteção é
  interna ao próprio monitor: `bindFetchFeedbackBridge()` em `ux-phase44.js`
  consulta apenas a própria marca (`__EPI_PHASE44_FETCH_BRIDGED__`) e não
  reconhece a do monitor. Hoje não há empilhamento porque o phase44 não
  inicializa — não porque os dois se coordenem.
- Crescimento não controlado de buffers de monitoramento.
- Mutação externa da API central de flags e monitoramento.
- Permanência da UX moderna durante incidente crítico.

### Limites definidos
- `errorsByModule`: máximo 50 eventos por módulo.
- `unstableApis`: máximo 50 endpoints monitorados.
- `criticalFailures`: buffer FIFO máximo 100 eventos.

### Salvaguardas automáticas
- Kill switch mestre: `ux_global_kill_switch` (`ux_kill_switch=1`) força UX em modo clássico.
- Rollback automático para modo clássico quando:
  - mais de 10 erros em janela de 10s; ou
  - mais de 5 respostas 5xx consecutivas.

### Status final
As salvaguardas desta seção (kill switch, limites de buffer, rollback automático)
foram verificadas como presentes no código. O status "pronto para rollout
controlado seguro" vale apenas para os módulos que efetivamente inicializam —
hoje, somente a 4.2. Default OFF e rollback por flag permanecem.

## 10) Auditoria de execução dos módulos UX

Medição por execução, não por leitura de código: cada arquivo servido foi carregado
num contexto isolado com o `ensureModuleBound` real extraído do `app.js`, contando
guarda de saída, leitura de flag e listeners registrados.

| Módulo | Inicializa hoje? | Onde para | Lê a flag? | Listeners com a flag ON |
|---|---|---|---|---|
| `ux-phase41.js` | não | `ensureModuleBound` ⇒ `false` | nunca | 0 |
| `ux-phase42.js` | **sim** | — chega ao `init()` | sim | 13 |
| `ux-phase43.js` | não | `ensureModuleBound` ⇒ `false` | nunca | 0 |
| `ux-phase44.js` | não | `ensureModuleBound` ⇒ `false` | nunca | 0 |
| `multitab-navigation.js` | não | `navApi.showView` ausente | sim | 0 |

### Causa em 4.1, 4.3 e 4.4 — colisão de chave de guarda

`ensureModuleBound(chave)` deriva o nome global `__EPI_<CHAVE>_BOUND__`. Os três
módulos gravam exatamente esse global nas primeiras linhas do próprio IIFE e, poucas
linhas abaixo, perguntam ao `ensureModuleBound` se já estão ligados. A resposta é
sempre "já ligado", e o módulo retorna **antes** do gate da flag.

Os dois padrões de guarda documentados em `spec/07-frontend-javascript.md` são
alternativas mutuamente exclusivas, não camadas que se somam. O phase42 usa apenas
`ensureModuleBound` — e é o único que inicializa.

### Causa em Tabs — ordem de publicação da API de navegação

`multitab-navigation.js` captura `globalThis.__EPI_APP_NAV_API__` na avaliação do
arquivo e retorna se `navApi.showView` não for função. Quem publica essa API é
`registerMultitabNavigationApi()`, chamada dentro do `init()` do `app.js`, ligado ao
`DOMContentLoaded`. Um `<script defer>` executa antes disso.

### Efeito colateral já em produção, com as flags desligadas

A limpeza de chave legada introduzida pela F5-B foi deliberadamente colocada **fora**
do gate da flag, para alcançar quem teve a flag ligada um dia. Mas ela está **depois**
da guarda no topo do IIFE. Medição com as flags desligadas:

| Módulo | Chave legada removida? |
|---|---|
| `ux-phase41.js` (`epi:ux:phase41:scroll:v2`) | **não** |
| `ux-phase42.js` (`epi:ux:phase42:memory:v2`) | sim |
| `ux-phase43.js` (`epi:ux:phase43:state:v1`) | **não** |
| `ux-phase44.js` (`epi.ux.phase44.filters.*`) | **não** |

As chaves dos três módulos inertes permanecem no `localStorage` indefinidamente.

### Sobre os testes que executam os módulos

A suíte JS carrega 4.1, 4.2 e 4.4 num contexto de execução. Nos casos em que o módulo
precisa realmente iniciar, o harness o carrega **antes** do `app.js`, para que o
`ensureModuleBound` usado seja o fallback local em vez do real — o próprio código do
harness documenta esse desvio. Ou seja: os testes de execução desses módulos rodam
sob uma ordem de carga que produção não usa. Isso é um dado, não uma crítica ao
harness; mas significa que passar nesses testes não equivale a funcionar em produção.

### Decisão registrada

A correção do bootstrap **não** é o primeiro passo. Enquanto ela não existe, quatro
conflitos de duplicidade permanecem contidos: persistência de formulário sem escopo
de usuário/tenant (4.1), dois gates de submit concorrentes no mesmo formulário de
entrega (4.2 + 4.3), segundo patch de `globalThis.fetch` sobre o do `error-monitor.js`
(4.4) e segunda autoridade de navegação sobre `bindMenuNavigation`/`navigateToView`
(Tabs). A ordem aprovada é: documentação, caracterização por testes, consolidação de
ownership, isolamento do 4.1, limpeza — e bootstrap por último, somente para os
módulos que sobreviverem à consolidação.

**Regra arquitetural adotada:** uma responsabilidade funcional tem um único owner. Se
a funcionalidade já opera por outro caminho, mantém-se o owner ativo, absorve-se nele
apenas o que faltar, e a implementação concorrente é removida — não reativada.
