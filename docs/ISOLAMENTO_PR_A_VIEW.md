# Isolamento entre Usuários em Computador Compartilhado — PR A: a View

Primeira das três fatias. Trata **só** o estado de navegação; tema, densidade,
sidebar, idioma (PR C) e telemetria (PR B) ficam para as fatias seguintes.

## Premissa de produto

O mesmo computador e navegador podem ser utilizados por pessoas diferentes.
Preferências pessoais, estado de navegação e telemetria de um usuário **não**
devem ser herdados por outro.

---

## 1) O defeito

A investigação mostrou que não existe nenhuma chave de storage persistindo
"modo de View" — o `epi_vtab_<grupo>` saiu na #343 F5-B. A View vazava por
outro caminho: **o histórico da aba**.

```
A entra → navega para "estoque" → history.state = { view: 'estoque', sid: <de A> }
A sai   → terminateSession() → recarrega (as entradas ANTERIORES ficam)
B entra → aperta Voltar → o navegador entrega o state de A
```

O carimbo `sid` da #343 F2 existia e funcionava — mas **tarde e de menos**:

| | antes | agora |
|---|---|---|
| **momento** | depois do `showView` | antes de escolher a view |
| **alcance** | só os filtros | a view também |

Medição do estado anterior, com o app real montado:

```
sid de A : uuid-073cfe61765c        sid de B : uuid-e460b8b5ccb84     casam? NÃO
[1] showView(event.state.view)        → view aplicada em B: "estoque"
[2] restoreInteractiveSnapshot(state) → filtros de A vazaram? NÃO — o sid barrou

filtros → isolados     view → VAZA
```

### O segundo defeito, que o gate A-8 expôs

`rotateSnapshotScope()` **não rotacionava nada sem recarga**. Ela apagava a
marca e deixava `snapshotScopeId()` recair em `DOCUMENT_INSTANCE_ID` — o mesmo
valor de antes, no mesmo documento.

Isso bastava no `terminateSession()`, que recarrega. Mas no **login de outro
principal** não há recarga — e esse é justamente o cenário que o comentário da
própria função descreve ("A logado, backend cai, F5, B entra sem encerramento").
A rotação era um no-op ali, e com ela caíam a proteção da view **e a dos
filtros**, que se acreditava garantida desde a F2.

---

## 2) O que mudou no código

| Onde | O quê |
|---|---|
| `escopoDoEstadoConfere()` | **novo** — dono único da regra "este estado é desta sessão?" |
| `restoreInteractiveSnapshot()` | passa a consumir esse dono em vez de repetir a comparação |
| handler de `popstate` | valida o escopo **antes** de escolher a view; fora do escopo, cai em `defaultView()` |
| `novoDiscriminadorDeEscopo()` | **novo** — o gerador saiu do IIFE de `DOCUMENT_INSTANCE_ID` e virou reutilizável |
| `rotateSnapshotScope()` | gera e **publica** um escopo novo, em vez de só apagar o atual |

Fora do escopo, o fallback é **direto** para `defaultView()` — não passa por
`resolveViewFromLocation()`. A URL daquela entrada de histórico é de quem saiu e
carrega o mesmo `?view=`: lê-la devolveria o vazamento pela porta dos fundos.

**Efeito colateral desejável:** ao caminhar pelo histórico, B reescreve cada
entrada com o próprio snapshot. O histórico de quem saiu se apaga à medida que
o atual passa por ele.

### O que esta fatia NÃO faz

