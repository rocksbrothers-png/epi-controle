import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/api/api_client.dart';
import '../../core/bloc/stock_config_cubit.dart';
import '../../core/bloc/unit_selector_cubit.dart';
import '../../core/utils/epi_status_utils.dart';
import '../../core/widgets/unit_selector.dart';

/// Configuração de estoque por `Unidade + EPI` (#271-B2-a).
///
/// Tela PRÓPRIA, e não um painel dentro de `stock_screen`. A tela de Controle
/// de Estoque é operacional — movimenta saldo, lista bloqueados, filtra
/// conformidade. Esta define os parâmetros que julgam aquele saldo. Embutir uma
/// na outra colocaria nove controles de escrita por linha dentro de uma lista
/// que rola, e é assim que um clique errado silencia um alerta.
///
/// Um EPI por vez, três blocos visualmente separados, cada um com o seu próprio
/// Salvar e o seu próprio Restaurar herança — porque no backend cada um é uma
/// rota independente e uma decisão independente.
class StockConfigScreen extends StatelessWidget {
  const StockConfigScreen({super.key, this.unitId, this.epiId});

  /// `?unit_id=` e `?epi_id=` da URL. **Entrada não confiável.**
  ///
  /// Nenhum dos dois seleciona nada por si. O `unitId` é entregue ao
  /// `EpiUnitSelector`, que só o aplica se ele constar de
  /// `GET /api/units/selectable`; o `epiId` fica retido no cubit até
  /// `/api/stock/epis?unit_id=` confirmar que aquele EPI é visível no escopo
  /// resolvido. Falhando qualquer das duas checagens, o valor é descartado em
  /// silêncio e a tela permanece fail-closed — nunca "abre no que foi pedido".
  final int? unitId;
  final int? epiId;

  @override
  Widget build(BuildContext context) => BlocProvider(
        create: (_) => StockConfigCubit(
          actorUserId: ApiClient.actorUserId,
          stockApi: ApiClient.stock,
        )..deepLinkEpi(epiId),
        child: _StockConfigBody(preferredUnitId: unitId),
      );
}

class _StockConfigBody extends StatelessWidget {
  const _StockConfigBody({this.preferredUnitId});

  final int? preferredUnitId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.stockConfigTitle)),
      body: BlocConsumer<StockConfigCubit, StockConfigState>(
        listenWhen: (p, c) => p.outcome != c.outcome || p.outcomeBlock != c.outcomeBlock,
        listener: (ctx, state) {
          final desfecho = state.outcome;
          final bloco = state.outcomeBlock;
          if (desfecho == null || bloco == null) return;
          ScaffoldMessenger.of(ctx).showSnackBar(
            SnackBar(content: Text(_mensagemDeDesfecho(l10n, bloco, desfecho))),
          );
        },
        builder: (ctx, state) => ListView(
          padding: const EdgeInsets.fromLTRB(
            EpiSpacing.lg, EpiSpacing.lg, EpiSpacing.lg, EpiSpacing.xl5,
          ),
          children: [
            Text(
              l10n.stockConfigIntro,
              style: Theme.of(ctx)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            ),
            const SizedBox(height: EpiSpacing.sm),

            // O seletor compartilhado é a ÚNICA autoridade de escopo desta
            // tela. Modo `write`: "Todas as Unidades" não é oferecida, porque
            // não existe gravar configuração em todas.
            //
            // `IgnorePointer` em vez de remover da árvore: sumir com o seletor
            // durante uma gravação faria a tela pular, e remontá-lo dispararia
            // um novo `GET /api/units/selectable` a cada salvamento.
            IgnorePointer(
              ignoring: state.isBusy,
              child: Opacity(
                opacity: state.isBusy ? 0.5 : 1,
                child: EpiUnitSelector(
                  purpose: UnitSelectorPurpose.write,
                  preferredUnitId: preferredUnitId,
                  label: l10n.stockConfigUnitLabel,
                  onChanged: (unitId) =>
                      ctx.read<StockConfigCubit>().setUnit(unitId),
                ),
              ),
            ),

            if (state.unitId == null)
              _Aviso(texto: l10n.stockConfigSelectUnit)
            else ...[
              const SizedBox(height: EpiSpacing.md),
              const _EpiPicker(),
              if (state.epiId == null)
                _Aviso(texto: l10n.stockConfigSelectEpi)
              else ...[
                const SizedBox(height: EpiSpacing.lg),
                const _DerivedSummary(),
                const SizedBox(height: EpiSpacing.lg),
                const _MinimumBlock(),
                const SizedBox(height: EpiSpacing.xl),
                const _AttentionBlock(),
                const SizedBox(height: EpiSpacing.xl),
                const _AlertBlock(),
              ],
            ],
          ],
        ),
      ),
    );
  }

  /// Salvar e restaurar terminam com valores possivelmente idênticos e
  /// significam coisas opostas — seis mensagens, nunca um "pronto" genérico.
  String _mensagemDeDesfecho(
    AppLocalizations l10n,
    StockConfigBlock bloco,
    StockConfigOutcome desfecho,
  ) =>
      switch ((bloco, desfecho)) {
        (StockConfigBlock.minimum, StockConfigOutcome.saved) =>
          l10n.stockConfigMinimumSaved,
        (StockConfigBlock.minimum, StockConfigOutcome.restored) =>
          l10n.stockConfigMinimumRestored,
        (StockConfigBlock.attention, StockConfigOutcome.saved) =>
          l10n.stockConfigAttentionSaved,
        (StockConfigBlock.attention, StockConfigOutcome.restored) =>
          l10n.stockConfigAttentionRestored,
        (StockConfigBlock.alert, StockConfigOutcome.saved) =>
          l10n.stockConfigAlertSaved,
        (StockConfigBlock.alert, StockConfigOutcome.restored) =>
          l10n.stockConfigAlertRestored,
      };
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.texto, this.erro = false});

  final String texto;
  final bool erro;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: EpiSpacing.md),
        child: Text(
          texto,
          style: erro
              ? const TextStyle(color: EpiColors.danger, fontSize: 12)
              : Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
        ),
      );
}

