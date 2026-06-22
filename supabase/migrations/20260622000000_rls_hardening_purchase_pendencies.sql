-- RLS Hardening — purchase_pendencies (criada após as fases 1-4)
-- Corrige o advisor `rls_disabled_in_public`: era a única tabela public sem RLS.
-- Idempotente. Backend Python (role postgres) nao afetado — apenas bloqueia o
-- acesso direto via PostgREST (anon/authenticated), como nas demais 42 tabelas.
-- Aplicado em produção via Supabase MCP em 2026-06-22.

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'purchase_pendencies'
  ];
BEGIN
  FOREACH tbl IN ARRAY tbls LOOP
    CONTINUE WHEN NOT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = tbl
    );

    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = tbl
        AND policyname = 'block_direct_api_access'
    ) THEN
      EXECUTE format(
        'CREATE POLICY block_direct_api_access ON public.%I AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)',
        tbl
      );
    END IF;
  END LOOP;
END $$;
