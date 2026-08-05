# Papéis e Atribuições do Sistema

> Documento de referência canônico. Esta separação deve orientar as
> permissões (`core/permissions.py`), as rotas, os menus, as telas e os
> testes de autorização do sistema — em ambos os repositórios
> (`epi-controle-app` e o espelho `epi-controle`).
>
> Origem: especificação fornecida pelo responsável do produto em 2026-07-28,
> após o bug em que o Gestor de EPI enxergava a aba CNPJs (gestão que não é
> dele). Ver `core/permissions.py` (`PERMISSIONS['user']`, `PERMISSIONS['admin']`)
> para o estado implementado e `tests/test_legal_entities_tab_visibility.py`
> para o primeiro caso fixado a partir deste documento.

A estrutura abaixo separa claramente as funções administrativas,
operacionais e de controle. O objetivo é evitar sobreposição de
responsabilidades, proteger a auditoria e garantir que cada perfil veja
apenas o que precisa para trabalhar.

## Mapa de nomes: papel do negócio → `role` no código

| Papel do negócio | `role` (`core/permissions.py`) |
|---|---|
| Admin Master da plataforma | `master_admin` |
| Administrador Geral | `general_admin` |
| Administrador de Registro | `registry_admin` |
| Administrador Local | `admin` |
| Gestor de EPI | `user` |
| Comprador | `buyer` |
| Aprovador | `approver` |
| Colaborador | `employee` |

## 1. Admin Master da plataforma

É o administrador da plataforma SaaS. Atua sobre clientes, planos, recursos
globais e infraestrutura, mas não participa da rotina operacional de entrega
de EPIs.

**Atribuições**
- Criar e administrar clientes ou tenants.
- Criar o primeiro usuário responsável da empresa. No sistema SaaS é criar o
  primeiro usuário automaticamente quando o cliente compra uma conta pela
  internet, pelo website oficial.
- Configurar planos baseados na quantidade de usuários.
- Administrar licenças.
- Configurar domínios e subdomínios.
- Configurar recursos globais da plataforma.
- Gerenciar integrações da plataforma.
- Acompanhar uso, disponibilidade e auditoria global.
- Prestar suporte técnico.
- Ativar ou desativar funcionalidades globais.
- Gerenciar parâmetros gerais que afetam todos os clientes.

**Não faz**
- Não cadastra colaboradores da operação do cliente.
- Não aprova solicitações de EPI.
- Não cria requisições de compra operacionais.
- Não entrega EPI.
- Não movimenta estoque.
- Não substitui os administradores internos da empresa.

Estas restrições são permanentes no papel (`core/permissions.py`), não
apenas recomendações de uso: o Administrador Master não retém
`employees:create/update/delete`, `deliveries:create`, `stock:adjust` nem
`purchase_requests:create/update` (decisão confirmada em 2026-07-29).
Quando o suporte à plataforma exigir agir sobre dados operacionais do
cliente, isso deve passar por um mecanismo formal de impersonation ou
acesso temporário auditado — ainda não implementado — nunca por concessão
permanente no papel.

## 2. Administrador Geral

É o responsável máximo pela administração do cliente dentro da plataforma.
Ele controla a estrutura organizacional, os perfis, as configurações gerais
e a visão consolidada da empresa.

**Atribuições — Estrutura da organização**
- Cadastrar e administrar a empresa.
- Cadastrar e administrar múltiplos CNPJs.
- Criar, editar, ativar e desativar unidades.
- Vincular cada unidade ao CNPJ correto.
- Organizar a estrutura da empresa.
- Visualizar a hierarquia completa da organização.
- Definir os responsáveis por cada unidade.

**Usuários e permissões**
- Criar usuários administrativos.
- Atribuir perfis.
- Definir carteiras de unidades.
- Ativar, bloquear ou desativar acessos.
- Definir permissões complementares.
- Criar Administradores de Registro.
- Criar Administradores Locais.
- Criar Gestores de EPI.
- Criar Compradores.
- Criar Aprovadores.

