# EST-V3.5-R1 — remediação B35-01 a B35-05

Esta é uma implementação de correções, com reprodução dos defeitos e testes próprios. O autor das correções não emite aprovação independente. A próxima auditoria deve utilizar os novos HEADs imutáveis dos PRs existentes, registrados no relatório de execução e nas descrições dos PRs.

Baseline Corporate #1027: `4f287a43e2bb2cbb50fc1ff023c08b62ec0d8d62`.
Baseline SaaS #399: `0ddcfeb50435b2e28b51195130eccc39f4638a7d`.
Ambos eram drafts abertos, sem threads de revisão. O trabalho anterior no checkout local foi preservado; as correções foram feitas em clones isolados das mesmas branches.

## Causas e correções

| Achado | Causa reproduzida | Correção |
|---|---|---|
| B35-01 | Data vazia era considerada não vencida; a peça desconhecida podia gerar entrega, movimento e ficha. | `effective_delivery_expiry` retorna apenas data física; `classify_physical` trata NULL, vazio, formato inválido e coluna ausente como desconhecido. `create_delivery_service` valida antes do claim e faz rollback de qualquer falha. |
| B35-02 | Reservas usavam o contador de `unit_epi_stock`, mesmo sem peças elegíveis que o respaldassem. | `unit_balance` separa bruto, peças rastreadas, elegíveis, reservas, divergência e déficit. Capacidade operacional = mínimo entre bruto não negativo e peças elegíveis; livre = máximo entre zero e capacidade menos reservas. |
| B35-03 | Consulta filtrava status, mas admitia peças vencidas ou desconhecidas; DTO usava catálogo. | Disponíveis são exclusivamente peças operacionais, conhecidas e não vencidas, em FEFO, limitadas pela capacidade livre. `StockItem` usa `physical_expiry_date` e autorização do servidor. Cubits recusam candidatos manuais e QR inelegíveis. |
| B35-04 | Menor data e fallback de catálogo ocultavam lotes mistos, unknown e ausência de peças. | Resumo físico mantém cada categoria; data cadastral é separada. `Epi`, `StockState`, filtros, cards e listas usam fatos físicos autoritativos. |
| B35-05 | Comparação de horário local do Flutter divergia de datas do backend no dia do vencimento. | Política por empresa: fuso IANA válido, data civil do servidor, último dia inclusivo, janela configurada inclusiva. Cliente usa classificação e contagens do servidor; relógio do cliente não concede entrega. |

`modules/stock/eligibility.py` centraliza calendário, elegibilidade e resumo. Reservas, entregas e transições de reserva tomam o mesmo bloqueio PostgreSQL no EPI e no saldo da unidade; a entrega também bloqueia a peça e revalida status, QR, empresa, unidade e pedido. A baixa preserva os movimentos e a ficha existentes. Quantidade por peça continua sendo 1, conforme o modelo físico vigente.

Pedido de outra empresa/unidade/EPI/colaborador é recusado. Entrega direta não consome saldo comprometido por reserva. Entrega vinculada à própria reserva pode consumir sua quantidade restante; uma entrega parcial mantém o pedido reservado até o consumo total.

## Contratos backend e Flutter

- `GET /api/stock/epis`: `catalog_validity_date` é cadastral; `effective_validity_date` é a menor data física conhecida dentre peças com status disponível, ou NULL. Ela é apenas informação. `physical_validity_summary` contém `physical_pieces`, `eligible_pieces`, `blocked_pieces`, `valid`, `expiring`, `expired`, `unknown`, `status`, `count_unit=physical_pieces`, `as_of_date`, `timezone`, `warning_days` e `expiry_day_inclusive`. `available_quantity` é saldo operacional livre da unidade; sem unidade é NULL.
- `GET /api/stock/available-items`: apenas candidatos físicos elegíveis em FEFO, com `physical_expiry_date`, `physical_validity_status`, `eligible_for_delivery` e `validity_policy`. `request_id` opcional permite considerar a reserva ativa do próprio pedido, validando seu escopo.
- `GET /api/stock/lookup-qr`: consulta continua informativa para peça bloqueada ou desconhecida, mas devolve `eligible_for_delivery=false`. QR de outro tenant não é resolvido.
- `POST /api/deliveries`: backend revalida todos os fatos na transação. Uma lista ou QR obtidos antes não conferem autorização persistente.
- Filtros Flutter contam **EPIs distintos**; resumo de cada EPI conta **peças físicas**. Um EPI misto pode aparecer nos filtros vencido, próximo e desconhecido. EPI sem peças aparece no filtro de ausência de estoque, sem assumir a validade do catálogo.

Datas físicas nunca são preenchidas artificialmente. Os fixtures com validade futura explícita são dados de testes isolados. Validade do CA permanece separada.

## Banco e migração