/// Escolha do EPI dentro da Unidade resolvida.
///
/// A lista vem de `/api/stock/epis?unit_id=`, já recortada pelo servidor
/// (visibilidade GLOBAL/JV reavaliada a cada consulta). A busca filtra
/// LOCALMENTE o que já veio: é navegação, não um segundo recorte.
class _EpiPicker extends StatelessWidget {
  const _EpiPicker();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<StockConfigCubit, StockConfigState>(
      builder: (ctx, state) {
        if (state.status == StockConfigStatus.loading && state.epis.isEmpty) {
          return const Padding(
            padding: EdgeInsets.all(EpiSpacing.md),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        if (state.status == StockConfigStatus.error && state.epis.isEmpty) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Aviso(texto: l10n.stockConfigEpisLoadError, erro: true),
              TextButton(
                onPressed: () =>
                    ctx.read<StockConfigCubit>().setUnit(state.unitId),
                child: Text(l10n.retry),
              ),
            ],
          );
        }
        if (state.epis.isEmpty) {
          return _Aviso(texto: l10n.stockConfigNoEpisInUnit);
        }
        final itens = state.filtered;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              enabled: !state.isBusy,
              decoration: InputDecoration(
                labelText: l10n.stockConfigEpiLabel,
                hintText: l10n.episSearchHint,
                prefixIcon: const Icon(Icons.search_rounded),
                isDense: true,
              ),
              onChanged: (q) => ctx.read<StockConfigCubit>().search(q),
            ),
            const SizedBox(height: EpiSpacing.sm),
            if (itens.isEmpty)
              _Aviso(texto: l10n.noResults)
            else
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 220),
                child: Material(
                  color: Colors.transparent,
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: itens.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) {
                      final epi = itens[i];
                      final marcado = epi.id == state.epiId;
                      return ListTile(
                        dense: true,
                        selected: marcado,
                        title: Text(epi.name),
                        trailing: marcado
                            ? const Icon(Icons.check_rounded, size: 18)
                            : null,
                        // Desabilitado durante gravação: trocar de EPI com uma
                        // requisição em voo faria a resposta chegar para o par
                        // errado. O cubit também descarta essa resposta, mas
                        // impedir é melhor do que corrigir depois.
                        onTap: state.isBusy
                            ? null
                            : () => ctx
                                .read<StockConfigCubit>()
                                .selectEpi(epi.id),
                      );
                    },
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// O que o SERVIDOR classificou para este par. Somente leitura.
///
/// `attention_limit`, `stock_status` e `underlying_status` chegam prontos de
/// `/api/stock/epis` e são exibidos como vieram. Nada aqui é recalculado — o
/// gate `tests/stock_rule_scan.py` (1.1D-C4) reprova o build se alguém
/// comparar saldo com mínimo em código de cliente.
class _DerivedSummary extends StatelessWidget {
  const _DerivedSummary();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<StockConfigCubit, StockConfigState>(
      builder: (ctx, state) {
        final epi = state.selected;
        if (epi == null) {
          // A gravação anterior deu certo; só os derivados não puderam ser
          // relidos. Dizer "erro" aqui afirmaria que a gravação falhou.
          return _Aviso(texto: l10n.stockConfigDerivedUnavailable);
        }
        final status = epiUnitBadgeStatus(epi);
        final subjacente = _rotuloDeStatus(l10n, epi.underlyingStatus);
        return Container(
          padding: const EdgeInsets.all(EpiSpacing.md),
          decoration: BoxDecoration(
            border: Border.all(color: EpiColors.border),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      epi.name,
                      style: Theme.of(ctx).textTheme.titleSmall,
                    ),
                  ),
                  if (status != null) EpiStockBadge(status: status),
                ],
              ),
              const SizedBox(height: EpiSpacing.sm),
              _Linha(
                rotulo: l10n.stockConfigUnitBalance,
                valor: '${epi.unitStockQuantity ?? '—'}',
              ),
              _Linha(
                rotulo: l10n.stockConfigAttentionLimit,
                valor: '${epi.attentionLimit ?? '—'}',
              ),
              // Exibido só quando DIFERE de `stock_status` — que é exatamente
              // quando ele acrescenta informação: monitoramento desligado sobre
              // uma condição física que continua sendo verdade.
              if (subjacente != null && epi.underlyingStatus != epi.stockStatus)
                _Linha(
                  rotulo: l10n.stockConfigUnderlyingStatus,
                  valor: subjacente,
                ),
            ],
          ),
        );
      },
    );
  }

  /// Rótulo traduzido para a chave de status do backend. A CHAVE é o contrato;
  /// o texto sai do ARB, senão o app falaria português nos outros quatro
  /// idiomas. Chave desconhecida devolve `null` — não inventa "normal".
  String? _rotuloDeStatus(AppLocalizations l10n, String? chave) =>
      switch (chave) {
        'critical' => l10n.stockConfigStatusCritical,
        'near_minimum' => l10n.stockConfigStatusNearMinimum,
        'normal' => l10n.stockConfigStatusNormal,
        'disabled' => l10n.stockConfigStatusDisabled,
        _ => null,
      };
}

