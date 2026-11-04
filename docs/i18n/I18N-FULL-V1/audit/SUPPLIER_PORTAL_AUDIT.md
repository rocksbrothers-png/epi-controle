# Auditoria independente do bloco Fornecedor

Escopo: snapshot Corporate do working tree posterior a `3f32341d`, copiado em `audit/supplier-snapshot`; revisão de apresentação, extração do portal público, transporte e wrappers de erro. Nenhuma alteração de produto, banco ou contato com fornecedores. Sem aprovação integral do I18N-FULL-V1 ou paridade SaaS deste bloco ainda não commitado.

## Contratos e autorização

`supplier-contract-results.json` compara por AST o JS inline anterior com o módulo extraído. São exatamente iguais:

- Extração do token pelo pathname.
- Corpo da resposta de cotação, itens, IDs, preços e prazos; parseFloat/parseInt mantidos.
- Corpo da confirmação, códigos `confirmed`, `delivery_update` e `rejected`.
- Objeto de anexo: nome, MIME e Data URL de FileReader.
- Predicado que bloqueia edição de cotação já respondida.

Os arquivos quotes_service, supplier_portal_service, rotas de cotação e portal público, core/security e core/permissions estão idênticos à base. O adapter usa os mesmos endpoints com encodeURIComponent(token), sem introduzir identidade/empresa no cliente; acrescenta apenas Accept-Language à requisição. A autoridade continua no token e nas regras do backend. Isto é prova estrutural; não é tentativa real de bypass de token/RBAC.

## Provas independentes em Chromium

`supplier-browser-results.json`: dez casos (cotação e pedido × cinco idiomas), com shell e módulos reais e transporte HTTP local. Confirma:

- Troca de idioma mantém campos preenchidos e anexo PDF sintético; os dois envios de cada caso têm JSON exatamente igual.
- Preços 1234.56, frete 12.34 e prazo 5 permanecem numéricos; datas ISO, status canônico, IDs, nome/MIME/Data URL e textos originais preservados.
- Paths conservam `/api/portal/supplier/capability-synthetic/...`; ausência de Authorization de sessão e de company_id/actor_user_id/locale/lang nos corpos públicos.
- Erro específico por item, mesmo com código genérico, é traduzido e retraduzido após troca de idioma sem perder detalhe. Sucesso também é apresentado.
- EPI/empresa/textos contendo HTML e aspas não criam elementos img/b nem executam scripts. Zero erros de página.

`procurement-error-results.json`: cinco casos com as funções privadas extraídas por AST, engine e showToast reais. O wrapper mantém Bearer sintético, corpo, status 400, código, validation e payload. O mesmo detalhe aparece em feedback, markup e toast, e retraduz após troca de idioma. Zero imagens injetadas/erros de página. A retirada do bypass de localização foi confirmada neste caminho de Procurement.

## Revisão adicional

O patch de ui-helpers conserva os chamadores de strings e adiciona suporte à apresentação de Error.i18n. O Error mantém payload/código/status; a tradução altera apenas a mensagem exibida. clearBinding evita reapresentar uma mensagem anterior quando um erro sem template substitui o conteúdo. A montagem de opções mantém valores canônicos enquanto os rótulos têm bindings. A nova seleção de arquivo conserva o input real e permite mostrar nome original sem marcar esse nome como tradução.

Os 42 templates únicos/54 ocorrências informados pelo implementador são inventário dos dois serviços, não prova de todos os caminhos de erro de Compras. As provas acima exercitam mensagens específicas reais, sem afirmar execução integral desses 54 raises.

## Limitações

O probe não repetiu link inválido, cotação já respondida, mobile ou todos os papéis por HTTP; a evidência do implementador para esses casos não é apresentada como execução independente. A preservação do predicado de cotação respondida e das regras backend foi verificada por comparação estrutural. Nenhum envio real de proposta, confirmação, email ou operação de banco foi executado. Os hashes do snapshot estão no resultado do browser; alterações posteriores exigem revisão correspondente.
