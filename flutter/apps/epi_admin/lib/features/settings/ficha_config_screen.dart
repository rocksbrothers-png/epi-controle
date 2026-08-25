import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import '../../core/bloc/auth_cubit.dart';
import '../../core/bloc/auth_state.dart';
import '../../core/bloc/settings_cubit.dart';
import 'widgets/settings_page.dart';

/// Configurações → Ficha de EPI.
///
/// Textos impressos na Ficha Individual de Controle de EPI (título,
/// declaração, observações e o rótulo de rastreabilidade do rodapé). Era uma
/// das seções empilhadas na tela única de Configurações; virou subtela própria
/// porque é um formulário, não um interruptor — e formulário no meio de uma
/// lista de opções é o que tornava a tela ilegível.
class FichaConfigScreen extends StatelessWidget {
  const FichaConfigScreen({super.key, this.companyId});

  /// Empresa em edição, vinda de `?company_id=` — só o `master_admin` a
  /// preenche (ver [settingsCompanyMissing]). Admins de empresa mandam `null`
  /// e o backend resolve a própria.
  final int? companyId;

  @override
  Widget build(BuildContext context) {
    final authState = context.read<AuthCubit>().state;
    final isMaster = authState is AuthAuthenticated &&
        authState.sessionContext.role == 'master_admin';
    return BlocProvider(
      create: (_) => SettingsCubit()
        ..initForCompany(isMaster: isMaster, companyId: companyId),
      child: _FichaConfigBody(companyId: companyId),
    );
  }
}

class _FichaConfigBody extends StatelessWidget {
  const _FichaConfigBody({this.companyId});

  final int? companyId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SettingsSubPage(
      title: l10n.settingsFichaTileTitle,
      child: settingsCompanyMissing(context, companyId)
          ? const SettingsCompanyRequired()
          : BlocConsumer<SettingsCubit, SettingsState>(
              listenWhen: (p, c) =>
                  p.successMessage != c.successMessage || p.error != c.error,
              listener: (ctx, state) {
                if (state.successMessage != null) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                    SnackBar(
                      content: Text(AppLocalizations.of(ctx).settingsSaved),
                    ),
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
                  return const Padding(
                    padding: EdgeInsets.all(EpiSpacing.xl),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _FichaConfigForm(
                  config: state.config ?? const FichaConfig(),
                  isSaving: state.isSaving,
                );
              },
            ),
    );
  }
}

// ── Ficha config form ──────────────────────────────────────────────────────

class _FichaConfigForm extends StatefulWidget {
  const _FichaConfigForm({required this.config, required this.isSaving});
  final FichaConfig config;
  final bool isSaving;

  @override
  State<_FichaConfigForm> createState() => _FichaConfigFormState();
}

class _FichaConfigFormState extends State<_FichaConfigForm> {
  late final TextEditingController _titulo;
  late final TextEditingController _declaracao;
  late final TextEditingController _observacoes;
  late final TextEditingController _rastreabilidade;

  @override
  void initState() {
    super.initState();
    _titulo = TextEditingController(text: widget.config.titulo);
    _declaracao = TextEditingController(text: widget.config.declaracao);
    _observacoes = TextEditingController(text: widget.config.observacoes);
    _rastreabilidade = TextEditingController(text: widget.config.rastreabilidade);
  }

  @override
  void didUpdateWidget(_FichaConfigForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.config != widget.config) {
      _titulo.text = widget.config.titulo;
      _declaracao.text = widget.config.declaracao;
      _observacoes.text = widget.config.observacoes;
      _rastreabilidade.text = widget.config.rastreabilidade;
    }
  }

  @override
  void dispose() {
    _titulo.dispose();
    _declaracao.dispose();
    _observacoes.dispose();
    _rastreabilidade.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _titulo,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaTitle,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _declaracao,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaDeclaration,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.md),
          TextField(
            controller: _observacoes,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaObservations,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
          ),
          const SizedBox(height: EpiSpacing.md),
          // Rótulo de rastreabilidade impresso no rodapé da ficha (texto
          // livre — o backend trata como String, não como liga/desliga).
          TextField(
            controller: _rastreabilidade,
            decoration: InputDecoration(
              labelText: l10n.settingsFichaTracking,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: EpiSpacing.lg),
          EpiButton(
            label: l10n.save,
            loading: widget.isSaving,
            fullWidth: true,
            onPressed: widget.isSaving ? null : _save,
          ),
        ],
      ),
    );
  }

  void _save() {
    context.read<SettingsCubit>().save(
          widget.config.copyWith(
            titulo: _titulo.text,
            declaracao: _declaracao.text,
            observacoes: _observacoes.text,
            rastreabilidade: _rastreabilidade.text,
          ),
        );
  }
}
