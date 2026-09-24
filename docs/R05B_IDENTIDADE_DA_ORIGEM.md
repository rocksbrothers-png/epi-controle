# R0.5B — a identidade da origem, e o que falta para `HOPS=3` estar provado

A R0.5 mediu a **forma** da cadeia de proxy: a borda contribui com 3 elementos,
e essa contribuição não muda com o que o cliente envia. Isso refutou spoofing
na rota medida e **não provou mais nada**.

O que ficou sem observação é a **identidade**: que `cadeia[-3]` represente quem
originou a requisição. `docs/R05_CADEIA_DE_PROXY.md` §2 registra a distinção
entre o medido e o inferido; esta fatia existe para fechar o inferido.

Enquanto ela não fechar, `RATE_LIMIT_TRUSTED_PROXY_HOPS` **não é aplicado**.

---

## 1. Contrato

<!-- CONTRATO-R05B-INICIO -->
ESTADO-DA-IDENTIDADE: INDETERMINADO
P1-IDENTIDADE: nao-medida
P2-DUAS-ORIGENS: nao-medida
P3-CF-CONNECTING-IP: nao-medida
P3-TRUE-CLIENT-IP: nao-medida
P4-SUFIXO-PRESERVADO: nao-medida
HOSTNAMES-COBERTOS: nao-medidos
<!-- CONTRATO-R05B-FIM -->

Bloco lido por gate. Enquanto `ESTADO-DA-IDENTIDADE` for `INDETERMINADO`:

- a sonda temporária de identidade **pode** existir;
- `PROXY_CHAIN_PROBE_KEY` **pode** ser lida, e **somente** pelas superfícies
  declaradas no §5;
- `HOPS=3` permanece **PARCIALMENTE PROVADO**, e a variável não é aplicada.

Quando passar a `DETERMINADA`, os três se invertem: a sonda passa a ser
proibida, a leitura da chave passa a ser proibida em qualquer lugar, e o
veredito de `HOPS` passa a depender do §4.

### Vocabulário fechado, e por que fechar exige evidência

| campo | valores |
|---|---|
| `ESTADO-DA-IDENTIDADE` | `INDETERMINADO` · `DETERMINADA` |
| `P1-IDENTIDADE`, `P2-DUAS-ORIGENS`, `P4-SUFIXO-PRESERVADO` | `nao-medida` · `provada` · `reprovada` |
| `P3-CF-CONNECTING-IP`, `P3-TRUE-CLIENT-IP` | `nao-medida` · `sentinela-sobrevive` · `substituida` · `ausente` |
| `HOSTNAMES-COBERTOS` | `nao-medidos` · a lista medida |

`R05B-1` recusa `DETERMINADA` enquanto P1, P2 e P4 não forem `provada`, os dois
campos de P3 continuarem `nao-medida`, ou os hostnames continuarem
`nao-medidos`.

Isso fechou o buraco mais sério do conjunto. Antes, o gate conferia só que o
estado era uma das duas palavras: dava para trocar `INDETERMINADO` por
`DETERMINADA`, recalcular o digesto, deixar todo o resto em `nao-medida` — e,
depois que a sonda e o script saíssem, **nada mais reprovava esse fechamento
sem medição nenhuma**. O instrumento inteiro existe para impedir exatamente
isso.

`HOSTNAMES-COBERTOS` precisa **nomear** as duas entradas onde `HOPS` será
aplicado; "diferente de `nao-medidos`" aceitava vazio e aceitava
`qualquer-coisa`.

### O que o digesto de paridade prova, e o que não prova

Ele é **auto-referente**: compara o documento com uma constante ao lado dele, no
mesmo repositório. Editar os dois juntos passa — então ele **não observa o outro
repositório e não prova paridade**.

O que ele pega é a edição unilateral que esquece a constante, que é o acidente
comum; e como a constante é a mesma nos dois lados, qualquer mudança legítima
obriga a tocar os dois. É quebra-molas com dente, não prova. Provar paridade
exigiria um passo de CI comparando os dois repositórios, fora do escopo desta
fatia.

A sabotagem `M` está rotulada de acordo: ela prova que o gate pega a **edição
sem recálculo**, não que pega divergência entre repositórios.

---

## 2. As quatro propriedades

### P1 — identidade

O elemento em `cadeia[-N]` é o endereço público que o próprio chamador observa
como sendo o seu?

O chamador declara o endereço em `X-Origin-Claim`. A sonda compara internamente
e devolve **apenas** `candidato_bate_com_origem_declarada: true/false`. Nenhum
dos dois endereços sai na resposta.

**A reivindicação nunca entra na construção do candidato.** O candidato sai do
`X-Forwarded-For` e só dele. Três booleanos deixam o script provar que o teste
não foi contaminado, em vez de assumir:

| booleano | o que denuncia |
|---|---|
| `prefixo_do_cliente_presente` | algum elemento da cadeia é sentinela |
| `cadeia_maior_que_hops` | o cliente acrescentou algo à esquerda |
| `reivindicacao_fora_do_candidato` | o valor declarado aparece em outra posição |

P1 só é válido com os três **falsos**. O controle de P1 não envia
`X-Forwarded-For`: assim toda a cadeia recebida foi escrita pela borda.

### P2 — duas origens públicas distintas

P1 verdadeiro numa origem só não distingue "o candidato é o cliente" de "o
candidato é um proxy compartilhado que por acaso é o endereço que o chamador
julga ter".

São necessárias **duas origens públicas realmente distintas**. Não contam: duas
execuções seguidas, dois navegadores, dois aparelhos atrás do mesmo NAT, nem
variar `X-Forwarded-For` à mão.

A distinção é provada **sem registrar endereço nenhum**, por dupla
reivindicação. Na segunda origem o chamador declara o próprio endereço **e** o
da primeira:

```
origem A:   candidato_bate_com_origem_declarada = true
origem B:   candidato_bate_com_origem_declarada = true
            candidato_bate_com_origem_alternativa = false   ← A ≠ B
```

O terceiro booleano é o que fecha: o candidato em B não é o endereço de A, logo
os candidatos diferem, logo o candidato acompanha o chamador. O relatório
registra só `ORIGEM_A != ORIGEM_B: true`.

**E declarar não é medir.** Os dois booleanos acima, sozinhos, não bastavam:
`EPI_IDENT_IP_ANTERIOR` com qualquer endereço válido diferente do candidato —
um endereço inventado, um erro de digitação — faria
`candidato_bate_com_origem_alternativa` dar `false`, e o veredito leria isso
como prova de duas origens. **Uma máquina só certificava
`ORIGEM_A != ORIGEM_B`.**

Por isso a primeira origem grava um **compromisso**: `sha256(sal || endereço)`,
com sal aleatório, e só o grava se P1 tiver sido verdadeiro ali, em cada
backend. A segunda recalcula o compromisso a partir do que foi declarado e
exige que bata — além de exigir rótulo de origem diferente, o mesmo `N`, e P1
verdadeiro nos dois backends já na primeira.

