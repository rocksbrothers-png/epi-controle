-- Migration: pedido de compra emitido para um CNPJ específico (Multi-CNPJ)
--
-- Diferente das entregas e requisições — onde o CNPJ é *derivado* do vínculo
-- jurídico do colaborador — o CNPJ do pedido de compra é uma escolha no momento
-- da emissão: o pedido pode ser emitido para a empresa (todos os CNPJs) ou para
-- um CNPJ específico. Por isso é um atributo próprio do pedido.
--
-- NULL = pedido da empresa (comportamento histórico preservado).

ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS legal_entity_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_purchase_orders_legal_entity
    ON purchase_orders (legal_entity_id);