class _Linha extends StatelessWidget {
  const _Linha({required this.rotulo, required this.valor});

  final String rotulo;
  final String valor;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              rotulo,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
            ),
            Text(valor, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
}

/// Moldura comum dos três blocos: título, ajuda, corpo, origem, erro, ações.
///
/// Existe para que os três fiquem visualmente idênticos em tudo que não seja o
/// parâmetro. Um bloco que se pareça diferente sugere que funciona diferente.
class _Bloco extends StatelessWidget {
  const _Bloco({
    required this.titulo,
    required this.ajuda,
    required this.corpo,
    required this.origem,
    required this.acoes,
    this.erro,
  });

  final String titulo;
  final String ajuda;
  final Widget corpo;
  final String origem;
  final Widget acoes;
  final String? erro;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(EpiSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(color: EpiColors.border),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(titulo, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: EpiSpacing.xs),
          Text(
            ajuda,
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: EpiColors.textMuted),
          ),
          const SizedBox(height: EpiSpacing.md),
          corpo,
          const SizedBox(height: EpiSpacing.sm),
          // A origem é TEXTO, não um estilo sutil. É o núcleo da hierarquia:
          // 20 herdado e 20 configurado são estados diferentes com o mesmo
          // número, e o usuário não pode depender de notar uma cor.
          Text(
            '${l10n.stockAttentionOriginLabel}: $origem',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (erro != null) ...[
            const SizedBox(height: EpiSpacing.sm),
            Text(
              erro!,
              style: const TextStyle(color: EpiColors.danger, fontSize: 12),
            ),
          ],
          const SizedBox(height: EpiSpacing.md),
          acoes,
        ],
      ),
    );
  }
}

/// Rótulo da origem — lido do que o SERVIDOR devolveu, nunca deduzido da ação
/// que o usuário acabou de executar.
String _rotuloDaOrigem(AppLocalizations l10n, String source) => switch (source) {
      kUnitEpiSourceUnit => l10n.stockConfigOriginUnit,
      kUnitEpiSourceCompany => l10n.stockConfigOriginCompany,
      kUnitEpiSourceSystem => l10n.stockAttentionOriginSystem,
      _ => l10n.stockConfigOriginUnknown,
    };

