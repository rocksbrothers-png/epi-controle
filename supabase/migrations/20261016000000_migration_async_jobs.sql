-- Migration: RLS versionada da fila de migração assíncrona (Fase 3, MIG-DATA-FIX-V1).
--
-- CONTEXTO
--
-- `migration_async_jobs` guarda o controle dos jobs assíncronos do Centro de
-- Migração: payload do arquivo CIFRADO (Fernet), empresa/ator, estratégia e
-- estado. É backend-only — toda leitura/escrita passa pelo backend, que conecta
-- como owner/service role. Como as demais tabelas multi-tenant (028/029 e #309),
-- nega acesso direto via PostgREST aos papéis `anon`/`authenticated`.
--
-- POR QUE VERSIONADA (não só no bootstrap)
--
-- `modules/data_migration/async_jobs.install_schema` cria a tabela e habilita a
-- RLS em todo boot. Mas a proteção não pode depender só de bootstrap (lição da
-- #309): esta migration versiona a RLS, deixando-a em `app_migrations` e visível
-- aos gates derivados de migrations (ci_migrations_report.py, test_rls_coverage).
--
-- POR QUE UM ÚNICO BLOCO `DO $$`
--
-- Se o `CREATE POLICY` falhar, o bloco inteiro reverte e o `ENABLE` vai junto —
-- o estado perigoso "RLS ligada sem policy" fica inalcançável por construção. É
-- o molde de `20260829000000_payment_attempts_rls.sql`.
--
-- UPGRADE / IDEMPOTÊNCIA
--
-- `IF EXISTS` (tabela criada pelo bootstrap antes) torna a migration no-op em
-- vez de erro; `IF NOT EXISTS (pg_policies …)` cobre o banco já provisionado e a
-- segunda passagem do relatório da #275. Único efeito garantido: registrar o id.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'migration_async_jobs'
  ) THEN
    EXECUTE 'ALTER TABLE public.migration_async_jobs ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'migration_async_jobs'
        AND policyname = 'block_direct_api_access'
    ) THEN
      EXECUTE 'CREATE POLICY block_direct_api_access ON public.migration_async_jobs AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)';
    END IF;
  END IF;
END $$;
