-- Migration 029: payment_attempts — idempotência do checkout (efeito externo MP).
--
-- CONTEXTO
--
-- A validação 1H-C da PR #1017 confirmou (espelho do SaaS #392) que duas
-- requisições concorrentes ou um retry após o Mercado Pago já ter criado o
-- preapproval podiam gerar DOIS preapprovals: o `mp_client` mandava um
-- `X-Idempotency-Key` com `uuid4()` NOVO a cada chamada. A correção dá
-- identidade estável à INTENÇÃO de checkout e registra cada tentativa em
-- `public.payment_attempts`, com unicidade imposta pelo BANCO.
--
-- POR QUE A UNICIDADE É VERSIONADA AQUI (não só no bootstrap)
--
-- `core/checkout_idempotency.ensure_payment_attempt_tables` cria a tabela e o
-- índice UNIQUE em todo boot (SQLite nos testes, Postgres em produção). Mas a
-- GARANTIA crítica de idempotência não pode depender apenas de
-- `CREATE ... IF NOT EXISTS` em bootstrap (mesma lição da #309): esta migration
-- versiona o índice UNIQUE e a RLS, deixando-os em `app_migrations` e visíveis
-- aos gates derivados de migrations.
--
-- POR QUE RLS RESTRICTIVE
--
-- `payment_attempts` guarda dados multi-tenant (company_id, ator, intenção).
-- Como as demais tabelas de billing (028/#309), nega acesso direto via
-- PostgREST aos papéis `anon`/`authenticated`: toda leitura/escrita passa pelo
-- backend. Um único bloco `DO $$` torna inalcançável o estado "RLS ligada sem
-- policy" (se o CREATE POLICY falhar, o ENABLE reverte junto).
--
-- UPGRADE / IDEMPOTÊNCIA
--
-- `CONTINUE WHEN NOT EXISTS` (tabela ainda não criada pelo bootstrap) torna a
-- migration no-op em vez de erro. `IF NOT EXISTS` no índice e na policy cobre o
-- banco já provisionado: o único efeito garantido é registrar o id em
-- `app_migrations`.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'payment_attempts'
  ) THEN
    -- Unicidade da intenção por empresa — a atomicidade da idempotência.
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes
      WHERE schemaname = 'public' AND indexname = 'idx_payment_attempts_company_key'
    ) THEN
      EXECUTE 'CREATE UNIQUE INDEX idx_payment_attempts_company_key ON public.payment_attempts(company_id, idempotency_key)';
    END IF;

    EXECUTE 'ALTER TABLE public.payment_attempts ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'payment_attempts'
        AND policyname = 'block_direct_api_access'
    ) THEN
      EXECUTE 'CREATE POLICY block_direct_api_access ON public.payment_attempts AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)';
    END IF;
  END IF;
END $$;
