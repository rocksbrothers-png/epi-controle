"""#343 F3 — D1 e D2 corrigidos; o escopo DEVICE valeu até o Isolamento PR C.

## A decisão de produto ORIGINAL, e a que a substituiu

O escopo por dispositivo/instalação NÃO era vazamento acidental: estava
declarado no código do Web Legado ("Persistência por dispositivo (localStorage)")
e prometido ao usuário na própria UI ("As preferências são salvas neste
dispositivo."). Esta fatia PRESERVOU esse contrato, e registrou que mudá-lo
seria decisão de produto, não correção.

A decisão foi tomada depois, na frente de Isolamento entre Usuários (PR C),
quando ficou demonstrado que num computador compartilhado quem entrava herdava
a aparência de quem saiu — tema, densidade, sidebar e idioma (gates `ISOL C-1`
a `ISOL C-12`). **No WEB LEGADO o escopo passou a ser USER, com o servidor como
fonte da verdade.** A promessa na UI mudou junto, porque um produto que troca o
escopo sem trocar a frase passa a mentir para o usuário.

O que NÃO mudou, e continua protegido aqui: o app Flutter. `LocaleProvider` e
`ThemeModeNotifier` seguem com escopo de instalação e sem conhecer identidade.
Os gates abaixo que falam de Dart valem palavra por palavra; os que falam do
Web Legado estão marcados ATUALIZADO e dizem por que o contrato anterior ficou
obsoleto. Nenhum deles foi apagado: um contrato superado por decisão explícita
é história do produto, não lixo.

## Os dois defeitos corrigidos

D1 — o login apagava a escolha explícita de idioma. `LocaleProvider` declarava a
prioridade "usuário > empresa > SO > pt-BR" e a alimentava com
`bootstrap.preferredLocale` / `companyLocale`. O backend NUNCA emitiu esses
campos: chegavam nulos, `_resolve` caía no sistema operacional, e o resultado
substituía em memória o idioma escolhido — a cada login. A correção é preservar
a escolha explícita, NÃO fabricar os campos no servidor.

D2 — `init()` lia o secure storage sem proteção. Uma exceção subia até o
`main()`, antes do `runApp`: tela preta em vez de degradação. A proteção fica
colada à leitura; o parse continua fora dela, para não esconder defeito nosso.

Nenhum teste usa credencial real.
"""

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
I18N_DART = RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'core' / 'i18n'
LOCALE_DART = I18N_DART / 'locale_provider.dart'
TEMA_DART = I18N_DART / 'theme_mode_notifier.dart'
MAIN_DART = RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'main.dart'
API_CLIENT = RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'core' / 'api' / 'api_client.dart'
APP_JS = RAIZ / 'static' / 'app.js'


def _sem_comentarios(texto):
    """Os comentários citam o comportamento antigo para explicar por que saiu."""
    fora = []
    for linha in texto.splitlines():
        limpa = linha.lstrip()
        if limpa.startswith('//') or limpa.startswith('///') or limpa.startswith('*'):
            continue
        fora.append(linha)
    return '\n'.join(fora)


