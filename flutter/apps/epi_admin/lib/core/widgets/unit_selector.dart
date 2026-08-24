import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../api/api_client.dart';
import '../bloc/unit_selector_cubit.dart';

/// Seletor de Unidade compartilhado.
///
/// **Não decide permissão.** Renderiza o que `GET /api/units/selectable`
/// devolveu: quais Unidades, se cabe "Todas", se o perfil é travado. Nenhum
/// `if` de perfil vive aqui, e a lista NUNCA vem de `bootstrap.units`.
///
/// Um componente, quatro consumidores previstos: a configuração por Unidade +
/// EPI (#271-B2-a) e as três fatias de Compras (P3-C/D/E). Construí-lo dentro
/// de uma delas produziria duas implementações do mesmo conceito — foi assim
/// que a comparação `saldo × mínimo` acabou duplicada entre Dart e JS.
class EpiUnitSelector extends StatelessWidget {
  const EpiUnitSelector({
    super.key,
    required this.purpose,
    required this.onChanged,
    this.label,
    this.preferredUnitId,
  });

  /// Leitura oferece "Todas as Unidades" quando o backend autoriza; escrita
  /// nunca oferece. Ver [UnitSelectorPurpose].
  final UnitSelectorPurpose purpose;

  /// Unidade escolhida, ou `null` para a visão consolidada (só em leitura).
  final ValueChanged<int?> onChanged;

  final String? label;

  /// Unidade sugerida por deep link. Só é aplicada se o backend a tiver
  /// oferecido — ver [UnitSelectorCubit.preferredUnitId].
  final int? preferredUnitId;

  @override
  Widget build(BuildContext context) => BlocProvider(
        create: (_) => UnitSelectorCubit(
          actorUserId: ApiClient.actorUserId,
          unitsApi: ApiClient.units,
          purpose: purpose,
          preferredUnitId: preferredUnitId,
        )..load(),
        child: _UnitSelectorBody(onChanged: onChanged, label: label),
      );
}

class _UnitSelectorBody extends StatelessWidget {
  const _UnitSelectorBody({required this.onChanged, this.label});

  final ValueChanged<int?> onChanged;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return BlocConsumer<UnitSelectorCubit, UnitSelectorState>(
      listenWhen: (p, c) => p.selectedUnitId != c.selectedUnitId,
      listener: (_, state) => onChanged(state.selectedUnitId),
      builder: (ctx, state) {
        final cubit = ctx.read<UnitSelectorCubit>();
        if (state.status == UnitSelectorStatus.loading) {
          return const Padding(
            padding: EdgeInsets.all(EpiSpacing.md),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        if (state.status == UnitSelectorStatus.error) {
          return _aviso(ctx, l10n.unitSelectorLoadError, erro: true);
        }
        // Carteira existente e VAZIA é diferente de empresa sem Unidades: as
        // duas dão lista vazia e pedem mensagens diferentes.
        if (state.blocked) {
          return _aviso(ctx, l10n.unitSelectorNoUnitsAssigned, erro: true);
        }
        if (state.scope.isEmpty) {
          return _aviso(ctx, l10n.unitSelectorCompanyHasNoUnits);
        }

        final itens = <DropdownMenuItem<int?>>[
          if (cubit.offersAllUnits)
            DropdownMenuItem<int?>(
              value: null,
              child: Text(l10n.unitSelectorAllUnits),
            ),
          for (final unidade in state.scope.units)
            DropdownMenuItem<int?>(
              value: unidade.id,
              child: Text(unidade.name),
            ),
        ];

        // Perfil travado vê a própria Unidade, desabilitada: saber onde se está
        // operando vale o controle. `onChanged` nulo é o que desabilita.
        final travado = state.scope.locked;
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: EpiSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // `initialValue` basta porque a seleção só muda POR AQUI: a
              // pré-seleção (perfil travado, opção única) é decidida durante o
              // `load()`, antes do primeiro build deste campo, e daí em diante
              // quem altera é o próprio usuário. Se um dia o estado passar a
              // ser alterado de fora, isto precisa virar campo controlado.
              DropdownButtonFormField<int?>(
                initialValue: state.selectedUnitId,
                items: itens,
                onChanged: travado ? null : cubit.select,
                decoration: InputDecoration(
                  labelText: label ?? l10n.unitSelectorLabel,
                ),
              ),
              if (travado) ...[
                const SizedBox(height: EpiSpacing.xs),
                Text(
                  l10n.unitSelectorLockedHint,
                  style: Theme.of(ctx)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: EpiColors.textMuted),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _aviso(BuildContext ctx, String texto, {bool erro = false}) => Padding(
        padding: const EdgeInsets.all(EpiSpacing.md),
        child: Text(
          texto,
          style: erro
              ? const TextStyle(color: EpiColors.danger, fontSize: 12)
              : Theme.of(ctx)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: EpiColors.textMuted),
        ),
      );
}
