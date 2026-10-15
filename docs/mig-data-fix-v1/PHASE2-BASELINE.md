# MIG-DATA-FIX-V1 — Fase 2 baseline

Somente Fase 2 autorizada. MERGE/DEPLOY/FORCE-PUSH=NO; sem dados reais,
sem migrations compartilhadas; branch protection inalterada. Fases3–5 não iniciadas.

HEADs main confirmados em 2026-10-15:
- Corporate 6fe74cf6a20eeaeb0e18dedfa26ebd32d950e2cd (merge #1034).
- SaaS 585a692a39a6decbfe7139685a71fe7f3f431aac (merge #407).

Ambos contêm os P0; seis workflows pós-merge acionados (Backend CI, Migration
Journey, Contract Tests, Isolation Guard, Security, CodeQL) concluíram success.
Branch/worktree dedicada codex/mig-data-fix-v1-phase2 em cada produto.

ADR-0003, relatório de auditoria MIG-DATA-AUDIT-V1, matriz das nove entidades,
contratos service/preview/mapper/sources/rotas/interface e proteções P0 inspecionados.
Nenhuma entidade nova autorizada; catálogos e modelos reais serão preservados.

GREEN existente: 430 passed por produto (299 PostgreSQL +131 unitários pertinentes).
RED novo: 32 failed,2 passed por produto em test_migration_phase2_postgres.py e
 test_migration_phase2_sources.py, sem produto alterado. Bancos novos separados
mig_phase2_corporate/mig_phase2_saas UTF8, somente fixtures sintéticas.

Defeitos RED: CPF/matrícula divergentes não bloqueados; chave secundária ignorada;
prévia ignora estratégia e inclui inválido como inserção; histórico sem chave
natural conta uma inserção para múltiplas linhas; reimportação não prevista;
rejeição total termina completed/applied; processados exclui erros; SQL técnico
nos diagnósticos; unidade vazia vira base; JSON/CSV/XML/XLSX perdem valores.

Plano: (1) baseline RED/drafts; (2) parsing estrito e contrato compatível;
(3) identidade/plano único por linha, revalidação/contagens/estados; (4) ajustes
pontuais UI e testes; (5) freeze/CI/auditoria independente. Jobs assíncronos,
checkpoints e redesign UI ficam para Fases3/4 mediante autorização posterior.
