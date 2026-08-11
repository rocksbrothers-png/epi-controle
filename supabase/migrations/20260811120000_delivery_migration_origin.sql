-- Procedência da entrega — Lote 2 do Centro de Migração (ADR-0003, issue #211).
--
-- Importar histórico de entregas cria linhas em `deliveries` que NÃO nasceram
-- de uma entrega real feita no sistema: ninguém assinou no aparelho, nenhum
-- estoque foi movimentado, a data é retroativa. Em auditoria trabalhista, a
-- diferença entre "o sistema registrou a entrega" e "o cliente afirmou que a
-- entrega ocorreu" é a diferença entre prova e declaração — e precisa ser
-- legível no dado, não só no processo.
--
-- Três colunas para três perguntas distintas, deliberadamente separadas:
--
--   origin           -> nasceu aqui ou veio de fora?  ('sistema' | 'migracao')
--   source_system    -> veio de fora a partir de quê? ('planilha','sap',...)
--   migration_job_id -> qual importação a trouxe?
--
-- `origin` é TEXT e não booleano: um booleano não distinguiria, depois,
-- importação de planilha de importação por integração sem outra migration.
-- `source_system` é separada porque a classificação é estável e o inventário
-- de sistemas de origem cresce — acrescentar um ERP não pode exigir mexer na
-- semântica de `origin`.
--
-- A FK usa ON DELETE SET NULL, não RESTRICT nem CASCADE: se o job for
-- expurgado por retenção ou LGPD, a limpeza não pode ser bloqueada nem levar
-- a entrega junto. A rastreabilidade some; a classificação permanece. É esse
-- cenário que justifica duas colunas em vez de só a FK.
--
-- `migration_reverted_at` é o rollback lógico: depois que a importação é
-- homologada, desfazê-la não pode mais apagar linha de tabela com valor
-- probatório.
--
-- Idempotente: reexecutar é seguro.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'deliveries'
                      AND column_name = 'origin') THEN
        ALTER TABLE public.deliveries ADD COLUMN origin TEXT NOT NULL DEFAULT 'sistema';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'deliveries'
                      AND column_name = 'source_system') THEN
        ALTER TABLE public.deliveries ADD COLUMN source_system TEXT NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'deliveries'
                      AND column_name = 'migration_job_id') THEN
        ALTER TABLE public.deliveries ADD COLUMN migration_job_id INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'deliveries'
                      AND column_name = 'migration_reverted_at') THEN
        ALTER TABLE public.deliveries ADD COLUMN migration_reverted_at TEXT NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_deliveries_migration_job') THEN
        ALTER TABLE public.deliveries
            ADD CONSTRAINT fk_deliveries_migration_job
            FOREIGN KEY (migration_job_id)
            REFERENCES public.migration_jobs(id) ON DELETE SET NULL;
    END IF;

    -- Homologação do job: a fronteira entre "ainda dá para apagar" e "agora
    -- só rollback lógico". Vazio = fisicamente reversível.
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'migration_jobs'
                      AND column_name = 'homologated_at') THEN
        ALTER TABLE public.migration_jobs ADD COLUMN homologated_at TEXT NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'migration_jobs'
                      AND column_name = 'homologated_by') THEN
        ALTER TABLE public.migration_jobs ADD COLUMN homologated_by INTEGER;
    END IF;
END $$;

-- Índice PARCIAL: o caso comum é `origin = 'sistema'`, e indexá-lo seria
-- indexar a tabela inteira sem ganho. Quem consulta procura o que foi migrado
-- — relatório de importação, tela de auditoria, o próprio rollback.
CREATE INDEX IF NOT EXISTS idx_deliveries_migrated
    ON public.deliveries (company_id, migration_job_id)
    WHERE origin <> 'sistema';
