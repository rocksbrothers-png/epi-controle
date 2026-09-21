# Hardening do Recovery — não enumeração na recuperação de senha

Continuação da frente de login, no endpoint que ficou registrado como achado
separado ali. O fluxo de login **não foi tocado**.

## 1. São dois endpoints, com contratos diferentes

| | rota | o que faz | rate limit |
|---|---|---|---|
| **A** | `POST /api/auth/request-email-recovery` | recebe só o usuário e dispara o e-mail com o token | **nenhum** |
| **B** | `POST /api/recover-password` | recebe usuário + senha nova + chave e troca a senha | 5 / 300 s por IP |

A frase *"se os dados estiverem cadastrados você receberá as instruções"*
descreve **A**. Em **B** ela não faria sentido: quem chama B está enviando uma
senha nova, não pedindo instruções. Por isso o contrato tem **duas** mensagens,
uma por endpoint, e não uma só.

## 2. Caracterização — endpoint A (ANTES)

| Cenário | HTTP | payload | e-mail | tempo |
|---|---|---|---|---|
| A1 existe + e-mail | 200 | genérico | **enviado** | **268 ms** |
| A2 não existe | 200 | genérico | não | **0,09 ms** |
| A3 existe sem e-mail | 200 | genérico | não | 0,07 ms |
| A4 existe + **SMTP falha** | **400** | `'Falha ao enviar e-mail: <detalhe interno>'` | não | 268 ms |
| A5 campo ausente | 400 | `'Campo obrigatório: username'` | não | 0,02 ms |

**A mensagem já era genérica — e o endpoint respondia a pergunta assim mesmo**,
por dois canais:

1. **A4.** A falha de SMTP só é alcançável para conta que existe **e** tem
   e-mail. Entregá-la ao solicitante confirma a existência, e ainda expõe
   detalhe interno de infraestrutura.
2. **Tempo: 5207×.** `generate_user_recovery_token` chama `hash_password`
   (`bcrypt`), e só o caminho de quem existe pagava. Medido com SMTP falso e
   instantâneo — ou seja, a diferença não era do e-mail, era do hash.

Este endpoint é o exemplo mais limpo de "não basta uniformizar a mensagem".

## 3. Caracterização — endpoint B (ANTES)

| Cenário | HTTP | payload | tempo |
|---|---|---|---|
| B1 não existe | 400 | `'Usuário não encontrado.'` | 0,04 ms |
| B2 existe, sem token, chave global errada | **403** | `'Chave de recuperação inválida.'` | 0,03 ms |
| B3 existe, com token, chave errada | **400** | `'Chave de recuperação inválida.'` | **268 ms** |
| B4 existe, token expirado | 400 | `'Chave de recuperação expirada…'` | 0,12 ms |
| B5 sucesso | 200 | `{ok: true}` | 268 ms |

Três canais: a mensagem de B1 nomeia a causa; **B2 e B3 têm a mesma mensagem e
status diferente** — o status sozinho revela se a conta tem token próprio; e o
tempo separa B3 dos demais.

## 4. O contrato novo

**A** responde sempre `200` com
`MSG_RECUPERACAO_SOLICITADA`, saindo sempre pelo mesmo caminho: exista o usuário
ou não, tenha e-mail ou não, funcione o SMTP ou não.

**B** responde `400 RECOVERY_FAILED` com `MSG_RECUPERACAO_RECUSADA` para todo o
espaço de falha de formato válido, gastando trabalho equivalente.

Validação estrutural (campo obrigatório ausente) fica de fora dos dois: nada
chegou a ser consultado.

## 5. O desenho de A, e por que não foi "pagar bcrypt dos dois lados"

A saída óbvia para o tempo seria fazer o caminho de quem não existe pagar um
`bcrypt` fictício — foi o que a frente de login fez. Aqui seria **pior**:
encareceria *toda* requisição num endpoint **sem limitador**, transformando a
correção de enumeração num amplificador de carga.

O trabalho saiu da linha da resposta:

