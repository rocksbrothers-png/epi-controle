# Verificação de integridade do release — remediação EST-V1.6-R2

Esta verificação protege o contrato de isolamento do backend nos caminhos de
publicação Android, iOS e Fastlane. A identidade autorizada continua específica
de cada produto em `ci/authorized_backend.json`; não copie esse arquivo entre
Corporate e SaaS.

O backend SaaS atende aos aplicativos Flutter Web, Android e iOS do SaaS. O
Corporate tem backend, banco e identidade de aplicativo próprios. O mesmo
contrato de teste existe nos dois repositórios; os destinos autorizados continuam
distintos. O Web Corporate usa same-origin; o Web SaaS embute seu próprio backend
na configuração de build existente.

## Execução local

Use Python 3.11 ou superior, Bash e Ruby 3.3, disponíveis no PATH. Instale a
dependência de desenvolvimento no mesmo Python usado para executar os testes:

```bash
python3 -m pip install -r ci/requirements-release.txt
python3 -I tests/test_api_backend_guard.py
python3 -I tests/test_flutter_release_api_base_url.py
```

O primeiro script executa 14 verificações; o segundo, 25. Ruby não precisa de
Fastlane ou gems para essas sondagens. Em ambientes com executável Ruby fora do
PATH, `RELEASE_TEST_RUBY` pode informar seu caminho absoluto. A execução de uma
lane Fastlane real também exige essa dependência Python antes do gate.

Para a suíte completa, instale também `requirements.txt`, pytest, pytest-cov e
`ruff==0.16.5`. Ela exige Node no PATH e deve ser executada sem DATABASE_URL,
conforme o job de testes de `.github/workflows/backend-ci.yml`.

## O que é executado

- O YAML dos workflows é interpretado como estrutura, com rejeição de chaves
  duplicadas. Gatilhos, condições, tolerância a erros, checkout e ordem dos
  passos críticos são verificados.
- Os comandos Bash dos gates são executados com runners instrumentados. Cada
  teste de integridade falha separadamente; a execução precisa parar.
- Os resolvedores Bash e Ruby executam o guard Python real. URL ausente,
  whitespace e backend de outro produto, inclusive com hostname em maiúsculas,
  precisam ser rejeitados antes do build.
- Os argumentos efetivos dos builds são capturados com uma saída validada de
  prova. O build precisa consumir essa saída exatamente uma vez, sem substituí-la
  por URL literal ou pela variável ainda não validada. As formas separadas,
  e o alias histórico `--dart-defines` também entram na contagem. Formas `-D`
  são contadas conservadoramente, sem afirmar compatibilidade com o SDK real.
  Arquivos de
  defines não verificados são rejeitados. Vírgulas permanecem no valor, conforme
  `splitCommas: false` no parser Flutter; o valor inteiro deve ser o validado.
- As lanes `beta` e `release` do Fastfile são carregadas pelo Ruby. Uma falha de
  integridade deve interromper a lane antes de preparação, credenciais e build.
  A sondagem percorre a lane inteira até a chamada instrumentada de upload e
  exige um único build válido. Diretórios e um marcador de artefato vazio são
  criados apenas em área temporária; nenhum IPA é gerado.
- As regressões B01–B04 introduzem sabotagens em cópias temporárias, exigem
  rejeição pelo contrato correspondente e confirmam a baseline restaurada.
  Incluem segundo build após `beta`, opções alternativas, flag em outro comando,
  ambiente de passo/job/workflow e fallback de variável de shell.
  Também cobrem continuação escapada entre palavras do build e separador de
  comandos sem espaço; esses formatos não podem ocultar um build direto.
  O Fastfile também rejeita leitura de ambiente fora das entradas conhecidas e
  operadores de shell nos comandos instrumentados. Valores fictícios das chaves
  de assinatura são exclusivos dos testes e impedem que seu fallback nulo oculte
  um uso indevido; nenhuma credencial real é herdada.

O contrato atual de publicação nativa aceita saídas GitHub validadas diretamente
nos builds e rejeita variáveis de shell ou ambiente explícito não modelado nesse
caminho. Adicionar esse ambiente exige ampliar o contrato antes do release. Uma
flag `--no-codesign` em outro comando não exclui o build da verificação.

As sondagens não compilam apps, assinam artefatos, acessam credenciais ou fazem
upload. Instrumentação é exclusiva dos testes; não altera a aplicação nem o
guard. A descoberta de workflows cobre comandos nativos diretos de publicação
`flutter build appbundle/ipa`, exigindo `--release`; não demonstra qualquer comando gerado
dinamicamente ou uma chamada arbitrária a ação externa.

## CI e aprovação

O workflow dedicado continua com o mesmo nome e sem filtro de paths em PRs. Ele
instala PyYAML e Ruby antes dos scripts. Os workflows de publicação e a suíte
backend também preparam essas ferramentas explicitamente. PyYAML está apenas em
`ci/requirements-release.txt`, sem nova dependência de execução do backend.

Passar esses testes é verificação da implementação. Uma nova validação
independente deve revisar o patch exato, repetir as sabotagens em cópias isoladas
e consultar os checks da PR. Remover o próprio workflow exige também revisão
humana e governança de required checks. A remediação não altera branch protection
e não autoriza merge, deploy ou início da EST-V2.
