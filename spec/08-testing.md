# Estratégia de Testes — EPI SaaS

## Visão Geral

| Camada | Framework | Localização | Quantidade |
|--------|-----------|-------------|-----------|
| Backend Python | pytest | `tests/` | 67 arquivos |
| Frontend JS (sintaxe) | pytest + py_compile | `tests/test_js_syntax.py` | 1 arquivo |
| Flutter (unitário) | flutter_test | `flutter/apps/epi_admin/test/` | Em desenvolvimento |
| Flutter (integração) | integration_test | `flutter/apps/epi_admin/integration_test/` | Em desenvolvimento |

## Testes Backend (pytest)

### Configuração

```bash
# Instalar dependências
pip install -r requirements.txt
pip install pytest pytest-cov

# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=. --cov-report=html

# Arquivo de configuração
tests/conftest.py
```

### Categorias de Teste

#### Autenticação e Usuários
| Arquivo | O que testa |
|---------|------------|
| `test_login_bootstrap_gate.py` | Login, bloqueio de bootstrap |
| `test_role_normalization.py` | Normalização de roles/aliases |
| `test_phase30_users_canary.py` | Canary deploy de usuários |

#### Funcionalidades Core
| Arquivo | O que testa |
|---------|------------|
| `test_epi_scope.py` | Regras de escopo de EPIs |
| `test_ficha_*.py` | Fichas de EPI (múltiplos arquivos) |
| `test_purchase_*.py` | Fluxo de compras |
| `test_devolutions_flow.py` | Fluxo de devoluções |

#### Rule Engine
| Arquivo | O que testa |
|---------|------------|
| `test_rule_engine.py` | Motor de regras unitário |
| `test_phase16_rule_engine_enforced.py` | Modo enforced |
| `test_phase20_rule_engine_go_live.py` | Go-live do rule engine |

#### Estabilidade / Canary
| Arquivo | O que testa |
|---------|------------|
| `test_phase29_bootstrap_canary.py` | Bootstrap canary |
| `test_phase31_jv_canary.py` | Joint venture canary |
| `test_phase32_production_validation.py` | Validação de produção |

#### OCR e Relatórios
| Arquivo | O que testa |
|---------|------------|
| `test_manufacture_date_ocr.py` | OCR de datas de fabricação |
| `test_reports_filters_validation.py` | Filtros de relatórios |

#### Infraestrutura
| Arquivo | O que testa |
|---------|------------|
| `test_sqlite_schema_hardening.py` | Schema hardening |
| `test_phase21_server_cleanup.py` | Limpeza de servidor |
| `test_bootstrap_resilience.py` | Resiliência do bootstrap |
| `test_static_assets.py` | Assets estáticos |
| `test_web_hardening_checks.py` | Verificações de segurança web |
| `test_js_syntax.py` | Sintaxe de todos os arquivos JS |

#### Integração
| Arquivo | O que testa |
|---------|------------|
| `test_epi_feedback_flow.py` | Fluxo de feedback de EPI |
| `test_commercial_contract_management.py` | Contratos comerciais |
| `test_low_stock_alert_scope.py` | Escopo de alertas de estoque |

### Padrão de Teste Backend

```python
import pytest
from app import EpiHandler

@pytest.fixture
def client():
    """Setup de cliente de teste."""
    # ...configuração do cliente HTTP de teste

def test_lista_epis_como_admin(client, auth_token_admin):
    """Verifica que admin vê EPIs da sua empresa."""
    response = client.get('/api/epis', headers={'Authorization': f'Bearer {auth_token_admin}'})
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
    assert isinstance(data['data'], list)

def test_employee_nao_acessa_epis(client, auth_token_employee):
    """Employee não tem permissão de listar EPIs."""
    response = client.get('/api/epis', headers={'Authorization': f'Bearer {auth_token_employee}'})
    assert response.status_code == 403
```

## Testes Flutter

### Configuração

```bash
# Unitários
cd flutter/apps/epi_admin
flutter test

# Via melos (todos os pacotes)
cd flutter
melos run test

# Cobertura
flutter test --coverage
```

### Estrutura de Testes Flutter (Planejada)

