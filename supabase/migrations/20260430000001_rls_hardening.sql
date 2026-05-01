-- RLS Hardening — Fase 1 + Fase 2 (todas as tabelas public)
-- Idempotente. Backend Python (role postgres) não é afetado.

-- FASE 1: tabelas com colunas sensíveis

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname='public' AND tablename='users' AND policyname='block_direct_api_access'
  ) THEN
    CREATE POLICY block_direct_api_access ON public.users
      AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false);
  END IF;
END $$;

ALTER TABLE public.employee_portal_links ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname='public' AND tablename='employee_portal_links' AND policyname='block_direct_api_access'
  ) THEN
    CREATE POLICY block_direct_api_access ON public.employee_portal_links
      AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false);
  END IF;
END $$;

-- FASE 2: demais tabelas
DO $$
DECLARE
  tbl text;
  tables text[] := ARRAY[
    'companies','app_meta','company_audit_logs','units','employees','epis',
    'deliveries','employee_unit_movements','commercial_contracts',
    'commercial_contract_events','epi_devolutions','stock_movements',
    'epi_qr_sequences','unit_epi_stock','epi_stock_items',
    'epi_stock_item_reprints','epi_ficha_periods','epi_ficha_items',
    'ficha_epi_snapshots','ficha_epi_audit_log','epi_requests',
    'epi_request_history','epi_feedbacks','epi_feedback_history',
    'employee_portal_audit_logs','unit_joint_venture_periods'
  ];
BEGIN
  FOREACH tbl IN ARRAY tables LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema='public' AND table_name=tbl
    ) THEN
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname='public' AND tablename=tbl AND policyname='block_direct_api_access'
      ) THEN
        EXECUTE format(
          'CREATE POLICY block_direct_api_access ON public.%I AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)',
          tbl
        );
      END IF;
    END IF;
  END LOOP;
END $$;
