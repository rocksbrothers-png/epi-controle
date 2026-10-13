# PORTAL-DOCS-V1 — implementação para revisão

Novas abas **EPIs Aprovados** e **Biblioteca de Segurança** no portal web e Flutter, com gestão documental administrativa, originais privados, versões preservadas e páginas autenticadas. Esta é uma implementação acompanhada de testes próprios; não constitui aprovação independente.

**MERGE = NÃO · DEPLOY = NÃO · MIGRAÇÕES EM AMBIENTE COMPARTILHADO = NÃO · BRANCH PROTECTION = INALTERADA · READY FOR HUMAN MERGE DECISION = NO.**

## Baseline e escopo

| Produto | main consultado antes dos edits |
|---|---|
| Corporate | `b5570dbb0a809d164d8439ba8d2df7288b4f0302` |
| SaaS | `4b457d3c7c04c7915d1f519b04acf4349d342307` |

Branches dedicadas `codex/portal-docs-v1`, checkouts separados e preservação dos HEADs e hashes do trabalho pendente nos checkouts originais. Nenhum backend, banco, applicationId, bundle identifier ou lista de backends autorizados foi compartilhado ou substituído. SaaS continua sendo o backend do seu Flutter web/Android/iOS; Corporate permanece independente.

Na consulta inicial não havia PRs abertas. Durante a execução surgiram as PRs de regularização **Corporate #1029** e **SaaS #402**, posteriormente integradas em main por outro ator. Main foi reconferido: Corporate `adb857e9d74cb68722a79825ecd10bfa3bc553a7` e SaaS `80406c438b75f220cd542c21f1422deadffdbbd0`. As branches dos drafts documentais foram sincronizadas com esses commits para resolver o conflito do manifesto de paridade; permissões, exports e traduções preservam ambas as funcionalidades. O diff documental contra main mantém escopo próprio. Nenhuma dessas PRs foi mergeada por esta execução.

## Auditoria inicial

| Elemento | Baseline | Evidência / decisão |
|---|---|---|
| Tabela administrativa de EPIs aprovados | FUNCIONAL | `static/js/views/epis.js::renderApprovedEpis`, `modules/epis/service.py::fetch_epis`; catálogo PostgreSQL existente reutilizado. |
| Consulta desse catálogo no portal | INEXISTENTE | Portal web tinha ficha/solicitação/avaliação; Flutter tinha entregas/fichas. Novas abas adicionadas. |
| Entrada Flutter no portal | PARCIALMENTE FUNCIONAL | `portal_api.dart::getAccess` enviava apenas token; backend exigia `cpf_last3`. Fluxo corrigido, inclusive desafio após QR e retenção apenas em memória. |
| Biblioteca oficial, upload privado, versões e publicação | INEXISTENTE | Não havia infraestrutura documental correspondente; novas tabelas privadas e serviços. |
| Visualizador seguro de Office com abas/páginas | INEXISTENTE | Conversão e visualizador integrados, sem substituir matrizes por texto extraído. |
| Permissões documentais específicas | INEXISTENTE | Novo piso `safety_library:manage`, exclusivamente Geral e Registro; backend também exige os dois papéis exatos e Bearer válido. |

O catálogo aprovado informa aprovação cadastral. **Não informa disponibilidade de estoque** e não usa validade de CA como validade física. A DTO exclui saldos e datas físicas; vida útil não informada é `null`.

## Persistência e migração

Migração numerada **034_safety_library**, SQL `supabase/migrations/20261013000100_safety_library.sql`, registrada pelo runner em `app_migrations`. Numeração independente da regularização de estoque pendente. SQLite usa `ensure_safety_library` para desenvolvimento; produção PostgreSQL possui uma única fonte DDL numerada.

| Tabela | Conteúdo |
|---|---|
| `safety_documents` | Empresa, criador, publicação atual e arquivamento. |
| `safety_document_versions` | Revisão, rótulo de versão, título, categoria, vigência, associações/ACL, original BYTEA, MIME/tamanho/SHA256, manifesto, idempotência, criador e estado. |
| `safety_preview_pages` | Páginas PNG privadas por versão/aba/página. |
| `safety_document_audit` | Acessos, decisões, recusas, mudanças, ator/colaborador/unidade e timestamp UTC. Append-only. |
| `safety_document_policy` | Permissão de download administrativo de original, desligada por padrão. |

