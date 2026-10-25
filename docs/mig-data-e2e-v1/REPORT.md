# MIG-DATA-E2E-V1 — Catálogo e auditoria funcional

Data: 25/10/2026. Escopo: Corporate e SaaS; somente dados sintéticos em
PostgreSQL 17.11 local e bancos exclusivos desta tarefa.

## Base e concorrência

- Corporate: `f596a04c0136220f39a6cb77954f949d79f00b90` (origin/main).
- SaaS: `ac7e072261b528d3c75ed583377397987909d8e4` (origin/main).
- Nenhum PR aberto em ambos na inspeção inicial. Worktrees dedicadas,
  branch `codex/mig-data-e2e-v1`; nenhuma alteração na main local.
- Os HEADs dos PRs e o estado final dos workflows constam na entrega da tarefa
  e na descrição dos PRs. Não há merge ou deploy autorizado por este relatório.

## Evidência funcional

O catálogo da API retorna exatamente seis entradas: Colaboradores (11),
Unidades (4), EPIs (11), Fornecedores (5), Histórico de Entregas (8) e Estoque (4).
As contagens são verificadas contra os descritores reais, sem mudanças de schema.

O Chromium percorreu os seis cartões de cada produto, seleção da categoria,
upload CSV, leitura, mapeamento automático, prévia, confirmação, processamento,
consulta do histórico, recarga sem duplicação e homologação via interface.
Não houve erro JavaScript de página. Busca pelas três categorias excluídas
retorna zero cartões; busca por estoque retorna um cartão.

- [Corporate: seis cartões](evidence/corporate-six-cards.png)
- [SaaS: seis cartões](evidence/saas-six-cards.png)
- [Corporate: resultados do navegador](evidence/corporate-browser-results.json)
- [SaaS: resultados do navegador](evidence/saas-browser-results.json)

`tests_postgres/test_migration_data_e2e_postgres.py` envia arquivos reais por HTTP
com o handler, roteador, autorização, parser e PostgreSQL reais. Exercita as
36 combinações de entidade/formato: CSV, TXT, XLSX, ODS, JSON e XML. Cada caso
compara situação inicial, prévia, contagens, valores normalizados e vínculos no
PostgreSQL, relatório, auditoria, recusa de repetição da confirmação, reversão
física, nova importação, homologação e regime de reversão pós-homologação.

## Matriz obrigatória

PASSOU significa evidência real no contrato descrito acima. A coluna Resultado
inclui o requisito de completude da solicitação, não apenas o sucesso do endpoint.

### Corporate

| Entidade | Upload | Mapeamento | Prévia | Importação | PostgreSQL | Homologação | Rollback | Resultado |
|---|---|---|---|---|---|---|---|---|
| Colaboradores | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Unidades | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| EPIs | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Fornecedores | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Histórico de Entregas | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Estoque | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | FALHOU |

### SaaS

| Entidade | Upload | Mapeamento | Prévia | Importação | PostgreSQL | Homologação | Rollback | Resultado |
|---|---|---|---|---|---|---|---|---|
| Colaboradores | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Unidades | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| EPIs | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Fornecedores | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Histórico de Entregas | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU |
| Estoque | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | PASSOU | FALHOU |

Rollback: PASSOU refere-se à reversão física antes de homologar. Após homologar,
a reversão lógica de Histórico de Entregas PASSOU; reversão das outras cinco
entidades é NÃO SUPORTADO e sua recusa explícita foi testada. Nenhuma linha
homologada é apagada para contornar essa restrição.

Estoque: Upload até PostgreSQL PASSOU **somente para saldo agregado auditado por
movimento**. Lotes, fabricação e validade física na migração são NÃO SUPORTADO.
A prova independente demonstrou saldo físico 100, peças rastreadas 0, elegível 0,
livre 0 e diferença de conciliação 100. Logo, o requisito de estoque utilizável
com rastreabilidade física FALHOU; não há aprovação de funcionamento completo.

## Defeitos corrigidos e provas

1. Removidas as três categorias de catálogo, seleção, busca e documentação
   operacional. `empresas`, `usuarios`, `solicitacoes` são recusadas com HTTP 400
   em análise, aplicação e submissão assíncrona. Prévia usa o mesmo gate. Jobs
   históricos continuam consultáveis e reversão sem contrato atual é recusada.
   Cadastro e gestão fora do Centro e os dados existentes não foram removidos.
