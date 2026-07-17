# Fluxo de Avaliação e Homologação de EPI em Teste

Entregáveis de análise (seção 26 da proposta) e documentação da implementação.

## 1. Inventário do módulo atual de avaliações

| Componente | Local | Função |
|---|---|---|
| Serviço de avaliações | `modules/feedback/service.py` | Avaliações/sugestões de EPIs **já aprovados** (`epi_feedbacks`), triagem do gestor, análise HSEQ, decisão administrativa, ranking |
| Rotas | `modules/feedback/routes.py` | `/api/feedbacks*`, `/api/avaliacoes/*` |
| Tabelas | `core/schema.py` | `epi_feedbacks`, `epi_feedback_history`, `epi_evaluation_summary` |
| Portal do colaborador | `modules/portal` | Colaborador envia avaliação/sugestão via link do portal |
| Engine de escopo | `epi_backend/epi_scope.py` | Regra de visibilidade C1+D1+E3 (confirmada) |
| JV (fonte de verdade) | `epi_backend/unit_jv_lifecycle.py` | `unit_joint_venture_periods` — período ativo de JV por unidade |

## 2. Fluxo atual dos EPIs aprovados (preservado)

`recebido → em_analise_gestor → (aguardando_hseq) → aguardando_aprovacao_admin →
aprovado/reprovado/acao_corretiva/encerrado`, com ranking e status computado
(`super_bem_avaliado` / `super_mal_avaliado`). **Nada desse fluxo foi alterado**,
exceto o final da *sugestão de novo EPI* (ver §11 — fluxo único).

## 3. Regras de escopo existentes (a regra correta, confirmada no código)

O escopo **não é um campo escolhido livremente** — é **derivado** do registro do
EPI (`epi_backend/epi_scope.py`, regra C1+D1+E3, coberta por `tests/test_epi_scope.py`):

- JV ativa na unidade do EPI → `JOINT_VENTURE` (fonte de verdade: `unit_joint_venture_periods.ended_at IS NULL`);
- `unit_id` preenchido → `UNIT`;
- nenhum dos dois → `GLOBAL`.

Visibilidade:
- Unidade **fora de JV**: vê `GLOBAL` + `UNIT` própria.
- Unidade **em JV X**: vê `UNIT` própria + EPIs da JV X. **GLOBAL fica oculto.**

**Única x Única**: quando a empresa possui **uma única unidade ativa**, o EPI
homologado nasce vinculado àquela unidade (semântica `UNIT` da regra existente) —
sem regra artificial de Global nem de Joint Venture. O rótulo `UNIQUE` é gravado
apenas como metadado de auditoria (`ppe_test_candidates.scope_type` /
`epis.approval_scope_type`); a visibilidade continua 100% no engine existente.
O servidor **nunca confia** no escopo enviado pelo frontend
(`resolve_approval_scope` valida unidades ativas e períodos de JV da tenant).

## 4. Lacunas que a implementação cobriu

- Não existia cadastro provisório: sugestão aceita virava EPI oficial **direto** (`INSERT INTO epis`), sem teste, plano, participantes ou decisão formal.
- Não existia período controlado, distribuição rastreada nem ocorrências.
- Não existia decisão formal transacional com escopo validado no servidor.

## 5. Arquitetura implementada

Novo módulo isolado, reutilizando os padrões do módulo de avaliações
(router, `authorize_action`, `ensure_resource_company`, histórico/auditoria):

- `epi_backend/ppe_test_schema.py` — tabelas (idempotente, registrado em `_ensure_fns` de `core/schema.py`).
- `modules/ppe_tests/service.py` — domínio (validações, máquina de estados, consolidação, escopo, homologação transacional).
- `modules/ppe_tests/routes.py` — rotas registradas em `app.py`.
- UI: sub-aba **🧪 Novos EPIs em Teste** dentro de Avaliações (`static/views/avaliacoes.html` + módulo `initPpeTestsModule` em `static/app.js`).

## 6. Máquina de estados

Sugestão: `recebida → em_triagem → aprovada_para_analise | info_solicitada | duplicada | inviavel | rejeitada → convertida`

Candidato (cadastro provisório):

```
rascunho → em_analise_tecnica → aprovado_para_teste → em_teste ⇄ teste_suspenso
        → teste_concluido → em_decisao → aprovado → homologado
                                       → reprovado | arquivado
decisões: aprovar | aprovar_com_restricao | prorrogar_teste (→ em_teste)
          | nova_rodada (→ aprovado_para_teste) | solicitar_ajuste_fornecedor
          | rejeitar | arquivar
```

