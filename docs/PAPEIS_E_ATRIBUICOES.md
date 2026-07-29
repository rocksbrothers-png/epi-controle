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
