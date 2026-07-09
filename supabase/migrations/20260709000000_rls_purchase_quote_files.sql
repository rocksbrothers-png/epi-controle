-- RLS — módulo de Compras Fase F2 (arquivos de proposta da cotação)
-- Mesmo padrão das fases anteriores: bloqueia acesso direto via PostgREST;
-- backend Python (role postgres) não é afetado. Idempotente.

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'purchase_quote_files'
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
