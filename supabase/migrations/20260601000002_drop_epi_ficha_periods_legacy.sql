-- Phase 26: safety-net drop para epi_ficha_periods_legacy.
-- A migration _ensure_ficha_periods_sequence_unique ja dropa esta tabela
-- ao final da execucao, mas bancos com falha parcial podem ainda te-la.
-- Idempotente.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'epi_ficha_periods_legacy'
  ) THEN
    DROP TABLE public.epi_ficha_periods_legacy;
  END IF;
END $$;
