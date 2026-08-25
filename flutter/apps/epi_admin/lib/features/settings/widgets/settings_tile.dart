import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';

/// Largura máxima do conteúdo de Configurações.
///
/// A tela nasceu como uma lista única esticada de ponta a ponta: no Web, com a
/// sidebar aberta, os campos passavam de 1.400 px e a leitura de um formulário
/// virava um varrer de olhos horizontal. Todo conteúdo de Configurações
/// (o hub e as subtelas) passa por [SettingsContent], que centraliza e limita.
const double kSettingsMaxWidth = 900;

/// Conteúdo de Configurações centralizado e limitado a [kSettingsMaxWidth].
class SettingsContent extends StatelessWidget {
  const SettingsContent({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: kSettingsMaxWidth),
        child: child,
      ),
    );
  }
}

/// Um grupo do hub de Configurações: rótulo da seção + cartão com os itens.
///
/// Os itens vêm separados por divisores para que cada grupo seja lido como uma
/// "pasta" — que é justamente o que a tela única não deixava enxergar.
class SettingsSection extends StatelessWidget {
  const SettingsSection({
    super.key,
    required this.label,
    required this.children,
  });

  final String label;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final tiles = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      if (i > 0) {
        tiles.add(
          const Divider(height: 1, indent: EpiSpacing.lg, endIndent: EpiSpacing.lg),
        );
      }
      tiles.add(children[i]);
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        EpiSpacing.lg,
        EpiSpacing.lg,
        EpiSpacing.lg,
        0,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              EpiSpacing.xs,
              0,
              EpiSpacing.xs,
              EpiSpacing.sm,
            ),
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: EpiColors.brand,
                    letterSpacing: 0.5,
                  ),
            ),
          ),
          EpiCard(
            padding: const EdgeInsets.symmetric(vertical: EpiSpacing.xs),
            // `Material` transparente entre o cartão e os itens: o `EpiCard`
            // pinta o fundo num `DecoratedBox`, e o `ListTile` desenha o
            // realce do toque no `Material` mais próximo — que sem isto fica
            // ATRÁS do cartão. O resultado seria um item que não responde ao
            // clique aos olhos do usuário (e um assert do framework em debug).
            child: Material(
              type: MaterialType.transparency,
              child: Column(children: tiles),
            ),
          ),
        ],
      ),
    );
  }
}

/// Item do hub: ícone da função, título, descrição e chevron de navegação.
class SettingsTile extends StatelessWidget {
  const SettingsTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: EpiSpacing.lg,
        vertical: EpiSpacing.xs,
      ),
      leading: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          // Tinta da marca com alfa em vez de `brandSoft` sólido: o mesmo
          // quadrado funciona sobre a superfície clara e a escura.
          color: EpiColors.brand.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(EpiRadius.md),
        ),
        child: Icon(icon, size: 22, color: EpiColors.brand),
      ),
      title: Text(title, style: theme.textTheme.titleSmall),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Text(
          subtitle,
          style: theme.textTheme.bodySmall?.copyWith(color: EpiColors.textMuted),
        ),
      ),
      trailing: const Icon(
        Icons.chevron_right_rounded,
        color: EpiColors.textMuted,
      ),
    );
  }
}
