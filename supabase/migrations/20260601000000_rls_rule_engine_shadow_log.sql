-- RLS: rule_engine_shadow_log
-- Tabela interna do shadow mode; sem acesso direto via PostgREST.
-- Idempotente. Backend Python (role postgres) nao afetado.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'rule_engine_shadow_log'
  ) THEN
    RETURN;
  END IF;

  ALTER TABLE public.rule_engine_shadow_log ENABLE ROW LEVEL SECURITY;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename  = 'rule_engine_shadow_log'
      AND policyname = 'block_direct_api_access'
  ) THEN
    CREATE POLICY block_direct_api_access
      ON public.rule_engine_shadow_log
      AS RESTRICTIVE
      FOR ALL
      TO anon, authenticated
      USING (false);
  END IF;
END $$;
