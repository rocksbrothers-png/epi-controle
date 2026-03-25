# Prompt para o Codex — mover QR Code de Cadastro de EPI para Controle de EPI

Use este prompt no Codex para implementar a mudança:

```text
Você é um engenheiro full-stack e vai alterar o sistema EPI Controle.

Objetivo funcional
1) Remover totalmente a funcionalidade de QR Code da aba/página “Cadastro de EPI”.
2) Adicionar essa funcionalidade na aba/página “Controle de EPI”.
3) No “Controle de EPI”, quando houver recebimento/entrada de estoque de um item, o sistema deve gerar automaticamente a quantidade equivalente de QR Codes para etiquetagem.
   Exemplo: se eu receber 10 unidades de “Luva”, o sistema deve gerar 10 QR Codes (1 por unidade).

Regras de negócio
- Cada unidade recebida deve ter um identificador único (ID unitário).
- Cada QR Code deve representar uma unidade específica, contendo no mínimo:
  - ID da unidade
  - nome do EPI
  - lote (se existir)
  - data de entrada
  - status inicial: “Em estoque”
- Não gerar QR no cadastro do produto (Cadastro de EPI). O cadastro deve ficar apenas com dados mestres do EPI.
- A geração de QR deve acontecer no fluxo de movimentação/entrada de estoque (Controle de EPI).

Mudanças esperadas no sistema
Frontend
- Remover botões, campos, ações e textos de QR Code da tela “Cadastro de EPI”.
- Incluir na tela “Controle de EPI”:
  - campo de quantidade recebida
  - ação “Gerar QRs” após confirmar entrada
  - listagem/preview dos QRs gerados
  - ação para impressão em lote (etiquetas)
- Ajustar validações para impedir quantidade <= 0.

Backend
- Criar/ajustar endpoint para registrar entrada de estoque com quantidade.
- Criar/ajustar endpoint para gerar N QR Codes com base na quantidade recebida.
- Persistir cada unidade como registro individual para rastreabilidade.
- Garantir unicidade de código por unidade.

Banco de dados
- Se necessário, criar tabela de unidades de EPI (ex.: epi_unidades), relacionada ao produto EPI.
- Campos sugeridos: id, epi_id, codigo_unico, lote, data_entrada, status, qr_payload, created_at, updated_at.
- Adicionar índices para busca por codigo_unico e epi_id.

Impressão/etiquetas
- Disponibilizar saída para impressão dos QRs em lote (PDF ou layout imprimível).
- Cada etiqueta deve exibir nome do EPI + QR + código legível.

Critérios de aceite
- [ ] Na aba Cadastro de EPI não existe mais nenhuma funcionalidade de QR Code.
- [ ] Na aba Controle de EPI, ao registrar entrada de 10 luvas, são gerados 10 QRs únicos.
- [ ] Os 10 QRs ficam vinculados ao item e podem ser listados/consultados.
- [ ] É possível imprimir as 10 etiquetas em lote.
- [ ] Testes cobrindo geração unitária, quantidade e unicidade.

Testes mínimos
- Teste unitário: geração de N IDs únicos para N unidades.
- Teste de integração: entrada de estoque -> persistência de N unidades -> geração de N QRs.
- Teste de interface: botão/ação disponível apenas em Controle de EPI.

Entrega
- Mostrar diff das alterações.
- Executar testes e informar resultado.
- Documentar rapidamente onde ficou cada mudança (frontend, backend e banco).
```

## Versão curta (para uso rápido)

```text
Remova a geração de QR Code da aba Cadastro de EPI e mova para a aba Controle de EPI.
No Controle de EPI, ao lançar entrada de estoque, gere 1 QR por unidade recebida.
Exemplo: entrada de 10 Luvas => gerar 10 QR Codes únicos para etiquetagem.
Persistir cada unidade individualmente para rastreabilidade, permitir listagem e impressão em lote das etiquetas.
Atualize frontend, backend e banco conforme necessário e entregue com testes.
```