- não persiste View em `localStorage` nem `sessionStorage`;
- não toca `bindMenuNavigation` → `navigateToView`, que continua a autoridade única de navegação (#343 PR 2D);
- não reintroduz `multitab-navigation.js`, listener em captura, `stopImmediatePropagation()` nem segundo dono;
- não altera o deep link `?view=` na carga inicial.

---

## 3) Gates

### Adicionados

| Gate | O que trava |
|---|---|
| `ISOL A-0` | o harness monta o app servido e alcança o caminho de Voltar (um listener de `popstate`, não zero, não dois) |
| `ISOL A-1` | **A → View X → logout → B → Voltar**: B não entra na View de A |
| `ISOL A-2` | **contraprova**: o Voltar legítimo da mesma sessão continua funcionando |
| `ISOL A-3` | estado **sem carimbo** não escolhe a View — ausência é recusa, não permissão |
| `ISOL A-4` | a URL antiga com `?view=` não é porta dos fundos |
| `ISOL A-5` | `popstate` sem estado não quebra e não escolhe View alheia |
| `ISOL A-6` | a validação de escopo **precede** o `showView` — o defeito era a ordem |
| `ISOL A-8` | troca de identidade **sem logout** também invalida a View anterior |
| `ISOL A-9` | o deep link `?view=` na **entrada inicial** continua abrindo a tela |
| `ISOL A-7` | a fatia não cria persistência de View nem segundo dono de navegação |

O harness `montarDocumentoIsolamento()` modela o que a #343 não precisava
modelar: **duas cargas de página na mesma aba**, com o `sessionStorage`
sobrevivendo entre elas. Ele declara `crypto` de propósito — sem Web Crypto,
`DOCUMENT_INSTANCE_ID` cai no fallback `t${Date.now()}` e duas cargas no mesmo
milissegundo receberiam o mesmo identificador: o gate passaria ou falharia por
relógio.

### Verificação de sabotagem

Os gates foram escritos **antes** da correção e falharam. Depois da correção,
duas sabotagens confirmaram que continuam portadores de carga:

| Sabotagem | Gates que ficaram vermelhos |
|---|---|
| remover a validação do `popstate` | `A-1`, `A-3`, `A-4`, `A-6`, `A-8` |
| rotação volta a só apagar a marca | `A-8` |

### Convertidos

| Gate | De | Para |
|---|---|---|
| `#343 F2 · snapshot de outro documento é descartado` | literal `snapshot.sid !== snapshotScopeId()` | `escopoDoEstadoConfere()` + a regra ainda compara o carimbo |
| `#343 F2 · o carimbo muda a cada carga` | `crypto` dentro do IIFE | `crypto` no gerador reutilizável, e `DOCUMENT_INSTANCE_ID` vem dele |
| `#343 F2 · a troca de principal invalida os snapshots` | `removeItem(SNAPSHOT_SCOPE_KEY)` uma vez | rotação **gera e publica**; um mecanismo, dois pontos de chamada |
| `#343 F2 · a rotação derruba o cache em memória` | `_escopoDeSnapshot = null` antes do `removeItem` | cache **substituído** antes de publicar |
| `#343 F5-B · o snapshot do Voltar continua carimbado` | mesma comparação literal | `escopoDoEstadoConfere()` |
| `PR3 A-4` | rotação DESCARTA e recai no documento | rotação **gera** — e a herança no F5 é modelada com um documento novo |

Nenhum gate foi removido, silenciado ou enfraquecido. O `PR3 A-4` merece nota:
ele travava explicitamente o mecanismo antigo (*"O mecanismo não é gerar um
escopo novo"*). Essa afirmação estava correta sobre o código de então e é
justamente o que esta fatia precisou mudar.

### Resultado

| Suíte | Antes | Depois |
|---|---:|---:|
| Gates JS | 356 | **366** |
| pytest (corporate) | 3 825 | **3 825** |
| pytest (app) | 3 820 | **3 820** |

---

## 4) Cobertura dos cenários exigidos

| Cenário | Gate |
|---|---|
| A → View X → logout → B → Back | `A-1` |
| Back/Forward legítimo dentro da sessão de A | `A-2` |
| state sem `sid` | `A-3` |
| state com `sid` atual | `A-2` |
| state com `sid` anterior | `A-1` |
| URL antiga com `?view=` | `A-4` |
| logout | `A-1` |
| sessão expirada | `A-1` — expiração chama `terminateSession()`, o mesmo caminho |
| troca de identidade sem encerramento | `A-8` |
| entrada inicial | `A-5`, `A-9` |

---

## 5) O que continua aberto

**PR B — telemetria.** `epi.analytics.master.events` é limpo quando o papel
deixa de ser master, mas um `master_admin` que entra depois de outro lê os
eventos do anterior. Medido na investigação, **não tratado aqui**.

**PR C — preferências pessoais.** `epi-theme`, `epi-density`,
`epi-sidebar-collapsed` e `epi_language` continuam DEVICE, e continuam vazando
entre usuários. É mudança de contrato de produto, com o problema do bootstrap
pré-paint, e não foi tocada nesta fatia.

**`epi_tenant`** segue sem classificação de escopo, deliberadamente fora das
três fatias.
