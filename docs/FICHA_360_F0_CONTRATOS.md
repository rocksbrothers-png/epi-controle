# Ficha 360° de EPI — F0: contratos e limites arquiteturais

Fatia **F0 (fundação)** da Ficha 360° de EPI por Colaborador. Entrega só a infraestrutura que as fatias
F1–F6 vão usar, **sem interface funcional, sem rota HTTP e sem mudança de comportamento** para o usuário.
Índice operacional da arquitetura: [`UBX_MIGRATION_PLAN.md`](UBX_MIGRATION_PLAN.md).

## 1. Onde vive cada responsabilidade

| Camada | Arquivo | Namespace / símbolo | Responsabilidade |
|---|---|---|---|
| Backend (contrato) | `modules/employee_ppe_360/contract.py` | `resolve_authorized_employee`, `parse_page_params`, `encode_cursor`/`decode_cursor`, `success_envelope`/`error_envelope`, `ContractError` | Autorização e escopo por colaborador, paginação no servidor e envelope de resposta. **Somente leitura**, sem rota |
| Frontend business | `static/js/modules/employee-ppe-360/business/employee-ppe-360-contract.js` | `__EPI_EMPLOYEE_PPE_360_BUSINESS__` | Regras puras: chave de contexto, validação do envelope, paginação pedida, estados de seção |
| Frontend UI (orquestração) | `static/js/modules/employee-ppe-360/ui/employee-ppe-360-lifecycle.js` | `__EPI_EMPLOYEE_PPE_360_LIFECYCLE__` | Montagem, atualização, desmontagem, troca de colaborador e invalidação por contexto |
| Frontend integrations | `static/js/modules/employee-ppe-360/integrations/` (a partir da F1) | `__EPI_EMPLOYEE_PPE_360_API__` | Único lugar com HTTP da Ficha, pelo cliente único `globalThis.api` |

A F0 **não** carrega os scripts em `static/views/_scripts.html`: não há tela que os use. A F1 acrescenta as
tags (antes de `/app.js`) junto com o botão no módulo Colaboradores. O `static/app.js` não muda (guarda §4).

## 2. Contrato de backend (todas as seções F1–F6)

1. **Autorização reaproveitada.** Exige `employees:view` (permissão existente) e o escopo de leitura oficial,
   `ensure_actor_employee_visibility_scope`: tenant primeiro, depois unidade operacional ou vínculo local ativo.
   Nenhuma permissão nova na F0. Seções futuras somam as próprias permissões (por exemplo, `deliveries:view`;
   custos: `finance:view`) **além** desta base.
2. **Conhecer o id não basta.** Colaborador inexistente, de outra empresa ou fora do escopo recebem a mesma
   resposta 404, sem revelar se existe.
3. **Paginação no servidor.** `limit` de 1 a 100 (padrão 20); `cursor` opaco (base64url de `{s: data, i: id}`)
   para ordenação estável `(data, id)` decrescente. Valor inválido é recusado, nunca "corrigido".
4. **Envelope único:**
   - sucesso: `{"ok": true, "data": …, "page": {"limit": 20, "next_cursor": "…" | null}}` (`page` só em listas);
   - erro: `{"ok": false, "error": {"code": "…", "message": "…"}}`, com mensagem genérica. O cliente traduz
     pelo `code`.

| Código | HTTP | Quando |
|---|---|---|
| `INVALID_EMPLOYEE_ID` | 400 | id não é inteiro positivo |
| `INVALID_PAGINATION` | 400 | `limit` fora de 1..100, repetido ou não numérico; cursor inválido |
| `FORBIDDEN` | 403 | perfil sem `employees:view` (verificado **antes** de qualquer leitura) |
| `EMPLOYEE_NOT_FOUND` | 404 | inexistente, outra empresa ou fora do escopo |

Rotas previstas a partir da F1 (não existem na F0): `GET /api/employees/{id}/ppe-360/<seção>`.

## 3. Contrato de ciclo de vida (frontend)

