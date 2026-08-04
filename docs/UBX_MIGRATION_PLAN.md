# Plano de Migração UBX — Fatoração de `app.js` e `index.html`

Status: **plano aprovado para execução incremental**. Auditado em 2026-07-30.

## Auditoria estrutural do repositório (2026-07-30)

Esta auditoria cobre a organização dos três clientes/servidores mantidos no monorepo, sem alterar
regras de negócio. O inventário foi feito sobre os arquivos versionados, os registradores de rotas,
os testes e os pipelines existentes. Neste documento, **UBX** continua sendo o nome da arquitetura-
alvo já adotada pelo projeto; não representa uma reescrita nem uma nova camada concorrente.

### Inventário e limites arquiteturais

| Superfície | Estado observado | Limite que deve permanecer canônico |
|---|---|---|
| Backend Python/REST | `app.py` é o composition root; 23 módulos de domínio registram rotas no `core.router`; serviços e repositórios já estão separados gradualmente | `modules/<domínio>/routes.py` adapta HTTP e `service.py` concentra a aplicação; `core/` contém infraestrutura transversal |
| Web legado | `index.html` é gerado por fragmentos; os assets têm versão por hash; o runtime ainda depende de `static/app.js` (16.227 linhas) | `static/js/core`, `utils`, `modules` e `views`, carregados nessa ordem; `app.js` deve terminar apenas como bootstrap compatível |
| Flutter | Monorepo Melos com app e pacotes `epi_api`, `epi_design` e `epi_i18n`; features usam Cubit/BLoC | UI → Cubit → `ApiClient`; tokens/componentes em `epi_design`; regras de negócio e financeiras somente no backend |
| Dados/tenancy | Migrações Python e Supabase coexistem para os runtimes suportados | Escopo explícito por `tenant_id`/`company_id`/`unit_id`, autorização no servidor e RLS no Supabase |
| Qualidade/entrega | 160 arquivos de teste Python e pipelines separados para backend, contratos, segurança, Flutter, Android e iOS | Mudanças incrementais, contrato primeiro e rollback por PR, sem migração *big-bang* |

### Evidências de evolução já concluída

- **Fase 0 concluída:** `scripts/build_index.py` calcula uma versão determinística a partir do
  conteúdo JS/CSS e resolve `__ASSET_VERSION__`; os testes impedem que o marcador chegue ao HTML
  servido.
- **Fase 1 concluída no contrato HTTP:** `app.js` mantém `api`, `apiOptional` e
  `apiWithBootstrapRetry` apenas como adaptadores de compatibilidade para
  `static/js/modules/api-client.js`. O teste estrutural impede a reintrodução da implementação.
- **Backend em modularização avançada:** as rotas dos domínios são registradas no composition root,
  enquanto os serviços canônicos vivem em `modules/`. A extração deve continuar sem criar um
  segundo framework de aplicação.
- **Flutter já possui fronteiras explícitas:** Design System, cliente da API e internacionalização
  são pacotes reutilizados pelo app Web/Android/iOS. Não há justificativa arquitetural para
  duplicá-los dentro de cada feature.

### Lacunas e duplicações encontradas

1. **P0 — monólito web:** `static/app.js` continua sendo o maior ponto de acoplamento e risco de
   regressão. A prioridade permanece extrair um domínio por PR, preservando os nomes globais como
   shims temporários.
2. **P0 — múltiplos adaptadores HTTP nas views:** `feedback.js`, `profile.js`, `procurement.js`,
   `fichas.js`, `purchases.js` e `employee-portal.js` ainda declaram wrappers locais chamados `api`.
   `devolution.js` e `feedback-detail.js` já consomem o cliente canônico.
   `fichas.js`, `purchases.js`, `feedback-detail.js` e `employee-portal.js` ainda declaram wrappers
   locais chamados `api`. `devolution.js` foi o primeiro domínio migrado para o cliente canônico.
   `fichas.js`, `purchases.js`, `feedback-detail.js`, `employee-portal.js` e `devolution.js` ainda
   declaram wrappers locais chamados `api`; `devolution.js` também possui um wrapper de retry.
   Eles não devem ser substituídos isoladamente: primeiro deve ser definido um único contrato de
   consumo do `api-client.js`, com teste de compatibilidade, e então migrados por domínio.
