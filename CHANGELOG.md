# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento adota [SemVer](https://semver.org/lang/pt-BR/).
Os commits seguem [Conventional Commits](https://www.conventionalcommits.org/pt-br/):
`feat` (minor), `fix` (patch), `BREAKING CHANGE` (major), além de
`chore`/`docs`/`refactor`/`test`/`ci`.

## [Unreleased]

### Added
- Infraestrutura de CI/CD fundacional: Dependabot, CodeQL (Python + JavaScript),
  workflow de Segurança (Dependency Review, Secret Scan via gitleaks, pip-audit).
- `backend-ci.yml`: pytest com cobertura, lint com ruff e validação PostgreSQL 16
  + invariantes Multi-Tenant (RLS / tenant_id) — substitui o antigo Python CI.
- `contract-tests.yml`: testes de contrato de API (envelope, enums, escopo).
- Governança: `CODEOWNERS`, template de Pull Request, templates de Issue
  (bug/feature), agrupamento automático de Release Notes.
- Documentação da infra de CI/CD em `docs/ci-cd/README.md`.

### Changed
- Removido `node.js.yml` (Python CI) em favor de `backend-ci.yml`.
