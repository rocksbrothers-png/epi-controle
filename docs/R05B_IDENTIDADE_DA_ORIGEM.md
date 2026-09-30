# R0.5B — identidade da origem

## A pergunta

A R0.5 mediu a **forma** da cadeia: a borda contribui com 3 elementos, e essa
contribuição não varia com o que o cliente envia
(`docs/R05_CADEIA_DE_PROXY.md`). Isso refutou spoofing na rota medida e não
provou mais nada.

Falta a **identidade**: o elemento que `cadeia[-N]` seleciona é mesmo quem
originou a requisição, e essa posição é estável a partir de **duas origens
públicas distintas**?

A medição de campo respondeu **sim, no ambiente em que foi feita**. Fechar essa
pergunta **não** autoriza ligar `RATE_LIMIT_TRUSTED_PROXY_HOPS`. São dois
estados diferentes, e o contrato abaixo os declara em campos separados.

<!-- CONTRATO-R05B-INICIO -->
ESTADO-DA-IDENTIDADE: DETERMINADA
P1-IDENTIDADE: medida-aprovada
P2-DUAS-ORIGENS: medida-aprovada
AMBIENTE-DA-EVIDENCIA: render-free-2026-09-26-corporate-e-saas
F-CADEIA-LONGA: inconclusiva
ATIVACAO-HOPS: nao-autorizada
<!-- CONTRATO-R05B-FIM -->

Vocabulário fechado, conferido por gate:

| campo | valores |
|---|---|
| `ESTADO-DA-IDENTIDADE` | `INDETERMINADO`, `DETERMINADA` |
| `P1-IDENTIDADE`, `P2-DUAS-ORIGENS` | `nao-medida`, `medida-aprovada`, `medida-reprovada` |
| `AMBIENTE-DA-EVIDENCIA` | token livre, não vazio — onde a evidência foi obtida |
| `F-CADEIA-LONGA` | `inconclusiva`, `medida-aprovada`, `medida-reprovada` |
| `ATIVACAO-HOPS` | `nao-autorizada`, `autorizada` |

`F-CADEIA-LONGA` tem vocabulário próprio porque `inconclusiva` é um resultado
que os campos de propriedade **não** admitem: eles registram medição aprovada
ou reprovada, e F não foi nenhuma das duas. Por isso F também **não** entra na
invariante de fechamento — ver abaixo por que isso não é uma brecha.

## Medição concluída não é autorização

São duas perguntas, e confundi-las é o erro que este contrato existe para
impedir:

**`ESTADO-DA-IDENTIDADE: DETERMINADA`** diz que a identidade foi medida e
aprovada **no ambiente nomeado em `AMBIENTE-DA-EVIDENCIA`**. Nada além disso.

**`ATIVACAO-HOPS: nao-autorizada`** diz que nenhuma superfície do repositório
pode carregar `RATE_LIMIT_TRUSTED_PROXY_HOPS` diferente de `0`.

A evidência registrada aqui foi obtida no plano **Free** do Render, que é
infraestrutura provisória. A R0.5 já registra que mudança de borda — CDN
retirada ou acrescentada, hostname de origem exposto, **mudança de plano ou
região** — invalida o número em silêncio, e para pior: ele passa a apontar para
dentro do território que o cliente escreve. Mudança de borda exige nova
medição, não ajuste por dedução.

Então a barreira é esta: **`ATIVACAO-HOPS` só pode virar `autorizada` junto com
um `AMBIENTE-DA-EVIDENCIA` diferente do atual.** Ligar `HOPS > 0` no ambiente
definitivo exige revalidar lá — forma da cadeia, identidade e a propriedade que
F deixou aberta — e escrever o ambiente novo no contrato. O gate `R05B-11`
recusa autorizar com a evidência de hoje, e o digesto do bloco força que a
mudança seja deliberada em vez de acidental.

O gate não proíbe `HOPS > 0` para sempre. Ele proíbe **herdar** a autorização
de uma medição feita em outro ambiente.