**Configurações**
- Configurar os métodos de confirmação de entrega.
- Habilitar assinatura digital.
- Habilitar biometria nativa do dispositivo.
- Habilitar biometria externa.
- Definir método principal e contingência.
- Configurar políticas de estoque.
- Configurar regras de aprovação.
- Configurar regras de compra.
- Configurar parâmetros gerais da empresa.
- Administrar integrações.

**Gestão e acompanhamento**
- Visualizar indicadores consolidados.
- Consultar auditorias.
- Acompanhar unidades, CNPJs, usuários, solicitações, compras e estoques.
- Supervisionar o funcionamento geral do sistema.
- Corrigir configurações organizacionais quando necessário.

**Não faz normalmente**

O Administrador Geral pode possuir permissões amplas, mas não deve ser
obrigado a executar a rotina diária de:
- entrega de EPI;
- separação de materiais;
- baixa física de estoque;
- cadastro operacional diário de colaboradores;
- aprovação diária de todas as solicitações.

Essas funções devem ser delegadas aos perfis responsáveis.

## 3. Administrador de Registro

É o responsável pelos cadastros gerais da organização e pelo controle
cadastral dos colaboradores. Ele auxilia diretamente o Administrador Geral
na manutenção dos dados organizacionais e cadastrais.

**Atribuições — Cadastro de colaboradores**
- Cadastrar colaboradores.
- Atualizar dados cadastrais.
- Corrigir informações pessoais e profissionais.
- Atualizar matrícula.
- Atualizar cargo.
- Atualizar função.
- Atualizar setor.
- Atualizar centro de custo.
- Atualizar data de admissão.
- Registrar desligamento.
- Reativar colaborador, quando permitido.
- Registrar afastamentos, quando o sistema contemplar essa informação.
- Atualizar status ativo ou inativo.

**Movimentação organizacional do colaborador**
- Transferir colaborador entre unidades.
- Alterar vínculo com CNPJ.
- Alterar setor.
- Alterar função.
- Alterar local de trabalho.
- Registrar mudança de atividade.
- Registrar mudança de risco.
- Registrar mudança de gestor.
- Registrar mudança que possa impactar o perfil de EPI.

Essas alterações devem gerar histórico e auditoria.

**Cadastros gerais da organização**

O Administrador de Registro pode auxiliar o Administrador Geral em
cadastros como: setores, departamentos, cargos, funções, centros de custo,
grupos de colaboradores, turnos, equipes, locais de trabalho, atividades,
riscos, vínculos organizacionais e dados complementares da estrutura.

**Importação e saneamento de dados**
- Importar colaboradores por planilha.
- Validar dados obrigatórios.
- Tratar duplicidades.
- Corrigir inconsistências cadastrais.
- Conferir vínculos com unidade e CNPJ.
- Acompanhar erros de importação.
- Manter a qualidade da base cadastral.

**Consulta e auditoria**
- Consultar histórico cadastral.
- Visualizar alterações realizadas.
- Identificar quem alterou determinado dado.
- Consultar colaboradores por unidade, setor, função ou status.
- Gerar relatórios cadastrais, quando permitido.

**Pode**
- Administrar os cadastros das unidades incluídas em sua carteira.
- Auxiliar o Administrador Geral em cadastros organizacionais.
- Corrigir dados que impactam os fluxos de EPI.
- Atualizar informações de colaboradores já existentes.

**Não faz**
- Não aprova solicitações de EPI.
- Não cria requisições de compra.
- Não aprova compras.
- Não entrega EPI.
- Não movimenta estoque físico.
- Não realiza baixa de estoque.
- Não altera configurações globais da empresa, salvo permissão adicional.
- Não cria novos perfis de acesso, salvo autorização expressa.

