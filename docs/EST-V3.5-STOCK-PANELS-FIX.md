# EST-V3.5 — painéis de estoque e validade comprovada no recebimento manual

O fluxo completo com anexos, seleção de peças e conciliação de saldo sem QR está
documentado em [EST-V3.5-LOT-EVIDENCE.md](EST-V3.5-LOT-EVIDENCE.md).

Na navegação clássica, entrar em Estoque não executava o hook que vinculava
os botões e consultava Gestão de Validade, Pendentes de regularização e
Estoque bloqueado. Os painéis exibiam o texto estático de lista vazia e os
botões Atualizar permaneciam sem ação. A navegação SPA opcional executava
esse hook, fazendo o problema depender do modo de navegação.

## Correção

- A entrada clássica e a entrada com `partial:false` executam o mesmo hook
  usado pela navegação SPA. O fluxo SPA mantém uma única atualização.
- Os três painéis consultam seus recursos independentemente da listagem de
  EPIs; uma falha nessa listagem não interrompe as consultas dos painéis.
- Os botões Atualizar refazem a consulta do respectivo painel. Trocar a
  empresa/unidade do estoque ou a unidade da configuração também atualiza
  os painéis.
- Carregamento, sucesso vazio e erro são estados distintos. Erros ficam
  visíveis mesmo com o log de diagnóstico desativado. Respostas e erros de
  consultas anteriores não substituem o resultado da consulta mais recente.
- O HTML gerado foi reconstruído com a nova versão dos assets. As mensagens
  de erro e contagem estão nos cinco idiomas da interface.

## Relação com QR indisponível

O saldo físico por tamanho inclui peças em estoque com validade desconhecida.
A entrega exige elegibilidade física, além de saldo livre e escopo autorizado.
Corrigir a consulta das pendências permite ao perfil autorizado acessar a ação
de regularização existente, informando validade física comprovada, evidência
verificável e justificativa. A correção não preenche datas históricas, não gera
peças ausentes e não altera permissões nem critérios de liberação do backend.

## Entrada manual por lote

A entrada manual agora solicita uma escolha explícita: comprovação por
embalagem/etiqueta (`label`), documento do fabricante (`manufacturer_document`)
ou validade ainda desconhecida. Cada entrada representa um lote; para lotes
diferentes devem ser feitas entradas separadas. Com comprovação, são exigidos
`lot_code`, `physical_expiry_date`, `expiry_source` e `expiry_evidence`.
`manufacture_date` continua separado da data de vencimento. Datas inválidas,
validade anterior à fabricação e comprovação parcial/conflitante são recusadas
antes de criar movimento, saldo ou QR.

Capturar validade física exige a permissão existente
`stock:regularize_validity`, além de `stock:adjust` e do escopo operacional de
unidade. Administrador Local e Gestor de EPI podem capturá-la; o Administrador
Geral continua podendo registrar entrada sem comprovação, mas não conceder
validade. A autorização é reaplicada no backend, inclusive via API direta.

A validade e sua evidência são gravadas em cada peça recém-criada, junto do
lote e fabricação física, sem alterar nem consultar a validade do catálogo/CA
para autorizar a peça. Recebimento comprovado gera evento `receipt` com ator,
escopo e snapshot da comprovação na mesma transação. Lote já vencido entra como
`blocked_expired`; um lote válido torna-se candidato físico, sujeito ao saldo
livre e demais regras do backend. A trava de escopo compartilhada protege o
saldo durante recebimentos concorrentes.

Clientes legados sem os novos campos continuam registrando peças com validade
desconhecida e inelegíveis. Na web, a opção desconhecida mostra que as peças
ficarão pendentes de regularização. Esse recebimento não regulariza peças
antigas nem recria QRs para saldos sem lastro físico.

## Verificação

`node static/js/test/run-tests.js` inclui 18 cenários novos que executam as
funções reais do `app.js` em VM com transporte e DOM substituídos: navegação
clássica/SPA/partial:false, reentrada sem duplicar listeners, atualização pelos
três botões, falha isolada da listagem, carregamento/erro/recuperação, troca de
empresa/unidade e descarte de respostas/erros atrasados.

Também executar `python scripts/build_index.py check` e `pytest tests/`.
`tests_postgres/test_stock_manual_receipt_validity_http.py` exercita HTTP/JWT
real, PostgreSQL, os dois perfis e fontes autorizadas, lotes com datas próprias,
desconhecidos, vencidos, evidência/data inválida, perfis negados, escopo e rollback
integral quando a auditoria falha. A suíte está incluída na CI física dedicada.
Os hashes de paridade F4/F5-B são recalculados para a alteração idêntica de
`app.js` e do runner; as asserções e listas de arquivos permanecem iguais.

Para validar após publicação, entrar em Estoque na navegação clássica e SPA,
verificar os três painéis, clicar em cada Atualizar e trocar empresa/unidade.
Uma indisponibilidade de rede deve produzir erro visível, sem indicar lista
vazia. A regularização exige os dados reais da peça e perfil autorizado.

Rollback: reverter o commit e reconstruir/publicar os assets correspondentes.
