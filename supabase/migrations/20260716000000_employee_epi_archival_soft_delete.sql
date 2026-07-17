-- Migration: ciclo de vida de arquivamento (soft delete) para Colaboradores e EPIs.
--
-- Mesma política já aplicada às Unidades (20260714000000): a exclusão vira
-- arquivamento (registro desativado, histórico 100% preservado); desarquivar
-- reativa; a exclusão definitiva só é habilitada após o período de retenção
-- do tenant (mínimo 5 anos), em duas etapas, mantendo o registro como
-- tombstone (status='deleted') e a trilha permanente em company_audit_logs.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.

-- Colaboradores
ALTER TABLE employees ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS archived_at TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS archived_by INTEGER;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS archive_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS retention_until TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS legal_hold INTEGER NOT NULL DEFAULT 0;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS legal_hold_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS deleted_at TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS deleted_by INTEGER;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS delete_reason TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees (company_id, status);

-- EPIs
ALTER TABLE epis ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE epis ADD COLUMN IF NOT EXISTS archived_at TEXT;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS archived_by INTEGER;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS archive_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE epis ADD COLUMN IF NOT EXISTS retention_until TEXT;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS legal_hold INTEGER NOT NULL DEFAULT 0;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS legal_hold_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE epis ADD COLUMN IF NOT EXISTS deleted_at TEXT;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS deleted_by INTEGER;
ALTER TABLE epis ADD COLUMN IF NOT EXISTS delete_reason TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_epis_status ON epis (company_id, status);

-- Integridade do ciclo de vida
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_employees_lifecycle_status') THEN
    ALTER TABLE employees ADD CONSTRAINT chk_employees_lifecycle_status
      CHECK (status IN ('active', 'inactive', 'archived', 'pending_deletion', 'deleted'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_epis_lifecycle_status') THEN
    ALTER TABLE epis ADD CONSTRAINT chk_epis_lifecycle_status
      CHECK (status IN ('active', 'inactive', 'archived', 'pending_deletion', 'deleted'));
  END IF;
END $$;
