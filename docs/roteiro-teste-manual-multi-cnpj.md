# Roteiro de teste manual — Multi-CNPJ

Este roteiro foi **executado** contra um PostgreSQL 16 vazio e um servidor
recém-subido, não escrito a partir da leitura do código. Os valores esperados
abaixo são os que o sistema devolveu de fato.

**O que foi executado de ponta a ponta:** passos 0 a 8, no **web legado**, em
navegador real (Chromium), com conferência via API e SQL a cada passo. O passo
0 encontrou um defeito de verdade (ordem das migrações no PostgreSQL), corrigido
antes do restante.

**O que não foi executado nesta rodada:** o passo 9 (Administrador Master →
CNPJs do cliente) e a variante do passo 3.1 no **app Flutter**. O ambiente não
tinha como rodar o app compilado. Estão cobertos por teste automatizado
(`legal_entities_cubit_scope_test.dart` confirma que o recorte muda o endpoint
chamado e que o cadastro envia `company_id`), mas **não** por verificação
visual — trate-os como pendentes de confirmação sua.

Cada passo diz: onde clicar, o que digitar, o que precisa aparecer na tela e
como confirmar no banco ou na API. Se algum passo divergir, o passo é o defeito
— não o roteiro.

---

## 0. Preparar o ambiente

```bash
export DATABASE_URL="postgres://usuario@host:5432/seu_banco"
export INITIAL_MASTER_PASSWORD='troque-esta-senha'
python app.py                       # sobe em http://localhost:8000
```

**Esperado:** nenhuma linha `application.bootstrap_failed` no log. Conferir:

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
-- 69 tabelas (ou mais, conforme a versão)
psql "$DATABASE_URL" -c "SELECT to_regclass('public.legal_entities');"
-- legal_entities
```

> Se o bootstrap falhar com `relation "epi_requests" does not exist`, a
> instalação está sem a correção de ordem das migrações.

---

## 1. Criar a empresa (perfil: Administrador Master)

| Campo | Valor |
| --- | --- |
| URL | `http://localhost:8000/` |
| Login | `admin` / a senha de `INITIAL_MASTER_PASSWORD` |
| Caminho | menu lateral → **Empresas** → aba **Cadastro** |

Preencher: Nome `Grupo ACME`, CNPJ `11.222.333/0001-81`, Razão social
`ACME Serviços Marítimos LTDA`, Plano `Business`, Limite de usuários `20`.

**Esperado na tela:** a empresa aparece na aba **Lista**.

**Confirmar que o CNPJ matriz nasceu junto** — este é o comportamento que
garante que nenhuma empresa fica sem pessoa jurídica:

```bash
curl -s "http://localhost:8000/api/companies/1/legal-entities?actor_user_id=1" | python3 -m json.tool
```

Esperado: **um** CNPJ, `entity_type: "matriz"`, `is_headquarters: 1`,
`active: 1`, com o mesmo número informado no cadastro da empresa.

---

## 2. Criar o Administrador Geral da empresa

Menu → **Usuários** → **Cadastro**. Perfil `Administrador Geral`, empresa
`Grupo ACME`.

No **primeiro login** o sistema exige troca de senha — isso é esperado e
precisa ser concluído, senão as telas ficam sem dados (o carregamento inicial
só ocorre após a troca).

Sair e entrar com esse usuário. Daqui em diante o roteiro usa **este** perfil.

---

## 3. A funcionalidade está visível? (a lacuna que motivou tudo)

### 3.1 App (Flutter — web, Android ou iOS)

**Esperado:** o menu lateral mostra **CNPJs** logo abaixo de **Unidades**,
com ícone de prédio. Clicar abre a tela de gestão de CNPJs.

Antes desta entrega o item não existia: a tela só era alcançável digitando
`/legal-entities` na barra de endereços.

### 3.2 Web legado

**Esperado:** o menu lateral mostra **CNPJs** entre **Unidades** e **Cadastro
de Colaborador**.

Antes desta entrega o web legado **não tinha nenhuma tela de CNPJ**.

> Se o item não aparecer, verifique a permissão: ele exige
> `legal_entities:view`. Administrador Geral e de Registro têm; confira em
> `GET /api/bootstrap?actor_user_id=<id>` → `permissions`.

---

## 4. Cadastrar um segundo CNPJ

Menu → **CNPJs** → aba **Cadastro**:

| Campo | Valor |
| --- | --- |
| CNPJ | `45.723.174/0001-10` |
| Razão social | `ACME Filial RJ LTDA` |
| Nome fantasia | `ACME Rio` |
| Tipo | `Filial` |
| Município / UF | `Macaé` / `RJ` |

**Esperado na aba Lista:** duas linhas, ambas com situação **Ativo** e botões
**Editar** e **Inativar**.

**Confirmar:**

```bash
curl -s "http://localhost:8000/api/companies/1/legal-entities?actor_user_id=<id>" \
  | python3 -c "import sys,json;[print(e['id'],e['cnpj'],e['legal_name'],e['active']) for e in json.load(sys.stdin)['legal_entities']]"
```

---

## 5. Vincular uma unidade ao CNPJ

Menu → **Unidades** → **Cadastro**. Nome `Base Macaé`, Tipo `Base`,
Cidade `Macaé`.

**Esperado:** existe o campo **CNPJ responsável**, com as duas opções no
formato `Nome fantasia — 00.000.000/0001-00`. Escolher `ACME Rio`.

