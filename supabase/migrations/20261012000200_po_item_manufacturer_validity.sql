-- EST-V3.5-F (G02): validade do fabricante do LOTE recebido, no item da PO.
-- Substitui a antiga escrita no catálogo (epis.epi_validity_date) no caminho da
-- PO: a validade é capturada na conferência ('received') e materializada na peça
-- ('checked'), sem ler o catálogo. Coluna por item/lot, não por EPI.
-- Idempotente (ADD COLUMN IF NOT EXISTS) — reaplicável sem erro.
ALTER TABLE purchase_order_items
    ADD COLUMN IF NOT EXISTS manufacturer_validity_date TEXT NOT NULL DEFAULT '';
