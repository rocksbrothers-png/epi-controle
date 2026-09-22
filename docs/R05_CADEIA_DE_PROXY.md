# R0.5 — qual é a cadeia de proxy, e qual valor `RATE_LIMIT_TRUSTED_PROXY_HOPS` deve ter

A R0 tirou do cliente a capacidade de escolher o próprio bucket de rate
limiting. Ela fez isso declarando a confiança em vez de adivinhá-la, com padrão
`0`: ignore o `X-Forwarded-For`, use o peer do socket.

`0` é seguro contra spoofing e pode estar **operacionalmente errado**. Se todos
os acessos chegam pelo mesmo peer da borda, o limitador enxerga milhares de
pessoas como uma origem só — e a proteção que deveria conter um atacante passa
a derrubar usuários legítimos. Essa é a lacuna que esta fatia existe para
fechar, e ela precisa ser fechada **antes** de colocarmos mais proteção baseada
em IP em cima da R0.

Esta fatia **não configura nada**. Ela determina como determinar, constrói o
instrumento de medição e trava as regressões. O número entra depois, com a
evidência na mão.

---

## 1. Contrato

<!-- CONTRATO-R05-INICIO -->
ESTADO-DA-CADEIA: INDETERMINADO
SALTOS-CONFIAVEIS: nao-determinado
MODELO-DA-BORDA: nao-determinado
ORIGENS-CORROBORADAS: nao-determinado
EVIDENCIA: nao-produzida
<!-- CONTRATO-R05-FIM -->

Este bloco é lido por gate, não só por gente. Enquanto `ESTADO-DA-CADEIA` for
`INDETERMINADO`:

- nenhuma superfície versionada dos dois repositórios pode declarar um valor
  para `RATE_LIMIT_TRUSTED_PROXY_HOPS` — declarar um número não comprovado é
  exatamente o erro que a R0 recusou;
- o padrão em `core/rate_limit.py` continua `0`;
- a sonda temporária pode existir.

Quando passar a `DETERMINADO`, os três se invertem: o valor passa a ser
**obrigatório** nas superfícies de deployment dos dois repositórios, e a sonda
passa a ser **proibida** no repositório.

O bloco é idêntico nos dois repositórios, e um gate de digesto reprova quem
editar só de um lado.

---

## 2. Três bloqueios, medidos

A R0 declarou que não conseguiu consultar a documentação da plataforma. A R0.5
mediu de novo, com controle positivo, e o quadro é pior do que "a documentação
está fora do ar":

| bloqueio | medição |
|---|---|
| documentação oficial | `render.com`, `docs.render.com` → **403 no CONNECT** (negação de política do proxy de egresso) |
| sondagem de produção | `*.onrender.com` → **403 no CONNECT** |
| controle positivo | `pypi.org` → **200**; `github.com` → **400** (alcançou o servidor) |

O egresso funciona. Estes três destinos, especificamente, estão negados por
política. Logo, do ambiente onde este código é escrito, **nem a documentação
nem o runtime são alcançáveis** — e a determinação tem de ser feita por quem
alcança.

Um quarto achado, de natureza diferente:

**`render.yaml` não é provadamente a configuração efetiva de produção.** O do
repositório corporativo não declara `DATABASE_URL`, `JWT_SECRET` nem `APP_ENV`
— e `epi_backend/config.py` recusa subir em produção sem `JWT_SECRET`. Se o
serviço sobe, esses valores vêm de outro lugar: o painel da Render. O
`docs/DEPLOY_SAAS.md` confirma o modelo ("variáveis a preencher no painel").

Consequência para esta fatia: escrever o valor em `render.yaml` **não garante**
que ele chegue ao processo. Quando o contrato for fechado, o valor precisa ir
para `render.yaml` **e** ser confirmado no painel — e o gate só consegue cobrir
a primeira metade. A segunda é do operador, e está escrita aqui para que a
lacuna seja deliberada em vez de silenciosa.

---

## 3. Como o número é determinado

### Por que uma requisição não basta

Uma cadeia de tamanho 1 é ambígua: pode ser a borda anexando o cliente, ou a
borda repassando intocado o que o cliente escreveu. As duas dão o mesmo
tamanho e exigem valores opostos — `1` numa, `0` na outra. Sem separar os
casos, o número seria um palpite com aparência de medição.

Três controles, cada um repetido três vezes:

| controle | o cliente envia | o que isola |
|---|---|---|
| **A** | nenhum `X-Forwarded-For` | quantos elementos a borda contribui sozinha |
| **B** | um sentinela | o que acontece com o que o cliente escreveu |
| **C** | três sentinelas | se a contribuição da borda muda conforme o cliente |

