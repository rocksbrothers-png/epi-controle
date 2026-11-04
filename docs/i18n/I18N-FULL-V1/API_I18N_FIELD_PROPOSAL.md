# Proposta técnica — campo opcional `i18n` nos erros da API (NÃO implementada)

Status: **proposta para decisão.** Nenhum payload, rota, status ou cliente foi alterado.

## Contexto

Hoje o cliente web traduz os erros **na apresentação**: `createApiError` → `EpiI18n.describeApiError`
casa o texto pt-BR recebido com `apiErrors.messages.*`, sem tocar o contrato.

Sobra um caso: variáveis cujo valor é **texto pt-BR dinâmico** montado no backend. Exemplos: o status em
“Esta requisição já tem a PO {number} vinculada ({status})”, `{actionlabel}` / `{get}` em EPI em teste e
`{label}` vindo de chamada não literal. A frase é traduzida, mas o valor da variável continua em pt-BR.

Os valores **fixos** já foram resolvidos sem API (expansão por domínio literal, §14 de
`CLAUDE_CONTINUATION.md`).

## 1. Payloads atual e proposto

Atual (inalterado):
```json
HTTP 400
{"error": "Esta requisição já tem a PO 4412 vinculada (Aguardando aprovação). Só é possível emitir outra PO depois que ela for reprovada ou cancelada."}
```
Proposto (aditivo; os campos existentes ficam byte a byte iguais):
```json
HTTP 400
{"error": "Esta requisição já tem a PO 4412 vinculada (Aguardando aprovação). Só é possível emitir outra PO depois que ela for reprovada ou cancelada.",
 "i18n": {"key": "apiErrors.messages.m_xxxxxxxxxxxx",
          "params": {"number": "4412"},
          "refs": {"status": "purchase.poStatus.waiting_admin_review"}}}
```
- `key`: chave do catálogo que já existe.
- `params`: valores neutros de idioma (números, códigos, nomes próprios).
- `refs`: **códigos canônicos** que o cliente resolve para rótulos do próprio catálogo. O backend envia
  o código, nunca o texto traduzido.

Formato estruturado (`{"ok": false, "error": {"code": "...", "message": "..."}}`): `i18n` entra **dentro**
de `error`. O motor já procura nos dois lugares (`payload.i18n || error.i18n || payload.validation.i18n`).

## 2. Compatibilidade com clientes antigos

- Quem lê só `error`/`message` não vê diferença: o campo é ignorado.
- O status HTTP e `code` não mudam.
- O texto pt-BR continua sendo a fonte de verdade para logs, testes e clientes sem catálogo.

## 3. Efeitos nos clientes

- **Web:** nenhum código novo para mensagens simples. `describeApiError` já aceita `i18n.key/params` e só
  usa chaves `apiErrors.*`; chave desconhecida cai no texto original. Para `refs`, `resolveMessageVars`
  já resolve referências; resta só mapear `i18n.refs` → `refs`, uma linha no motor.
- **Flutter** (`ApiClient._extractErrorMessage` → `ApiException(message)`): hoje usa `error`/`message`
  e continua igual. Usar o campo exigiria mapear `key` → ARB (os catálogos ARB são separados dos web).
  Isso é opcional e pode vir depois sem quebrar nada.

## 4. Testes de contrato

- Os testes que comparam `error` continuam válidos, porque o texto não muda.
- Testes de contrato de API (`API Contract & Multi-Tenant Scope`) que fixam o conjunto de chaves do JSON
  precisariam aceitar `i18n` como opcional.
- Novos testes:
  - `i18n.key` existe nos 5 catálogos;
  - `params`/`refs` cobrem os placeholders;
  - `refs` aponta só para códigos canônicos (enum fechado);
  - o texto `error` é idêntico com e sem o campo.

## 5. Parâmetros dinâmicos

- **Números, IDs e datas:** vão em `params` crus (ISO para datas), e o cliente formata no idioma ativo.
- **Nomes do usuário** (EPI, empresa, colaborador): vão em `params` como texto opaco, nunca traduzidos.
  Continuam passando por `textContent`/`escape` nos destinos.
- **Rótulos de status, ação ou campo:** vão em `refs` como **código** (`waiting_admin_review`, `minimum_stock`),
  nunca como texto pt-BR.

## 6. Fallback para português

Na ordem:
1. `i18n.key` válida no idioma ativo;
2. a mesma chave no pt-BR do catálogo;
3. o casamento atual por texto (`describeApiError`);
4. o texto `error` original.

Nenhum caminho deixa a mensagem vazia.

## 7. Exposição de informações sensíveis

- `params` não pode trazer nada que `error` já não traga. Regra de teste: todo valor de `params` aparece
  literalmente em `error`.
- `refs` aceita só códigos de uma lista fechada, validados contra o catálogo.
- Nunca entram em `params`: tokens, hashes, CPF completo, e-mails de terceiros ou detalhes de stack ou SQL.

## 8. Versionamento

- A mudança é aditiva, sem nova versão de rota: o campo é opcional e ignorável.
- A adoção seria por endpoint, começando pelas mensagens com variável dinâmica (hoje cerca de 15 nos
  módulos já tratados).
- Nenhum cliente precisa ser atualizado em sincronia.

## 9. Alternativas sem mudar a API (preferidas)

1. **Expansão por domínio literal** (já implementada): resolve valores fixos.
2. **Templates por valor para enums pequenos:** quando o valor dinâmico vem de um enum com rótulo pt-BR
   conhecido (por exemplo `po_status_label`), o inventário pode gerar um template por rótulo, como em (1).
   Também sem mudar a API.
3. **Tradução por rótulo conhecido no cliente:** depois do casamento, o motor tentaria traduzir a variável
   quando ela coincide **exatamente** com um rótulo pt-BR do catálogo, numa lista fechada por placeholder.
   Muda só o motor, mas é heurística e precisa de lista explícita para não traduzir nomes de usuário.

**Recomendação:**
- adotar (2) agora, sem mudança de contrato;
- deixar (3) e o campo `i18n` como evolução, se ainda restarem casos;
- o campo `i18n` só com sua autorização específica.
