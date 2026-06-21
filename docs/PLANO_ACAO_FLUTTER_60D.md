# Plano de Ação Estratégico — Migração do Frontend para Flutter

> **Autor:** Arquitetura de Software (revisão sênior).
> **Data:** 2026-06-20.
> **Base factual:** varredura do repositório `rocksbrothers-png/epi-controle` (não de uma
> auditoria colada — o placeholder `[COLAR A AUDITORIA COMPLETA AQUI]` veio vazio, então este
> plano foi reancorado no **código real**). Complementa e atualiza:
> `docs/PLANO_MIGRACAO_FLUTTER_WEB.md`, `docs/PARITY_SHEETS.md` (de 2026-06-16),
> `docs/AUDITORIA_SISTEMA_2026-06-19.md`, `docs/UBX_MIGRATION_PLAN.md`.

---

## Nota importante sobre divergência com a auditoria anterior

O `PARITY_SHEETS.md` (16/06) listava **4 bloqueadores de cutover** do lado Flutter:
`EmployeesApi`, `EpisApi`, workflow de Compras (PO) e pipeline de Avaliações. **Esses
quatro já não são mais bloqueadores** — a varredura de hoje confirma que os clientes
existem em `flutter/packages/epi_api/lib/endpoints/`:

- `employees_api.dart`, `epis_api.dart` ✅ (CRUD cabeado);
- `purchases_api.dart` ✅ com `getPurchaseOrders/getPurchaseOrder/createPurchaseOrder/`
  `reviewPurchaseOrder/approvePurchaseOrder/receivePurchaseOrder/resubmitPurchaseOrder`;
- `feedback_api.dart` ✅ com pipeline completo (`triage/hseqReview/managerValidate/`
  `managerReject/adminDecision/preEvaluate/adminEvaluate/setReassessment/acceptSuggestion/close`).

Telas correspondentes existem: `employee_form_screen.dart`, `epi_form_screen.dart`,
`purchase_orders_screen.dart`, `receive_purchase_order_screen.dart`, etc.

