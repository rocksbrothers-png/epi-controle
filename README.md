# Controle de EPI v4

Estrutura atual com hierarquia de usuários.

## Perfis

- `Administrador Geral`: pode criar/remover administradores e usuários
- `Administrador`: pode criar/remover usuários
- `Usuário`: opera entrega e ficha

## Empresas

- `DOF Brasil`
- `Norskan Offshore`

## Logins iniciais

- Administrador Geral: `admin` / `admin123`
- Administrador DOF: `dof.admin` / `dofadmin123`
- Usuário DOF: `dof.user` / `dof123`
- Administrador Norskan: `norskan.admin` / `norskanadmin123`
- Usuário Norskan: `norskan.user` / `norskan123`

## Regras de gestão

- O Administrador Geral pode adicionar ou retirar administradores e usuários.
- O Administrador pode adicionar ou retirar apenas usuários da própria empresa.
- Usuário comum não acessa a gestão de usuários.

## Como iniciar

1. Execute `python server.py`
2. Abra `http://127.0.0.1:8000`


## Bootstrap inicial

- Na primeira execu??o, se n?o existir nenhum `Administrador Geral` ativo, o sistema cria automaticamente o usu?rio inicial `admin / admin123`.
- Esse bootstrap acontece apenas uma vez e fica registrado internamente para n?o recriar o usu?rio em toda inicializa??o.
- Quando isso ocorrer, o servidor mostra no terminal o login e a senha inicial criados.
