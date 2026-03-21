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

> Se houver inconsistência de base, a API tenta revalidar e recriar esse usuário automaticamente no próximo login.

> Para recuperação de senha, configure a variável de ambiente `PASSWORD_RECOVERY_KEY` no servidor.

## Deploy (Render)
Para funcionamento online (login + bootstrap), configure no serviço web:
- `DATABASE_URL` (Postgres válido e acessível pelo Render).
- `JWT_SECRET` (obrigatório em produção; não usar o fallback padrão).
- `PASSWORD_RECOVERY_KEY` (obrigatório para fluxo de recuperação de senha).
- `JWT_EXP_SECONDS` (opcional, padrão: `28800`).

Checklist rápido pós-deploy:
1. `GET /health` deve retornar `200 {"status":"ok"}`.
2. `GET /api/auth-diagnostics` deve retornar `database_configured=true`, `db_connector_available=true` e `jwt_secret_default=false`.
3. Login no frontend deve retornar token JWT e liberar `GET /api/bootstrap`.

## Módulo do Master
O Administrador Master pode acessar a tela `Empresas` para:
- cadastrar e editar empresas
- configurar razão social, CNPJ e logo tipo
- definir plano/licença
- definir limite máximo de usuários
- ativar ou inativar empresas
- acompanhar uso atual por empresa