O arquivo fica **fora do repositório** (`~/.r05b_origem_anterior.json`), nunca é
impresso, e o relatório diz apenas se o vínculo bateu. Gates `R05B-11` e
`R05B-11b`.

Três coisas que a primeira versão do vínculo deixou passar:

- **o compromisso era reversível.** `sha256(sal ‖ endereço)` com o sal guardado
  ao lado: o sal impede tabela precomputada e não impede enumeração — IPv4 tem
  2^32 valores, e o roteiro manda levar o arquivo de uma máquina para outra.
  Agora é `scrypt` (memória-dura), que não torna a recuperação impossível mas
  torna o custo proibitivo. Gate `R05B-22`.
- **o vínculo não amarrava o endpoint.** Os rótulos `corporativo` e `saas` são
  estáticos: trocar uma URL entre A e B combinaria P1 de um serviço com P2 de
  outro. O estado guarda as URLs medidas. Gate `R05B-19`.
- **os dois backends podiam ser o mesmo endpoint.** Exigir as duas variáveis não
  basta se apontarem para o mesmo lugar: um deployment se compara consigo mesmo
  e passa por dois. Gate `R05B-18`.

### P3 — confiança dos cabeçalhos de identidade

`CF-Connecting-IP` e `True-Client-IP` chegaram à aplicação na medição da R0.5,
**mas o instrumento nunca os enviou** — então só se sabe que a borda os injeta
quando ausentes. Se ela **sobrescreve** um valor fornecido pelo cliente é
pergunta sem medição.

A assimetria é o motivo de não se poder adotar por inferência:

| se a borda… | consequência |
|---|---|
| **sobrescreve** | melhor que contar posição: não depende de `N`, e continua correto numa rota mais curta |
| **repassa o do cliente** | o cliente nomeia o próprio balde com **um cabeçalho**, em toda rota, e `HOPS` vira irrelevante |

Teste: enviar sentinela de TEST-NET-1 em cada um e classificar o que chega.

| classificação | leitura |
|---|---|
| `sentinela_sobrevive` | o cliente controla o cabeçalho → **não adotável** |
| `substituida` | a borda o reescreveu → candidato a fonte confiável |
| `ausente` | a borda o removeu |

P3 **não entra no critério de `HOPS`** — o limitador é posicional sobre
`X-Forwarded-For` e não lê esses cabeçalhos. Mas `sentinela_sobrevive` é achado
grave por conta própria: significa que o cliente controla um cabeçalho de
identidade, em toda rota. O relatório o destaca em `ALERTA P3`, e o veredito
deixou de anunciar "todas as propriedades satisfeitas" — ele diz exatamente
quais. Gate `R05B-16`.

**`X-Forwarded-For` já está classificado pela R0.5**: os controles B e C
mostraram o sentinela sobrevivendo no índice 0. O cliente controla o prefixo.
Por isso a confiança nele é **posicional** — vale a janela `cadeia[-N]`, nunca o
cabeçalho inteiro — e depende de `N` estar certo em toda rota.

### P4 — truncamento

Uma cadeia longa enviada pelo cliente pode deslocar ou truncar a região que
`cadeia[-N]` consome. Teste: enviar cadeia longa composta só de endereços
reservados.

**`sufixo_confiavel_preservado` é definido como: nenhum dos `N` elementos mais à
direita é sentinela.** É essa a janela que a seleção consome, e é ela que um
truncamento pela direita destruiria — empurrando `cadeia[-N]` para dentro do que
o cliente escreveu.

Truncamento pela **esquerda** não quebra a propriedade: descarta prefixo do
cliente, que já era ignorado. Por isso a definição olha só a janela.

---

## 3. Hostnames

A matriz precisa cobrir as entradas públicas relevantes. Nenhuma equivalência é
assumida: cada hostname é medido, ou registrado como não comprovado.

| hostname | papel | estado |
|---|---|---|
| `epi-controle-app-gupy.onrender.com` | API corporativa | a medir |
| `epi-controle-app-livamobile-api.onrender.com` | API SaaS | a medir |
| `epi-controle.onrender.com` | documentado como Produção em `spec/09-deployment.md:7`; o `render.yaml` corporativo declara `name: epi-controle` | **a investigar** — pode não existir, não responder, ou não ser o mesmo serviço |

**Domínios customizados:** o produto suporta CNAME de cliente
(`modules/tenant/domains_service.py`, resolução por `Host` em
`modules/tenant/service.py:50`). Capacidade do produto **não é prova de domínio
ativo**. Enquanto não houver evidência de um domínio configurado e acessível, o
registro é `nenhum domínio customizado ativo comprovado`.

### 3.1 DNS não decide se um serviço existe — medido

`*.onrender.com` é **wildcard**. Medido em 2026-09-23: um nome inventado
(`nome-que-nao-existe-r05b-7f3a91.onrender.com`) resolve para os **mesmos**
endereços e a **mesma** cadeia de CNAME que `epi-controle.onrender.com` e que os
dois serviços medidos:

```
<nome qualquer>.onrender.com
  → gcp-us-west1-1.origin.onrender.com.cdn.cloudflare.net
  → o MESMO par de endereços, para todos os nomes acima
```

> Os endereços não são transcritos aqui de propósito: o gate `R05B-10` proíbe
> literal fora de faixa reservada em qualquer superfície da fatia, e ele
> reprovou a primeira redação desta seção. O que importa é a igualdade, não o
> valor — e a igualdade é reproduzível com `getent hosts`.

Consequência direta: **resolver DNS não é evidência de que o serviço existe.**
`epi-controle.onrender.com` continua `NÃO COMPROVADO`, e só uma resposta HTTP
da aplicação decide — nunca o DNS.

A cadeia terminar em `.cdn.cloudflare.net` **corrobora** a Cloudflare estar à
frente da borda do Render, o que é consistente com `CF-Connecting-IP` ter
chegado à aplicação na R0.5. Corrobora e nada mais: o registro é do wildcard
compartilhado, não de um serviço, e não diz **qual** elemento da cadeia é qual.
Identidade continua sendo o que o §2 mede.

### 3.2 Por que a medição é humana

O ambiente onde este agente roda tem política de egresso que **nega CONNECT**
para `*.onrender.com` — os três hostnames foram recusados com o mesmo 403 do
gateway, inclusive os dois que se sabe estarem vivos. Logo a recusa **não é
evidência** sobre nenhum deles.

Some-se a isso as duas origens públicas realmente distintas que o P2 exige, que
um agente em container único não tem. A medição é do operador, e as instruções
exatas estão em `scripts/certificar_identidade_da_origem.py`.

---

## 4. Critério para `HOPS=3` PROVADO

Só com **todos** os itens satisfeitos:

- [ ] rota relevante sem caminho mais curto conhecido;
- [ ] P1 verdadeiro;
- [ ] P2 verdadeiro em duas origens públicas distintas;
- [ ] ausência de controle do cliente sobre o elemento efetivamente
      selecionado (`candidato_e_do_cliente: false`);
