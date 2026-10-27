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
| **B — Já preservavam a tela** | `archiveEntityRecord`/`restoreArchivedRecord`/`purgeArchivedRecord` (Colaboradores/Terceirizados, via `ARCHIVAL_ENTITIES.preserveView`), `saveSimpleForm` (3 formulários), `toggleEmployeeUnitLink` | Arquivar/desarquivar/excluir ganham o fluxo novo (mensagem, clique único, recarga sem duplicata). `saveSimpleForm` e `toggleEmployeeUnitLink` **não mudaram**. |
| **C — Corrigidas nesta demanda** | `saveEmployeeMovement` (transferência), arquivar/desarquivar/excluir **EPI** (`ARCHIVAL_ENTITIES.epi.preserveView`), `archiveUnit`/`restoreArchivedUnit`/`purgeArchivedUnit` | `preserveView: true` + fluxo gravar → atualizar (abaixo). |
| **D — Mesma classe, fora do escopo autorizado** (registradas para decisão) | Comercial (`toggleCommercialStatus`, `saveCommercial`, `saveCommercialSettings`), Empresas (`openCompanyLogoEditor`, `saveCompany`, `toggleCompany`), Usuários (`copyUserAccessMessage`, `setTemporaryPassword`, `generateAndCopyTemporaryPassword`, `saveUser`, `users-view.js` ×2), `deactivateLegalEntity`, `finalizeFichaPeriod` ×2, `handleStockMovementSubmit`, `saveMyCompany`, `views/devolution.js`, botões "Atualizar" da Fase 2 (`refreshPhase2Module`, `refreshPhase2EpisModule`, `INTERACTIVE_TOOLS_MODULES.colaboradores.refresh`), `saveSimpleForm` nos demais formulários (Unidade, CNPJ, EPI, Entrega) | **Inalteradas.** Ao contrário do grupo C, muitas delas acontecem com a tela de origem em modo SPA ou em fluxos com navegação própria. Cada uma precisa de cenário próprio antes de mudar. |
| **Código morto** | `deleteRegistryEntity` (sem chamadores) | Inalterado; vai para a limpeza da UBX-V5. |

## Correção

**`static/js/modules/shared/ui/mutation-flow.js`** é um módulo UBX novo (`shared/ui`), carregado antes do `app.js`. Nenhuma
declaração nova foi criada no monólito: a guarda continua em 798 declarações e 112 endpoints. O `modules/api-client.js`
expõe `apiWriteEpoch()`, usado só por `coalesceLoad`.

- **`runExclusiveMutation(key, task)`**: uma execução por chave (`archive:epi:61`, `employee-movement`…). Clique duplo,
  ou repetição antes do diálogo abrir, não reenvia a gravação. A chave é liberada depois de sucesso **e** de erro.
- **`refreshAfterMutation(refresh)`**: roda a recarga depois da gravação já concluída. Se ela falhar, mostra o aviso
  verdadeiro `mutation.refreshFailed` ("A operação foi registrada, mas não foi possível atualizar a tela…") e não trata a
  gravação como falha. Com 401/403 não há aviso extra, porque `loadBootstrap` já encerra a sessão.
- **`coalesceLoad(key, load)`**: durante a recarga, a mesma lista pedida pela tela reaberta (`showView`) e pela própria
  operação gera **uma** requisição. Fora dessa janela não há efeito. Dentro dela, só junta leituras da mesma **época de
  escrita** do `api-client`: a época avança no início e no fim de toda requisição que não é GET. Assim, se outra gravação
  de qualquer fluxo começar ou terminar depois da leitura em andamento, uma leitura nova é feita, e a lista não volta
  anterior a uma gravação. Isso vale para `loadArchivedRecords`, `loadArchivedUnits` e `loadOutsourcedCompanies`.
  Os 4 `fetch` crus aceitos pela catraca (`procurement.js`, `safety-library.js`, `i18n.js`, `tenant-init.js`) não tocam
  essas listas.

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

- **`static/js/test/fix-nav-refresh-runtime.js`**: 45 casos sobre as funções **reais** do `app.js` (fatiadas) e o módulo
  real. Cobre tela mantida, uma requisição de lista, gravação ok com recarga falha, gravação recusada e clique duplo, para
  8 operações, mais a transferência, a chave liberada após cancelar o diálogo e o próprio módulo (inclusive leitura
  nova quando outra gravação acontece na janela). Contra o `app.js` da `main`, **23 deles falham**; outros 3 falham em
  `fix-colab-terc-runtime.js`, porque o EPI passou a manter a tela.
- **`scripts/browser/fix_nav_refresh.py`** (Chromium, 5 idiomas, roda no workflow *Colaboradores and outsourced browser
  regression*): `transfer`, `epi_archival`, `unit_archival`, `lost_access`, `redundant_reloads`, `truthful_message` e
  `double_click`, com **35/35**. Contra a `main`, 6 dos 7 falham em todos os idiomas; `lost_access` passa nos dois, porque
  é o controle de RBAC.
- `fix_colab_terc.py` (FIX-COLAB-TERC-V1) continua com 40/40.
- Harnesses de caracterização (`outsourced-view-runtime.js`, `fix-colab-terc-runtime.js`) passam a carregar o módulo real.
  Nenhuma tabela esperada mudou, exceto `epi`, que passou a manter a tela.

## Rollback

Reverter o commit. Não há migração nem dado envolvido.
