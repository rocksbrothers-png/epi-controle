"""R0.5 — o que protege o comportamento de HOJE.

`RATE_LIMIT_TRUSTED_PROXY_HOPS = 0` é a única configuração suportada nesta
fatia. Com `0`, `core/rate_limit.py` devolve o peer do socket e ignora
`X-Forwarded-For` por completo: dez linhas do algoritmo não executam. Quem
prova o COMPORTAMENTO do limitador é `tests/test_r0_origem_do_rate_limit.py`,
com quinze gates que exercitam a função real. Esta suíte não repete isso.

Oito gates, um por propriedade:

  R05-1  a configuração versionada declara 0
  R05-2  sem configuração, ou com lixo, o padrão continua 0
  R05-3  o limitador é idêntico nos dois repositórios
  R05-4  o limitador não lê cabeçalho de identidade não certificado
  R05-5  a instrumentação temporária não está no repositório
  R05-6  os documentos são registro histórico, não autorização
  R05-7  nenhum endereço real ficou nos documentos
  R05-7b a varredura de endereços enxerga IPv4 e IPv6, colados ou não

## Por que esta suíte encolheu de 29 gates para 8

As versões anteriores construíram uma máquina de estados executável — onze
campos de contrato, seis invariantes de transição, vinte e quatro sabotagens —
cuja única finalidade era permitir e depois bloquear uma transição para
`HOPS > 0`. Nenhum arquivo de runtime lia qualquer um desses campos.

Três rodadas de revisão automatizada produziram quatorze achados; nove estavam
dentro dessa máquina, protegendo uma configuração que esta PR não ativa. O
último deles observou que o gate de evidência aceitava uma amostra finita para
aprovar uma propriedade que o próprio documento define como universal — o mesmo
regresso infinito que já havia produzido um certificador de 7.334 linhas, agora
reproduzido dentro do mecanismo criado para impedi-lo.

A decisão foi retirar a máquina em vez de continuar corrigindo-a. Ativar
`HOPS > 0` passa a exigir outra PR, no ambiente definitivo, com medição própria.
Os fatos medidos no Render Free continuam registrados nos documentos, como
história — o `R05-6` trava cada um deles.
"""

import hashlib
import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOC_R05 = RAIZ / 'docs' / 'R05_CADEIA_DE_PROXY.md'
DOC_R05B = RAIZ / 'docs' / 'R05B_IDENTIDADE_DA_ORIGEM.md'
ENV_EXEMPLO = RAIZ / 'env.example'
RENDER = RAIZ / 'render.yaml'
LIMITADOR = RAIZ / 'core' / 'rate_limit.py'

VARIAVEL = 'RATE_LIMIT_TRUSTED_PROXY_HOPS'

#: Digesto de `core/rate_limit.py`. Os dois repositórios carregam a MESMA
#: constante: quem mexer no limitador de um lado só deixa aquele lado vermelho.
#: Limitação honesta — pega edição unilateral, não pega os dois editando igual e
#: errado ao mesmo tempo.
DIGESTO_LIMITADOR = 'aab6c8acb2212232c3558887eac85f8061033e323baeb7ee59592a9903f0237e'


# ── R05-1: a configuração versionada declara 0 ──────────────────────────────

def _valores_declarados(texto: str) -> list:
    """Extrai os valores da variável nas DUAS formas.

    `env.example` usa `VARIAVEL=0`. O `render.yaml` usa a estrutura de lista que
    o blueprint da Render consome:

        - key: RATE_LIMIT_TRUSTED_PROXY_HOPS
          value: "0"

    Procurar a variável e um número na MESMA linha reprovaria a declaração
    correta do blueprint — e empurraria quem tentasse satisfazer o gate a
    escrever um mapeamento inline que a Render não lê.
    """
    valores = []
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        casou = re.match(rf'\s*{VARIAVEL}\s*=\s*"?(\d+)"?\s*$', linha)
        if casou:
            valores.append(casou.group(1))
            continue
        if not re.search(rf'key:\s*{VARIAVEL}\s*$', linha):
            continue
        for seguinte in linhas[i + 1:]:
            if re.match(r'\s*-\s', seguinte):
                break  # começou outra entrada de envVars sem declarar valor
            casou = re.match(r'\s*value:\s*"?(\d+)"?\s*$', seguinte)
            if casou:
                valores.append(casou.group(1))
                break
    return valores


