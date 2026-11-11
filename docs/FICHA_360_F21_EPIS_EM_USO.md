# Ficha 360° — F2.1: API de EPIs em uso

Implementação exclusiva do backend. Sem nova interface, entrada em Entregas,
permissão global, migração, índice ou alteração do pool. F1 permanece intacta.

## Contrato

`GET /api/employees/{id}/ppe-360/in-use`, com Bearer obrigatório pelo helper
oficial `require_bearer_actor`, com tipo access validado por `decode_token_of_type`. `actor_user_id`, se presente, deve coincidir com
o JWT. O usuário é recarregado por `require_actor`; permissões vêm do mapa do
servidor, nunca das claims de papel/empresa do navegador.

Requer conjuntamente `employees:view` e `deliveries:view`. Admin Master é
bloqueado antes da leitura do colaborador. A pessoa passa pelo
`resolve_authorized_employee` e pela exclusão lógica da F1.

Administrador Geral/Registro consultam a empresa. Administrador Local/Gestor
consultam exclusivamente a unidade operacional resolvida pelo servidor,
incluindo alocação temporária vigente. A unidade resolvida deve pertencer à
empresa. Vínculo local ativo autoriza a pessoa, jamais outras linhas de entrega.
Sem unidade não existe fallback para visão corporativa.

Parâmetros: `limit` (20 por padrão, 1..100), `cursor`, `actor_user_id` de
compatibilidade. Parâmetros desconhecidos são recusados, inclusive empresa e
unidade. Repetições de paginação são inválidas; identidade repetida é inválida.

Resposta: `{ok:true,data:{employee_id,scope,items,generated_at},page:{limit,next_cursor}}`.
`scope`: empresa, modo `company|operational_unit`, `authorized_unit_ids` (`null`
ou `[U]`), `partial_by_unit`. O indicador parcial descreve a política; não
confirma que existam registros ocultos. Não existe total global/omitido.

Cada item é uma entrega: `delivery_id`, `product` (`id,name,category`),
`quantity`, `delivery_date`, `next_replacement_date`, `unit` (`id,name`).
Referências relacionadas só são resolvidas na mesma empresa, por LEFT JOIN;
referência inconsistente retorna objeto `null`. Texto ausente retorna `null`.
Quantidade SQL NULL vira 1, como na F1; zero/negativo legado não é corrigido.
Nenhum CPF, assinatura, token, comprovante, contato, nota livre, custo ou CA.

Posse oficial: `COALESCE(returned_date,'')=''` e `active_delivery_sql`.
Uma linha por entrega, sem consolidação por produto ou recálculo de troca.

## SQL, calendário e cursor

Filtro obrigatório: empresa do ator + pessoa autorizada + posse ativa; para
`admin/user`, também `d.unit_id = unidade_operacional_autorizada`.
Nenhum OR com vínculo local. Todo parâmetro de valor é parametrizado.

Uma consulta de itens, com limite no PostgreSQL. A janela de até `limit+1`
linhas é selecionada antes dos joins de enriquecimento. Não há consultas por
item, OFFSET, advisory lock ou transação mantida entre páginas.

Datas aceitas: calendário gregoriano estrito `YYYY-MM-DD`, anos 0001..9999,
após remoção de whitespace ASCII externo. Não reinterpretar DD/MM/AAAA ou
timestamp. Ausentes/impossíveis viram `null` na API e `0000-00-00` apenas na
chave SQL. CASE protege os casts; teste inclui 1900/2000 e fevereiro inválido.

Ordenação: `(sort_date DESC,id DESC)`; inválidas/ausentes ficam por último,
por ID decrescente. Cursor reutiliza base64url sem padding de `{s:data,i:id}`,
até 200 caracteres. Validação complementar exige data canônica/sentinela e
ID positivo até BIGINT. Próxima página usa comparação estrita da tupla e
cursor da última linha devolvida. Cursor não concede escopo; toda página
revalida sessão, permissões, pessoa e unidade.

A consulta é uma visão em mudança, sem snapshot entre páginas. Mudanças já
confirmadas antes da página seguinte são reaplicadas; não se promete revogar
uma resposta que já está sendo processada.

## Erros e auditoria

