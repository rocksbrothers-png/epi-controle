import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/portal_cubit.dart';
import 'portal_sign_screen.dart';

class PortalHomeScreen extends StatelessWidget {
  const PortalHomeScreen({super.key, required this.access});
  final PortalAccess access;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final unsigned = access.deliveries.where((d) => !d.signed).toList();

    return BlocListener<PortalCubit, PortalState>(
      listenWhen: (p, c) => p.signSuccess != c.signSuccess && c.signSuccess,
      listener: (ctx, _) {
        ScaffoldMessenger.of(ctx).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(ctx).portalSignSuccess),
            backgroundColor: EpiColors.success,
          ),
        );
        context.read<PortalCubit>().clearSignSuccess();
      },
      child: DefaultTabController(
        length: 2,
        child: Scaffold(
          body: NestedScrollView(
            headerSliverBuilder: (ctx, innerScrolled) => [
              SliverAppBar(
                pinned: true,
                expandedHeight: 160,
                leading: IconButton(
                  icon: const Icon(Icons.arrow_back_rounded),
                  onPressed: () => context.read<PortalCubit>().reset(),
                ),
                flexibleSpace: FlexibleSpaceBar(
                  background: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [EpiColors.brand, EpiColors.brandDark],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                    ),
                    padding: const EdgeInsets.fromLTRB(
                      EpiSpacing.lg,
                      EpiSpacing.xl5,
                      EpiSpacing.lg,
                      EpiSpacing.md,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            EpiAvatar(name: access.employeeName, size: 44),
                            const SizedBox(width: EpiSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    access.employeeName,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium
                                        ?.copyWith(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w700,
                                        ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  Text(
                                    // Empresa / CNPJ / Unidade: o CNPJ e o
                                    // vinculo juridico do colaborador, nao o da
                                    // empresa contratante. Omitido enquanto o
                                    // schema Multi-CNPJ nao estiver ativo.
                                    [
                                      if (access.companyName.isNotEmpty)
                                        access.companyName,
                                      if (access.legalEntityCnpj.isNotEmpty)
                                        access.legalEntityCnpj,
                                      if (access.unitName.isNotEmpty)
                                        access.unitName,
                                    ].join(' · '),
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(color: Colors.white70),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                bottom: TabBar(
                  labelColor: Colors.white,
                  unselectedLabelColor: Colors.white60,
                  indicatorColor: Colors.white,
                  tabs: [
                    Tab(text: l10n.portalDeliveries),
                    Tab(text: l10n.portalFichas),
                  ],
                ),
              ),
            ],
            body: TabBarView(
              children: [
                _DeliveriesTab(deliveries: access.deliveries),
                _FichasTab(fichas: access.fichas),
              ],
            ),
          ),
          bottomNavigationBar: unsigned.isEmpty
              ? null
              : _SignAllBar(unsigned: unsigned),
        ),
      ),
    );
  }
}

// ── Bottom sign-all bar ────────────────────────────────────────────────────

class _SignAllBar extends StatelessWidget {
  const _SignAllBar({required this.unsigned});
  final List<PortalDelivery> unsigned;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          EpiSpacing.lg,
          EpiSpacing.sm,
          EpiSpacing.lg,
          EpiSpacing.md,
        ),
        child: EpiButton(
          label: '${l10n.portalSignAll} (${unsigned.length})',
          fullWidth: true,
          icon: Icons.draw_rounded,
          onPressed: () => _openSign(context, unsigned),
        ),
      ),
    );
  }

  Future<void> _openSign(
    BuildContext context,
    List<PortalDelivery> deliveries,
  ) async {
    final cubit = context.read<PortalCubit>();
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => BlocProvider.value(
          value: cubit,
          child: PortalSignScreen(
            title: AppLocalizations.of(context).portalSignAll,
            onSign: (sig) => cubit.signBatch(
              deliveries.map((d) => d.id).toList(),
              sig,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Deliveries tab ─────────────────────────────────────────────────────────

class _DeliveriesTab extends StatelessWidget {
  const _DeliveriesTab({required this.deliveries});
  final List<PortalDelivery> deliveries;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (deliveries.isEmpty) {
      return EpiEmptyState(
        title: l10n.portalNoDeliveries,
        icon: Icons.inventory_2_outlined,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.only(
        top: EpiSpacing.sm,
        bottom: EpiSpacing.xl5,
      ),
      itemCount: deliveries.length,
      separatorBuilder: (_, __) => const Divider(height: 1, indent: 72),
      itemBuilder: (_, i) => _DeliveryTile(delivery: deliveries[i]),
    );
  }
}

class _DeliveryTile extends StatelessWidget {
  const _DeliveryTile({required this.delivery});
  final PortalDelivery delivery;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<PortalCubit>();
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: delivery.signed
              ? EpiColors.success.withValues(alpha: 0.1)
              : EpiColors.warning.withValues(alpha: 0.1),
          shape: BoxShape.circle,
        ),
        child: Icon(
          delivery.signed
              ? Icons.check_circle_rounded
              : Icons.pending_rounded,
          color: delivery.signed ? EpiColors.success : EpiColors.warning,
          size: 22,
        ),
      ),
      title: Text(
        delivery.epiName,
        style: Theme.of(context).textTheme.bodyLarge,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        '${l10n.portalQty}: ${delivery.quantity}  •  ${delivery.deliveryDate}',
        style: Theme.of(context)
            .textTheme
            .bodySmall
            ?.copyWith(color: EpiColors.textMuted),
      ),
      trailing: delivery.signed
          ? Text(
              l10n.portalSigned,
              style: Theme.of(context)
                  .textTheme
                  .labelSmall
                  ?.copyWith(color: EpiColors.success),
            )
          : TextButton(
              onPressed: () => _openSign(context, cubit, delivery),
              child: Text(l10n.portalSignDelivery),
            ),
    );
  }

  Future<void> _openSign(
    BuildContext context,
    PortalCubit cubit,
    PortalDelivery delivery,
  ) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => BlocProvider.value(
          value: cubit,
          child: PortalSignScreen(
            title: delivery.epiName,
            onSign: (sig) => cubit.signDelivery(delivery.id, sig),
          ),
        ),
      ),
    );
  }
}