Enquanto `ESTADO-DA-IDENTIDADE` era `INDETERMINADO`, a sonda temporária podia
existir e `PROXY_CHAIN_PROBE_KEY` podia ser lida. Com o fechamento, os dois se
inverteram: sonda proibida, leitura da chave proibida em qualquer lugar. O gate
`R05B-1` inverteu junto, sem edição.

## O instrumento — removido

`epi_backend/proxy_identity_probe.py` (~80 linhas) exposto em
`GET /api/origin-identity-diagnostics`, atrás de `X-Diagnostics-Key`. Sem a
variável no ambiente, a rota respondia **404** — byte a byte igual ao de uma
rota inexistente. Saiu do repositório no fechamento, com a rota e o import.

A sonda **nunca devolvia endereço**. Ela devolvia:

| campo | o que diz |
|---|---|
| `cadeia_tamanho` | quantos elementos chegaram |
| `cadeia_suficiente_para_hops` | a cadeia tem pelo menos `N` elementos |
| `candidato_bate_com_origem_declarada` | `cadeia[-N]` é o endereço que você declarou ser o seu |
| `candidato_e_do_cliente` | `cadeia[-N]` saiu do prefixo que **você** enviou — se `true`, `N` está errado |
| `prefixo_do_cliente_presente` | seu prefixo chegou à aplicação |
| `xff_instancias_repetidas` | chegou **mais de uma** instância de `X-Forwarded-For` |
| `candidato_ja_canonico` | a borda escreveu o candidato na forma canônica |

Os dois últimos existiam porque `core/rate_limit.py` lê só a **primeira**
instância (`headers.get`) e usa a string **crua** como chave de balde. Ver a
classificação de **D** e **E** abaixo.

Esta seção fica porque a tabela de evidência reporta esses campos: sem a
descrição do instrumento, a evidência deixa de ser auditável.

## Procedimento de medição

Registro histórico do que foi executado. A rota não existe mais, então o
procedimento não é executável — fica para que a evidência possa ser conferida
e, se alguém precisar remedir, para que a próxima medição parta daqui em vez de
ser reinventada.

Precisava de **duas origens públicas distintas** (ex.: banda larga e 4G) e da
chave, que ficava só no painel do Render. Nunca cole a chave, o IP nem a saída
bruta em lugar nenhum versionado.

`BACKEND` **tem de ser `https://`**. A guarda abaixo aborta antes de enviar
qualquer coisa, e `--proto '=https'` impede que um redirecionamento leve o
cabeçalho com a chave para uma conexão em claro.

Em cada origem, para cada backend:

```bash
MEU_IP=$(curl -s https://api.ipify.org)          # seu IP público
CHAVE='<valor do painel>'                        # não versione
SEM='192.0.2.1,192.0.2.2,192.0.2.3'              # prefixo sentinela (RFC 5737)

# A chave NUNCA sai em claro: aborta antes de qualquer requisição.
case "$BACKEND" in https://*) ;; *) echo "ABORTA: BACKEND precisa ser https://"; exit 1;; esac

LONGA=$(python3 -c "print(','.join(f'192.0.2.{i+1}' for i in range(100)))")

sonda() {  # $1=hops  $2=XFF (vazio = sem o cabeçalho) — 3×, e as 3 têm de concordar
  for _ in 1 2 3; do curl -s --proto '=https' \
    -H "X-Diagnostics-Key: $CHAVE" -H "X-Probe-Hops: $1" \
    -H "X-Origin-Claim: $MEU_IP" ${2:+-H "X-Forwarded-For: $2"} \
    "$BACKEND/api/origin-identity-diagnostics"; done
}

for N in 1 2 3 4; do echo "--- hops=$N"; sonda $N "$SEM"; done
echo "--- hops=3 SEM cabeçalho";      sonda 3 ""
echo "--- hops=3 cadeia longa (100)"; sonda 3 "$LONGA"
```

**Como ler.** O `N` correto é aquele em que, **nas duas origens, nos dois
backends e nas três repetições**:

