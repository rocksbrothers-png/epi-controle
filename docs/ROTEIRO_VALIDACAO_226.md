# Roteiro de validação ponta a ponta — issue #226

Vínculo local por Unidade de **empresa terceirizada** e de **colaborador
terceirizado**, entregue pelos PRs F1 → F6B.

Este roteiro existe porque CI verde não é a mesma coisa que fluxo funcionando.
Os testes provam que cada camada respeita o contrato que lhe foi escrito; o que
eles não provam é que as camadas, juntas e contra um banco real, produzem o
comportamento que o produto pediu. É essa diferença que os seis cenários abaixo
cobrem.

## O que está sendo validado

A regra de domínio, em uma frase: **a empresa terceirizada e o colaborador
terceirizado são únicos no tenant, e cada Unidade tem o seu próprio vínculo com
eles, com estado próprio.** Disso decorre tudo o mais — não herdar, não
duplicar, arquivar sem afetar os outros, reativar preservando histórico.

## Como executar

```bash
# Sobe PostgreSQL 16 local, aplica as 25 migrations, semeia dois tenants,
# sobe o app.py real e exercita as rotas por HTTP.
python3 scripts/validar_226_ponta_a_ponta.py
```

O executor não usa mock nenhum: fala HTTP com o servidor de verdade, que fala
com PostgreSQL de verdade. Toda asserção é sobre o corpo da resposta ou sobre o
estado das tabelas depois dela.

## Cenário base

Dois tenants, para que o isolamento seja testável e não presumido:

| | Tenant | Unidade | Papel do ator |
|---|---|---|---|
| Norte | Alfa | Unidade Norte | Administrador Local (`admin`) |
| Sul | Alfa | Unidade Sul | Administrador Local (`admin`) |
| Externa | Beta | Unidade Beta | Administrador Local (`admin`) |
| Geral | Alfa | — | Administrador Geral (`general_admin`), não escopado |

No tenant Alfa existem, **cadastrados uma única vez**:

- a empresa terceirizada **Construtora Ômega**, originada na Unidade Norte e
  vinculada a ela;
- o colaborador terceirizado **Beltrano de Souza**, lotado na Unidade Norte.

A Unidade Sul começa sem vínculo com nenhum dos dois. É exatamente essa a
situação que motivou a #226: hoje a Sul não os enxerga na listagem comum —
justamente por não ter vínculo — e, sem o fluxo de busca, a saída do operador
seria cadastrar tudo de novo.

---

## C1 · Vínculo multi-Unidade de empresa, sem duplicar cadastro

**Dado** que a Construtora Ômega está vinculada só à Unidade Norte,
**quando** o Administrador Local da Unidade Sul buscar por "Ômega" e vincular,
**então**:

1. a busca a encontra, **mascarada** (`linked_units_count` presente,
   `local_status` ausente) — a Sul sabe que a empresa existe e quantas Unidades
   já a usam, sem ver dado operacional de outra Unidade;
2. o vínculo é criado e a empresa passa a aparecer na listagem da Sul com
   `local_status: 'active'`;
3. `outsourced_companies` continua com **exatamente uma** linha para a Ômega —
   o cadastro corporativo não foi duplicado;
4. `outsourced_company_unit_links` passa a ter **duas** linhas, uma por Unidade.

O item 3 é o coração do cenário. Se ele falhar, a #226 não foi resolvida: terá
sido contornada com um segundo cadastro.

## C2 · Vínculo multi-Unidade de colaborador, sem duplicar cadastro

Mesma estrutura, um nível abaixo. **Dado** Beltrano lotado na Norte, **quando**
a Sul o vincular:

1. `GET /api/employees` da Sul passa a incluí-lo com
   `local_unit_link_status: 'active'` e `is_linked_to_actor_unit: true`;
2. `employees` continua com **uma** linha para Beltrano, e o seu `unit_id`
   **continua sendo o da Norte** — vincular não é transferir;
3. `employee_unit_links` tem duas linhas.

O item 2 merece atenção: a tabela de vínculos é paralela justamente para que
`employees.unit_id` nunca seja tocado. Uma implementação que "resolvesse" o
problema movendo o colaborador passaria em qualquer teste ingênuo de
visibilidade e quebraria a lotação.