**Esperado na aba Lista:** a tabela tem a coluna **CNPJ**, e a linha da
`Base Macaé` mostra `ACME Rio — 45.723.174/0001-10`.

**Confirmar que persistiu (e que o rótulo vem da API, não da tela):**

```bash
curl -s "http://localhost:8000/api/units?actor_user_id=<id>" \
  | python3 -c "import sys,json;[print(u['name'],'|',u.get('legal_entity_cnpj'),'|',u.get('legal_entity_trade_name')) for u in json.load(sys.stdin)['units']]"
```

Esperado: `Base Macaé | 45.723.174/0001-10 | ACME Rio`.

### 5.1 Unidade sem CNPJ continua existindo

Cadastrar `Base Sem CNPJ` **sem** escolher CNPJ.

**Esperado:** a unidade aparece na lista com `-` na coluna CNPJ. Ela **não**
pode sumir — é justamente nesse estado que alguém precisa encontrá-la para
atribuir o CNPJ depois.

### 5.2 CNPJ de outra empresa é recusado

Só verificável por API (a tela nem oferece a opção, que é o ponto):

```bash
curl -s -X PUT "http://localhost:8000/api/units/2" -H 'Content-Type: application/json' \
  -d '{"actor_user_id":<id>,"company_id":1,"name":"Base Macaé","unit_type":"base","city":"Macaé","legal_entity_id":<id de outra empresa>}'
```

Esperado: `{"error": "CNPJ informado não pertence a esta empresa."}`

---

## 6. Trocar o CNPJ de uma unidade

Menu → **Unidades** → **Lista** → **Editar** na `Base Macaé`.

**Esperado:** o formulário abre com o CNPJ atual já selecionado. Trocar para
`Grupo ACME` e salvar; a coluna CNPJ da lista passa a mostrar o novo.

> Diferente do colaborador, o CNPJ da unidade **é** alterável — reorganização
> societária e troca de operadora de JV acontecem. O que não existe é opção de
> "limpar" o vínculo: enviar vazio mantém o valor atual, então o seletor não
> oferece uma opção que não teria efeito.

---

## 7. Inativar um CNPJ (e o que o sistema recusa)

Menu → **CNPJs** → **Lista** → **Inativar** no `ACME Filial RJ LTDA`.

**Esperado:** confirmação explicando que o histórico é preservado. Após
confirmar, a linha some da lista (inativos ficam ocultos por padrão).

Marcar **Mostrar inativos**: a linha reaparece com situação **Inativo**.

**Esperado no CNPJ que sobrou:** o botão **Inativar** não aparece. Tentar pela
API confirma a regra:

```bash
curl -s -X DELETE "http://localhost:8000/api/legal-entities/1?actor_user_id=<id>"
```

Esperado: `{"error": "Não é possível inativar o único CNPJ ativo da empresa."}`

> A empresa ficaria sem pessoa jurídica e todo colaborador perderia o vínculo.

### 7.1 Editar um CNPJ inativo não o reativa

Com **Mostrar inativos** marcado, clicar **Editar** no CNPJ inativo, alterar o
nome fantasia e salvar.

**Esperado:** ele continua **Inativo**.

> Este é um ponto perigoso do backend: `PUT` sem o campo `active` assume `1` e
> reativaria o CNPJ em silêncio. O formulário envia a situação atual junto.
> Verificado: a chamada crua sem `active` **de fato** reativa — por isso a tela
> não pode depender do padrão.

---

## 8. Colaborador em empresa com mais de um CNPJ

Reativar o segundo CNPJ (Editar → salvar com situação Ativo) para ter dois.

Menu → **Cadastro de Colaborador**.

**Esperado:** o campo **CNPJ** aparece e é **obrigatório** — com dois CNPJs
ativos o backend recusa o cadastro sem ele. Com um único CNPJ ativo o campo
some e o sistema resolve sozinho.

**Na edição:** o campo aparece **desabilitado**. O CNPJ é o vínculo jurídico do
contrato de trabalho: mudar exige o processo administrativo auditado
(transferência de vínculo), não uma edição comum.

---

## 9. Administrador Master abre os CNPJs de um cliente (app)

Entrar no app como **Administrador Master** → menu **Empresas**.

**Esperado:** cada empresa da lista tem um botão com ícone de prédio. Clicar
abre a tela de CNPJs **daquele cliente**, com o nome da empresa no título
(`CNPJs · Grupo ACME`).

**Esperado ao cadastrar por ali:** o CNPJ nasce na empresa do recorte, não em
outra. O Master não tem empresa própria — sem o recorte, o backend recusaria
com `Campo obrigatório: company_id`.

---

## 10. O que **não** deve acontecer em lugar nenhum

- O Multi-CNPJ **não** é limitado por plano. Não existe `max_legal_entities`,
  `max_cnpjs`, `legal_entity_limit` nem `multi_cnpj_enabled_by_plan` no código.
  O plano comercial é por **número de usuários** e não gateia esta
  funcionalidade. Se aparecer qualquer mensagem de limite de CNPJ, é defeito.
- Nenhuma tela pede para "ativar" ou "habilitar" Multi-CNPJ. Não há feature
  flag: empresa com um CNPJ apenas não vê os campos extras, e passa a vê-los ao
  cadastrar o segundo.

---

## Como reportar uma divergência

Informe: o passo, o perfil usado, o que apareceu na tela e a saída do comando
de confirmação daquele passo. Com isso dá para distinguir problema de dado,
de permissão ou de código sem precisar reproduzir do zero.
