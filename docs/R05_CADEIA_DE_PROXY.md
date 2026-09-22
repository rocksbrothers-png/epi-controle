# R0.5 — a cadeia de proxy, medida, e o valor de `RATE_LIMIT_TRUSTED_PROXY_HOPS`

A R0 tirou do cliente a capacidade de escolher o próprio bucket de rate
limiting. Ela fez isso declarando a confiança em vez de adivinhá-la, com padrão
`0`: ignore o `X-Forwarded-For`, use o peer do socket.

`0` era seguro contra spoofing e estava **operacionalmente errado**. Todos os
acessos chegam pelo mesmo peer da borda, então o limitador enxergava a base
inteira como uma origem só — a proteção que deveria conter um atacante passava a
derrubar usuário legítimo.

Esta fatia mediu a cadeia em produção e fechou o contrato. O número é **3**, e
ele veio de medição, não de documentação presumida.

---

## 1. Contrato

<!-- CONTRATO-R05-INICIO -->
ESTADO-DA-CADEIA: DETERMINADO
SALTOS-CONFIAVEIS: 3
MODELO-DA-BORDA: ANEXA
ORIGENS-CORROBORADAS: 1
EVIDENCIA: medicao-render-2026-09-22-corporate-e-saas
<!-- CONTRATO-R05-FIM -->

Este bloco é lido por gate, não só por gente. Com `ESTADO-DA-CADEIA` em
`DETERMINADO`:

- `RATE_LIMIT_TRUSTED_PROXY_HOPS=3` é **obrigatório** nas superfícies de
  deployment versionadas dos dois repositórios;
- a sonda temporária é **proibida** no repositório;
- `PROXY_CHAIN_PROBE_KEY` deixa de ser dependência de qualquer caminho.

O bloco é idêntico nos dois repositórios, e um gate de digesto reprova quem
editar só de um lado.

---

## 2. A medição

Executada contra os dois serviços reais no Render, em 2026-09-22, com a sonda
temporária `GET /api/proxy-chain-diagnostics` — já removida. Três controles,
três repetições cada, com sentinelas de TEST-NET-1 (`192.0.2.0/24`, RFC 5737:
espaço de documentação, não roteável, que nenhuma infraestrutura real emite).

Corporate e SaaS produziram **exatamente a mesma forma**:

| controle | o cliente envia | cadeia recebida | sentinela | à direita | contribuição da borda |
|---|---|---|---|---|---|
| **A** | nada | 3 | — | — | **3** |
| **B** | 1 sentinela | 4 | índice 0 | 3 | **3** |
| **C** | 3 sentinelas | 6 | índice 2 | 3 | **3** |

Cabeçalhos de forwarding recebidos, nos dois ambientes: `X-Forwarded-For`,
`X-Forwarded-Proto`, `CF-Connecting-Ip`, `True-Client-Ip`. O peer do socket é
**privado** e **não aparece** na cadeia.

### O que cada controle estabelece

**A contribuição da borda é 3, e é constante.** Em A o cliente não mandou nada e
chegaram 3 elementos. Em B mandou 1 e chegaram 4. Em C mandou 3 e chegaram 6.
Três amostras, a mesma contribuição — a borda não muda o que acrescenta conforme
o que o cliente escreve.

**O cliente não consegue deslocar a janela.** Este é o ponto que decide a
segurança do número, e quem o prova é o controle C. Se a borda acrescentasse
menos quando o cliente mandasse mais, `cadeia[-3]` cairia em território
controlado pelo cliente. Ela não muda: em C o último sentinela ficou no índice 2
com 3 elementos à direita, exatamente como em B.

**O modelo é `ANEXA`.** Em B e C o sentinela sobreviveu, na posição 0, com a
contribuição da borda à direita dele. A borda preserva o que o cliente escreveu
e acrescenta.

