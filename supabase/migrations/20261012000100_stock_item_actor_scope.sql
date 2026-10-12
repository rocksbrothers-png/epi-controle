-- EST-V2: correção do achado da revisão independente. Sem reescrever 030.
-- Na inserção/troca de responsável ou de empresa, o ator deve pertencer
-- à empresa da peça. Mudanças posteriores do usuário preservam o histórico.
DROP TRIGGER IF EXISTS stock_item_block_actor_scope ON epi_stock_items;
CREATE TRIGGER stock_item_block_actor_scope BEFORE INSERT OR UPDATE ON epi_stock_items
    FOR EACH ROW EXECUTE FUNCTION stock_actor_company_guard('blocked_by_user_id');
