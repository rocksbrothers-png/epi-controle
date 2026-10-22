-- A destinação não reabre estoque nem altera a validade física comprovada.
ALTER TABLE epi_stock_items DROP CONSTRAINT IF EXISTS stock_item_operational_state;
ALTER TABLE epi_stock_items ADD CONSTRAINT stock_item_operational_state CHECK (status IN (
    'in_stock', 'available', 'reserved', 'delivering', 'delivered', 'blocked', 'blocked_expired', 'blocked_discard', 'blocked_return', 'blocked_analysis', 'blocked_rejected', 'blocked_archived', 'maintenance', 'hygiene', 'quarantine', 'returned_base', 'discard_pending', 'discarded', 'supplier_returned', 'donated')) NOT VALID;
ALTER TABLE epi_stock_events DROP CONSTRAINT IF EXISTS epi_stock_events_event_type_check;
ALTER TABLE epi_stock_events ADD CONSTRAINT epi_stock_events_event_type_check CHECK (event_type IN (
    'receipt', 'block', 'unblock', 'transfer', 'delivery', 'return', 'return_base', 'quarantine', 'discard', 'supplier_return', 'expiry_regularization', 'reserve', 'reservation_release', 'reconcile', 'disposition_requested', 'disposition_rejected', 'donation')) NOT VALID;
ALTER TABLE epi_stock_decisions DROP CONSTRAINT IF EXISTS epi_stock_decisions_action_check;
ALTER TABLE epi_stock_decisions ADD CONSTRAINT epi_stock_decisions_action_check CHECK (action IN (
    'unblock', 'return_base', 'quarantine', 'supplier_return', 'discard', 'donation')) NOT VALID;