/// Mensagem de erro do bloco. As chaves locais viram texto traduzido; qualquer
/// outra coisa é erro do servidor e é exibida como veio.
String _mensagemDeErro(AppLocalizations l10n, String erro) => switch (erro) {
      'negative' => l10n.stockConfigMinimumNegativeError,
      'range' => l10n.stockConfigAttentionRangeError,
      _ => erro,
    };

class _MinimumBlock extends StatefulWidget {
  const _MinimumBlock();

  @override
  State<_MinimumBlock> createState() => _MinimumBlockState();
}

class _MinimumBlockState extends State<_MinimumBlock> {
  final _controller = TextEditingController();

  /// Último valor escrito no campo a partir do servidor. Impede que um rebuild
  /// sobrescreva o que o usuário está digitando, e faz o campo acompanhar a
  /// resposta de salvar/restaurar.
  int? _ultimoDoServidor;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<StockConfigCubit, StockConfigState>(
      listenWhen: (p, c) => p.minimum != c.minimum || p.epiId != c.epiId,
      listener: (_, state) {
        // Sincroniza AQUI, e não no `builder`: escrever num
        // TextEditingController durante o build notifica listeners e derruba o
        // frame com "setState() called during build".
        final atual = state.minimum;
        if (atual != null && _ultimoDoServidor != atual.minimumStock) {
          _ultimoDoServidor = atual.minimumStock;
          _controller.text = '${atual.minimumStock}';
        }
      },
      builder: (ctx, state) {
        final atual = state.minimum;
        if (atual == null) return const SizedBox.shrink();
        final gravando = state.busyBlock == StockConfigBlock.minimum;
        // O cubit sai para uma variável em vez de `ctx.read<...>()` inline nos
        // callbacks. Motivo prático: o gate `tests/stock_rule_scan.py` procura
        // um termo de saldo e um de mínimo na MESMA linha, e lê os `<>` de tipo
        // genérico do Dart como comparadores —
        // `ctx.read<StockConfigCubit>().restoreMinimum()` casa nos dois termos
        // sem comparar nada. É falso positivo do detector (mesma família do
        // `=>` já documentado em `_comparadores`), não um problema deste
        // arquivo; extrair a variável evita o ruído sem afrouxar o gate.
        final cubit = ctx.read<StockConfigCubit>();
        return _Bloco(
          titulo: l10n.stockConfigMinimumTitle,
          ajuda: l10n.stockConfigMinimumHelp,
          erro: state.errorBlock == StockConfigBlock.minimum
              ? _mensagemDeErro(l10n, state.error ?? '')
              : null,
          origem: _rotuloDaOrigem(l10n, atual.source),
          corpo: TextField(
            controller: _controller,
            enabled: !state.isBusy,
            keyboardType: TextInputType.number,
            // Só dígitos: o backend não publica teto para o mínimo, então o
            // cliente NÃO inventa um. Valida formato e negatividade, e a régua
            // continua sendo a resposta do servidor.
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(
              labelText: l10n.stockConfigMinimumLabel,
            ),
          ),
          acoes: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpiButton(
                label: l10n.stockConfigSave,
                loading: gravando,
                onPressed: state.isBusy ? null : () => _salvar(cubit),
              ),
              const SizedBox(height: EpiSpacing.xs),
              TextButton(
                onPressed: (state.isBusy || !state.canRestoreMinimum)
                    ? null
                    : cubit.restoreMinimum,
                child: Text(l10n.stockConfigRestore),
              ),
            ],
          ),
        );
      },
    );
  }

  void _salvar(StockConfigCubit cubit) {
    final digitado = int.tryParse(_controller.text.trim());
    // Campo vazio ou ilegível cai no mesmo erro de negatividade do cubit: uma
    // régua só, e ela mora lá.
    cubit.saveMinimum(digitado ?? -1);
  }
}

class _AttentionBlock extends StatefulWidget {
  const _AttentionBlock();

  @override
  State<_AttentionBlock> createState() => _AttentionBlockState();
}

