"""R0.5B — gates que protegem PRODUÇÃO.

Esta suíte não certifica nada. Ela garante as propriedades que precisam valer
depois que a medição de identidade fechou:

  R05B-1   o contrato dirige a existência da sonda, e inverte sozinho
  R05B-5   nenhum endereço real fica versionado nesta fatia
  R05B-6   nenhuma configuração de proxy é aplicada sem autorização
  R05B-7   o limitador não lê cabeçalho de identidade não certificado
  R05B-9   o procedimento registrado não expõe a chave em claro
  R05B-10  o valor de F não pode contradizer o registro do 403
  R05B-11  autorização de ativação não se herda de outro ambiente

`R05B-2`, `-3`, `-4` e `-8` verificavam a sonda temporária campo a campo. Ela
saiu do repositório no fechamento de 29/09, então eles saíram com ela — gate
que não tem sujeito é gate oco. As duas asserções do `-8` que falavam do
LIMITADOR, e não da sonda, foram preservadas no `-6`: é delas que depende a
classificação de D e E continuar verdadeira.

O certificador de ~1.550 linhas e os 62 gates que só o protegiam foram
removidos na simplificação de 24/09 — ver o histórico em
`docs/R05B_IDENTIDADE_DA_ORIGEM.md`.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / 'docs' / 'R05B_IDENTIDADE_DA_ORIGEM.md'
SONDA_MODULO = RAIZ / 'epi_backend' / 'proxy_identity_probe.py'
ROTAS = RAIZ / 'modules' / 'auth' / 'routes.py'
LIMITADOR = RAIZ / 'core' / 'rate_limit.py'
EXEMPLO_ENV = RAIZ / 'env.example'

#: Digesto do bloco de contrato. Mudar o contrato exige recalcular — o que
#: obriga a passar por aqui de propósito, e não por acidente de edição.
DIGESTO_CONTRATO = '7ff4ab1635b915e66b518082f5840dc136eb930db736c0c8223b784e1831d92d'

ESTADOS_VALIDOS = ('INDETERMINADO', 'DETERMINADA')

#: Vocabulário dos campos de propriedade do contrato. Antes não existia: os
#: campos eram texto livre que nenhum gate conferia, e `nao-medida` podia virar
#: qualquer coisa sem ninguém notar. Três valores é o menor conjunto COERENTE —
#: com dois, uma medição reprovada não teria como ser escrita e alguém
#: inventaria um valor em silêncio, que é o que este vocabulário existe para
#: impedir.
VALORES_DE_PROPRIEDADE = ('nao-medida', 'medida-aprovada', 'medida-reprovada')

#: Campos de propriedade DECISIVOS para o estado global. `F-CADEIA-LONGA` fica
#: fora de propósito: ela não é decisiva para a identidade, e `inconclusiva`
#: não é um valor que este vocabulário admita.
CAMPOS_DE_PROPRIEDADE = ('P1-IDENTIDADE', 'P2-DUAS-ORIGENS')

#: F tem vocabulário próprio porque o resultado dela foi INCONCLUSIVO — nem
#: aprovação nem reprovação. Forçá-la no vocabulário acima obrigaria a mentir
#: em um dos dois sentidos.
VALORES_DE_F = ('inconclusiva', 'medida-aprovada', 'medida-reprovada')

VALORES_DE_ATIVACAO = ('nao-autorizada', 'autorizada')

#: O ambiente em que a evidência de hoje foi obtida. A barreira do `R05B-11` é
#: escrita contra ESTE token: autorizar ativação sem trocá-lo é herdar a
#: autorização de um ambiente provisório, que é exatamente o que a decisão
#: normativa de 29/09 proibiu.
AMBIENTE_DA_MEDICAO_ATUAL = 'render-free-2026-09-26-corporate-e-saas'

#: Guarda de esquema do procedimento, verbatim. O gate confere que ela está no
#: documento E que ela se comporta — declarar sem executar provaria só que o
#: texto existe.
GUARDA_HTTPS = (
    'case "$BACKEND" in https://*) ;; '
    '*) echo "ABORTA: BACKEND precisa ser https://"; exit 1;; esac'
)

#: Fatos do controle `LONGA100` que o documento tem de continuar registrando.
#: Apagar qualquer um deles reescreveria o que a medição produziu; e é a
#: presença do segundo que trava o valor de F no `R05B-10`.
FATOS_DO_403 = (
    'HTTP 403 em 3/3 nos dois backends, sem corpo JSON',
    'Nenhum dos quatro campos exigidos foi observado',
    'não permite nomear',
    'não é status de tamanho',
    'o intervalo entre 2 e 99 elementos',
)

#: O registro de que o controle não produziu observação. Enquanto ele estiver
#: no documento, F não pode estar medida.
SEM_OBSERVACAO = 'Nenhum dos quatro campos exigidos foi observado'


def _texto() -> str:
    return CONTRATO.read_text(encoding='utf-8')


def _corrido() -> str:
    """Documento com espaço normalizado.

    O texto é quebrado em ~78 colunas, então frase procurada como substring
    literal atravessa quebra de linha e não casa. Mesma convenção do
    `test_r05_4d`.
    """
    return ' '.join(_texto().split())


def _bloco_do_contrato() -> str:
    achado = re.search(
        r'<!-- CONTRATO-R05B-INICIO -->\n(.*?)<!-- CONTRATO-R05B-FIM -->',
        _texto(), re.DOTALL)
    assert achado, 'o bloco de contrato sumiu do documento'
    return achado.group(1)


def _campo(nome: str) -> str:
    """Valor de um campo do bloco, ou '' se o campo estiver vazio.

    O espaço horizontal é casado com `[^\\S\\n]`, não com `\\s`: `\\s` atravessa
    a quebra de linha, então `CAMPO:` vazio capturaria o conteúdo da linha
    SEGUINTE e o gate de campo vazio nunca dispararia. A R0.5 já levou esse
    achado uma vez, em `EVIDENCIA:`.
    """
    achado = re.search(rf'^{nome}:[^\S\n]*(\S*)[^\S\n]*$',
                       _bloco_do_contrato(), re.MULTILINE)
    assert achado, f'o contrato não declara {nome}'
    return achado.group(1)


def _procedimento() -> str:
    """Só o bloco executável do procedimento.

    Asserção que varre o documento inteiro é satisfeita pela PROSA: a sabotagem
    que tirou `--proto` do comando deixou o gate verde porque o texto explicativo
    ainda citava a flag. Critério tem de olhar o que o operador executa.
    """
    texto = _texto()
    inicio = texto.index('## Procedimento de medição')
    bloco = re.search(r'```bash\n(.*?)```', texto[inicio:], re.DOTALL)
    assert bloco, 'o bloco executável do procedimento sumiu'
    return bloco.group(1)


def _estado() -> str:
    return _campo('ESTADO-DA-IDENTIDADE')


# ── R05B-1 ──────────────────────────────────────────────────────────────────
def test_r05b_1_o_contrato_dirige_a_existencia_da_sonda():
    """O contrato é a chave: o gate inverte junto com ele, sem edição.

    INDETERMINADO → a sonda pode existir.
    DETERMINADA   → sonda e rota são proibidas, e o fechamento exige que cada
                    propriedade decisiva esteja aprovada E que o ambiente da
                    evidência esteja nomeado.
    """
    bloco = _bloco_do_contrato()
    estado = _estado()
    assert estado in ESTADOS_VALIDOS, f'estado fora do vocabulário: {estado}'

    # Vocabulário fechado em todos os campos. Sem isto, `P1-IDENTIDADE`
    # aceitaria qualquer texto e o contrato deixaria de ser legível por máquina
    # exatamente onde ele afirma o que foi medido.
    propriedades = {c: _campo(c) for c in CAMPOS_DE_PROPRIEDADE}
    for campo, valor in propriedades.items():
        assert valor in VALORES_DE_PROPRIEDADE, (
            f'{campo} fora do vocabulário: {valor!r}'
        )
    assert _campo('F-CADEIA-LONGA') in VALORES_DE_F, (
        f"F-CADEIA-LONGA fora do vocabulário: {_campo('F-CADEIA-LONGA')!r}"
    )
    assert _campo('ATIVACAO-HOPS') in VALORES_DE_ATIVACAO, (
        f"ATIVACAO-HOPS fora do vocabulário: {_campo('ATIVACAO-HOPS')!r}"
    )

    if estado == 'DETERMINADA':
        # INVARIANTE DE FECHAMENTO. Pertencer ao vocabulário não basta:
        # `DETERMINADA` com uma propriedade `medida-reprovada` ou `nao-medida`
        # passava por válido, e o CI endossaria um fechamento que a evidência
        # não sustenta. Este buraco nasceu junto com o vocabulário de três
        # valores, e foi fechado no hotfix de 28/09.
        reprovadas = {c: v for c, v in propriedades.items()
                      if v != 'medida-aprovada'}
        assert not reprovadas, (
            f'contrato DETERMINADA com propriedade que não foi aprovada: '
            f'{reprovadas}. O estado global só fecha quando cada propriedade '
            f'decisiva estiver em medida-aprovada'
        )

        # VÍNCULO DE AMBIENTE. Identidade medida é medida EM ALGUM LUGAR.
        # Fechamento sem o ambiente nomeado é uma afirmação sem escopo, e é
        # dela que a barreira do `R05B-11` depende para saber o que não pode
        # ser herdado.
        ambiente = _campo('AMBIENTE-DA-EVIDENCIA')
        assert ambiente, (
            'contrato DETERMINADA sem AMBIENTE-DA-EVIDENCIA. Evidência sem '
            'ambiente nomeado não delimita onde ela vale, e a barreira de '
            'ativação não tem contra o que comparar'
        )

    atual = hashlib.sha256(bloco.encode('utf-8')).hexdigest()
    assert atual == DIGESTO_CONTRATO, (
        'o bloco de contrato mudou sem que o digesto fosse recalculado — '
        'mudar o estado da identidade ou a autorização tem de ser deliberado'
    )

    rotas = ROTAS.read_text(encoding='utf-8')
    if estado == 'DETERMINADA':
        assert not SONDA_MODULO.exists(), 'a sonda ficou depois do fechamento'
        assert 'origin-identity-diagnostics' not in rotas, 'a rota ficou'
        assert 'proxy_identity_probe' not in rotas, 'o import ficou'
        # A ausência de leitores da chave é do `R05-6`, que varre o
        # repositório inteiro com o nome literal da variável.
    else:
        assert SONDA_MODULO.exists(), 'contrato aberto e sonda ausente'
        assert 'origin-identity-diagnostics' in rotas, \
            'contrato aberto e rota ausente'


# ── R05B-5 ──────────────────────────────────────────────────────────────────
FAIXAS_SEGURAS = (
    '192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24',
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10',
    '127.0.0.0/8', '0.0.0.0/8', '169.254.0.0/16', '224.0.0.0/4', '240.0.0.0/4',
    '2001:db8::/32', 'fc00::/7', 'fe80::/10', 'ff00::/8', '100::/64',
)
_TOKEN = re.compile(r'[0-9A-Fa-f:][0-9A-Fa-f.:]*')


def _enderecos(texto: str) -> list:
    achados = []
    for bruto in _TOKEN.findall(texto):
        candidato = bruto
        while candidato:
            try:
                achados.append(ipaddress.ip_address(candidato))
                break
            except ValueError:
                candidato = candidato[:-1]
    return achados


def _seguro(endereco, faixas) -> bool:
    """Toda forma IPv6 que EMBUTE um IPv4 é julgada por esse IPv4."""
    if endereco.version == 6 and int(endereco) < 2 ** 32:
        endereco = ipaddress.ip_address(int(endereco))
    elif getattr(endereco, 'ipv4_mapped', None) is not None:
        endereco = endereco.ipv4_mapped
    return any(endereco in f for f in faixas if f.version == endereco.version)


def test_r05b_5_nenhum_endereco_real_na_fatia():
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    alvos = [CONTRATO, Path(__file__)] + [p for p in (SONDA_MODULO,) if p.exists()]
    for caminho in alvos:
        for endereco in _enderecos(caminho.read_text(encoding='utf-8')):
            # A mensagem NÃO ecoa o endereço: o gate existe para impedir que
            # endereço real seja gravado, e não pode publicá-lo no log do CI.
            assert _seguro(endereco, faixas), (
                f'{caminho.name} tem um endereço IPv{endereco.version} fora '
                'das faixas reservadas'
            )


def test_r05b_5b_a_varredura_enxerga_as_duas_familias():
    """Meta-gate: varredura IPv4-only deixaria o gate acima verde com um IPv6
    real dentro do arquivo. Os endereços de prova vêm de inteiros, senão o
    próprio `R05B-5` os pegaria."""
    faixas = [ipaddress.ip_network(f) for f in FAIXAS_SEGURAS]
    for real in (ipaddress.ip_address((0x2a01 << 112) | 1),
                 ipaddress.ip_address(0x60606060)):
        achados = _enderecos(f'a borda respondeu de {real}.')
        assert real in achados, f'a varredura não enxergou IPv{real.version}'
        assert not _seguro(real, faixas), 'endereço real passou por reservado'
    for reservado in ('192.0.2.1', '2001:db8::1', '::ffff:192.0.2.1'):
        assert _seguro(ipaddress.ip_address(reservado), faixas)


# ── R05B-6 ──────────────────────────────────────────────────────────────────
def test_r05b_6_nenhuma_configuracao_de_proxy_sem_autorizacao():
    """`HOPS` fica em 0 no modelo genérico, e o padrão do limitador é 0.

    As duas últimas asserções vinham do `R05B-8`, que media a sonda. Elas não
    falam da sonda: fixam que o limitador lê a PRIMEIRA instância do cabeçalho
    e usa a string CRUA de `cadeia[-N]` como chave de balde. São as duas
    premissas da classificação de D e E no documento — se o limitador mudar
    qualquer uma, aquela classificação para de valer em silêncio.
    """
    linhas = [l.strip() for l in EXEMPLO_ENV.read_text(encoding='utf-8').splitlines()
              if l.strip().startswith('RATE_LIMIT_TRUSTED_PROXY_HOPS')]
    assert linhas, 'o modelo de ambiente parou de declarar a variável'
    for linha in linhas:
        assert linha.split('=', 1)[1].strip().strip('"\'') == '0', (
            f'o modelo genérico carrega valor topológico: {linha!r}'
        )

    # E o padrão do próprio limitador é 0 — ausência de configuração não pode
    # significar confiar no cabeçalho.
    fonte = LIMITADOR.read_text(encoding='utf-8')
    assert "os.environ.get('RATE_LIMIT_TRUSTED_PROXY_HOPS', '0')" in fonte
    assert 'if TRUSTED_PROXY_HOPS <= 0:' in fonte, (
        'o limitador deixou de tratar 0 como "ignore o cabeçalho"'
    )

    assert "handler.headers.get('X-Forwarded-For', '')" in fonte, (
        'o limitador mudou a forma de ler o cabeçalho; a classificação de D no '
        'documento depende de ele ler só a PRIMEIRA instância'
    )
    assert 'return cadeia[-TRUSTED_PROXY_HOPS]' in fonte, (
        'o limitador deixou de usar a string crua de cadeia[-N] como chave; a '
        'classificação de E no documento depende disso'
    )


# ── R05B-7 ──────────────────────────────────────────────────────────────────
def test_r05b_7_o_limitador_nao_le_cabecalho_nao_certificado():
    """`CF-Connecting-IP`, `True-Client-IP` e `X-Real-IP` não foram medidos.

    Enquanto não forem, o limitador não pode lê-los: seriam identidade escolhida
    pelo cliente entrando na chave de balde por outra porta.
    """
    fonte = LIMITADOR.read_text(encoding='utf-8').lower()
    for nome in ('cf-connecting-ip', 'cf_connecting_ip', 'true-client-ip',
                 'true_client_ip', 'x-real-ip', 'x_real_ip', 'forwarded ='):
        assert nome not in fonte, f'o limitador passou a ler {nome!r}'


# ── R05B-9 ──────────────────────────────────────────────────────────────────
def test_r05b_9_o_procedimento_exige_https_antes_da_chave():
    """A chave de diagnóstico não pode sair em claro.

    O procedimento ficou no documento como registro histórico e como base de
    uma remedição futura. Enquanto esse texto existir, ele não pode voltar a
    ser um comando que manda a chave sem `https`: a guarda que ABORTA antes de
    qualquer requisição e `--proto '=https'`, que impede o curl de cair em http
    por redirecionamento.
    """
    comandos = _procedimento()
    assert GUARDA_HTTPS in comandos, (
        'o procedimento perdeu a guarda de esquema: com `BACKEND` em http:// a '
        'chave sairia em claro antes de qualquer verificação'
    )
    assert "--proto '=https'" in comandos, (
        'sem `--proto`, um redirecionamento 30x para http levaria o cabeçalho '
        'com a chave junto'
    )

    # E a guarda FUNCIONA: aceita https, aborta em http — antes de enviar nada.
    for url, esperado in (('https://exemplo.invalid', 0), ('http://exemplo.invalid', 1),
                          ('ftp://exemplo.invalid', 1), ('exemplo.invalid', 1)):
        r = subprocess.run(['bash', '-c', f'BACKEND={url}\n{GUARDA_HTTPS}\nexit 0'],
                           capture_output=True, text=True)
        assert r.returncode == esperado, (
            f'a guarda devolveu {r.returncode} para {url!r}, esperado {esperado}'
        )
        if esperado:
            assert 'ABORTA' in (r.stdout + r.stderr)


def test_r05b_9b_o_criterio_de_aceitacao_cobre_o_campo_do_balde():
    """`candidato_ja_canonico` foi medido em todas as observações, mas ficou
    fora da tabela de aceitação — e é ele que diz se a chave de balde do
    limitador é a forma canônica. Critério que não o exige aceita uma borda que
    escreve canônico nas amostras curtas e expandido na longa."""
    tabela = _texto()
    inicio = tabela.index('Os dois controles com `N=3` exigem, campo a campo:')
    fim = tabela.index('> **Limitação registrada.**')
    assert '`candidato_ja_canonico`' in tabela[inicio:fim], (
        'a tabela de aceitação dos dois controles não exige '
        '`candidato_ja_canonico`, que é o campo que o limitador usa como chave'
    )


# ── R05B-10 ─────────────────────────────────────────────────────────────────
def test_r05b_10_o_valor_de_f_nao_contradiz_o_registro_do_403():
    """F não pode virar aprovada por edição de campo.

    O controle `LONGA100` devolveu 403 sem corpo: nenhum dos quatro campos
    exigidos foi observado. Enquanto esse registro estiver no documento,
    `F-CADEIA-LONGA` medida seria uma afirmação contra a própria evidência
    registrada ao lado.

    Duas travas, de propósito: os fatos do 403 têm de continuar escritos, e o
    valor de F tem de concordar com eles. Apagar o registro para liberar o
    campo derruba a primeira; mudar só o campo derruba a segunda.
    """
    corrido = _corrido()
    for fato in FATOS_DO_403:
        assert fato in corrido, (
            f'sumiu do documento um fato do controle LONGA100: {fato!r}. O '
            'resultado 403 é histórico e não se reescreve'
        )

    if _campo('F-CADEIA-LONGA') != 'inconclusiva':
        assert SEM_OBSERVACAO not in corrido, (
            f"F-CADEIA-LONGA está {_campo('F-CADEIA-LONGA')!r} e o documento "
            f'continua registrando {SEM_OBSERVACAO!r}. Um dos dois é falso: '
            'F só sai de inconclusiva com observação que hoje não existe'
        )


# ── R05B-11 ─────────────────────────────────────────────────────────────────
def test_r05b_11_a_autorizacao_de_ativacao_nao_se_herda():
    """A barreira da decisão B.

    Medir a identidade no Render Free não autoriza ligar
    `RATE_LIMIT_TRUSTED_PROXY_HOPS` no ambiente definitivo: a R0.5 já registra
    que mudança de plano ou região invalida o número em silêncio, e para pior —
    ele passa a apontar para dentro do território que o cliente escreve.

    Este gate NÃO proíbe `HOPS > 0` para sempre, que seria bloqueio permanente
    por construção. Ele proíbe autorizar com a evidência de OUTRO ambiente:
    `autorizada` exige um `AMBIENTE-DA-EVIDENCIA` diferente do atual, e trocar
    esse token passa pelo digesto do bloco. Uma revalidação no ambiente
    definitivo escreve o ambiente novo e o gate abre.

    A metade que olha as superfícies de deployment — `render.yaml` e
    `env.example` — é do `R05-3`, que já tem o parser das duas formas de
    declaração.
    """
    ativacao = _campo('ATIVACAO-HOPS')
    if ativacao != 'autorizada':
        return

    ambiente = _campo('AMBIENTE-DA-EVIDENCIA')
    assert ambiente != AMBIENTE_DA_MEDICAO_ATUAL, (
        f'ATIVACAO-HOPS: autorizada com AMBIENTE-DA-EVIDENCIA={ambiente!r}, '
        'que é a medição do Render Free. Autorização herdada de outro '
        'ambiente é exatamente o que a decisão normativa de 29/09 proibiu: '
        'revalide no ambiente definitivo e escreva o ambiente novo'
    )