```js
const life = globalThis.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__;
life.mountEmployeePpe360({ employeeId, container, sections, render, hostView, onUnmount });
life.refreshEmployeePpe360();
life.unmountEmployeePpe360(reason);
// sections: { nome: ({ employeeId, page }) => Promise<envelope> }  — loaders vindos de integrations/
// render({ section, state, result, employeeId })                    — estados: idle, loading, ready, empty, error, forbidden
```

| Evento | Efeito |
|---|---|
| Montar outra Ficha (fachada) | desmonta a anterior: uma Ficha ativa por vez, sem listener duplicado |
| Troca de colaborador | nova geração; resposta do colaborador anterior é descartada |
| Logout (`clearSession` zera `state.user`) | a próxima resposta ou refresh detecta a ausência de contexto e desmonta, limpando o contêiner. `terminateSession` ainda recarrega a página |
| Troca de usuário, perfil, empresa ou unidade (mesma aba) | a chave de contexto muda → respostas em voo descartadas e Ficha desmontada |
| Logout/login em outra aba (`storage` com chave de sessão) | desmonta |
| Navegação para outra tela (`epi:viewchange`) ou `pagehide` | desmonta |
| Desmontagem | aborta o `AbortController` (todos os listeners saem juntos), limpa contêiner e estado em memória |

O contexto vem do estado oficial da sessão (`__EPI_APP_STATE__.user`: id, perfil, empresa, unidade
operacional). Nenhum token ou permissão é copiado para dentro da Ficha, e nada vai para storage.

## 4. Guardas automatizadas

| Guarda | Arquivo | Executada por |
|---|---|---|
| UBX geral: `app.js` não cresce, camadas, ciclos, 500 linhas, catracas de endpoint/fetch | `static/js/test/app-js-boundary.js` (existente) | CI `frontend-tests`, `tests/test_app_js_ubx_boundary.py` |
| Domínio da Ficha: `app.js` sem referência à Ficha; UI sem HTTP; sem cálculo financeiro; só namespaces próprios e sem storage; listeners com `AbortSignal`; sem acoplamento com Compras (nos dois sentidos); todo arquivo em `business/`, `integrations/` ou `ui/` | `static/js/test/employee-ppe-360-boundary.js` | harness `run-tests.js` (CI `frontend-tests`) e `tests/test_employee_ppe_360_boundary.py` (com sabotagens) |
| Contrato de backend, isolamento, somente leitura, sem rota prematura, sem dependência de Compras | `tests/test_employee_ppe_360_f0_contract.py` | CI `test` (pytest) |
| Ciclo de vida e isolamento de estado | `static/js/test/employee-ppe-360-lifecycle-runtime.js` | harness `run-tests.js` |

## 5. Como a F1 começa sem reestruturar a F0

1. Criar `integrations/employee-ppe-360-api.js` (HTTP pelo cliente único) e `modules/employee_ppe_360/routes.py`
   usando `resolve_authorized_employee`, `parse_page_params` e os envelopes; registrar no `app.py`.
2. Acrescentar as tags dos scripts em `static/views/_scripts.html` antes de `/app.js`.
3. Adicionar a ação "Ficha 360°" na linha do colaborador em `modules/employees/ui/employees-view.js`, chamando
   `mountEmployeePpe360`.
4. Atualizar `tests/test_employee_ppe_360_f0_contract.py::test_f0_nao_expoe_rota`, que existe para travar a
   exposição de rota **até** a F1.

## 6. Decisões que permanecem abertas (não resolvidas pela F0)

- ~~Acesso de `master_admin` à Ficha (D-10)~~ — **decidido na F1 (DF-3):** bloqueado no contrato
  (`BLOCKED_ROLES`), antes de qualquer leitura. Ver [`FICHA_360_F1_IDENTIFICACAO.md`](FICHA_360_F1_IDENTIFICACAO.md).
- A F1 abriu a primeira rota e a única escrita do pacote (auditoria de abertura, DF-7); as guardas desta
  F0 foram atualizadas para fixar exatamente isso.
- Classificação de região corporal (mapa), rateio por utilização e demais decisões da especificação consolidada.