def test_r05_1_a_configuracao_versionada_declara_zero():
    """Owner único da configuração de deployment.

    As duas superfícies declaram `0`, e declaram — não omitem. Omitir parece
    equivalente, porque o padrão do limitador também é `0`, mas não é: um valor
    posto à mão no painel do Render SOBREVIVE a uma sincronização de blueprint
    que não menciona a variável. Declarar `0` sobrescreve esse valor. É a única
    alavanca que o repositório tem sobre o painel, e por isso é deliberada.

    `env.example` é o caso mais perigoso dos dois: `spec/09-deployment.md:112`
    manda `cp env.example .env`, e `app.py` importa `epi_backend.config` — que
    chama `load_dotenv()` — ANTES de importar `core.rate_limit`. Num ambiente
    sem proxy, um valor positivo aqui deixa o cliente completar a cadeia até o
    comprimento exigido e receber `cadeia[-N]`, que foi ele quem escreveu.
    Baldes ilimitados: exatamente o defeito que a R0 fechou.
    """
    for caminho in (ENV_EXEMPLO, RENDER):
        assert caminho.exists(), f'{caminho.name} sumiu'
        valores = _valores_declarados(caminho.read_text(encoding='utf-8'))
        assert valores, (
            f'{caminho.name} não declara {VARIAVEL}. Omitir não é fail-closed: '
            'um valor posto no painel sobrevive à sincronização do blueprint'
        )
        for valor in valores:
            assert valor == '0', (
                f'{caminho.name} declara {VARIAVEL}={valor}. Esta fatia suporta '
                'apenas 0; ativar um valor positivo exige outra PR, no ambiente '
                'definitivo, com medição daquele ambiente'
            )


# ── R05-2: sem configuração, ou com lixo, o padrão continua 0 ───────────────

def _hops_com_ambiente(valor):
    """Import limpo em processo separado. `importlib.reload` aqui dentro criaria
    limitadores novos enquanto `modules/auth/routes.py` continuaria apontando
    para os antigos — efeito colateral silencioso sobre estado global."""
    ambiente = {k: v for k, v in os.environ.items() if k != VARIAVEL}
    if valor is not None:
        ambiente[VARIAVEL] = valor
    ambiente['PYTHONPATH'] = str(RAIZ)
    return subprocess.run(
        [sys.executable, '-c',
         'import core.rate_limit as RL; print(RL.TRUSTED_PROXY_HOPS)'],
        capture_output=True, text=True, env=ambiente, cwd=str(RAIZ),
        timeout=60, check=False)


def test_r05_2_sem_configuracao_ou_com_lixo_o_padrao_e_zero():
    """O INICIALIZADOR, que os gates comportamentais da R0 não enxergam: eles
    forçam `RL.TRUSTED_PROXY_HOPS` antes de exercitar a função, então nunca
    passam pela linha que lê o ambiente. Trocar o default de `'0'` para um
    número positivo faria toda implantação não configurada confiar no cabeçalho
    do cliente, e passaria por aquela suíte inteira."""
    saida = _hops_com_ambiente(None)
    assert saida.returncode == 0, f'import limpo falhou: {saida.stderr}'
    assert saida.stdout.strip() == '0', (
        f'sem {VARIAVEL} no ambiente o padrão virou {saida.stdout.strip()!r} — '
        'implantação não configurada passaria a confiar no cabeçalho do cliente'
    )

    for invalido in ('', '-5', '-1'):
        saida = _hops_com_ambiente(invalido)
        assert saida.returncode == 0, f'{invalido!r} quebrou o import: {saida.stderr}'
        assert saida.stdout.strip() == '0', (
            f'{VARIAVEL}={invalido!r} virou {saida.stdout.strip()!r} em vez de 0'
        )

    # Não numérico: o processo NÃO sobe. Falha barulhenta e reversível, em vez
    # de silenciosa — e nunca uma confiança que ninguém pediu.
    saida = _hops_com_ambiente('abc')
    assert saida.returncode != 0, (
        f'{VARIAVEL}=abc não derrubou o import; a aplicação subiria com uma '
        'configuração que ninguém consegue ler'
    )
    assert 'ValueError' in saida.stderr


# ── R05-3: o limitador é idêntico nos dois repositórios ─────────────────────

def test_r05_3_o_limitador_e_identico_nos_dois_repositorios():
    """Corporate e SaaS rodam o mesmo algoritmo de origem. Se um lado mexer no
    limitador e o outro não, os dois produtos passam a decidir bucket de formas
    diferentes — e nenhum teste local de cada repositório notaria."""
    atual = hashlib.sha256(LIMITADOR.read_bytes()).hexdigest()
    assert atual == DIGESTO_LIMITADOR, (
        'core/rate_limit.py mudou sem o digesto ser recalculado, ou divergiu '
        'entre os repositórios. Esta fatia não altera o limitador'
    )


