# ADR-0004 — Quando uma feature multiplataforma está concluída

**Status:** aceito
**Data:** 2026-08-18
**Contexto gerador:** auditoria de paridade Flutter (Lotes 1–6) e o fechamento
formal registrado em `docs/PARIDADE_ESPELHO.md`.

---

## Contexto

Durante a paridade entre `epi-controle-app` e o espelho `epi-controle`, o mesmo
achado apareceu **quatro vezes seguidas**, em fluxos diferentes:

| lote | backend | i18n | cliente Flutter |
|---|---|---|---|
| 3 — conformidade de estoque | rota + serviço + testes ✅ | 9 chaves × 5 idiomas ✅ | ❌ ausente |
| 4 — conferência por QR | 2 rotas + serviço + idempotência ✅ | 19 chaves × 5 idiomas ✅ | ❌ ausente |
| 5 — Ficha por empresa | escopo por `company_id` ✅ | 32 chaves × 5 idiomas ✅ | ❌ ausente |
| 2b — rótulo da Ficha | coluna TEXT + render ✅ | chave presente ✅ | ❌ tipo errado |

Em todos, alguém tinha razão para acreditar que a feature estava pronta: havia
rota registrada, havia serviço, havia teste de backend verde, e havia tradução
nos cinco idiomas. Faltava só a parte que o usuário toca.

O modo de falha é silencioso por construção:

- **tradução órfã não acusa nada** — nenhum gate reclama de uma chave que
  ninguém usa;
- **rota sem consumidor não acusa nada** — o backend responde 200 para quem
  chamar, e ninguém chama;
- **teste de backend verde reforça a impressão de pronto** — ele está correto,
  apenas mede outra coisa.

Um caso ilustra o inverso e fecha o argumento: no espelho, a senha temporária
tinha tela, cliente Dart e teste de cliente passando — e **nenhum backend**. O
teste stubava a resposta do servidor, então provava que o app reage bem *quando
o campo chega*, sem poder detectar um backend que nunca o envia. O guard nunca
disparava; a "senha temporária" era permanente.

## Decisão

> **Backend implementado + rota registrada + i18n existente não significa
> feature Flutter concluída.**
>
> Uma feature multiplataforma só é considerada completa quando houver
> **evidência do consumidor Flutter correspondente**, ou uma **decisão
> explícita e documentada** de que aquela funcionalidade não pertence ao
> Flutter.

A decisão de exclusão é legítima e esperada — nem tudo pertence ao app. O que
não é aceitável é a **ausência de decisão**: uma capacidade que existe no
backend, aparece traduzida, e ninguém sabe dizer se deveria ou não estar no
Flutter.

## Definition of Done — feature multiplataforma

Uma feature só é dada por concluída com **todos** os itens abaixo, ou com a
decisão explícita de exclusão registrada:

- [ ] **Consumidor Flutter** — método no `epi_api` e uso real em cubit/tela.
      Cliente sem tela não conta; tela sem cliente também não.
- [ ] **Teste** — que falhe se o consumidor for removido. Um teste que stuba a
      resposta prova o comportamento do cliente, **não** a existência do
      contrato: quando a feature depende do que o servidor envia, é preciso
      cobrir a fronteira.
- [ ] **i18n** — chaves nos 5 idiomas **e referenciadas em código**. Chave
      traduzida sem uso é sinal de feature pela metade, não de pronto.
- [ ] **Evidência Web** — `Build Flutter Web` verde.
- [ ] **Evidência Android** — `Build Android APK`/`AAB` verde.
- [ ] **Evidência iOS** — `flutter build ios --no-codesign` verde.
- [ ] **Ou:** decisão de exclusão registrada — onde a funcionalidade vive
      (Web Legado, integração, back-office), por quê, e quem decidiu.

## Como verificar

Cruzamento reprodutível, usado na auditoria de fechamento:

1. Extrair `router.register('<MÉTODO>', '<caminho>')` de `modules/**/routes.py`.
2. Extrair literais `'/api/...'` de `flutter/packages/epi_api/lib` e
   `flutter/apps/epi_admin/lib`, normalizando `{id}` e `$id`.
3. A diferença é a lista de candidatas. Usar `static/app.js` como discriminador:
   rota usada pelo legado e ausente no Flutter é lacuna de cobertura; rota
   ausente nos dois é provavelmente integração ou back-office.
4. Complementar por i18n: chave presente no ARB e não referenciada em código.
   **Cluster** coerente de chaves órfãs (não vocabulário solto) indica feature
   pela metade.

O método foi validado contra casos conhecidos: rodado hoje, ele **não** aponta
`/api/stock/compliance` nem as rotas `handover-*`, corrigidas nos Lotes 3 e 4 —
e rodado antes daqueles lotes, as teria apontado.

## Relação com o gate de drift

O gate de `tool/check_parity_drift.py` mede **espelho × principal**: os dois
Flutters entre si. Ele **não** mede — e não deve medir — **Flutter × Web
Legado**. São eixos distintos:

| eixo | o que detecta | quem cobre |
|---|---|---|
| espelho × principal | replicação incompleta entre repositórios | gate de drift (236 arquivos) |
| Flutter × Web Legado | capacidade sem consumidor no app | este ADR + auditoria periódica |

Confundir os dois leva à conclusão errada de que "o gate está verde, logo não
há lacuna".

## Consequências

- Toda feature nova que toque backend passa a exigir a resposta explícita:
  *tem consumidor Flutter, ou tem decisão de exclusão?*
- A auditoria cruzada de rotas e i18n deve ser repetida ao fim de cada frente
  relevante, não só quando alguém desconfia.
- Um `parametrize` vazio, uma allowlist que não casa e um gate que varre nada
  são a mesma família de defeito desta ADR: **artefato que afirma verificar e
  não verifica**. Ao escrever guarda, verificar que ela reprova o estado
  anterior — sabotagem deliberada — é parte do trabalho, não zelo extra.

## Referências

- `docs/PARIDADE_ESPELHO.md` — auditoria, lotes e fechamento
- `docs/ARQUITETURA_FRONTEND_BACKEND.md` — Fases 4/6/7 da migração legado→Flutter
- `flutter/tool/check_parity_drift.py` e `tests/test_parity_drift_gate.py`
