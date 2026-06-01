-- Phase 26: drop user_unit_links (substituída por purchase_role_unit_links).
-- Idempotente.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'user_unit_links'
  ) THEN
    DROP TABLE public.user_unit_links;
  END IF;
END $$;
