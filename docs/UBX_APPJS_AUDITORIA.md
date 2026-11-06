

## 21. UBX Comercial — fatia C4 (2026-11-06): funções compartilhadas

Base: Corporate `main` `fad33dd4`, SaaS `main` `46262e8b` (C1 #1083/#457, SEC-C1-1 #1084/#458, C2 #1085/#459 e C3
#1086/#460 integrados; CI pós-merge verde; revisão automática da C3 sem achados; nenhum PR aberto). Somente
JavaScript do frontend: nenhum arquivo de backend, banco, migrações, endpoints, contrato HTTP, `modules/payments`,
`pagamento.js`, checkout, webhook, autenticação, autorização ou assinatura eletrônica de EPI.

### 21.1 Inventário dos candidatos

| Função | Domínio | Chamadores | Dependências / efeitos | Destino | Extrair na C4? |
|---|---|---|---|---|---|
| `formatCompanyCurrency` | Empresas (apresentação) | só `companies-view.js` (resumo, detalhes, tabela) | `formatCurrency` (shared/value-format) e `EpiI18n.lang`; pura | `modules/companies/ui/companies-view.js` | **Sim** — reutiliza o formatador oficial; módulo dono já existe |
| `renderMyCompanyDomains` | Minha Empresa (UI) | só `loadMyCompanyDomains` (`my-company-view.js`) | `tr`, `escapeHtml`, `domainStatusLabel`; escreve a tabela e as instruções DNS | `modules/my-company/ui/my-company-view.js` | **Sim** — o próprio módulo registrava que ela só ficara para trás pelo I18N-FULL-V1 |
| `fileToBase64` | Utilitário de arquivo (UI) | só `uploadSignedCommercialContract` (C3) | `FileReader`, `tr` | `modules/shared/ui/file-data-url.js` | **Sim** — o módulo oficial dos leitores de arquivo já existe; não é transferido artificialmente para o Comercial |
| `getCommercialSettings`, `cloneCommercialSettings`, `cloneDefaultCommercialSettings` | Estado da sessão | C1, C3, inicialização do `state`, `loadBootstrap` | `state`, `DEFAULT_COMMERCIAL_SETTINGS`, `deepClone` | permanecem no `app.js` | **Não** — ver §21.2 |
| `platformBrandDisplayName`, `savePlatformBrand` | Marca da plataforma | exportações da C3 / formulário de marca | `state.platformBrand`; `savePlatformBrand` faz `POST /api/platform-brand` | permanecem | **Não** — outro domínio, com HTTP; pede integração própria (proposta separada) |
| `openAndPrintPopup` | Infraestrutura de UI | Comercial (C3), Colaboradores, relatórios do `app.js` | `globalThis.open`, `safeOn`, timers | permanece | **Não** — infraestrutura compartilhada; candidata a `shared/ui` em proposta separada |
| `updateTopbarCompanyBadge` | Shell / topbar | só o `app.js` (contexto do usuário) | DOM do topbar, `state.user` | permanece | **Não** — não há módulo dono; criaria um módulo novo fora do Comercial (proposta separada) |
| listeners, resets de navegação, `renderAll` | Orquestração | — | — | permanecem | **Não** — camada de inicialização e navegação |

### 21.2 Estado comercial e sessão

- Não há duplicação de lógica: `cloneDefaultCommercialSettings()` e `cloneCommercialSettings(settings = DEFAULT)` são
  o mesmo `deepClone` (uma com o padrão fixo, usada só no inicializador do `state`; a outra no `loadBootstrap`).
- Fonte de verdade única: `state.commercialSettings`, substituído por inteiro a cada `loadBootstrap`
  (`cloneCommercialSettings(payload.commercial_settings || DEFAULT_COMMERCIAL_SETTINGS)`); `getCommercialSettings()`
  só lê (com o padrão quando vazio). Nenhum cache paralelo, nenhuma cópia em `localStorage`/`sessionStorage`.
- Troca de empresa: não muda os parâmetros (são da plataforma, vindos do bootstrap). Troca de usuário ou tenant: o
  bootstrap seguinte substitui o objeto; o encerramento da sessão é `location.reload()` (`terminateSession`), que
  descarta a memória. Sem referências obsoletas: C1/C3 chamam `getCommercialSettings()` a cada uso.
- Mover essas funções separaria o padrão e o inicializador do `state` do ciclo do bootstrap sem ganho; ficam no
  `app.js`.

### 21.3 O que mudou

- As três funções foram movidas com corpo idêntico e continuam globais com o mesmo nome (eram globais pelo Annex B);
  também entram nos namespaces congelados dos módulos (`__EPI_COMPANIES_UI__`, `__EPI_MY_COMPANY_UI__`,
  `__EPI_SHARED_FILE_DATA_URL__`). Nenhum módulo novo; `_scripts.html` não mudou (os três módulos já carregavam antes
  do `app.js`, e `file-data-url.js` antes do contrato comercial).
- Testes existentes ajustados pela mudança de lugar, sem mudar a intenção: os harnesses de Empresas e Minha Empresa
  passam a usar a função real nos dois lados (a cópia literal no "antes"), em vez de um substituto; o contrato do
  módulo Minha Empresa confere que `renderMyCompanyDomains` saiu do `app.js`.

### 21.4 Métricas

| Métrica | Antes | Depois |
|---|---|---|
| Linhas do `app.js` | 16.441 | 16.394 |
| Declarações de nível superior | 679 | 676 |
| Endpoints no `app.js` | 94 | 94 |
| Ciclos entre scripts | 0 | 0 |
| Módulos UBX | 55 | 55 |

### 21.5 Equivalência

- Caracterização antes de mover (commit próprio, verde contra o `app.js` original): fixture literal das três funções
  e `commercial-shared-runtime.js`, com as dependências reais (motor de tradução e os cinco catálogos,
  `formatCurrency`, `escapeHtml`, `domainStatusLabel`) e `FileReader`/`document` simulados. 1.735 comparações:
  moeda com 42 valores (zero e `-0`, negativos, meio-centavo, grandes, `NaN`/`Infinity`, inválidos, `null`/`undefined`,
  strings com vírgula, objetos) em 7 variantes de idioma por locale (sem motor, vazio, inválido, não suportado);
  domínios com marcação, padrões de `replace` (`$&`, `$1`, `$$`), subdomínio pendente antes de domínio próprio, sem
  campos, `null` e sem elementos; leitura de arquivo com e sem prefixo, vazia, nula, falha e duas simultâneas.
  0 divergências.
- Mutação: 17/19 sabotagens detectadas. As duas restantes são mutantes equivalentes: `value ?? 0` em vez de
  `value || 0` (o `formatCurrency` oficial já faz `Number(value || 0)`) e `is_primary == 1` em vez de
  `Number(is_primary) === 1` (a comparação frouxa com número coage como `Number()`).
- Chromium (`scripts/browser/ubx_commercial_shared.py`, no workflow de navegador): com o ICU real do navegador e o
  relógio fixo, moeda nos valores de borda, tela de Empresas, domínios e `fileToBase64` com `File` reais (PDF, texto
  Unicode, vazio, binário), antes e depois de trocar o idioma, reproduzem a referência gravada da `main`
  (`static/js/test/fixtures/ubx-commercial-c4-browser.json`) nos cinco idiomas. A `main` reproduz a própria
  referência; uma sabotagem no arredondamento reprova.

### 21.6 Segurança e isolamento

Autorização, escopo de empresa/unidade e isolamento por tenant seguem no backend, sem mudança. Os escapes de
`renderMyCompanyDomains` (host, tipo, status e valores DNS) e a ordem do `replace` com função (que impede a
interpretação de `$&` em valores vindos do servidor) estão cobertos por teste e por sabotagem. Nenhum listener foi
movido; nenhum armazenamento no navegador; nenhum achado novo.

### 21.7 Propostas separadas (fora da C4)

- Marca da plataforma: `modules/platform-brand/{integrations,ui}` com `savePlatformBrand` e `platformBrandDisplayName`.
- `openAndPrintPopup` para `modules/shared/ui/` (consumidores: Comercial, Colaboradores, relatórios).
- `updateTopbarCompanyBadge` num módulo de shell/topbar, junto com o restante do contexto do usuário.
