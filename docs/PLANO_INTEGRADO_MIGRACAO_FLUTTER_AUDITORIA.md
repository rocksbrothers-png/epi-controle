# Plano Integrado — Migração Flutter Web + Correções da Auditoria

## 1. Roadmap executivo

| Fase | Objetivo | Resultado esperado |
| --- | --- | --- |
| 1. Fundação | Autenticação, RBAC, SessionContext, guards e rotas públicas | Nenhuma rota privada acessível indevidamente; `/portal` e `/qr` públicos quando aplicável |
| 2. Multi-tenant | Auditoria e enforcement de `company_id`/`unit_id` no backend | Usuário não acessa dados de outra empresa/unidade |
| 3. Employees | Migrar Funcionários para `presentation/domain/data` | Paridade de CRUD, permissões e filtros |
| 4. Stock | Migrar Estoque para Repository Pattern | Movimentações, QR e fila offline preservados |
| 5. Deliveries | Migrar Entregas | Assinatura, histórico e baixa de estoque validados |
| 6. Purchases | Migrar Compras | Requisição, aprovação, recebimento e estoque automático validados |
| 7. Reports | Migrar Relatórios | Filtros tenant, exportação e performance validados |

## 2. Roadmap técnico

1. Manter o legado em `/` e Flutter Web em `/app` sem alterar contratos existentes.
2. Consumir somente API REST no Flutter; regras de negócio continuam no backend Python.
3. Evoluir gradualmente de `Cubit → ApiClient` para `Cubit → UseCase → Repository → ApiClient`.
4. Adotar a estrutura alvo por módulo:
   - `presentation/pages`, `presentation/widgets`, `presentation/cubits`
   - `domain/entities`, `domain/repositories`, `domain/usecases`
   - `data/datasources`, `data/repository_impl`
5. Criar testes de contrato para cada endpoint consumido antes de migrar telas.

## 3. Backlog priorizado

| Prioridade | Item | Tipo | Critério de aceite |
| --- | --- | --- | --- |
| P0 | Garantir contrato de login/auth-me | Segurança | Flutter lê `permissions`, `role`, `company_id`, `unit_id` do backend |
| P0 | SessionContext central | Arquitetura | Cubits e módulos consomem contexto único |
| P0 | Guards públicos/privados | Segurança | `/portal` e `/qr` não exigem sessão; rotas privadas exigem login |
| P0 | Matriz RBAC Flutter × backend | Segurança | `routePermissions` espelha `core/permissions.py` |
| P1 | Auditoria multi-tenant por endpoint | Segurança | Todos os endpoints validam `company_id` e escopo operacional |
| P1 | Employees Repository Pattern | Migração | CRUD com paridade e testes |
| P1 | Stock Repository Pattern | Migração | Movimentações e QR com filtros tenant |
| P2 | Deliveries/Purchases/Reports | Migração | Paridade funcional e testes de integração |
| P2 | PlutoGrid Web/Desktop | UX | Recomendação aprovada antes da implementação |

## 4. Matriz de riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Divergência de permissões frontend/backend | Acesso indevido ou bloqueio falso | Testes unitários da matriz e revisão contra `core/permissions.py` |
| Acesso cross-tenant | Vazamento de dados | Enforce backend por `company_id`, `unit_id`, role e testes negativos |
| Quebra do legado | Interrupção operacional | Deploy paralelo; não remover `app.js/index.html/static` |
| Regras duplicadas no Flutter | Inconsistência | Flutter só orquestra estado; backend decide regras |
| Migração Big Bang | Alto risco de regressão | Migrar por módulo, com feature flags e rollback |

## 5. Plano de migração

- Usar `SessionContext` como fundação de todos os módulos Flutter.
- Para cada módulo, primeiro envolver chamadas existentes em datasource/repository sem mudar payloads.
- Depois criar entities/usecases e adaptar cubits.
- Por fim, substituir widgets/telas mantendo rotas e contratos.
- O legado permanece como fallback até a paridade ser comprovada.

## 6. Plano multi-tenant

| Área | Já implementado | Parcial | Faltando implementar |
| --- | --- | --- | --- |
| Autenticação | Login retorna usuário e permissões | Contexto Flutter central recém-adicionado | Testes E2E por tenant |
| Backend auth | `ensure_company_access` e `authorize_action` | Cobertura varia por módulo | Auditoria endpoint a endpoint |
| Employees | Filtros por empresa no backend | Unidade operacional em evolução | Testes negativos por unidade |
| Stock | Endpoints protegidos por permissão | Validar filtros em relatórios/movimentos | Canary cross-tenant automatizado |
| Purchases | Escopo por empresa e unidade operacional | Fluxos de aprovação complexos | Matriz de papéis por etapa |
| Portal/QR | Rotas públicas previstas | Garantir endpoints públicos mínimos | Rate limit/auditoria pública |
| Reports | Permissões existentes | Performance e filtros avançados | Testes de exportação por tenant |

