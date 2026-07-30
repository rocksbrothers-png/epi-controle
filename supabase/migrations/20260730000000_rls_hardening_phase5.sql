-- RLS Hardening Phase 5 — tabelas criadas após a fase 4 (Multi-CNPJ,
-- Cadastro Simplificado de Terceirizados/ADR-0002, PPE Test, estoque F0)
-- que o Supabase Security Advisor sinalizou sem policy (ou com RLS
-- desabilitado — ambos os casos são cobertos pelo mesmo ALTER idempotente).
-- Mesmo padrão das fases 1-4: bloqueia acesso direto via PostgREST
-- (anon/authenticated); o backend Python (role postgres) não é afetado.
-- Idempotente — tabelas ausentes são ignoradas (o bootstrap roda antes).

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'legal_entities',
    'user_legal_entities',
    'employee_legal_entity_movements',
    'outsourced_companies',
    'service_contracts',
    'epi_reimbursements',
    'delivery_evidence',
    'stock_reservations',
    'stock_replenishment_needs',
    'ppe_test_plans',
    'ppe_test_candidates',
    'ppe_test_participants',
    'ppe_test_distributions',
    'ppe_test_evaluations',
    'ppe_test_events',
    'ppe_test_incidents',
    'ppe_test_suggestions'
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
