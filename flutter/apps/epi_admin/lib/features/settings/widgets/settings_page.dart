import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../../core/bloc/auth_cubit.dart';
import '../../../core/bloc/auth_state.dart';
import 'settings_tile.dart';

/// Moldura das subtelas de Configurações: AppBar com o nome da "pasta" (o
/// botão de voltar vem do próprio Navigator, já que o hub abre as subtelas
/// com `push`) e conteúdo rolável dentro de [SettingsContent].
class SettingsSubPage extends StatelessWidget {
  const SettingsSubPage({
    super.key,
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(vertical: EpiSpacing.lg),
        child: SettingsContent(child: child),
      ),
    );
  }
}

/// `true` quando a sessão é de `master_admin` e nenhuma empresa foi escolhida.
///
/// O master_admin não pertence a uma empresa: cada configuração abaixo é de um
/// tenant e precisa que ele nomeie qual. O hub resolve isso no seletor do topo
/// e propaga a escolha para as subtelas em `?company_id=`; sem ela não há o
/// que carregar — nem para ler.
bool settingsCompanyMissing(BuildContext context, int? companyId) {
  if (companyId != null) return false;
  final authState = context.read<AuthCubit>().state;
  return authState is AuthAuthenticated &&
      authState.sessionContext.role == 'master_admin';
}

/// Aviso exibido no lugar do formulário quando [settingsCompanyMissing].
class SettingsCompanyRequired extends StatelessWidget {
  const SettingsCompanyRequired({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(EpiSpacing.lg),
      child: Text(
        AppLocalizations.of(context).settingsSelectCompanyFirst,
        style: const TextStyle(color: EpiColors.textMuted),
      ),
    );
  }
}