Guardas principais:
- iniciar teste exige plano + ≥1 participante;
- entrega exige teste `em_teste`, participante e **saldo do lote**;
- ocorrência **crítica** pode suspender; retomada bloqueada com crítica aberta;
- decisão de aprovação exige justificativa + parecer técnico + críticas tratadas + mínimos do plano (participantes/taxa de resposta/avaliações finais), com exceção justificada (`override_minimums`);
- homologação exige decisão `aprovar|aprovar_com_restricao`, é idempotente (`approved_epi_id`) e bloqueia duplicidade de código/CA no banco oficial;
- reprovação bloqueia novas entregas (devolução/descarte continuam permitidos para recolhimento) e preserva todo o histórico.

## 7. Modelo de dados

`ppe_test_suggestions`, `ppe_test_candidates` (cadastro provisório + decisão + escopo + vínculo `approved_epi_id`), `ppe_test_plans`, `ppe_test_participants`, `ppe_test_distributions` (recebimento/entrega/devolução/descarte), `ppe_test_evaluations` (estágios inicial/intermediária/final, notas 1–5 em JSON + comparativo com EPI atual), `ppe_test_incidents`, `ppe_test_events` (auditoria/timeline).

Colunas novas em `epis`: `origin_test_candidate_id`, `approval_scope_type` (metadado), `homologated_at`. Todas as tabelas carregam `company_id` (+`unit_id` quando aplicável) — isolamento por tenant via `ensure_resource_company`, como no restante do sistema.

## 8. APIs

Adaptação: o servidor HTTP legado não atende `PATCH`; atualizações usam `POST` em sub-rotas.

```
GET/POST /api/ppe-test-suggestions
GET      /api/ppe-test-suggestions/{id}
POST     /api/ppe-test-suggestions/{id}/triage
POST     /api/ppe-test-suggestions/from-feedback      (ponte portal → fluxo único)

GET/POST /api/ppe-tests
GET      /api/ppe-tests/{id}
GET      /api/ppe-tests/{id}/results
POST     /api/ppe-tests/{id}/update | technical-review | plan | start | suspend
         | resume | complete | participants | participants/{pid}/status
         | distributions | evaluations | incidents | incidents/{iid}/resolve
         | decision | homologate | reject
```

## 9. Matriz de permissões (`core/permissions.py`)

| Papel | view | suggest | triage | manage | evaluate | tech_review | decide | homologate |
|---|---|---|---|---|---|---|---|---|
| master_admin (suporte auditado) | ✔ | — | — | — | — | — | — | — |
| general_admin | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| registry_admin | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | — | — |
| user (Admin Local) | ✔ | ✔ | — | ✔ | ✔ | — | — | — |
| epi_manager (Segurança) | ✔ | ✔ | ✔ | — | ✔ | ✔ | — | — |
| admin | ✔ | ✔ | — | — | — | — | — | — |
| colaborador | via portal (sugestão promovida pelo fluxo único) |

## 10. Regras de homologação

Operação **transacional** (uma conexão; commit na rota): valida decisão formal,
resolve/valida escopo no servidor, bloqueia duplicidade (código/CA), cria o EPI
oficial com `(unit_id, active_joinventure)` conforme a regra C1+D1+E3, grava
vínculo bidirecional e evento de auditoria, e arquiva (nunca apaga) o registro
provisório com status `homologado`.

## 11. Fluxo único de sugestões (sem duplicidade)

`apply_accept_suggestion_as_epi` **não cria mais EPI direto**: a sugestão aceita
no módulo legado entra no fluxo de EPI em teste
(`create_suggestion_from_feedback`) e segue **um único caminho até o final**:
triagem → análise técnica → teste controlado → decisão → homologação. Dois
pontos de entrada (portal do colaborador e cadastro direto pela
empresa/fornecedor/representante), um único fluxo e um único final.

## 12. Riscos e mitigação

- Duplicidade no banco oficial → guarda por `approved_epi_id` + verificação de código/CA na homologação (testado).
- Escopo inválido vindo do frontend → `resolve_approval_scope` valida tenant/unidades/JV no servidor (testado).
- Regressão do fluxo legado → suíte completa verde (1203 passed) e fluxo de EPIs aprovados intocado.

## 13. Plano de testes

`tests/test_ppe_test_flow.py` (29 casos): ciclo completo, triagem com justificativa,
lote/saldo, suspensão por ocorrência crítica, escala 1–5, mínimos de decisão com
exceção, escopos GLOBAL/JV/UNIT com asserção de visibilidade no engine real,
Única x Única, idempotência/anti-duplicidade da homologação, reprovação,
isolamento multi-tenant, matriz de permissões, auditoria e fluxo único da
sugestão aceita.

## 14. Migração e rollback

- **Migração**: tabelas novas criadas de forma idempotente no bootstrap (`ensure_ppe_test_tables`); colunas novas em `epis` via `ALTER TABLE` guardado por `PRAGMA table_info`. Nenhum dado existente é alterado.
- **Rollback**: reverter o deploy basta — as tabelas `ppe_test_*` ficam órfãs sem afetar o legado; as 3 colunas novas em `epis` são inertes para o código antigo. Nenhuma migração destrutiva.
