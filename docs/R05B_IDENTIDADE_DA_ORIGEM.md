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
