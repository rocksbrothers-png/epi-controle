<!--
Título do PR: use Conventional Commits — feat|fix|chore|docs|refactor|test|ci(escopo): resumo
Ex.: feat(estoque): baixa automática ao confirmar entrega
-->

## O que muda
<!-- Descreva objetivamente a alteração e o porquê. -->

## Tipo
- [ ] feat (nova funcionalidade)
- [ ] fix (correção de bug)
- [ ] refactor / chore
- [ ] docs
- [ ] ci / infra

## Checklist
- [ ] `flutter analyze` e `flutter test` passam (se tocou em `flutter/`)
- [ ] `pytest tests/` passa (se tocou no backend)
- [ ] Regra de negócio permanece **centralizada no backend** (não migrei lógica para o app)
- [ ] Isolamento **Multi-Tenant** preservado (tenant_id / company_id / unit_id respeitados)
- [ ] Migrations acompanham índices/constraints/RLS quando aplicável
- [ ] Sem strings hardcoded no Flutter (usar `context.l10n`)
- [ ] Documentação/CHANGELOG atualizados quando aplicável

## Impacto Multi-Tenant
<!-- A mudança afeta escopo UNIQUE / GLOBAL / UNIT ou Joint Venture? Descreva. -->

## Como testar / rollback
<!-- Passos para validar. Como reverter caso algo dê errado. -->

## Issues relacionadas
<!-- Closes #123 -->