- [ ] P4 preservando a janela (`sufixo_confiavel_preservado: true`);
- [ ] resultado equivalente nos dois backends onde `HOPS` será aplicado.

Faltando qualquer um: **`HOPS=3` permanece PARCIALMENTE PROVADO** e
`RATE_LIMIT_TRUSTED_PROXY_HOPS` permanece `0` no ambiente.

Refutar spoofing não prova atribuição correta. As três classificações são
distintas:

| | significado | estado na R0.5 |
|---|---|---|
| **A** spoofing | o cliente escolhe o próprio balde | refutado **na rota medida** |
| **B** colapso | clientes distintos caem no mesmo balde | **não excluído** |
| **C** atribuição correta | clientes distintos recebem baldes da origem observada | **não provado** |

---

## 5. A sonda

`epi_backend/proxy_identity_probe.py`, em `GET /api/origin-identity-diagnostics`.

**Superfícies que podem ler `PROXY_CHAIN_PROBE_KEY`** enquanto esta fatia está
aberta, e só elas:

- `epi_backend/proxy_identity_probe.py`
- `modules/auth/routes.py`, dentro das cercas `R0.5B SONDA TEMPORÁRIA`
- `scripts/certificar_identidade_da_origem.py`
- este documento e `tests/test_r05b_identidade_da_origem.py`

**O que devolve:** booleanos, contagens estritamente necessárias e
classificações de vocabulário fixo. **Nunca** endereço, cadeia, valor de
cabeçalho, cookie ou token. O gate `R05B-2` prova por varredura adversarial.

**O oráculo, dito em voz alta.** `candidato_bate_com_origem_declarada` é um
oráculo de igualdade: quem tem a chave pode testar endereços um a um. Aceito
deliberadamente — a chave é do operador, a sonda é temporária, e sem esse
booleano a identidade continua não observável. O que não é aceito é devolver o
endereço, que trocaria um oráculo lento por vazamento direto.

**Falha fechada:** sem `PROXY_CHAIN_PROBE_KEY` no ambiente, 404 — com o mesmo
corpo de `app.not_found()`, para não confirmar a existência da rota.

**É temporária.** Quando `ESTADO-DA-IDENTIDADE` deixar de ser `INDETERMINADO`, o
gate `R05B-7` reprova a suíte enquanto o módulo, o handler, a rota ou o script
continuarem no repositório, e `R05-6` volta a proibir a leitura da chave em
qualquer lugar.

---

## 6. O que esta fatia deliberadamente não faz

**Não aplica `RATE_LIMIT_TRUSTED_PROXY_HOPS`.** Nem no repositório — onde já
está declarado em `render.yaml` desde a R0.5 — nem no painel do Render, que é a
configuração efetiva.

**Não altera `core/rate_limit.py`.** A fatia é certificação e configuração de
deployment. Qualquer alteração futura da lógica do limitador continua sujeita às
regras normais do repositório.

**Não corrige `AGENTS.md`** nem cria exceção permanente nele.

**Não corrige o flake do bucket global** — `epi-controle#1002` e
`epi-controle-app#375` são fatia própria posterior.

**Não corrige a divergência de nome de serviço** entre o `render.yaml`
corporativo (`name: epi-controle`) e o serviço medido
(`epi-controle-app-gupy`). Achado
registrado, correção fora de escopo.

---

## 7. O instrumento falhou na revisão, antes de medir

Uma revisão automatizada encontrou **nove defeitos** na primeira versão desta
fatia. Três deles deixavam o instrumento certificar o que ele existe para
impedir:

| | defeito | consequência | gate |
|---|---|---|---|
| 1 | P2 aceitava `IP_ANTERIOR` declarado, sem lastro | **uma máquina certificava duas origens** | `R05B-11`, `R05B-11b` |
| 2 | um backend configurado bastava | **meia certificação anunciada como inteira** | `R05B-12` |
| 3 | `DETERMINADA` sem P1–P4 medidos | **fechamento sem evidência nenhuma** | `R05B-1` |
| 4 | hostname alternativo contraditório era informativo | mais de um caminho de borda numa entrada pública, ignorado | `R05B-13` |
| 5 | guardas de contaminação fora de `CAMPOS_DECISIVOS` | repetição contaminada passava por idêntica | `R05B-14` |
| 6 | campo malformado virava `TypeError` | traceback no lugar do código de saída | `R05B-15` |
| 7 | `EPI_IDENT_HOPS` inválido virava `ValueError` | erro de digitação com o mesmo status de propriedade reprovada | `R05B-15` |
| 8 | P3 fora do veredito | `sentinela_sobrevive` dentro de um "tudo certo" | `R05B-16` |
| 9 | import incondicional do script nos testes | nenhum estado fechado com a suíte verde | coleta, sabotagem V |

Nenhum foi encontrado por gate meu: os 19 primeiros gates cobriam a **sonda** e
não o **veredito**. Os dezenove não eram suficientes — e a medição ainda não
tinha rodado, então o custo foi só de tempo.

Cada correção ganhou gate, e cada gate foi provado por sabotagem (N–V): defeito
reintroduzido, gate vermelho, defeito revertido, gate verde. A sabotagem U foi
refeita recalculando o digesto junto, senão ela provaria só o gate de paridade.

Um décimo achado — "remova a rota de diagnóstico de produção, `AGENTS.md` só
permite refatoração estrutural" — é decisão já tomada pelo autor, não defeito.
A resposta está na thread: a sonda é autorizada, protegida por chave, 404 por
omissão, e sai por gate quando a certificação fechar.

### Segunda rodada: mais nove, e um padrão

A revisão voltou sobre a versão corrigida e achou **mais nove**. O padrão é
instrutivo: quase todos são *a correção anterior fechou metade do caso*.

| | achado | a metade que faltou | gate |
|---|---|---|---|
| 1 | alternativo com negativo **estável** | só a contradição reprovava | `R05B-17` |
| 2 | os dois backends podiam ser o **mesmo** endpoint | exigi as variáveis, não que fossem distintas | `R05B-18` |
| 3 | o vínculo não amarrava o **endpoint** | amarrei o IP anterior, não o serviço | `R05B-19` |
| 4 | `HOSTNAMES-COBERTOS` aceitava qualquer valor | rejeitei um placeholder, não validei a lista | `R05B-1` |
| 5 | campo **ausente** virava guarda falsa | rejeitei container, não ausência (`None` é escalar) | `R05B-20` |
| 6 | `hops_avaliado` nunca conferido | a sonda satura em `HOPS_MAXIMO` | `R05B-21` |
| 7 | compromisso **reversível** em segundos | sal impede tabela, não enumeração | `R05B-22` |
| 8 | digesto de paridade é auto-referente | limitação real — registrada, não "corrigida" | §1 |
| 9 | gates ainda liam o script removido | corrigi o import, não as leituras | `R05B-23` |

