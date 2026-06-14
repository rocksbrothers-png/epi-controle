# Deployment — EPI SaaS

## Ambientes

| Ambiente | URL | Deploy | Branch |
|----------|-----|--------|--------|
| Produção | https://epi-controle.onrender.com | Automático (merge main) | `main` |
| Staging | N/A | Manual | `develop` |
| Local | http://localhost:8000 | Manual | qualquer |

## Stack de Produção

- **Hospedagem**: Render.com
- **Runtime**: Docker (multi-stage build)
- **Servidor**: Gunicorn + Python 3.11
- **Banco**: PostgreSQL (Supabase)
- **CDN/Assets**: Render serve arquivos estáticos via Python

## Dockerfile

Build multi-stage:

```dockerfile
# Stage 1: Flutter Web Build
FROM ghcr.io/cirruslabs/flutter:3.24.5 AS flutter-build
WORKDIR /app
COPY flutter/ .
RUN melos bootstrap && melos run build:web

# Stage 2: Python Runtime
FROM python:3.11-slim
# Instala Tesseract OCR
RUN apt-get update && apt-get install -y tesseract-ocr

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Copia Flutter Web buildado
COPY --from=flutter-build /app/apps/epi_admin/build/web ./flutter/apps/epi_admin/web

EXPOSE 8000
CMD ["gunicorn", "app:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

## render.yaml

```yaml
services:
  - type: web
    name: epi-controle
    runtime: docker
    buildCommand: ""
    startCommand: ""
    envVars:
      - key: DATABASE_URL
        sync: false        # definido manualmente no painel
      - key: JWT_SECRET
        sync: false
      - key: CORS_ALLOW_ORIGIN
        value: https://epi-controle.onrender.com
    healthCheckPath: /health
    autoDeploy: true
```

## Variáveis de Ambiente

### Obrigatórias em Produção

```bash
DATABASE_URL=postgresql://user:pass@host:5432/epi_db?sslmode=require
JWT_SECRET=<string aleatória ≥ 32 chars>
PASSWORD_RECOVERY_KEY=<string aleatória ≥ 32 chars>
CORS_ALLOW_ORIGIN=https://epi-controle.onrender.com
```

### Opcionais

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=SG.xxx
SMTP_FROM=noreply@epi-controle.com

AUTH_DIAGNOSTICS_KEY=<chave secreta para diagnóstico>
CSP_REPORT_URI=/api/csp-report
APP_ENV=production
```

## Roteamento

```
/              → static/index.html (SPA web legada)
/app/          → flutter/apps/epi_admin/web/index.html (Flutter Web)
/api/*         → Backend Python (REST API)
/auth/*        → Módulo de autenticação
/health        → Health check (200 OK)
/ready         → Readiness check (verifica DB)
/bootstrap     → Status do schema
/ux-phase*.js  → Servido como arquivo estático
/static/*      → Assets estáticos (CSS, imagens)
/fragments/*   → Fragmentos HTML para HTMX
```

## Deploy Local

```bash
# Backend
pip install -r requirements.txt
cp env.example .env
# editar .env com DATABASE_URL e JWT_SECRET
python app.py

# Flutter Web (desenvolvimento)
cd flutter
melos bootstrap
melos run build:web
# Flutter Web estará em flutter/apps/epi_admin/build/web/
# app.py serve automaticamente em /app/

# Flutter Mobile
cd flutter/apps/epi_admin
flutter run
```

## CI/CD — GitHub Actions

### Flutter CI (`.github/workflows/flutter.yml`)

```yaml
name: Flutter CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.24.5'
      - name: Install Melos
        run: dart pub global activate melos
      - name: Bootstrap
        run: melos bootstrap
      - name: Lint
        run: melos run lint
      - name: Test
        run: melos run test
      - name: Build Web
        run: melos run build:web
```

### Android Deploy (`.github/workflows/deploy-android.yml`)

```yaml
# Gera AAB e envia para Google Play (track: internal)
- name: Build Android AAB
  run: melos run build:android
- name: Upload to Play Store
  uses: r0adkll/upload-google-play@v1
```

### iOS Deploy (`.github/workflows/deploy-ios.yml`)

```yaml
# Gera IPA e envia para App Store Connect
- name: Build iOS IPA
  run: melos run build:ios
- name: Upload to TestFlight
  uses: apple-actions/upload-testflight-build@v1
```

## Health Checks

**`GET /health`**
```json
{ "status": "ok", "timestamp": "2026-06-14T12:00:00Z" }
```

**`GET /ready`**
```json
{
  "status": "ready",
  "database": "connected",
  "schema_version": 8
}
```

## Monitoramento

- Logs: `stdout` capturado pelo Render
- Erros de frontend: `error-monitor.js` com buffer em memória
- Rule engine: `rls_rule_engine_shadow_log` no banco
- Health check path configurado no Render para auto-restart

## Rollback

Em caso de regressão:
1. Reverter deploy no painel do Render (redeploy de commit anterior)
2. Ou: desativar feature flags via localStorage/query params
3. Kill switch global: `ux_global_kill_switch=1` desativa todos os módulos UX

## Runbooks

- `docs/RESET_TEST_DB_RUNBOOK.md` — Reset do banco de testes
- `docs/PHASE5_0_GO_LIVE_PROGRESSIVO.md` — Go-live progressivo
- `docs/DOCKER_RENDER_OCR.md` — Setup Docker + OCR
