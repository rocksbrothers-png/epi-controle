# Arquitetura oficial de URLs: website institucional + Flutter Web

## 1. Decisão oficial

A estrutura oficial recomendada é:

- `/` — website institucional/marketing, otimizado para SEO, velocidade, conteúdo público e conversão.
- `/app/` — aplicativo autenticado Flutter Web, com roteamento interno de SPA.
- `/flutter_web/` — caminho legado temporário, mantido por redirecionamento para `/app/` durante a transição.

Recomendação: usar `/app/`, não `/painel/`, como URL oficial do Flutter Web.

## 2. Justificativa técnica

### SEO

- A raiz `/` permanece dedicada ao conteúdo institucional indexável: landing pages, páginas comerciais, conteúdo de produto, política de privacidade e material de suporte.
- O aplicativo Flutter Web é uma SPA autenticada e não deve competir com páginas institucionais por indexação.
- `/app/` é curto, neutro, internacionalizável e mais adequado caso o produto ganhe outros idiomas; `/painel/` é mais descritivo em português, mas menos escalável para usuários internacionais.

### Performance

- A raiz pode ser servida como HTML/CSS/JS leve, com cache, imagens otimizadas e menor JavaScript inicial.
- O bundle Flutter Web fica isolado em `/app/`, evitando que usuários públicos baixem assets pesados do aplicativo antes do login.
- Separar website e app facilita políticas de cache diferentes: páginas institucionais podem ter cache agressivo; `index.html` do app deve ter revalidação curta para evitar versões inconsistentes.

### UX

- `/app/` é uma chamada de ação clara: `Entrar no app`, `Acessar app`.
- Links compartilhados do produto ficam previsíveis: `/app/dashboard`, `/app/settings`, `/app/employees/123`.
- O caminho legado `/flutter_web/` continua funcional via redirecionamento para não quebrar favoritos, links antigos ou rotas já distribuídas.

### Organização de URLs

- `/` e páginas públicas: website institucional.
- `/app/`: aplicação autenticada.
- `/api/`: backend/API.
- `/assets/`, `/images/`, `/fonts/`: assets do website legado/institucional.
- `/flutter_web/`: legado compatível, redirecionando para `/app/`.

## 3. Plano de transição sem quebrar `/flutter_web/`

1. Buildar o Flutter Web com `base-href /app/`.
2. Publicar o build em `static/app/`.
3. Servir `/app/` e qualquer deep link `/app/*` com fallback para `/app/index.html` quando o arquivo físico não existir.
4. Redirecionar `/flutter_web` e `/flutter_web/*` para `/app/` e `/app/*`, preservando a query string.
5. Manter o redirecionamento por pelo menos 2 ciclos de release ou 90 dias, o que for maior.
6. Atualizar links internos, documentação, monitoramento e materiais de suporte para apontarem para `/app/`.
7. Depois da janela de transição, manter o redirecionamento se o custo operacional for baixo; ele é seguro e evita links quebrados de longo prazo.

## 4. Regras de redirecionamento e fallback

### Nginx