O achado 9 tinha consequência concreta: **o estado fechado não existia com a
suíte verde**, então a promessa de remoção não era executável. Agora é, e está
verificado — contrato `DETERMINADA`, sonda, script, handler e rota removidos:
**53 gates passam**.

`R05B-23` é meta-gate: varre este próprio arquivo por `ast` e reprova qualquer
teste que use o script sem guarda. Ele também nasceu fraco — usava fronteira de
função por texto, engolia os helpers de módulo entre os testes e acusou o
`R05B-10`, que nem usa o script. Gate que erra a fronteira acusa o inocente e
deixa passar o culpado.

### Terceira rodada: mais seis, e o mesmo padrão

| | achado | a lacuna que a correção anterior abriu | gate |
|---|---|---|---|
| 1 | o alternativo **emprestava** o vínculo dos obrigatórios | reprovei o contraditório e o negativo estável, e deixei o veredito dele depender de um `p2_alt` que ele não tem | `R05B-24` |
| 2 | estado carregado sem validar esquema | `backends_com_p1` como inteiro → `TypeError` fora de todo caminho controlado | `R05B-25` |
| 3 | sentinela procurado **só no primeiro elemento** | borda que antepõe e preserva (`real, 192.0.2.10`) dava `substituida` com o sentinela vivo | `R05B-26` |
| 4 | P4 não conferia identidade | sufixo intacto apontando para proxy compartilhado: P1 passa sem cabeçalho, P4 passa com outro candidato, e a cadeia longa colapsa num balde | `R05B-27` |
| 5 | alternativo configurado pela metade | URL sem chave era tratada como "não investigado" | `R05B-28` |
| 6 | `https://host` ≠ `https://host:443` | a checagem de endpoints distintos comparava texto cru | `R05B-29` |

O achado 3 é o único que atinge a **sonda**, não o veredito — e é o mais caro
dos seis: um falso `substituida` leva a **adotar** um cabeçalho que o cliente
controla. Os outros cinco levam a recusar ou a travar, que erra para o lado
seguro.

O achado 4 é a distinção B/C do §4 aparecendo dentro de um controle: sem
declarar origem, P4 respondia "o sufixo sobreviveu" e não "o sufixo sobreviveu
apontando para quem chamou".

#### Duas sabotagens que não isolaram o mecanismo

`AD` passou na primeira tentativa: o cenário que montei tornava emprestar ou não
emprestar o vínculo **indistinguíveis**. A propriedade que separa as duas
versões é outra — mesma medição, `p2_alt` trocado, veredito tem de ser igual —,
e o gate foi reescrito assim.

`Q` passou porque a correção do negativo estável criou um **segundo caminho** que
também reprova o alternativo contraditório. Os dois são redundantes de
propósito: desabilitar qualquer um sozinho não muda o resultado; desabilitados
juntos, `R05B-13` e `R05B-17` ficam vermelhos. O gate mede o resultado, não o
caminho.

### Quarta rodada: mais quatro, um deles na sonda

| | achado | por que importa | gate |
|---|---|---|---|
| 1 | sentinela **mapeado em IPv6** ficava invisível | `_e_sentinela` alimenta seis campos: um `::ffff:192.0.2.10` cegaria **todas** as guardas de contaminação de uma vez, e faria um cabeçalho controlado pelo cliente passar por `substituida` | `R05B-30` |
| 2 | origem declarada podia ser **privada** | dois candidatos privados satisfazem as duas execuções sem que haja duas origens públicas; e endereço privado se repete entre redes não relacionadas | `R05B-31` |
| 3 | P3 entrava na **concordância entre backends** | duas bordas classificando um cabeçalho de formas legítimas e diferentes reprovavam a certificação — contra o contrato que diz que P3 não é critério | `R05B-32` |
| 4 | backend inalcançável devolvia **1** | ausência de medição ficava indistinguível de produção que rejeitou a propriedade; o documentado para alvo inalcançável é **2** | `R05B-33` |

O achado 1 é o segundo a atingir a **sonda**, e tem o mesmo formato do anterior:
a classificação olhava a forma errada do valor. Aqui a correção é num ponto só,
e conserta os seis campos juntos.

#### `is_global` não basta

A primeira versão da checagem do achado 2 usava `alvo.is_global`. O gate pegou:
em CPython, **multicast é `is_global=True`** (`224.0.0.0/4`, `ff00::/8`).
Multicast não é origem de ninguém. A recusa agora é explícita para multicast,
reservado e não-especificado, antes do `is_global`.

As faixas de documentação (RFC 5737, RFC 3849) são **aceitas de propósito**: é
com elas que os gates exercitam o instrumento, já que `R05B-10` proíbe endereço
real nas superfícies da fatia. Nenhum eco de IP devolve uma delas, e uma medição
real declarada assim reprova em P1 de qualquer jeito.

### Quinta rodada: três achados, dois corrigidos e um que não é meu

| | achado | estado | gate |
|---|---|---|---|
| 1 | `render.yaml` declara `3` enquanto o contrato R0.5B exige `0` no ambiente | **não corrigido — decisão do autor** | — |
| 2 | o compromisso da primeira origem sobrevivia à certificação | corrigido | `R05B-35` |
| 3 | instâncias **repetidas** do cabeçalho: só a primeira era lida | corrigido | `R05B-34` |

O achado 3 é o terceiro a atingir a sonda, e fecha a terceira porta do mesmo
cômodo: primeiro a grafia (`R05B-8c`), depois a vírgula (`R05B-26`), agora as
instâncias repetidas. `HTTPMessage.get()` devolve só a primeira, então uma borda
que emitisse o próprio endereço numa instância e preservasse o sentinela noutra
seria classificada `substituida` com o sentinela vivo na requisição. Juntar as
instâncias com vírgula é o que a semântica de HTTP já manda.

A sabotagem `AO` não pegou na primeira tentativa: desabilitar só o `get_all`
deixava o caminho de `items()` coletando tudo do mesmo jeito. Os dois caminhos
são redundantes de propósito; a sabotagem que isola o mecanismo reintroduz o
comportamento antigo nos dois.

#### Sobre o achado 1

A tensão é real e está registrada: o repositório declara `3` em `render.yaml`
e, ao mesmo tempo, declara no contrato R0.5B que o valor no ambiente tem de ser
`0` enquanto a identidade não fechar. Se um deployment consumir o blueprint,
o `3` entra em vigor sem que ninguém decida isso.

A mitigação hoje é documental: a descrição do PR e o roteiro de medição mandam
conferir o painel depois de qualquer deploy deste branch. Isso depende de
disciplina humana, que é exatamente o que esta fatia existe para substituir por
gate.

**Não foi corrigido porque o número não é meu para mudar.** A declaração do `3`
foi autorizada na R0.5, e a autorização da R0.5B é explícita: não alterar o
número de saltos. Levado ao autor como decisão, com recomendação registrada.

