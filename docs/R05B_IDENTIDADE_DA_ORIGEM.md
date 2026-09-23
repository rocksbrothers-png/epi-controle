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

O bloco é idêntico nos dois repositórios, e um gate de digesto reprova quem
editar de um lado só.

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
| `epi-controle.onrender.com` | documentado como Produção em `spec/09-deployment.md:7`; o `render.yaml` declara `name: epi-controle` | **a investigar** — pode não existir, não responder, ou não ser o mesmo serviço |

**Domínios customizados:** o produto suporta CNAME de cliente
(`modules/tenant/domains_service.py`, resolução por `Host` em
`modules/tenant/service.py:50`). Capacidade do produto **não é prova de domínio
ativo**. Enquanto não houver evidência de um domínio configurado e acessível, o
registro é `nenhum domínio customizado ativo comprovado`.

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

**Não corrige a divergência de nome de serviço** entre `render.yaml`
(`name: epi-controle`) e o serviço medido (`epi-controle-app-gupy`). Achado
registrado, correção fora de escopo.
