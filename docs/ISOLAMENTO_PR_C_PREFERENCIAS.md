# Isolamento entre Usuários — PR C: preferências pessoais de interface

Terceira e última fatia da frente de Isolamento, depois de **PR A** (View,
`#993`/`#366`) e **PR B** (telemetria, `#994`/`#367`).

## 1. O defeito

Num computador compartilhado, quem entrava herdava a aparência de quem saiu.
Quatro preferências, quatro chaves de `localStorage`, todas de escopo DEVICE:

| Preferência | Chave antiga | Dono antigo |
|---|---|---|
| Tema | `epi-theme` | `_applySettings` + botão da topbar |
| Densidade da tabela | `epi-density` | `_applySettings` |
| Sidebar recolhida | `epi-sidebar-collapsed` | `toggleSidebarCollapsed` |
| Idioma | `epi_language` | `i18n.js` |

A caracterização mediu 12 heranças entre identidades em 3 trocas (`ISOL C-5`).

O caminho mais grave era o **pré-paint**. O `_head.html` lia `epi-theme` e
aplicava o tema **antes de qualquer autenticação**, para evitar o flash de tema
claro. Corrigir depois não resolve: quem entrou **já viu** a tela de quem saiu.

## 2. O que NÃO era

O escopo DEVICE não era descuido. Era decisão de produto declarada — na UI
("As preferências são salvas neste dispositivo.") e no código ("Persistência
por dispositivo (localStorage)") — com gates próprios na `#343 F3` que
**reprovavam** quem tentasse indexar preferência por usuário.

Portanto esta fatia não corrigiu um bug: **substituiu uma decisão de produto
por outra**, o que exigiu converter os gates que protegiam a anterior, e trocar
a promessa na UI junto com o escopo. Um produto que muda o escopo sem mudar a
frase passa a mentir para o usuário.

## 3. A decisão

**Escopo USER, com o servidor como fonte da verdade.**

Não `USER+TENANT`: `users.company_id` é FK única e não existe fluxo de troca de
tenant dentro da sessão — o tenant é função da identidade, não uma dimensão
independente.

Não uma chave namespaced (`epi-theme:${user.id}`): ela deixaria o valor de cada
usuário legível no disco compartilhado por quem soubesse o id do outro, e não
resolveria o pré-paint, que não conhece identidade nenhuma. O gate
`test_nenhuma_preferencia_e_indexada_por_usuario` da F3 continua reprovando-a,
e continua certo.

## 4. O desenho

```
  servidor  users.ui_preferences  ← fonte da verdade, escopo USER
     │
     ├─ /api/bootstrap ─┐
     ├─ /api/auth/me    ├→ adotarPreferenciasDoServidor()  ← ponto único de entrada
     └─ GET  .../preferences
                        │
              RAM: _prefsEmMemoria + _prefsPrincipal
                        │
                        ├→ aplicarPreferenciasNaTela()
                        └→ cópia em sessionStorage, carimbada com o principal
                                 │
                                 └→ lida pelo PRÉ-PAINT da próxima carga desta aba
     ↑
  PUT /api/auth/me/preferences  ← definirPreferencias(), ator nunca vem do corpo
```

**A cópia de sessão existe por um motivo só:** deixar o pré-paint aplicar o tema
certo num F5 sem piscar. Ela vive em `sessionStorage`, que não atravessa aba nem
janela; carrega um **carimbo derivado** do principal — nunca o id em texto claro
—; é recusada **e removida** se o carimbo não bater; e é derrubada no
encerramento de sessão.

O carimbo é derivado porque responde a uma pergunta só — *"esta cópia é minha?"*
—, que é comparação e nunca leitura de volta. **Não é segredo criptográfico:** o
espaço de ids é pequeno e quem lê o `sessionStorage` pode enumerar. A cópia morre
com a aba; o que se ganha é guardar menos e deixar o fluxo legível.

**Por que não bastava apagar tudo no logout.** Isso impediria B de herdar de A,
mas destruiria a possibilidade de A recuperar as próprias preferências. O
objetivo era *ownership* correto, não limpeza mais agressiva. Com o servidor
como dono, o logout derruba só a cópia — e A reencontra tudo no próximo login,
em qualquer dispositivo (`ISOL C-11`).

## 5. UNOWNED LEGACY

Valores gravados pela versão anterior não têm dono comprovável. Entregá-los ao
primeiro que logasse transformaria preferência **compartilhada** em preferência
**pessoal da pessoa errada**.

`aposentarPreferenciasLegadas()` apaga as quatro chaves **sem nunca lê-las**.
Nomeadas uma a uma: nada de `localStorage.clear()` — sessão, flags e tenant
moram no mesmo storage com contratos diferentes. O `ISOL C-8` prova as duas
metades, com chaves de outros donos como controle.

## 6. Três defeitos encontrados pelos próprios gates

**Um segundo escritor de tema.** O botão da topbar aplicava o tema no DOM e
gravava `epi-theme` por conta própria, sem passar pelo drawer. Duas gravações
independentes da mesma preferência é como uma delas sobrevive a uma correção
feita só na outra. Achado pelo `ISOL C-12`.

**A primeira leitura apagava a cópia da própria aba.** `_prefsPrincipal`
começava em `null`, indistinguível de "ninguém logado", então a primeira
pergunta da página parecia uma troca de principal e derrubava o atalho do
pré-paint. Achado pelo controle positivo do `ISOL C-14`.

**O `ISOL C-14` media a própria suposição.** Ele semeava a cópia de sessão na
mão, com o carimbo literal — então media o formato que eu tinha imaginado, e não
o mecanismo; quebraria a cada mudança interna do dono. Foi reescrito para usar o
caminho real: A entra na aba e configura, B entra na mesma aba depois.

## 7. Sabotagens

Cada mecanismo foi quebrado de propósito, um por vez, e um gate específico
acusou. **Duas passaram verde na primeira rodada** — β e γ —, repetindo a lição
do PR B: os gates estavam certos no resultado e errados no motivo. `ISOL C-13` e
`ISOL C-14` nasceram daí. A η e o `ISOL C-15` vieram depois, com a revisão do
CodeQL (§ 9).

| Sabotagem | Acusada por |
|---|---|
| α — pré-paint volta a ler a chave DEVICE | `C-9`, `C-9b`, `C-14` |
| β — troca de principal deixa de descartar | `C-13` |
| γ — cópia de sessão deixa de conferir o carimbo | `C-14` |
| δ — legado sem dono deixa de ser aposentado | `C-8` |
| ε — cliente deixa de persistir no servidor | `C-5`, `C-11` |
| ζ — o dono volta a gravar em `localStorage` | `C-12` |
| η — o carimbo volta a ser o id em texto claro | `C-15`, `C-14` |

A **ε** é a mais importante: sem o `C-11`, uma versão que simplesmente não
guardasse nada passaria em todos os gates de não-herança — e perder a
preferência de todo mundo não é isolamento, é outro defeito.

## 8. Gates convertidos

Nenhum foi apagado. Cada um diz no próprio corpo o que ficou obsoleto e por quê.

| Gate | O que mudou |
|---|---|
| `F3 :: a promessa ao usuário` | a frase na UI acompanha o escopo novo; a antiga passa a ser proibida |
| `F3 :: logout não limpa tema nem idioma` | virou "o logout não **destrói** a preferência do usuário" — ela está no servidor |
| `F3 :: nenhuma persistência server-side` | virou "os campos `preferred_locale`/`company_locale` do D1 continuam sem existir", + um gate novo exigindo que a persistência do PR C exista |
| `F3 :: nenhuma preferência indexada por usuário` | **mantido sem alteração** — e passa por mérito, não por escopo |
| `F2 :: a F2 não toca no tema` | a metade que exigia a chave DEVICE **existir** saiu; a que proíbe `localStorage` no encerramento ficou |
| `F2 :: o encerramento só mexe nas próprias chaves` | quatro chaves em vez de três; a lista continua fechada |
| `navegação :: drawer de Configuração` | exige o dono único em vez de uma chave solta |
| `navegação :: sidebar recolhível` | idem |

## 9. CodeQL

Quatro alertas no diff, todos fechados, todos apontando para algo real.

`js/clear-text-storage-of-sensitive-data` foi o mais instrutivo, e exigiu **duas
rodadas**. A primeira correção — nomear os quatro campos gravados em vez de
espalhar o objeto — era boa por si, mas não era o caminho que a ferramenta via, e
o alerta voltou. O caminho real: `prefsPrincipalCorrente()` alcança o objeto
`state`, que também guarda `requirePasswordChange` e o token de sessão; a análise
não distingue campos dentro dele. Estava certa sobre a forma, e a resposta foi
derivar o carimbo (§ 4).

`js/bad-tag-filter` (2×) apontou a regex de `<script>` com que o harness extraía
o pré-paint: frágil e lida como tentativa de filtrar HTML. Passou a extrair por
delimitador literal, num lugar só — a expressão estava duplicada nos dois gates.

`py/empty-except` apontou o `except` do rollback, que engolia sem dizer por quê.

## 10. Limites desta fatia

- O **app Flutter** não mudou de escopo. `LocaleProvider` e `ThemeModeNotifier`
  seguem com escopo de instalação, e os gates que os protegem valem palavra por
  palavra.
- O pré-paint parte do **padrão neutro** quando a aba é nova. É o único
  comportamento que não pode vazar por construção, e o preço é um quadro de tema
  claro no primeiro acesso de cada aba — não a cada F5.
- `epi_tenant`, feature flags, diagnostic mode e rollout flags **não** foram
  tocados: contratos diferentes, fora do escopo autorizado.
