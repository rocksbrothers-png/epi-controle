-- Migration: política de arquivamento configurável por entidade e por tenant.
--
-- Configurações → Regras → Arquivamento: o cliente define a retenção (anos)
-- de Unidades, EPIs e Colaboradores conforme a política interna da empresa,
-- respeitando o piso legal de 5 anos aplicado pelo backend.
--
-- A retenção da Ficha de EPI (5 anos, NR-6) tem regra própria e permanece
-- inalterada — não usa estes parâmetros.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS.

ALTER TABLE companies ADD COLUMN IF NOT EXISTS epi_retention_years INTEGER NOT NULL DEFAULT 5;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS employee_retention_years INTEGER NOT NULL DEFAULT 5;
