# Autenticação e Autorização (RBAC) — EPI SaaS

## Modelo de Autenticação

### JWT (JSON Web Token)

- **Algoritmo**: HS256
- **Expiração**: 8 horas (`JWT_EXP_SECONDS = 28800`)
- **Armazenamento Web**: `localStorage` sob a chave `epi-session-v4-token`
- **Armazenamento Mobile**: `flutter_secure_storage` (iOS Keychain / Android Keystore)

**Payload do Token:**
```json
{
  "user_id": "uuid",
  "company_id": "uuid",
  "role": "admin",
  "unit_id": "uuid | null",
  "exp": 1234567890,
  "iat": 1234500000
}
```

### Sessão Web

Chaves de `localStorage`:

| Chave | Conteúdo |
|-------|----------|
| `epi-session-v4` | Dados da sessão (user, company, role) |
| `epi-session-v4-token` | JWT token bruto |
| `epi-session-v4-permissions` | Lista de permissões do role atual |
| `epi-session-v4-password-change-required` | Flag de troca obrigatória de senha |

## Hierarquia de Roles

```
master_admin          ← Plataforma SaaS (Rocks Brothers)
  └── general_admin   ← Empresa contratante (acesso total)
        └── registry_admin  ← Cadastros e operações
              └── admin     ← Administrador de unidade local
                    ├── user      ← Gestor de EPI
                    ├── buyer     ← Comprador
                    └── approver  ← Aprovador de compras
                          └── employee  ← Funcionário (portal)
```

## Permissões por Role

### master_admin
Todas as permissões abaixo + `companies:license`, `commercial:view`, `usage:view`

### general_admin
```
dashboard:view, users:*, units:*, employees:*, epis:*, deliveries:view+create,
fichas:view, reports:view, alerts:view, companies:view, stock:view+adjust,
settings:view+update, purchase_requests:*, purchase_orders:*, finance:view,
suppliers:manage, unit_links:manage, epi_feedback:*, epi_evaluation:*
```

### registry_admin
```
dashboard:view, users:view+create+update+delete, units:*, employees:*,
epis:*, deliveries:view, fichas:view, reports:view, alerts:view,
stock:view, settings:view+update, purchase_requests:view+create+update,
purchase_orders:view+receive, finance:view, epi_feedback:view+triage+manager_eval,
epi_evaluation:view+decide
```

### admin
```
dashboard:view, users:view, units:view, employees:view+update, epis:view,
deliveries:view+create, fichas:view, reports:view, alerts:view, stock:view+adjust,
purchase_requests:view+create+update, purchase_orders:view+review+receive,
finance:view, epi_feedback:view, epi_evaluation:view
```

### buyer
```
dashboard:view, epis:view, units:view, stock:view,
purchase_requests:view+update, purchase_orders:view+create+upload, finance:view
```

### approver
```
dashboard:view, epis:view, units:view, stock:view,
purchase_requests:view, purchase_orders:view+approve, finance:view
```

### user
```
dashboard:view, deliveries:view+create, fichas:view, alerts:view,
units:view, employees:view+update, epis:view, stock:view+adjust,
epi_feedback:view+manager_eval, epi_evaluation:view
```

### employee
Sem permissões de API diretas. Acessa apenas o Portal do Funcionário.

## Permissões por View (Frontend)

| View | Permissão Necessária |
|------|---------------------|
| dashboard | `dashboard:view` |
| empresas | `companies:view` |
| comercial | `commercial:view` |
| usuarios | `users:view` |
| unidades | `units:view` |
| colaboradores | `employees:view` |
| gestao-colaborador | `employees:update` |
| epis | `epis:view` |
| estoque | `stock:view` |
| entregas | `deliveries:view` |
| fichas | `fichas:view` |
| compras | `purchase_requests:view` |
| configuracao | `settings:view` |
| relatorios | `reports:view` |
| avaliacoes | `epi_evaluation:view` |

## Fluxo de Login

```
1. Usuário submete { email, password }
2. Backend:
   a. Busca usuário por email
   b. Verifica password_hash com bcrypt.verify()
   c. Verifica company.is_active
   d. Gera JWT com payload completo
   e. Atualiza last_login_at
3. Frontend armazena JWT em localStorage
4. Redireciona para /dashboard ou tela de troca de senha
```

## Fluxo de Recuperação de Senha

```
1. Usuário envia email → POST /api/auth/password-recovery
2. Backend gera token temporário (exp: 1h)
3. Email enviado com link /reset-password?token=<token>
4. Usuário define nova senha → POST /api/auth/password-reset
5. Token é invalidado após uso
```

## Troca Obrigatória de Senha

- Ativada via `password_change_required = true` na tabela `users`
- Frontend detecta via `epi-session-v4-password-change-required` em localStorage
- Redireciona para tela de troca antes de qualquer operação
- Backend bloqueia todas as rotas (exceto `/api/auth/change-password`) até troca

## Segurança da Autenticação

- **bcrypt** com fator de custo padrão para hashing de senhas
- **JWT Secret** obrigatório em produção (variável `JWT_SECRET`)
- **CORS** configurado via `CORS_ALLOW_ORIGIN`
- **Rate limiting** em endpoints de auth: 10 req/min por IP
- **CSP** (Content Security Policy) com `report-uri`
- **SRI** (Subresource Integrity) em assets externos

## Normalização de Roles

Aliases aceitos pelo backend para compatibilidade:

| Alias | Role Normalizado |
|-------|-----------------|
| masteradmin | master_admin |
| generaladmin | general_admin |
| registryadmin | registry_admin |
| comprador | buyer |
| aprovador | approver |

## Escopo de Visibilidade (RLS)

Regras de escopo além do role:

- `master_admin`: vê todas as empresas
- `general_admin`, `registry_admin`: veem todos os dados da empresa
- `admin`, `user`: escopo limitado à(s) sua(s) unidade(s)
- `buyer`, `approver`: escopo limitado às compras da empresa
- `employee`: apenas próprios dados no portal