3. **P1 — composition root Python volumoso:** `app.py` ainda importa muitos serviços e símbolos de
   migração diretamente. Extrações futuras devem mover somente a composição/registro para módulos
   existentes; handlers, assinaturas e ordem de bootstrap precisam permanecer idênticos.
4. **P1 — duas interfaces web durante a migração:** o SPA legado e o Flutter Web coexistem. A fonte
   de verdade continua sendo a REST API; nenhuma regra deve ser copiada de um cliente para o outro.
5. **P2 — documentação histórica dispersa:** ADRs e auditorias registram decisões válidas, mas este
   plano deve ser o índice operacional da migração UBX. Novas fases devem referenciar a decisão já
   existente em vez de criar planos paralelos.

> **Gate de unificação:** a duplicação de adaptadores HTTP nas views foi registrada antes de qualquer
> extração adicional. Conforme a política do projeto, a Fase 2 não deve avançar criando outro cliente
> ou wrapper. O próximo PR de código deve propor e testar a unificação desses adaptadores no módulo
> canônico existente.

### Arquitetura-alvo e dependências permitidas

```text
Web/Flutter UI
      │
      ▼
controller | Cubit/BLoC
      │
      ▼
cliente REST canônico
      │
      ▼
router HTTP ──► serviço de domínio ──► repository/conexão
      │                    │
      └── autenticação ────┴── escopo tenant/company/unit + permissões
```

Dependências inversas (serviço importando handler, widget acessando Dio diretamente, view web
reimplementando cliente HTTP ou cliente calculando regra financeira) ficam proibidas. Integrações
Supabase, Firebase e Mercado Pago devem entrar por adaptadores/configuração já existentes, nunca por
URLs, tokens ou IDs codificados no cliente.

### Sequência segura de execução

1. Congelar o contrato público da área com testes antes da extração.
2. Mapear referências globais, endpoints, permissões e filtros multi-tenant da área.
3. Reutilizar o cliente HTTP e o estado existentes; não criar implementações paralelas.
4. Extrair somente um domínio em `api/state/view/events/controller`, mantendo shim reversível.
5. Executar formatter, lint, testes Python/JS/Flutter aplicáveis e smoke no navegador.
6. Remover o shim apenas quando não houver referências e em PR separado de limpeza.

### Critérios mensuráveis de conclusão

- `static/app.js` contém somente bootstrap, registro e shims ainda explicitamente rastreados.
- Cada regra de negócio possui uma implementação no backend e testes de contrato para os clientes.
- Nenhuma view mantém cliente HTTP próprio após a migração do respectivo domínio.
- Toda consulta protegida valida ator, permissão e escopo multi-tenant no servidor.
- `index.html` continua reprodutível pelo build, e Web/Android/iOS usam os mesmos contratos REST.
- Cada fase é pequena, reversível, documentada e aprovada pelos checks existentes.

## Por que (motivação)

- `static/app.js` é um monólito de **16.227 linhas** dentro de **um único closure**
  (`if (!globalThis.__EPI_APP_RUNTIME_LOADED__) { ... }`).
