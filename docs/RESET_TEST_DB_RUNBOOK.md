# Reset controlado do banco de teste

Este procedimento **apaga 100% dos dados atuais** (cadastros, transações, QR, estoque, entregas, fichas e assinaturas) e recria a base limpa.

## Comando único

```bash
DATABASE_URL="postgres://..." python scripts/reset_test_db.py
```

## O que o script faz

1. `DROP SCHEMA public CASCADE`
2. `CREATE SCHEMA public`
3. `GRANT ALL ON SCHEMA public TO public`
4. Executa `init_db()` para recriar tabelas/estrutura/migrations iniciais
5. Recria o bootstrap inicial (admin master inicial)

## Resultado esperado

- IDs e sequências reiniciados.
- Nenhum dado legado remanescente.
- Sistema volta a subir com bootstrap limpo.
