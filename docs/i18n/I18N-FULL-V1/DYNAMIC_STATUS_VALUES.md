# Valores dinâmicos de status nos erros do backend (`{get}`, `{postatuslabel}`) — análise e proposta

Status: **proposta, não implementada.** Nenhum estado persistido, enum, identificador ou payload foi alterado.
O campo `i18n: {key, params}` **não** é usado.

## O que esses placeholders são

| Template (pt-BR) | Origem do valor | Valor persistido | Valor na mensagem |
|---|---|---|---|
| `Ação "{actionlabel}" não permitida no status atual ({get}).` (EPI em teste, 15 ações) | `CANDIDATE_STATUSES[status]`, `modules/ppe_tests/service.py` `_require_status` | código (`em_teste`, `teste_suspenso`, …) | rótulo pt-BR (`Em Teste`) |
| `Revisão / Reenvio / Aprovação indisponível: PO em "{postatuslabel}".` e `Ação "{act}" indisponível: PO em "{postatuslabel}".` | `PO_STATUS_LABELS` via `po_status_label()`, `epi_backend/purchase_order_workflow.py` | código (`waiting_admin_review`, …) | rótulo pt-BR |
| `Transição inválida: {get} não permite {definition}.` | `PURCHASE_STATUS_LABELS[current]` e `WORKFLOW_ACTIONS[a]['label']`, `epi_backend/purchase_workflow.py` | código | rótulos pt-BR |
| `Reserva já {get}. Atualize e tente novamente.` | `reservation['status']`, `modules/stock/reservations.py` | código (`consumed`, `released`) | **o próprio código** (inglês no meio da frase pt-BR) |

Conclusão:
- Os quatro casos vêm de **listas fechadas**: 12 status de EPI em teste, 13 de PO, 19 de requisição, 8 ações de compra e 3 estados de reserva.
- O valor persistido e o retornado pela API nos campos `status` é sempre o **código canônico**.
- O texto do erro leva um **rótulo de interface** (ou o código cru, no caso da reserva). Nenhum deles é identificador que o cliente use para decidir comportamento.
- Ficam fora: `{get}` com nome de fornecedor, de EPI ou de empresa (`Fornecedor "{get}" está inativo.`) e datas. São **texto opaco** do usuário e não podem ser traduzidos.

## Proposta (apresentação, mecanismo existente)

O `describeApiError` já resolve variáveis por referência: `{key}` e `{field}` viram `apiErrors.fields.<valor>` via `refs`. A proposta generaliza isso **por template e por placeholder**, com lista fechada:

```json
"apiErrors": {
  "valueLabels": {
    "ppeTestStatus": {"Em Teste": "ppetest.status.em_teste", "...": "..."},
    "poStatus":      {"Aguardando Aprovação": "purchase.poStatus.pending_approval", "...": "..."},
    "reservationStatus": {"consumed": "stock.reservation.consumed", "released": "stock.reservation.released"}
  },
  "valueBindings": {
    "m_<hash do template _require_status>": {"get": "ppeTestStatus"},
    "m_<hash de 'Revisão indisponível…'>":  {"postatuslabel": "poStatus"}
  }
}
```

No motor, depois do casamento do template:
1. Para cada placeholder com `valueBindings`, o motor procura o valor capturado no mapa da lista daquele template, **por igualdade exata**.
2. Se encontrar, o valor vira referência ao rótulo do idioma ativo; o caminho é o mesmo de `refs`/`resolveMessageVars` já usado por `{key}`.
3. Se não encontrar, o valor fica **opaco e como veio** (comportamento atual).

Por que listas por template, e não um mapa global: rótulos repetem entre domínios. “Rascunho” aparece em PO, requisição e EPI em teste, e um mapa global erraria a origem. Fora das listas nada é traduzido, então nome de usuário nunca entra.

Testes necessários:
- todo rótulo pt-BR dos dicionários do backend aparece no mapa (gate gerado do código, como o inventário);
- todo alvo existe nos 5 catálogos;
- um valor fora da lista continua opaco;
- o payload fica idêntico com e sem a tradução;
- o pt-BR exibido é idêntico ao texto do servidor.

Lacunas de catálogo a preencher (rótulos ainda sem chave de UI): 7 status de EPI em teste, 3 de PO, 1 de requisição e os 3 de reserva.

Alternativa sem mudar o motor: expandir por valor no inventário, como já é feito com o domínio literal. Para `_require_status` isso dá 15 ações × 12 status = 180 templates, o que é combinatório e caro de manter. **Recomendação:** `valueBindings` no motor, num lote próprio e depois do merge da I18N-FULL-V1.
