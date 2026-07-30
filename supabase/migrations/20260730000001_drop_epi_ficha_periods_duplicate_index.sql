-- Duplicate Index (Supabase Performance Advisor) — epi_ficha_periods tinha
-- duas constraints/índices UNIQUE cobrindo exatamente as mesmas colunas
-- (employee_id, period_start, period_end, ficha_sequence):
--   - uma legada, com nome auto-gerado pelo Postgres (herdada de uma versão
--     anterior do schema, antes de ficha_sequence ganhar nome próprio na
--     constraint);
--   - uq_epi_ficha_periods_employee_window_sequence, a atual, criada por
--     core.schema._ensure_ficha_periods_sequence_unique.
--
-- Essa função de bootstrap tem uma guarda de idempotência que retorna assim
-- que o índice atual já existe — e por isso nunca chegou a limpar a legada
-- depois que ela apareceu num banco já migrado. Esta migration cobre esse
-- gap uma única vez. Idempotente: sem linhas a dropar na segunda execução.

DO $$
DECLARE
  legacy record;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'epi_ficha_periods'
  ) THEN
    RETURN;
  END IF;

  FOR legacy IN
    SELECT indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename = 'epi_ficha_periods'
      AND indexname <> 'uq_epi_ficha_periods_employee_window_sequence'
      AND indexdef ILIKE '%(employee_id, period_start, period_end, ficha_sequence)%'
  LOOP
    EXECUTE format('ALTER TABLE public.epi_ficha_periods DROP CONSTRAINT IF EXISTS %I', legacy.indexname);
    EXECUTE format('DROP INDEX IF EXISTS public.%I', legacy.indexname);
  END LOOP;
END $$;