```
flutter/apps/epi_admin/
├── test/
│   ├── unit/
│   │   ├── bloc/
│   │   │   ├── auth_bloc_test.dart
│   │   │   ├── stock_bloc_test.dart
│   │   │   └── delivery_bloc_test.dart
│   │   ├── repositories/
│   │   │   ├── epi_repository_test.dart
│   │   │   └── stock_repository_test.dart
│   │   └── utils/
│   │       └── permissions_test.dart
│   └── widget/
│       ├── dashboard_test.dart
│       ├── epi_list_test.dart
│       └── delivery_form_test.dart
└── integration_test/
    ├── login_flow_test.dart
    ├── delivery_flow_test.dart
    └── stock_management_test.dart
```

### Padrão de Teste de BLoC

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';

void main() {
  group('AuthBloc', () {
    late AuthBloc authBloc;
    late MockAuthRepository mockRepo;

    setUp(() {
      mockRepo = MockAuthRepository();
      authBloc = AuthBloc(repository: mockRepo);
    });

    blocTest<AuthBloc, AuthState>(
      'emite [Loading, Authenticated] ao fazer login com sucesso',
      build: () => authBloc,
      act: (bloc) => bloc.add(LoginRequested(email: 'a@b.com', password: '123')),
      expect: () => [AuthLoading(), AuthAuthenticated(user: mockUser)],
    );
  });
}
```

## Testes JS (Harness Node — Implementado)

Harness de testes unitários **sem dependências** (usa `node` + `vm`), em
`static/js/test/run-tests.js`. Cria mocks mínimos de browser (`window`,
`localStorage`, `location`, `document`), carrega os módulos de `static/js/` na
ordem de dependência e roda asserções.

```bash
# Rodar diretamente
node static/js/test/run-tests.js

# Via pytest (roda no CI; pula se Node ausente)
pytest tests/test_js_unit.py

# Linting (após instalar eslint)
npx eslint static/js/
```

O wrapper `tests/test_js_unit.py` executa o harness dentro de `pytest tests/`
(usado no CI) e pula automaticamente se o Node não estiver disponível.

### Casos de Teste JS Cobertos (15 testes)

1. **Permissões**: `hasPermission(role, 'epis:view')` true/false por role e alias
2. **Rotas**: `canViewRoute('dashboard', role)` respeita VIEW_PERMISSIONS
3. **Feature flags**: `getFeatureFlag` lê localStorage; query param tem prioridade
4. **Storage**: `safeStorageWrite/Read` round-trip; `safeJsonParse` com fallback
5. **Normalização de role**: `normalizeRole('masteradmin')` → `'master_admin'`
6. **Constantes**: `STORAGE_KEYS`, `ROLE_ALIASES`, `ROLE_PERMISSIONS`, `VIEW_PERMISSIONS`
7. **Guards**: `ensureModuleBound` bloqueia duplo-carregamento

### Próximos passos do harness

Conforme `app.js` for decomposto (auth, api-client), adicionar casos para
cada módulo extraído — pré-requisito de segurança antes de remover o código
correspondente do `app.js`.

## CI/CD — Testes Automatizados

### GitHub Actions

**`.github/workflows/flutter.yml`:**
```yaml
- name: Flutter Analyze
  run: melos run lint
- name: Flutter Test
  run: melos run test
```

**`.github/workflows/node.js.yml`:**
```yaml
- name: Lint JS
  run: npx eslint static/js/    # após refatoração
- name: Test JS
  run: npx jest static/js/      # após refatoração
```

### Pipeline Backend (a ser criado)

```yaml
- name: Python Tests
  run: pytest tests/ -v --tb=short
- name: Coverage Check
  run: pytest tests/ --cov=. --cov-fail-under=70
```

## Qualidade de Código

### QA_CHECKLIST.md

O arquivo `QA_CHECKLIST.md` na raiz define 7 seções de validação manual:
1. Autenticação e sessão
2. Navegação e rotas
3. CRUD de entidades
4. Entregas e fichas
5. Alertas e relatórios
6. Compras
7. Responsividade e acessibilidade

### Scripts de Auditoria

```bash
python scripts/check_web_hardening.py    # Verifica CSP, SRI, headers
python scripts/check_ocr_runtime.py     # Verifica disponibilidade do Tesseract
python scripts/audit_qr_integrity.py   # Audita integridade dos QR codes
```
