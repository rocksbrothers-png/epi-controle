# Database Schema — EPI SaaS

## Tecnologia

- **SGBD**: PostgreSQL 15+ (hospedado no Supabase)
- **Segurança**: Row-Level Security (RLS) habilitado em todas as tabelas de negócio
- **Migrações**: Gerenciadas via `core/schema.py` (DDL) + `epi_backend/migrations/` (scripts)
- **Supabase**: `supabase/migrations/` para políticas RLS

## Convenções

- PKs: `UUID` gerado com `gen_random_uuid()`
- Timestamps: `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ`
- Soft delete: coluna `deleted_at TIMESTAMPTZ` (quando aplicável)
- Audit trail: `created_by UUID REFERENCES users(id)`, `updated_by UUID REFERENCES users(id)`
- Multi-tenant: coluna `company_id UUID` em todas as tabelas de negócio

## Tabelas Principais

### `companies`
```sql
CREATE TABLE companies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  legal_name      TEXT,
  cnpj            TEXT,
  logo_url        TEXT,
  logo_type       TEXT,        -- 'url' | 'svg' | 'base64'
  login_logo_type TEXT,
  display_name    TEXT,
  whitelabel      JSONB,       -- configurações white-label
  plan            TEXT,        -- 'individual' | 'start' | 'business' | 'corporate' | 'enterprise'
  max_users       INTEGER,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ
);
```

### `users`
```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  email           TEXT NOT NULL,
  password_hash   TEXT NOT NULL,
  role            TEXT NOT NULL,  -- ver enum de roles
  unit_id         UUID REFERENCES units(id),
  is_active       BOOLEAN DEFAULT true,
  password_change_required BOOLEAN DEFAULT false,
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ,
  UNIQUE (email)
);
```

### `units`
```sql
CREATE TABLE units (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  code            TEXT,
  parent_id       UUID REFERENCES units(id),  -- hierarquia
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ,
  created_by      UUID REFERENCES users(id)
);
```

### `employees`
```sql
CREATE TABLE employees (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  unit_id         UUID REFERENCES units(id),
  name            TEXT NOT NULL,
  cpf             TEXT,
  registration    TEXT,
  job_title       TEXT,
  department      TEXT,
  admission_date  DATE,
  is_active       BOOLEAN DEFAULT true,
  photo_url       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ,
  created_by      UUID REFERENCES users(id),
  updated_by      UUID REFERENCES users(id)
);
```

### `epis`
```sql
CREATE TABLE epis (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  description     TEXT,
  ca_number       TEXT,        -- Certificado de Aprovação
  ca_expires_at   DATE,
  category        TEXT,
  unit_of_measure TEXT DEFAULT 'unidade',
  is_active       BOOLEAN DEFAULT true,
  image_url       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ,
  created_by      UUID REFERENCES users(id)
);
```

### `stock`
```sql
CREATE TABLE stock (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  unit_id         UUID NOT NULL REFERENCES units(id),
  epi_id          UUID NOT NULL REFERENCES epis(id),
  quantity        INTEGER NOT NULL DEFAULT 0,
  min_quantity    INTEGER DEFAULT 0,    -- para alertas de estoque baixo
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (unit_id, epi_id)
);
```

### `stock_movements`
```sql
CREATE TABLE stock_movements (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  unit_id         UUID NOT NULL REFERENCES units(id),
  epi_id          UUID NOT NULL REFERENCES epis(id),
  type            TEXT NOT NULL,   -- 'in' | 'out' | 'adjust' | 'transfer'
  quantity        INTEGER NOT NULL,
  reference       TEXT,            -- nota fiscal, pedido, etc.
  manufacture_date DATE,           -- data de fabricação (OCR)
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  created_by      UUID REFERENCES users(id)
);
```

