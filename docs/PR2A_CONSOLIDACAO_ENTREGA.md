# #343 PR 2A — Consolidação: phase43 × phase42

Data: 2026-09-15. Primeira fatia do PR 2.

**Resultado: nenhuma linha de código de produção foi alterada.** A capacidade que
se pretendia absorver já tem dono, e o dono a implementa melhor que o candidato.

## 1) O que foi investigado

O PR 1 apontou como capacidade exclusiva do `ux-phase43.js` a **exigência do
código lido do item de estoque**, e a autorização do PR 2A mandou confirmar isso
"no código e nos testes" antes de absorver. A confirmação **refutou** a
candidatura.

## 2) Onde a regra realmente mora

| Camada | Arquivo | O que faz |
|---|---|---|
| **Decisão** | `modules/deliveries/service.py` | `if not stock_item_id or not stock_qr_code: raise ValueError('Leitura do código da unidade é obrigatória.')` — a regra de negócio, no backend, como o contrato do projeto exige |
| **Antecipação** | `static/app.js`, `saveSimpleForm`, ramo do `#delivery-form` | recusa antes da rede, com mensagem traduzida (`delivery.readQrBeforeSubmit`) |
| Cópia inerte | `static/ux-phase43.js`, `validateContext()` | terceira cópia, sem as exceções que o dono conhece |

Os outros cinco campos obrigatórios da entrega (`company_id`, `employee_id`,
`epi_id`, `quantity`, `delivery_date`) têm `required` no HTML e são barrados pela
validação nativa antes do submit chegar ao JavaScript. O campo do código é
`readonly` — e controle `readonly` é **barrado da validação de restrições** pelo
próprio padrão, então `required` nele seria inerte. Essa é a única lacuna da
camada nativa, e é exatamente a que o `app.js` preenche à mão.

## 3) Por que a cópia do phase43 é pior que o original

Medido em `PR2A A-3` e `PR2A A-4`:

- **Devolução.** O app roteia devolução para `/api/devolutions` e **remove**
  `stock_item_id` e `stock_qr_code` do payload. O `validateContext()` do phase43
  exige o código incondicionalmente e o arquivo inteiro não menciona devolução.
  Ativá-lo **bloquearia toda devolução**.
- **Leitura em lote.** O app tem o caminho da sessão de QR, que valida cada item
  da sessão separadamente. O phase43 só conhece o campo único.
- **Idioma.** A mensagem do app passa por `tr()`; a do phase43 é literal.

## 4) Por que o PR 1 errou, e o que mudou no harness

O gate `PR1 H-2` mediu que o phase43 exige o código e concluiu que a capacidade
era exclusiva. Ele comparou **phase42 com phase43** e nunca mediu o `app.js` —
por um limite que o próprio PR 1 tinha declarado: o bind do submit da entrega
(`bindAppListener(#delivery-form, 'submit', ...)`) mora dentro do `init()`, que
o harness não executava.

O PR 2A fechou esse buraco sem tocar em produção:

- `dispararBootstrapDoApp()` dispara `DOMContentLoaded` no documento do harness,
  e o **próprio app** chama `init()` pelo listener que ele já registra. É o
  caminho de produção, não um atalho.
- Foi preciso dar ao contexto um `FormData` (o `formValues()` do app é
  `Object.fromEntries(new FormData(form).entries())`) e a permissão
  `deliveries:create` no fixture.

Limite novo, declarado: `saveSimpleForm` e `init` são `async function`
declaradas dentro do bloco `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) {` que
envolve o `app.js` inteiro, e **declaração `async function` em bloco nunca vaza
para o global** — a hoisting legada do Annex B não se aplica a elas. Por isso
elas não existem em `ctx`, enquanto `navigateToView` e `showView`, que são
`function` comum, existem. Chamá-las diretamente não é possível; o bootstrap
real é.

## 5) Contabilidade dos gates de submit

Medido em `PR2A A-5`:

| Cenário | Gates de submit no `#delivery-form` | Quem |
|---|---|---|
| Produção hoje | **1** | `app.js` — regra de negócio |
| `ux_phase42=1` | 2 | `app.js` + phase42 (revisão explícita) — **arranjo autorizado** |
| `ux_phase42=1` + `ux_phase43=1` | 3 | o terceiro é o que esta fatia dispensa |

O contrato "um owner por responsabilidade" é sobre a **regra**, não sobre a
contagem de listeners. O phase42 permanece owner do assistente, e a exigência de
revisão explícita é responsabilidade dele — distinta da regra de negócio da
entrega, que é do backend.

## 6) Entregáveis

| Item | Resultado |
|---|---|
| Responsabilidade consolidada | Exigência do código lido no envio da entrega |
| Owner anterior | `app.js` (antecipação) + backend (decisão) — já era |
| Owner final | **inalterado** |
| Capacidade absorvida | **nenhuma** — não havia o que absorver |
| Código concorrente dispensado | `validateContext()` e o gate de submit do `ux-phase43.js` |
| Arquivos de PRODUÇÃO alterados | **nenhum** |
| Testes acrescentados | `PR2A A-1`..`A-5` |
| Gates do PR 1 convertidos | `H-1` e `H-2` (comentário corrigido), `Z-1` (linha nova), `Z-2` (phase43 reclassificado), `Z-4` (passa a cobrir os gates do PR 2) |
| Impacto comportamental | **zero** |
| Flag órfã | `ux_phase43_enabled` — lida **somente** pelo próprio `ux-phase43.js`; declarada em `app.js`, `js/core/feature-flags.js` e `error-monitor.js`. Remover no PR 4, junto do módulo |
| Classificação do módulo | **REMOVER NO PR 4** |

## 7) O que sobra no phase43, e por que não impede a remoção

A autorização pede parar e documentar se aparecer outra capacidade exclusiva.
Aparecem quatro, e todas são **afordâncias de interface**, não regra de negócio:

| Afordância | Situação |
|---|---|
| Barra fixa de ação (`#phase43-sticky-actions`) | sem dono; nunca rodou em produção |
| Confirmar por teclado (Enter / Ctrl+Enter) | sem dono ativo; o phase41 tem equivalente, também inerte |
| Modo manual | interno ao próprio phase43 |
| Eco do estado do envio | o `app.js` **emite** `epi:delivery-submit-start/success/error`; o phase43 só os renderiza no DOM dele. O `ux-analytics.js` já consome os mesmos eventos |

Nenhuma delas carrega regra de negócio, e nenhuma jamais alcançou um usuário —
o módulo nunca inicializou. Por isso a classificação é **REMOVER NO PR 4**, e
não "manter por capacidade exclusiva". A remoção física fica para o PR 4 para
não ampliar o escopo desta fatia, conforme a autorização permite.
