# Hardening do Login — não enumeração de credenciais

## 1. O fluxo atual, ponta a ponta

```
  formulário  static/index.html  (#login-form)
     │
     ├─ validação local   app.js handleLogin  →  "Informe Usuário e senha para entrar."
     │                    (nada sai do navegador; NÃO é falha de autenticação)
     ↓
  POST /api/login  ·  POST /api/auth/login        ← as duas rotas, o mesmo handler
     ↓
  modules/auth/routes.py  handle_post_login       ← rate limit por IP, antes de tudo
     ↓
  modules/auth/service.py  authenticate_login     ← OWNER da decisão
     ↓
  resposta {error, code} + status
     ↓
  js/modules/api-client.js  throwIfApiRequestFailed → createApiError(code)
     ↓
  js/modules/auth.js  getLoginErrorMessage(code)   ← OWNER da mensagem no cliente
     ↓
  app.js  setLoginMessage(texto, true)
```

**Owner backend:** `modules/auth/service.py :: authenticate_login`.
**Owner frontend:** `static/js/modules/auth.js :: getLoginErrorMessage`.

O app Flutter é um terceiro cliente: já mostrava `'Usuário ou senha incorretos'`
(`login_screen.dart` → `_ => l10n.loginError`), mas **recebia o payload que
distingue** — o caso exato de "não basta o frontend substituir visualmente".

## 2. e 3. Comportamento medido ANTES (S1–S4)

| Cenário | HTTP | `code` | `error` | tempo |
|---|---|---|---|---|
| **S1** usuário existe + senha errada | 401 | `INVALID_PASSWORD` | `Senha incorreta.` | **269 ms** |
| **S2** usuário inexistente | 401 | `USER_NOT_FOUND` | `Usuário não encontrado.` | **0,06 ms** |
| **S3** credenciais válidas | 200 | — | — | 284 ms |
| **S4** campos vazios | — | `ValueError` local | `Usuário e senha são obrigatórios.` | 0 ms |

Mais dois oráculos, ambos alcançáveis **sem** a senha:

| Cenário | HTTP | `code` |
|---|---|---|
| conta inativa | 403 | `USER_INACTIVE` |
| perfil funcionário | 403 | `EMPLOYEE_EXTERNAL_ONLY` |

## 4. Diferenças observáveis

**Por conteúdo:** `code` e `error` diziam qual credencial falhou. Com a lista de
códigos, enumerar a base é uma requisição por palpite.

**Por tempo:** o caminho de usuário inexistente retornava **antes** do `bcrypt`;
o de senha incorreta pagava o hash inteiro. **269 ms contra 0,06 ms — 4260×.**
Trocar só a mensagem deixaria a enumeração funcionando por cronômetro.

## 5. Contrato novo

Para o cliente não autenticado, **toda** falha de credencial responde:

```
401  { "code": "INVALID_CREDENTIALS", "error": "Usuário ou senha incorretos." }
```

e gasta o **mesmo trabalho**, para que os caminhos não se separem por tempo.

Colapsam: usuário inexistente · senha incorreta · conta inativa · perfil
funcionário.

**Continuam distintos, e por quê:** `TOTP_REQUIRED`, `TOTP_INVALID` e
`TEMP_PASSWORD_EXPIRED` só são alcançáveis **depois** da senha correta — quem
chega neles já provou conhecer a credencial, então não há o que enumerar, e
uniformizá-los quebraria o 2FA e a política de senha temporária. O mesmo vale
para 429 e 5xx, que precisam continuar distinguíveis de credencial inválida.

**Validação local (S4) fica como está:** campo obrigatório não é tentativa de
autenticação — nada chega a sair do navegador.

## 6. Alterações de produção

`modules/auth/service.py`
- `MSG_USER_NOT_FOUND` **removida** (não renomeada: a frase deixaria de existir
  em vez de ficar disponível para o próximo chamador).
- `MSG_CREDENCIAIS_INVALIDAS` + `CODIGO_CREDENCIAIS_INVALIDAS` + `_recusa_de_credencial()`,
  ponto único de saída das quatro recusas.
- `_hash_ficticio()`: hash real, de senha aleatória, verificado quando o usuário
  não existe. **Não é `sleep()`** — é fazer o mesmo trabalho. Preguiçoso, para
  não somar um `bcrypt` a todo arranque de processo.