O Administrador de Registro mantém apenas as permissões de cadastro
organizacional (`employees:create/update/delete` — arquivamento lógico,
nunca exclusão física — e `employees:transfer`); as permissões
operacionais de compra (`purchase_requests:create/update`,
`purchase_orders:review/receive`) e de estoque (`stock:adjust`,
`deliveries:create`) foram removidas do papel (decisão confirmada em
2026-07-29). A consulta a requisições/pedidos de compra permanece, para
relatórios cadastrais.

## 4. Administrador Local

É o responsável administrativo por exatamente uma unidade — vínculo único,
nunca uma carteira de N unidades (decisão confirmada em 2026-07-29; ver
`actor_operational_unit_id`). Ele controla solicitações, necessidades de
compra, aprovações e acompanhamento administrativo do estoque, mas não
realiza o cadastro dos colaboradores. Se tentar acessar outra unidade,
mesmo do mesmo CNPJ, o backend nega o acesso.

**Atribuições — Solicitações de EPI**
- Receber solicitações dos colaboradores.
- Analisar solicitações.
- Aprovar solicitações.
- Rejeitar solicitações.
- Solicitar correção ou complementação.
- Registrar justificativas.
- Acompanhar o status das solicitações.
- Consultar histórico.
- Identificar solicitações aguardando estoque.
- Identificar solicitações bloqueadas.
- Encaminhar demandas para atendimento.

**Solicitações geradas pelo estoque**
- Receber alertas de estoque mínimo.
- Analisar necessidades de reposição.
- Validar necessidades geradas pelo sistema.
- Criar ou confirmar requerimentos de compra.
- Acompanhar requisições originadas pelo estoque.
- Verificar itens críticos.
- Priorizar necessidades da unidade.

**Requerimentos de compra**
- Criar requisições de compra.
- Informar unidade solicitante.
- Informar item, quantidade e justificativa.
- Anexar documentos, quando necessário.
- Encaminhar requisições ao comprador.
- Acompanhar o andamento.
- Responder solicitações de ajuste.
- Consultar aprovação ou rejeição.
- Acompanhar recebimento.

**Acompanhamento de estoque**
- Consultar saldo físico.
- Consultar saldo reservado.
- Consultar saldo disponível.
- Consultar itens abaixo do mínimo.
- Consultar itens aguardando compra.
- Consultar itens próximos do vencimento.
- Consultar movimentações.
- Visualizar indicadores da unidade.
- Identificar falta de material.
- Solicitar compra ou transferência formal.

O Administrador Local acompanha e gerencia administrativamente o estoque,
mas não realiza a movimentação física.

**Gestão da unidade**
- Acompanhar indicadores operacionais.
- Consultar auditorias da unidade.
- Acompanhar solicitações pendentes.
- Acompanhar compras.
- Acompanhar entregas.
- Acompanhar necessidades geradas por mudanças dos colaboradores.
- Administrar apenas a própria unidade.
- Transferir colaboradores da própria unidade para outra unidade.

**Não faz**
- Não cadastra colaboradores.
- Não atualiza cadastro de colaboradores.
- Não entrega EPI.
- Não captura assinatura.
- Não captura biometria.
- Não realiza baixa física.
- Não recebe fisicamente material.
- Não altera usuários ou permissões.
- Não administra CNPJs.

## 5. Gestor de EPI

É o responsável pela operação física do estoque e pela entrega dos EPIs aos
colaboradores. Ele controla o almoxarifado, as reservas, a separação, a
entrega, as devoluções e os efeitos das mudanças organizacionais sobre os
EPIs.

**Atribuições — Controle de estoque**
- Controlar saldo físico.
- Controlar saldo reservado.
- Controlar saldo disponível.
- Controlar lotes.
- Controlar CA.
- Controlar datas de validade.
- Controlar tamanhos e variações.
- Controlar localização física.
- Conferir divergências.
- Realizar ajustes autorizados.
- Acompanhar estoque mínimo.
- Identificar materiais críticos.