2. Homologação passou a ter ação no histórico da interface, com confirmação que
   explica o efeito sobre a reversão física. Integração foi extraída para
   `static/js/modules/data-migration/integrations/job-decisions.js`.
3. Confirmação é desabilitada antes da resposta; guarda de operação ocupada e
   prévia já aplicada impede clique duplicado. Prova JavaScript mantém a
   requisição pendente e verifica exatamente um envio.
4. Rollback de fornecedor valida snapshots completos dos vínculos secundários,
   com locks do pai e dos vínculos. Vínculo posterior, desativado, excluído ou
   job legado sem prova impede a reversão inteira, preservando os dados.
5. Mudar unidade de fornecedor existente pela importação é recusado na prévia
   e na aplicação; deve ser feito pela gestão explícita de vínculos. Isso evita
   sucesso que aponta para B mantendo disponibilidade somente em A.
6. Worker assíncrono finaliza controle, dados, job e auditoria no mesmo commit.
   Interrupção após commit encontra controle concluído; falha da auditoria
   desfaz os dados. As seis entidades exercitam fila, idempotência e cancelamento.
   Estratégias `dry_run` ou desconhecidas são recusadas antes de enfileirar.
7. Reimportar saldo igual mostra “ignorado” também na prévia, sem movimento novo.
8. Estoque mostra aviso explícito de contrato agregado. Colunas preenchidas de
   lote/fabricação/validade física impedem a importação mesmo quando omitidas do
   mapeamento. Escopo com peças já rastreadas é bloqueado sob o lock de estoque
   compartilhado com as operações de domínio, preservando lote, datas e saldo.

As regressões existentes das Fases 1–3 cobrem identidade CPF/matrícula/CA,
referências entre tenants, IDOR/RBAC, valores malformados, inteiros sem truncamento,
duplicatas, upsert, overwrite, concorrência, snapshots ABA, dependências FK,
reversão atômica, sanitização e fences/leases do worker. Elas foram mantidas.

## Execução reproduzível

Use somente banco PostgreSQL isolado: o bootstrap aplica as migrations reais.

```sh
DATABASE_URL=postgresql://USUARIO@127.0.0.1/BANCO_EXCLUSIVO pytest tests_postgres/ -q
pytest tests/ -q
node static/js/test/run-tests.js
node static/js/test/app-js-boundary.js
python scripts/build_index.py check
```

Os bancos dedicados foram `mig_data_e2e_corporate`, `mig_data_e2e_saas`,
`mig_data_e2e_ui_corporate`, `mig_data_e2e_ui_saas` e `mig_data_e2e_audit`.
A auditoria aplicou todas as 36 migrations. Nenhum banco compartilhado ou
serviço remoto de dados foi usado. Não há alteração de schema nesta entrega.

## Limitação bloqueante e correção proposta

O catálogo de quatro campos de Estoque não representa lote, fabricação, validade
física ou evidência. O writer existente produz movimento + saldo, mas não cria
`epi_stock_items`, `epi_stock_lots` ou eventos do ciclo físico. O saldo importado
não passa automaticamente a ser elegível para entrega. A regularização de peças
não resolve a ausência de peças criadas. O aviso da prévia informa essa dependência.

Completar esse requisito exige contrato explícito de importação física com
proveniência da validade, associação de lotes/peças, eventos de recebimento,
conciliação entre razão, itens, reservas e saldo, e rollback desses efeitos.
Não se fabricaram datas, lotes ou evidências para simular completude. Até essa
capacidade ser implementada e comprovada, **Estoque não recebe veredito completo**.

Não foram executados formatos de banco/API/ERP ou binários: NÃO SUPORTADO pelo
contrato atual. O navegador auditado é o web legado; jornada Flutter é
NÃO EXECUTADO nesta tarefa. Cancelamento em fila foi comprovado para as seis
entidades; interrupção durante cada linha não é prometida pelo executor atômico.
O progresso disponível no contrato atual é o estado e totais duráveis, sem prova
de progresso por linha na interface síncrona.

## Veredito

**TECHNICAL VERDICT: REPROVADO** para a exigência de seis categorias integralmente
operacionais com rastreabilidade física de estoque. A limpeza do catálogo e as
correções de integridade têm evidência positiva, mas não eliminam esse bloqueador.

**READY FOR HUMAN MERGE DECISION: NO** para aprovar o escopo completo solicitado.
A entrega permanece em PRs draft; nenhuma execução de merge, deploy, force-push,
exclusão de dados existentes ou mudança de proteção de branch foi realizada.
