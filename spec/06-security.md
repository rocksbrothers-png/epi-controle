# Segurança — EPI SaaS

## Camadas de Segurança

```
1. Rede:        HTTPS/TLS obrigatório em produção
2. Aplicação:   JWT + RBAC, rate limiting, CORS
3. Banco:       RLS (Row-Level Security), usuário sem acesso direto
4. Frontend:    CSP, SRI, XSS sanitization
5. Infraestrutura: Variáveis de ambiente, sem secrets em código
```

## Autenticação

- **JWT** com `HS256`, expiração de 8 horas
- **bcrypt** para hashing de senhas (fator de custo padrão ≥ 12)
- **Variável obrigatória**: `JWT_SECRET` deve ser definida em produção (≥ 32 chars)
- Tokens não são reutilizáveis após logout (invalidação por sessão)

## Autorização

- Verificação de permissão em **todo** endpoint protegido
- Middleware `decode_jwt_token()` valida assinatura, expiração e `company_id`
- RLS no PostgreSQL: linha de defesa adicional independente do backend
- Frontend nega acesso visual a views sem permissão (defense-in-depth)

## Content Security Policy (CSP)

Definida no `index.html`:
```
default-src 'self';
script-src 'self' 'nonce-{NONCE}';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
connect-src 'self' https://api.example.com;
frame-ancestors 'none';
report-uri /api/csp-report
```

- `frame-ancestors 'none'` → protege contra Clickjacking
- `report-uri` → monitora violações de CSP

## Subresource Integrity (SRI)

Assets externos carregados com atributo `integrity`:
```html
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

## CORS

Configuração via variável `CORS_ALLOW_ORIGIN`:
- Em produção: domínios específicos da plataforma
- Em desenvolvimento: `http://localhost:*` permitido
- `credentials: true` necessário para cookies de sessão

## Rate Limiting

Implementado em `core/rate_limit.py`:

| Endpoint | Limite |
|----------|--------|
| `/api/auth/login` | 10 req/min por IP |
| `/api/auth/password-recovery` | 5 req/min por IP |
| Endpoints gerais | 100 req/min por IP |
| Endpoints de export | 10 req/min por usuário |

Headers retornados:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## Proteção contra Ataques Comuns

### SQL Injection
- Uso exclusivo de queries parametrizadas via `psycopg2`
- Nenhuma concatenação de strings em SQL
- `core/database.py` abstrai toda execução de queries

### XSS (Cross-Site Scripting)
- Frontend: `textContent` em vez de `innerHTML` por padrão
- `innerHTML` apenas via `data-i18n-html` com conteúdo controlado
- CSP com nonce mitiga XSS residual

### CSRF
- API stateless com JWT (não usa cookies de sessão)
- SameSite header em cookies auxiliares

### Clickjacking
- `X-Frame-Options: DENY`
- CSP `frame-ancestors 'none'`

### Path Traversal
- Validação de paths em `app.py` para servir arquivos estáticos
- `SimpleHTTPRequestHandler` sanitiza paths automaticamente

## Variáveis de Ambiente Sensíveis

| Variável | Obrigatória em Prod | Descrição |
|----------|--------------------|-----------| 
| `DATABASE_URL` | Sim | Connection string PostgreSQL |
| `JWT_SECRET` | Sim | Chave de assinatura JWT (≥ 32 chars) |
| `PASSWORD_RECOVERY_KEY` | Sim | Chave para tokens de recovery |
| `SMTP_HOST` | Recomendado | SMTP para envio de emails |
| `SMTP_USER` | Recomendado | Usuário SMTP |
| `SMTP_PASS` | Recomendado | Senha SMTP |
| `CORS_ALLOW_ORIGIN` | Sim | Domínios permitidos |
| `AUTH_DIAGNOSTICS_KEY` | Opcional | Chave para diagnóstico de auth |
| `CSP_REPORT_URI` | Opcional | Endpoint de relatório CSP |

**Nunca commitar** valores de produção. Usar `.env` local (listado em `.gitignore`).

## Auditoria e Logging

- Todas as decisões do Rule Engine são logadas em `rls_rule_engine_shadow_log`
- Logins bem-sucedidos atualizam `last_login_at`
- Falhas de autenticação são logadas (sem dados sensíveis)
- `error-monitor.js` captura erros de frontend em modo de diagnóstico

## Hardening do Banco de Dados

- Usuário de aplicação sem `SUPERUSER`
- RLS habilitado em todas as tabelas de negócio
- Conexões via SSL obrigatório (`sslmode=require`)
- Connection pooling com limite por processo

## Checklist de Segurança para Deploy

- [ ] `JWT_SECRET` definido (≥ 32 chars aleatórios)
- [ ] `DATABASE_URL` aponta para instância de produção
- [ ] CORS configurado com domínios reais
- [ ] HTTPS habilitado (TLS 1.2+)
- [ ] CSP configurada no `index.html`
- [ ] Variáveis sensíveis em variáveis de ambiente (não em código)
- [ ] RLS habilitado no Supabase
- [ ] Backups automatizados configurados no PostgreSQL
- [ ] Rate limiting ativo
- [ ] Logs de erro capturados (sem dados sensíveis)