### `deliveries`
```sql
CREATE TABLE deliveries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  unit_id         UUID NOT NULL REFERENCES units(id),
  employee_id     UUID NOT NULL REFERENCES employees(id),
  delivered_by    UUID NOT NULL REFERENCES users(id),
  delivered_at    TIMESTAMPTZ DEFAULT NOW(),
  signature       TEXT,           -- base64 da assinatura digital
  qr_code         TEXT,           -- token único para QR code
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `delivery_items`
```sql
CREATE TABLE delivery_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id     UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
  epi_id          UUID NOT NULL REFERENCES epis(id),
  quantity        INTEGER NOT NULL DEFAULT 1,
  manufacture_date DATE,
  serial_number   TEXT,
  lot_number      TEXT
);
```

### `devolutions`
```sql
CREATE TABLE devolutions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  unit_id         UUID NOT NULL REFERENCES units(id),
  employee_id     UUID NOT NULL REFERENCES employees(id),
  delivery_id     UUID REFERENCES deliveries(id),
  epi_id          UUID NOT NULL REFERENCES epis(id),
  quantity        INTEGER NOT NULL DEFAULT 1,
  reason          TEXT,           -- 'worn' | 'damaged' | 'exchange' | 'termination'
  condition       TEXT,           -- 'good' | 'worn' | 'damaged' | 'lost'
  returned_at     TIMESTAMPTZ DEFAULT NOW(),
  returned_by     UUID REFERENCES users(id)
);
```

### `purchase_requests`
```sql
CREATE TABLE purchase_requests (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  unit_id         UUID REFERENCES units(id),
  epi_id          UUID NOT NULL REFERENCES epis(id),
  quantity        INTEGER NOT NULL,
  status          TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected' | 'ordered'
  notes           TEXT,
  requested_by    UUID NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ
);
```

### `purchase_orders`
```sql
CREATE TABLE purchase_orders (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  supplier_name   TEXT,
  total_value     NUMERIC(12,2),
  status          TEXT DEFAULT 'draft',   -- 'draft' | 'sent' | 'approved' | 'received' | 'cancelled'
  invoice_file    TEXT,
  invoice_number  TEXT,
  ordered_at      TIMESTAMPTZ,
  received_at     TIMESTAMPTZ,
  created_by      UUID NOT NULL REFERENCES users(id),
  approved_by     UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ
);
```

### `alerts`
```sql
CREATE TABLE alerts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  unit_id         UUID REFERENCES units(id),
  type            TEXT NOT NULL,  -- 'low_stock' | 'ca_expiring' | 'ca_expired' | 'overdue_return'
  epi_id          UUID REFERENCES epis(id),
  severity        TEXT DEFAULT 'warning',  -- 'info' | 'warning' | 'critical'
  message         TEXT,
  is_dismissed    BOOLEAN DEFAULT false,
  dismissed_by    UUID REFERENCES users(id),
  dismissed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `epi_feedback`
```sql
CREATE TABLE epi_feedback (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID NOT NULL REFERENCES companies(id),
  employee_id     UUID NOT NULL REFERENCES employees(id),
  epi_id          UUID NOT NULL REFERENCES epis(id),
  delivery_id     UUID REFERENCES deliveries(id),
  rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
  comment         TEXT,
  status          TEXT DEFAULT 'pending',   -- 'pending' | 'triaged' | 'evaluated' | 'closed'
  triage_notes    TEXT,
  manager_notes   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ
);
```

### `rls_rule_engine_shadow_log`
```sql
CREATE TABLE rls_rule_engine_shadow_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      TEXT,
  user_id         UUID,
  company_id      UUID,
  rule_id         TEXT,
  mode            TEXT,   -- 'shadow' | 'canary' | 'enforced'
  input           JSONB,
  decision        JSONB,
  duration_ms     INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

## Índices Principais

```sql
-- Performance de queries multi-tenant
CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_employees_company_unit ON employees(company_id, unit_id);
CREATE INDEX idx_epis_company ON epis(company_id);
CREATE INDEX idx_stock_unit_epi ON stock(unit_id, epi_id);
CREATE INDEX idx_deliveries_employee ON deliveries(employee_id);
CREATE INDEX idx_alerts_company_dismissed ON alerts(company_id, is_dismissed);
CREATE INDEX idx_movements_company_epi ON stock_movements(company_id, epi_id, created_at DESC);
```

## RLS Policies (Supabase)

Padrão aplicado a todas as tabelas de negócio:

```sql
-- Usuários só veem dados da sua empresa
CREATE POLICY "company_isolation" ON <table>
  FOR ALL USING (company_id = (current_setting('app.company_id'))::UUID);

-- master_admin vê tudo
CREATE POLICY "master_admin_bypass" ON <table>
  FOR ALL USING (
    current_setting('app.role') = 'master_admin'
  );
```

## Migrações

Numeração sequencial em `epi_backend/migrations/`:
```
001_unit_jv_periods.py
002_enable_rls_phase1.py
003_enable_rls_phase2.py
004_enable_rls_phase3.py
005_rls_rule_engine_shadow_log.py
006_drop_user_unit_links.py
007_drop_epi_ficha_periods_legacy.py
008_companies_whitelabel.py
```

Supabase em `supabase/migrations/` (formato timestamp):
```
20260501000000_rls_hardening_phase1.sql
20260530000000_rls_hardening_phase4.sql
20260604000000_companies_whitelabel.sql
```