- A verificação de senha passou a rodar **sempre**, e `active`/perfil passaram a
  ser avaliados **depois** dela. O bloqueio continua valendo; deixou de ser
  observável por quem não tem a credencial.

`static/js/modules/auth.js`
- `CODIGOS_DE_CREDENCIAL` → uma mensagem só. Os códigos antigos continuam
  mapeados como **rede de segurança**: sem isso, um cliente novo contra um
  servidor antigo reabriria a enumeração sozinho.

## 7. Logs

Inalterados em riqueza: `reason='user_not_found' | 'invalid_password' |
'user_inactive' | 'employee_external_only'` continuam no log, com `username` e
`user_id`. Diagnóstico interno não foi sacrificado para uniformizar a resposta
pública. Nenhum log contém senha, hash ou credencial completa — auditado.

## 8. Gates

11 no backend (`tests/test_login_sem_enumeracao.py`) e 3 no cliente
(`LOGIN L-1..L-3`). O central é `test_s1_vs_s2_nenhum_campo_publico_distingue`:
compara o **payload inteiro**, não só a mensagem.

Convertidos, nenhum apagado: `auth: getLoginErrorMessage USER_NOT_FOUND`,
`auth: getLoginErrorMessage INVALID_CREDENTIALS` e
`test_auth_service_has_msg_constants`.

## 9. Sabotagens

| Sabotagem | Acusada por |
|---|---|
| α — backend volta a dizer "Senha incorreta" | `s1`, `s1_vs_s2`, estrutural, inativa, funcionário |
| β — backend volta a dizer "Usuário não encontrado" | `s2`, `s1_vs_s2`, estrutural |
| γ — **UI genérica, códigos públicos distintos** | `s1`, `s2`, `s1_vs_s2`, inativa, funcionário |
| δ — usuário inexistente volta a pular o `bcrypt` | `usuario_inexistente_tambem_paga`, `tempo_medido` |
| ε — uniformiza tudo, inclusive o 2FA | `totp_e_senha_temporaria_continuam_distintos` |

A **γ** é a que o contrato exige: interface genérica com payload distinto
continua sendo enumeração, porque o atacante lê a resposta HTTP, não a tela.
A **ε** é o controle contra o excesso — uniformizar demais quebra o 2FA.

## 10. Depois

| | antes | depois |
|---|---|---|
| S1 senha incorreta | 401 `INVALID_PASSWORD` · 269 ms | 401 `INVALID_CREDENTIALS` · 286 ms |
| S2 usuário inexistente | 401 `USER_NOT_FOUND` · 0,06 ms | 401 `INVALID_CREDENTIALS` · 289 ms |
| razão de tempo | **4260×** | **1×** |

## 11. Rate limiting — situação (auditoria, não alterado)

**Existe.** `core/rate_limit.py :: login_limiter = RateLimiter(max_calls=10,
period_seconds=60)`, sliding window em memória, thread-safe. Aplicado em
`handle_post_login` antes de qualquer consulta, respondendo **429
`AUTH_RATE_LIMITED`**. Escopo: **por IP** (`get_client_ip`, respeitando
`X-Forwarded-For`).

Limites conhecidos, registrados como achado — **não ampliado aqui**:
- em memória e por processo: com mais de uma instância, o teto efetivo é
  10 × número de instâncias;
- por IP apenas: não há limite por conta, então uma botnet distribui o ataque;
- não reinicia contagem em login bem-sucedido.

## 12. Achados separados, fora do escopo desta fatia

- **Enumeração na recuperação de senha.** `validate_and_clear_recovery_token`
  responde `'Usuário não encontrado.'` a cliente não autenticado em
  `/api/recover-password`. Mesmo defeito, outro endpoint; a correção usual
  ("enviamos um e-mail se a conta existir") muda o fluxo visível e é decisão de
  produto. O gate estrutural foi **escopado ao login** de propósito, para não
  arrastar essa mudança para cá sem decisão.
- **`app.py :: authenticate_login` é código morto.** Chama o serviço com
  parâmetros que a assinatura atual não aceita (`msg_user_not_found=` e outros
  oito) — levantaria `TypeError` se fosse alcançado. Nenhuma rota o referencia;
  `/api/login` vai por `modules/auth/routes.py`. Não removido: fora do escopo.
