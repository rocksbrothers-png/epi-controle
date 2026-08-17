import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/companies_cubit.dart';
import '../../core/router/routes.dart';
import '../../core/widgets/create_company_dialog.dart';

class CompaniesScreen extends StatelessWidget {
  const CompaniesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => CompaniesCubit()..load(),
      child: const _CompaniesBody(),
    );
  }
}

class _CompaniesBody extends StatelessWidget {
  const _CompaniesBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final authState = context.watch<AuthCubit>().state;
    final canCreate = authState is AuthAuthenticated &&
        authState.permissions.contains('companies:create');
    final actorUserId = authState is AuthAuthenticated
        ? (authState.sessionContext.userId ?? 0)
        : 0;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.companiesTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => context.read<CompaniesCubit>().load(),
          ),
        ],
      ),
      floatingActionButton: (canCreate && actorUserId > 0)
          ? FloatingActionButton(
              // Sem tooltip de propósito: o gate de i18n barra `tooltip:` em
              // lib/features. O ícone "+" é autoexplicativo; o título do
              // diálogo ("Nova empresa") dá o contexto textual.
              onPressed: () => CreateCompanyDialog.show(
                context,
                context.read<CompaniesCubit>(),
                actorUserId,
              ),
              child: const Icon(Icons.add_rounded),
            )
          : null,
      body: Column(
        children: [
          _SearchBar(),
          Expanded(
            child: BlocBuilder<CompaniesCubit, CompaniesState>(
              builder: (ctx, state) {
                if (state.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state.error != null) {
                  return _RetryView(
                    onRetry: () => context.read<CompaniesCubit>().load(),
                  );
                }
                final items = state.filtered;
                if (items.isEmpty) {
                  return EpiEmptyState(
                    title: l10n.noResults,
                    icon: Icons.business_outlined,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () => context.read<CompaniesCubit>().load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(
                      top: EpiSpacing.sm,
                      bottom: EpiSpacing.xl5,
                    ),
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        const Divider(height: 1, indent: 16),
                    itemBuilder: (_, i) => _CompanyTile(company: items[i]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SearchBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.sm,
        EpiSpacing.lg,
        EpiSpacing.xs,
      ),
      child: TextField(
        onChanged: context.read<CompaniesCubit>().search,
        decoration: InputDecoration(
          hintText: l10n.companiesSearchHint,
          prefixIcon: const Icon(Icons.search_rounded),
          border: const OutlineInputBorder(),
          isDense: true,
          contentPadding: const EdgeInsets.symmetric(vertical: 10),
        ),
      ),
    );
  }
}

/// Rota da tela de CNPJs recortada por empresa.
///
/// Vive fora do widget para ser testável: o Admin Master atende vários
/// clientes, e um recorte montado errado o faria cadastrar CNPJ na empresa
/// errada sem nenhum sinal na tela.
String legalEntitiesRouteForCompany(int companyId, String companyName) {
  return Uri(
    path: Routes.legalEntities,
    queryParameters: {
      'company_id': '$companyId',
      if (companyName.trim().isNotEmpty) 'company_name': companyName.trim(),
    },
  ).toString();
}

class _CompanyTile extends StatelessWidget {
  const _CompanyTile({required this.company});
  final Company company;

  Color _statusColor(AppLocalizations l10n) {
    if (company.isSuspended) return EpiColors.danger;
    if (!company.active) return EpiColors.textMuted;
    return EpiColors.success;
  }

  String _statusLabel(AppLocalizations l10n) {
    if (company.isSuspended) return l10n.companyStatusSuspended;
    if (!company.active) return l10n.companyStatusInactive;
    return l10n.companyStatusActive;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final color = _statusColor(l10n);
    final label = _statusLabel(l10n);
    final authState = context.watch<AuthCubit>().state;
    final canViewLegalEntities = authState is AuthAuthenticated &&
        authState.permissions.contains('legal_entities:view');
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: EpiColors.brandSoft,
              borderRadius: BorderRadius.circular(EpiRadius.md),
            ),
            alignment: Alignment.center,
            child: const Icon(
              Icons.business_rounded,
              color: EpiColors.brand,
              size: 22,
            ),
          ),
          const SizedBox(width: EpiSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  company.name,
                  style: Theme.of(context).textTheme.bodyLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: EpiSpacing.xs),
                Row(
                  children: [
                    if (company.cnpj != null) ...[
                      Text(
                        company.cnpj!,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: EpiColors.textMuted),
                      ),
                      const SizedBox(width: EpiSpacing.sm),
                    ],
                    if (company.planName != null)
                      Text(
                        company.planName!,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: EpiColors.textMuted),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                  ],
                ),
                if (company.userLimit != null) ...[
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      const Icon(
                        Icons.people_outline_rounded,
                        size: 12,
                        color: EpiColors.textMuted,
                      ),
                      const SizedBox(width: 3),
                      Text(
                        '${company.userCount ?? 0} / ${company.userLimit}',
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(color: EpiColors.textMuted),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: EpiSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: EpiSpacing.sm,
              vertical: 3,
            ),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(EpiRadius.full),
              border: Border.all(color: color.withValues(alpha: 0.4)),
            ),
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          // Caminho do Admin Master para os CNPJs do cliente. Sem ele, a única
          // forma de gerenciar o Multi-CNPJ de uma empresa que não é a sua era
          // digitar a URL com o `company_id` na mão.
          if (canViewLegalEntities)
            IconButton(
              icon: const Icon(Icons.domain_rounded, size: 20),
              color: EpiColors.brand,
              onPressed: () => context.push(
                legalEntitiesRouteForCompany(company.id, company.name),
              ),
            ),
        ],
      ),
    );
  }
}

class _RetryView extends StatelessWidget {
  const _RetryView({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 48, color: EpiColors.textMuted),
          const SizedBox(height: EpiSpacing.lg),
          Text(l10n.errorNetwork, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(label: l10n.retry, onPressed: onRetry),
        ],
      ),
    );
  }
}
