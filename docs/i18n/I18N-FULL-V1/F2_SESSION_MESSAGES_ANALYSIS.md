# F2 — avisos de encerramento de sessão: análise para tradução (somente leitura)

Status: **análise, sem implementação.** Nenhum arquivo do contrato F2 foi alterado.
Base: Corporate `620adf58` / SaaS `62cd7f7` (`static/app.js` idêntico nos dois).

## 1. Textos atuais e locais de definição

| # | Texto (pt-BR, literal) | Onde é emitido | Gatilho | No contrato F2? |
|---|---|---|---|---|
| 1 | `Sua sessão foi encerrada. Faça login novamente para continuar.` | `loadBootstrap` (`static/app.js` ~5700) | 401/403 durante o uso | Sim |
| 2 | `Sessão expirada. Faça login novamente.` | restauração de sessão no `init` (~13013) | `isSessionRestoreAuthError` (401/403) | Sim |
| 3 | `Não foi possível restaurar sua sessão automaticamente. Faça login para continuar.` | restauração de sessão no `init` (~13038) | bootstrap inválido após as tentativas | Sim |
| 4 | `Não foi possível concluir o login. Faça login novamente.` | `handleLogin` (~10068) | falha após autenticar | Não listado em `MENSAGENS_DE_ENCERRAMENTO`, mas usa o mesmo mecanismo |

Mecanismo único (`terminateSession`, ~2566):
1. desliga a câmera, limpa a sessão e os rascunhos;
2. grava o texto em `sessionStorage['epi-session-end-message']` (`SESSION_END_MESSAGE_KEY`);
3. marca o teardown, rotaciona o escopo de snapshots, remove as preferências de sessão e a `view` da URL;
4. recarrega a página.

Na carga seguinte, `consumePendingSessionMessage` (~2697) lê a chave, **apaga antes de exibir** e chama
`setLoginMessage(texto, true)`, que escreve em `#login-message` por `textContent`.

## 2. Consumidores

- **Frontend:** só `consumePendingSessionMessage` → `setLoginMessage` (exibição). Nenhuma decisão de
  fluxo lê o texto. A detecção de sessão inválida é por **status** (`isSessionRestoreAuthError`:
  401/403; `isBootstrapRequestError`: 502/503 ou `nonFatal`).
- **Backend:** não lê nem recebe esses textos. Existe uma mensagem **homônima e independente** do
  backend: `epi_backend/security.py:75` (`PermissionError`) e `core/security.py:145`
  (`AuthenticationError`), ambas “Sessão expirada. Faça login novamente.”. Ela chega ao cliente como
  erro de API. Hoje já é traduzida na apresentação pela chave de UI `errors.sessionExpired`, que o
  motor casa. Isso não altera o fluxo, porque o cliente decide pelo status.
- **Flutter:** tem a própria string localizada (`app_localizations*.dart`). Não participa do mecanismo web.

## 3. Testes e contratos que dependem das mensagens

`tests/test_343_f2_teardown_logout.py`:
- `MENSAGENS_DE_ENCERRAMENTO` (textos 1–3) e
  `test_cada_encerramento_involuntario_avisa_pelo_mecanismo_one_shot`: exige a chamada literal
  `terminateSession('<texto>')` no `app.js`.
- `test_o_aviso_do_caminho_2_nao_afirma_causa_que_nao_pode_provar`: o texto 1 fica no ramo `[401, 403]`
  e não contém “expirada/expirou”.
- `test_as_duas_mensagens_de_sessao_continuam_existindo`: os textos 2 e 3 existem no `app.js`.
- `test_a_mensagem_atravessa_a_recarga`, `test_a_mensagem_e_de_uso_unico`,
  `test_a_mensagem_nao_reaparece_em_recarga_seguinte`: exatamente um escritor e um consumidor; o
  `removeItem` vem antes do `setLoginMessage`.
- `test_a_chave_one_shot_nao_guarda_nada_sensivel`: a chave guarda só texto de aviso, nunca token,
  usuário ou senha.
- Dígitos de paridade F4/F5B: qualquer mudança no `app.js` exige recalcular os dígitos nos dois produtos
  (procedimento já usado nesta branch).

## 4. Impactos possíveis

- **Autenticação/logout:** nenhum, desde que só a exibição mude. O encerramento, a limpeza e a recarga não
  dependem do texto.
- **Isolamento de sessão:** o aviso é exibido **depois** que o dono anterior foi removido (preferências
  de sessão apagadas, escopo rotacionado).
  - Se o texto fosse traduzido no momento do encerramento, o idioma de quem saiu atravessaria a recarga
    para a tela de login do próximo usuário.
  - Traduzir na exibição usa o idioma resolvido para a nova carga (padrão do tenant ou navegador), que é
    o comportamento correto.
