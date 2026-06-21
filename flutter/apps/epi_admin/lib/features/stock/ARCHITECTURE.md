# Arquitetura alvo — stock

Este módulo deve ser migrado gradualmente para a estrutura:

- `presentation/`: páginas, widgets e cubits.
- `domain/`: entidades, contratos de repositório e use cases.
- `data/`: datasources REST e implementações de repositório.

Regras obrigatórias:

1. Não acessar Supabase/banco diretamente no Flutter.
2. Não duplicar regra de negócio do backend Python.
3. Preservar contratos REST existentes durante a migração.
4. Consumir `SessionContext` para `companyId`, `unitId`, `role` e `permissions`.
5. Validar paridade com o legado antes de substituir a tela em produção.