**Recebimento**
- Receber materiais.
- Conferir quantidades.
- Conferir item, tamanho, lote e CA.
- Registrar divergências.
- Registrar recebimento parcial ou total.
- Confirmar entrada na unidade correta.
- Imprimir ou associar QR Code.
- Organizar o material recebido.

**Reserva**
- Reservar itens para solicitações aprovadas.
- Conferir disponibilidade.
- Impedir reserva acima do saldo disponível.
- Manter reserva vinculada à unidade.
- Liberar reserva cancelada.
- Ajustar reserva quando permitido.
- Acompanhar reservas pendentes.

A reserva não baixa o estoque físico. Ela apenas reduz o saldo disponível
para novas promessas.

**Separação e entrega**
- Separar os EPIs.
- Preparar a entrega.
- Conferir colaborador.
- Conferir solicitação.
- Conferir quantidade.
- Conferir unidade.
- Realizar a entrega.
- Capturar confirmação de recebimento.
- Finalizar a entrega.
- Executar a baixa física.
- Encerrar ou atualizar a solicitação.

**Confirmação de recebimento**

Conforme a configuração da empresa, o Gestor de EPI poderá usar:
- assinatura digital;
- biometria nativa do dispositivo;
- biometria externa por impressão digital;
- biometria externa facial;
- método alternativo configurado.

A confirmação deve ficar vinculada à entrega e à auditoria.

**Atendimento parcial**

O atendimento parcial nunca ocorre automaticamente. O Gestor de EPI poderá
autorizar atendimento parcial apenas quando:
- houver saldo insuficiente para o total;
- a empresa permitir esse tipo de decisão;
- a quantidade parcial for informada;
- a justificativa for obrigatória;
- a ação ficar auditada.

O sistema deve manter registrada a quantidade pendente.

**Gestão de mudança**

O Gestor de EPI acompanha alterações que impactam os equipamentos do
colaborador, como: mudança de função, mudança de setor, mudança de
atividade, mudança de risco, mudança de unidade, alteração de exposição,
necessidade de substituição de EPI, devolução de itens anteriores, entrega
de novos itens, mudança do conjunto obrigatório de EPIs.

O Administrador de Registro atualiza os dados do colaborador. O Gestor de
EPI trata o impacto operacional dessa mudança sobre os EPIs.

**Devoluções, trocas e substituições**
- Registrar devolução.
- Conferir condição do item.
- Registrar troca.
- Registrar perda.
- Registrar dano.
- Registrar substituição.
- Registrar descarte.
- Atualizar histórico do colaborador.
- Movimentar o estoque conforme a regra aplicável.

**Não faz**
- Não cadastra colaboradores.
- Não altera dados cadastrais.
- Não aprova compras.
- Não cria usuários.
- Não altera permissões.
- Não administra a estrutura da empresa.
- Não consome estoque de outra unidade sem transferência formal.

## 6. Comprador

É o responsável pelo processo de aquisição dos EPIs e materiais. Pode
atender várias unidades, mas toda compra continua vinculada à unidade
solicitante.

**Atribuições**
- Receber requisições de compra.
- Conferir unidade solicitante.
- Conferir CNPJ.
- Conferir item e quantidade.
- Solicitar cotações.
- Cadastrar ou selecionar fornecedores.
- Comparar propostas.
- Negociar condições.
- Registrar preços.
- Registrar prazos.
- Criar pedido de compra.
- Acompanhar aprovação.
- Acompanhar entrega do fornecedor.
- Tratar divergências comerciais.
- Consultar histórico de compras.
- Administrar compras das unidades de sua carteira.

**Pode**
- Consolidar a visualização das necessidades autorizadas.
- Filtrar por unidade.
- Filtrar por CNPJ.
- Acompanhar várias unidades.
- Agrupar cotações, quando a regra permitir.

**Não faz**
- Não aprova a própria compra, salvo regra excepcional formal.
- Não entrega EPI.
- Não baixa estoque.
- Não reserva material.
- Não aprova solicitação de colaborador.
- Não altera cadastro do colaborador.
- Não usa saldo de uma unidade para atender outra.

