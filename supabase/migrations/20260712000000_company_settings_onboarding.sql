-- Migration: Minha Empresa (configuração pelo Administrador Geral) + onboarding
-- Novos dados cadastrais/preferências da empresa contratante e o flag do
-- assistente de primeiro acesso. Todas as colunas são idempotentes.
--
-- onboarding_completed usa DEFAULT 1: empresas já cadastradas não devem ver o
-- assistente de implantação; novas tenants são criadas explicitamente com 0.

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS state_registration      TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS municipal_registration  TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS address                 TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS whatsapp                TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS display_name            TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS timezone                TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
  ADD COLUMN IF NOT EXISTS onboarding_completed    INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS onboarding_completed_at TEXT NOT NULL DEFAULT '';
