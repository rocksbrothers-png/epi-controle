-- RLS Hardening Phase 6 — tabelas ainda sem RLS depois da fase 5.
--
-- Três vieram do Centro de Migração (ADR-0003): criadas em core/schema.py,
-- nasceram depois da fase 5 e nunca entraram numa fase de hardening. O
-- Supabase Security Advisor as reporta como ERROR (`rls_disabled_in_public`)
-- no projeto corporativo e INFO (`rls_enabled_no_policy`) no SaaS.
--
-- As outras três já têm RLS nos dois projetos de produção, mas NÃO ganham RLS
-- num banco criado do zero: as fases que as cobriam pulam tabela ausente
-- (`CONTINUE WHEN NOT EXISTS`) e nunca voltam. Sem elas aqui, todo ambiente
-- novo nasce com essas tabelas descobertas. Incluí-las é idempotente onde já
-- está aplicado.
--
-- Mesmo padrão das fases 1-5: bloqueia acesso direto via PostgREST
-- (anon/authenticated); o backend Python (role postgres) não é afetado.
-- Idempotente — tabelas ausentes são ignoradas.

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    -- Centro de Migração (ADR-0003). migration_job_records guarda o payload
    -- importado, incluindo dados pessoais como CPF.
    'migration_jobs',
    'migration_job_records',
    'migration_field_mappings',
    -- Cobertas em produção, mas ausentes em banco novo pelo motivo acima.
    'epi_evaluation_summary',
    'purchase_pendencies',
    'report_requests'
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