FKs compostas impedem trocar empresa entre documento, versão, publicação e página. Triggers preservam versões, páginas e auditoria, vedam exclusão e validam transições. Estados: rascunho → publicado → substituído/arquivado; rascunho também pode ser arquivado. Documento arquivado não retorna por uma operação comum. Originais e versões anteriores permanecem disponíveis aos administradores autorizados dentro da política.

Upload renderiza antes da gravação, revalida ator/empresa/permissões depois da conversão e mantém a empresa da requisição. Operações serializam por empresa com lock PostgreSQL; revisões e idempotência não duplicam em envios simultâneos. Publicação troca o ponteiro para uma versão pronta; o rascunho seguinte não oculta a publicação atual.

## Contratos HTTP

Todas as respostas documentais têm `private, no-store`, `nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` e política de incorporação. Origem web externa exige configuração CORS explícita. Sem original URL, bucket público ou link permanente na DTO do colaborador.

| Superfície | Operações |
|---|---|
| `POST /api/employee-library/approved-epis` | Catálogo ativo autorizado, sem dados de elegibilidade física. |
| `POST /api/employee-library/documents` | Publicação vigente autorizada por empresa/unidade/setor/atividade. |
| `POST /api/employee-library/manifest` | Identidade da versão publicada, abas e páginas; associações EPI filtradas. |
| `POST /api/employee-library/page` | Somente PNG da representação autorizada; revalida cada acesso. |
| `POST /api/employee-library/photo` | Foto do EPI autorizada, reencodificada e sem metadados do original. |
| `POST /api/safety-library/options, documents, upload` | Gestão: unidades/EPIs/categorias, versões e upload. |
| `POST /api/safety-library/publish, archive, history, policy` | Justificativa nas decisões, histórico e política auditada. |
| `POST /api/safety-library/manifest, page` | Administradores podem revisar suas versões, inclusive anteriores. |
| `GET /api/safety-library/original/{version_id}` | Original apenas para Geral/Registro, própria empresa e política habilitada. Colaborador sempre recusado. |

Portal envia `token` e `cpf_last3` em JSON nas novas leituras, sem armazenamento no navegador. Contexto vem do servidor, incluindo movimento temporário vigente calculado no mesmo fuso da empresa usado na vigência documental; `company_id`/`unit_id` enviados pelo cliente não substituem a autoridade. Não publicado, futuro, substituído ou arquivado não aparece para o colaborador.

Upload exige título, categoria, versão, vigência ISO, alcance de unidades explícito, arquivo/base64, MIME coerente e chave de idempotência. Limites: original 20 MiB, corpo de upload 28 MiB, demais corpos 64 KiB, até 160 páginas/32 milhões de pixels por página/96 MiB de previews. Caminhos, extensões, conteúdo, associações e justificativas são validados no backend.

## Visualização e segurança de arquivos

PDF rasterizado com navegação/zoom; DOCX convertido para PDF e páginas; XLSX/XLS exportados por seleção UNO explícita de cada aba visível, respeitando áreas de impressão, imagens, legendas e células mescladas; PNG/JPEG orientados corretamente, transparência sobre branco, EXIF removido. Web usa diálogo integrado e Flutter usa `InteractiveViewer`, seleção de abas, páginas e zoom. Não há controles de download, salvar ou exportar na biblioteca do colaborador.

A conversão ocorre em processo sem credenciais herdadas, diretório privado, limites de recursos e timeout. **libseccomp obrigatório**, com teste real de bloqueio de sockets Internet; Unix IPC permitido para UNO. MacroExecutionMode é o constante UNO **NEVER_EXECUTE**, atualizações externas desativadas e perfil isolado. Macros/VBA/XLM, DDE, referências externas ativas, objetos incorporados, cifragem, zip bombs, PDF ativo e SVG incorporado são recusados.

O DOCX fornecido referencia um template `.dotx` em um caminho externo de estação de trabalho. Essa referência é removida somente da cópia de conversão; original permanece intacto e a limitação é exibida. Formatos não suportados/conversão falha têm recusa explícita e não podem ser publicados como preview pronta.

**Fidelidade:** a representação Office preserva conteúdo visual e estrutura, mas fontes/paginação podem diferir do aplicativo original; isso é informado no visualizador. Não se afirma igualdade pixel a pixel. O XLS denso precisa de zoom. **Segurança:** o ambiente não oferece namespace/Landlock para jail completo de filesystem; o bloqueio testado é de rede/recursos e a validação de conteúdo. Antes de produção, revisar isolamento do conversor e atualização de bibliotecas nativas. **Cópia:** screenshots e extração técnica da representação visível não podem ser totalmente impedidos. O servidor proíbe o original ao colaborador.

