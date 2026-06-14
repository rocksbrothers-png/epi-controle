# Internacionalização (i18n) — EPI SaaS

## Idiomas Suportados

| Código | Idioma | Status |
|--------|--------|--------|
| `pt-BR` | Português (Brasil) | Principal / Fallback |
| `en-GB` | Inglês (Reino Unido) | Completo |
| `es-ES` | Espanhol (Espanha) | Completo |
| `fr-FR` | Francês (França) | Completo |
| `nb-NO` | Norueguês Bokmål | Completo |

## Implementação Web (JS)

### Motor i18n (`static/i18n.js`)

```javascript
// API pública
window.t(key, vars)                     // traduz chave com interpolação
window.EpiI18n.setLang(locale)          // troca idioma e re-traduz DOM
window.EpiI18n.translateDOM(root)       // aplica traduções a subárvore
window.EpiI18n.lang                     // idioma ativo
window.EpiI18n.ready                    // Promise resolvida após carregar
```

### Resolução de Chaves

Ordem de fallback:
1. Idioma ativo (ex: `fr-FR`)
2. Português `pt-BR` (fallback global)
3. A própria chave (último recurso)

Chaves aninhadas via `.`:
```javascript
t('dashboard.title')          // → "Visão Geral"
t('alerts.low_stock.message') // → "Estoque baixo para {epi}"
```

### Interpolação

```javascript
t('greeting', { name: 'Ana' })  // "Olá, {name}" → "Olá, Ana"
t('stock.quantity', { qty: 5 }) // "Quantidade: {qty}" → "Quantidade: 5"
```

### Atributos HTML de Tradução

```html
<span data-i18n="dashboard.title"></span>
<p data-i18n-html="alerts.description"></p>
<input data-i18n-placeholder="search.placeholder">
<button data-i18n-title="actions.save"></button>
<button data-i18n-aria-label="actions.close"></button>
<input data-i18n-value="filter.all">
```

### Armazenamento de Preferência

Chave localStorage: `epi_language`

Ordem de prioridade:
1. Parâmetro de URL: `?lang=en-GB`
2. `localStorage.epi_language`
3. `navigator.language` (idioma do navegador)
4. `pt-BR` (padrão)

### Arquivos de Tradução

```
static/i18n/
  pt-BR.json   ← arquivo principal / fallback
  en-GB.json
  es-ES.json
  fr-FR.json
  nb-NO.json
```

Formato JSON:
```json
{
  "dashboard": {
    "title": "Visão Geral",
    "kpis": {
      "employees": "Colaboradores",
      "deliveries": "Entregas"
    }
  },
  "actions": {
    "save": "Salvar",
    "cancel": "Cancelar",
    "delete": "Excluir"
  }
}
```

## Implementação Flutter

### Pacote `epi_i18n`

Localização: `flutter/packages/epi_i18n/lib/l10n/`

Arquivos ARB (Application Resource Bundle):
```
app_pt_BR.arb
app_en_US.arb
app_es_ES.arb
app_fr_FR.arb
app_no_NO.arb
```

Geração via `flutter gen-l10n`:
```yaml
# flutter/pubspec.yaml
flutter:
  generate: true
```

### Uso no Flutter

```dart
// Em widgets
import 'package:epi_i18n/epi_i18n.dart';

Text(context.l10n.dashboardTitle)
Text(context.l10n.alertsLowStock(epiName: 'Capacete'))
```

### Configuração no App

```dart
MaterialApp.router(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: userPreferredLocale,
)
```

## Regras para Novas Chaves

1. **Namespace obrigatório**: sempre prefixar com o módulo (`dashboard.`, `epis.`, `stock.`)
2. **Sem HTML em valores**: usar `data-i18n-html` apenas para conteúdo rico necessário
3. **Interpolação segura**: usar `{varName}` para variáveis, nunca concatenar strings
4. **Fallback em pt-BR**: toda chave nova deve existir em `pt-BR.json` e `app_pt_BR.arb`
5. **Paridade de chaves**: todos os idiomas devem ter as mesmas chaves (CI verifica)
6. **Plural simples**: usar `{count}` + lógica JS/Dart para pluralização (sem ICU complexo por ora)

## Processo de Tradução

1. Adicionar chave em `pt-BR.json` (e `app_pt_BR.arb` para Flutter)
2. Abrir issue ou PR com a tradução
3. Tradutores preenchem os demais idiomas
4. CI valida paridade de chaves antes do merge