Não há DDL novo nesta remediação. A migração Python `032_po_item_manufacturer_validity` e o SQL correspondente são preservados byte a byte. O teste de atualização parte dos commits main anteriores à 032, sem a coluna nova, com pedido recebido, peça sem data/custo físico conhecido e saldo existente. Verifica criação da coluna, uma única linha `applied` em `app_migrations`, preservação de todos os valores anteriores, NULLs desconhecidos e bootstrap repetido sem alteração de dados ou `applied_at`. Banco novo é exercitado pelas suítes PostgreSQL e pelo fixture HTTP.

## Testes permanentes e reprodução

Executar somente em PostgreSQL descartável, com roles `anon` e `authenticated`, dependências de `requirements.txt`, pytest e `APP_ENV=test`. Nenhum comando desta fase deve usar banco compartilhado.

```sh
pytest -q
ruff check tests scripts --select F401
node static/js/test/run-tests.js
# Em banco PostgreSQL isolado, com DATABASE_URL e JWT_ENFORCEMENT_MODE=enforce:
pytest tests_postgres/ -q
pytest tests/test_est_v3_5_r1_policy.py -q
cd flutter
flutter pub get
dart run melos run gen:l10n
dart run melos run gen
dart run melos run lint
dart run melos run test
python3 tool/check_parity_drift.py
```

`tests_postgres/test_est_v3_5_r1_postgres.py` cobre catálogo futuro/vencido/ausente sem data física; reserva só unknown, só vencida, mista e sem peças; FEFO de lotes; resumo misto/vazio; saldo divergente; terminalidade; reserva própria; pedido estrangeiro; QR; RBAC; rollback após claim; e conexões PostgreSQL concorrentes reais. As corridas entrega/entrega, reserva/reserva e entrega/reserva usam barreira, dois workers e três repetições. Há também duas peças disputando o último saldo agregado.

`tests/test_est_v3_5_r1_policy.py` cobre datas inválidas, coluna física ausente, último dia inclusivo, fusos com datas civis diferentes e janelas 0/60. Testes Flutter verificam contratos, filtros, catálogo separado e rejeição de seleção manual/QR inelegível.

O novo workflow `Stock Validity Integration` executa `stock_http_integration_test.dart` com Dio, JWT real, `app.EpiHandler` e PostgreSQL 16 descartável. O teste é explicitamente pulado na suíte Flutter comum quando não há `EST35_HTTP_CONTEXT_JSON`; o workflow dedicado fornece o contexto e efetivamente o executa. O fixture `scripts/stock_r1_http_fixture.py` aceita somente APP_ENV=test e banco loopback de nome restrito; não usa credenciais ou dados de produção. Gera chave aleatória em memória, inicia o servidor real e passa JWT e contexto ao processo Flutter por ambiente. Nenhum arquivo de contexto, chave ou token é gravado. O fixture encerra o servidor ao concluir o teste.

A primeira CI detectou uma chave determinística de fixture no workflow e gravação do JWT de teste em arquivo. Ambas foram removidas. Para preservar o histórico dos PRs, `.gitleaksignore` contém apenas os dois fingerprints exatos dos commits que introduziram aquela chave pública de teste descartável, já retirada; nenhuma regra, diretório, arquivo futuro ou linha futura é ignorada. A configuração `.gitleaks.toml` não muda. Notas CodeQL de ciclo de importação e importação duplicada também foram corrigidas.

Sabotagens executadas em cópias descartáveis, em ambos os produtos, com DB próprio por etapa e restauração de bytes:

1. Remover o gate central de validade, classificando tudo como elegível → testes de unknown detectam entrega 201 e escrita indevida.
2. Reintroduzir catálogo em `effective_validity_date` → teste do payload desconhecido detecta data física fabricada.
3. Voltar a capacidade operacional ao agregado bruto → testes de reserva detectam autorização sem peças elegíveis.

Cada cenário fez **GREEN → RED por asserção de negócio → GREEN**, sem erro de importação/sintaxe como substituto da sabotagem. Logs, comandos, snapshots de dados, resultados e hashes estão no pacote de evidências da execução.

## Limites e governança

Divergência de saldo é exposta, e a capacidade usa o limite conservador; esta fase não regulariza automaticamente dados antigos. Validade desconhecida deve ser corrigida pelo processo auditável existente antes de uso. Testes não equivalem a validação manual em câmera/dispositivo físico, homologação de produção ou aprovação independente. A conclusão abrange os cinco achados, sem antecipar aprovação de outros fluxos ou de fases posteriores, como destinação completa e valorização financeira por custo real.

Backend autorizado, identidades de Android/iOS/web e isolamento Corporate × SaaS são preservados; mesmos contratos físicos não significam backend compartilhado.

```text
MERGE = NÃO
DEPLOY = NÃO
MIGRAÇÃO EM AMBIENTE COMPARTILHADO = NÃO
BRANCH PROTECTION = INALTERADA
READY FOR HUMAN MERGE DECISION = NO
NEXT = EST-V3.5-R1-INDEPENDENT-VALIDATION
```

STOP.
