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

> Ao iniciar o backend, o usuário `admin` é garantido como `master_admin` ativo.

---

## Variáveis de ambiente

Crie um arquivo `.env` baseado no `.env.example`:
DATABASE_URL=postgresql://postgres.seu_ref:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
JWT_SECRET=
SUPABASE_URL=
SUPABASE_ANON_KEY=
ENVIRONMENT=production
PORT=8000


---

## Como rodar localmente

1. Instalar dependências
2. Configurar `.env`
3. Executar servidor

---

## Deploy (Render)

1. Configurar variáveis de ambiente no Render
2. Fazer deploy automático via GitHub
3. Garantir DATABASE_URL e JWT_SECRET

---

## Módulo do Master

O Administrador Master pode:
- cadastrar empresas
- definir plano/licença
- controlar usuários
- ativar/inativar empresas