// ── Fichas tab ─────────────────────────────────────────────────────────────

class _FichasTab extends StatelessWidget {
  const _FichasTab({required this.fichas});
  final List<PortalFicha> fichas;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (fichas.isEmpty) {
      return EpiEmptyState(
        title: l10n.noResults,
        icon: Icons.folder_open_outlined,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.only(
        top: EpiSpacing.sm,
        bottom: EpiSpacing.xl5,
      ),
      itemCount: fichas.length,
      separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
      itemBuilder: (_, i) => _FichaTile(ficha: fichas[i]),
    );
  }
}

class _FichaTile extends StatelessWidget {
  const _FichaTile({required this.ficha});
  final PortalFicha ficha;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<PortalCubit>();
    final progress = ficha.totalItems > 0
        ? ficha.signedItems / ficha.totalItems
        : 0.0;
    final color = ficha.isFullySigned ? EpiColors.success : EpiColors.warning;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  ficha.periodLabel,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
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
                  ficha.isFullySigned ? l10n.portalSigned : l10n.portalUnsigned,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: color,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: EpiSpacing.sm),
          LinearProgressIndicator(
            value: progress,
            color: color,
            backgroundColor: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(EpiRadius.full),
            minHeight: 6,
          ),
          const SizedBox(height: EpiSpacing.xs),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${ficha.signedItems}/${ficha.totalItems} ${l10n.portalDeliveries.toLowerCase()}',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: EpiColors.textMuted),
              ),
              if (ficha.hasUnsigned)
                TextButton(
                  onPressed: () => _openSignBatch(context, cubit, ficha),
                  child: Text(l10n.portalSignAll),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _openSignBatch(
    BuildContext context,
    PortalCubit cubit,
    PortalFicha ficha,
  ) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => BlocProvider.value(
          value: cubit,
          child: PortalSignScreen(
            title: ficha.periodLabel,
            onSign: (sig) =>
                cubit.signBatch(ficha.deliveryIds, sig),
          ),
        ),
      ),
    );
  }
}