# ── R05-4: o limitador não lê cabeçalho não certificado ─────────────────────

#: Acesso ao cabeçalho `Forwarded` (RFC 7239). Casa a FORMA DE ACESSO, não o
#: nome solto: `x-forwarded-for` é leitura legítima e está no limitador, então
#: proibir a palavra reprovaria o uso correto.
ACESSO_AO_FORWARDED = re.compile(r"""(?:\.get\(|\[)\s*['"]forwarded['"]""")


def test_r05_4_o_limitador_nao_le_cabecalho_nao_certificado():
    """`CF-Connecting-IP`, `True-Client-IP`, `X-Real-IP` e `Forwarded` nunca
    foram medidos nesta borda. Enquanto não forem, o limitador não pode lê-los:
    seriam identidade escolhida pelo cliente entrando na chave de balde por
    outra porta, contornando o `0` sem que nada mais mudasse."""
    fonte = LIMITADOR.read_text(encoding='utf-8').lower()
    for nome in ('cf-connecting-ip', 'cf_connecting_ip', 'true-client-ip',
                 'true_client_ip', 'x-real-ip', 'x_real_ip'):
        assert nome not in fonte, f'o limitador passou a ler {nome!r}'

    achado = ACESSO_AO_FORWARDED.search(fonte)
    assert not achado, (
        f'o limitador passou a ler o cabeçalho `Forwarded` ({achado.group(0)!r}) '
        'da RFC 7239, que não foi medido e o cliente pode escrever'
    )


# ── R05-5: a instrumentação temporária não está no repositório ──────────────

#: Superfícies das duas sondas temporárias — a da R0.5 e a da R0.5B. Ambas
#: cumpriram a função e saíram. Qualquer uma de volta é diagnóstico virando API.
RASTROS_DA_INSTRUMENTACAO = (
    'proxy_chain_probe',
    'proxy-chain-diagnostics',
    'proxy_identity_probe',
    'origin-identity-diagnostics',
    'PROXY_CHAIN_PROBE_KEY',
    'certificar_cadeia_de_proxy',
    'certificar_identidade_da_origem',
)


def test_r05_5_a_instrumentacao_temporaria_nao_esta_no_repositorio():
    """Varredura do repositório INTEIRO, não de um arquivo.

    A versão anterior deste gate lia só `modules/auth/routes.py`. O projeto tem
    vinte e oito módulos com `register_routes`, todos importados por `app.py`:
    o handler podia reaparecer em qualquer um dos outros vinte e sete e o gate
    passaria. Achado de revisão, e o motivo de a varredura ser repo-wide.

    Cobre as três superfícies de uma vez — módulo, rota e chave — porque são uma
    responsabilidade só: a instrumentação saiu.
    """
    sobreviventes = {}
    for caminho in RAIZ.rglob('*'):
        if not caminho.is_file() or caminho.suffix not in ('.py', '.yaml', '.yml', '.js'):
            continue
        if '__pycache__' in caminho.parts or '.git' in caminho.parts:
            continue
        if caminho == Path(__file__):
            continue  # nomear para proibir não é depender
        texto = caminho.read_text(encoding='utf-8', errors='replace')
        achados = [r for r in RASTROS_DA_INSTRUMENTACAO if r in texto]
        if achados:
            sobreviventes[str(caminho.relative_to(RAIZ)).replace('\\', '/')] = achados

    assert not sobreviventes, (
        f'a instrumentação temporária voltou: {sobreviventes}. Ela era '
        'temporária por contrato — a rota é um oráculo de igualdade protegido '
        'por uma chave que sai do painel'
    )


# ── R05-6: os documentos são registro histórico, não autorização ────────────

#: Fatos que os documentos têm de continuar afirmando. Alterar qualquer um deles
#: muda a interpretação de segurança da fatia — por isso são travados, e só
#: eles. O resto do texto é livre.
FATOS_HISTORICOS = {
    DOC_R05: (
        'a borda contribui com 3 elementos',
        'a contribuição não varia com o que o cliente envia',
        'a borda ANEXA: acrescenta à direita sem apagar o que veio',
        'medição de 2026-09-22, no plano Free do Render',
        'Uma origem mede um caminho',
    ),
    DOC_R05B: (
        'P1 — identidade: medida e aprovada',
        'P2 — duas origens: medida e aprovada',
        'o procedimento não verificava que as duas origens eram distintas',
        'HTTP 403 em 3/3 nos dois backends, sem corpo JSON',
        'a evidência não permite nomear a camada',
        '403 não é status de tamanho',
        'LONGA100 é um ponto amostral e não prova F',
        'F permanece INCONCLUSIVA',
        'o plano Free do Render não certifica o ambiente definitivo',
    ),
}

