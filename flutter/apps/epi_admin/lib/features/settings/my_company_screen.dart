import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/my_company_cubit.dart';

/// Configurações > Minha Empresa — exclusiva do Administrador Geral (Owner).
///
/// Espelha a tela web: dados cadastrais, identidade/tema, preferências e
/// domínios da tenant (com verificação CNAME/SSL). Upload de imagens
/// (logotipo/favicon) permanece no frontend web.
class MyCompanyScreen extends StatelessWidget {
  const MyCompanyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => MyCompanyCubit()..load(),
      child: const _MyCompanyBody(),
    );
  }
}

class _MyCompanyBody extends StatelessWidget {
  const _MyCompanyBody();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.myCompanyTitle)),
      body: BlocConsumer<MyCompanyCubit, MyCompanyState>(
        listenWhen: (p, c) => p.saved != c.saved || p.error != c.error,
        listener: (ctx, state) {
          if (state.saved) {
            ScaffoldMessenger.of(ctx).showSnackBar(
              SnackBar(content: Text(l10n.myCompanySaved)),
            );
          }
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
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          final profile = state.profile;
          if (profile == null) {
            return Center(child: Text(l10n.myCompanyLoadError));
          }
          return _MyCompanyForm(
            profile: profile,
            domains: state.domains,
            isSaving: state.isSaving,
          );
        },
      ),
    );
  }
}

class _MyCompanyForm extends StatefulWidget {
  const _MyCompanyForm({
    required this.profile,
    required this.domains,
    required this.isSaving,
  });

  final MyCompanyProfile profile;
  final List<TenantDomain> domains;
  final bool isSaving;

  @override
  State<_MyCompanyForm> createState() => _MyCompanyFormState();
}

class _MyCompanyFormState extends State<_MyCompanyForm> {
  late final Map<String, TextEditingController> _fields;
  final _domainController = TextEditingController();
  String _domainType = 'platform_subdomain';
  late String _stockControlScope;

  static const _fieldKeys = [
    'name',
    'legal_name',
    'cnpj',
    'state_registration',
    'municipal_registration',
    'address',
    'contact_phone',
    'whatsapp',
    'contact_email',
    'website',
    'display_name',
    'institutional_message',
    'primary_color',
    'secondary_color',
    'timezone',
  ];

  @override
  void initState() {
    super.initState();
    final p = widget.profile;
    final values = <String, String>{
      'name': p.name,
      'legal_name': p.legalName,
      'cnpj': p.cnpj,
      'state_registration': p.stateRegistration,
      'municipal_registration': p.municipalRegistration,
      'address': p.address,
      'contact_phone': p.contactPhone,
      'whatsapp': p.whatsapp,
      'contact_email': p.contactEmail,
      'website': p.website,
      'display_name': p.displayName,
      'institutional_message': p.institutionalMessage,
      'primary_color': p.primaryColor,
      'secondary_color': p.secondaryColor,
      'timezone': p.timezone,
    };
    _fields = {
      for (final key in _fieldKeys)
        key: TextEditingController(text: values[key] ?? ''),
    };
    _stockControlScope = widget.profile.stockControlScope;
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    _domainController.dispose();
    super.dispose();
  }

  void _save() {
    final body = <String, dynamic>{
      for (final entry in _fields.entries) entry.key: entry.value.text.trim(),
      'stock_control_scope': _stockControlScope,
    };
    context.read<MyCompanyCubit>().save(body);
  }