> **Sobre o `SOBRESCREVE` do controle A.** A sonda classificava cada amostra
> isoladamente, e em A nenhum sentinela é enviado — uma cadeia não vazia sem
> sentinela é, para aquele classificador, sobrescrita. É artefato do controle,
> não contradição: A existe para medir a contribuição da borda sozinha, e o
> modelo vem de B e C, que são os controles que carregam sentinela.

### Por que 3 é o número certo

Num encadeamento onde cada proxy **acrescenta** o endereço do peer dele, com 3
proxies confiáveis entre cliente e aplicação a cadeia chega assim:

```
cliente manda:   X-Forwarded-For: <lixo do cliente>
P1 acrescenta:   <lixo>, <cliente>
P2 acrescenta:   <lixo>, <cliente>, <P1>
P3 acrescenta:   <lixo>, <cliente>, <P1>, <P2>
aplicação vê:    peer = P3
```

`cadeia[-3]` é `<cliente>` — o endereço que o proxy mais externo observou. É o
que `get_client_ip` devolve com `TRUSTED_PROXY_HOPS = 3`, e bate com as três
medições:

| controle | cadeia | `cadeia[-3]` |
|---|---|---|
| A | 3 elementos | índice 0 — o cliente |
| B | 4 elementos | índice 1 — o cliente, logo após o sentinela |
| C | 6 elementos | índice 3 — o cliente, logo após os três sentinelas |

---

## 3. O que a medição NÃO estabelece

**Uma origem mede um caminho.** A medição saiu de uma máquina. Se o roteamento
da borda dependesse de origem ou região, uma rota que atravessasse menos de 3
proxies faria `cadeia[-3]` devolver um elemento escrito pelo cliente — o bypass
que a R0 fechou. Três repetições de cada controle não cobrem isso: elas saem
todas do mesmo lugar.

`ORIGENS-CORROBORADAS: 1` registra esse limite em vez de escondê-lo. Amostragem
refuta um roteamento divergente; ela não prova que toda rota tenha esta forma.
O que fecharia a lacuna é uma premissa de arquitetura — *todo tráfego externo
entra pela mesma borda, sem rota publicada que a contorne* — que nenhum
instrumento local verifica.

**Consequência prática, e o que fazer com ela:** se a topologia de borda mudar
— Cloudflare retirado ou acrescentado, hostname de origem exposto diretamente,
mudança de plano ou região no Render — o número 3 deixa de valer **em silêncio**,
e para pior: ele passa a apontar para dentro do território que o cliente
escreve. Mudança de borda exige nova medição, não ajuste por dedução.

**O peer do socket não é o cliente.** `peer_na_cadeia=não` e `peer=privado` nos
dois ambientes: o endereço da outra ponta do socket é da infraestrutura da
borda, não de quem fez a requisição. Todo ponto que grava esse peer como IP de
auditoria está gravando o endereço errado. Isso é achado próprio, com issue
própria — ver §6.

---

## 4. O que ficou versionado e o que é do operador

O gate cobre o que está no repositório. Metade da configuração efetiva não está.

| superfície | quem aplica | gate cobre? |
|---|---|---|
| `env.example` | ninguém (é exemplo) | sim — o valor tem de estar lá |
| `render.yaml` | blueprint, quando aplicado | sim — o valor tem de estar lá |
| painel do Render | **o operador, à mão** | **não** |

`render.yaml` **não é provadamente a configuração efetiva**: o do repositório
corporativo não declara `DATABASE_URL`, `JWT_SECRET` nem `APP_ENV`, e
`epi_backend/config.py` recusa subir em produção sem `JWT_SECRET`. Se o serviço
sobe, esses valores vêm do painel — o `docs/DEPLOY_SAAS.md` confirma o modelo.

Escrever `3` em `render.yaml` **não garante** que `3` chegue ao processo. A
segunda metade é do operador, e está escrita aqui para ser deliberada em vez de
silenciosa.

### Instruções para o operador, nos dois serviços

1. **Adicionar** a variável de ambiente:
   `RATE_LIMIT_TRUSTED_PROXY_HOPS` = `3`