```nginx
# Website institucional na raiz.
location / {
    try_files $uri $uri/ /index.html;
}

# Compatibilidade: Flutter Web legado -> URL oficial.
location = /flutter_web {
    return 308 /app/;
}

location ^~ /flutter_web/ {
    rewrite ^/flutter_web/(.*)$ /app/$1 permanent;
}

# Flutter Web oficial em /app/.
location ^~ /app/ {
    try_files $uri $uri/ /app/index.html;
}

# API continua separada.
location ^~ /api/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

### Firebase Hosting

```json
{
  "hosting": {
    "public": "static",
    "redirects": [
      { "source": "/flutter_web", "destination": "/app/", "type": 308 },
      { "source": "/flutter_web/**", "destination": "/app/:splat", "type": 308 }
    ],
    "rewrites": [
      { "source": "/app/**", "destination": "/app/index.html" },
      { "source": "/api/**", "function": "api" },
      { "source": "**", "destination": "/index.html" }
    ],
    "headers": [
      {
        "source": "/app/index.html",
        "headers": [{ "key": "Cache-Control", "value": "no-store, max-age=0" }]
      },
      {
        "source": "/app/**",
        "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
      }
    ]
  }
}
```

### Cloudflare Pages

Arquivo `_redirects`:

```text
/flutter_web    /app/      308
/flutter_web/*  /app/:splat 308
/app/*          /app/index.html 200
/*              /index.html 200
```

Se houver Functions/Workers para `/api/*`, coloque a regra da API antes do fallback global e evite que `/api/*` caia em `/index.html`.

### Render/static hosting ou Render com backend Python

Para Render servindo pelo backend Python deste repositório:

- Build Flutter com `--base-href /app/`.
- Copie o build para `static/app/`.
- Redirecione `/flutter_web/*` para `/app/*`.
- Faça fallback de `/app/*` para `/app/index.html` quando o arquivo físico não existir.
- Preserve `/` como website institucional (`static/index.html`).

No backend Python atual, essas regras estão implementadas em `EpiHandler`:

- `_legacy_flutter_web_redirect()` mantém compatibilidade com `/flutter_web/*`.
- `_resolve_static_fallback_path()` mantém `/` no website e aplica fallback interno para `/app/*`.

## 5. Checklist de validação pós-deploy

- `GET /` retorna o website institucional.
- `GET /app/` retorna o `index.html` do Flutter Web.
- `GET /app/dashboard` retorna o `index.html` do Flutter Web, não 404.
- `GET /app/flutter_bootstrap.js` retorna o arquivo físico do build, não o fallback HTML.
- `GET /flutter_web/` retorna redirecionamento para `/app/`.
- `GET /flutter_web/dashboard?tab=epis` retorna redirecionamento para `/app/dashboard?tab=epis`.
- `GET /api/auth-diagnostics` continua passando pela rota de API e não pelo fallback estático.
- `GET /health` e `GET /ready` seguem retornando diagnósticos de runtime.
- Verificar no navegador que o Flutter Web carrega assets relativos a `/app/`.
- Verificar que a raiz não baixa assets Flutter no primeiro carregamento público.
- Verificar headers de cache: `index.html` do app sem cache agressivo; assets versionados/hash com cache longo.

## 6. Riscos e rollback

### Riscos

- Build Flutter com `base-href` incorreto pode fazer o app buscar assets em `/flutter_web/` ou `/`.
- Regras de rewrite muito amplas podem capturar `/api/*` e devolver HTML em vez de JSON.
- Cache de CDN/navegador pode manter `index.html` antigo apontando para assets antigos.
- Redirecionamento permanente `308` pode ser cacheado por clientes; durante rollout inicial, se houver baixa confiança operacional, use `302` por uma release e promova para `308` depois.

### Rollback

1. Reverter o build para `--base-href /flutter_web/`.
2. Publicar novamente em `static/flutter_web/`.
3. Remover ou inverter o redirecionamento `/flutter_web/* -> /app/*`.
4. Manter `/` inalterado para preservar o website institucional.
5. Limpar cache de CDN para `index.html`, regras de redirect e assets Flutter.
6. Validar `/flutter_web/`, `/flutter_web/dashboard`, `/health` e `/ready`.

## 7. Estrutura final recomendada de pastas

```text
static/
  index.html                 # website institucional/marketing na raiz
  styles.css                 # estilos do website institucional
  app.js                     # JS legado/institucional enquanto existir
  assets/                    # assets públicos do website
  images/                    # imagens públicas/SEO
  fonts/                     # fontes locais
  app/                       # build Flutter Web oficial
    index.html
    flutter_bootstrap.js
    main.dart.js
    manifest.json
    assets/
  legacy/                    # opcional: legado autenticado congelado se migrado no futuro

docs/
  WEB_APP_URL_ARCHITECTURE.md

flutter/
  apps/epi_admin/            # código-fonte Flutter
```

## Decisão final

Use `/app/` como URL oficial do Flutter Web. Mantenha `/` como website principal/institucional e preserve `/flutter_web/` apenas como caminho legado redirecionado para `/app/`.
