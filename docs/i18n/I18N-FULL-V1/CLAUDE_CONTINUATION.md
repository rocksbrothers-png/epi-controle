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
