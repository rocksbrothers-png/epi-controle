# Auditoria F-04 — Exigência de JWT Bearer (rollout shadow → enforce)

**Data:** 2026-07-10
**Escopo:** autenticação do `actor_user_id` nas rotas autenticadas do backend.
**Status:** Fase **shadow** implementada. Enforce **não** ativado (aguarda estabilização).

---

## 1. Problema

`core/security.py::resolve_actor_user_id` resolve o usuário-ator a partir de três
fontes, aceitando a primeira disponível e apenas checando consistência entre elas:

1. `actor_user_id` no corpo (body) da requisição;
2. `actor_user_id` na query string;
3. claim `sub` de um JWT Bearer válido.

Como o JWT é **opcional**, um cliente pode se passar por qualquer usuário
enviando apenas `actor_user_id=<id>` — sem provar posse de credencial. O RBAC e o
escopo de empresa continuam sendo aplicados, porém **para o usuário personificado**
(ver §3), o que caracteriza personificação (impersonation), não escalonamento de
privilégio via body.

## 2. Solução (rollout seguro, sem quebra)

Flag `JWT_ENFORCEMENT_MODE` (`epi_backend/config.py`):

| Modo | Comportamento | Default |
|---|---|---|
| `off` | Legado silencioso (sem log, sem bloqueio). | fora de produção |
| `shadow` | Registra a requisição sem JWT (`structured_log`) e **permite**. | **produção** |
| `enforce` | Exige Bearer válido; sem token → `403`. | — |

Ponto único de controle: `resolve_actor_user_id`. Quando o ator é resolvido **sem
um token válido** (`token_actor` vazio), chama `_enforce_jwt_presence`, que loga o
evento `auth.actor_without_jwt` (campos: `mode`, `path`, `method`, `actor_user_id`,
`ip`) e, em `enforce`, levanta `PermissionError`.

A checagem de consistência body/query/token permanece **independente do modo**.
A compatibilidade antiga só é removida ao mudar para `enforce` via variável de
ambiente — nada é removido nesta fase.

## 3. RBAC / company_id / unit_id continuam íntegros

`core/repository.py::authorize_action` carrega o ator do **banco** por id
(`require_actor`) e aplica:

- **RBAC:** `ensure_permission(actor, action)` — usa o `role` do banco, nunca do
  body/token;
- **company_id:** `ensure_company_access(actor, company_id)` — usa o `company_id`
  do banco;
- **unit_id:** escopo operacional via `actor_operational_unit_id` derivado do ator
  do banco.

Ou seja, papel/empresa/unidade nunca vêm do cliente. O enforce fecha a lacuna de
**personificação** (provar que o `sub` do token corresponde ao ator), sem alterar
essas regras.

## 4. Clientes afetados

| Cliente | Envia JWT hoje? | Observação |
|---|---|---|
| **Web legado** (`static/js/modules/api-client.js`) | **Sim** | `buildApiHeaders` injeta `Authorization: Bearer <token>` quando `__EPI_APP_STATE__.token` existe (definido no login, persistido em `localStorage`). |
| **Flutter** (`flutter/apps/epi_admin/lib/core/api/api_client.dart`) | **Sim** | `_BearerInterceptor` injeta o Bearer e faz **refresh automático** em `401`. |
| **Site institucional** (`epi-controle-site`) | N/A | Só chama `/api/payments/*` (checkout público) — **não** usa `actor_user_id`. O `Bearer` do site é o token do Mercado Pago, não o nosso JWT. |

## 5. Endpoints públicos (não devem ser bloqueados por enforce)

Não passam por `resolve_actor_user_id` e permanecem anônimos:

- **Checkout / pagamentos públicos:** `GET /api/payments/config`, `/catalog`,
  `/status`, `POST /api/payments/pix`, `/boleto`, `/subscriptions`, `/webhook`
  (verificado: `actor-gated=0`).
- **Portal do colaborador:** ações (assinar ficha, solicitar/avaliar EPI) usam
  `employee_token` via `resolve_external_employee_context`, caminho separado do
  `resolve_actor_user_id`.
- **Login** (`POST /api/login`): actor-free — emite o token (verificado:
  `handle_post_login` não chama `resolve_actor`).
- **Bootstrap / me / refresh** (`GET /api/bootstrap`, `/api/auth/me`,
  `POST /api/auth/refresh`): exigem ator/token, porém são chamados **após** o
  login, já com o Bearer anexado pelo cliente — portanto não geram violação em
  enforce.

Os endpoints admin de pagamento (`/api/payments/plans`, gestão de assinatura) usam
`resolve_actor` e são acessados por administradores autenticados (web, com JWT).

## 6. Plano de rollout

1. **Shadow (agora):** produção roda `JWT_ENFORCEMENT_MODE=shadow` por default.
   Monitorar o evento `auth.actor_without_jwt` nos logs.
2. **Estabilização:** confirmar volume ~0 de `auth.actor_without_jwt` de clientes
   legítimos (web/Flutter). Qualquer origem residual → corrigir o cliente para
   anexar o Bearer antes de prosseguir.
3. **Enforce:** definir `JWT_ENFORCEMENT_MODE=enforce` em produção. Só então a
   compatibilidade antiga (ator via body/query sem token) deixa de ser aceita.
4. **Limpeza (futuro, fora deste PR):** após período estável em enforce, remover a
   aceitação de `actor_user_id` por body/query — **somente** após este relatório e
   testes completos, conforme diretriz.

## 7. Testes

- `tests/test_jwt_enforcement.py`: `off` permite silenciosamente; `shadow` permite
  e loga; `enforce` bloqueia sem JWT (body-only e query-only); JWT válido sempre
  aceito; mismatch body/token sempre bloqueia; ausência total de ator bloqueia.
- Suíte completa permanece verde com o default `off` em dev/test (sem ruído de log
  nem regressão): **1088 passed, 1 skipped**.

## 8. Como ativar em cada ambiente

```bash
# Produção (default já é shadow quando APP_ENV=prod|production)
JWT_ENFORCEMENT_MODE=shadow   # medir
JWT_ENFORCEMENT_MODE=enforce  # exigir (após estabilização)

# Forçar desligado (ex.: incidente)
JWT_ENFORCEMENT_MODE=off
```
