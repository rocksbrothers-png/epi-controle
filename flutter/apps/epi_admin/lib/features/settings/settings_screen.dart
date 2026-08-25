import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/settings_cubit.dart';
import '../../core/router/routes.dart';
import 'stock_defaults_screen.dart';
import 'widgets/settings_tile.dart';

/// Configurações — hub.
///
/// Antes esta era UMA tela: seletor de tema, idioma, formulário da Ficha,
/// política de arquivamento, matriz de visibilidade por módulo e a faixa de
/// atenção, tudo empilhado numa lista só. Achar qualquer uma delas exigia
/// rolar por todas as outras, e um formulário longo no meio escondia o
/// próximo assunto.
///
/// Agora cada assunto é uma "pasta" com ícone, descrição e subtela própria
/// (`/settings/...`). O hub só decide **o que aparece** — cada subtela mantém
/// a sua própria checagem de permissão, porque a URL direta não passa por
/// aqui.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final authState = context.read<AuthCubit>().state;
    final isMaster = authState is AuthAuthenticated &&
        authState.sessionContext.role == 'master_admin';
    return BlocProvider(
      create: (_) => SettingsCubit()..initCompanies(isMaster: isMaster),
      child: const _SettingsHub(),
    );
  }
}

class _SettingsHub extends StatelessWidget {
  const _SettingsHub();

  /// Propaga a empresa escolhida para a subtela.
  ///
  /// Query em vez de `extra`: no Web `state.extra` não sobrevive a um refresh,
  /// e a subtela de um tenant errado é pior do que uma subtela vazia. Mesmo
  /// padrão de `/legal-entities?company_id=` e `/stock/config?unit_id=`.
  String _withCompany(String route, int? companyId) =>
      companyId == null ? route : '$route?company_id=$companyId';

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsTitle)),
      body: BlocConsumer<SettingsCubit, SettingsState>(
        listenWhen: (p, c) => p.error != c.error,
        listener: (ctx, state) {
          if (state.error != null) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(
                content: Text(state.error!),
                backgroundColor: EpiColors.danger,
              ),
            );
          }
        },
        builder: (ctx, state) {
          final authState = ctx.watch<AuthCubit>().state;
          final canConfigureCompany = authState is AuthAuthenticated &&
              authState.permissions.contains('company_settings:view');
          // Só o master_admin edita a Ficha/Regras de OUTRO tenant; para os
          // demais o backend resolve a própria empresa e a query fica fora.
          final companyId = state.isMaster ? state.selectedCompanyId : null;
          return ListView(
            padding: const EdgeInsets.only(bottom: EpiSpacing.xl5),
            children: [
              SettingsContent(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (state.isMaster) _CompanySelector(state: state),
                    if (canConfigureCompany)
                      SettingsSection(
                        label: l10n.settingsSectionCompany,
                        children: [
                          SettingsTile(
                            icon: Icons.apartment_rounded,
                            title: l10n.myCompanyTitle,
                            subtitle: l10n.myCompanySubtitle,
                            onTap: () => context.push(Routes.myCompany),
                          ),
                        ],
                      ),
                    SettingsSection(
                      label: l10n.settingsSectionOperation,
                      children: [
                        SettingsTile(
                          icon: Icons.assignment_rounded,
                          title: l10n.settingsFichaTileTitle,
                          subtitle: l10n.settingsFichaTileSubtitle,
                          onTap: () => context.push(
                            _withCompany(Routes.settingsFicha, companyId),
                          ),
                        ),
                        if (podeConfigurarEstoque(context))
                          SettingsTile(
                            icon: Icons.inventory_2_rounded,
                            title: l10n.stockAttentionSectionTitle,
                            subtitle: l10n.settingsStockTileSubtitle,
                            onTap: () => context.push(
                              _withCompany(Routes.settingsStock, companyId),
                            ),
                          ),
                        SettingsTile(
                          icon: Icons.visibility_rounded,
                          title: l10n.moduleVisibilityTitle,
                          subtitle: l10n.settingsModulesTileSubtitle,
                          onTap: () => context.push(
                            _withCompany(Routes.settingsModules, companyId),
                          ),
                        ),
                        SettingsTile(
                          icon: Icons.archive_rounded,
                          title: l10n.settingsArchivalTitle,
                          subtitle: l10n.settingsArchivalSubtitle,
                          onTap: () => context.push(
                            _withCompany(Routes.settingsArchival, companyId),
                          ),
                        ),
                      ],
                    ),
                    SettingsSection(
                      label: l10n.settingsAppSection,
                      children: [
                        SettingsTile(
                          icon: Icons.palette_rounded,
                          title: l10n.settingsAppearanceTitle,
                          subtitle: l10n.settingsAppearanceSubtitle,
                          onTap: () =>
                              context.push(Routes.settingsAppearance),
                        ),
                      ],
                    ),
                    SettingsSection(
                      label: l10n.settingsSectionSubscription,
                      children: [
                        SettingsTile(
                          icon: Icons.card_membership_rounded,
                          title: l10n.settingsSubscriptionTileTitle,
                          subtitle: l10n.settingsSubscriptionTileSubtitle,
                          onTap: () => context.push(Routes.subscription),
                        ),
                        SettingsTile(
                          icon: Icons.receipt_long_rounded,
                          title: l10n.settingsInvoicesTileTitle,
                          subtitle: l10n.settingsInvoicesTileSubtitle,
                          onTap: () => context.push(Routes.invoices),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ── Seletor de empresa (master_admin) ───────────────────────────────────────
// As configurações abaixo são por tenant. O master_admin, que não pertence a
// uma empresa, escolhe explicitamente qual está administrando; um banner
// deixa a empresa ativa visível para evitar edição na empresa errada. A
// escolha viaja para cada subtela em `?company_id=`.
class _CompanySelector extends StatelessWidget {
  const _CompanySelector({required this.state});
  final SettingsState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final active =
        state.companies.where((c) => c.id == state.selectedCompanyId).toList();
    final activeName = active.isNotEmpty ? active.first.name : null;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.lg,
        EpiSpacing.lg,
        0,
      ),
      child: EpiCard(
        child: state.isLoading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<int>(
                    value: state.selectedCompanyId,
                    decoration: InputDecoration(
                      labelText: l10n.settingsCompanyLabel,
                      border: const OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: [
                      for (final c in state.companies)
                        DropdownMenuItem(value: c.id, child: Text(c.name)),
                    ],
                    onChanged: (v) {
                      if (v != null) {
                        context.read<SettingsCubit>().selectCompany(v);
                      }
                    },
                  ),
                  if (activeName != null) ...[
                    const SizedBox(height: EpiSpacing.sm),
                    Container(
                      padding: const EdgeInsets.all(EpiSpacing.sm),
                      decoration: BoxDecoration(
                        color: EpiColors.brand.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(EpiRadius.sm),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.apartment_rounded,
                              size: 18, color: EpiColors.brand),
                          const SizedBox(width: EpiSpacing.sm),
                          Expanded(
                            child: Text(
                              l10n.settingsCompanyScopeBanner(activeName),
                              style: const TextStyle(
                                color: EpiColors.brand,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
      ),
    );
  }
}