- Um único defeito nesse arquivo degrada o sistema inteiro. Exemplos reais já corrigidos:
  - guard tornou `async function` block-scoped → loaders de Compras viraram no-op (#620);
  - cache-buster manual dessincronizado → JS obsoleto em produção (#619).
- Os módulos de view (`static/js/views/*.js`) hoje são **cascas finas** que delegam ao `app.js`
  via `globalThis.<fn>()` — acoplamento implícito e frágil.

## Estado atual (o que já existe)

`index.html` **já é modular** via `scripts/build_index.py` (montado de `static/views/_layout.html`
+ fragmentos `_head/_login/_sidebar/_topbar/_modals/_scripts` + views). O CI valida com
`tests/test_index_html_build.py`.

Estrutura JS parcial já presente:

```
static/js/
  core/      config.js  constants.js  feature-flags.js  permissions.js
  modules/   api-client.js  auth.js  router.js  feature-flags-rt.js  permissions-rt.js
  utils/     dom.js  storage.js  debug.js  perf.js
  views/     dashboard.js  epis.js  estoque.js  fichas.js  purchases.js  devolution.js
             employee-portal.js  feedback.js  feedback-detail.js  profile.js
             ui-helpers.js  view-helpers.js
  test/      run-tests.js   (harness Node em sandbox vm — permite testar módulos extraídos)
```

**Conclusão:** a arquitetura-alvo já existe. A migração = **mover a lógica do `app.js` para os
módulos** e **inverter a dependência** (módulos passam a ser donos da lógica; `app.js` vira um
bootstrap fino). Não é reescrever do zero.

## Princípios (inegociáveis)

1. **Aditivo e reversível.** Cada fase mantém a API pública (`globalThis.<fn>`) compatível via
   *shim* temporário, então nada quebra durante a transição.
2. **Uma fase = um PR pequeno e revisável**, validado em navegador antes do merge.
3. **Sem big-bang.** Nunca mover milhares de linhas de uma vez.
4. **Testável.** Toda lógica extraída ganha teste no harness `static/js/test/run-tests.js`.
5. **Versão no build.** Trocar o cache-buster manual por versão derivada no `build_index.py`
   (hash/commit) — elimina a causa-raiz do desync de cache (Fase 0).

## Validação por fase (obrigatória)

- `pytest` (inclui `test_js_unit.py`, `test_index_html_build.py`, `test_static_assets.py`).
- `node --check` em cada arquivo novo/alterado.
- **Smoke em navegador** (responsabilidade conjunta, pois o SPA não roda em CI): Login →
  Bootstrap → a área migrada (ex.: cada sub-aba de Compras) → DevTools sem erros.

## Fases

### Fase 0 — De-risk (fundação) — **concluída**
- `build_index.py`: injetar `ASSET_VERSION` (git short SHA ou hash do conteúdo) nos `?v=` ao montar
  o `index.html`; trocar os `?v=` hardcoded dos fragmentos por `?v=__ASSET_VERSION__`.
- Ajustar `test_index_html_build.py`/`test_static_assets.py` ao novo contrato.
- Remover arquivos mortos (ex.: `static/app.v20260326.js` — **já removido**).
- **Resultado:** nunca mais JS obsoleto por `?v=` esquecido.

### Fase 1 — Núcleo HTTP/estado (consolidação) — **contrato HTTP concluído**
- `app.js` delega `api`/`apiOptional`/`apiWithBootstrapRetry` ao módulo canônico
  (`apiFetch`/`apiFetchOptional`/`apiFetchWithRetry`), sem manter a lógica HTTP duplicada.
- Expor `state`/`refs` por um acessor estável (`__EPI_APP_STATE__` já existe) e parar de depender de
  closure para o que os módulos precisam.
- Testes no harness para a camada de API.

### Fase 2 — Módulo Compras (alto valor)
Extrair de `app.js` para `static/js/modules/purchases/`:
- `purchases.api.js` — endpoints: requisições, fornecedores autorizados, aprovações, POs, demandas,
  criar requisição, atualizar status, aprovar, gerar PO.
- `purchases.state.js` — `_authorizedSuppliers`, listas, aba ativa, filtros.
- `purchases.view.js` — render de tabelas/dropdowns/estados (vazio/erro/loading).
- `purchases.events.js` — binds (parte já em `views/purchases.js`).
- `purchases.controller.js` — orquestra api→state→view + permissões; expõe `initPurchaseModule()`.
- Durante a transição, `globalThis.loadAuthorizedSuppliers` etc. apontam para o controller (shim),
  até remover as versões do `app.js`.

### Fase 3..N — Demais módulos (um por PR)
Ordem sugerida por isolamento/risco: `delivery` → `stock` → `reports` → `employees` → `dashboard`.
Cada um no mesmo padrão (api/state/view/events/controller).

### Fase final — Limpeza
- Remover funções migradas do `app.js` e os shims.
- `app.js` reduzido a bootstrap: carregar config, montar estado, registrar módulos, iniciar router.
- Atualizar `index.html`/`_scripts.html` (via build) para a lista final de módulos.

## Riscos e mitigação
- **Acoplamento por closure** (causa dos bugs recentes): mitigado pelo contrato explícito
  `globalThis`/`__EPI_APP_STATE__` e shims durante a transição.
- **Sem execução de browser no CI:** mitigado por smoke manual por fase + testes de harness.
- **Ordem de carga dos `<script>`:** manter `core` → `modules` → `views` → `app.js` (bootstrap)
  no `_scripts.html`; `app.js` por último.

## Próximo passo
Executar o **gate de unificação dos adaptadores HTTP locais das views**, com contrato e teste de
compatibilidade sobre `static/js/modules/api-client.js`. Somente depois iniciar a **Fase 2**
(Compras), sem criar um segundo cliente HTTP.
