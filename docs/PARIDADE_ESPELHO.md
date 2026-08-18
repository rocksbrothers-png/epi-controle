# Paridade `epi-controle` ⇄ `epi-controle-app`

Decisão vigente: o `epi-controle` é **réplica funcional completa e
release-capable** do `epi-controle-app`, cobrindo Flutter Web, Android e iOS.
Publicar pelo espelho é opcional; **construir** pelo espelho não é.

| | Web | Android | iOS build | Publicação |
|---|---|---|---|---|
| `epi-controle-app` | ✅ | ✅ | ✅ | ✅ |
| `epi-controle` | ✅ | ✅ | ✅ | opcional |

Paridade aqui significa **funcional e arquitetural**, nunca igualdade byte a
byte. Este documento classifica cada divergência conhecida e é a fonte da
lista que o gate de drift verifica.

## Classificação

1. **Drift funcional** — comportamento existente no principal, ausente ou
   diferente aqui. Sincronizar.
2. **Drift estrutural** — widget, service, model ou componente necessário para
   manter a mesma arquitetura. Sincronizar.
3. **Diferença legítima** — identidade, assinatura, deploy. Preservar.
4. **Gerado/derivável** — reconstruível de forma confiável. Não copiar.
5. **Cosmético ou legado** — investigar antes de transportar.

---

## Resumo

| categoria | itens |
|---|---|
| 1 · Drift funcional | 30 arquivos + 4 ausentes |
| 2 · Drift estrutural | 1 diretório (`lib/core/widgets/`) |
| 3 · Legítimo — preservar | 8 |
| 4 · Gerado — não copiar | projeto iOS inteiro (38 arquivos) |
| 5 · Cosmético/legado | 2 |

---

## Categoria 4 primeiro: o iOS **não** é dívida

Este é o achado que muda o plano, e vale antes de tudo.

`Runner.xcodeproj`, `Runner.xcworkspace`, `RunnerTests`, `AppDelegate.swift`,
`Assets.xcassets`, `Base.lproj`, `Runner-Bridging-Header.h` e
`Flutter/*.xcconfig` **não deveriam estar versionados em repositório nenhum**.
Os dois CIs os geram:

```yaml
# ios_ci.yml, idêntico nos dois repositórios
if [ ! -d ios/Runner.xcodeproj ]; then
  flutter create . --platforms=ios --org com.rocksbrothers --project-name epi_admin
```

O cabeçalho do próprio workflow diz: *"o projeto iOS (Runner.xcodeproj/Podfile)
NÃO é versionado — é gerado por `flutter create`"*.