O valor só é aceito quando:

- as três repetições de cada controle produzem a **mesma forma** — formas
  diferentes significam mais de um caminho de borda, e uma média não protege
  ninguém;
- **B** e **C** concordam no modelo da borda;
- a contribuição da borda é **a mesma nos três controles**. Se ela variar com o
  que o cliente mandou, o modelo está errado e o script recusa o número.

### Por que uma origem não basta

Os três controles saem todos da mesma máquina e enxergam o mesmo caminho. Se o
roteamento da borda depender de origem ou região, esse caminho pode não ser o
que os outros usuários atravessam — e as repetições concordariam, de forma
perfeitamente consistente, com uma cadeia que vale só para quem mediu.

O estrago é concreto. `get_client_ip` lê `cadeia[-N]`, e o guarda é
`len(cadeia) < N`. Com `N = 2` e um caminho de **um** proxy, o cliente manda
`evil`, o proxy anexa o endereço dele, a cadeia chega como `[evil, cliente]`,
o comprimento não é menor que 2, e `cadeia[-2]` devolve `evil`. É exatamente o
bypass que a R0 fechou, reaberto com aparência de medição.

Logo o valor seguro não é o que uma origem mediu: é o **menor** entre todos os
caminhos. O script grava a forma que mediu e só certifica quando uma segunda
origem independente produz a mesma forma — `EPI_PROXY_ORIGEM`,
`EPI_PROXY_SALVAR_MEDICAO` e `EPI_PROXY_MEDICAO_ANTERIOR`. De uma origem só,
ele sai com `[MEDIDO]` e código 3, que não é sinal verde.

O rótulo da origem é declarado pelo operador e o instrumento não tem como
verificá-lo. Está assim de propósito: é um passo deliberado do procedimento,
não uma garantia do script. `ORIGENS-CORROBORADAS` registra quantas origens
sustentaram o número, e o contrato não fecha com menos de duas.

Achado levantado pela revisão automática do Codex (P1) e confirmado lendo
`core/rate_limit.py` antes de ser aceito.

### Os sentinelas

`192.0.2.10`, `192.0.2.11`, `192.0.2.12` — TEST-NET-1 (RFC 5737). Espaço de
documentação, não roteável, que nenhuma infraestrutura real emite. Se um deles
chega até a aplicação, só pode ter vindo do cliente. É isso, e só isso, que
torna a distinção entre "anexou" e "sobrescreveu" observável.

Nenhum endereço real aparece em lugar nenhum desta fatia — nem no código, nem
nos testes, nem neste documento.

### Tabela de decisão

| veredito | o que a borda fez | `RATE_LIMIT_TRUSTED_PROXY_HOPS` |
|---|---|---|
| `ANEXA` | manteve o do cliente e acrescentou N à direita | **N** |
| `SOBRESCREVE` | descartou o do cliente e escreveu por conta própria | **nenhum** — ver abaixo |
| `PASSA_DIRETO` | repassou intocado, sem acrescentar nada | **0** — o cabeçalho é escolha do cliente |
| `HIGIENIZA` | removeu o cabeçalho inteiro | **0** — não há nada encaminhado para confiar |
| `INDETERMINADO` | inseriu algo à esquerda do cliente | **nenhum** — recusar é mais honesto que ler errado |

Em `PASSA_DIRETO` e `HIGIENIZA` o `0` deixa de ser padrão de segurança e passa
a ser **a resposta medida**. Nos dois casos o peer do socket é a única origem
honesta — e se esse peer for o da borda, o colapso de origens é real e precisa
ser resolvido em outro lugar que não a posição de um cabeçalho.

### Por que `SOBRESCREVE` não vira número

A primeira versão desta tabela certificava `N` para sobrescrita, e estava
errada. Forma constante não prova que o elemento restante seja o cliente.

Contraexemplo: dois proxies, e o interno sobrescreve o `X-Forwarded-For` com o
peer **dele** — que é o proxy externo. Os três controles produzem, de forma
perfeitamente consistente, uma cadeia de um elemento sem sentinela. A regra
antiga diria `1`, e `get_client_ip` passaria a devolver o proxy externo para
todo usuário: um bucket só para a base inteira. Seria exatamente o dano que
esta frente existe para evitar, agora com aparência de medição.

Separar esse caso do benigno exige observar, de **duas origens distintas**, que
o elemento escolhido muda com o cliente. O script tem um ponto de vista só,
então recusa. Achado levantado pela revisão automática do Codex no PR e
confirmado por contraexemplo antes de ser aceito.

