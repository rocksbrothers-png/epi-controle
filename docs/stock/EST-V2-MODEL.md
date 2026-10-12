# EST-V2 — modelo físico de estoque

Esta fase cria estrutura e contratos de valores. Bloqueio operacional, reservas,
entrega/FEFO, decisões, indicadores e interfaces serão integrados em EST-V3–V8.
Não se declara Gestão de Validade/Estoque Bloqueado completa por esta migração.

## Dependência e isolamento

R2 técnica revisada por outro agente nos commits Corporate `6c93161` e SaaS
`418895c`: suítes completas, B01–B04, A01–A32, três QA adicionais próprios e CI
atual aprovados. A primeira tentativa CI SaaS falhou; o rerun do mesmo SHA passou.
A causa daquela tentativa permanece em investigação, sem alegar falha de timing.
Required isolation/owner review não estão enforced: dívida de liberação, sem
alteração de proteção. Main não contém estas correções; não foi autorizado merge.

SaaS atende Flutter Web/Android/iOS SaaS. Corporate mantém backend, banco e
identidade próprios. O modelo é implementado em cada checkout; não há conexão
entre os bancos nem mudança em hosts, applicationIds ou configuração de deploy.

## Modelo e migração 030

| Entidade | Dados e garantias |
| --- | --- |
| `epi_stock_lots` | Empresa/EPI/recebimento/unidade de origem; lote textual opcional; fabricação/vencimento físico; prazo documentado em dias/meses/anos quando conhecido; evidência; snapshot CA/validade CA; quantidade recebida; fornecedor; custo `NUMERIC(18,4)` nullable; ator e horário. `receipt_key` identifica o recebimento dentro da empresa. Repetição de rótulo não funde recebimentos. |
| `epi_stock_items` | QR e identidade preservados; lote opcional para legado; datas físicas próprias; fonte/evidência; custo nullable; versão; campos de bloqueio. `status` existente é operacional; validade é calculada. |
| `epi_stock_events` | Item/lote/quantidade positiva, empresa, origem/destino, tipo/motivo/justificativa, ator com snapshots, horário, antes/depois, decisão e movimento. UPDATE/DELETE são recusados pelo banco. FKs restritivas preservam histórico após disposição. |
| `epi_stock_decisions` | Pedido de desbloqueio/destinação, justificativa, responsável, estado, decisão/justificativa/decisor e horários. Uma decisão pendente por peça. Permissões e transições operacionais serão integradas na EST-V5. |
| `company_stock_validity_config` | Prazo de alerta inteiro não negativo por empresa, responsável e horário. Sem linha, o contrato usa padrão explícito de 30 dias; leitura/gravação auditada e UI serão integradas nas fases seguintes. |

Migração aditiva `20261012000000_stock_lifecycle_model.sql`, descoberta pelo runner
real como `030_stock_lifecycle_model`. Novas tabelas nascem com RLS e policy que
nega acesso direto de `anon`/`authenticated`. Backend continua responsável por
JWT, RBAC e escopo; RLS não substitui autorização no backend owner.

FKs compostas impedem novos vínculos de item/lote/EPI/unidade/fornecedor,
movimento e decisão entre empresas. Triggers validam empresa do responsável na
escrita; mudanças posteriores de perfil não reescrevem snapshots históricos.
Saldo agregado recebe CHECK não negativo. Constraints sobre tabelas legadas
usam `NOT VALID`: protegem novas escritas sem inventar correções do histórico.
Reconciliar inconsistências existentes e validar essas constraints é EST-V3/V7.

A revisão independente identificou que `blocked_by_user_id` ainda aceitava ator
de outra empresa. A migração aditiva `031_stock_item_actor_scope` fecha esse
vínculo na inserção, troca de responsável e troca de empresa. Os testes novos
falharam contra a 030 com `DID NOT RAISE`, antes da correção. Alterações posteriores
do usuário continuam preservando a responsabilidade histórica registrada.

