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

for N in 1 2 3 4; do
  echo "--- hops=$N"
  curl -s -H "X-Diagnostics-Key: $CHAVE" \
          -H "X-Probe-Hops: $N" \
          -H "X-Origin-Claim: $MEU_IP" \
          -H "X-Forwarded-For: $SEM" \
          "$BACKEND/api/origin-identity-diagnostics"
done
```

**Como ler.** O `N` correto é aquele em que, **nas duas origens e nos dois
backends**:

- `candidato_bate_com_origem_declarada: true`
- `candidato_e_do_cliente: false`
- `prefixo_do_cliente_presente: true` (prova que o teste chegou de verdade)

Se nenhum `N` satisfizer isso nas duas origens, a posição **não é estável** e
o valor continua `0`. Um `N` que só funciona numa origem não é resposta.

Repita sem o `X-Forwarded-For` sentinela: `cadeia_tamanho` deve cair em 3. Se
não cair, a borda não está apenas anexando, e a leitura acima não vale.

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
| **D** | juntar instâncias repetidas de `X-Forwarded-For` | **NÃO COMPROVADO NECESSÁRIO** *(condicional)* | com **duas** instâncias e o cliente escolhendo 3 elementos na primeira, `get_client_ip` devolveu o valor do CLIENTE — bypass real. Mas só ocorre se a borda **emitir segunda instância** em vez de anexar, o que ninguém mediu. `xff_instancias_repetidas` responde isso em uma requisição |
| **E** | canonicalizar a chave de balde | **NÃO COMPROVADO NECESSÁRIO** *(condicional)* | com a borda escrevendo `::ffff:<ip>`, o balde saiu diferente do balde de `<ip>` — mesmo endereço, dois baldes. Não é bypass: a posição `-N` é escrita por proxy confiável e o cliente não escolhe a grafia. Efeito máximo: dobrar o limite para quem alterna família de endereço. `candidato_ja_canonico` responde em uma requisição |
| **F** | limitar tamanho de cabeçalho na aplicação | **NÃO COMPROVADO NECESSÁRIO** | cadeia de 5000 elementos enviada pelo cliente **não** deslocou a janela: `get_client_ip` continuou devolvendo o endereço certo. O risco real é a borda **truncar** o fim — e aí `get_client_ip` devolve dado do cliente. Mas limite na aplicação **não previne truncamento a montante**: quando o cabeçalho chega, já veio truncado. A correção proposta não trata o risco que a motivou |

**Nenhuma das três é bloqueadora.** D e E viram necessárias apenas se a
medição devolver `xff_instancias_repetidas: true` ou
`candidato_ja_canonico: false` — cada uma é correção de **uma linha**, e só
então se justifica tocar em `core/rate_limit.py`. F fica registrada como
descartada, com o motivo.

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