---

## 8. O 403 da primeira medição real

A primeira execução com os heads implantados devolveu, nos **dois** backends:

```
NÃO ALCANÇADO — HTTP 403 em /api/origin-identity-diagnostics
$LASTEXITCODE = 2
```

### O que está provado

**A aplicação não sabe devolver 403 nesta rota.** Exercitada no caminho HTTP
real — `EpiHandler` num socket, requisição idêntica à do script — ela devolve:

| requisição | resposta |
|---|---|
| chave correta | **200** com o JSON da sonda |
| chave errada | **404** `{"error": "Rota não encontrada."}` |
| sem chave | **404**, idem |
| controle P4, cadeia longa | **200** |

Gate `R05B-37`, que sobe o servidor de verdade e reprova se algum desses virar
403.

O caminho antes do handler também não produz 403: o único portão pré-dispatch
para `/api/` é o de bootstrap, que responde **503**; `router.dispatch` não tem
hook algum; e os 403 de `do_GET` vêm só de `PasswordChangeRequiredError` e
`PermissionError`, que este handler não levanta — ele nem toca em sessão.

**Conclusão: quem recusou está à frente da aplicação.**

### O que NÃO estava provado, e por quê

Qual camada, e por qual regra. E aqui o instrumento tinha a resposta na mão e a
jogou fora: `_sondar` colapsava todo `HTTPError` não-404 em `HTTP {code}`,
descartando cabeçalhos e corpo — exatamente o que distingue uma recusa da borda
de uma recusa da aplicação.

Uma medição que produz um número sem conteúdo diagnóstico é uma medição
desperdiçada. Corrigido: a recusa agora reporta o status, a **camada**
(`borda` · `aplicacao` · `indeterminado`) e uma lista fechada de cabeçalhos de
resposta que identificam quem respondeu.

**O corpo nunca sai.** A página de bloqueio da Cloudflare **exibe o endereço do
visitante**, e o relatório existe para ser colado numa revisão. Do corpo sai
apenas se ele parece JSON ou HTML. Gate `R05B-36` prova as duas metades:
identifica a camada, e não ecoa nem o corpo nem o endereço que ele contém.

### O que ainda não dá para afirmar daqui

A política de egresso deste ambiente nega CONNECT para `*.onrender.com`, então
não consigo observar a resposta real. Cloudflare está comprovadamente à frente
(§3.1), o que a torna a candidata mais provável — mas **candidata não é causa
comprovada**, e nomear uma sem evidência seria o mesmo erro que esta fatia
inteira existe para não cometer.

A próxima execução traz essa evidência no próprio relatório, sem medição extra.

### O 503 da triagem: é nosso, e não é o 403

A triagem sem chave devolveu **503** nos dois backends, e os cabeçalhos dizem de
quem é:

| observado em produção | reproduzido localmente |
|---|---|
| `HTTP/1.1 503` | `503` |
| `content-type: application/json; charset=utf-8` | idêntico, é o que `send_json` emite |
| `x-render-origin-server: SimpleHTTP/0.6 Python/…` | `Server: SimpleHTTP/0.6 Python/…`, que é o `version_string()` do `EpiHandler` |
| `server: cloudflare` + `CF-RAY` | a borda repassou; o corpo veio da origem |

**É o portão de bootstrap.** `_require_bootstrap_ready` roda para toda rota
`/api/` **antes** do dispatch e responde 503 enquanto
`DB_BOOTSTRAP_STATE['ready']` for falso. A sonda não recusa nada aqui — ela nem
é alcançada.

A condição exata: o caminho normalizado começa com `/api/`, não está em
`BOOTSTRAP_READY_EXEMPT_PATHS`, não começa com `/api/i18n/` nem `/api/tenant/`,
e o bootstrap não completou.

#### A rota NÃO é isenta, e isso é decisão registrada

Isentá-la seria tecnicamente inócuo — a sonda não toca no banco. E ainda assim é
a decisão errada, por dois motivos:

1. **O 503 é informação verdadeira.** Ele diz que a superfície `/api/` inteira
   dos dois serviços está indisponível. Medir topologia de proxy num backend que
   não está servindo certificaria um caminho degradado — outro sabor da
   certificação falsa que esta fatia existe para impedir.
2. **Seria um bypass de portão fail-closed.** A sonda passaria a ser alcançável
   num estado em que nada mais da API é, com pré-condição mais fraca que a de
   todo o resto.

Gate `R05B-38` trava a interceptação e a não-isenção; a sabotagem `AT`, que põe
a rota na lista de isenção, o deixa vermelho.

#### 403 e 503 são fenômenos distintos

Mesma URL, mesmo método, resultados diferentes conforme o cliente:

| cliente | resultado | chegou à aplicação? |
|---|---|---|
| `curl`, sem chave | **503** com corpo da origem | **sim** |
| `urllib` (o script), com chave | **403** | **não** — o portão teria dado 503 |

Se o 403 viesse da aplicação, ele seria 503: o portão dispara antes do handler,
para qualquer cliente. O script recebeu algo que o `curl` não recebeu, então a
diferença está **na requisição**, não na rota — e alguma camada à frente a trata
de outro jeito.

As variáveis que diferem são três: o `User-Agent` (`Python-urllib/3.x`), e os
cabeçalhos `X-Probe-Hops` e `X-Origin-Claim`. Isolá-las é um A/B de uma variável
por vez, sem chave nenhuma.

**Ressalva honesta:** o 403 e o 503 foram observados em momentos diferentes. O
teste limpo roda as duas requisições **em sequência imediata**, para que o
estado do serviço não seja uma explicação alternativa.

### Sexta rodada: cinco achados, e um deles derrubou uma afirmação minha

| | achado | gate |
|---|---|---|
| 1 | o 404 da sonda **não** era indistinguível de rota inexistente | `R05B-39` |
| 2 | `HOSTNAMES-COBERTOS` comparado por substring | `R05B-40` |
| 3 | falha ao **gravar** o compromisso virava traceback com status 1 | `R05B-41` |
| 4 | falha ao **apagar** o compromisso saía 0, declarando fechado o que não fechou | `R05B-41` |
| 5 | contrato ABERTO sem o script deixava a suíte verde | `R05B-7` |

#### O achado 1 desmente o que este documento afirmava

Estava escrito aqui que a rota devolvia 404 "com o mesmo corpo de
`app.not_found()`, para não confirmar a existência da rota". **Era falso.**
Medido:

| requisição | status | content-type | bytes |
|---|---|---|---|
| sonda sem chave | 404 | `application/json; charset=utf-8` | 34 |
| rota inexistente sob `/api/` | 404 | `text/html;charset=utf-8` | 335 |

Quem sondasse distinguiria "sonda desligada" de "rota ausente" por inspeção
trivial. A correção usa `send_error(404, 'File not found')`, que é exatamente o
caminho do fallthrough, e o gate compara status, content-type e **corpo byte a
byte** contra uma rota que não existe.

