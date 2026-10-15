# MIG-DATA-FIX-V1 — Fase 2: contrato e matriz

Escopo: somente entidades e fontes já habilitadas; sem schema/infraestrutura novos.

## Contrato compatível

`run` preserva os campos existentes e acrescenta `status`, `revalidated`,
`preview_matches_result`, `preview.preview_token`, `row_classifications`,
`will_skip`, `will_reject`, `actual_totals` e diagnósticos `code/row/source_line/field/message/severity/entity`.
O cliente pode informar `preview_strategy` no dry-run e `preview_token` na confirmação.
A UI sempre envia token. Consumidores antigos sem token continuam funcionando,
mas o servidor sempre recalcula o plano sob locks antes de gravar.
Token divergente retorna HTTP400 `preview_stale`, nova prévia e nenhuma escrita.
A prévia não é reserva nem promessa contra erros de constraints/triggers na execução.

Qualquer erro de parsing/mapeamento/validação bloqueia o arquivo inteiro, como
previsto na política estrita existente. Falhas de escrita por linha continuam
isoladas por SAVEPOINT. Falha estrutural ou conciliação divergente reverte tudo.
Relatório final usa contagens reais e ações efetivas, não contagens da simulação.
Erros do banco exibem mensagem segura; SQL e dados de exceções não são exportados.
Colunas não mapeadas e metadados/abas ignorados são avisados expressamente.

## Estados e transições

Sem job: aguardando validação → prévia bloqueada ou pronta. Durante a requisição:
indicador ocupado, sem percentual fictício. `running` é transacional e não promete
observabilidade entre conexões. Ao finalizar: `completed` (zero erros),
`completed_with_rejections` (há resultados e rejeições), `failed` (tudo rejeitado
ou falha estrutural). Somente completed aceita homologação; completed e parcial
aceitam reversão segura. `completed` sem homologated_at é apresentado como
aguardando homologação; com homologated_at, homologado. `reverted` tem prioridade.
Jobs legados completed continuam legíveis, sem reinterpretar seu passado.
Falha integral não é sucesso e não é homologável. Jobs parciais não homologam.
Histórico lista processados e contadores existentes. Detalhe de registros é
paginado em até500 por página, com `offset/next_offset`; export percorre todas.
`source_line` é a linha física inicial CSV/TXT e linha da planilha; JSON/XML usam
posição do registro. Históricos legados sem linha física deixam o campo vazio.

## Identidade

Empresa é sempre do ator autorizado. Colaboradores: CPF e matrícula precisam
convergir no mesmo registro, inclusive chaves secundárias. Unidade: nome único
no tenant. EPI: código de compra e CA; nome é descritivo e não UNIQUE. Referências
aceitam identificadores internos/nomes/chaves somente se todos os candidatos
convergirem; ambiguidade numérica nome×ID bloqueia. Migrações são serializadas
por empresa, referências são protegidas durante a execução e linhas existentes
bloqueadas; constraints PostgreSQL seguem como autoridade final.
Histórico usa hash do arquivo+linha+payload normalizado; mesmo arquivo reimportado
é ignorado, enquanto arquivos diferentes com eventos distintos são preservados.
A chave legada só deduplica se for comprovado o mesmo source_hash.

## Matriz do catálogo (sem novas entidades)

|Entidade|Estado nesta fase|Pendência/dependência|
|---|---|---|
|Colaboradores|Operacional, identidade e prévia corrigidas|Recuperação assíncrona futura|
|Unidades|Operacional; tipo obrigatório sem default artificial|Recuperação assíncrona futura|
|EPIs|Operacional; conflitos CA/código detectados|Recuperação assíncrona futura|
|Histórico de entregas|Operacional; contagens e reimportação corrigidas|Reconciliação entre arquivos diferentes depende de identidade do legado|
|Estoque físico|Não implementado deliberadamente no writer atual|Movimentos/ajustes e rastreabilidade; não saldo direto, Fase5|
|Solicitações|Não implementado|Identidade e workflow de negócio, Fase5|
|Fornecedores|Bloqueado por decisão arquitetural|Vínculos com unidades e políticas; Fase5 mediante aprovação|
|Usuários|Excluído deliberadamente do writer atual|Credenciais/perfis e política de acesso, decisão separada|
|Empresas|Excluído deliberadamente do writer atual|Criação de tenant fora do administrador geral|

Nenhuma tabela/relação inventada para completar o catálogo. Campos obrigatórios,
campos mapeáveis e limitações de domínio continuam nos descritores reais do
catalog.py e na matriz P0, preservada nesta branch.

## Fase3 futura — não iniciada

Pipeline ainda síncrono, memória de parsing/base64, transação por arquivo e
serialização por empresa limitam volume. Continuam sem fila persistente,
progresso consultável, checkpoint, retomada ou cancelamento seguro. Fase3 precisa
de IDs estáveis por linha/job, ownership/leases, idempotência, fronteira de commit,
tratamento de interrupções e revalidação das garantias P0; tenant/RBAC/locks devem
permanecer comuns aos dois produtos. Nenhuma infraestrutura foi implementada.

## Verificação e governança

Baseline existente:430 aprovados/produto. RED independente:32 falhas e2 aprovados
por produto, commits baseline documentados nos PRs. Testes novos mantidos ativos.
Sete expectativas antigas foram fortalecidas para exigir estados honestos,
diagnósticos sanitizados e CSV irregular rejeitado sem persistência. Digestos de
paridade F4/F5B recalculados pelo helper original após alteração pontual app.js;
asserts e conjunto de arquivos permanecem intactos. index.html regenerado pelo
build oficial; dependência odfpy declarada para ODS previamente anunciado.

Resultados finais, SHAs congelados, CI e auditoria independente constarão no
relatório final de cada PR. Até aprovação independente: READY FOR HUMAN MERGE
DECISION=NO. Merge, deploy, force-push, dados reais, migração compartilhada e
alteração de branch protection proibidos. Fases3–5 aguardam nova autorização.
