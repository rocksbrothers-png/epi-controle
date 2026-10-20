# EST-V3.5 — correções da auditoria pós-merge

A conferência de requisição de compra passa a proteger os quatro cenários PM35-01 a PM35-04 da auditoria de 20/10/2026.

- **Duplicação:** a API recusa reabrir `checked`/`closed` como `received`. Também consulta os movimentos de origem da requisição sob a trava da PR: um lançamento já persistido impede novo recebimento mesmo se o status tiver sido revertido externamente. Reenvio `checked → checked` mantém zero novas peças.
- **Validade entre linhas:** cada linha/lote usa somente sua data e evidência. Linhas do mesmo EPI não herdam validade umas das outras. Catálogo e CA não preenchem validade física ausente.
- **Evidência:** no formato legado sem `lots`, `received_items[].manufacturer_validity_date` exige `received_items[].evidence` não vazia. A ausência de comprovação pode ser representada sem data, mantendo a peça desconhecida e inelegível. Com `lots`, a exigência de evidência continua em cada lote. A validação de todas as linhas ocorre antes de qualquer alteração da conferência.
- **Concorrência:** antes de ler saldo, o recebimento toma as travas físicas compartilhadas com reservas/entregas. Todos os escopos da conferência são travados em ordem de EPI/unidade, cobrindo saldo existente, saldo inicialmente ausente e vários EPIs em ordens opostas.

## Contrato legado com comprovação

```json
{
  "status": "checked",
  "actor_user_id": 123,
  "received_items": [
    {
      "id": 456,
      "received": true,
      "manufacturer_validity_date": "2027-10-20",
      "evidence": "Etiqueta do lote L-42 verificada na conferência"
    }
  ]
}
```

Os IDs acima são ilustrativos. O formato por `lots` já usado pelas telas R3 continua com quantidade, validade, evidência e identificação de cada lote. Não há preenchimento automático de validade, alteração de permissões, migração de schema ou regularização de dados históricos nesta correção.

## Verificação

`tests_postgres/test_est_v3_5_postmerge_receipt.py` usa HTTP real, JWT nativo e PostgreSQL. Cobre recusa de evidência ausente, não propagação entre linhas, desconhecida inelegível, rollback de conferência mista, reabertura/reenvio, status revertido com origem persistida, concorrência entre PRs com/sem saldo, vários EPIs em ordem oposta e recebimento concorrendo com entrega.

A sincronização do teste de duas PRs pausa a primeira leitura nativa. Antes da correção a segunda conexão lê o mesmo saldo; com a trava ela espera no PostgreSQL. O teste libera ambos os casos e exige o mesmo resultado persistido: duas peças, saldo 2 e movimentos 0→1→2. Assim não se usa uma barreira depois da trava que impediria o segundo worker de avançar e produziria um falso erro de fixture.

Com `APP_ENV=test`, `JWT_ENFORCEMENT_MODE=enforce` e `DATABASE_URL` apontando exclusivamente para PostgreSQL local descartável, executar:

```sh
python -m pytest -q tests_postgres/test_est_v3_5_postmerge_receipt.py
python -m pytest -q tests_postgres
python -m pytest -q tests
python flutter/tool/check_parity_drift.py
```

O workflow `Stock Validity Integration` executa a nova suíte e reconhece alterações isoladas nesse arquivo de regressão.
