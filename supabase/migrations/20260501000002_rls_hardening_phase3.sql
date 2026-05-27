-- RLS Hardening Phase 3 — tabelas de compras e links
-- Idempotente. Backend Python (role postgres) nao afetado.

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'app_migrations',
    'purchase_requests','purchase_request_items',
    'purchase_orders','purchase_order_items','purchase_order_files',
    'purchase_approvals','purchase_events',
    'purchase_role_unit_links','authorized_suppliers','user_unit_links'
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