class _AttentionBlockState extends State<_AttentionBlock> {
  final _controller = TextEditingController();
  int? _ultimoDoServidor;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<StockConfigCubit, StockConfigState>(
      listenWhen: (p, c) => p.attention != c.attention || p.epiId != c.epiId,
      listener: (_, state) {
        final atual = state.attention;
        if (atual != null && _ultimoDoServidor != atual.attentionPercentage) {
          _ultimoDoServidor = atual.attentionPercentage;
          _controller.text = '${atual.attentionPercentage}';
        }
      },
      builder: (ctx, state) {
        final atual = state.attention;
        if (atual == null) return const SizedBox.shrink();
        final gravando = state.busyBlock == StockConfigBlock.attention;
        return _Bloco(
          titulo: l10n.stockConfigAttentionTitle,
          ajuda: l10n.stockConfigAttentionHelp,
          erro: state.errorBlock == StockConfigBlock.attention
              ? _mensagemDeErro(l10n, state.error ?? '')
              : null,
          origem: _rotuloDaOrigem(l10n, atual.source),
          corpo: TextField(
            controller: _controller,
            enabled: !state.isBusy,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(
              labelText: l10n.stockAttentionPercentageLabel,
              suffixText: '%',
            ),
          ),
          acoes: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpiButton(
                label: l10n.stockConfigSave,
                loading: gravando,
                onPressed: state.isBusy
                    ? null
                    : () => ctx.read<StockConfigCubit>().saveAttention(
                          int.tryParse(_controller.text.trim()) ?? -1,
                        ),
              ),
              const SizedBox(height: EpiSpacing.xs),
              TextButton(
                onPressed: (state.isBusy || !state.canRestoreAttention)
                    ? null
                    : () => ctx.read<StockConfigCubit>().restoreAttention(),
                child: Text(l10n.stockConfigRestore),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Monitoramento de alerta — com gravação EXPLÍCITA (#271-B2-a, ajuste 1).
///
/// O toggle mexe só no rascunho local. A persistência acontece no Salvar, e
/// quando a alteração pendente DESLIGA o alerta há uma confirmação antes do
/// `POST`: silenciar o monitoramento de um EPI é decisão operacional, e um
/// toggle que grava ao toque a torna reversível apenas por acidente.
///
/// `Restaurar padrão` continua sendo operação distinta de `Salvar habilitado`:
/// aquela apaga a decisão da Unidade, esta grava a decisão de manter ligado.
/// As duas terminam com o alerta ligado e significam coisas opostas.
class _AlertBlock extends StatelessWidget {
  const _AlertBlock();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocBuilder<StockConfigCubit, StockConfigState>(
      builder: (ctx, state) {
        final atual = state.alert;
        if (atual == null) return const SizedBox.shrink();
        final gravando = state.busyBlock == StockConfigBlock.alert;
        return _Bloco(
          titulo: l10n.stockConfigAlertTitle,
          ajuda: l10n.stockConfigAlertHelp,
          erro: state.errorBlock == StockConfigBlock.alert
              ? _mensagemDeErro(l10n, state.error ?? '')
              : null,
          origem: _rotuloDaOrigem(l10n, atual.source),
          corpo: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(l10n.stockConfigAlertToggle),
                value: state.alertDraft,
                onChanged: state.isBusy
                    ? null
                    : (v) =>
                        ctx.read<StockConfigCubit>().toggleAlertDraft(v),
              ),
              if (state.alertDirty)
                Text(
                  l10n.stockConfigAlertPending,
                  style: const TextStyle(
                    color: EpiColors.warning,
                    fontSize: 12,
                  ),
                ),
            ],
          ),
          acoes: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpiButton(
                label: l10n.stockConfigSave,
                loading: gravando,
                // Sem alteração pendente não há o que gravar. Um Salvar sempre
                // ativo sugeriria que o toggle ainda não foi aplicado mesmo
                // quando ele já reflete o servidor.
                onPressed: (state.isBusy || !state.alertDirty)
                    ? null
                    : () => _salvar(ctx, state),
              ),
              const SizedBox(height: EpiSpacing.xs),
              TextButton(
                onPressed: (state.isBusy || !state.canRestoreAlert)
                    ? null
                    : () => ctx.read<StockConfigCubit>().restoreAlert(),
                child: Text(l10n.stockConfigRestore),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _salvar(BuildContext ctx, StockConfigState state) async {
    final l10n = AppLocalizations.of(ctx);
    final cubit = ctx.read<StockConfigCubit>();
    // Ligar não pergunta; desligar pergunta. A condição mora no cubit
    // (`alertRequiresConfirmation`) para ser testável sem widget.
    if (state.alertRequiresConfirmation) {
      final confirmado = await showDialog<bool>(
        context: ctx,
        builder: (dialogCtx) => AlertDialog(
          title: Text(l10n.stockConfigAlertDisableTitle),
          content: Text(l10n.stockConfigAlertDisableBody),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(false),
              child: Text(l10n.cancel),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(true),
              child: Text(l10n.stockConfigAlertDisableConfirm),
            ),
          ],
        ),
      );
      if (confirmado != true) return;
    }
    await cubit.saveAlert();
  }
}
