# Achados históricos do gitleaks (classificação de 17/11/2026)

## Contexto

Quando o workflow `Security` é disparado manualmente (`workflow_dispatch`), o
gitleaks varre o histórico inteiro do repositório. Em pull requests ele varre
só os commits do PR. A varredura completa encontra 12 achados, todos da regra
`generic-api-key` e todos anteriores a esta correção. Os valores não são
reproduzidos aqui.

## Classificação

| Arquivo | Achados | Natureza | Classificação |
|---|---|---|---|
| `tests/test_tenant_domains_and_owner_security.py`, linha 109 | 1 | Segredo TOTP fictício usado no teste da URI `otpauth://` | Falso positivo (dado de teste) |
| `.../chrome-device/Default/Secure Preferences` | 4 | Campo `key` dos manifestos das extensões nativas do Chrome (chaves públicas) | Falso positivo (público por natureza) |
| idem | 2 | MACs de integridade das preferências (`protection.macs`), locais ao perfil | Falso positivo (dado interno do navegador) |
| idem | 2 | `policy_recovery_token` e seu hash, gerados pelo navegador; o perfil não tem conta Google | Falso positivo (sem vínculo com serviço) |
| `.../chrome-device/Default/Preferences` | 2 | `receiver_id_hash_token` (Media Router) e `hash_real_time_ohttp_key` (chave pública do Safe Browsing) | Falso positivo |
| `.../chrome-device/Default/BrowsingTopicsState` | 1 | `hex_encoded_hmac_key` local da Topics API | Falso positivo |

Os bancos do perfil foram inspecionados só por contagem: 0 senhas salvas, 0
cookies, 0 itens de autopreenchimento, 0 cartões, 0 tokens de conta e 1 entrada
de histórico local. Nenhum dos achados é credencial do sistema ou de usuários,
e nenhum exige revogação.

## Causa e correção

O perfil foi criado por `flutter run -d chrome` em
`flutter/apps/epi_admin/.dart_tool/chrome-device/` e entrou no git antes da
regra `flutter/**/.dart_tool/` do `.gitignore`. Arquivo já versionado continua
versionado mesmo com a regra.

Esta correção retira os 139 arquivos do índice (`git rm --cached`) sem
reescrever o histórico. `tests/test_no_versioned_browser_profile.py` impede
que o perfil volte.

## Regras específicas propostas (não aplicadas)

A remoção não apaga os achados do histórico. Se a varredura completa precisar
ficar verde, a proposta mais restrita é registrar só os 12 fingerprints em
`.gitleaksignore`, um por achado (`<commit>:<arquivo>:generic-api-key:<linha>`),
em vez de uma exceção por caminho ou por regra. Isso depende de aprovação
explícita e não faz parte desta correção.

Os demais artefatos gerados pelo Flutter que estavam versionados (`.dart_tool/`,
`.flutter-plugins-dependencies` e o `GeneratedPluginRegistrant.java` do Android,
38 arquivos) não geraram achados, mas traziam caminhos absolutos da máquina de
quem os gerou. Foram retirados do índice num PR separado, com regras próprias no
`.gitignore` e a guarda `tests/test_no_versioned_flutter_generated.py`.