A evidência já estava na reprodução do caminho HTTP que eu mesmo rodei para
investigar o 403 — e eu não a li.

#### O achado 5 é buraco criado por uma correção anterior

O import condicional do script (rodada 2) resolveu o estado fechado e abriu o
aberto: com o contrato `INDETERMINADO`, apagar o script fazia todo teste
dependente dele **pular**, e a suíte ficava verde enquanto o operador perdia a
capacidade de medir e de fechar. `R05B-7` agora exige presença no aberto e
ausência no fechado — simetria que faltava.

#### Códigos de saída: agora há um `4`

Falha de filesystem não é veredito sobre propriedade, e as duas direções
estavam erradas:

| situação | era | virou |
|---|---|---|
| não consegue **gravar** o compromisso | traceback, status 1 (igual a propriedade reprovada) | **2**, não executado |
| não consegue **apagar** o compromisso | **0**, certificação "fechada" com o compromisso vivo no disco | **4**, propriedades satisfeitas e encerramento falho |

### Sétima rodada: três achados, e o primeiro derruba uma escolha minha

| | achado | gate |
|---|---|---|
| 1 | faixa de documentação era aceita como **origem pública** em produção | `R05B-31` |
| 2 | URL malformada (`https://[`) virava traceback com status 1 | `R05B-42` |
| 3 | a varredura antivazamento de endereço era **IPv4-only** | `R05B-10b` |

#### O achado 1: eu tinha enfraquecido a validação de produção por conveniência de teste

`_origem_plausivel` aceitava RFC 5737 e RFC 3849 para que os gates pudessem
exercitar `main()` sem escrever endereço real nas superfícies da fatia — que é
o que `R05B-10` proíbe. A troca era ruim e era minha: um placeholder esquecido
em `EPI_IDENT_MEU_IP` produziria certificação a partir de endereço não
roteável, e a identidade de rate limit que a fatia existe para provar sairia de
um endereço que não é de ninguém.

Quem cede agora é o teste, não o código. Produção recusa documentação; os gates
que precisam dirigir `main()` substituem a função por
`_plausivel_com_documentacao`, e o gate que testa a **função** usa os endereços
de verdade — o global vem de um inteiro (`0x60606060`), porque literal pontuado
fora de faixa reservada é justamente o que `R05B-10` proíbe.

#### O achado 2: erro de operador com o código de saída de veredito

`urlsplit('https://[')` levanta `ValueError: Invalid IPv6 URL`. O erro escapava
de `main()`: traceback e **status 1** — o mesmo status de propriedade
reprovada. Um erro de digitação na variável de ambiente ficava indistinguível,
para quem lê só o código de saída, de "a cadeia não provou a identidade".

| situação | era | virou |
|---|---|---|
| `EPI_IDENT_CORP_URL` / `EPI_IDENT_SAAS_URL` malformada | traceback, status 1 | **2**, `PARE: URL inválida em: …` |
| `EPI_IDENT_ALT_URL` malformada | `hostname alternativo: não comprovado — não alcançou o serviço` | **2**, `PARE: URL inválida em: …` |

O alternativo entrou na mesma conferência por ser o mesmo defeito com outra
roupa: `não comprovado` é conclusão sobre o mundo — "esta entrada pública não
responde à sonda" — e o que houve foi erro de digitação. É a razão pela qual o
alternativo **pela metade** já era `2` (`R05B-28`): o operador pediu para
investigar aquele alvo.

#### O achado 3: o gate antivazamento só enxergava metade das famílias

`R05B-10` varria `\b(\d{1,3}(?:\.\d{1,3}){3})\b` — só IPv4. O instrumento
aceita reivindicação **IPv6** de ponta a ponta (`_origem_plausivel`,
`_e_sentinela`, a seleção da sonda), e a própria lista de faixas seguras já
citava `2001:db8::/32`. Um endereço IPv6 real caído no contrato, no script, na
sonda ou no arquivo de testes não era achado por ninguém, e o gate seguia verde
afirmando que a fatia não grava endereço de ninguém.

A varredura agora casa o token bruto e corta do fim até algo analisar — porque
literal de endereço não tem fronteira `\b` que sirva: `2001:db8::1` acaba em
dígito, `2001:db8::` acaba em dois-pontos, `127.0.0.1:8000` continua depois do
endereço e a pontuação da prosa cola no fim.

Duas decisões que não são óbvias:

1. **Toda grafia IPv6 que embute um IPv4 é julgada pelo IPv4 embutido.** Sem
   isso, `::ffff:<real>` e `::<real>` entrariam pelas faixas reservadas
   `::ffff:0:0/96` e `::/96` carregando dentro o endereço real de alguém. É a
   mesma canonicalização que `_e_sentinela` faz na sonda, e pelo mesmo motivo:
   a grafia muda, o endereço não.
2. **A mensagem de falha não ecoa o endereço**, só arquivo e linha. Um gate que
   existe para impedir que endereço real seja gravado não pode publicá-lo no
   log do CI ao falhar.

#### Sabotagens da rodada

| | sabotagem | gate | resultado |
|---|---|---|---|
| AZ | documentação volta a ser origem pública | `R05B-31` | vermelho |
| BA-1 | `urlsplit` volta a levantar de `main()` | `R05B-42` | vermelho |
| BA-2 | a conferência de URL inválida some | `R05B-42` | vermelho |
| BA-3 | as duas ao mesmo tempo | `R05B-42` | vermelho |
| BA-4 | o alternativo sai da conferência de URL | `R05B-42` | vermelho |
| BB-1 | a varredura volta a ser IPv4-only | `R05B-10b` | vermelho |
| BB-2 | IPv6 real plantado no contrato | `R05B-10` | vermelho |
| BB-3 | IPv6 real plantado **+** varredura IPv4-only | `R05B-10` | **verde** |
| BB-4 | IPv4 real plantado no contrato | `R05B-10` | vermelho |

BB-3 é a linha que importa: com a varredura anterior, o endereço plantado
passa. Não é falha do gate — é a demonstração do estado que o achado 3
descreve. BB-4 existe porque reescrever a varredura podia perder a cobertura
IPv4 em silêncio.

### Oitava rodada: três achados, e dois são a janela que a correção anterior deixou

| | achado | gate |
|---|---|---|
| 1 | grafia de **IPv6** fazia um endpoint passar por dois | `R05B-43` |
| 2 | o gate da contradição **nunca criava a contradição** que diz exercitar | `R05B-33` |
| 3 | três gates importavam `app` dependendo do ambiente de quem roda a suíte | `R05B-44` |

#### O achado 1: normalizar esquema e porta não bastava

A rodada 6 corrigiu `https://host` versus `https://host:443`. Ficou de fora o
literal: `https://[2001:db8::1]` e a forma expandida do mesmo endereço chegam ao
mesmo socket, e a comparação de texto os tratava como **dois backends
distintos** — deixando um deployment fornecer as duas medições obrigatórias, que
é precisamente o que a conferência existe para impedir.

