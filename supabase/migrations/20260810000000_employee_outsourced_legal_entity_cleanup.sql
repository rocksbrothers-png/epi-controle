-- Migration: limpa employees.legal_entity_id gravado indevidamente em
-- colaborador terceirizado/prestador (ADR-0002 §13.7).
--
-- resolve_employee_legal_entity_id era chamado por
-- create_employee_outsourced_simplified mesmo sem sentido para esse fluxo
-- -- o vinculo juridico de um colaborador terceirizado e com
-- outsourced_company_id (pessoa juridica terceira), nunca com um CNPJ do
-- proprio tenant (legal_entities). Toda linha criada antes da correcao pode
-- ter legal_entity_id apontando para a matriz do tenant (o fallback de
-- resolve_employee_legal_entity_id quando a empresa tem so um CNPJ ativo),
-- fazendo esse colaborador aparecer indevidamente como vinculado ao CNPJ do
-- tenant e podendo bloquear deactivate_legal_entity por causa de gente que
-- nunca deveria ter sido contada ali.
--
-- Idempotente: so afeta linhas com outsourced_company_id preenchido e
-- legal_entity_id nao nulo -- reexecutar nao tem efeito adicional depois da
-- primeira aplicacao. Colaborador CLT (outsourced_company_id NULL) nao e
-- tocado.

UPDATE employees
SET legal_entity_id = NULL
WHERE outsourced_company_id IS NOT NULL
  AND legal_entity_id IS NOT NULL;