Dockerfiles de ambos os produtos incluem LibreOffice Writer/Calc, UNO, libseccomp e fontes. `scripts/check_library_runtime.py` testa a conversão real offline no build/start, sem acessar banco nem arquivos fornecidos pelo usuário.

## Testes e evidências reproduzíveis

Ambiente de execução: PostgreSQL 17 em cluster próprio local, bancos distintos `portal_docs_corporate` e `portal_docs_saas`. Nenhuma migração compartilhada/remota. Suite de CI adicional usa PostgreSQL 16 descartável e ferramenta Office real.

```sh
# Suite geral: sem DATABASE_URL.
python -m pytest tests/ -q

# Apenas DB local explícito, nunca um banco compartilhado.
DATABASE_URL="$LOCAL_TEST_DSN" PORTAL_DOCS_TEST_DSN="$LOCAL_TEST_DSN" \
  python -m pytest tests/test_portal_docs_postgres.py tests/test_portal_docs_security.py -q

python scripts/test_portal_docs_mutations.py --dsn "$LOCAL_TEST_DSN" --output /tmp/portal-docs-mutations
python scripts/check_library_runtime.py
node static/js/test/run-tests.js
cd flutter && dart run melos run lint && dart run melos run test
```

Cobertura: Geral e Registro positivos; oito demais perfis negativos; Bearer obrigatório e personificação recusada; escopo entre empresas/unidades, todas as unidades sem atravessar empresas, movimento temporário, setor/atividade, vigência futura, revogação, publicação/rascunho/substituição/arquivamento, idempotência/concorrência, originais vedados ao colaborador mesmo com política habilitada, originais autorizados aos dois administradores, auditoria imutável, migração idempotente/preservação/RLS, PDF/Office/imagens reais, extensão/MIME/base64/tamanho, macros renomeadas/DDE/ZIP ativo/zip bomb/PDF ativo/EXIF/transparência. Cliente Dart/Dio também foi executado contra os HTTPs PostgreSQL dos dois produtos.

Sete sabotagens em cópias privadas e bancos novos fazem a suite ficar vermelha: liberar Master; confiar na empresa do recurso em vez do contexto; remover unidade; permitir original ao colaborador; aceitar PDF ativo; remover migração 034 (upload em banco novo falha); repetir o conteúdo da primeira aba na exportação das demais. A implementação não é alterada pelo script. A remoção isolada do filtro de empresa ainda encontrou proteção da FK de auditoria; a sabotagem de IDOR reproduz confiança indevida no contexto para testar vazamento real, sem atribuir falso resultado a uma mudança apenas de status HTTP.

Arquivos fornecidos usados somente em empresas fictícias de laboratório: DOCX com cinco páginas; XLSX com abas POR/ENG, uma página por aba; XLS com uma aba e duas páginas. Inspeção visual desktop/celular, zoom, navegação, pesquisa e ação administrativa, com páginas recebidas do backend. Fixtures originais, credenciais e screenshots permanecem fora dos repositórios; não se tornaram conteúdo oficial de uma empresa.

## CI, paridade e decisão

Novo workflow `Portal Docs V1` roda HTTP/PostgreSQL/Office/RBAC/ataques e as sete sabotagens. Checks existentes de backend, Flutter, CodeQL, segurança, PostgreSQL e isolamento permanecem ativos. Manifesto Flutter atualizado nos dois lados; digests anteriores do portal atualizados após comprovar igualdade dos arquivos pareados. As identidades e os contratos de backend autorizados permanecem protegidos.

Resultados por HEAD, URLs de PRs/checks, screenshots e veredito final estão no relatório de execução entregue com os PRs. Revisor deve repetir o workflow adicional, examinar a qualidade dos arquivos reais localmente e conciliar o manifesto com as PRs de regularização quando elas forem aprovadas.

Próximo passo: **PORTAL-DOCS-V1-INDEPENDENT-VALIDATION**. Permanecem bloqueados merge, deploy e migrações compartilhadas. Compilação/uso em dispositivo físico Android/iOS não substituídos por screenshots do Flutter Web; revisão de produção e aprovação administrativa de documentos oficiais ainda necessárias.
