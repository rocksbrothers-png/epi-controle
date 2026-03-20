# epi-controle
Sistema de controle de EPI

## Perfis padrão
- Administrador Master: `admin`
- Administrador Geral DOF Brasil: `dof.general`
- Administrador DOF Brasil: `dof.admin`
- Usuário DOF Brasil: `dof.user`
- Administrador Geral Norskan: `norskan.general`
- Administrador Norskan: `norskan.admin`
- Usuário Norskan: `norskan.user`

> Ao iniciar o backend, o usuário `admin` é garantido como `master_admin` ativo para evitar bloqueio de acesso em ambiente novo/deploy.
> Se houver inconsistência de base, a API tenta revalidar e recriar o usuário administrativo inicial no próximo login.
> Para recuperação de senha pela tela de login, configure a variável de ambiente `PASSWORD_RECOVERY_KEY` no servidor.
< codex/check-github-updates-to-render-f75ndr

> Ao iniciar o backend, o usuário `admin` é garantido como `master_admin` ativo com senha `admin123` para evitar bloqueio de acesso em ambiente novo/deploy.
< codex/check-github-updates-to-render-jhp221
> Se o login `admin / admin123` falhar por inconsistência de base, a API tenta revalidar e recriar esse usuário automaticamente no próximo login com essas credenciais.

## Módulo do Master
O Administrador Master pode acessar a tela `Empresas` para:
- cadastrar e editar empresas
- configurar razão social, CNPJ e logo tipo
- definir plano/licença
- definir limite máximo de usuários
- ativar ou inativar empresas
- acompanhar uso atual por empresa





