# static/views — Fragmentos modulares do index.html

Esta pasta contém o `index.html` decomposto em fragmentos editáveis por view.
O `static/index.html` servido em produção é **gerado** a partir destes arquivos.

## Arquivos

- `_layout.html` — esqueleto: apenas marcadores `<!-- EPI_SHELL_INCLUDE:<name> -->`
  (casca) e `<!-- EPI_VIEW_INCLUDE:<id> -->` (views).
- `_head.html`, `_login.html`, `_sidebar.html`, `_topbar.html`, `_modals.html`,
  `_scripts.html` — sub-fragmentos da casca (head, login, navegação, topbar,
  modais globais, bloco de scripts).
- `<view>.html` — uma seção `<section id="<view>-view" class="view">` por arquivo.
- `modals/<id>.html` — modais extraídos de views grandes (compras, avaliacoes),
  referenciados por `<!-- EPI_MODAL_INCLUDE:<id> -->` dentro da view.

## Como editar

1. Edite o fragmento desejado (ex.: `epis.html`) ou o `_layout.html`.
2. Reconstrua o index.html:
   ```bash
   python scripts/build_index.py build
   ```
3. Commite o fragmento **e** o `static/index.html` gerado juntos.

## Verificação

O CI roda `python scripts/build_index.py check` (via
`tests/test_index_html_build.py`). Se o `index.html` estiver fora de sincronia
com os fragmentos, o teste falha.

## Importante

- **Não** edite o `static/index.html` diretamente — suas mudanças seriam
  sobrescritas no próximo `build` e o teste de drift acusaria divergência.
- A reconstrução é byte-idêntica por construção (fatiamento/rejunção do texto).

Ver `spec/11-index-html-refactoring-plan.md` para detalhes e roadmap.
