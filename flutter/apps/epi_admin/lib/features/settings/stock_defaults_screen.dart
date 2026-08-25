import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import 'widgets/company_attention_card.dart';
import 'widgets/settings_page.dart';

/// Configurações → Estoque: padrão corporativo da faixa de atenção (#271-B2-b).
///
/// O padrão corporativo exige `settings:update` — a mesma permissão que o
/// backend cobra em `/api/stock/company-attention-percentage`.
///
/// A checagem aqui é de EXIBIÇÃO, não de autorização: quem decide é o
/// servidor, e um cliente adulterado que chame a rota continua sendo recusado
/// lá. O que ela evita é oferecer a um `admin`/`user` um controle que sempre
/// terminaria em 403 — o padrão que eles alterariam é herdado por todas as
/// outras Unidades. Com a subtela própria a checagem passou a valer também
/// para quem chega por URL direta, e não só para quem chega pelo hub.
bool podeConfigurarEstoque(BuildContext context) {
  final authState = context.read<AuthCubit>().state;
  return authState is AuthAuthenticated &&
      authState.sessionContext.hasPermission('settings:update');
}

class StockDefaultsScreen extends StatelessWidget {
  const StockDefaultsScreen({super.key, this.companyId});

  /// Empresa em edição, vinda de `?company_id=` (só o `master_admin`).
  final int? companyId;

  @override
  Widget build(BuildContext context) {
    return SettingsSubPage(
      title: AppLocalizations.of(context).stockAttentionSectionTitle,
      child: _corpo(context),
    );
  }

  Widget _corpo(BuildContext context) {
    if (!podeConfigurarEstoque(context)) {
      return Padding(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        child: Text(
          AppLocalizations.of(context).settingsNoPermission,
          style: const TextStyle(color: EpiColors.textMuted),
        ),
      );
    }
    if (settingsCompanyMissing(context, companyId)) {
      return const SettingsCompanyRequired();
    }
    return CompanyAttentionCard(companyId: companyId);
  }
}