2. **Remover** a variável `PROXY_CHAIN_PROBE_KEY`, que existia só para a sonda.
   Sem a sonda no código ela não faz nada; removê-la evita deixar credencial
   órfã no painel.
3. **Redeploy é necessário.** As variáveis são lidas no import de
   `core/rate_limit.py`, ou seja, na subida do processo. Alterar no painel sem
   reiniciar não muda o comportamento do processo que já está rodando. No
   Render, salvar variáveis de ambiente dispara um deploy automaticamente; se o
   serviço estiver com deploy manual, dispare um *Manual Deploy → Deploy latest
   commit*.
4. **Conferir depois do deploy** que o rate limiting passou a separar origens:
   com `3`, dois clientes distintos deixam de compartilhar bucket. Se todos
   continuarem colapsando num só, a variável não chegou ao processo.

Os serviços são `epi-controle` (corporativo) e
`epi-controle-app-livamobile-api` (SaaS). O static site do SaaS não roda o
backend e não precisa da variável.

---

## 5. Fail-closed preservado

O valor declarado não afrouxa nenhuma das proteções da R0:

| situação | comportamento | por quê |
|---|---|---|
| variável ausente | `0` — ignora o cabeçalho, usa o peer | ausência de configuração nunca vira confiança |
| valor negativo | `0` — `max(0, ...)` | idem |
| cadeia mais curta que 3 | peer do socket | a requisição não atravessou a cadeia esperada; nada nela prova origem |
| cliente manda lixo | `cadeia[-3]` continua sendo o cliente | a borda acrescenta 3 independentemente — medido em C |

`get_client_ip` continua sem ler `cadeia[0]` e sem `split(',')[0]`. O primeiro
elemento é escrito pelo cliente e nunca volta a ser origem.

---

## 6. O que esta fatia deliberadamente não faz

**Não substitui `client_address[0]` em massa.** A medição provou que o peer é da
borda. São **35 pontos em 15 arquivos**, em cada repositório, gravando esse peer
como IP de auditoria — `signature_ip` em devoluções, `ip_address` em assinaturas
de ficha, `client_ip` em entregas, `ip` em configurações, e o portal do
fornecedor. Trocar as 35 chamadas por `get_client_ip` responderia antes de
perguntar se rate limiting e auditoria devem compartilhar o mesmo dono
semântico. Vai para issue própria.

**Não toca na dívida de deployment** — gunicorn, `requirements.txt` duplicado,
`app:application` inexistente e `authenticate_login` seguem em
`epi-controle#1000` e `epi-controle-app#373`. Sem migração para gunicorn, sem
mudança de worker count, sem mudança de Start Command.

**Não mexe nos limites** `10/60`, `5/300`, `60/60`, `30/60`. A proposta
quantitativa é da R1.

**Não altera a lógica de `core/rate_limit.py`.** A investigação não encontrou
defeito novo lá. Só a configuração mudou de estado: de "não declarada" para
"declarada e medida".

---

## 7. Como isto seria refeito

A sonda e o script de certificação saíram do repositório — diagnóstico não vira
API, e código que não roda mais é dívida. O método fica registrado aqui para
quem precisar medir de novo:

1. Uma rota temporária, fechada por chave de ambiente, que devolva **só a forma**
   da cadeia recebida: quantos elementos, posição do sentinela, quantos ficaram
   à direita dele, se o peer aparece na cadeia, a classe do peer. Nenhum
   endereço na resposta.
2. Três controles — sem `X-Forwarded-For`, com um sentinela de TEST-NET-1, com
   três sentinelas —, cada um repetido, aceitando o número só quando as
   repetições concordam, B e C concordam no modelo, e a contribuição da borda é
   a mesma nos três.
3. Ler o resultado pela tabela do §2, e registrar aqui a evidência antes de
   configurar qualquer coisa.

A implementação anterior está no histórico do PR que fechou esta fatia.
