-- Migration: ciclo de vida de Unidades — Arquivamento (Soft Delete) com retenção.
--
-- Política: a exclusão de uma unidade NUNCA é física. O DELETE da API arquiva
-- a unidade (status='archived'), preservando todo o histórico operacional,
-- documental e de auditoria (colaboradores, EPIs, entregas, estoque, compras,
-- requisições, avaliações, fichas e logs) pelo período de retenção configurado
-- por tenant (mínimo legal de 5 anos). A exclusão definitiva só ocorre após a
-- retenção, sem bloqueio jurídico, em duas etapas confirmadas por um
-- Administrador Geral/Master, e mantém a unidade como tombstone
-- (status='deleted') para não quebrar rastreabilidade nem FKs remanescentes.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.

-- Ciclo de vida: active | inactive | archived | pending_deletion | deleted
ALTER TABLE units ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE units ADD COLUMN IF NOT EXISTS archived_at TEXT;
ALTER TABLE units ADD COLUMN IF NOT EXISTS archived_by INTEGER;
ALTER TABLE units ADD COLUMN IF NOT EXISTS archive_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE units ADD COLUMN IF NOT EXISTS retention_until TEXT;
ALTER TABLE units ADD COLUMN IF NOT EXISTS legal_hold INTEGER NOT NULL DEFAULT 0;
ALTER TABLE units ADD COLUMN IF NOT EXISTS legal_hold_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE units ADD COLUMN IF NOT EXISTS deleted_at TEXT;
ALTER TABLE units ADD COLUMN IF NOT EXISTS deleted_by INTEGER;
ALTER TABLE units ADD COLUMN IF NOT EXISTS delete_reason TEXT NOT NULL DEFAULT '';

-- Retenção configurável por tenant (anos); o backend aplica o piso de 5.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS unit_retention_years INTEGER NOT NULL DEFAULT 5;

-- Consultas por status dentro do tenant (lista principal exclui arquivadas).
CREATE INDEX IF NOT EXISTS idx_units_status ON units (company_id, status);

-- Garantia adicional de integridade: nenhum status fora do ciclo de vida.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_units_lifecycle_status'
  ) THEN
    ALTER TABLE units ADD CONSTRAINT chk_units_lifecycle_status
      CHECK (status IN ('active', 'inactive', 'archived', 'pending_deletion', 'deleted'));
  END IF;
END $$;