- `candidato_bate_com_origem_declarada: true`
- `candidato_e_do_cliente: false`
- `prefixo_do_cliente_presente: true` (prova que o teste chegou de verdade)
- `candidato_ja_canonico: true` e `xff_instancias_repetidas: false` — são os
  dois campos que dizem se o que foi medido é o que `core/rate_limit.py` vai
  usar como chave de balde; a sonda normaliza antes de comparar, então sem
  exigi-los uma borda podia escrever forma canônica nas amostras curtas e
  expandida na longa, e os outros campos ainda passariam

Se as três repetições discordarem, há mais de um caminho de borda e a posição
**não é estável**. Se nenhum `N` satisfizer isso nas duas origens, o valor
continua `0`. Um `N` que só funciona numa origem não é resposta.

Os dois controles com `N=3` exigem, campo a campo:

| campo | sem cabeçalho | cadeia longa (100) |
|---|---|---|
| `cadeia_tamanho` | `3` | `103` |
| `candidato_bate_com_origem_declarada` | `true` | `true` |
| `candidato_e_do_cliente` | `false` | `false` |
| `prefixo_do_cliente_presente` | `false` | `true` |
| `candidato_ja_canonico` | `true` | `true` |
| `xff_instancias_repetidas` | `false` | `false` |

O primeiro representa o **cliente normal**, que não envia `X-Forwarded-For`:
conferir só o tamanho deixaria passar uma borda que monta a cadeia de outro
jeito quando o cliente cala. No segundo, tamanho abaixo de 103 significa que a
borda **truncou** — e aí `cadeia[-3]` pode cair em elemento do cliente sem que
a guarda de cadeia curta dispare.

> **Limitação registrada.** A medição demonstra ausência de truncamento até o
> tamanho efetivamente testado; não constitui prova para cadeias
> arbitrariamente maiores. Esta limitação é para ficar registrada, não para
> gerar varredura, escada, bisseção ou busca de fronteira.

### Limitação de reprodutibilidade — as duas origens

O procedimento pedia duas origens públicas **distintas** e não verificava que
elas eram distintas. A sonda compara `cadeia[-N]` com o endereço que o chamador
declara (`X-Origin-Claim`) — ela nunca devolve endereço, e por isso não tem como
dizer se a segunda execução veio de outro endereço que a primeira.

A evidência operacional usada foi **banda larga versus 4G/5G, com recaptura do
IP na Origem B** antes de medir. Isso é indício, não verificação.

`P2-DUAS-ORIGENS` continua `medida-aprovada`: o que foi observado sustenta o
campo, e não há evidência nova que o reprove. A limitação fica registrada como
**dívida de reprodutibilidade**, obrigatória de resolver antes de qualquer
certificação ou ativação futura — não nesta fatia, e não por instrumentação
nova.

## Evidência de campo — 2026-09-26

Medido nos heads `42871aec` (Corporate) e `ac30cd1` (SaaS), implantados e
`ready`, no plano **Free** do Render, com `RATE_LIMIT_TRUSTED_PROXY_HOPS=0` no
painel dos dois serviços. Duas origens públicas distintas, `N=3`, três
repetições por cenário.

| cenário | `cadeia` | `bate` | `do_cliente` | `prefixo` | `repetidas` | `canonico` | rep. |
|---|---|---|---|---|---|---|---|
| A, sem XFF | 3 | true | false | false | false | true | 3/3 |
| A, 1 sentinela | 4 | true | false | true | false | true | 3/3 |
| B, sem XFF | 3 | true | false | false | false | true | 3/3 |
| B, 1 sentinela | 4 | true | false | true | false | true | 3/3 |

Idêntico nos dois backends. A borda contribui com **exatamente 3** elementos
nos dois tamanhos, e o elemento injetado pelo cliente **não desloca**
`cadeia[-3]`: com cadeia de 3 o candidato é o índice 0, com cadeia de 4 é o
índice 1, e nos dois casos é o endereço público declarado pelo chamador.

**A identidade está estabelecida neste ambiente**: `cadeia[-3]` corresponde à
origem pública real, e a posição é estável nas duas origens, nos dois backends
e nas três repetições.

