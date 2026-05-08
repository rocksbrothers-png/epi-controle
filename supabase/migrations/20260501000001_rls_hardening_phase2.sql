-- RLS Hardening Phase 2 — demais tabelas public
-- Idempotente. Backend Python (role postgres) nao afetado.

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'companies','app_meta','company_audit_logs','units','employees','epis',
    'deliveries','employee_unit_movements','commercial_contracts',
    'commercial_contract_events','epi_devolutions','stock_movements',
    'epi_qr_sequences','unit_epi_stock','epi_stock_items',
    'epi_stock_item_reprints','epi_ficha_periods','epi_ficha_items',
    'ficha_epi_snapshots','ficha_epi_audit_log','ficha_epi_config',
    'epi_requests','epi_request_history','epi_feedbacks','epi_feedback_history',
    'employee_portal_audit_logs','unit_joint_venture_periods'
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