#: A afirmação que separa história de autorização. Tem de estar nos DOIS
#: documentos: quem ler um só não pode concluir que a medição autoriza.
NAO_AUTORIZA = 'Esta PR não autoriza RATE_LIMIT_TRUSTED_PROXY_HOPS > 0'

#: Vocabulário de contrato executável. Estes marcadores faziam os documentos
#: serem lidos por máquina para decidir uma transição de autorização. A máquina
#: saiu; se voltarem, voltou com ela.
MAQUINA_REMOVIDA = (
    'CONTRATO-R05-INICIO',
    'CONTRATO-R05B-INICIO',
    'ATIVACAO-HOPS',
    'ESTADO-DA-IDENTIDADE',
    'AMBIENTE-DA-EVIDENCIA',
)


def _corrido(caminho) -> str:
    """Texto com espaço normalizado: o documento é quebrado em ~78 colunas, e
    frase procurada como substring literal atravessa quebra de linha e não casa.
    """
    return ' '.join(caminho.read_text(encoding='utf-8').split())


def test_r05_6_os_documentos_sao_registro_historico_nao_autorizacao():
    """O gate documental mínimo, e o que ele trava.

    Os dois documentos deixaram de ser contrato executável. Eles registram o que
    foi medido no Render Free, em 2026-09-22 e 2026-09-26, e registram o que a
    medição NÃO estabelece. Nenhuma máquina lê esses fatos; um humano lê.

    Três coisas, e só três:

    - os fatos essenciais continuam escritos, porque apagá-los mudaria a
      interpretação de segurança da fatia;
    - os dois documentos afirmam que esta PR não autoriza `HOPS > 0`;
    - o vocabulário da máquina de autorização não volta.
    """
    for caminho, fatos in FATOS_HISTORICOS.items():
        assert caminho.exists(), f'{caminho.name} sumiu'
        corrido = _corrido(caminho)
        for fato in fatos:
            assert fato in corrido, (
                f'sumiu de {caminho.name} um fato da medição: {fato!r}. '
                'A investigação do Render Free é registro histórico e não se '
                'reescreve'
            )
        assert NAO_AUTORIZA in corrido, (
            f'{caminho.name} não afirma {NAO_AUTORIZA!r}. Sem isso, quem ler só '
            'este documento pode concluir que a medição autoriza a ativação'
        )
        for marcador in MAQUINA_REMOVIDA:
            assert marcador not in corrido, (
                f'{caminho.name} voltou a trazer {marcador!r}, que é vocabulário '
                'da máquina de autorização removida. Ativar HOPS > 0 é assunto '
                'de outra PR, no ambiente definitivo'
            )


# ── R05-7: nenhum endereço real nos documentos ──────────────────────────────

FAIXAS_SEGURAS = (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10',
    '127.0.0.0/8', '0.0.0.0/8', '169.254.0.0/16', '224.0.0.0/4', '240.0.0.0/4',
    '2001:db8::/32', 'fc00::/7', 'fe80::/10', 'ff00::/8', '100::/64',
)
_TOKEN = re.compile(r'[0-9A-Fa-f:][0-9A-Fa-f.:]*')
_SEPARADOR = re.compile(r'[:.]')


def _endereco_no_inicio(candidato: str):
    """O maior prefixo de `candidato` que é um endereço, ou `None`."""
    while candidato:
        try:
            return ipaddress.ip_address(candidato)
        except ValueError:
            candidato = candidato[:-1]
    return None


def _enderecos(texto: str) -> list:
    """O token é uma corrida de caracteres de endereço, e não sabe onde o
    endereço começa: `origem:<ip>` entrega o token `:<ip>`, e `fonte:<ip>` ou
    `IPv4:<ip>` entregam `e:<ip>` e `4:<ip>`, porque o rótulo termina em dígito
    hexadecimal. Aparar só da direita nunca chegava ao endereço.

    Só quando NENHUM prefixo do token é endereço o início avança para depois do
    próximo separador. Token que já rendia endereço rende o mesmo de antes, e um
    endereço que casou nunca é relido a partir do meio."""
    achados = []
    for bruto in _TOKEN.findall(texto):
        inicio = 0
        while inicio < len(bruto):
            endereco = _endereco_no_inicio(bruto[inicio:])
            if endereco is not None:
                achados.append(endereco)
                break
            separador = _SEPARADOR.search(bruto, inicio)
            if separador is None:
                break
            inicio = separador.end()
    return achados


