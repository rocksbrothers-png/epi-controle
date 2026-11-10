# Ficha 360° de EPI — F1: identificação e indicadores

Primeira interface funcional da Ficha 360°. Constrói sobre a fundação da F0
([`FICHA_360_F0_CONTRATOS.md`](FICHA_360_F0_CONTRATOS.md)): mesmo contrato de autorização, mesmo
envelope, mesmo ciclo de vida. Sem custos, mapa corporal, exportação ou listas detalhadas — esses
blocos aparecem como **indisponíveis**, sem número nem conteúdo simulado.

## 1. O que a F1 entrega

| Item | Onde |
|---|---|
| Entrada pela linha do colaborador | botão "Ficha 360°" em Colaboradores (administradores estruturais) e em Gestão do colaborador (Administrador Local) — `modules/employees/ui/employees-view.js` pede o botão ao módulo da Ficha |
| Painel responsivo | modal `#employee-ppe-360-modal` (`static/views/_modals.html`), desenhado por `static/js/modules/employee-ppe-360/ui/employee-ppe-360-view.js` |
| Regras de apresentação (puras) | `static/js/modules/employee-ppe-360/business/employee-ppe-360-summary.js` |
| HTTP | `static/js/modules/employee-ppe-360/integrations/employee-ppe-360-api.js` (única chamada do domínio) |
| Endpoint único | `GET /api/employees/{id}/ppe-360/summary` — `modules/employee_ppe_360/routes.py` + `summary.py` |
| Auditoria (DF-7) | `modules/employee_ppe_360/audit.py` |
| i18n | namespace `employee360.*` nos 5 idiomas |

`static/app.js`: **0 linhas alteradas**.

## 2. Contrato do resumo

Autenticação como em toda a API; depois, o contrato da F0 (`resolve_authorized_employee`):
papel bloqueado e permissão **antes** de qualquer leitura, 404 indistinto para inexistente, outra
empresa ou fora do escopo. Colaborador excluído (anonimizado) também responde 404.

```json
{ "ok": true, "data": {
  "employee": { "id", "name", "registration", "job_title", "sector", "employment_type", "lifecycle",
                "company": {"id","name"}, "unit": {"id","name","temporary_allocation","base_unit_name"},
                "legal_entity": {"name","legal_name","cnpj"} | null,
                "contracted_workforce": {"outsourced_company": {...} | null, "contract": {...} | null, "origin_name"} | null },
  "responsibles": { "unit": [{"role","name"}], "company": [{"role","name"}] },
  "indicators": { "pending_requests": {"total", "by_status": [{"code","count"}]},
                  "next_replacement": {"date","epi_name","overdue_count"} | null,
                  "in_use": {"units","products","categories","uncategorized_products"} } | null,
  "generated_at" } }
```

Regras:

- **Pendentes** = solicitações não concluídas, detalhadas pelo código canônico da máquina de estados
  (`SPEC_CODE`); estado gravado desconhecido aparece como `UNKNOWN`, não é escondido. A pendência de
  assinatura/aceite **não** entra aqui: depende das regras de período da ficha e pertence a
  "Assinaturas e evidências" (fatia própria), para não criar uma contagem enganosa.
- **Próxima troca** = a menor `next_replacement_date` gravada entre as entregas em posse; nunca recalculada.
- **Em uso** = entregas não devolvidas e não revertidas (rollback lógico).
- `indicators` é `null` sem `deliveries:view` (seção ausente, nunca "0").
- Nunca saem CPF, e-mail, WhatsApp, assinatura, foto ou senha (teste negativo em PostgreSQL).

## 3. Decisões aplicadas

| Decisão | Implementação |
|---|---|
| **DF-1** responsáveis | Derivados, nunca um "gestor direto": Administrador Local e Gestor de EPI ativos cuja unidade operacional (incluindo alocação temporária vigente) é a unidade atual do colaborador; Administrador Geral e de Registro ativos da empresa. Só nome e papel |
| **DF-3** Admin Master | `contract.BLOCKED_ROLES` — `FORBIDDEN` antes de qualquer leitura, mesmo tendo `employees:view`. Demais perfis com `employees:view` seguem abrindo |
| **DF-7** auditoria | Concedida → `ficha_epi_audit_log` (`view_360`, aparece no filtro de auditoria da Configuração). Negada → `company_audit_logs` da empresa do ator (`ppe360_view_denied`, com o código do resultado e o id pedido, **sem** o nome do colaborador). Sempre → log estruturado `employee_ppe_360.view` (única trilha possível para o Admin Master, sem empresa). Sem tabela nova |

A trilha `ficha_epi_audit_log` não comporta negativas: exige colaborador, unidade e empresa existentes
(chaves estrangeiras). Por isso a negativa vai para a trilha da empresa.

## 4. Desempenho e pool

Uma requisição por abertura, uma conexão por requisição, devolvida ao fim. Medido em PostgreSQL
(`tests_postgres/test_employee_ppe_360_f1_summary_postgres.py`): 10 Fichas simultâneas → 10 × 200,
nenhuma conexão retida. O pool padrão (`DB_POOL_MAXCONN=10`, `SimpleConnectionPool`) não espera:
o diagnóstico do esgotamento observado em produção é pendência operacional separada.

## 5. Testes

| Suíte | O que prova |
|---|---|
| `tests_postgres/test_employee_ppe_360_f1_summary_postgres.py` | conteúdo real, responsáveis, terceirizado, vazio, arquivado/excluído, autorização por perfil, isolamento por empresa e unidade, 401/403, auditoria concedida e negada, carga de 10 Fichas |
| `tests/test_employee_ppe_360_f0_contract.py` | DF-3 antes de qualquer leitura; a única escrita é a auditoria, pelos registradores oficiais; exatamente uma rota |
| `static/js/test/employee-ppe-360-summary-runtime.js` | regras puras e envelope da integração |
| `scripts/browser/ubx_employee_ppe_360.py` | Chromium, 5 idiomas, desktop e mobile: entrada, uma requisição, estados, descarte de resposta obsoleta, troca de contexto, foco/Escape, perfis, sem moeda, sem rolagem horizontal |

## 6. Pendências

- **Gestor de EPI:** autorizado pelo backend, mas o produto não tem tela de listagem de colaboradores
  para esse perfil (`accessibleEmployeesView` no `app.js`). Uma entrada fora da "linha do
  colaborador" (por exemplo, a partir de Entregas) depende de decisão.
- Fatias seguintes: F3 (entregas, solicitações, devoluções, assinaturas), F2 (EPIs em uso; mapa após a
  classificação de região corporal), F4, F3b, F5 (custos), F6 (exportação).