Erros controlados usam `{ok:false,error:{code,message}}`, sem SQL/exceção.
400: `INVALID_EMPLOYEE_ID`, `INVALID_PAGINATION`, `INVALID_QUERY_PARAM`.
401: `UNAUTHENTICATED` (inclui refresh token e claims/base64 malformados). 403: `FORBIDDEN`, `PASSWORD_CHANGE_REQUIRED`.
404 indistinto: `EMPLOYEE_NOT_FOUND` (inexistente, fora do escopo, excluído).
500: `AUDIT_UNAVAILABLE` ou `INTERNAL_ERROR`.
503 por saturação: contrato P0 `DB_POOL_SATURATED`, `Retry-After: 1`.
O gate de bootstrap anterior ao handler mantém seu contrato existente.

Cada página, inclusive vazia, usa `register_company_audit` em `audit.py`:
`ppe360_in_use_view` ou `ppe360_in_use_denied`, sempre na empresa do ator.
Metadados: ID solicitado, código, papel, limite, presença de cursor, modo,
unidades autorizadas e quantidade devolvida quando concedido. Sem cursor
bruto ou conteúdo de itens na trilha própria da F2.1. Log estruturado próprio:
`employee_ppe_360.in_use`. Ator ainda não validado/Master sem empresa: somente
log estruturado. Logs HTTP preexistentes não foram alterados.
Falha da persistência obrigatória gera rollback e impede 200.
F1 mantém eventos, registradores e comportamento anteriores.

## Matriz executável e execução

`tests_postgres/test_employee_ppe_360_f21_in_use_postgres.py` contém:

| Cenário | Prova HTTP/PostgreSQL |
|---|---|
| F2-T01 | Geral/Registro: empresa, duas unidades |
| F2-T02 | Local/Gestor: somente unidade operacional |
| F2-T03 | Vínculo local ativo não amplia linhas |
| F2-T04 | Vínculo arquivado/ausente e 404 indistinto |
| F2-T05 | Unidade ausente/inconsistente não vira empresa inteira |
| F2-T06 | Duas empresas, IDOR e vínculo inconsistente |
| F2-T07 | Master/demais perfis/dupla permissão antes da pessoa |
| F2-T08 | Bearer em off/shadow/enforce; token expirado; identidade e senha |
| F2-T09 | Devolvida/revertida/importada; NULLs reais em tabela temporária |
| F2-T10 | Limites, SQL limitado, parâmetros/IDs adversariais |
| F2-T11 | Keyset com empates, sem duplicação em conjunto estático |
| F2-T12 | Datas legadas, calendário, whitespace e cursor sentinela |
| F2-T13 | Cursor malformado, adulterado e reutilizado sem ampliar escopo |
| F2-T14 | Movimento temporário, perda de autorização/papel e outro usuário |
| F2-T15 | Vazio parcial, arquivado e excluído |
| F2-T16 | Allowlist de campos e referências cruzadas de produto/unidade |
| F2-T17 | Auditoria persistente, negativa e rollback de escrita interrompida |
| F2-T18 | Concorrência, saturação, devolução entre páginas, F1, plano/buffers, erro SQL real |

Os identificadores foram estabelecidos no planejamento desta entrega; não
foram localizados em especificação anterior nos repositórios.

Banco deve ser local/descartável; nunca apontar estes testes para produção.

```sh
PYTHONPATH=.:tests_postgres python -m pytest -q \
  tests/test_employee_ppe_360_f0_contract.py \
  tests/test_employee_ppe_360_f21_contract.py \
  tests/test_employee_ppe_360_boundary.py \
  tests_postgres/test_employee_ppe_360_f1_summary_postgres.py \
  tests_postgres/test_employee_ppe_360_f21_in_use_postgres.py \
  tests_postgres/test_db_pool_p0_postgres.py
```

Requer `DATABASE_URL` do banco descartável e `JWT_SECRET` de teste.
Workflow próprio executa PostgreSQL 16 e publica JUnit. Evidências locais usam
PostgreSQL 17; benchmarks são sintéticos, sem equivalência com produção.
Índices declarados no código não são considerados instalados em produção.
A normalização ainda pode ordenar linhas candidatas; eventual índice é decisão
separada, não parte deste PR. Certificação operacional SaaS continua separada.
