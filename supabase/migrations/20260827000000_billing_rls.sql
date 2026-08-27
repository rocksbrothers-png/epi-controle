-- Migration: a RLS das cinco tabelas de billing passa a ser versionada (#309).
--
-- O QUE ESTAVA ERRADO
--
-- `payments`, `payment_plans`, `subscriptions`, `invoices` e
-- `subscription_audit_logs` recebiam RLS de `modules/payments/service.py`, via
-- o helper `_enable_rls`, chamado de `ensure_payment_tables` e
-- `ensure_subscription_tables`. As duas estão em `_ensure_fns`
-- (`core/bootstrap.py`), então rodavam em TODO boot: a proteção existia em
-- produção, e continua existindo. O defeito nunca foi ausência de RLS.
--
-- O defeito é de RASTREABILIDADE. Aquele DDL não era migration: não entrava em
-- `app_migrations`, não tinha ordem declarada em relação às demais, e era
-- INVISÍVEL a qualquer gate derivado de migrations. O relatório da #275
-- acusava as cinco como `unexpected_policy` — o CI chamando de intrusa uma
-- policy que o próprio bootstrap criava — até a etapa 2 separá-las num
-- conjunto próprio, `known_bootstrap_rls_tables`. Este arquivo é o que zera
-- esse conjunto pela via certa.
--
-- POR QUE UM ÚNICO BLOCO `DO $$`, E NÃO INSTRUÇÕES SOLTAS
--
-- Não é preferência de estilo. `20260712120000_tenant_domains_owner_2fa.sql`
-- faz `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` na linha 52 e `CREATE POLICY`
-- na 54 — duas instruções separadas. Quando a segunda falhou (roles `anon`
-- ausentes no CI), o autocommit já tinha gravado a primeira, e a tabela ficou
-- com RLS LIGADA e ZERO POLICY: nega tudo em silêncio, que é pior do que
-- nenhuma das duas. Foi assim que a etapa 1 da #275 encontrou o caso.
--
-- Dentro de um `DO $$` o conjunto é UMA instrução. Se o `CREATE POLICY` falhar,
-- o bloco inteiro reverte e o `ENABLE` vai junto — o estado perigoso fica
-- inalcançável por construção, não por disciplina. É o molde de
-- `20260501000000_rls_hardening_phase1.sql`, repetido sem variação.
--
-- UPGRADE EM BANCO JÁ PROVISIONADO
--
-- Em produção as cinco já têm RLS e a policy, aplicadas pelo bootstrap. O
-- `IF NOT EXISTS (pg_policies …)` encontra a policy e não faz nada; o
-- `ALTER … ENABLE` sobre tabela já habilitada é inócuo. O único efeito é
-- registrar `028_billing_rls` em `app_migrations` — que é exatamente a
-- rastreabilidade que faltava.
--
-- O `CONTINUE WHEN NOT EXISTS` cobre a ordem do bootstrap: os `ensure_*` criam
-- as tabelas antes de `run_pending_migrations`, mas se alguma ainda não
-- existir a migration vira no-op em vez de erro.

DO $$
DECLARE
  tbl  text;
  tbls text[] := ARRAY[
    'payments',
    'payment_plans',
    'subscriptions',
    'invoices',
    'subscription_audit_logs'
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