### O controle de cadeia longa NÃO foi obtido

`LONGA100` devolveu **HTTP 403 em 3/3 nos dois backends, sem corpo JSON**.
Nenhum dos quatro campos exigidos foi observado.

O que é demonstrável: **não é desta aplicação**. A rota emitia somente `404`
(não autorizado) e `200` (`medir`); os `403` do projeto são tratadores de
`PermissionError` e `PasswordChangeRequiredError` em volta de
`router.dispatch`, e aquele handler não levantava nenhuma das duas. O portão de
bootstrap responde `503`. Qual camada acima produziu o 403 — borda, WAF ou a
rede de saída da origem — a evidência **não permite nomear**, e `403` não é
status de tamanho: pode ser regra sobre o conteúdo, já que a cadeia enviada era
feita de endereços de documentação.

Consequência: permanece **não medido** o intervalo entre 2 e 99 elementos, e
não se sabe se a recusa em 100 é por tamanho ou por conteúdo. O controle fica
**INCONCLUSIVO** — não é aprovação nem reprovação.

Uma requisição recusada acima da aplicação não consegue escolher balde nenhum,
porque `get_client_ip` não é chamada para ela. Isso vale **só para as entradas
efetivamente recusadas**: como a regra que produziu o 403 não está
caracterizada, não há generalização defensável a partir dela.

### `LONGA100` era método, não a propriedade

A propriedade que F precisa provar é universal sobre **toda requisição que a
aplicação aceita**: os três elementos mais à direita da cadeia recebida foram
escritos pela borda confiável, e `cadeia[-3]` é o endereço que o proxy mais
externo observou. A guarda `len(cadeia) < N → peer` cobre só a cadeia **mais
curta** que `N`; truncamento que deixe 3 ou mais elementos não a dispara.

`LONGA100` é **um ponto amostral**. Testar exatamente 100 não é necessário — a
propriedade não menciona 100 — nem suficiente: passar em 100 nada diz sobre 99
ou 101. Nenhuma escada finita de tamanhos prova uma propriedade universal, e
foi esse regresso que levou o instrumento anterior a 7.334 linhas de diff.

Com borda que **anexa**, a aplicação não consegue distinguir o prefixo do
cliente da contribuição da borda olhando só a cadeia recebida. F é, portanto, da
mesma natureza da premissa que a R0.5 já registra como não verificável
localmente — "todo tráfego externo entra pela mesma borda, sem rota publicada
que a contorne". Fechar F exige garantia de infraestrutura no ambiente
definitivo, ou uma invariante de aplicação independente de comprimento; não
exige mais amostragem.

Por isso F não bloqueia o fechamento da identidade e também não é declarada
aprovada. Ela fica `inconclusiva`, e a barreira de `ATIVACAO-HOPS` é o que
impede que essa lacuna chegue a produção por herança.

### Por que o fechamento não autoriza ativação

`ESTADO-DA-IDENTIDADE` fechou porque as duas propriedades decisivas da
pergunta — a identidade de `cadeia[-3]` e a estabilidade a partir de duas
origens — foram medidas e aprovadas, e o gate recusa `DETERMINADA` com qualquer
uma delas fora de `medida-aprovada`.

`ATIVACAO-HOPS` continua `nao-autorizada` por três motivos, cada um suficiente:
a evidência é de infraestrutura provisória; F está `inconclusiva`; e `P2` se
apoia em indício operacional em vez de verificação. `RATE_LIMIT_TRUSTED_PROXY_HOPS`
permanece `0` em todas as superfícies do repositório e no painel.

## D, E e F — classificação

Exigência: demonstrar que, **com a posição correta já determinada**, o
comportamento atual pode escolher balde errado ou permitir bypass. Medido
contra `core/rate_limit.py` com `N=3`.

