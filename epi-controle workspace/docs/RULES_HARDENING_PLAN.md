# Hardening incremental do motor de regras (EPI Controle)

## Objetivo
Preparar enforcement progressivo sem alterar o comportamento atual do sistema.

## Estado atual (já funcional)
- Regras legadas em endpoints (escopo por empresa, unidade operacional, JV, RBAC).
- Área administrativa de Configuração com persistência de regras de visibilidade.

## Estrutura adicionada para evolução segura
1. `epi_backend/rule_engine.py`
   - contrato central de contexto de regra (`RuleContext`)
   - payload padrão de framework (`default_framework_payload`)
   - normalização de configuração (`normalize_framework_payload`)
   - feature flag de ativação (`should_enable_new_engine`)
   - resolução padronizada de filtros de visibilidade (`resolve_visibility_filters`)
   - resolução padronizada de escopo de relatório (`resolve_report_scope`)
   - diagnóstico de decisão (`evaluate_rule_decision`)

2. Persistência de framework por empresa
   - chave: `configuration_framework:<company_id>` em `app_meta`
   - compatível com regras atuais (`visibility_rules`) já salvas em `configuration_rules:<company_id>`

3. Endpoints de base para rollout
   - `GET /api/configuration-framework`
   - `POST /api/configuration-framework`
   - `GET /api/rules-engine/diagnostics`

4. Execução dupla com fallback obrigatório
   - comparação em background (`shadow/canary`) entre legado e novo motor para `units`, `employees` e `epis`
   - resposta final sempre do legado (fonte da verdade)
   - divergências registradas em log estruturado:
     - `rules_engine.shadow_diff_detected`
     - `rules_engine.shadow_diff_none`
     - `rules_engine.shadow_failed_fallback_legacy`

## Estratégia de rollout recomendada
1. **Fase 0 (atual)**: `enable_new_rules_engine = false` (fallback 100% legado).
2. **Fase 1 (canary)**: ativação por endpoint em ambiente `staging`.
3. **Fase 2 (perfil)**: ativação por `registry_admin` e `general_admin` em endpoints de relatório.
4. **Fase 3 (usuário)**: ativação por lista controlada de usuários.
5. **Fase 4 (produção parcial)**: ativação gradativa endpoint a endpoint.
6. **Fase 5 (enforcement completo)**: remover fallback apenas quando métricas e auditoria estiverem estáveis.

### Chaves de feature flag granular
- `execution_mode`: `off|shadow|canary|enforced`
- `enabled_profiles`
- `enabled_user_ids`
- `enabled_company_ids`
- `enabled_endpoints`
- `enabled_environments`
- `rollout_percentage` (bucket determinístico por usuário/endpoint)
- `allow_new_engine_response` (deve permanecer `false` até validação total)

## Pontos de integração futura (sem quebrar legado)
- `reports`: consumir `resolve_report_scope` antes de filtros finais.
- `stock/epis`: usar `resolve_visibility_filters` como hook de pré-filtro.
- `deliveries`: validar escopo por colaborador/unidade via contexto central.
- `dashboard`: consolidar cards e alertas com escopo unificado.

## Observabilidade futura
- habilitar `observability.audit_decisions` para registrar decisões de visibilidade por endpoint.
- habilitar `observability.debug_visibility` para troubleshooting controlado.

## Riscos e mitigação
- **Risco**: divergência entre regra legada e regra nova ao ativar flag.
  - **Mitigação**: ativação progressiva + endpoint de diagnóstico.
- **Risco**: configuração incompleta por empresa.
  - **Mitigação**: `normalize_framework_payload` com defaults determinísticos.
- **Risco**: regressão por migração ampla.
  - **Mitigação**: manter fallback legado até cobertura total por testes e auditoria.
