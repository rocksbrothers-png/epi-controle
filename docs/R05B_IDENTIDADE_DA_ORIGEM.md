# R0.5B — identidade da origem

## A pergunta

A R0.5 mediu a **forma** da cadeia: a borda contribui com 3 elementos, e essa
contribuição não varia com o que o cliente envia
(`docs/R05_CADEIA_DE_PROXY.md`). Isso refutou spoofing na rota medida e não
provou mais nada.

Falta a **identidade**: o elemento que `cadeia[-N]` seleciona é mesmo quem
originou a requisição, e essa posição é estável a partir de **duas origens
públicas distintas**?

Enquanto a resposta não existir, `RATE_LIMIT_TRUSTED_PROXY_HOPS` permanece
`0` — o limitador ignora o cabeçalho e usa o peer do socket.

<!-- CONTRATO-R05B-INICIO -->
ESTADO-DA-IDENTIDADE: INDETERMINADO
P1-IDENTIDADE: nao-medida
P2-DUAS-ORIGENS: nao-medida
<!-- CONTRATO-R05B-FIM -->

Bloco lido por gate. Enquanto `ESTADO-DA-IDENTIDADE` for `INDETERMINADO`, a
sonda temporária **pode** existir e `PROXY_CHAIN_PROBE_KEY` **pode** ser lida
— somente por `epi_backend/proxy_identity_probe.py`. Quando passar a
`DETERMINADA`, os dois se invertem: sonda proibida, leitura da chave proibida
em qualquer lugar. O gate `R05B-1` inverte junto, automaticamente.

## O instrumento

`epi_backend/proxy_identity_probe.py` (~80 linhas) exposto em
`GET /api/origin-identity-diagnostics`, atrás de `X-Diagnostics-Key`. Sem a
variável no ambiente, a rota responde **404** — byte a byte igual ao de uma
rota inexistente.

A sonda **nunca devolve endereço**. Ela devolve:

| campo | o que diz |
|---|---|
| `cadeia_tamanho` | quantos elementos chegaram |
| `cadeia_suficiente_para_hops` | a cadeia tem pelo menos `N` elementos |
| `candidato_bate_com_origem_declarada` | `cadeia[-N]` é o endereço que você declarou ser o seu |
| `candidato_e_do_cliente` | `cadeia[-N]` saiu do prefixo que **você** enviou — se `true`, `N` está errado |
| `prefixo_do_cliente_presente` | seu prefixo chegou à aplicação |
| `xff_instancias_repetidas` | chegou **mais de uma** instância de `X-Forwarded-For` |
| `candidato_ja_canonico` | a borda escreveu o candidato na forma canônica |

Os dois últimos existem porque `core/rate_limit.py` lê só a **primeira**
instância (`headers.get`) e usa a string **crua** como chave de balde. Ver a
classificação de **D** e **E** abaixo.

## Procedimento de medição

Precisa de **duas origens públicas distintas** (ex.: banda larga e 4G) e da
chave, que fica só no painel do Render. Nunca cole a chave, o IP nem a saída
bruta em lugar nenhum versionado.

Em cada origem, para cada backend:

```bash
MEU_IP=$(curl -s https://api.ipify.org)          # seu IP público
CHAVE='<valor do painel>'                        # não versione
SEM='192.0.2.1,192.0.2.2,192.0.2.3'              # prefixo sentinela (RFC 5737)

LONGA=$(python3 -c "print(','.join(f'192.0.2.{i+1}' for i in range(100)))")

sonda() {  # $1=hops  $2=XFF (vazio = sem o cabeçalho) — 3×, e as 3 têm de concordar
  for _ in 1 2 3; do curl -s -H "X-Diagnostics-Key: $CHAVE" -H "X-Probe-Hops: $1" \
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

O primeiro representa o **cliente normal**, que não envia `X-Forwarded-For`:
conferir só o tamanho deixaria passar uma borda que monta a cadeia de outro
jeito quando o cliente cala. No segundo, tamanho abaixo de 103 significa que a
borda **truncou** — e aí `cadeia[-3]` pode cair em elemento do cliente sem que
a guarda de cadeia curta dispare.

> **Limitação registrada.** A medição demonstra ausência de truncamento até o
> tamanho efetivamente testado; não constitui prova para cadeias
> arbitrariamente maiores. Esta limitação é para ficar registrada, não para
> gerar varredura, escada, bisseção ou busca de fronteira.

## Evidência de campo — 2026-09-26

Medido nos heads `42871aec` (Corporate) e `ac30cd1` (SaaS), implantados e
`ready`, com `RATE_LIMIT_TRUSTED_PROXY_HOPS=0` no painel dos dois serviços.
Duas origens públicas distintas, `N=3`, três repetições por cenário.

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

**A identidade está estabelecida**: `cadeia[-3]` corresponde à origem pública
real, e a posição é estável nas duas origens, nos dois backends e nas três
repetições.

### O controle de cadeia longa NÃO foi obtido

`LONGA100` devolveu **HTTP 403 em 3/3 nos dois backends, sem corpo JSON**.
Nenhum dos quatro campos exigidos foi observado.

O que é demonstrável: **não é desta aplicação**. A rota emite somente `404`
(não autorizado) e `200` (`medir`); os `403` do projeto são tratadores de
`PermissionError` e `PasswordChangeRequiredError` em volta de
`router.dispatch`, e este handler não levanta nenhuma das duas. O portão de
bootstrap responde `503`. Qual camada acima produziu o 403 — borda, WAF ou a
rede de saída da origem — a evidência **não permite nomear**, e `403` não é
status de tamanho: pode ser regra sobre o conteúdo, já que a cadeia enviada
era feita de endereços de documentação.

Consequência: permanece **não medido** o intervalo entre 2 e 99 elementos, e
não se sabe se a recusa em 100 é por tamanho ou por conteúdo. O controle fica
**INCONCLUSIVO** — não é aprovação nem reprovação.

### Por que o contrato continua INDETERMINADO

O bloco de contrato tem três campos e nenhum deles é sobre truncamento; o
`LONGA100`, porém, está escrito no procedimento acima como controle
**exigido**, campo a campo. Ele não foi satisfeito, então a medição não foi
executada como especificada — e o estado **não** é promovido a `DETERMINADA`
com base numa execução incompleta. `RATE_LIMIT_TRUSTED_PROXY_HOPS` permanece
`0`.

Os campos `P1-IDENTIDADE` e `P2-DUAS-ORIGENS` seguem escritos como
`nao-medida` por conservadorismo: alterá-los é mudança do bloco de contrato,
e mudança de contrato é decisão do autor, não consequência automática de uma
medição parcial.

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
| **D** | juntar instâncias repetidas de `X-Forwarded-For` | **NÃO COMPROVADO NECESSÁRIO** | com **duas** instâncias e o cliente escolhendo 3 elementos na primeira, `get_client_ip` devolveu o valor do CLIENTE — bypass real. Mas depende de a borda **emitir segunda instância** em vez de anexar, e o campo agora está **medido**: `xff_instancias_repetidas: false` nas quatro células, nos dois backends, 3/3. O bypass não é alcançável nesta borda |
| **E** | canonicalizar a chave de balde | **NÃO COMPROVADO NECESSÁRIO** | com a borda escrevendo `::ffff:<ip>`, o balde saiu diferente do balde de `<ip>` — mesmo endereço, dois baldes. Não é bypass: a posição `-N` é escrita por proxy confiável e o cliente não escolhe a grafia. Campo **medido**: `candidato_ja_canonico: true` nas quatro células, nos dois backends, 3/3. A borda escreve a forma canônica |
| **F** | limitar tamanho de cabeçalho na aplicação | **INCONCLUSIVO** | em simulação, cadeia de 5000 elementos **não** deslocou a janela, e limite na aplicação **não previne truncamento a montante** — quando o cabeçalho chega, já veio truncado. Mas em campo o controle `LONGA100` devolveu 403 sem corpo, então o intervalo entre 2 e 99 elementos segue **não medido**. Não é "descartada": é não respondida |

**D e E estão respondidas pela medição**: ambos os campos vieram no valor
seguro em todas as observações, então nenhuma das duas correções é necessária
nesta borda, e `core/rate_limit.py` não precisa ser tocado. **F continua
aberta** — o controle que a responderia não produziu observação.

O que continua valendo sem depender de D/E/F: o `len(cadeia) < N → peer`
existente já faz o truncamento severo falhar **fechando**.

## O que esta fatia não faz

- não altera `core/rate_limit.py`;
- não aplica `RATE_LIMIT_TRUSTED_PROXY_HOPS` — o painel continua em `0`;
- não classifica `CF-Connecting-IP` nem `True-Client-IP`: são outra pergunta,
  e a sonda que os media foi removida com o resto do instrumento;
- não decide o `3` declarado em `render.yaml`, que é contrato documentado e
  decisão do autor;
- não isenta a sonda do portão de bootstrap.

## Histórico, em um parágrafo

A primeira versão desta fatia construiu um certificador de ~1.550 linhas com
73 gates, endurecido em 14 rodadas de revisão automatizada até 7.334 linhas de
diff — sem nunca ter medido a borda real, porque a rota ficou atrás do portão
de bootstrap durante a janela em que foi tentada. A auditoria de 24/09
concluiu que a pergunta é de **leitura**, não de certificação automatizada:
quatro campos lidos de duas origens respondem. O certificador, os 62 gates que
só o protegiam e o histórico rodada a rodada foram removidos. O que sobrou são
as propriedades que protegem **produção**, e as três descobertas de campo
(D, E, F) acima, classificadas com demonstração em vez de asserção.