## 7. Aprovador

É o responsável pela aprovação administrativa ou financeira das compras.
Pode possuir uma carteira com várias unidades e diferentes níveis de
alçada.

**Atribuições**
- Receber solicitações de aprovação.
- Conferir requisição.
- Conferir unidade e CNPJ.
- Conferir justificativa.
- Conferir valor.
- Conferir quantidade.
- Conferir fornecedor.
- Conferir cotações.
- Aprovar.
- Rejeitar.
- Solicitar ajuste.
- Registrar justificativa.
- Respeitar limites de alçada.
- Consultar histórico.
- Acompanhar decisões anteriores.
- Visualizar apenas unidades autorizadas.

**Não faz**
- Não entrega EPI.
- Não movimenta estoque.
- Não cadastra colaborador.
- Não cria requisição em nome da unidade.
- Não altera usuários.
- Não altera configurações da empresa.

## 8. Colaborador

É o usuário final que solicita, recebe e acompanha seus EPIs.

**Atribuições**
- Solicitar EPI.
- Informar tamanho, quando necessário.
- Informar motivo da solicitação.
- Solicitar troca.
- Solicitar reposição.
- Informar perda.
- Informar dano.
- Consultar o status da solicitação.
- Consultar histórico de entregas.
- Consultar itens recebidos.
- Consultar pendências.
- Receber avisos.
- Confirmar o recebimento.
- Assinar digitalmente.
- Utilizar biometria, quando configurada.

**Visualização**

O colaborador deve visualizar apenas: seus próprios dados permitidos, suas
solicitações, suas entregas, seus EPIs, suas pendências e seu histórico.

**Não faz**
- Não aprova solicitações.
- Não cria requisição de compra.
- Não movimenta estoque.
- Não consulta dados de outros colaboradores.
- Não altera sua unidade ou função diretamente.
- Não cria ou altera usuários.

## Fluxo geral do sistema

```
Administrador de Registro
cadastra ou atualiza o colaborador
        │
        ▼
Colaborador
solicita o EPI
        │
        ▼
Administrador Local
analisa e aprova ou rejeita
        │
        ▼
Verificação do estoque da unidade
        │
   ┌────┴────┐
   │         │
Tem saldo   Não tem saldo
   │         │
   ▼         ▼
Gestor      Administrador Local
de EPI      cria requerimento de compra
   │         │
   │         ▼
   │      Comprador
   │         │
   │         ▼
   │      Aprovador
   │         │
   │         ▼
   │      Pedido de compra
   │         │
   │         ▼
   └──── Recebimento na unidade
             │
             ▼
        Gestor de EPI
   reserva → separa → entrega
             │
             ▼
 assinatura ou biometria
             │
             ▼
      baixa física do estoque
             │
             ▼
 histórico do colaborador
```

## Separação central entre os perfis

```
Administrador de Registro
→ cadastra e atualiza colaboradores e dados organizacionais

Administrador Local
→ aprova solicitações, cria requerimentos de compra e acompanha o estoque

Gestor de EPI
→ controla fisicamente o estoque e realiza as entregas

Comprador
→ conduz o processo de aquisição

Aprovador
→ aprova ou rejeita a compra

Administrador Geral
→ administra a empresa, sua estrutura, usuários e configurações

Admin Master
→ administra a plataforma SaaS
```

Essa distribuição deve orientar as permissões, as rotas, os menus, as
telas e os testes de autorização do sistema.

## Política de acesso: regra padrão + personalização por módulo

Além da permissão técnica individual (seção anterior), o sistema tem uma
segunda camada — **visibilidade estrutural por módulo** (menu lateral, menu
inferior, rotas, deep links) — que o **Administrador Geral** pode
personalizar por tenant em **Configuração → Regras → Visualização →
Visibilidade por Módulo**. É a mesma tela e o mesmo armazenamento já usados
pela visibilidade por Unidade/Colaborador (nenhuma tabela nova).