Linha de base, com borda que **anexa** (`$proxy_add_x_forwarded_for` do nginx):
com o cliente pré-semeando 3, 50 ou 5000 elementos falsos, `get_client_ip`
devolveu o endereço real do cliente em **todos** os casos. A pré-semeadura só
alonga a cadeia; `-N` conta do fim. Cadeia mais curta que `N` cai no peer.

| | correção | classificação | demonstração |
|---|---|---|---|
| **D** | juntar instâncias repetidas de `X-Forwarded-For` | **NÃO COMPROVADO NECESSÁRIO** | com **duas** instâncias e o cliente escolhendo 3 elementos na primeira, `get_client_ip` devolveu o valor do CLIENTE — bypass real. Mas depende de a borda **emitir segunda instância** em vez de anexar, e o campo ficou **medido**: `xff_instancias_repetidas: false` nas quatro células, nos dois backends, 3/3. O bypass não é alcançável nesta borda |
| **E** | canonicalizar a chave de balde | **NÃO COMPROVADO NECESSÁRIO** | com a borda escrevendo `::ffff:<ip>`, o balde saiu diferente do balde de `<ip>` — mesmo endereço, dois baldes. Não é bypass: a posição `-N` é escrita por proxy confiável e o cliente não escolhe a grafia. Campo **medido**: `candidato_ja_canonico: true` nas quatro células, nos dois backends, 3/3. A borda escreve a forma canônica |
| **F** | limitar tamanho de cabeçalho na aplicação | **INCONCLUSIVO** | em simulação, cadeia de 5000 elementos **não** deslocou a janela, e limite na aplicação **não previne truncamento a montante** — quando o cabeçalho chega, já veio truncado. Em campo o controle `LONGA100` devolveu 403 sem corpo, então o intervalo entre 2 e 99 elementos segue **não medido**. Não é "descartada": é não respondida, e o motivo está acima |

**D e E estão respondidas pela medição**: ambos os campos vieram no valor
seguro em todas as observações, então nenhuma das duas correções é necessária
nesta borda, e `core/rate_limit.py` não precisa ser tocado. **F continua
aberta**, e a barreira de ativação é o que a mantém fora de produção.

O que continua valendo sem depender de D/E/F: o `len(cadeia) < N → peer`
existente já faz o truncamento severo falhar **fechando**.

## O que esta fatia não faz

- não altera `core/rate_limit.py`;
- não aplica `RATE_LIMIT_TRUSTED_PROXY_HOPS` — o painel continua em `0`;
- não classifica `CF-Connecting-IP` nem `True-Client-IP`: são outra pergunta,
  e a sonda que os media foi removida com o resto do instrumento;
- não resolve F, e não transforma F em bloqueio permanente;
- não verifica que as duas origens eram distintas — ver a limitação acima;
- não isenta a sonda do portão de bootstrap.

## Risco histórico da instrumentação temporária

O procedimento passava a chave em `argv` (`-H "X-Diagnostics-Key: $CHAVE"`),
então ela podia ficar no histórico do shell e na tabela de processos da máquina
do operador. A sonda saiu do repositório e a chave sai do painel, então o risco
morre com o instrumento. Fica registrado porque já esteve exposto, não para
gerar redesenho de um mecanismo que não existe mais.

## Histórico, em um parágrafo

A primeira versão desta fatia construiu um certificador de ~1.550 linhas com
73 gates, endurecido em 14 rodadas de revisão automatizada até 7.334 linhas de
diff — sem nunca ter medido a borda real, porque a rota ficou atrás do portão
de bootstrap durante a janela em que foi tentada. A auditoria de 24/09
concluiu que a pergunta é de **leitura**, não de certificação automatizada:
quatro campos lidos de duas origens respondem. O certificador, os 62 gates que
só o protegiam e o histórico rodada a rodada foram removidos. A medição de
26/09 fechou a identidade e deixou F sem observação; a decisão normativa de
29/09 separou **medição concluída** de **autorização para ativar**, fechou o
contrato com a barreira de ambiente e retirou a instrumentação temporária. O
que sobrou são as propriedades que protegem **produção** e as três descobertas
de campo (D, E, F) acima, classificadas com demonstração em vez de asserção.
