# Assinatura Android — keystore, secrets e o AAB de release

> Issue de origem: **rocksbrothers-png/epi-controle-app#200**. Este documento é a referência para configurar a
> geração de AAB assinado na CI e no deploy para a Google Play.

## 1. O problema que este documento fecha

Até a rocksbrothers-png/epi-controle-app#200 do repositório principal, a esteira Android entregava três dos quatro artefatos:

| Artefato | Estado |
|---|---|
| APK debug | ✅ gerado |
| Flutter Web | ✅ gerado |
| Integração no emulador | ✅ roda |
| **AAB release** | ❌ falhava |

A falha não era de código. `flutter build appbundle --release` exige uma chave
de assinatura, e o repositório não tem nenhuma — corretamente, porque **chave
privada não entra em repositório**. O que estava errado era a *forma* da falha:
o passo `Configure Android signing` imprimia `not set — skipping signing setup`
e **saía com código 0**, deixando o build estourar três passos adiante com um
erro de Gradle sobre `storeFile` nulo.

O efeito colateral disso vale registrar, porque custou tempo: um passo verde
chamado "Configure Android signing" é lido por qualquer pessoa como prova de
que os secrets existem. Ele não era. Um job vermelho por falta de configuração
é indistinguível, no painel do GitHub, de um job vermelho por código quebrado —
e essa ambiguidade é o defeito real.

## 2. A regra adotada

- **Sem secrets → o job fica `skipped`.** Nunca vermelho. Não há AAB a produzir
  sem chave; dizer isso com `skipped` é honesto.
- **Com secrets → o AAB sai assinado, automaticamente, em todo push na `main`.**
- O motivo do skip aparece no **resumo do job** `Check Android signing secrets`,
  nomeando quais secrets faltam.

Como `secrets` não é acessível num `if:` de job no GitHub Actions — só dentro de
um step — a implementação usa um job-sonda (`android-signing`) que exporta
`configured=true|false`, e o job de build depende desse output.

Os quatro secrets são exigidos **em conjunto**: um keystore sem alias ou sem
senha produz exatamente a mesma falha de build que keystore nenhum, e é bem mais
difícil de diagnosticar. Parcialmente configurado conta como não configurado.

## 3. Secrets — `flutter.yml` (CI, build do AAB)

Configurar em **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Conteúdo |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | o arquivo `.jks` inteiro, codificado em base64 |
| `ANDROID_STORE_PASSWORD` | senha do keystore (`storePassword`) |
| `ANDROID_KEY_ALIAS` | alias da chave dentro do keystore (`keyAlias`) |
| `ANDROID_KEY_PASSWORD` | senha da chave (`keyPassword`) |

O workflow decodifica o base64 para
`flutter/apps/epi_admin/android/upload-keystore.jks` e escreve
`flutter/apps/epi_admin/android/key.properties`, que é o arquivo que
`app/build.gradle` já lê (`rootProject.file('key.properties')`). Nenhuma dessas
duas coisas é versionada — ambas nascem e morrem dentro do runner.

## 4. Secrets — `deploy-android.yml` (publicação na Google Play)

O workflow de deploy usa **outro conjunto de nomes**, herdado de antes:

| Secret | Conteúdo |
|---|---|
| `KEYSTORE_BASE64` | mesmo `.jks` em base64 |
| `KEYSTORE_PASSWORD` | mesma senha do keystore |
| `KEY_ALIAS` | mesmo alias |
| `KEY_PASSWORD` | mesma senha da chave |
| `GOOGLE_PLAY_JSON_KEY` | JSON da service account do Google Play |

**A divergência de nomes é real e conhecida.** Os dois conjuntos apontam para a
mesma chave física. Unificá-los é trabalho da issue de *Padronização de
Artefatos Android*, não desta — mudar os nomes aqui exigiria recriar secrets em
dois repositórios ao mesmo tempo, e essa é justamente a classe de mudança que a
padronização existe para fazer de uma vez só.

Enquanto isso: para ter **CI verde com AAB**, bastam os quatro `ANDROID_*`. Os
`KEYSTORE_*`/`KEY_*` só são necessários quando for de fato publicar na Play.

## 5. Gerando o keystore

Se ainda não existe uma chave de upload:

```bash
keytool -genkey -v \
  -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias upload
```

O `keytool` pergunta a senha do keystore e a senha da chave (podem ser a mesma)
e os dados do certificado.

Para gerar o valor do secret:

```bash
base64 -w 0 upload-keystore.jks    # Linux
base64 -i upload-keystore.jks      # macOS
```

Cole a saída inteira, em uma única linha, em `ANDROID_KEYSTORE_BASE64`.

### Cuidados que não são formalidade

- **Guarde o `.jks` fora do repositório e faça backup.** Perder a chave de
  upload de um app já publicado significa não conseguir mais atualizá-lo sem
  passar pelo processo de reset de chave do Google. O `.gitignore` já cobre
  `*.jks` e `key.properties`, mas a proteção real é não colocar o arquivo na
  árvore.
- **Não reaproveite a chave entre `epi-controle-app` e `epi-controle`** a menos
  que os dois publiquem o *mesmo* `applicationId`. Hoje só o principal publica.
- O secret é escrito no runner em texto claro dentro de `key.properties`. Isso é
  inerente ao processo de assinatura; o que evita vazamento é o runner ser
  efêmero e os logs mascararem valores de secrets.

## 6. Como confirmar que funcionou

Depois de cadastrar os quatro secrets, dispare `Flutter CI` na `main`
(**Actions → Flutter CI → Run workflow**, ou qualquer push que toque
`flutter/**`) e verifique:

1. `Check Android signing secrets` — verde, com
   `✅ Secrets de assinatura presentes` no resumo.
2. `Build Android (AAB)` — deixa de aparecer como `skipped` e roda.
3. O artefato `epi-admin-release-<sha>` aparece no run, contendo
   `app-release.aab`.

Para verificar a assinatura do artefato baixado:

```bash
unzip -p app-release.aab META-INF/*.RSA | keytool -printcert
```

## 7. Reverter

Remover os quatro secrets devolve o comportamento anterior à configuração: o job
volta a `skipped` e o CI segue verde. Nenhum código precisa mudar para isso — é
exatamente o ponto do gate.

## 8. Nota sobre o filtro `paths:`

`flutter.yml` dispara em `paths: ['flutter/**']`. Um PR que altere **apenas** o
próprio workflow não o dispara — o filtro não cobre o arquivo que o define. Para
validar mudanças neste workflow use **Run workflow** (`workflow_dispatch`) ou
inclua alguma alteração sob `flutter/` no mesmo PR.
