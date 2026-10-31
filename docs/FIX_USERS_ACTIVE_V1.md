# FIX-USERS-ACTIVE-V1 — editar usuário não reativa conta inativa

Base: Corporate `91b60160` / SaaS `decedc5`. Arquivos alterados idênticos nos dois projetos.

## 1. Defeito

Editar um usuário **inativo** pelo formulário (por exemplo, só o nome) e salvar **reativava a conta**.

Causa raiz, nas duas pontas:

| Onde | Código (main) | Efeito |
|---|---|---|
| `static/js/modules/users/business/user-form.js` | `values.active = Number(values.active \|\| 1)` | O formulário de usuário **não tem campo de status**; `active` vinha vazio e virava `1` em toda edição. |
| `modules/users/service.py` (`update_user`) | `int(payload.get('active', 1))` | Sem `active` no corpo, o servidor também gravava `1`. |

Defeito vizinho encontrado na reprodução (mesma tela, mesmo item "o formulário deve apresentar corretamente o
estado existente"):

- `populateLinkedEmployeeOptions` (`static/app.js`) recriava as opções do vínculo com `innerHTML` e apagava a
  seleção.
- Ao editar um Gestor de EPI ou um Administrador Local, o colaborador vinculado sumia do formulário.
- Salvar então falhava com "devem ser vinculados a um colaborador", a menos que o operador escolhesse o vínculo de
  novo.

## 2. Reprodução no fluxo real (antes)

O ambiente usou o SPA real e o `app.py` real, contra um **PostgreSQL local descartável** (cluster dedicado no
contêiner, porta 55432). Os dados eram fictícios e criados pela própria API: Empresa Teste A/B, `geral.a`,
`gestor.inativo.a`, `gestor.ativo.a` e `geral.b`.

Ação: Administrador Geral A edita só o nome de `gestor.inativo.a` e salva. Para conseguir salvar na `main`, foi
preciso escolher de novo o vínculo, que o formulário perdeu.

| | Banco antes | Corpo do PUT | Banco depois | Lista após recarregar |
|---|---|---|---|---|
| Usuário inativo | `active=0` (lista: Inativo) | `active: 1` | **`active=1`** | **Ativo** |
| Usuário ativo | `active=1` | `active: 1` | `active=1` | Ativo |

O formulário mostrou o vínculo vazio nos dois casos.

## 3. Correção

- **Frontend** (`user-form.js`): sem valor explícito, `active` **não vai** no corpo; valor explícito (`'0'`/`'1'`)
  continua indo como número.
  - O botão **Ativar/Desativar Usuário** (`userAccessUpdatePayload`) manda o status explícito.
  - **Promover/rebaixar** e **senha provisória** não mandam mais `active` (achado da auditoria independente).
    Antes enviavam o status da lista carregada; com a lista desatualizada, por exemplo depois de outro
    administrador desativar a conta, a ação reativava o usuário.
- **Backend** (`update_user`): `resolve_user_active` mantém o status atual quando `active` não vem (ou vem vazio).
  - Aceita só `0`/`1`; outro valor é recusado com "Status do usuário inválido." e nada é gravado.
  - O limite de usuários da empresa passa a usar o status resultante.
- **Auditoria**: quando o status **muda**, a troca é registrada na trilha da empresa (`company_audit_logs`, a mesma
  do histórico).
  - Ações `user_reactivate` / `user_deactivate`, com quem fez, o usuário e antes/depois.
  - Hoje nenhuma operação de usuário era auditada; esta é a única adição de comportamento e pode sair sem afetar a
    correção.
- **Formulário** (`populateLinkedEmployeeOptions`): ao refazer as opções, mantém o colaborador selecionado se ele
  continua entre as opções. Vínculo de outra empresa não é mantido.

**Não mudou:** RBAC (`users:update` e `authorize_user_management`), isolamento por empresa, criação de usuário (cria
ativo, como antes), regras de promoção, rotas e textos de interface.

## 4. Testes

| Teste | `main` | Com a correção |
|---|---|---|
| `tests_postgres/test_fix_users_active_v1_postgres.py` (13), PostgreSQL real via `update_user` com autorização: editar inativo (Adm. Geral e Registro) e ativo sem status; reativar/desativar explícitos com trilha; status inválido; perfil sem permissão (Gestor, Comprador); outra empresa (A→B, B→A); leitura em conexão nova; status explícito igual ao atual sem registro; ator e antes/depois na trilha; editar inativo com a empresa no limite | 5 falham | 13 passam |
| `tests/test_fix_users_active_v1.py` (26): regra de status, trilha, rótulos | não importa | 26 passam |
| `static/js/test/users-active-runtime.js` (6): corpo sem `active`, status explícito, botão Ativar/Desativar (promover não manda status), formulário sem campo de status (fragmento e `index.html`), senha provisória sem status, vínculo preservado | 4 falham | 6 passam |
| Caracterização `users-view-runtime.js`: os corpos de salvar com `active` vazio e de promover/rebaixar deixam de levar `active` (mudança deliberada, comentada) | — | 665 testes JS |
| `scripts/browser/fix_users_active_realflow.py`, Chromium **no fluxo real** (SPA + app.py + PostgreSQL local), 5 idiomas: cenários 1–6 da demanda, inclusive recarregar a página | pt-BR: falha ao salvar (vínculo perdido) | 5/5 idiomas, todos os cenários |

O harness real recusa `DATABASE_URL` e `--base` que não sejam `localhost`/`127.0.0.1`. Ele não roda no CI, porque precisa de
servidor e banco reais. O CI cobre o mesmo caminho pela suíte `tests_postgres`.

## 5. Riscos residuais

- **Criação inativa**: a criação ignora `active=0` (`int(payload.get('active', 1) or 1)`), comportamento anterior
  que ficou como está; o formulário não oferece isso.
- **Clientes antigos**: um cliente que mande `active` explícito continua mudando o status, como sempre, pelas mesmas
  regras de permissão.
- **Usuários sem empresa (Master)**: ativar/desativar não gera registro, porque a trilha é por empresa.
- **Status já alterados**: contas reativadas indevidamente antes desta correção continuam ativas. Identificá-las
  exigiria cruzar logs; nenhum dado foi alterado.