def _seguro(endereco, faixas) -> bool:
    """Toda forma IPv6 que EMBUTE um IPv4 é julgada por esse IPv4."""
    if endereco.version == 6 and int(endereco) < 2 ** 32:
        endereco = ipaddress.ip_address(int(endereco))
    elif getattr(endereco, 'ipv4_mapped', None) is not None:
        endereco = endereco.ipv4_mapped
    return any(endereco in f for f in faixas if f.version == endereco.version)


def test_r05_7_nenhum_endereco_real_nos_documentos():
    """As medições foram feitas de origens públicas reais. Os documentos contam
    o que foi observado sem jamais gravar de onde — só sentinelas de
    documentação e faixas reservadas.

    Havia dois scanners: um IPv4-only sobre o documento da R0.5 e este, que
    enxerga as duas famílias, sobre o da R0.5B. Um IPv6 real no primeiro passava
    pelos dois. Ficou um scanner, sobre os dois documentos.
    """
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    for caminho in (DOC_R05, DOC_R05B, Path(__file__)):
        for endereco in _enderecos(caminho.read_text(encoding='utf-8')):
            # A mensagem NÃO ecoa o endereço: o gate existe para impedir que
            # endereço real seja gravado, e não pode publicá-lo no log do CI.
            assert _seguro(endereco, faixas), (
                f'{caminho.name} tem um endereço IPv{endereco.version} fora das '
                'faixas reservadas'
            )


#: Contextos em que o endereço chega colado ao que vem antes — o que a varredura
#: perdia: `:` logo antes do endereço, e rótulo que termina em dígito
#: hexadecimal (`fonte`, `IPv4`) grudado ao token.
CONTEXTOS_COLADOS = (
    'origem:{}', 'ip:{}', 'fonte:{}', 'IPv4:{}', 'X-Forwarded-For:{}',
    '| origem | {} |', '| ip:{} |', '(origem:{})',
)

#: Texto corrente com `:` e sem endereço nenhum.
PROSA_SEM_ENDERECO = (
    'Status: pronto; horário 12:30; razão 3:1; proporção 16:9; chave:valor.',
    'X-Forwarded-For: lista de origens; Forwarded: for=, by=; Via: 1.1 borda.',
    'dead:beef, fe:ed:fa:ce e aa:bb:cc:dd:ee:ff não são endereços.',
)


def test_r05_7b_a_varredura_enxerga_as_duas_familias():
    """Meta-gate, e ele se paga: uma varredura IPv4-only deixa o gate acima
    verde com um IPv6 real dentro do arquivo, que foi exatamente o defeito do
    scanner anterior. Uma que só apara o token pela direita deixa passar o
    endereço colado a `:`, que foi o segundo. Os endereços de prova vêm de
    inteiros, senão o próprio `R05-7` os pegaria aqui.

    Nos contextos colados, o critério é o do `R05-7`: algum achado FORA das
    faixas reservadas. Não é igualdade com o endereço escrito, porque um IPv6
    colado a rótulo terminado em hexadecimal é lido como um vizinho, com o
    dígito do rótulo na frente — igualmente global, igualmente vermelho."""
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    for real in (ipaddress.ip_address((0x2a01 << 112) | 1),
                 ipaddress.ip_address(0x60606060)):
        achados = _enderecos(f'a borda respondeu de {real}.')
        assert real in achados, f'a varredura não enxergou IPv{real.version}'
        assert not _seguro(real, faixas), 'endereço real passou por reservado'
        for contexto in CONTEXTOS_COLADOS:
            achados = _enderecos(contexto.format(real))
            assert any(not _seguro(a, faixas) for a in achados), (
                f'a varredura perdeu um IPv{real.version} real no contexto '
                f'{contexto!r}'
            )
    for reservado in ('192.0.2.1', '2001:db8::1', '::ffff:192.0.2.1'):
        assert _seguro(ipaddress.ip_address(reservado), faixas)
    # Faixa documental colada continua aceita. O IPv6 documental fica de fora
    # dos rótulos que terminam em hexadecimal: ali ele sempre foi lido como um
    # vizinho e reprovado — fail-closed, e inalterado por esta correção.
    for contexto in CONTEXTOS_COLADOS:
        for achado in _enderecos(contexto.format('192.0.2.1')):
            assert _seguro(achado, faixas), f'192.0.2.1 reprovado em {contexto!r}'
    for contexto in ('origem:{}', 'ip:{}', '| origem | {} |', '(origem:{})'):
        for achado in _enderecos(contexto.format('2001:db8::1')):
            assert _seguro(achado, faixas), f'2001:db8::1 reprovado em {contexto!r}'
    for prosa in PROSA_SEM_ENDERECO:
        assert _enderecos(prosa) == [], 'texto sem endereço virou endereço'
