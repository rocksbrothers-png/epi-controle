-- RLS — módulo de Compras Fase F0 (tabelas de fornecedores/cotações/portal)
-- Habilita RLS nas 7 tabelas novas criadas pelo bootstrap Python
-- (core/schema.ensure_procurement_supplier_tables), no mesmo padrão das fases
-- de hardening anteriores: bloqueia acesso direto via PostgREST
-- (anon/authenticated); o backend Python (role postgres) não é afetado.
-- Idempotente — tabelas ausentes são ignoradas (o bootstrap roda antes).

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'supplier_products',
    'purchase_quotes',
    'purchase_quote_items',
    'supplier_portal_links',
    'supplier_portal_audit_logs',
    'purchase_order_confirmations',
    'supplier_integrations'
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