  String _domainStatusLabel(AppLocalizations l10n, String status) {
    switch (status) {
      case 'verified':
      case 'active':
        return l10n.myCompanyDomainVerified;
      case 'failed':
        return l10n.myCompanyDomainFailed;
      default:
        return l10n.myCompanyDomainPending;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final p = widget.profile;
    return ListView(
      padding: const EdgeInsets.all(EpiSpacing.lg),
      children: [
        // Contrato — somente leitura (administrado pelo Master)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(EpiSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.myCompanyContractSection,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: EpiSpacing.sm),
                Text('${l10n.myCompanyPlan}: ${p.planName}'),
                Text('${l10n.myCompanyUserLimit}: ${p.userLimit}'),
                Text('${l10n.myCompanyLicense}: ${p.licenseStatus}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: EpiSpacing.lg),
        _SectionTitle(label: l10n.myCompanyRegistrationSection),
        _field('name', l10n.myCompanyName),
        _field('legal_name', l10n.myCompanyLegalName),
        _field('cnpj', l10n.myCompanyCnpj),
        _field('state_registration', l10n.myCompanyStateRegistration),
        _field('municipal_registration', l10n.myCompanyMunicipalRegistration),
        _field('address', l10n.myCompanyAddress),
        _field('contact_phone', l10n.myCompanyPhone),
        _field('whatsapp', l10n.myCompanyWhatsapp),
        _field('contact_email', l10n.myCompanyEmail),
        _field('website', l10n.myCompanyWebsite),
        const SizedBox(height: EpiSpacing.lg),
        _SectionTitle(label: l10n.myCompanyIdentitySection),
        _field('display_name', l10n.myCompanyDisplayName),
        _field('institutional_message', l10n.myCompanyInstitutionalMessage),
        _field('primary_color', l10n.myCompanyPrimaryColor),
        _field('secondary_color', l10n.myCompanySecondaryColor),
        const SizedBox(height: EpiSpacing.lg),
        _SectionTitle(label: l10n.myCompanyPreferencesSection),
        _field('timezone', l10n.myCompanyTimezone),
        _stockScopeField(l10n),
        const SizedBox(height: EpiSpacing.lg),
        FilledButton(
          onPressed: widget.isSaving ? null : _save,
          child: widget.isSaving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(l10n.myCompanySave),
        ),
        const SizedBox(height: EpiSpacing.xl),
        _SectionTitle(label: l10n.myCompanyDomainsSection),
        ...widget.domains.map((d) => _DomainTile(
              domain: d,
              statusLabel: _domainStatusLabel(l10n, d.verificationStatus),
              sslLabel: _domainStatusLabel(l10n, d.sslStatus),
            )),
        const SizedBox(height: EpiSpacing.sm),
        TextField(
          controller: _domainController,
          decoration: InputDecoration(labelText: l10n.myCompanyDomainField),
        ),
        const SizedBox(height: EpiSpacing.sm),
        DropdownButtonFormField<String>(
          initialValue: _domainType,
          items: [
            DropdownMenuItem(
              value: 'platform_subdomain',
              child: Text(l10n.myCompanyDomainTypePlatform),
            ),
            DropdownMenuItem(
              value: 'custom_subdomain',
              child: Text(l10n.myCompanyDomainTypeCustomSub),
            ),
            DropdownMenuItem(
              value: 'custom_domain',
              child: Text(l10n.myCompanyDomainTypeCustom),
            ),
          ],
          onChanged: (value) =>
              setState(() => _domainType = value ?? 'platform_subdomain'),
        ),
        const SizedBox(height: EpiSpacing.sm),
        OutlinedButton(
          onPressed: () {
            final domain = _domainController.text.trim();
            if (domain.isEmpty) return;
            context.read<MyCompanyCubit>().registerDomain(domain, _domainType);
            _domainController.clear();
          },
          child: Text(l10n.myCompanyDomainAdd),
        ),
        const SizedBox(height: EpiSpacing.xl5),
      ],
    );
  }

  /// Consolidação de saldos — deliberadamente NÃO se chama "controlar estoque".
  ///
  /// O rótulo antigo induzia à leitura de que a configuração escolheria de onde
  /// o material sai. O texto auxiliar existe para fechar essa porta: a decisão
  /// do ADR-0001 §15 é que o estoque pertence sempre a uma unidade.
  Widget _stockScopeField(AppLocalizations l10n) {
    final options = <String, String>{
      'unit': l10n.myCompanyStockScopeUnit,
      'legal_entity': l10n.myCompanyStockScopeLegalEntity,
      'company': l10n.myCompanyStockScopeCompany,
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: EpiSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          DropdownButtonFormField<String>(
            initialValue: options.containsKey(_stockControlScope)
                ? _stockControlScope
                : 'company',
            isExpanded: true,
            decoration: InputDecoration(labelText: l10n.myCompanyStockScope),
            items: options.entries
                .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                .toList(),
            onChanged: (value) =>
                setState(() => _stockControlScope = value ?? 'company'),
          ),
          const SizedBox(height: EpiSpacing.xs),
          Text(
            l10n.myCompanyStockScopeHint,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: EpiColors.textMuted,
                ),
          ),
        ],
      ),
    );
  }

  Widget _field(String key, String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: EpiSpacing.sm),
      child: TextField(
        controller: _fields[key],
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: EpiSpacing.sm),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: EpiColors.brand,
              letterSpacing: 0.5,
            ),
      ),
    );
  }
}

class _DomainTile extends StatelessWidget {
  const _DomainTile({
    required this.domain,
    required this.statusLabel,
    required this.sslLabel,
  });

  final TenantDomain domain;
  final String statusLabel;
  final String sslLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final subtitleLines = <String>[
      '${domain.typeLabel} · $statusLabel · SSL: $sslLabel',
      if (!domain.isVerified && domain.domainType != 'platform_subdomain') ...[
        '${l10n.myCompanyDomainCname}: ${domain.cnameTarget}',
        '${l10n.myCompanyDomainTxt}: ${domain.txtRecord}',
        '${l10n.myCompanyDomainToken}: ${domain.verificationToken}',
      ],
    ];
    return Card(
      child: ListTile(
        title: Text(
          domain.isPrimary
              ? '${domain.fullHost} · ${l10n.myCompanyDomainPrimary}'
              : domain.fullHost,
        ),
        subtitle: Text(subtitleLines.join('\n')),
        isThreeLine: subtitleLines.length > 1,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!domain.isVerified)
              IconButton(
                icon: const Icon(Icons.verified_outlined),
                tooltip: l10n.myCompanyDomainVerify,
                onPressed: () =>
                    context.read<MyCompanyCubit>().verifyDomain(domain.id),
              ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: l10n.myCompanyDomainDelete,
              onPressed: () =>
                  context.read<MyCompanyCubit>().deleteDomain(domain.id),
            ),
          ],
        ),
      ),
    );
  }
}