E o erro tem duas direções, não uma. `partes.hostname` **remove os colchetes**:

| URL | normalizava para | problema |
|---|---|---|
| `https://[2001:db8::1]` | `https://2001:db8::1` | ≠ da forma expandida do mesmo endereço |
| `https://[::1]:8443` | `https://::1:8443` | **colide** com `https://[::1:8443]`, que é outro endereço |

Corrigir só a canonicalização e deixar os colchetes de fora trocaria um defeito
pelo outro. A sabotagem `BC-2` existe por isso.

`::ffff:<v4>` e `<v4>` entram na mesma canonicalização — é o mesmo destino, e é
a mesma regra que `_e_sentinela` já aplica na sonda.

#### O achado 2: o gate passava porque o dublê não sabotava nada

```python
resposta['cadeia_tamanho'] = resposta['cadeia_tamanho'] + (id(resposta) % 2)
```

Em CPython os objetos são alinhados: `id(x) % 2` é **sempre 0**. As três
repetições do SaaS saíam idênticas, `_forma` concordava, e a contradição que o
gate diz exercitar nunca acontecia. A asserção ainda aceitava `3` junto com `1`,
então uma regressão que tratasse medição contraditória como **pendente** — em vez
de reprovada — passaria batido.

Agora o dublê alterna por contador próprio, o gate exige **1** e exige ver
`INCONSISTENTE` no relatório. A sabotagem `BD-b` mostra o estado anterior:
com a mesma regressão em produção, a forma antiga do gate fica **verde**.

Montar essa sabotagem custou duas tentativas. A primeira trocava o ramo inteiro
de `_veredito` por pendente, o que atingia também o **inalcançável** — e o gate
ficava vermelho pela primeira metade, sem dizer nada sobre a contradição. Uma
sabotagem que não isola o mecanismo não prova o gate.

#### O achado 3: `app` importado com o ambiente de quem roda a suíte

`epi_backend/config.py` **levanta no import** quando `APP_ENV`/`ENVIRONMENT` é
produção e não há `JWT_SECRET`. Três gates desta fatia importam `app` para subir
o servidor real, e reprovariam por causa de uma variável de ambiente, não por
causa do que medem. Agora passam por `_importar_app()`, que define o ambiente
mínimo antes do import e restaura depois; `R05B-44` roda os três num processo à
parte, com `ENVIRONMENT=production` e sem `JWT_SECRET`.

**O que isso não afirma:** que a suíte inteira sobrevive a esse ambiente. Não
sobrevive — dez arquivos de teste importam `app` no topo do módulo e morrem na
**coleta**, antes de qualquer gate rodar:

```
ERROR collecting tests/test_login_bootstrap_gate.py
E   RuntimeError: JWT_SECRET é obrigatório quando APP_ENV/ENVIRONMENT=prod|production.
```

Isso é anterior a esta fatia, está em arquivos que este PR não toca, e a
correção pertence a `tests/conftest.py` — fora do escopo daqui.

#### Sabotagens da rodada

| | sabotagem | gate | resultado |
|---|---|---|---|
| BC-1 | grafia de IPv6 volta a não ser canonicalizada | `R05B-43` | vermelho |
| BC-2 | os colchetes somem da autoridade | `R05B-43` | vermelho |
| BD-a | contradição obrigatória vira PENDENTE | `R05B-33` | vermelho |
| BD-b | a mesma regressão, com o gate na forma **antiga** | `R05B-33` | **verde** |
| BE | o import de `app` volta a depender do ambiente | `R05B-44` | vermelho |

### Nona rodada: o instrumento vazava o segredo no relatório

| | achado | estado | gate |
|---|---|---|---|
| 1 | a rota de diagnóstico não deveria existir em produção (`AGENTS.md`) | **não corrigido — decisão do autor, já tomada** | — |
| 2 | o compromisso copiado sobrevive na primeira máquina | corrigido **na parte alcançável** | `R05B-46` |
| 3 | chave malformada vazava **inteira** no relatório | corrigido | `R05B-45` |

#### O achado 3 é o mais grave da fatia, e não era hipótese

`urllib` valida cabeçalho na hora de **enviar** e levanta
`ValueError: Invalid header value b'<valor>'` — com o valor inteiro dentro. A
chave viaja em cabeçalho, e o `except Exception` de `_sondar` interpolava a
exceção crua em `alvo.motivo`, que `_relatar` imprime no relatório que o roteiro
manda o operador colar. Reproduzido:

```
não alcançou o serviço: Invalid header value b'<a chave inteira>'
```

Uma chave com quebra de linha — copiada de um painel, colada com `\n` no fim —
publicava o segredo para quem lesse o relatório.

Duas correções, e cada uma é provada por sabotagem própria:

1. **Conferir antes de montar a requisição.** `_cabecalho_valido` recusa
   quebra de linha, nulo e o que não couber em latin-1, com mensagem que nomeia
   a variável e **não** mostra o valor.
2. **Redigir na saída.** `_redigir` remove chave, reivindicação e alternativa de
   qualquer mensagem que o catch-all produza. A conferência fecha o caminho
   conhecido; a redação fecha os que eu não previ.

A sabotagem `BF-3` desliga as duas e o gate acusa **o vazamento**, não a
redação da mensagem — é a linha que prova que o gate mede a propriedade certa.

O gate nasceu errado numa parte: eu usei `ção` como exemplo de "fora de
latin-1", e `ç` e `ã` **cabem** em latin-1. O próprio gate me corrigiu.

#### O achado 2 não tem correção completa possível daqui

O roteiro manda **levar** o compromisso para a segunda máquina, e um operador
normalmente **copia**. A execução de fechamento apagava a cópia local e
anunciava:

> Compromisso da primeira origem apagado: a certificação fechou.

Afirmação que o script não pode sustentar. Nenhuma execução alcança outra
máquina, e arquivo carregado à mão sempre pode ser copiado — então a cópia
esquecida na primeira máquina continua valendo como evidência de primeira
origem depois, quando o deployment ou a topologia já podem ter mudado.

**Limitação registrada, como a do digesto auto-referente no §1.** O que dá para
consertar daqui é a promessa, e foi o que se fez: a primeira origem manda
**mover, não copiar**, e diz o que acontece se copiar; o fechamento nomeia o
caminho que apagou e manda apagar a cópia de lá.

**A mitigação real é decisão do autor.** Dar prazo de validade ao compromisso
(a primeira origem grava o instante, a segunda recusa um compromisso velho
demais) limita a janela de reuso sem depender de disciplina — mas muda o
procedimento humano: as duas origens passariam a ter de ser medidas dentro do
prazo. Levado como decisão, não aplicado.

#### O achado 1 já tinha sido decidido