A decisão final de acesso combina cinco fatores, nesta ordem:

```
Acesso Final = Regra Padrão AND Configuração Administrativa AND Permissões Técnicas AND Escopo AND Backend
```

- **Regra Padrão**: visibilidade de cada módulo computada a partir da
  permissão técnica do perfil (`core/permissions.py`), com uma exceção
  explícita: Comprador e Aprovador continuam sem acesso estrutural a
  Estoque, Entregas e Fichas de EPI mesmo tendo `stock:view`/
  `deliveries:view` como apoio à decisão de compra.
- **Configuração Administrativa**: override por tenant que o Administrador
  Geral grava na tela acima. Pode restringir ou liberar um módulo, **nunca**
  além do que a permissão técnica do perfil autoriza.
- **Permissões Técnicas**: o teto. `resolve_module_visibility()` sempre
  reclampa `configuração AND permissão_técnica` — é estruturalmente
  impossível a configuração conceder um módulo sem a permissão
  correspondente (`tests/test_module_visibility_negative_authz.py` trava
  isso por prova estrutural e comportamental).
- **Escopo**: tenant/empresa/CNPJ/unidade, já aplicado pelas regras
  existentes (`actor_operational_unit_id`, `ensure_resource_company`,
  `ensure_actor_employee_scope` etc.) — inalterado por esta camada.
- **Backend**: autoridade final. Esta política é **só de navegação**
  (menu/rotas/deep links, Web e Flutter); nenhuma rota de dados passa a
  confiar nela para autorizar leitura/escrita — a autorização real continua
  exclusivamente nas rotas de API, gateadas por `ensure_permission`/
  `authorize_action`, sem qualquer acoplamento a `module_visibility`.

### Matriz oficial

| Perfil | Dashboard | Compras | Estoque | Entregas | Solicitações | Fichas de EPI | Relatórios | Administração | Configurações |
|---|---|---|---|---|---|---|---|---|---|
| Admin Master | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Administrador Geral | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Administrador de Registro | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Administrador Local | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Gestor de EPI | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Comprador | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Aprovador | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Colaborador | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Esta é a **visibilidade padrão do sistema** (`default_framework_payload()`
em `epi_backend/rule_engine.py`) — o ponto de partida antes de qualquer
override do Administrador Geral. Colaborador não usa esta matriz porque
opera pelo Portal externo (token), fora da navegação estrutural do
`epi_admin`/web legado.

Permissão técnica mínima exigida por módulo — o teto que a configuração
nunca ultrapassa (`MODULE_REQUIRED_PERMISSIONS` em `rule_engine.py`):

| Módulo | Permissão técnica exigida (qualquer uma) |
|---|---|
| Dashboard | `dashboard:view` |
| Compras | `purchase_requests:view` ou `purchase_orders:view` |
| Estoque | `stock:view` |
| Entregas | `deliveries:view` |
| Solicitações | `purchase_requests:view` |
| Fichas de EPI | `fichas:view` |
| Relatórios | `reports:view` |
| Administração | `users:view`, `companies:view` ou `legal_entities:view` |
| Configurações | `settings:view` |

**Configurável pelo Administrador Geral** (restringir ou liberar dentro do
teto técnico): todos os módulos acima, por perfil, por tenant, via
`GET/POST /api/module-visibility`. Cada alteração é auditada
(`company_audit_logs`, evento `visibility_config_updated`, com tenant/
empresa, perfil, módulo, unidade (quando aplicável), estado anterior, novo
estado, admin responsável e data/hora).

**Override por Unidade**: para os perfis `admin` (Administrador Local) e
`user` (Gestor de EPI) — os únicos com vínculo de unidade única —
`POST /api/module-visibility` aceita um `unit_id` opcional para gravar a
configuração num bucket específico da unidade em vez do bucket padrão
(`"*"`). Um módulo ausente do bucket da unidade herda o valor do bucket
`"*"` do mesmo perfil. `unit_id` para um perfil fora de `admin`/`user`, ou
para uma unidade fora do tenant do ator, é rejeitado (`ValueError` → HTTP
400). `module_visibility` é a única fonte de verdade para
`tenant + perfil + unidade + módulo` — não existe mais um mecanismo
paralelo (`module_unit_scope` foi retirado no PR18).