## 7. Plano de arquitetura

A transição deve ser incremental:

```text
Hoje:    Page → Cubit → ApiClient → Backend
Alvo:    Page → Cubit → UseCase → Repository → Datasource/ApiClient → Backend
```

Regra de ouro: repository não decide regra de negócio corporativa; ele apenas traduz contratos, trata erros técnicos e entrega entidades ao domínio Flutter.

## 8. Plano de paridade

| Módulo | Funcionalidade | Legado | Flutter | Status | Diferença | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| Auth | Login, refresh, permissões | Sim | Sim | 🟢 Completo | SessionContext centralizado | P0 |
| Portal/QR | Acesso público | Sim | Sim | 🟡 Parcial | Requer validação E2E | P0 |
| Employees | CRUD | Sim | Sim | 🟢 Base arquitetural migrada | Cubit agora passa por UseCase/Repository/DataSource; paridade funcional preservada | P1 |
| Employees | CRUD | Sim | Sim | 🟡 Parcial | Arquitetura ainda não alvo | P1 |
| Stock | Movimentações/QR/offline | Sim | Sim | 🟡 Parcial | Repository Pattern pendente | P1 |
| Deliveries | Entrega, assinatura, histórico | Sim | Sim | 🟡 Parcial | Testes E2E pendentes | P1 |
| Purchases | Solicitação/aprovação/recebimento | Sim | Sim | 🟡 Parcial | Matriz de fluxo pendente | P1 |
| Reports | Filtros/exportação | Sim | Sim | 🟡 Parcial | Performance e tenant a validar | P2 |
| Companies/Users | Administração | Sim | Sim | 🟡 Parcial | Paridade UX pendente | P2 |

## 9. Plano de testes

- Unitários: parsing de login/auth-me, SessionContext, route permissions e usecases.
- Widget: login, shell, menu por permissão, telas migradas.
- Integração: navegação pública/privada, refresh token, CRUD por módulo.
- Segurança: usuário sem permissão, usuário de outra empresa, usuário de outra unidade.
- API: contratos REST e envelopes `{success,data,message}`.
- Cobertura por módulo deve ser publicada no CI antes do go-live Flutter.

## 10. UX Web/Desktop e PlutoGrid

Recomendação: adoção gradual, não imediata em todos os módulos.

| Módulo | Benefício | Impacto | Complexidade | Recomendação |
| --- | --- | --- | --- | --- |
| Estoque | Alto para filtros e colunas | Médio | Média | Piloto |
| Funcionários | Alto para operações administrativas | Médio | Baixa | Após Employees repository |
| Compras | Alto para conferência | Alto | Alta | Após estabilizar fluxo |
| Relatórios | Alto para análise | Médio | Média | Após filtros tenant |
| Empresas/Usuários | Médio | Baixo | Baixa | Oportunista |

## 11. Checklist de Go-Live Flutter

- [ ] Flutter servido em `/app` com legado preservado em `/`.
- [ ] SessionContext usado por todos os módulos migrados.
- [ ] Rotas privadas exigem login e permissão.
- [ ] `/portal` e `/qr` validados sem autenticação quando o fluxo exigir.
- [ ] JWT/refresh testados em expiração e rotação.
- [ ] Testes negativos multi-tenant aprovados.
- [ ] Paridade por módulo aprovada pelo negócio.
- [ ] Observabilidade e logs de auditoria habilitados.
- [ ] Rollback documentado para frontend legado.

## 12. Evidência de execução automatizada

A execução do roadmap passa a ter uma auditoria estática versionada em `scripts/flutter_migration_audit.py`. Ela valida:

- Fundação: `SessionContext`, rotas públicas e guard de permissões.
- Multi-tenant: presença de autorização e indícios de escopo por empresa/unidade nos módulos executivos.
- Arquitetura Flutter: estrutura alvo `presentation/domain/data` para Employees, Stock, Deliveries, Purchases e Reports. Employees já possui Cubit, UseCases, Repository e DataSource nesta estrutura.
- Arquitetura Flutter: estrutura alvo `presentation/domain/data` para Employees, Stock, Deliveries, Purchases e Reports.

O teste `tests/test_flutter_migration_roadmap_audit.py` falha o CI quando algum guardrail do roadmap deixa de existir.
