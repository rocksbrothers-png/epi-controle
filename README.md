# epi-controle
Sistema de controle de EPI

## Perfis padrão
- Administrador Master: `admin / admin123`
- Administrador Geral DOF Brasil: `dof.general / dofgeneral123`
- Administrador DOF Brasil: `dof.admin / dofadmin123`
- Usuário DOF Brasil: `dof.user / dof123`
- Administrador Geral Norskan: `norskan.general / norskangeneral123`
- Administrador Norskan: `norskan.admin / norskanadmin123`
- Usuário Norskan: `norskan.user / norskan123`

> Ao iniciar o backend, o usuário `admin` é garantido como `master_admin` ativo com senha `admin123` para evitar bloqueio de acesso em ambiente novo/deploy.
> Se o login `admin / admin123` falhar por inconsistência de base, a API tenta revalidar e recriar esse usuário automaticamente no próximo login com essas credenciais.

## Módulo do Master
O Administrador Master pode acessar a tela `Empresas` para:
- cadastrar e editar empresas
- configurar razão social, CNPJ e logo tipo
- definir plano/licença
- definir limite máximo de usuários
- ativar ou inativar empresas
- acompanhar uso atual por empresa

## Verificação rápida de deploy (GitHub + Render)
Entre no diretório do projeto antes de rodar os comandos:

```bash
cd /workspace/epi-controle
```

Execute:

```bash
./scripts/check_deploy_status.sh
```

O script valida se:
- o `origin` do GitHub está configurado;
- existe `render.yaml` no projeto;
- há alterações locais sem commit.

## Como verificar se as atualizações foram para o GitHub
1. Veja se o repositório remoto está configurado:
   ```bash
   git remote -v
   ```
2. Confirme sua branch e se há commits locais pendentes:
   ```bash
   git status --short --branch
   git log --oneline -n 5
   ```
3. Envie a branch para o GitHub:
   ```bash
   git push -u origin <sua-branch>
   ```
4. Valide se o commit está no remoto:
   ```bash
   git fetch origin
   git log --oneline origin/<sua-branch> -n 5
   ```
5. No GitHub, abra a aba **Commits** da branch e confirme o hash mais recente.

## Windows (Prompt de Comando) — caminho completo para testar
No Windows, o caminho `/workspace/epi-controle` **não existe** (esse caminho é do ambiente Linux do servidor/agente).

1. Instale o Git for Windows (inclui o comando `git`):  
   https://git-scm.com/download/win
2. Abra o **Git Bash** (recomendado) ou Prompt de Comando.
3. Entre na pasta local onde seu projeto foi clonado. Exemplo:
   ```bat
   cd /d C:\Users\SEU_USUARIO\Documents\epi-controle
   ```
4. Rode os comandos de verificação:
   ```bat
   git remote -v
   git status --short --branch
   git log --oneline -n 5
   ```
5. Envie as atualizações para o GitHub:
   ```bat
   git push -u origin NOME_DA_SUA_BRANCH
   ```
6. Confirme se chegou no remoto:
   ```bat
   git fetch origin
   git log --oneline origin/NOME_DA_SUA_BRANCH -n 5
   ```
7. Abra o GitHub no navegador e confira a aba **Commits** da branch.

## Sem instalar Git/GitHub Desktop (alternativa via navegador)
Se você não quer instalar nada agora, dá para atualizar pelo próprio site do GitHub:

1. Abra o repositório no GitHub.
2. Entre no arquivo que deseja alterar e clique em **Edit** (ícone de lápis).
3. Faça a alteração e clique em **Commit changes**.
4. Para novo arquivo, use **Add file** > **Create new file** ou **Upload files**.
5. Abra a aba **Commits** para confirmar que o commit entrou.

> Limitação: sem Git local você não roda comandos como `git status`, `git log` e `git fetch`.
