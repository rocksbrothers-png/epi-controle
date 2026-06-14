# EPI SaaS — Visão Geral do Projeto

## Objetivo

Sistema SaaS multi-tenant de gestão de EPI (Equipamento de Proteção Individual) voltado para empresas brasileiras. Controla o ciclo de vida completo dos EPIs: cadastro, estoque, entrega, devolução, avaliação e relatórios, em conformidade com a NR-6 (Norma Regulamentadora nº 6 do MTE).

## Público-Alvo

| Perfil | Responsabilidade |
|--------|-----------------|
| master_admin | Administrador da plataforma SaaS (Rocks Brothers) |
| general_admin | Administrador geral da empresa contratante |
| registry_admin | Administrador de cadastros |
| admin | Administrador local de unidade |
| user | Gestor de EPI (operador) |
| buyer | Comprador |
| approver | Aprovador de compras |
| employee | Funcionário (portal de auto-serviço) |

## Plataformas

| Plataforma | Stack | Status |
|-----------|-------|--------|
| Web Admin (legado) | Python/Flask + HTML/JS vanilla | Produção |
| Mobile Admin | Flutter (iOS + Android) | Em desenvolvimento |
| Web Admin (Flutter Web) | Flutter Web servido em `/app/` | Em desenvolvimento |
| Portal do Funcionário | Flutter Web / HTML | Planejado |

## Módulos de Negócio

1. **Dashboard** — KPIs, alertas ativos, métricas de entrega
2. **Empresas** — Cadastro multi-tenant com white-label
3. **Unidades** — Hierarquia organizacional (matriz/filiais)
4. **Colaboradores** — Cadastro, ficha de EPI, histórico
5. **EPIs** — Catálogo com CA (Certificado de Aprovação), vencimentos
6. **Estoque** — Entradas, saídas, ajustes, inventário
7. **Entregas** — Entrega com assinatura digital e QR code
8. **Devoluções** — Controle de devoluções e descarte
9. **Fichas** — Ficha de EPI por colaborador (NR-6)
10. **Compras** — Solicitação, cotação, pedido, recebimento
11. **Alertas** — Estoque baixo, EPIs vencidos, CAs expirados
12. **Relatórios** — Relatórios exportáveis (PDF/Excel)
13. **Avaliações** — Avaliação de EPI com feedback do colaborador
14. **Configuração** — Configurações do sistema por empresa
15. **Comercial** — Contratos, licenças, faturamento (master_admin)

## Diferenciais

- **Multi-tenant com RLS**: isolamento total por empresa via Row-Level Security no PostgreSQL
- **Rule Engine**: motor de regras de visibilidade com rollout progressivo (off → shadow → canary → enforced)
- **OCR de datas**: leitura automática de data de fabricação em embalagens de EPI
- **Offline-first mobile**: Flutter com sincronização via Drift (SQLite local)
- **i18n nativo**: 5 idiomas (pt-BR, en-US, es-ES, fr-FR, nb-NO)
- **Feature flags**: controle granular de funcionalidades por empresa/usuário/ambiente

## Versão Atual

- Backend: Python 3.11 + PostgreSQL (Supabase)
- Frontend Web: Vanilla JS (fase de refatoração modular)
- Mobile: Flutter 3.24.5 / Dart 3.3+
- Deploy: Render.com via Docker multi-stage
