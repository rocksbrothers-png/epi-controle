# EST-V3.5 — plano prévio de resolução da integração

Registrado antes de combinar branches. Nenhum merge na main, force-push, deploy ou migração compartilhada autorizado.

Baselines: Corporate RBAC ddc8a78496ba3b7fa1d88a067766132fd2ed0c22 + R3 f934a4fbc0037888a7bc881bbc35d2be39260353; SaaS RBAC fe6fdeb1a868f7037c382db70de4b054e3af033e + R3 b202e8fbdd767380415b0043a137437100ef3e89.

Cada produto apresenta os mesmos oito conflitos na simulação:

| Arquivo | Conteúdo concorrente | Resolução proposta |
|---|---|---|
| static/i18n/en-GB.json | stock.pendingReg e stock.receipt | União das duas árvores de traduções, preservando valores e chaves; validar JSON e cobertura. |
| static/i18n/es-ES.json | stock.pendingReg e stock.receipt | União sem sobrescrever nenhuma árvore. |
| static/i18n/fr-FR.json | stock.pendingReg e stock.receipt | União sem sobrescrever nenhuma árvore. |
| static/i18n/nb-NO.json | stock.pendingReg e stock.receipt | União sem sobrescrever nenhuma árvore. |
| static/i18n/pt-BR.json | stock.pendingReg e stock.receipt | União sem sobrescrever nenhuma árvore. |
| static/index.html | tokens de cache dos assets (`?v=`) divergentes | Preservar o HTML estrutural auto-unido e recalcular um token único a partir dos assets combinados; conservar IDs/navegação de Biblioteca de Segurança/EPIs Aprovados. |
| tests/test_343_f4_portal_cpf_sem_cache.py | DIGESTO_PARIDADE_F4 calculado do app.js divergente | Recalcular digest normalizado do JS combinado e conservar todas as asserções do portal. |
| tests/test_343_f5b_navegacao_estado_inicial.py | DIGESTO_PARIDADE_F5B calculado do app.js divergente | Recalcular digest normalizado do JS combinado e conservar todas as asserções de navegação. |

A integração partirá dos HEADs corrigidos em branches dedicadas claude/est-v35-blockers-integration. Um commit de merge nessas branches manterá ambos os pais e todo o histórico; main permanecerá intocada. A união será aplicada aos JSONs por estrutura, e ao HTML por token de cache após conferir o conteúdo auto-unido, nunca pela seleção indiscriminada de ours/theirs. Manifesto de paridade será recalculado somente após resolução e comparado entre os produtos.

Regressão combinada obrigatória: testes de portal/navegação, Biblioteca de Segurança, EPIs Aprovados, recebimento por lotes, regularização e pendências HTTP, atomicidade/concorrência/FEFO, RBAC e isolamento, análise/testes Flutter/web e CI completa. Nova auditoria independente avaliará os HEADs isolados e os dois HEADs de integração. GREEN→RED→GREEN provará os gates específicos.

Teste visual funcional é pendência pré-deploy. READY FOR HUMAN MERGE DECISION = NO.

## Resolução efetiva

Os oito conflitos foram resolvidos conforme a proposta. Traduções pendingReg e receipt preservadas; index mantém HTML combinado e novo token de cache; digests F4/F5B recalculados sem alterar asserts. Workflow combinado executa ambos os contratos HTTP. Commit de integração conserva dois pais; main não foi alterada. Validação independente e CI dos novos HEADs são obrigatórias.