**Escopo da configuração**: por tenant (`company_id`), reaproveitando a
mesma chave `configuration_framework:{company_id}` já usada pela
visibilidade por Unidade/Colaborador. Administrador Geral e Administrador
de Registro operam sempre na própria empresa; Admin Master sem seleção
explícita de empresa grava no escopo `global` (mesma limitação pré-existente
da aba de regras por unidade).

**Web Legado (admin UI)**: Configuração → Regras → Visualização →
"Visibilidade por Módulo" (`static/views/configuracao.html`). Um seletor de
Unidade (`#module-visibility-unit`) aparece só quando o perfil selecionado
está em `MODULE_VISIBILITY_UNIT_SCOPED_ROLES` (espelha `_UNIT_SCOPED_ROLES`
do backend — `admin`/`user`); com "Todas as unidades" (padrão) grava no
bucket `"*"`, com uma Unidade específica grava no bucket daquela unidade.
As checkboxes exibem o valor efetivo (`moduleVisibilityEffectiveValue`,
mesma regra de fallback do backend). Isto corrige uma regressão silenciosa
introduzida pelo PR18: as checkboxes liam `roleConfig[moduleKey]`
diretamente, formato que deixou de existir quando `module_visibility`
passou a ser aninhado por bucket — toda checkbox aparecia sempre marcada,
independentemente do valor salvo.

**Regra Flutter**: `NavigationPolicy`
(`flutter/apps/epi_admin/lib/core/router/navigation_policy.dart`) — mapa
`routeModules` (rota → módulo) e `isModuleLocationAccessible()`, único
ponto de verdade consumido por três lugares: o `redirect` do `GoRouter`
(cobre navegação direta por URL e deep link, não só clique no menu), o
menu lateral (`AppShell`) e os atalhos do FAB no dashboard. `module_visibility`
chega ao app no login, em `/api/auth/me` e em `/api/bootstrap`.

**Flutter (admin UI)**: Configurações → Regras → `_ModuleVisibilityCard`
(`flutter/apps/epi_admin/lib/features/settings/settings_screen.dart`) —
mesma experiência unificada do Web Legado: cobre os 11 módulos
(`_kModuleVisibilityModules`, espelha `MODULE_KEYS`) e mostra um seletor de
Unidade quando o perfil está em `_kModuleVisibilityUnitScopedRoles`
(`admin`/`user`). `_isVisible()` aplica o mesmo fallback
Unidade → `"*"` → visível-por-padrão do backend. O antigo card separado
"Escopo por Unidade" (`_ModuleUnitScopeCard`, restrito aos dois módulos
opt-in de Terceirizados) foi retirado — apontava para `/api/module-unit-scope`,
rota removida no PR18; ficou quebrado (chamada 404) entre o merge do PR18 e
este PR. Também corrigido aqui: `_ModuleVisibilityCard` lia
`_visibility[role][module]` diretamente, formato que deixou de existir
quando `module_visibility` passou a ser aninhado por bucket — toda checkbox
aparecia sempre **desmarcada** (o `??` do Dart caía no `false` default,
diferente do bug equivalente no Web Legado, que caía no `true` default).

**Regra backend**: `resolve_module_visibility()` em `epi_backend/
rule_engine.py`, consumido por `get_effective_module_visibility()` em
`modules/settings/service.py` — chamado a partir de `authenticate_login`,
`handle_get_auth_me` e `build_bootstrap`. Rota/módulo ausente do mapa
(`MODULE_REQUIRED_PERMISSIONS`/`routeModules`) continua gateado **só** pela
permissão técnica, exatamente como antes desta política — sem regressão.