- **Ordem de carga:** `consumePendingSessionMessage` roda no `init`. O catálogo do idioma pode ainda não
  estar carregado nesse ponto, então a tradução precisa de fallback pt-BR e de uma nova tradução
  quando o motor terminar de carregar (binding vivo / `epi:langchange`).
- **Compatibilidade durante o deploy:** uma aba que encerrou a sessão na versão antiga guarda o texto
  pt-BR. A versão nova precisa exibi-lo normalmente.

## 5. Estratégia para traduzir somente a exibição (sem tocar valores canônicos)

**Opção A — manter o contrato (recomendada):**
- `terminateSession('<texto pt-BR>')` permanece **idêntico**. As chamadas literais, o texto
  armazenado e os testes F2 não mudam.
- Em `consumePendingSessionMessage`, depois do `removeItem`, um mapa congelado e fechado
  `{texto canônico → chave}` (4 entradas) resolve a chave.
  - Exibe com `EpiI18n.textFor(refs.loginMessage, chave, textoCanônico)`, com binding vivo, para que a
    carga tardia do catálogo ou a troca de idioma retraduzam.
  - Texto fora do mapa é exibido como veio.
- Testes novos (aditivos):
  - mapeamento dos 4 textos nos 5 idiomas;
  - texto desconhecido exibido intacto;
  - valor de `sessionStorage` antigo (pt-BR) exibido traduzido;
  - ordem `removeItem` → exibição preservada;
  - exatamente 1 escritor e 1 consumidor;
  - nenhum dado sensível.
- Custo: 1 função tocada (`consumePendingSessionMessage`), 4 chaves × 5 idiomas e regeneração de
  `index.html` e dos dígitos.

**Opção B — códigos estáveis:**
- `terminateSession({ code: 'SESSION_REVOKED' })`, com `sessionStorage` guardando o código e a exibição
  feita pela chave.
- Exige reescrever `MENSAGENS_DE_ENCERRAMENTO` e três testes F2 (as asserções literais deixam de
  valer). Também muda o formato do valor em `sessionStorage`, o que pede leitura retrocompatível
  durante o deploy.

| Critério | A — contrato mantido | B — códigos estáveis |
|---|---|---|
| Testes F2 existentes | intactos | 3–4 reescritos |
| Formato em `sessionStorage` | inalterado | muda (compatibilidade necessária) |
| Risco em logout/autenticação | nenhum (só exibição) | baixo, mas toca o escritor |
| Robustez a mudança de texto | o mapa precisa acompanhar o texto (um teste trava) | independe do texto |
| Reversibilidade | trivial | média |
| Escopo | 1 função | escritor + leitor + contrato |

## 6. Recomendação

Opção A, como mudança aditiva e reversível, **somente após nova autorização**. Até lá, os quatro
avisos permanecem em pt-BR e o contrato F2 fica intacto.


## Quarto aviso — “Não foi possível concluir o login. Faça login novamente.” (não traduzido)

**Onde:** `static/app.js`, no `catch` do fluxo de login, quando `sessaoEstabelecidaNestaTentativa` é verdadeiro.
O `saveSession` já gravou usuário, permissões e token, e o bootstrap pós-login falhou. Antes desse ponto (TOTP, credencial) não há
terminação: há `clearSession()` e a mensagem fica no formulário, sem recarga.

**Contrato atual:**
- A mensagem é gravada por `terminateSession('<texto>')` (teardown completo, aviso de uso único em `sessionStorage`, recarga).
- `consumePendingSessionMessage` lê o aviso, apaga a chave e o exibe **como veio**: ele não está no mapa de exibição.
- **Não** está em `MENSAGENS_DE_ENCERRAMENTO` (`tests/test_343_f2_teardown_logout.py`), e nenhum teste fixa esse texto.

**Para traduzir sem mexer em autenticação, encerramento, isolamento ou no F2:**
1. Acrescentar a entrada ao mapa fechado `avisosCanonicos` em `consumePendingSessionMessage` (só exibição) e criar
   `login.messages.loginIncomplete` nos 5 catálogos, com o pt-BR idêntico ao texto gravado.
2. Testes:
   - o literal continua em `terminateSession('…')`;
   - em pt-BR o texto exibido é idêntico;
   - nos outros idiomas há tradução própria, sem placeholders;
   - a troca de idioma não grava storage nem dispara evento (cenário Chromium `f2_session_notice`).
3. Decisão a tomar: hoje `test_mapa_cobre_exatamente_os_avisos_do_contrato_f2` exige mapa == `MENSAGENS_DE_ENCERRAMENTO`. Há duas saídas:
   - (a) incluir o 4º aviso em `MENSAGENS_DE_ENCERRAMENTO`. Isso amplia o contrato F2 com mais um caso, que passaria a ser fixado também
     pelo teste de mecanismo único, e exige autorização por tocar o teste de contrato;
   - (b) manter o contrato F2 como está e declarar o 4º aviso numa lista própria do teste de i18n.
   A recomendação é (a), porque fixa um aviso que hoje não tem teste.
