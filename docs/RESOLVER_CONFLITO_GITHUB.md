# Como resolver conflito no GitHub (PR com "Merge conflicts")

> Cenário: PR da branch de feature para `main` com conflito.

## 1) Atualizar sua branch com a `main`
No seu computador (com Git instalado):

```bash
git checkout codex/check-github-updates-to-render-jhp221
git fetch origin
git merge origin/main
```

Se aparecer conflito, o Git vai listar os arquivos.

## 2) Resolver arquivos em conflito
Abra cada arquivo conflitante e procure blocos assim:

```text
(seu código)
```

Mantenha o conteúdo correto (ou combine os dois), removendo os marcadores.

## 3) Marcar como resolvido e concluir merge

```bash
git add README.md server_postgres.py static/app.js static/index.html
# adicione também outros arquivos que aparecerem no seu conflito

git commit -m "resolve merge conflict with main"
```

## 4) Enviar branch atualizada

```bash
git push origin codex/check-github-updates-to-render-jhp221
```

Depois disso, o PR normalmente sai de "Merge conflicts" e o botão de merge volta.

## 5) Se preferir (via GitHub Web)
No PR, clique em **Resolve conflicts**, ajuste os arquivos, marque como resolvido e faça commit.

---

## Dica para este projeto
Se o conflito for em textos/documentação, mantenha os trechos novos de ambos os lados (principalmente no `README.md`).
Se for em `server_postgres.py`, preserve:
- normalização de login com `strip()`;
- auto-recuperação do `admin/admin123` quando necessário.
