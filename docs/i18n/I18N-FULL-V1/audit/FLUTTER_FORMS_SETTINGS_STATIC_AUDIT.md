# Revisão parcial independente — Users/Units/archival/QR

Fonte Corporate: HEAD46fd5d67 + alterações locais inspecionadas em 2026-10-28. Somente leitura; sem SDK do workspace, Flutter runtime, gerador ou modificação de produto.

## Contratos

`flutter-forms-contracts.json` compara AST normalizada do HEAD e worktree. As quatro telas mantêm todas as chamadas ApiClient com argumentos exatos e regras selecionadas idênticas. Foram comparados body, _roles(7), _unitTypes(3), _needsEmployee, _parseYears, canEdit, _generatePassword, _onDetect e _showResult onde existentes. Resultado: quatro pares iguais em API e regras. Isso verifica o recorte estático escolhido; não é equivalência semântica integral nem teste HTTP.

entity_labels.dart recebe código e retorna apenas label; nove papéis e três tipos têm mappings explícitos e fallback _=>role/type preserva dado desconhecido. _roles e _unitTypes originais, DropdownMenuItem.value e parâmetros de create/update não recebem tradução. Empresa/ator/vínculo permanecem nos payloads. As traduções afetam Text/tooltip/hint; selectedItemBuilder e isExpanded/itemHeight ajustam layout sem trocar values.

Users/Units passam a guardar erro local como callback lazy de AppLocalizations, limpam-no ao iniciar save e mantêm mensagem específica backend intacta. _errorMessageFrom só mudou o fallback literal para null; o consumer usa formSaveFailed no locale corrente. Política mantém parse int/min5, valores updateArchivalPolicy e gate master_admin/general_admin. QR preserva rawValue, picker, guarda de repetição, navegação e torch callback; mudanças são labels/tooltips.

Nenhum desvio material de contrato identificado na leitura desse recorte. Persistência de controllers/códigos durante mudança de idioma é compatível com a estrutura, mas requer prova runtime; este relatório não certifica renderização ou comportamento da câmera.

## Linguística parcial

O TSV contém 40 mensagens × cinco idiomas, conferidas nos cinco ARBs regionais atuais: 200/200 textos idênticos ao TSV e 200/200 conjuntos de parâmetros preservados. Leitura dos rótulos, verbos, papéis, termos de unidade e retenção não encontrou bloqueio linguístico material. Master/General continuam perfis diferentes em FR/NO. O mínimo de cinco anos e NR-6 permanecem referidos ao Brasil nos idiomas externos; não foi reavaliado fundamento jurídico. Nomes e exemplos João Silva/Macaé, números, códigos, company IDs e QR permanecem opacos.

`flutter-forms-settings-linguistic-review.json` contém cada locale/key/current e resultados. Conclusão parcial: apropriado para seguir à validação/CI do implementador; não representa aprovação da tarefa integral nem certificação independente de runtime. As 36 provas reais informadas pelo implementador não foram reexecutadas por este auditor e não foram usadas como resultado independente.
