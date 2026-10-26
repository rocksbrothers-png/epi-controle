# FIX-NAV-REFRESH-V1 — gravar → atualizar a tela

Correção dos três achados residuais da auditoria independente da FIX-COLAB-TERC-V1 (Corporate #1063 / SaaS #437).
Base: Corporate `3c1b01d1`, SaaS `eac9fb35` (`main` com a FIX-COLAB-TERC-V1 integrada).
Sem mudança de backend, regra de negócio, permissão, contrato HTTP, banco ou dados.

## Causa comum

`loadBootstrap()` sem `{preserveView: true}` termina em `renderAll()` → `showView(defaultView())` fora do modo SPA. A
operação gravava certo, mas o usuário era levado ao Dashboard. Além disso, a gravação e a recarga ficavam no mesmo
`try`: uma falha da recarga aparecia como falha da gravação, e nada impedia o clique duplo.

## Inventário das recargas (`loadBootstrap(`)

São 37 chamadas: 33 no `app.js` e 4 em `modules/`/`views/`. A proposta citava "36"; a contagem exata desta base é 37.

| Grupo | Chamadas | Tratamento |
|---|---|---|
| **A — Inicialização / sessão / navegação** (mantêm a navegação atual) | `init` ×2, `handleLogin`, `handleForcedPasswordChange`, `retryBootstrap`, `advanceOnboardingStep` (o onboarding navega de propósito) | **Inalteradas.** Login, logout, inicialização e revalidação de permissões continuam iguais. |
| **B — Já preservavam a tela** | `archiveEntityRecord`/`restoreArchivedRecord`/`purgeArchivedRecord` (Colaboradores/Terceirizados, via `ARCHIVAL_ENTITIES.preserveView`), `saveSimpleForm` (3 formulários), `toggleEmployeeUnitLink` | Mantidas; ganham o fluxo novo de mensagem, clique único e recarga sem duplicata. |
| **C — Corrigidas nesta demanda** | `saveEmployeeMovement` (transferência), arquivar/desarquivar/excluir **EPI** (`ARCHIVAL_ENTITIES.epi.preserveView`), `archiveUnit`/`restoreArchivedUnit`/`purgeArchivedUnit` | `preserveView: true` + fluxo gravar → atualizar (abaixo). |
| **D — Mesma classe, fora do escopo autorizado** (registradas para decisão) | Comercial (`toggleCommercialStatus`, `saveCommercial`, `saveCommercialSettings`), Empresas (`openCompanyLogoEditor`, `saveCompany`, `toggleCompany`), Usuários (`copyUserAccessMessage`, `setTemporaryPassword`, `generateAndCopyTemporaryPassword`, `saveUser`, `users-view.js` ×2), `deactivateLegalEntity`, `finalizeFichaPeriod` ×2, `handleStockMovementSubmit`, `saveMyCompany`, `views/devolution.js`, botões "Atualizar" da Fase 2 (`refreshPhase2Module`, `refreshPhase2EpisModule`, `INTERACTIVE_TOOLS_MODULES.colaboradores.refresh`), `saveSimpleForm` nos demais formulários (Unidade, CNPJ, EPI, Entrega) | **Inalteradas.** Ao contrário do grupo C, muitas delas acontecem com a tela de origem em modo SPA ou em fluxos com navegação própria. Cada uma precisa de cenário próprio antes de mudar. |
| **Código morto** | `deleteRegistryEntity` (sem chamadores) | Inalterado; vai para a limpeza da UBX-V5. |

## Correção

**`static/js/modules/shared/ui/mutation-flow.js`** é um módulo UBX novo (`shared/ui`), carregado antes do `app.js`. Nenhuma
declaração nova foi criada no monólito: a guarda continua em 798 declarações e 112 endpoints.

- **`runExclusiveMutation(key, task)`**: uma execução por chave (`archive:epi:61`, `employee-movement`…). Clique duplo,
  ou repetição antes do diálogo abrir, não reenvia a gravação. A chave é liberada depois de sucesso **e** de erro.
- **`refreshAfterMutation(refresh)`**: roda a recarga depois da gravação já concluída. Se ela falhar, mostra o aviso
  verdadeiro `mutation.refreshFailed` ("A operação foi registrada, mas não foi possível atualizar a tela…") e não trata a
  gravação como falha. Com 401/403 não há aviso extra, porque `loadBootstrap` já encerra a sessão.
- **`coalesceLoad(key, load)`**: durante a recarga, a mesma lista pedida pela tela reaberta (`showView`) e pela própria
  operação gera **uma** requisição. Fora dessa janela não há efeito, então uma requisição iniciada antes da gravação nunca
  é reaproveitada e a lista nunca volta desatualizada. Isso vale para `loadArchivedRecords`, `loadArchivedUnits` e
  `loadOutsourcedCompanies`.

**`app.js`**:

- Arquivar, desarquivar e excluir: a gravação fica num `try` próprio, com a mesma mensagem de erro de antes e sem recarga
  quando a gravação é recusada. A recarga passa para `refreshAfterMutation`.
- Unidades e EPI usam `preserveView: true`.
- A transferência usa o mesmo fluxo, com envio único.

**RBAC**: manter a tela não ignora permissão. `showView` revalida com o bootstrap recarregado; quem perdeu acesso (por
exemplo, módulo Terceirizados desligado no tenant) volta à tela padrão. O cenário Chromium `lost_access` comprova isso, e
os gates `requirePermission` e o backend continuam decidindo.

**Auditoria das operações**: os mesmos endpoints e corpos (`actor_user_id`, `reason`, `justification`, `confirm_name`); a
trilha é do backend. Com o envio único por chave, a auditoria não registra mais tentativas repetidas por clique duplo.

**i18n**: uma chave nova, `mutation.refreshFailed`, aninhada como o motor `i18n.js` resolve, nos 5 idiomas (pt-BR, en-GB,
es-ES, fr-FR, nb-NO).

## Regressões

- **`static/js/test/fix-nav-refresh-runtime.js`**: 37 casos sobre as funções **reais** do `app.js` (fatiadas) e o módulo
  real. Cobre tela mantida, uma requisição de lista, gravação ok com recarga falha, gravação recusada e clique duplo, para
  8 operações, mais a transferência e o próprio módulo. Contra a `main`, **26 falham**.
- **`scripts/browser/fix_nav_refresh.py`** (Chromium, 5 idiomas, roda no workflow *Colaboradores and outsourced browser
  regression*): `transfer`, `epi_archival`, `unit_archival`, `lost_access`, `redundant_reloads`, `truthful_message` e
  `double_click`, com **35/35**. Contra a `main`, 6 dos 7 falham em todos os idiomas; `lost_access` passa nos dois, porque
  é o controle de RBAC.
- `fix_colab_terc.py` (FIX-COLAB-TERC-V1) continua com 40/40.
- Harnesses de caracterização (`outsourced-view-runtime.js`, `fix-colab-terc-runtime.js`) passam a carregar o módulo real.
  Nenhuma tabela esperada mudou, exceto `epi`, que passou a manter a tela.

## Rollback

Reverter o commit. Não há migração nem dado envolvido.