É o mesmo achado da segunda rodada — a rota de diagnóstico existir em produção
contraria as diretrizes de `AGENTS.md`. A decisão do autor foi manter a sonda,
temporária e fechada por gate (`R05B-7`), porque sem ela a identidade da origem
não é observável e `HOPS=3` não sai de PARCIALMENTE PROVADO. **Reabrir a
decisão não é minha.** A revisão automatizada não a conhece e a levanta de novo
a cada rodada; o registro fica aqui para que a resposta não precise ser
redescoberta.

#### Sabotagens da rodada

| | sabotagem | gate | resultado |
|---|---|---|---|
| BF-1 | a chave deixa de ser conferida antes do envio | `R05B-45` | vermelho |
| BF-2 | a redação vira no-op | `R05B-45` | vermelho |
| BF-3 | as duas — o **segredo volta ao relatório** | `R05B-45` | vermelho, acusando o vazamento |
| BG-1 | a primeira origem para de mandar mover | `R05B-46` | vermelho |
| BG-2 | o fechamento volta a prometer o que não alcança | `R05B-46` | vermelho |

### Décima rodada: quatro ataques à VALIDADE da medição

As nove rodadas anteriores acharam defeito no instrumento. Esta achou defeito
no **desenho da medição** — um instrumento que roda certo e mede a coisa errada
certifica com a mesma confiança.

| | achado | gate |
|---|---|---|
| 1 | P4 media um tamanho fixo e concluía sobre produção | `R05B-47` |
| 2 | P3 inferia confiança de sentinela **só de documentação** | `R05B-48` |
| 3 | o P3 da primeira origem sumia do veredito final | `R05B-49` |
| 4 | a evidência da primeira origem não tinha instante | `R05B-50` |

#### 1. Uma amostra não é uma fronteira

O controle de P4 mandava 30 elementos e concluía "o sufixo é preservado". Uma
borda que preserve em 30 e trunque em 120 passava — e `cadeia[-N]` continuava
podendo cair em dado do cliente numa requisição maior, que a aplicação aceita
igual. **Nada na aplicação limita o tamanho do `X-Forwarded-For`.**

Agora o controle **varre** `(1, 30, 120, 480)` e procura a fronteira:

| observação | conclusão | resultado |
|---|---|---|
| preserva em todos | P4 vale **até o maior tamanho testado**, e o relatório diz qual | segue |
| quebra em algum | P4 reprova e o relatório **nomeia o tamanho** | reprova |
| a borda **recusa** com status de tamanho (400/413/414/431/494) | fronteira segura: acima dela o cliente não consegue nem enviar | segue, e registra |

A distinção entre **recusa por status** e **falha de rede** é o ponto delicado:
um timeout num tamanho maior não é evidência de limite seguro, e continua
abortando a medição como "não executado". A sabotagem `BH-2` prova isso.

#### 2. O sentinela de documentação não separa dois comportamentos diferentes

P3 mandava `192.0.2.10` e concluía `substituida` quando o valor não voltava. Mas
uma borda que **higieniza por faixa** — descarta documentação, repassa o que
parece endereço público — produz exatamente essa observação **e mesmo assim
deixa o cliente escrever o cabeçalho**. A classificação dizia "a borda escreve
isto" onde a verdade é "a borda descarta ISTO".

Agora cada cabeçalho é sondado com **duas** classes de sentinela — documentação
(RFC 5737) e CGNAT (RFC 6598) — e a classificação que vale é a mais
conservadora: `substituida` exige **unanimidade**, porque é a única que licencia
adotar o cabeçalho.

**Limitação que fica:** uma borda que higienize tudo que não é global e ainda
assim repasse um valor de forma pública continua sendo classificada como
`substituida`. Fechar isso exigiria um sentinela de forma pública — ou seja, o
endereço real de alguém —, que é justamente o que `R05B-10` proíbe gravar nesta
fatia. **Decisão do autor:** acrescentar `inconclusiva` ao vocabulário do
contrato mudaria o bloco e o digesto, e não faço isso sem autorização.

Um detalhe que não é óbvio: a segunda classe entra **só em P3**. As guardas de
contaminação continuam com documentação apenas, porque endereço CGNAT aparece de
verdade em cadeia de operadora móvel — contá-lo como sentinela ali reprovaria P1
numa medição legítima feita de 4G, que é exatamente a segunda origem que o
roteiro sugere. A sabotagem `BI-2` trava essa separação.

#### 3. O que a primeira origem viu tem de sobreviver até o veredito

O tratamento de cabeçalho pode variar por rota: a origem A pode observar
`sentinela_sobrevive` e a B, `substituida`. O estado carregado guardava só P1 e
URLs, então o relatório final da segunda origem não tinha **traço** do resultado
inseguro de A — e o operador fecharia o contrato adotando um cabeçalho que o
cliente controla na outra rota.

O compromisso agora carrega a classificação de P3 da primeira origem, o
relatório final a mostra, e **sobreviver em qualquer uma das duas origens**
torna o cabeçalho não adotável.

#### 4. A idade da evidência estava invisível

O compromisso não tinha instante. Medir a origem B semanas depois — com outro
deployment ou outra topologia — era aceito desde que URL e `hops` batessem, e o
relatório não dizia nada sobre isso.

O compromisso agora grava o instante e o relatório final imprime a idade da
evidência, com o alerta de que medições de topologias diferentes não são
comparáveis. **O script não expira nada**: prazo de validade obriga as duas
origens a serem medidas dentro da janela, e elas são, por desenho, em redes
diferentes e possivelmente em dias diferentes. Isso muda o procedimento humano,
e é **decisão do autor** — levada a ele junto com a alternativa melhor: amarrar
as duas execuções à mesma revisão implantada, em vez de a um prazo.

O relógio para trás não vira "0 min": a idade negativa aparece como sintoma no
relatório, porque uma das máquinas está com a hora errada.

#### Consequência operacional

A sonda mudou (`_e_sentinela_p3`), então **os dois serviços precisam ser
reimplantados** antes da próxima medição. A medição também passou a fazer mais
requisições por backend — quatro controles de P3 e até quatro de P4, além de P1.

#### Sabotagens da rodada

| | sabotagem | gate | resultado |
|---|---|---|---|
| BH-1a | a constante volta à amostra fixa de 30 | `R05B-47` | vermelho |
| BH-1b | a varredura para no primeiro tamanho | `R05B-47` | vermelho |
| BH-2 | qualquer erro vira "fronteira segura" | `R05B-47` | vermelho |
| BI-1 | P3 volta a uma classe de sentinela só | `R05B-48` | vermelho |
| BI-2 | CGNAT entra nas guardas de contaminação | `R05B-48` | vermelho |
| BJ | o P3 da primeira origem some do veredito | `R05B-49` | vermelho |
| BK | a idade da evidência some do relatório | `R05B-50` | vermelho |

O harness desta rodada confere **qual** asserção falhou: sabotagem que deixa o
gate vermelho pelo motivo errado não prova nada. `BH-1a` e `BH-1b` existem
separadas por isso — a primeira derruba a guarda estrutural, a segunda derruba
a varredura de verdade.
