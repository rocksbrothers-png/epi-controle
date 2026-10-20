# EST-V3.5 — inicialização dos painéis de estoque

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

## Verificação

`node static/js/test/run-tests.js` inclui 18 cenários novos que executam as
funções reais do `app.js` em VM com transporte e DOM substituídos: navegação
clássica/SPA/partial:false, reentrada sem duplicar listeners, atualização pelos
três botões, falha isolada da listagem, carregamento/erro/recuperação, troca de
empresa/unidade e descarte de respostas/erros atrasados.

Também executar `python scripts/build_index.py check` e `pytest tests/`.
Os hashes de paridade F4/F5-B são recalculados para a alteração idêntica de
`app.js` e do runner; as asserções e listas de arquivos permanecem iguais.

Para validar após publicação, entrar em Estoque na navegação clássica e SPA,
verificar os três painéis, clicar em cada Atualizar e trocar empresa/unidade.
Uma indisponibilidade de rede deve produzir erro visível, sem indicar lista
vazia. A regularização exige os dados reais da peça e perfil autorizado.

Rollback: reverter o commit e reconstruir/publicar os assets correspondentes.
