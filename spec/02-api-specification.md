# API Specification — EPI SaaS

## Base URL

```
https://<host>/api
```

## Autenticação

Todos os endpoints (exceto `/api/auth/login` e `/health`) requerem:
```
Authorization: Bearer <jwt_token>
```

JWT payload:
```json
{
  "user_id": "uuid",
  "company_id": "uuid",
  "role": "general_admin",
  "exp": 1234567890
}
```

## Endpoints por Módulo

### Auth

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| POST | `/api/auth/login` | Público | Login com email/senha |
| POST | `/api/auth/logout` | Autenticado | Invalidar sessão |
| POST | `/api/auth/password-recovery` | Público | Solicitar reset de senha |
| POST | `/api/auth/password-reset` | Token temporário | Definir nova senha |
| GET | `/api/auth/me` | Autenticado | Dados do usuário logado |

**POST /api/auth/login**
```json
// Request
{ "email": "user@empresa.com", "password": "secret" }

// Response 200
{
  "token": "eyJ...",
  "user": {
    "id": "uuid",
    "name": "João Silva",
    "email": "user@empresa.com",
    "role": "admin",
    "company_id": "uuid",
    "company_name": "Empresa ABC"
  }
}
```

### Usuários

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/users` | `users:view` | Listar usuários da empresa |
| POST | `/api/users` | `users:create` | Criar usuário |
| GET | `/api/users/:id` | `users:view` | Detalhe do usuário |
| PATCH | `/api/users/:id` | `users:update` | Atualizar usuário |
| DELETE | `/api/users/:id` | `users:delete` | Remover usuário |

### Empresas

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/companies` | `companies:view` | Listar empresas (master_admin) |
| POST | `/api/companies` | `companies:create` | Criar empresa |
| GET | `/api/companies/:id` | `companies:view` | Detalhe da empresa |
| PATCH | `/api/companies/:id` | `companies:update` | Atualizar empresa |
| GET | `/api/companies/:id/settings` | `settings:view` | Configurações da empresa |
| PATCH | `/api/companies/:id/settings` | `settings:update` | Atualizar configurações |

### Unidades

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/units` | `units:view` | Listar unidades |
| POST | `/api/units` | `units:create` | Criar unidade |
| GET | `/api/units/:id` | `units:view` | Detalhe da unidade |
| PATCH | `/api/units/:id` | `units:update` | Atualizar unidade |
| DELETE | `/api/units/:id` | `units:delete` | Remover unidade |

### Colaboradores (Employees)

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/employees` | `employees:view` | Listar colaboradores |
| POST | `/api/employees` | `employees:create` | Criar colaborador |
| GET | `/api/employees/:id` | `employees:view` | Detalhe do colaborador |
| PATCH | `/api/employees/:id` | `employees:update` | Atualizar colaborador |
| DELETE | `/api/employees/:id` | `employees:delete` | Remover colaborador |
| GET | `/api/employees/:id/ficha` | `fichas:view` | Ficha de EPI do colaborador |

### EPIs

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/epis` | `epis:view` | Listar EPIs do catálogo |
| POST | `/api/epis` | `epis:create` | Criar EPI |
| GET | `/api/epis/:id` | `epis:view` | Detalhe do EPI |
| PATCH | `/api/epis/:id` | `epis:update` | Atualizar EPI |
| DELETE | `/api/epis/:id` | `epis:delete` | Remover EPI |

### Estoque

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/stock` | `stock:view` | Posição de estoque |
| POST | `/api/stock/adjust` | `stock:adjust` | Ajuste de estoque |
| GET | `/api/stock/movements` | `stock:view` | Histórico de movimentações |

### Entregas

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/deliveries` | `deliveries:view` | Listar entregas |
| POST | `/api/deliveries` | `deliveries:create` | Registrar entrega |
| GET | `/api/deliveries/:id` | `deliveries:view` | Detalhe da entrega |
| GET | `/api/deliveries/:id/pdf` | `deliveries:view` | PDF do comprovante |

### Devoluções

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/devolutions` | `deliveries:view` | Listar devoluções |
| POST | `/api/devolutions` | `deliveries:create` | Registrar devolução |

### Compras

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/purchase-requests` | `purchase_requests:view` | Listar solicitações |
| POST | `/api/purchase-requests` | `purchase_requests:create` | Criar solicitação |
| PATCH | `/api/purchase-requests/:id` | `purchase_requests:update` | Atualizar solicitação |
| GET | `/api/purchase-orders` | `purchase_orders:view` | Listar pedidos de compra |
| POST | `/api/purchase-orders` | `purchase_orders:create` | Criar pedido |
| PATCH | `/api/purchase-orders/:id/approve` | `purchase_orders:approve` | Aprovar pedido |
| PATCH | `/api/purchase-orders/:id/receive` | `purchase_orders:receive` | Registrar recebimento |

### Alertas

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/alerts` | `alerts:view` | Listar alertas ativos |
| PATCH | `/api/alerts/:id/dismiss` | `alerts:view` | Dispensar alerta |

### Relatórios

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/api/reports/stock-by-unit` | `reports:view` | Relatório de estoque por unidade |
| GET | `/api/reports/delivery-by-employee` | `reports:view` | Entregas por colaborador |
| GET | `/api/reports/movement` | `reports:view` | Movimentações |
| GET | `/api/reports/epi-ficha` | `reports:view` | Fichas de EPI |
| GET | `/api/reports/alerts` | `reports:view` | Relatório de alertas |

### Bootstrap / Sistema

| Método | Path | Permissão | Descrição |
|--------|------|-----------|-----------|
| GET | `/health` | Público | Health check |
| GET | `/ready` | Público | Readiness check |
| GET | `/bootstrap` | Público | Status do schema |
| GET | `/api/bootstrap` | master_admin | Bootstrap forçado |

## Padrão de Response

```json
// Sucesso com lista
{
  "data": [...],
  "total": 100,
  "page": 1,
  "per_page": 20
}

// Sucesso com objeto
{
  "data": { ... }
}

// Erro
{
  "error": "Mensagem de erro",
  "code": "ERROR_CODE"
}
```

## Códigos de Erro

| Código HTTP | Significado |
|-------------|------------|
| 400 | Dados inválidos / validação falhou |
| 401 | Não autenticado (token ausente ou inválido) |
| 403 | Sem permissão para este recurso |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: email duplicado) |
| 422 | Entidade não processável |
| 429 | Rate limit excedido |
| 500 | Erro interno do servidor |

## Filtros e Paginação

Query params padrão:
- `page` — Número da página (padrão: 1)
- `per_page` — Itens por página (padrão: 20, máx: 100)
- `unit_id` — Filtrar por unidade
- `search` — Busca textual
- `status` — Filtrar por status
- `from_date` / `to_date` — Intervalo de datas

## Rate Limiting

- Padrão: 100 req/min por IP
- Endpoints de auth: 10 req/min por IP
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
