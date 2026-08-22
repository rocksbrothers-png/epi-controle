import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../../core/api/api_client.dart';
import '../../../core/bloc/company_attention_cubit.dart';

/// Padrão CORPORATIVO da faixa de atenção de estoque (#271-B2-b).
///
/// Fecha o degrau do meio da hierarquia:
///
///     system_default (20%) → company_configured → unit_configured
///
/// Vive em Configurações, e não na tela de Estoque, porque a permissão é
/// `settings:update`: é parâmetro administrativo da empresa, não ajuste
/// operacional. `admin` e `user` configuram a própria Unidade e não podem
/// alterar o padrão que TODAS as outras herdam.
class CompanyAttentionCard extends StatelessWidget {
  const CompanyAttentionCard({super.key, this.companyId});

  /// Empresa em edição. `null` para admins de empresa — o backend força a
  /// própria. Preenchido apenas para o `master_admin`, que não tem empresa e
  /// precisa nomear o tenant.
  final int? companyId;

  @override
  Widget build(BuildContext context) => BlocProvider(
        create: (_) => CompanyAttentionCubit(
          actorUserId: ApiClient.actorUserId,
          stockApi: ApiClient.stock,
        )..load(companyId: companyId),
        child: _CompanyAttentionBody(companyId: companyId),
      );
}

class _CompanyAttentionBody extends StatefulWidget {
  const _CompanyAttentionBody({this.companyId});

  final int? companyId;

  @override
  State<_CompanyAttentionBody> createState() => _CompanyAttentionBodyState();
}

class _CompanyAttentionBodyState extends State<_CompanyAttentionBody> {
  final _controller = TextEditingController();

  /// Último valor escrito no campo a partir do servidor. Serve para não
  /// sobrescrever o que o usuário está digitando a cada rebuild, e para o
  /// campo acompanhar a resposta de salvar/restaurar.
  int? _ultimoDoServidor;

  @override
  void didUpdateWidget(_CompanyAttentionBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    // master_admin trocou de empresa: o padrão é outro.
    if (oldWidget.companyId != widget.companyId) {
      _ultimoDoServidor = null;
      context.read<CompanyAttentionCubit>().load(companyId: widget.companyId);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<CompanyAttentionCubit, CompanyAttentionState>(
      listenWhen: (p, c) =>
          p.savedFeedback != c.savedFeedback || p.setting != c.setting,
      listener: (ctx, state) {
        // O campo é sincronizado AQUI, e não no `builder`: escrever num
        // TextEditingController durante o build notifica listeners e derruba
        // o frame com "setState() called during build".
        final setting = state.setting;
        if (setting != null &&
            _ultimoDoServidor != setting.attentionPercentage) {
          _ultimoDoServidor = setting.attentionPercentage;
          _controller.text = '${setting.attentionPercentage}';
        }
        final desfecho = state.savedFeedback;
        if (desfecho == null) return;
        // Salvar e restaurar podem terminar com o MESMO número e significam
        // coisas opostas. Duas mensagens, nunca um "pronto" genérico.
        ScaffoldMessenger.of(ctx).showSnackBar(
          SnackBar(
            content: Text(desfecho == CompanyAttentionOutcome.saved
                ? l10n.stockAttentionSaved
                : l10n.stockAttentionRestored),
          ),
        );
      },
      builder: (ctx, state) {
        final setting = state.setting;
        if (state.status == CompanyAttentionStatus.loading && setting == null) {
          return const Padding(
            padding: EdgeInsets.all(EpiSpacing.lg),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        if (setting == null) {
          return Padding(
            padding: const EdgeInsets.all(EpiSpacing.lg),
            child: Text(
              l10n.stockAttentionLoadError,
              style: const TextStyle(color: EpiColors.danger, fontSize: 12),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l10n.stockAttentionCompanyTitle,
                style: Theme.of(ctx).textTheme.titleSmall,
              ),
              const SizedBox(height: EpiSpacing.sm),
              // Obrigatória: sem ela o administrador acredita que salvar
              // reescreve todas as Unidades — que é exatamente o que o backend
              // recusa fazer. A propagação é leitura, nunca escrita.
              Text(
                l10n.stockAttentionCompanyHelp,
                style: Theme.of(ctx)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: EpiColors.textMuted),
              ),
              const SizedBox(height: EpiSpacing.md),
              TextField(
                controller: _controller,
                enabled: !state.isBusy,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: InputDecoration(
                  labelText: l10n.stockAttentionPercentageLabel,
                  suffixText: '%',
                  helperText: l10n.stockAttentionSystemDefaultHint(
                    setting.systemDefaultPercentage,
                  ),
                ),
              ),
              const SizedBox(height: EpiSpacing.sm),
              // A origem é TEXTO, não um estilo sutil. É o núcleo da fatia:
              // 20% herdado e 20% configurado são estados diferentes com o
              // mesmo número, e o usuário não pode depender de notar uma cor.
              Text(
                '${l10n.stockAttentionOriginLabel}: '
                '${_rotuloDaOrigem(l10n, setting)}',
                style: Theme.of(ctx).textTheme.bodySmall,
              ),
              if (state.error != null) ...[
                const SizedBox(height: EpiSpacing.sm),
                Text(
                  state.error == 'range'
                      ? l10n.stockAttentionRangeError(setting.maxPercentage)
                      : state.error!,
                  style: const TextStyle(color: EpiColors.danger, fontSize: 12),
                ),
              ],
              const SizedBox(height: EpiSpacing.md),
              EpiButton(
                label: l10n.stockAttentionSave,
                loading: state.status == CompanyAttentionStatus.saving,
                onPressed: state.isBusy ? null : () => _salvar(ctx),
              ),
              const SizedBox(height: EpiSpacing.sm),
              // Desabilitado quando já é `system_default`: o backend trata
              // como no-op, mas um botão que não faz nada é pior que um botão
              // desabilitado.
              TextButton(
                onPressed: (state.isBusy || !state.canRestore)
                    ? null
                    : () =>
                        ctx.read<CompanyAttentionCubit>().restoreSystemDefault(),
                child: Text(l10n.stockAttentionRestore),
              ),
            ],
          ),
        );
      },
    );
  }

  /// Rótulo da origem — lido do que o SERVIDOR devolveu, nunca deduzido da
  /// ação que o usuário acabou de executar.
  String _rotuloDaOrigem(
    AppLocalizations l10n,
    CompanyAttentionSetting setting,
  ) =>
      setting.isCompanyConfigured
          ? l10n.stockAttentionOriginCompany
          : l10n.stockAttentionOriginSystem;

  void _salvar(BuildContext ctx) {
    final digitado = int.tryParse(_controller.text.trim());
    final cubit = ctx.read<CompanyAttentionCubit>();
    if (digitado == null) {
      // Deixa o cubit produzir o mesmo erro de faixa: uma régua só.
      cubit.save(-1);
      return;
    }
    cubit.save(digitado);
  }
}