## C3 · Ausência de herança entre Unidades

**Quando** a Sul vincula uma empresa que a Norte já usa, ela **não** recebe
nada do que a Norte construiu em cima daquele vínculo:

1. contratos de serviço da Norte não aparecem para a Sul;
2. colaboradores que a Norte vinculou não aparecem para a Sul;
3. o vínculo da Sul nasce limpo — sem número de contrato, sem centro de custo,
   sem responsável local herdado.

Vínculo é uma relação entre **uma** Unidade e a empresa. Herdar seria tratá-lo
como propriedade da empresa.

## C4 · Arquivamento local independente

**Quando** a Sul arquivar o seu vínculo com a Ômega:

1. o vínculo da Sul fica `inactive`, com motivo, ator e carimbo de tempo
   gravados;
2. o vínculo da **Norte permanece `active`** e intocado;
3. o cadastro corporativo da Ômega permanece `active` — arquivar na Unidade
   não é arquivar no tenant;
4. nenhuma linha é apagada: `outsourced_company_unit_links` continua com duas.

O item 4 é a garantia contra o atalho que a #226 proíbe: apagar o vínculo para
destravar exclusão. Arquivar deixa rastro; apagar não deixaria.

## C5 · Reativação preservando histórico

**Quando** a Sul reativar o vínculo arquivado:

1. o `local_status` volta a `active`;
2. é **a mesma linha** — mesmo `id` de antes do arquivamento;
3. o vínculo reativado **não** carrega motivo de arquivamento residual;
4. a auditoria preserva o arquivamento anterior, com motivo, Unidade e papel de
   quem arquivou.

Os itens 3 e 4 andam juntos e a divisão entre eles é intencional. As colunas
`deactivated_*` do vínculo são **estado corrente**, não histórico: um vínculo
ativo carregando "arquivado porque a obra encerrou" leria como se ainda
estivesse arquivado. Quem guarda a sequência do que aconteceu é
`company_audit_logs` — e é lá que ela precisa sobreviver à reativação.

Se a reativação criasse uma linha nova, o histórico do arquivamento ficaria
órfão de um vínculo que não existe mais, e a auditoria perderia a sequência do
que aconteceu naquela Unidade.

## C6 · `null` é "não informado", nunca "sem vínculo"

Para um perfil **não escopado** por Unidade (Administrador Geral), a busca não
tem uma Unidade de referência para anotar o vínculo local. Nesse caso:

1. a resposta vem **sem** `local_status` e **sem** `linked_units_count`;
2. a tela renderiza "vínculo não informado" — não oferece "Vincular".

A distinção importa porque as duas ausências são visualmente idênticas e
semanticamente opostas. Tratar `null` como "não vinculado" faria a tela
oferecer uma ação sobre uma empresa que pode já estar vinculada, e o operador
descobriria isso só pelo erro do backend.

## C7 · Isolamento entre tenants

O Administrador Local da Unidade Beta (tenant Beta) **não** alcança nada do
tenant Alfa:

1. a busca por "Ômega" não retorna a empresa do Alfa;
2. tentar vincular a empresa do Alfa pelo id é recusado;
3. tentar ler os vínculos do colaborador do Alfa é recusado.

Nenhum comportamento pode atravessar tenants — nem em leitura, nem mascarado.

---

## Fora deste roteiro

**Exclusão definitiva.** Não existe exclusão manual de colaborador ou de
empresa neste fluxo, por decisão de produto: arquiva-se o vínculo, o registro é
preservado pelo prazo de retenção configurado pelo Administrador do Sistema, e
só a purga remove o que for elegível. Não há botão, rota ou caminho a validar
aqui — o que se valida é justamente a **ausência** deles, coberta em C4.

**Camada visual do Flutter.** Os cenários exercitam a API, que é onde as regras
de autorização vivem. O comportamento da tela sobre essas respostas está travado
pelos testes de `outsourced_company_unit_link_test.dart` e
`outsourced_employee_unit_link_test.dart` — inclusive C6, que na tela é o ramo
`outsourcedCompanyLinkNotInformed`.