O gate `ci_migrations_report.py` requer os alvos RLS em um dos moldes derivados
das migrações. A declaração da030 foi adaptada para `tbls text[] := ARRAY[...]`;
as quatro tabelas, RLS e policies permanecem iguais. O mesmo comando de CI foi
reproduzido contra PostgreSQL local, sem relaxar o verificador ou suas exigências.

Nenhum lote, custo ou vencimento é inferido do catálogo. Colunas físicas novas
de peças legadas permanecem NULL. Fabricação antiga já registrada é preservada
como legado; a cópia automática da fabricação do catálogo foi removida. A
informação antiga não é promovida à nova coluna física sem regularização.

## Estados e valores

- Validade: `valid`, `expiring`, `expired`, `unknown`; vencimento anterior ao dia
  de referência é vencido, e a data informada vale até esse dia. Todas as
  operações deverão usar o mesmo cálculo de data de referência.
- Desconhecido é inelegível por validade. Isso é contrato estrutural nesta fase;
  a imposição em entrega/reserva será conectada na EST-V3/V4.
- CA e seu vencimento são snapshots separados. CA não substitui validade física.
- Data física inválida é rejeitada. Ausência permanece NULL; não há data fictícia.
- Custo desconhecido permanece NULL; zero informado é distinto. Custos negativos,
  infinitos ou inválidos são rejeitados. Precisão monetária é de quatro decimais.
- Motivos de bloqueio: vencido, avaria, não conformidade, quarentena, inspeção
  pendente, suspeita de defeito, recolhimento e outros com justificativa.
- Destinos: retorno à base, quarentena, fornecedor e descarte. `discarded` e
  `supplier_returned` são terminais no vocabulário; a máquina de transição e a
  aprovação por Administrador Geral serão ativadas na EST-V5.

## Contratos API para integração nas fases seguintes

Não foram expostos endpoints fictícios nesta fase. Os endpoints atuais seguem
com as limitações inventariadas na auditoria inicial.

| Comando/consulta | Integração prevista |
| --- | --- |
| Recebimento por lote | Empresa/unidade/EPI validados no backend; chave idempotente; quantidade; dados físicos e evidência; CA separado; custo nullable; etiquetas por peça; recebimento e evento na mesma transação. |
| Listagem e QR físico | Registro físico por empresa/unidade, validade/estado operacional, disponibilidade e histórico; identidade autenticada determina escopo. |
| Bloqueio/desbloqueio | Item ou peças de lote na unidade, versão, motivo/justificativa; responsável obtido do JWT; evento transacional; elegibilidade atualizada. |
| Regularização | Datas/custo e origem documental explícita, justificativa, versão, antes/depois e responsável; não é alteração visual de status. |
| Entrega/FEFO | Seleção elegível, menor vencimento, locking e baixa atômica; desconhecido/vencido/bloqueado/descartado excluídos. |
| Destinação | Solicitação e decisão auditáveis; descarte exige papel geral autorizado; terminalidade preservada. |
| Indicadores | Mesmos IDs das listas filtradas; custo real por peça/lote; ausência de custo declarada separadamente; prazo da empresa. |

## Validação e limites

Testes de valores em `tests/test_stock_lifecycle_values.py`. Contratos PostgreSQL
em `tests_postgres/test_stock_lifecycle_model_postgres.py` usam bootstrap/DDL
reais, dois tenants e roles restritos. A CI PostgreSQL Migration Journey já
descobre todo `tests_postgres/`, incluindo o novo arquivo; não depende de teste
estático ou schema copiado.

Estes testes cobrem estrutura/proveniência/constraints/RLS/histórico. Não são
aceitação antecipada de entrega, FEFO, bloqueio funcional, UI ou câmera.
Recebimento operacional ainda precisa parar de alterar o catálogo na EST-V3.
Desbloqueio/descarte/quantidade disponível antigos ainda precisam ser substituídos.

MERGE = NÃO. DEPLOY = NÃO. BRANCH PROTECTION = INALTERADA.
READY FOR HUMAN MERGE DECISION = NÃO até a validação independente final do sistema.