@pytest.fixture(scope='module')
def locale_src():
    return _sem_comentarios(LOCALE_DART.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def tema_src():
    return _sem_comentarios(TEMA_DART.read_text(encoding='utf-8'))


def _corpo_de(src, assinatura):
    """Extrai o corpo de um método Dart por contagem de chaves."""
    i = src.index(assinatura)
    inicio = src.index('{', i)
    prof, j = 0, inicio
    while j < len(src):
        if src[j] == '{':
            prof += 1
        elif src[j] == '}':
            prof -= 1
            if prof == 0:
                return src[inicio:j + 1]
        j += 1
    raise AssertionError(f'não consegui delimitar {assinatura}')


# ── 1. O contrato de escopo por dispositivo, provado nos dois sentidos ───────

def test_a_promessa_ao_usuario_acompanha_o_escopo_no_web_legado():
    """A frase na UI tem de descrever o escopo REAL.

    ATUALIZADO na frente de Isolamento (PR C). O enunciado do gate não mudou —
    "se alguém mudar o escopo sem mudar a promessa, o produto passa a mentir
    para o usuário" — mas o escopo mudou, então a frase esperada mudou junto.

    O gate agora exige as duas metades: a promessa nova presente, e a antiga
    AUSENTE. Manter as duas seria pior do que trocar: o usuário leria uma coisa
    e o sistema faria outra.
    """
    js = APP_JS.read_text(encoding='utf-8')
    assert 'As preferências são salvas na sua conta' in js, \
        'a UI parou de dizer ao usuário onde as preferências dele ficam'
    assert 'As preferências são salvas neste dispositivo.' not in js, \
        'a promessa antiga voltou: ela descreve o escopo DEVICE, que saiu no PR C'
    assert 'Persistência por dispositivo (localStorage)' not in js, \
        'o comentário do código voltou a descrever o escopo anterior'


def test_nenhuma_preferencia_e_indexada_por_usuario():
    """Nenhuma chave de storage pode ser composta com identidade.

    MANTIDO, e não por acaso: o Isolamento PR C deu dono às preferências SEM
    criar `epi-theme:${user.id}`. A identidade ficou no servidor, e o navegador
    guarda no máximo uma cópia de sessão carimbada — que é conferida, não
    concatenada. Uma chave composta continua reprovando aqui, e continua sendo
    a solução errada: ela deixaria o valor de cada usuário legível no disco
    compartilhado para quem soubesse o id do outro.

    A metade Dart vale palavra por palavra: o Flutter não mudou de escopo.
    """
    js = APP_JS.read_text(encoding='utf-8')
    for chave in ('epi-theme', 'epi_language', 'epi-density'):
        for m in re.finditer(re.escape(chave), js):
            trecho = js[m.start():m.start() + 80]
            assert '${' not in trecho.split('\n')[0], \
                f'{chave} passou a ser composta com identidade: {trecho[:60]}'
    for arq in (LOCALE_DART, TEMA_DART):
        src = arq.read_text(encoding='utf-8')
        assert 'userId' not in src and 'user_id' not in src, \
            f'{arq.name} passou a conhecer identidade de usuário'


def test_o_logout_nao_destroi_a_preferencia_do_usuario():
    """O logout não pode fazer o usuário PERDER a preferência dele.

    ATUALIZADO na frente de Isolamento (PR C). O contrato anterior — "a
    preferência de dispositivo sobrevive ao logout, de propósito" — deixou de
    descrever o Web Legado, porque lá não existe mais preferência de
    dispositivo. Mas o VALOR que ele protegia continua de pé, e é o mesmo que
    orientou o PR C: dar dono não é apagar.

    Então o gate mudou de pergunta. Antes: "o logout preserva a chave do
    dispositivo?". Agora: "o logout preserva a preferência DO USUÁRIO?" — e a
    resposta é sim, porque ela mora no servidor e volta inteira no próximo
    login (`ISOL C-11`). O que o encerramento derruba é só a CÓPIA DE SESSÃO,
    que serve ao pré-paint da aba e cuja sobrevivência pintaria o tema de quem
    saiu para quem entra (`ISOL C-10`).

    A metade Flutter é a original, intocada: lá o escopo de instalação continua
    valendo e o logout continua proibido de limpá-lo.
    """
    api = API_CLIENT.read_text(encoding='utf-8')
    corpo = _corpo_de(api, 'static Future<void> clearSession()')
    assert 'theme_mode' not in corpo and 'user_locale' not in corpo, \
        'o logout do Flutter passou a limpar preferência de instalação'

    js = APP_JS.read_text(encoding='utf-8')
    encerramento = _corpo_de(js, 'function terminateSession(')
    # As chaves DEVICE não podem reaparecer: elas não existem mais.
    for chave in ('epi-theme', 'epi_language', 'epi-density'):
        assert chave not in encerramento, \
            f'{chave} voltou ao encerramento — ela foi aposentada no PR C'
    # E o que o encerramento derruba é a cópia, nomeadamente.
    assert 'PREFS_SESSAO_KEY' in encerramento, \
        'o encerramento parou de derrubar a cópia de sessão: ver ISOL C-10'
    assert 'localStorage' not in encerramento, \
        'o encerramento não pode alcançar o que sobrevive à aba'


def test_os_campos_de_locale_do_d1_continuam_sem_existir_no_backend():
    """Os dois campos que o D1 proibiu continuam não existindo.

    ATUALIZADO na frente de Isolamento (PR C). O título anterior era "nenhuma
    persistência server-side foi introduzida", e ele mediria falso hoje: o PR C
    introduziu `users.ui_preferences`, por decisão de produto explícita. Deixar
    o gate verde com aquele título seria pior do que deixá-lo vermelho — um
    contrato que já não descreve o sistema, passando despercebido.

    O que o gate sempre mediu, na letra, foi outra coisa, e essa continua
    valendo: `preferred_locale` e `company_locale` não podem existir no
    backend. Eles eram a correção ERRADA do D1 — fabricar no servidor os campos
    que o `LocaleProvider` esperava, em vez de preservar a escolha explícita do
    dispositivo. O PR C não os ressuscitou: a coluna nova guarda a preferência
    do USUÁRIO, resolvida no cliente, e não um fallback de empresa ou de SO
    descendo do servidor para sobrescrever escolha de ninguém.
    """
    for nome in ('preferred_locale', 'company_locale'):
        achados = []
        for py in (RAIZ / 'modules').rglob('*.py'):
            if nome in py.read_text(encoding='utf-8'):
                achados.append(py.name)
        assert not achados, f'{nome} apareceu no backend: {achados}'


def test_a_preferencia_do_web_legado_tem_dono_no_servidor():
    """O contrapeso do gate acima: o que o PR C criou, criou de verdade.

    Sem este gate, a conversão do anterior poderia ser lida como "afrouxamos a
    regra". Não foi: a persistência server-side existe, é nomeada, e tem de
    continuar existindo — senão o `ISOL C-11` (A reencontra o que é de A) perde
    o alicerce e a preferência de todo mundo some a cada logout.
    """
    servico = (RAIZ / 'modules' / 'auth' / 'service.py').read_text(encoding='utf-8')
    rotas = (RAIZ / 'modules' / 'auth' / 'routes.py').read_text(encoding='utf-8')
    esquema = (RAIZ / 'core' / 'schema.py').read_text(encoding='utf-8')

    assert 'def normalize_ui_preferences' in servico and 'def save_user_ui_preferences' in servico, \
        'o dono das preferências sumiu do backend'
    assert "_safe_add_column(connection, 'users', 'ui_preferences', 'TEXT')" in esquema \
        or "('ui_preferences', 'TEXT')" in esquema, \
        'a migração da coluna de preferências sumiu'
    assert "'/api/auth/me/preferences'" in rotas, \
        'a rota de preferências sumiu'
    # O ator NUNCA pode vir do corpo nesta rota: seria escrever na linha alheia.
    corpo = rotas[rotas.index('def handle_put_auth_me_preferences'):]
    corpo = corpo[:corpo.index('\ndef ', 1)]
    assert '_require_authenticated_actor' in corpo, \
        'a rota de escrita parou de exigir ator autenticado'
    assert "payload.get('user_id')" not in corpo and "entrada.get('id')" not in corpo, \
        'a rota passou a aceitar identidade vinda do corpo'


# ── 2. D1 — a escolha explícita do dispositivo está no topo ─────────────────

def test_existe_a_distincao_entre_escolha_e_ausencia(locale_src):
    """Sem esta distinção, "escolheu espanhol" e "ninguém escolheu" são a mesma
    coisa — e foi assim que o fallback passou a vencer a escolha."""
    assert 'bool _hasExplicitPreference = false;' in locale_src
    assert 'bool get hasExplicitPreference => _hasExplicitPreference;' in locale_src


def test_o_bootstrap_nao_sobrescreve_escolha_explicita(locale_src):
    """D1. A guarda precisa vir ANTES de `_resolve`: resolver e depois descartar
    deixaria a porta aberta para efeito colateral no meio."""
    corpo = _corpo_de(locale_src, 'void applyUserPreference(')
    guarda = 'if (_hasExplicitPreference) return;'
    assert guarda in corpo, 'a guarda do D1 sumiu'
    assert corpo.index(guarda) < corpo.index('_resolve('), \
        'a guarda precisa preceder a resolução do fallback'


def test_a_marca_de_escolha_so_nasce_de_valor_valido(locale_src):
    """Um valor persistido inválido não é escolha: precisa cair no fallback."""
    corpo = _corpo_de(locale_src, 'Future<void> init()')
    i_parsed = corpo.index('if (parsed != null)')
    i_marca = corpo.index('_hasExplicitPreference = true;')
    assert i_parsed < i_marca, 'a marca é aplicada sem validar o valor lido'


def test_a_escolha_manual_marca_e_persiste(locale_src):
    corpo = _corpo_de(locale_src, 'Future<void> setLocale(')
    assert '_hasExplicitPreference = true;' in corpo
    assert '_storage.write(' in corpo


def test_escolher_o_valor_que_ja_valia_por_fallback_ainda_e_escolha(locale_src):
    """A saída antecipada não pode ser só `_locale == locale`: sem preferência
    salva o locale ativo já pode ser o mesmo por fallback, e a escolha explícita
    se perderia. É o mesmo D1 por outro caminho."""
    corpo = _corpo_de(locale_src, 'Future<void> setLocale(')
    assert 'if (_locale == locale && _hasExplicitPreference) return;' in corpo, \
        'a saída antecipada voltou a ignorar se havia escolha explícita'


def test_ausencia_de_preferencia_nunca_vira_valor_persistido(locale_src):
    """Nem o startup nem o bootstrap podem gravar. Só a escolha manual grava."""
    for metodo in ('Future<void> init()', 'void applyUserPreference('):
        corpo = _corpo_de(locale_src, metodo)
        assert '_storage.write' not in corpo, \
            f'{metodo} passou a persistir o valor resolvido'


def test_o_backend_continua_sem_emitir_preferencia(locale_src):
    """Premissa do D1, medida e não assumida: a correção é do lado do cliente.
    Se o backend um dia emitir os campos, este gate fica vermelho e alguém
    decide conscientemente onde eles entram no contrato."""
    assert 'applyUserPreference' in locale_src
    campos = (RAIZ / 'flutter' / 'packages' / 'epi_api' / 'lib' / 'models'
              / 'bootstrap_response.dart').read_text(encoding='utf-8')
    assert 'preferred_locale' in campos, 'o cliente parou de ler o campo'
    emitido = any('preferred_locale' in p.read_text(encoding='utf-8')
                  for p in (RAIZ / 'modules').rglob('*.py'))
    assert not emitido, \
        'o backend passou a emitir preferred_locale: revisar o topo do contrato'


# ── 3. D2 — falha de storage degrada, nunca aborta o startup ────────────────

@pytest.mark.parametrize('arquivo', ['locale_provider.dart', 'theme_mode_notifier.dart'])
def test_a_leitura_de_storage_e_protegida(arquivo):
    src = _sem_comentarios((I18N_DART / arquivo).read_text(encoding='utf-8'))
    corpo = _corpo_de(src, 'Future<void> init()')
    assert 'try {' in corpo, f'{arquivo}: a leitura voltou a ser desprotegida'
    i_try = corpo.index('try {')
    i_read = corpo.index('_storage.read(')
    i_catch = corpo.index('catch (_)')
    assert i_try < i_read < i_catch, \
        f'{arquivo}: o try não envolve a leitura'


@pytest.mark.parametrize('arquivo', ['locale_provider.dart', 'theme_mode_notifier.dart'])
def test_a_protecao_nao_engole_erro_de_programacao(arquivo):
    """O `try` cobre só a operação de storage. O parse fica FORA: defeito nosso
    continua propagando."""
    src = _sem_comentarios((I18N_DART / arquivo).read_text(encoding='utf-8'))
    corpo = _corpo_de(src, 'Future<void> init()')
    i_catch = corpo.index('catch (_)')
    fim_catch = corpo.index('}', corpo.index('{', i_catch))
    assert '_parse(' not in corpo[i_catch:fim_catch], \
        f'{arquivo}: o parse entrou no bloco protegido'
    assert '_parse(' in corpo[fim_catch:], \
        f'{arquivo}: o parse precisa ficar fora do try'


@pytest.mark.parametrize('arquivo', ['locale_provider.dart', 'theme_mode_notifier.dart'])
def test_a_falha_de_leitura_nao_tem_efeito_colateral(arquivo):
    """O catch não pode gravar nem apagar: degradar é seguir com o default, não
    destruir a preferência que está lá."""
    src = _sem_comentarios((I18N_DART / arquivo).read_text(encoding='utf-8'))
    corpo = _corpo_de(src, 'Future<void> init()')
    i_catch = corpo.index('catch (_)')
    fim_catch = corpo.index('}', corpo.index('{', i_catch))
    bloco = corpo[i_catch:fim_catch]
    assert '_storage.write' not in bloco and '_storage.delete' not in bloco


def test_a_protecao_nao_virou_try_generico_no_main():
    """Um `try/catch` em volta do `main()` esconderia qualquer outra falha de
    inicialização. A proteção tem de ficar colada à operação de storage."""
    src = _sem_comentarios(MAIN_DART.read_text(encoding='utf-8'))
    corpo = _corpo_de(src, 'Future<void> main(')

    def profundidade(ate):
        return corpo[:ate].count('{') - corpo[:ate].count('}')

    i_init = corpo.index('themeNotifier.init()')
    i_runapp = corpo.index('runApp(')
    assert profundidade(i_init) == profundidade(i_runapp), (
        'a inicialização de tema/idioma está mais aninhada que o runApp(): '
        'foi envolvida por um bloco (try genérico) que esconderia outras falhas'
    )


# ── 4. Paridade do espelho versionado ───────────────────────────────────────

def test_os_arquivos_do_espelho_estao_no_manifesto_de_paridade():
    """Os dois arquivos são espelhados entre os repositórios e o drift é travado
    por manifesto. Se saírem dele, a divergência passa a ser silenciosa."""
    import json
    manifesto = json.loads(
        (RAIZ / 'flutter' / 'tool' / 'parity_manifest.json').read_text(encoding='utf-8'))
    arquivos = manifesto['files']
    for rel in ('apps/epi_admin/lib/core/i18n/locale_provider.dart',
                'apps/epi_admin/lib/core/i18n/theme_mode_notifier.dart'):
        assert rel in arquivos, f'{rel} saiu do manifesto'
