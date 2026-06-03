import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../core/bloc/portal_cubit.dart';
import 'portal_home_screen.dart';

/// Root widget — provides PortalCubit and delegates to sub-screens.
class PortalScreen extends StatelessWidget {
  const PortalScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => PortalCubit(),
      child: const _PortalFlow(),
    );
  }
}

class _PortalFlow extends StatelessWidget {
  const _PortalFlow();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<PortalCubit, PortalState>(
      builder: (ctx, state) {
        if (state.isLoaded) {
          return PortalHomeScreen(access: state.access!);
        }
        if (state.status == PortalStatus.error) {
          return _PortalErrorScreen(message: state.error ?? '');
        }
        return const _PortalEntryScreen();
      },
    );
  }
}

// ── Entry screen ───────────────────────────────────────────────────────────

class _PortalEntryScreen extends StatefulWidget {
  const _PortalEntryScreen();

  @override
  State<_PortalEntryScreen> createState() => _PortalEntryScreenState();
}

class _PortalEntryScreenState extends State<_PortalEntryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _cpfController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _cpfController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<PortalCubit>();
    final isLoading = context.select(
      (PortalCubit c) => c.state.status == PortalStatus.loading,
    );

    return Scaffold(
      backgroundColor: EpiColors.brand,
      body: SafeArea(
        child: Column(
          children: [
            // ── Header ────────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(
                EpiSpacing.lg,
                EpiSpacing.xl2,
                EpiSpacing.lg,
                EpiSpacing.xl,
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.shield_rounded,
                    color: Colors.white,
                    size: 32,
                  ),
                  const SizedBox(width: EpiSpacing.md),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.portalTitle,
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      Text(
                        l10n.appName,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: Colors.white70),
                      ),
                    ],
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, color: Colors.white),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            // ── Card ──────────────────────────────────────────────────────
            Expanded(
              child: Container(
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(EpiRadius.xl),
                  ),
                ),
                child: Column(
                  children: [
                    const SizedBox(height: EpiSpacing.lg),
                    TabBar(
                      controller: _tabController,
                      tabs: [
                        Tab(
                          icon: const Icon(Icons.badge_outlined),
                          text: l10n.portalEnterCpf,
                        ),
                        Tab(
                          icon: const Icon(Icons.qr_code_scanner_rounded),
                          text: l10n.portalScanQr,
                        ),
                      ],
                    ),
                    Expanded(
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          // CPF tab
                          _CpfTab(
                            controller: _cpfController,
                            isLoading: isLoading,
                            onSubmit: () =>
                                cubit.lookupByCpf(_cpfController.text),
                          ),
                          // QR tab
                          _QrTab(
                            onDetect: (token) => cubit.loadFromToken(token),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── CPF tab ────────────────────────────────────────────────────────────────

class _CpfTab extends StatelessWidget {
  const _CpfTab({
    required this.controller,
    required this.isLoading,
    required this.onSubmit,
  });
  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(EpiSpacing.xl2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: EpiSpacing.lg),
          Text(
            l10n.portalEnterCpf,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: EpiSpacing.lg),
          TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              _CpfInputFormatter(),
            ],
            decoration: InputDecoration(
              hintText: l10n.portalCpfHint,
              prefixIcon: const Icon(Icons.badge_outlined),
              border: const OutlineInputBorder(),
            ),
            onSubmitted: (_) => onSubmit(),
          ),
          const SizedBox(height: EpiSpacing.xl),
          EpiButton(
            label: l10n.portalCpfVerify,
            loading: isLoading,
            fullWidth: true,
            onPressed: isLoading ? null : onSubmit,
          ),
        ],
      ),
    );
  }
}

class _CpfInputFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final buf = StringBuffer();
    for (var i = 0; i < digits.length && i < 11; i++) {
      if (i == 3 || i == 6) buf.write('.');
      if (i == 9) buf.write('-');
      buf.write(digits[i]);
    }
    final formatted = buf.toString();
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}

// ── QR tab ─────────────────────────────────────────────────────────────────

class _QrTab extends StatefulWidget {
  const _QrTab({required this.onDetect});
  final ValueChanged<String> onDetect;

  @override
  State<_QrTab> createState() => _QrTabState();
}

class _QrTabState extends State<_QrTab> {
  late final MobileScannerController _controller;
  bool _scanned = false;

  @override
  void initState() {
    super.initState();
    _controller = MobileScannerController(
      detectionSpeed: DetectionSpeed.noDuplicates,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.only(
        bottomLeft: Radius.circular(EpiRadius.xl),
        bottomRight: Radius.circular(EpiRadius.xl),
      ),
      child: MobileScanner(
        controller: _controller,
        onDetect: (capture) {
          if (_scanned) return;
          final value = capture.barcodes.firstOrNull?.rawValue;
          if (value == null) return;
          setState(() => _scanned = true);
          widget.onDetect(value);
        },
      ),
    );
  }
}

// ── Error screen ───────────────────────────────────────────────────────────

class _PortalErrorScreen extends StatelessWidget {
  const _PortalErrorScreen({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final cubit = context.read<PortalCubit>();
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(EpiSpacing.xl2),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.error_outline_rounded,
                  size: 64,
                  color: EpiColors.danger,
                ),
                const SizedBox(height: EpiSpacing.lg),
                Text(
                  l10n.errorGeneric,
                  style: Theme.of(context).textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: EpiSpacing.sm),
                Text(
                  message,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: EpiColors.textMuted),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: EpiSpacing.xl2),
                EpiButton(
                  label: l10n.retry,
                  fullWidth: true,
                  onPressed: cubit.reset,
                ),
                const SizedBox(height: EpiSpacing.md),
                EpiButton(
                  label: l10n.back,
                  variant: EpiButtonVariant.ghost,
                  fullWidth: true,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