**O novo bloqueador #1 (crítico, ainda aberto):** o `auth_interceptor.dart` **não faz
refresh de token**. O docstring diz "faz refresh automático em 401", mas o código apenas
**deleta o `access_token` e desloga**. O backend já expõe `POST /api/auth/refresh` e
`GET /api/auth/me` (PRs #590/#591), **não consumidos**. Hoje, toda expiração de token
derruba a sessão do usuário no Flutter — regressão direta de UX frente ao legado.

---

## 1. Diagnóstico Executivo

### 1.1 Maturidade e percentual de conclusão

| Frente | Estado | % concl. | Evidência |
|---|---|---|---|
| **Backend / API (contratos)** | Pronto | **~95%** | 18 módulos, ~192 handlers GET, `core/router.py`; 902 testes pytest passando; `send_api_response`/`/auth/*` prontos |
| **Coexistência legado + Flutter** | Em produção | **100%** | `/` legado, `/app/` Flutter, mesma API; Dockerfile multi-stage; redirect `/flutter_web`→`/app/` |
| **Infra de cutover** | Pronta e reversível | **100%** | flag `FLUTTER_WEB_ROOT_REDIRECT` (default OFF) |
| **Paridade funcional Flutter (telas + clientes)** | Quase completa | **~85%** | 18 domínios com tela; 16 clientes `epi_api`; PO e pipeline de feedback cabeados |
| **Autenticação Flutter (refresh/sessão)** | Incompleta | **~50%** | login OK; **refresh token não implementado**; `/auth/me` não consumido |
| **Hardening / testes Flutter** | Incipiente | **~15%** | só 5 `*_test.dart` + 1 smoke (`integration_test/smoke_test.dart`); CI roda `lint`+`test` mas cobertura baixíssima |
| **Mobile (Android/iOS)** | Pipeline pronto, release não validado | **~30%** | `deploy-android.yml`/`deploy-ios.yml` existem (exigem secrets); build APK debug no CI; sem evidência de release assinado/loja |
| **Arquitetura em camadas (UBX/clean)** | Não iniciada | **~10%** | `features/*` são telas planas; sem `domain/application/infrastructure/presentation/shared` |
| **Observabilidade Flutter** | Ausente | **~10%** | legado tem `error-monitor.js`; Flutter sem crash/telemetria equivalente |

> **Conclusão de maturidade:** a migração está em estágio **avançado** — o trabalho restante
> **não é construir**, é **endurecer, fechar a paridade de sessão, testar e fazer o cutover
> com segurança**. Percentual global estimado: **~75–80% concluído**.

### 1.2 Principais riscos

1. **Refresh token ausente no Flutter (CRÍTICO):** expiração de token = logout. Bloqueia o
   cutover — usuários reais perderiam sessão constantemente.
2. **Cobertura de testes Flutter quase nula:** cutover sem rede de segurança automatizada.
   O backend tem 902 testes; o Flutter tem ~5. Regressões de UI/fluxo passariam batido.
3. **Stale deploy / cold start (503 bootstrap):** já diagnosticado (auditoria 19/06, itens
   4–6). Não é bug de código — é redeploy + cold start do plano Render. Pode contaminar a
   percepção do cutover se não for resolvido antes.
4. **Mobile não validado em loja:** pipelines existem mas dependem de secrets e de um release
   assinado real; Android/iOS não estão comprovadamente publicáveis.
5. **Ausência de observabilidade no Flutter:** sem telemetria, o cutover fica "às cegas" —
   não há como medir taxa de erro por tela como o `__EPI_MONITORING__` do legado faz.

### 1.3 Principais gargalos

- **Ambiente:** este repositório é o backend; **não há Flutter SDK aqui** para `flutter
  test`/`build`. Toda entrega Dart precisa rodar no CI (`flutter.yml`) ou em ambiente Flutter.
- **Disciplina de paridade:** o padrão de bug "chave de resposta divergente" (`items` vs
  `companies`/`deliveries`) já mordeu duas vezes. Sem testes de contrato, volta.
- **Conhecimento concentrado no monólito `app.js`** (12k linhas) — a fonte de verdade do
  comportamento legado a ser replicado.

### 1.4 Dependências críticas

- Backend **congelado em contrato** durante a paridade (sem quebrar chaves de resposta).
- Secrets de assinatura mobile (`KEYSTORE_*`, `GOOGLE_PLAY_JSON_KEY`, certificados Apple).
- Redeploy estável no Render (resolver 503 de boot antes do cutover).
- Flag `FLUTTER_WEB_ROOT_REDIRECT` como ponto único de cutover/rollback.

### 1.5 Riscos para produção (hoje)

- Nenhum imediato enquanto a flag está OFF — `/` segue no legado. O legado é a rede de
  segurança. **O risco aparece no momento do cutover** e é mitigável (ver Fase 4).

---

## 2. Roadmap Estratégico

> Marcadores: ✅ feito · 🟡 em andamento · ⬜ pendente.

### Fase 0 — Correções Críticas (pré-cutover) ⬜ **caminho crítico**

| Item | Estado | Ação |
|---|---|---|
| **Refresh Token** | ⬜ | Implementar fila de refresh no `AuthInterceptor`: em 401, chamar `POST /api/auth/refresh`, reemitir a request original, e só deslogar se o refresh falhar. Persistir `refresh_token` no `flutter_secure_storage`. |
| **`GET /api/auth/me`** | ⬜ | Hidratar sessão/permissões no boot e após refresh, em vez de confiar só no payload de login. |
| **Permissões (RBAC)** | 🟡 | Garantir que o gate de rota Flutter usa as permissões do `/auth/me`/bootstrap (mesma matriz do backend). Consolidar a dívida do legado (`hasPermission` duplicado) **não** se propagou ao Flutter — validar. |
| **Rotas públicas** | 🟡 | Portal por token CPF (HMAC 48h) já existe; confirmar que `/app/` não exige Bearer nas rotas de portal e que o gate 503 isenta o necessário. |
| **Contratos de API** | 🟡 | Travar com **testes de contrato** as chaves de resposta usadas pelos 16 clientes (`items`/dict). Impede a recorrência do bug `items` vs `companies`. |

**Aceite Fase 0:** sessão sobrevive à expiração de token; nenhum 401 desloga indevidamente;
suíte de contrato verde; smoke de login→bootstrap→navegação sem erro de console.

### Fase 1 — Paridade Funcional 🟡 (~85% → 100%)

Estado por domínio (varredura de hoje):

| Domínio | Tela | Cliente API | Paridade | Pendência |
|---|---|---|---|---|
| Dashboard | ✅ | bootstrap | 🟡 | `pendingPurchases` (TODO no cubit) |
| Funcionários | ✅ (form+detail) | ✅ CRUD | ✅ | validar movimentações |
| EPIs | ✅ (form+detail) | ✅ CRUD | ✅ | — |
| Estoque | ✅ | ✅ | ✅ | — |
| Entregas | ✅ (+nova) | ✅ | ✅ | — |
| Devoluções | ✅ (+nova) | ✅ | ✅ | — |
| Compras | ✅ (PO+receber) | ✅ PO completo | ✅ | validar fluxo multinível ponta-a-ponta |
| Relatórios | ✅ | ✅ | 🟡 | botão "Exportar PDF" (`/api/reports.pdf`) |
| Portal | ✅ (home/sign) | ✅ | ✅ | — |
| QR Code | ✅ | n/a | 🟡 | validar scan em web/mobile |
| Configurações | ✅ | ✅ | 🟡 | conferir cobertura multi-tenant |
| Empresas | ✅ | ✅ | ✅ | — |
| Usuários | ✅ | ✅ | ✅ | — |
| Unidades | ✅ | ✅ | ✅ | — |
| Avaliações | ✅ | ✅ pipeline | ✅ | validar HSEQ→avaliação final E2E |

**Aceite Fase 1:** cada domínio com *parity sheet* 100% verde + 1 piloto real via `/app/`
sem fallback. Itens não-bloqueantes (PDF de relatório, `pendingPurchases`) podem ir pós-cutover.

### Fase 2 — Hardening ⬜ (maior gap atual)

- **Testes de widget** por tela crítica (login, dashboard, CRUDs, PO, pipeline de feedback).
- **Testes de integração** (`integration_test/`) expandindo o `smoke_test.dart`: login→cada
  domínio→operação→logout.
- **Testes de contrato** (Fase 0) mantidos no CI como gate.
- **Testes de regressão** dos bugs já corrigidos (i18n, `items` vs chave, ficha arquivada).
- **Testes de permissões:** matriz RBAC por papel × rota no Flutter.
- **Testes de carga:** k6/Locust contra os endpoints quentes (bootstrap, listas) — backend.
- **Testes mobile:** smoke em emulador Android + simulador iOS no CI (build já existe).
- **Meta de cobertura:** mínimo 60% em `epi_api` (lógica de parsing/clientes) e telas críticas.

### Fase 3 — Arquitetura em Camadas (UBX/Clean) ⬜ (refator gradual, pós-paridade)

Estrutura-alvo **por feature** (migração incremental, uma feature por PR, sem parar entregas):

```
features/<dominio>/
  domain/         entidades, value objects, contratos de repositório (puro Dart)
  application/    use cases / cubits (orquestração, sem detalhe de HTTP)
  infrastructure/ implementação de repositório sobre epi_api (Dio)
  presentation/   telas, widgets, mapeamento de estado→UI
packages/
  epi_shared/     erros, result types, i18n, design tokens (camada Shared)
```

**Estratégia sem interromper entregas:** _strangler_ por feature. Hoje os cubits chamam o
`epi_api` direto; introduzir a interface de repositório no `domain`, mover a chamada Dio para
`infrastructure`, e o cubit passa a depender da interface. Começar pela feature de **menor
risco já estável** (ex.: Unidades/Usuários) como referência, depois replicar. **Não fazer
antes da paridade e do cutover** — é higiene, não pré-requisito de Go-Live.

### Fase 4 — Cutover ⬜

- **Critérios de Go-Live:** Fase 0 fechada + Fase 1 100% + Fase 2 mínima (smoke E2E verde) +
  503 de boot resolvido + observabilidade básica ativa.
- **Canary:** ligar `FLUTTER_WEB_ROOT_REDIRECT` por **% de tenants** (ou por allowlist de
  empresa), começando por 1 empresa piloto interna.
- **Piloto:** janela de 1 ciclo de release com a empresa piloto 100% no `/app/`.
- **Métricas de sucesso:** taxa de erro por tela ≤ legado; tempo de login ≤ legado; 0
  logouts por expiração; nenhum fallback manual ao `/legacy/`.
- **Rollback:** desligar a flag → `/` volta ao legado **sem deploy**.

### Fase 5 — Desativação do Legado ⬜ (só após validação)

Sequência segura (cada passo um PR reversível, ≥1 release de espera entre eles):
1. `/` redireciona para `/app/` há ≥1 ciclo sem incidentes; `/legacy/` sem tráfego relevante.
2. Remover dependências de `static/index.html` em `/` → `static/views/` →
   `scripts/build_index.py` → `static/app.js`/`static/js/` → testes do legado → Dockerfile.
3. **Critério de remoção definitiva:** nenhum teste/rota/deploy depende do legado; Flutter é
   frontend único; manter tag/branch de arquivamento por retenção.

---

## 3. Backlog Priorizado

| Prioridade | Item | Impacto | Complexidade | Risco | Responsável |
|---|---|---|---|---|---|
| **Crítico** | Refresh token + `/auth/me` no `AuthInterceptor` | Alto | Média | Alto | Time Flutter |
| **Crítico** | Testes de contrato das chaves de resposta (16 clientes) | Alto | Baixa | Médio | Backend + Flutter |
| **Crítico** | Resolver 503 de boot / stale deploy (Render) | Alto | Baixa | Médio | DevOps |
| **Alto** | Smoke E2E por domínio (`integration_test/`) | Alto | Média | Médio | Time Flutter |
| **Alto** | Observabilidade Flutter (crash/telemetria por tela) | Alto | Média | Médio | Time Flutter |
| **Alto** | Testes de permissões (RBAC) por papel × rota | Alto | Média | Médio | Time Flutter |
| **Alto** | Validar PO multinível e pipeline de feedback E2E | Alto | Média | Médio | QA |
| **Médio** | Botão "Exportar PDF" em Relatórios (`/api/reports.pdf`) | Médio | Baixa | Baixo | Time Flutter |
| **Médio** | `pendingPurchases` no Dashboard | Médio | Baixa | Baixo | Backend + Flutter |
| **Médio** | Release mobile assinado (Android internal + iOS TestFlight) | Médio | Média | Médio | DevOps |
| **Médio** | Testes de carga (bootstrap/listas) | Médio | Média | Baixo | Backend |
| **Baixo** | Refator em camadas (UBX) — feature piloto | Médio | Alta | Baixo | Arquitetura |
| **Baixo** | Cache headers/CSP para `/app/` (Fase 3 residual) | Baixo | Baixa | Baixo | Backend |

---

## 4. Plano de Sprints (6 sprints × ~1 semana)

### Sprint 1 — Fundação de sessão (desbloqueio do cutover)
- **Objetivos:** eliminar o bloqueador crítico de autenticação.
- **Entregas:** refresh token com fila no `AuthInterceptor`; consumo de `/auth/me`;
  persistência segura de `refresh_token`; testes unitários do interceptor.
- **Aceite:** token expira → request é refeita transparentemente; falha de refresh → logout
  limpo; CI Flutter verde.
- **Dependências:** backend `/auth/refresh` + `/auth/me` (já prontos).

### Sprint 2 — Contratos e regressão
- **Objetivos:** travar a paridade de dados.
- **Entregas:** testes de contrato das chaves de resposta (16 clientes); testes de regressão
  dos bugs conhecidos (i18n, `items`, ficha arquivada); gate no `flutter.yml` + `node.js.yml`.
- **Aceite:** qualquer mudança de chave de resposta quebra o CI.
- **Dependências:** Sprint 1 (clientes estáveis).

### Sprint 3 — Smoke E2E + permissões
- **Objetivos:** rede de segurança de fluxo.
- **Entregas:** `integration_test/` cobrindo login→cada domínio→operação; matriz RBAC por
  papel; smoke em emulador Android no CI.
- **Aceite:** E2E verde para os 14 domínios; RBAC nega/permite igual ao backend.
- **Dependências:** Sprints 1–2.

### Sprint 4 — Observabilidade + estabilização de infra
- **Objetivos:** "ligar a luz" antes do cutover.
- **Entregas:** telemetria/crash por tela no Flutter (equivalente ao `__EPI_MONITORING__`);
  resolver 503 de boot (Render env/cold start); validar cache/CSP de `/app/`.
- **Aceite:** dashboard de erro por tela disponível; `/api/bootstrap` estável pós-deploy.
- **Dependências:** DevOps (Render).

### Sprint 5 — Canary + piloto
- **Objetivos:** cutover controlado.
- **Entregas:** `FLUTTER_WEB_ROOT_REDIRECT` por empresa (allowlist); 1 empresa piloto 100% no
  `/app/`; coleta de métricas; runbook de rollback.
- **Aceite:** piloto opera 1 ciclo sem incidente crítico; 0 logouts por expiração.
- **Dependências:** Sprints 1–4 fechadas.

### Sprint 6 — Expansão de cutover + mobile
- **Objetivos:** ampliar rollout e habilitar mobile.
- **Entregas:** rollout para % maior de tenants; release Android (internal) + iOS
  (TestFlight) assinados; checklist de prontidão revisado.
- **Aceite:** maioria dos tenants no `/app/` sem regressão; build mobile publicável.
- **Dependências:** secrets de assinatura.

> A **refatoração UBX (Fase 3)** entra como trilha paralela de baixa prioridade a partir do
> Sprint 4, **uma feature por PR**, sem bloquear o cutover.

---

## 5. Critérios de Prontidão para Produção (checklist)

### Backend
- [x] 902 testes pytest passando.
- [x] Roteamento modular (`core/router.py`) + `HANDLED` sentinel (sem resposta dupla).
- [ ] 503 de boot estável pós-redeploy (item infra).
- [ ] Testes de contrato das respostas consumidas pelo Flutter.

### Flutter Web
- [ ] Refresh token funcional (bloqueador).
- [ ] Smoke E2E dos 14 domínios.
- [ ] i18n 5 idiomas paridade (ARB validado no CI ✅).
- [ ] Observabilidade por tela.

### Android
- [x] Build APK debug no CI.
- [ ] Build assinado (keystore) + upload internal.
- [ ] Smoke em emulador no CI.

### iOS
- [x] Pipeline `deploy-ios.yml` definido.
- [ ] Certificados/perfis configurados (secrets).
- [ ] Build TestFlight validado.

### CI/CD
- [x] `flutter.yml` (analyze+test+build), `node.js.yml` (pytest), deploy mobile.
- [ ] Gate de contrato + cobertura mínima.
- [ ] Gate de E2E mobile.

### Segurança
- [x] Advisors Supabase: 0 alertas.
- [x] Portal por token HMAC (48h).
- [ ] Revisão de CSP cobrindo `/app/`.
- [ ] Storage seguro de tokens validado (secure storage por plataforma).

### Banco de Dados
- [x] 92 índices de FK criados (advisor 92→0).
- [x] Migrações idempotentes (`app_migrations`).

### Observabilidade
- [ ] Telemetria de erro por tela no Flutter.
- [ ] Métricas de cutover (taxa de erro, tempo de login, fallbacks).

### Multi-Tenant
- [x] Escopo por empresa no backend (testado).
- [ ] Troca de empresa validada no Flutter (todas as telas).

### Performance
- [ ] Testes de carga em bootstrap/listas.
- [ ] Cache headers de assets `/app/` (hash) vs `no-cache` do HTML.

---

## 6. Arquitetura Recomendada — A ou B

**Decisão: opção B — finalizar a migração Flutter e só depois aposentar o legado.**

Justificativa técnica:
1. **O Flutter já está ~80% pronto** e em produção em `/app/`; o legado tem **12.369 linhas
   em um único closure** (`app.js`), cuja fatoração (UBX) é alto esforço e **só serve para
   manter vivo um frontend que será desligado**. Investir em B é investir no destino;
   investir em A é melhorar algo descartável.
2. O backend já expõe **100% das APIs** e os 16 clientes Flutter existem — o custo marginal
   para fechar paridade é baixo frente a refatorar o monólito JS.
3. **Redução de risco:** o legado permanece **congelado e intacto** como rede de segurança
   (rollback por flag, sem deploy). Não precisamos torná-lo bonito; precisamos mantê-lo
   estável até o cutover.
4. A fatoração do `app.js` (doc `UBX_MIGRATION_PLAN.md`) deve ser **suspensa/minimizada** —
   só corrigir o que for necessário para manter o legado operacional, nada de refator amplo.

> **Exceção:** a "arquitetura UBX" no sentido de **clean architecture do app Flutter**
> (Fase 3 deste plano) **vale a pena**, mas só **depois** da paridade e do cutover, de forma
> incremental. Não confundir com refatorar o `app.js` legado (não recomendado).

---

## 7. Matriz de Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Refresh token ausente derruba sessão | Alta | Alto | Sprint 1 (fila de refresh + `/auth/me`); gate de cutover depende disso |
| Regressão por chave de resposta divergente | Média | Alto | Testes de contrato (Sprint 2) como gate de CI |
| Cobertura de testes Flutter insuficiente | Alta | Alto | Smoke E2E + widget tests (Sprints 2–3); meta 60% |
| 503 de boot percebido como falha do Flutter | Média | Médio | Resolver cold start/env no Render antes do canary (Sprint 4) |
| Mobile não publicável (secrets/assinatura) | Média | Médio | Validar release internal/TestFlight cedo (Sprint 6); não bloqueia web |
| Cutover sem observabilidade ("voar às cegas") | Média | Alto | Telemetria por tela antes do canary (Sprint 4) |
| Refator UBX atrasa entregas | Baixa | Médio | Pós-cutover, 1 feature/PR, trilha paralela de baixa prioridade |
| Divergência de permissões Flutter × backend | Baixa | Alto | Testes de RBAC por papel × rota (Sprint 3) |
| Multi-tenant com vazamento entre empresas | Baixa | Crítico | Reuso do escopo do backend (testado) + teste de troca de empresa no Flutter |

---

## 8. Plano Final de Execução — próximos 60 dias

**Princípio condutor:** *paridade + sessão estável → testes → observabilidade → cutover
canário → expansão*. Refator arquitetural só depois. Legado intocado como rollback.

### Dias 1–10 (Sprint 1) — Desbloquear a sessão
1. Implementar refresh token (fila no `AuthInterceptor`) + `refresh_token` em secure storage.
2. Consumir `GET /api/auth/me` no boot e pós-refresh; hidratar permissões.
3. Testes unitários do interceptor; CI Flutter verde.
4. **Gate:** nenhum 401 desloga indevidamente.

### Dias 11–20 (Sprint 2) — Travar contratos
5. Testes de contrato das chaves de resposta dos 16 clientes; adicionar ao CI.
6. Testes de regressão dos bugs conhecidos (i18n, `items`, ficha arquivada).
7. Fechar follow-ups não-bloqueantes baratos: PDF de relatório, `pendingPurchases`.

### Dias 21–30 (Sprint 3) — Rede de segurança de fluxo
8. Expandir `integration_test/` para os 14 domínios (login→operação→logout).
9. Matriz de permissões (RBAC) por papel × rota.
10. Smoke em emulador Android no CI.

### Dias 31–40 (Sprint 4) — Acender a luz + estabilizar infra
11. Telemetria/crash por tela no Flutter (paridade com `__EPI_MONITORING__`).
12. DevOps: resolver 503 de boot (cold start/env no Render); validar cache/CSP de `/app/`.
13. Definir métricas e dashboard de cutover.

### Dias 41–50 (Sprint 5) — Canary + piloto
14. Ligar `FLUTTER_WEB_ROOT_REDIRECT` por allowlist; 1 empresa piloto 100% no `/app/`.
15. Operar 1 ciclo de release; coletar métricas; manter runbook de rollback à mão.
16. **Gate de Go-Live ampliado:** erro por tela ≤ legado, 0 logouts por expiração.

### Dias 51–60 (Sprint 6) — Expandir + mobile
17. Ampliar cutover para % maior de tenants conforme métricas.
18. Release mobile assinado: Android internal + iOS TestFlight.
19. Iniciar trilha paralela UBX (1 feature piloto) — sem bloquear nada.
20. Revisar checklist de prontidão e planejar a **Fase 5 (desativação do legado)** para o
    ciclo seguinte (não nos 60 dias).

---

## Trilha MOBILE — Prontidão para Play Store / App Store (M0–M5)

Pré-requisito do **item 18** (release mobile). Detalhe e evidências em
`docs/AUDITORIA_PUBLICACAO_MOBILE.md`. Bloqueadores de loja primeiro; não afetam o Web em `/app`.

| Fase | Correção | Tipo | Bloqueia |
|---|---|---|---|
| **M0** | Remover permissão de **localização** não usada (Android + iOS) | cfg | AAB + App Store |
| **M1** | Criar `PrivacyInfo.xcprivacy` + `Runner.entitlements` (APNs) | cfg | App Store |
| **M2** | Política de Privacidade + Termos + suporte (URLs) | legal | ambas |
| **M3** | Formulários Data Safety (Google) + App Privacy (Apple) + IARC | console | ambas |
| **M4** | Ícone + screenshots + descrições | console | ambas |
| **M5** | Build `appbundle`/`ios` release + smoke em device real + gate de rejeição | qa | Go-Live mobile |

> Status de prontidão (auditoria 2026-06-21): APK de teste 🟢 · AAB 🟡 (falta M0+M2+M3) ·
> App Store 🔴 (falta M0+M1+M2+M3). App é **Flutter nativo sem WebView** (risco 4.2 Apple baixo).
> **M0/M1** mexem em config Android/iOS (baixo risco) e aguardam autorização; **M2–M4** dependem do
> negócio; **M5** exige devices reais.

---

## Restrições respeitadas
- ✅ Sem reescrever o backend (apenas testes de contrato + ajustes de infra).
- ✅ Sem trocar de framework frontend (Flutter é definitivo).
- ✅ Paridade funcional **antes** de qualquer refator arquitetural profundo (UBX só na Fase 3).
- ✅ Prioridade total à redução de risco (legado congelado como rollback por flag).
</invoke>