- Aqui: **15 arquivos** versionados em `ios/` — só o que não é gerável.
- No principal: **53**, incluindo o `Runner.xcodeproj` inteiro, que entrou por
  engano num merge (`27611d3`, PR #19) e nunca foi removido.

**O espelho está certo; o principal é que tem a anomalia.** E a capacidade que
a decisão exige já existe e é comprovada: `flutter build ios --release
--no-codesign` passa aqui há três execuções seguidas na `main`
(`f4f45d3`, `21fb61b`, `3eb247f`).

Ação: **nenhuma cópia**. Abrir issue no principal para remover o projeto gerado
do controle de versão. O que a decisão pede já está satisfeito.

### Comparação item a item pedida

| item | principal | espelho | veredito |
|---|---|---|---|
| `Runner.xcodeproj` | versionado (por engano) | gerado no CI | 4 · não copiar |
| `Runner.xcworkspace` | versionado (por engano) | gerado no CI | 4 · não copiar |
| `Podfile` | não versionado | não versionado | — já em paridade |
| `Info.plist` | versionado | versionado | 3 · difere só no bundle id |
| `Runner.entitlements` | versionado | versionado | **idênticos** |
| schemes/configurations | gerado | gerado | 4 · não copiar |
| bundle identifier | `com.livamobile.epicontrole` | `com.rocksbrothers.epicontrole` | 3 · preservar |
| signing | fastlane próprio | fastlane próprio | 3 · preservar |
| Firebase | `iosBundleId` no `firebase_options.dart` | idem, org própria | 3 · preservar |

Não há `GoogleService-Info.plist` versionado em nenhum dos dois.

---

## Categoria 3 · Diferenças legítimas — preservar

| arquivo | diferença |
|---|---|
| `lib/firebase_options.dart` | `iosBundleId` (única linha divergente) |
| `ios/Runner/Info.plist` | bundle identifier |
| `ios/ExportOptions.plist` | bundle identifier |
| `ios/fastlane/{Appfile,Fastfile,pin_ios_deployment_target.rb}` | assinatura e deploy |
| `android/app/build.gradle`, `proguard-rules.pro` | applicationId e ofuscação |
| `android/app/src/main/kotlin/com/{rocksbrothers,livamobile}/` | namespace |
| `web/manifest.json` | ausente aqui — **verificar**: pode ser gerado por `flutter create`, ou identidade PWA própria |

---

## Categoria 5 · Cosmético ou legado

| arquivo | situação |
|---|---|
| `features/reports/reports_screen.dart` | o **espelho tem 3 linhas de comentário a mais** (nota sobre `SideTitleWidget` no fl_chart 1.x). Código idêntico. Sincronizar apagaria informação útil — o certo é **portar o comentário para o principal**, não removê-lo daqui |
| `test/employee_unit_movement_contract_test.dart` | 3 linhas: cobre `current_unit_name`, que depende do lote de models. Vai junto com o Lote 2 |

---

## Categorias 1 e 2 · Lotes de sincronização

Ordem por risco, não por tamanho.

### Lote 1 — Segurança e autenticação · 9 arquivos

Senha temporária no 1º acesso: o backend provisiona credencial com
`must_change_password`, e **este repositório ignora a flag por completo** — o
usuário entra direto, com a senha temporária válida indefinidamente. É a
divergência de maior severidade do conjunto.

| arquivo | o que falta | cat. |
|---|---|---|
| `features/auth/change_password_screen.dart` | **ausente** | 1 |
| `core/router/routes.dart` | rota `changePassword` | 1 |
| `core/router/app_router.dart` | gate que prende na tela até trocar | 1 |
| `core/bloc/auth_state.dart` | `mustChangePassword` no estado e em `props` | 1 |
| `core/bloc/auth_cubit.dart` | `completePasswordChange()` | 1 |
| `core/api/api_client.dart` | `changePassword()`, `ApiException` | 1 |
| `lib/app.dart` | `ValueNotifier` que alimenta o gate | 1 |
| `packages/epi_api/lib/endpoints/auth_api.dart` | leitura de `must_change_password` (topo **ou** dentro de `user`) | 1 |
| `packages/epi_api/test/auth_contract_test.dart` | teste do contrato acima | 1 |

**Prova de paridade:** `auth_contract_test` (captura da flag nas duas posições)
+ `route_permissions_test` e `navigation_policy_test` para a rota nova.

### Lote 2 — Models e parsing · 5 arquivos

Não é refinamento: **os models daqui leem chaves que o backend não envia.**

- `Employee`: lê `code`, `role`, `schedule`; o backend manda
  `employee_id_code`, `role_name`, `schedule_type`. Os campos chegam nulos.
- `Company.active`: lê `bool`; a coluna é `INTEGER` e o backend serializa 0/1.
- `FichaConfig.rastreabilidade`: tipado `bool` aqui, é **String** no backend —
  um rótulo de rodapé. Hoje o rodapé da ficha imprime `true`/`false`.

| arquivo | cat. |
|---|---|
| `packages/epi_api/lib/models/employee.dart` | 1 |
| `packages/epi_api/lib/models/company.dart` | 1 |
| `packages/epi_api/lib/models/ficha_config.dart` | 1 |
| `packages/epi_api/test/clients_contract_test.dart` | 1 |
| `packages/epi_api/test/employee_unit_movement_contract_test.dart` | 5 |

**Prova:** os 5 testes de `clients_contract_test` que usam payload real do
backend (`active` 0/1, `rastreabilidade` String, `employee_id_code`,
`current_unit_name`, tolerância a bool antigo).

### Lote 3 — Gestão de EPI e conformidade de estoque · 4 arquivos

Fonte única de conformidade (`GET /api/stock/compliance`), consumida pelo
dashboard.

| arquivo | o que falta | cat. |
|---|---|---|
| `packages/epi_api/lib/endpoints/stock_api.dart` | `getStockCompliance` | 1 |
| `core/bloc/dashboard_cubit.dart` | campo `compliance` | 1 |
| `features/dashboard/dashboard_screen.dart` | `_ComplianceSection` | 1 |
| `packages/epi_api/test/audit_fixes_contract_test.dart` | **ausente** | 1 |

Observação: o `epi_archival_contract_test.dart` daqui já cobre a metade de EPI
desse arquivo. Ao trazer o `audit_fixes_contract_test`, decidir entre fundir os
dois ou manter separados.

### Lote 4 — Fluxo operacional de entrega · 8 arquivos

Conferência de entrega por QR.

| arquivo | o que falta | cat. |
|---|---|---|
| `features/deliveries/handover_conference_screen.dart` | **ausente** | 1 |
| `packages/epi_api/lib/endpoints/deliveries_api.dart` | `handoverLookup` | 1 |
| `features/deliveries/deliveries_screen.dart` | botão de acesso | 1 |
| `features/qr/qr_scanner_screen.dart` | modo `returnResult` (picker) | 1 |
| `core/router/routes.dart` | rota `handover` (junto com o Lote 1) | 1 |
| `core/router/navigation_policy.dart` | módulo da rota | 1 |
| `core/router/route_permissions.dart` | `deliveries:view` | 1 |
| `packages/epi_api/test/handover_contract_test.dart` | **ausente** | 1 |

**Prova:** `handover_contract_test` + os 3 testes de navegação
(`app_shell_navigation_test`, `navigation_policy_test`,
`route_permissions_test`), que divergem hoje exatamente por esta rota.

### Lote 5 — Configurações e empresas · 6 arquivos

| arquivo | o que falta | cat. |
|---|---|---|
| `core/widgets/create_company_dialog.dart` | **ausente** (diretório inteiro) | **2** |
| `core/bloc/companies_cubit.dart` | `create()`, `catch` amplo | 1 |
| `features/companies/companies_screen.dart` | FAB gateado por `companies:create` | 1 |
| `core/api/api_client.dart` | `createCompany()` (junto com o Lote 1) | 1 |
| `core/bloc/settings_cubit.dart` | `isMaster`, `companies`, `selectedCompanyId` | 1 |
| `features/settings/settings_screen.dart` | `_CompanySelector` (master_admin escolhe o tenant) | 1 |
| `packages/epi_api/lib/endpoints/settings_api.dart` | `companyId` em `get/updateFichaConfig` | 1 |

Sem o seletor, o `master_admin` **não consegue configurar a Ficha de nenhum
tenant** — ele não tem empresa própria.

### Lote 6 — Robustez de plataforma · 2 arquivos

| arquivo | o que falta | cat. |
|---|---|---|
| `core/sync/sync_service.dart` | guard `kIsWeb` — sem ele, `sqflite` lança exceção não tratada em **todas as telas** no Web | 1 |
| `core/shell/app_shell.dart` | botão "Sair" na AppBar | 1 |

O guard `kIsWeb` é candidato a subir de prioridade: afeta o Web inteiro, que é
plataforma ativa aqui.

---

## Gate de drift

`flutter/tool/check_parity_drift.py`, executado no CI dos dois repositórios.

### Como funciona sem acesso ao outro repositório

Por um **manifesto compartilhado**. `tool/parity_manifest.json` lista os
arquivos que precisam permanecer funcionalmente sincronizados, cada um com o
hash do conteúdo **normalizado**. O mesmo manifesto vive nos dois lados.

```
editou aqui → regenera o manifesto → commita nos DOIS
                                   ↘ o outro repo fica vermelho até sincronizar
```

Isso importa porque o CI de um repositório não tem credencial para ler o outro.
Fazer `actions/checkout` do repo vizinho exigiria um PAT compartilhado; o
manifesto entrega a mesma garantia sem introduzir segredo novo.

### Normalização — as diferenças legítimas

`tool/parity_normalize.py` troca por um marcador canônico o que **deve**
diferir. Hoje há uma regra só, e ela cobre toda a categoria 3:

    <ORG>  ← prefixo da organização: applicationId, bundle identifier,
             iosBundleId, namespace do pacote Kotlin e o --org do
             flutter create.

Só o **prefixo** é normalizado. `<ORG>.epicontrole` e `<ORG>.outro` continuam
distintos — colapsar o sufixo faria dois pacotes diferentes produzirem o mesmo
hash, e o gate deixaria de ver uma troca real.

Espaço em branco e comentário **não** são normalizados, de propósito: uma
reformatação que só um dos lados recebeu é drift. Ela torna o próximo diff entre
os repositórios ilegível — que foi exatamente como a divergência de 33 arquivos
chegou até aqui sem ninguém notar.

### Cobertura

O manifesto começa com **199 arquivos** — os que já estão em paridade — e cresce
a cada lote. Não cobre os ainda divergentes, de propósito: um gate que exigisse
paridade total hoje nasceria vermelho, e gate que nasce vermelho é gate que
alguém desliga. O que falta está nas seções de lotes acima, não no gate.

Dois arquivos ficaram de fora por estarem **em trânsito**, não por divergirem
de verdade: os do Lote 1 e o `reports_screen.dart` (nota do fl_chart). O
manifesto só pode listar o que já está em paridade nas DUAS `main` — gerá-lo a
partir de um branch não mergeado prometeria uma paridade que o outro lado ainda
não tem. Foi o próprio gate que barrou as duas tentativas de fazer isso, o que
é uma demonstração razoável de que ele funciona.

### Testes

`tests/test_parity_drift_gate.py` cobre as duas formas de um gate assim ser
inútil: **rígido demais** (acusar identidade de loja como drift — vermelho
permanente) e **frouxo demais** (deixar passar mudança funcional). Inclui a
prova viva de que `firebase_options.dart`, que difere entre os repositórios em
exatamente uma linha, entra no manifesto.

---

## Fechamento — Lotes 1 a 6 (concluídos)

Os 33 arquivos `.dart` divergentes mapeados nesta auditoria chegaram a **zero**.

| | |
|---|---|
| SHA final `epi-controle-app` | `7a9645d` |
| SHA final `epi-controle` | `b161b8a` |
| Manifesto | **236 arquivos**, byte a byte idêntico nos dois (sha256 `f07d90cd5dc2a26f`) |
| Suítes | **2422 passed, 1 skipped** em cada repositório |
| Gate de drift | ✅ nos dois lados |
| Web / Android / iOS | Build Flutter Web ✅ · APK debug ✅ · AAB assinado ✅ · emulador Android ✅ · `flutter build ios --no-codesign` ✅ — nas duas `main` |

### O que cada lote corrigiu

| lote | defeito real (não cosmético) |
|---|---|
| 1 | `must_change_password` sem tela; `sqflite` derrubava **todas** as telas no Web |
| 2a | `Employee` lia chaves inexistentes; `Company.active` lançava `_CastError` e **apagava a lista de Empresas** |
| 2b | `FichaConfig.rastreabilidade` como `bool`: a aba nunca carregava, e o Switch gravava `'True'` no rodapé de documento de NR-6 |
| 3 | Dashboard não consumia a fonte única de conformidade |
| 4 | Conferência de entrega por QR ausente por inteiro |
| 5 | `master_admin` não configurava a Ficha de **nenhum** tenant |
| 6 | Sem botão de sair: encerrar sessão exigia limpar dados do app |

### Divergências remanescentes, classificadas

| # | arquivo(s) | categoria |
|---|---|---|
| 6 | `app_localizations*.dart` | **gerável** — os 10 ARBs são idênticos; `melos run gen:l10n` roda em todos os jobs e sobrescreve |
| 1 | `firebase_options.dart` | **diferença legítima** — `iosBundleId`; normalizada, dentro do manifesto |
| 4 | testes de `change_password_gate`, `ficha_rastreabilidade`, `sync_service_web_guard`, `epi_archival_contract` | **espelho à frente** em cobertura |

### O padrão que este trabalho revelou

Em **quatro lotes seguidos** (3, 4, 5 e o caso da Ficha) o achado foi idêntico:
rota registrada no backend, serviço implementado, testes de backend passando e
todas as chaves de i18n traduzidas nos 5 idiomas — e **nenhuma linha de Flutter
consumindo**. Não era desatualização difusa do espelho: era um ponto cego
reprodutível na camada Flutter do processo de replicação, invisível porque cada
replicação *parecia* completa e tradução órfã não acusa nada.

Daí a regra do ADR-0004. Ver também a issue de cobertura Flutter × Web Legado,
que quantifica a mesma classe de lacuna no outro eixo.
