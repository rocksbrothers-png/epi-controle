# I18N-FULL-V1 — continuação (transferência Codex → Claude)

Data: 03/11/2026. Este documento registra o diagnóstico, a matriz de requisitos e
o que esta continuação alterou. Não é certificação de cobertura integral.

## 1. Ponto de partida (Fase A)

| | Corporate | SaaS |
|---|---|---|
| Inventariadas (únicas por módulo) | 1.121 | 1.128 |
| Falhas técnicas de infraestrutura (500/503, pt-BR de propósito) | 29 | 29 |
| **Denominador (mensagens de negócio)** | **1.092** | **1.099** |
| Traduzidas / cobertas | 1.089 | 1.096 |
| Preservadas por contrato | 3 | 3 |
| Cobertura real | **99,7%** (100% das traduzíveis) | **99,7%** (100% das traduzíveis) |

Preservadas: `QR não encontrado com correspondência exata no estoque da unidade.` (lookup-qr) e os 2
avisos de bloqueio do portal. Catálogos, `app.js`, `i18n.js`, inventário e gate idênticos nos dois
repositórios.

## 18. Auditoria independente dos lotes D–F e da camada compartilhada

Agente separado, só leitura, sobre `2d295d4c` / `095b6c2`. **Nenhum P0.** Testes do auditor: 216/219
pytest e 666 JS, sem nenhum teste pulado.

| ID | Sev. | Achado | Tratamento |
|---|---|---|---|
| A1 | P1 | Rótulos pt-BR dentro de templates genéricos: `Data da entrega inválida` virava “Invalid Data da entrega…”; `stock/disposition` (“Invalid Motivo da destinação.”) | O inventário não ligava `{fieldlabel}` ao parâmetro `field_label` nem lia `for … in [tuplas literais]`. Agora faz as duas coisas: 30 templates expandidos (datas do histórico, 8 da destinação, 15 ações de EPI em teste, 3 entidades arquivadas). `{key}`/`{field}` não são expandidos, porque o motor já os traduz via `apiErrors.fields.*`. Há amostra Chromium nova |
| A2 | P2 | “Infraestrutura não chega ao cliente” é falso: `app.py` devolve `str(exc)` em 500, e o 503 do bootstrap leva `details.detail` | Motivo reescrito (falha técnica 500/503, pt-BR de propósito). O gate exige que venham só de `INFRA_FILES` e só como `RuntimeError`/`SchemaMigrationError`. **Risco de segurança registrado, sem alteração (backend/contrato):** `details.detail` do 503 expõe o erro bruto de banco/migração |
| A3 | P2 | O scanner não via `/regex/.test(message)`: `error-monitor.js` marca `critical_error` | `TELEMETRY_TEXT_LOGIC` declarado e gate novo: regex sobre mensagem precisa estar declarado, e tradução que passe a casar a telemetria precisa estar na lista `allow` justificada. 3 chaves en-GB com “critical” (rótulo oficial da gravidade) foram aceitas: o efeito fica só na etiqueta de telemetria de erro não tratado, e o limite de rollback conta antes |
| A4 | P2 | O gate de gatilho só olhava um sentido | Sentido inverso acrescentado: mensagem traduzida cujo pt-BR contém o termo comparado reprova |
| A5 | P2 | O ramo 503 da reimpressão depende do fallback do gateway (texto do frontend) ficar sem template | Teste que fixa: nenhum template casa `Servidor temporariamente indisponível…` |
| A6 | P2 | `my-company-view.js:156` usa `innerHTML` com `error.message` (anterior, módulo UBX) | Não alterado (escopo UBX); continua registrado |
| A7 | P3 | es-ES “EPI” em 3 chaves; nb “Obligatorisk felt”; fr “non valide” | Corrigidos para EPP / “Påkrevd felt” / “invalide” |

## 19. Auditoria final (PRs #1080 / #454) e decisões pendentes

Feita por um agente separado, só leitura, em worktrees próprios. **Nenhum P0/P1.**

| Sev. | Achado | Tratamento |
|---|---|---|
| P2 | O PR **altera o backend** em relação à `main`. As mudanças vêm da base da Codex, não desta continuação: `modules/i18n/presentation.py`, alerts (`presentation`), compras e portal do fornecedor (e-mails/PDF/anexo no idioma de `Accept-Language`/`?lang`, link do portal com `?lang=`, scripts com SRI), `safety_library` (`name_i18n_key`), `core/pdf.py` (`/WinAnsiEncoding` e fim do duplo escape) e `requirements.txt` (+Babel). São campos aditivos, sem mudança de status, códigos ou textos de erro, e sem mudança de tenant ou autorização. A descrição dos PRs dizia “sem backend” | Descrição dos PRs corrigida |
| P3 | `Translator.t` falha fechado com `DocumentLocaleUnavailable` quando falta chave | É intencional e testado (`test_partial_document_catalogue_does_not_send_portuguese_or_raw_key`): não envia documento com idioma misturado ou chave crua. Mantido |
| P3 | O e-mail ao fornecedor sai no idioma de quem envia, não no do fornecedor | Decisão de produto, registrada |
| P3 | O comentário de `_apiTemplates` (`i18n.js`) cita só `apiErrors`, mas o código também casa chaves de UI com nome de erro | Comportamento seguro: valores opacos, ≥8 caracteres fixos, casamento ancorado. Comentário registrado para correção futura |
| P3 | `createApiError` também lê `payload.error.code`/`validation.code` | Só no cliente; registrado |
| P3 | `pagamento.js` (SaaS) interpola `max_users` sem escape (anterior); `my-company-view.js:156` (UBX) | Fora do escopo; registrados |

Fases desta etapa:
- Valores dinâmicos: `DYNAMIC_STATUS_VALUES.md`.
- 4º aviso F2: `F2_SESSION_MESSAGES_ANALYSIS.md`.
- Integração com a UBX: `UBX_INTEGRATION_PLAN.md`.
- Segurança do 503: PRs separados #1081 / #455.