```
  SELECT usuário            ← única coisa que o solicitante paga
  responde 200 genérico     ← imediato, sempre
  thread daemon             ← sobe SEMPRE, decide lá dentro
     └─ se existe e tem e-mail: gera token (bcrypt) + envia + loga
        senão:                  loga o motivo e encerra
```

A thread sobe nos dois casos de propósito: criar uma thread custa ~0,6 ms, e
fazê-lo só para quem existe reabria a diferença em escala menor — **11,8×**,
medido depois da primeira versão desta correção.

Segue o precedente de thread daemon do `init_db` (`app.py`).

## 6. O desenho de B

`_recusa_de_recuperacao()` é a saída única das quatro falhas. As mensagens de
`validate_and_clear_recovery_token` viraram **sinais internos**
(`recovery_user_not_found`, `recovery_token_expired`, …): não são mais texto de
usuário, alimentam o log, e o chamador converte tudo na recusa única.

O ramo sem token por usuário passou a pagar `verify_password(_hash_ficticio(), …)`
— o mesmo `bcrypt` que o ramo com token já pagava.

## 7. Efeito preservado: o e-mail continua indo só para quem tem conta

Uniformizar a resposta não pode virar "manda e-mail para todo mundo". O gate
`test_a_email_so_sai_para_conta_existente_com_endereco` prova as duas metades:
sai para quem tem conta com endereço, não sai para conta inexistente nem para
conta sem endereço.

## 8. Sabotagens — sete, sete acusadas

| Sabotagem | Acusada por |
|---|---|
| α — volta a emitir `USER_NOT_FOUND` | `b_nenhum_campo_publico_distingue` |
| β — volta a dar mensagem específica | `b_a_mensagem_nao_nomeia_a_causa`, `b_nenhum_campo…` |
| γ — payload ganha campo diferenciável | `b_nenhum_campo_publico_distingue` |
| δ — envio volta à linha da resposta e a falha sobe | `a_falha_de_smtp…`, `a_nenhum_caminho_paga_bcrypt…`, estrutural, `tempo_medido` |
| ε — geração do token volta à linha da resposta | `a_nenhum_caminho_paga_bcrypt…`, `tempo_medido` |
| ζ — thread só sobe para quem existe | `tempo_medido` |
| η — falhas de B deixam de pagar trabalho igual | `b_todas_as_falhas_pagam_o_mesmo_trabalho` |

A **δ** passou verde na primeira versão, e a sabotagem é que estava errada: ela
só levantava exceção *dentro da thread*, de onde nada alcança o solicitante.
Reescrita como a regressão real — o envio volta para a linha da resposta **e** a
falha sobe —, passou a ser acusada por quatro gates.

## 9. Rate limiting — situação (auditoria, **não alterado**)

| | limitador | parâmetros |
|---|---|---|
| **A** `request-email-recovery` | **NENHUM** | — |
| **B** `recover-password` | `recovery_limiter` | 5 chamadas / 300 s, por IP |

**Achado registrado, não corrigido aqui:** o endpoint A é não autenticado, não
tem limitador e **dispara e-mail**. Hoje ele é também o mais barato de chamar,
porque o trabalho saiu da linha da resposta — o que é bom para o solicitante
legítimo e não muda o fato de que um laço consegue provocar envio repetido para
uma caixa de entrada alheia. A proteção pertence a uma fatia própria, com
decisão sobre escopo (por IP, por conta, ou os dois) e sobre o que fazer com
pedidos repetidos para o mesmo usuário.

O limitador de B tem os mesmos limites estruturais já registrados na frente de
login: memória por processo, e por IP apenas.

## 10. Fora do escopo

- **O fluxo de login não foi tocado.** `authenticate_login` e `_recusa_de_credencial`
  estão como a frente anterior os deixou; o gate estrutural desta fatia é
  escopado aos três donos da recuperação.
- **`app.py::authenticate_login` continua sendo código morto**, por decisão
  explícita: fechar a superfície de segurança antes da higiene interna.
