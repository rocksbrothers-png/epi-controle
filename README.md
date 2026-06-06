# epi-controle
Sistema de controle de EPI.

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
- `APP_ENV=production` ou `ENVIRONMENT=production`.
- `JWT_SECRET` (obrigatório em produção; não usar fallback).
- `PASSWORD_RECOVERY_KEY` (obrigatório para fluxo de recuperação de senha).
- `JWT_EXP_SECONDS` (opcional, padrão: `28800`).
- `CORS_ALLOW_ORIGIN` com as origens HTTPS permitidas, separadas por vírgula.
- `AUTH_DIAGNOSTICS_KEY` para liberar diagnóstico completo via header `X-Diagnostics-Key` quando necessário.

Checklist rápido pós-deploy:
1. `GET /health` deve retornar `200 {"status":"ok"}`.
2. `GET /ready` ou `GET /health/ready` deve retornar `200` após bootstrap do banco.
3. `GET /api/auth-diagnostics` deve retornar diagnóstico público sem expor host do banco em produção sem autenticação/chave.
4. `GET /api/auth-diagnostics` com `X-Diagnostics-Key` válido deve retornar `database_configured=true`, `db_connector_available=true` e `jwt_secret_default=false`.
5. Login no frontend deve retornar token JWT e liberar `GET /api/bootstrap`.
6. `GET /app/alguma-rota-interna` deve servir o SPA Flutter Web quando o arquivo físico não existir.
7. `GET /flutter_web/alguma-rota-interna` deve redirecionar para `/app/alguma-rota-interna` durante a janela de compatibilidade.

## Módulo do Master
O Administrador Master pode acessar a tela `Empresas` para:
- cadastrar e editar empresas;
- configurar razão social, CNPJ e logo tipo;
- definir plano/licença;
- definir limite máximo de usuários;
- ativar ou inativar empresas;
- acompanhar uso atual por empresa.


## Arquitetura Web
- A raiz `/` é o website institucional/marketing.
- O Flutter Web oficial fica em `/app/`; `/flutter_web/` é legado e deve redirecionar para `/app/`.
- Consulte `docs/WEB_APP_URL_ARCHITECTURE.md` para regras de Nginx, Firebase Hosting, Cloudflare Pages, Render/static hosting, checklist, riscos e rollback.

## Hardening Web
- O website legado ainda usa dependências externas pinadas por versão e protegidas por SRI no `index.html`; não substitua bibliotecas por shims parciais sem validação funcional completa.
- O servidor emite `Content-Security-Policy-Report-Only` enquanto o legado ainda contém scripts/estilos inline; a política pode evoluir para CSP bloqueante quando o legado for modularizado.
- Execute `python scripts/check_web_hardening.py` antes do deploy para validar README, CDNs versionadas com SRI, fallback Flutter Web e headers de segurança.
- Opcionalmente configure `CSP_REPORT_URI=/api/csp-report` para registrar violações da política em modo report-only durante o rollout; em produção, endpoints absolutos devem usar HTTPS.