---

## 4. A sonda

`epi_backend/proxy_chain_probe.py`, exposta em `GET /api/proxy-chain-diagnostics`.

**O que devolve:** contagem de elementos da cadeia, posição do sentinela,
quantos elementos ficaram à direita dele, se o peer aparece na cadeia e em que
posição, a classe do peer (`privado`/`publico`/`indisponivel`) e os nomes dos
cabeçalhos de forwarding presentes, vindos de uma lista fixa.

**O que nunca devolve:** endereço nenhum. Nem o peer, nem elementos do
`X-Forwarded-For`, nem valor de cabeçalho nenhum, nem cookie, nem
`Authorization`. A saída é forma pura. O gate `R05-3` prova isso varrendo a
saída com entradas adversariais.

**Como é fechada:** exige `X-Diagnostics-Key` igual a `PROXY_CHAIN_PROBE_KEY`,
comparada com `hmac.compare_digest`. Sem a variável definida no ambiente, a
rota devolve **404** — não 403, que confirmaria a existência da sonda para quem
sondasse. Não há modo aberto, variante pública nem fallback por sessão
autenticada: um diagnóstico que descreve topologia de rede não tem versão
pública que seja útil.

**É temporária.** Diagnóstico não vira API. Quando `ESTADO-DA-CADEIA` deixar de
ser `INDETERMINADO`, o gate `R05-9` reprova a suíte enquanto o módulo, o
handler ou a rota continuarem no repositório. A remoção deixa de depender de
alguém lembrar.

---

## 5. Procedimento para fechar a R0.5

1. Definir `PROXY_CHAIN_PROBE_KEY` no serviço (painel da Render), nos dois
   ambientes. Sem isso a sonda fica inerte.
2. Rodar `scripts/certificar_cadeia_de_proxy.py` com `EPI_PROXY_CORP_URL`,
   `EPI_PROXY_CORP_KEY`, `EPI_PROXY_SAAS_URL`, `EPI_PROXY_SAAS_KEY`,
   `EPI_PROXY_ORIGEM` e `EPI_PROXY_SALVAR_MEDICAO`.
3. Rodar **de novo, de uma rede independente** — outra operadora, 4G, uma
   máquina em outra região — com um `EPI_PROXY_ORIGEM` diferente e
   `EPI_PROXY_MEDICAO_ANTERIOR` apontando para o arquivo do passo 2.
4. Conferir a evidência impressa. `NOT DETERMINED`, `INCONSISTENT` ou
   `[MEDIDO]` (código 3) significam **não configure nada** — o `0` continua
   valendo. Só `RESULTADO: cadeia determinada e corroborada por duas origens`
   libera o passo seguinte.
5. Com o número em mãos: preencher o bloco de contrato acima nos dois
   repositórios — incluindo `ORIGENS-CORROBORADAS` —, declarar
   `RATE_LIMIT_TRUSTED_PROXY_HOPS` em `env.example` e `render.yaml`, confirmar
   o valor no painel da Render, e **remover a sonda**.
6. Os gates passam a exigir exatamente isso — não é disciplina, é suíte
   vermelha.

Se os dois ambientes tiverem cadeias diferentes, cada repositório recebe o seu
próprio número. O script reprova a unificação automática.

---

## 6. O que esta fatia deliberadamente não faz

**Não configura o valor.** A evidência vem antes. Esse foi o ponto todo.

**Não altera `core/rate_limit.py`.** A investigação não encontrou defeito novo
lá. O módulo continua lendo só a variável de ambiente, e a sonda não é
consumida por nenhum caminho de produção.

**Não mexe nos limites** `10/60`, `5/300`, `60/60`, `30/60`.

**Não substitui `client_address[0]` em massa.** A investigação encontrou dezenas
de pontos que gravam o peer direto como IP de auditoria — `signature_ip` em
devoluções, `ip_address` em assinaturas de ficha, `client_ip` em entregas. Se a
medição provar que esse peer é o da borda, todos eles estão gravando o endereço
errado. Isso é um achado real e vai para issue própria: antes de unificar,
precisamos decidir se rate limiting e auditoria devem mesmo compartilhar o
mesmo dono semântico. Trocar cinquenta chamadas para responder essa pergunta
depois seria fazer na ordem errada.

**Não toca na dívida de deployment** — gunicorn, `requirements.txt` duplicado,
`app:application` inexistente e `authenticate_login` continuam nas issues
`epi-controle#1000` e `epi-controle-app#373`.
