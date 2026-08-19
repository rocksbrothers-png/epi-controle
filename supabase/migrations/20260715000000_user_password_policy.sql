-- Migration: política de senha temporária para usuários provisionados por admin.
--   • must_change_password: exige troca no primeiro acesso (0/1).
--   • password_expires_at: expiração da senha temporária (ISO-8601; vazio = sem expiração).
-- Idempotente (ADD COLUMN IF NOT EXISTS). Não afeta usuários existentes:
-- o default 0 mantém quem já usa o sistema fora da exigência.

ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_expires_at TEXT NOT NULL DEFAULT '';
