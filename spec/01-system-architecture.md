# Arquitetura do Sistema EPI SaaS

## Visão Geral

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTES                           │
│  Browser (JS Web)  │  Flutter Mobile  │  Flutter Web    │
└─────────┬──────────┴────────┬─────────┴────────┬────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              CAMADA DE APRESENTAÇÃO                     │
│  static/ (HTML/JS/CSS)  │  Flutter apps/epi_admin       │
└─────────────────────────┴───────────────────────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────────────┐
│              API HTTP (Python/Flask-like)                │
│  app.py — EpiHandler (SimpleHTTPRequestHandler)         │
│  Rotas: /api/* | /app/ | /health | /auth/* | /bootstrap │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌────────────────┐      ┌──────────────────────┐
│  Rule Engine   │      │   Business Modules   │
│ (rule_engine.  │      │  modules/auth/       │
│  py, 12K lines)│      │  modules/epis/       │
│  shadow/canary │      │  modules/stock/      │
│  /enforced     │      │  ...21 módulos       │
└────────────────┘      └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   core/ (infraestr.) │
                        │  database.py          │
                        │  auth.py / security.py│
                        │  permissions.py       │
                        │  roles.py             │
                        │  schema.py (DDL)      │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   PostgreSQL          │
                        │   (Supabase)          │
                        │   RLS por empresa     │
                        └──────────────────────┘
```

## Camadas

### 1. Infraestrutura (`core/`)

| Arquivo | Responsabilidade |
|---------|-----------------|
| `database.py` | Pool de conexões PostgreSQL, wrapper de execução de queries |
| `schema.py` | Definição DDL completa + migrações incrementais |
| `auth.py` | JWT encode/decode, middleware de autenticação |
| `security.py` | Hash de senhas (bcrypt), sanitização |
| `permissions.py` | Matriz de permissões por role |
| `roles.py` | Hierarquia de roles, normalização |
| `repository.py` | Padrão Repository para operações CRUD genéricas |
| `router.py` | Registro de rotas nos módulos |
| `rate_limit.py` | Rate limiting por IP/usuário |
| `pdf.py` | Geração de fichas PDF |

### 2. Backend (`epi_backend/`)

| Arquivo | Responsabilidade |
|---------|-----------------|
| `config.py` | Leitura de variáveis de ambiente, defaults |
| `db.py` | Wrappers de DB de alto nível |
| `bootstrap.py` | Bootstrap da aplicação (schema, dados iniciais) |
| `rule_engine.py` | Motor de regras de visibilidade multi-modo |
| `security.py` | JWT helpers, password recovery |
| `epi_scope.py` | Regras de escopo de visibilidade de EPIs |
| `manufacture_date_ocr.py` | OCR de datas via Tesseract/OpenCV |
| `purchase_workflow.py` | Fluxo de compras |
| `unit_jv_lifecycle.py` | Lifecycle de joint ventures |

### 3. Módulos de Negócio (`modules/`)

Cada módulo segue a estrutura:
```
modules/<domain>/
  routes.py   → Registro de rotas HTTP
  service.py  → Lógica de negócio
```

Módulos: `auth`, `users`, `companies`, `employees`, `units`, `epis`, `stock`, `deliveries`, `devolutions`, `ficha`, `purchases`, `commercial`, `alerts`, `reports`, `feedback`, `settings`, `tenant`, `portal`, `i18n`

### 4. Frontend Web Legado (`static/`)

SPA (Single Page Application) vanilla JavaScript carregada via `<script>` tags. Padrão IIFE com guards de duplo-carregamento via `globalThis.__EPI_*_LOADED__`.

### 5. Flutter (`flutter/`)

Monorepo gerenciado via Melos com 3 pacotes compartilhados:
- `epi_design` — Design System (Atomic: atoms/molecules/organisms)
- `epi_api` — Cliente HTTP (Dio + Retrofit)
- `epi_i18n` — Localizações ARB (5 idiomas)

App principal: `flutter/apps/epi_admin/`

## Padrões Arquiteturais

### Multi-tenancy
- Todas as queries são escopadas por `company_id`
- RLS (Row-Level Security) no PostgreSQL garante isolamento
- Supabase gerencia as políticas RLS

### RBAC (Role-Based Access Control)
- 8 roles em hierarquia: `master_admin > general_admin > registry_admin > admin > user/buyer/approver > employee`
- Permissões definidas por role em `core/permissions.py` (backend) e `static/js/core/permissions.js` (frontend)
- Middleware de autenticação valida JWT em cada request

### Feature Flags
- Sistema de flags para rollout progressivo de funcionalidades
- Modos: `off` → `shadow` → `canary` → `enforced`
- Granularidade: por ambiente, empresa, usuário, percentual de rollout
- Frontend: flags armazenadas em `localStorage` com query param override

### Rule Engine
- Localização: `epi_backend/rule_engine.py` (~12.500 linhas)
- Centraliza decisões de visibilidade e acesso
- Log de decisões em `rls_rule_engine_shadow_log` para auditoria
- Rollout controlado sem alteração de código

## Fluxo de Autenticação

```
1. POST /api/auth/login {email, password}
2. Backend valida credentials → gera JWT (exp: 8h)
3. Frontend armazena JWT em localStorage (STORAGE_KEYS.token)
4. Requests subsequentes: Authorization: Bearer <token>
5. Middleware decode_jwt_token() valida em cada request protegida
6. Flutter usa flutter_secure_storage para armazenamento seguro
```

## Decisões Arquiteturais (ADRs)

Ver `flutter/DECISIONS.md` para ADRs do Flutter. Decisões principais:
- **ADR-001**: BLoC/Cubit para state management (escalabilidade, testabilidade)
- **ADR-002**: GoRouter para navegação (deep linking, type-safe routes)
- **ADR-003**: Drift para persistência offline (type-safe, migrations)
- **ADR-004**: Retrofit + Dio para HTTP (code-gen, interceptors)
- **ADR-005**: Melos para monorepo (scripts unificados, workspace)
