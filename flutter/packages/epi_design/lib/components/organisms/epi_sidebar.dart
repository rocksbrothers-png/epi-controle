/// Sidebar de navegação lateral com suporte a colapso, badges e sub-items.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

/// Item de navegação da sidebar.
class EpiNavItem {
  const EpiNavItem({
    required this.icon,
    required this.label,
    this.badge,
    this.children = const [],
  });

  final IconData        icon;
  final String          label;
  final int?            badge;
  final List<EpiNavItem> children;
}

class EpiSidebar extends StatelessWidget {
  const EpiSidebar({
    super.key,
    required this.items,
    required this.selectedIndex,
    required this.onItemSelected,
    this.collapsed   = false,
    this.onCollapse,
    this.header,
  });

  final List<EpiNavItem>  items;
  final int               selectedIndex;
  final ValueChanged<int> onItemSelected;
  final bool              collapsed;
  final VoidCallback?     onCollapse;
  final Widget?           header;

  static const double _expanded  = 240;
  static const double _collapsed = 64;

  @override
  Widget build(BuildContext context) {
    final isDark      = Theme.of(context).brightness == Brightness.dark;
    final bgColor     = isDark ? EpiColors.darkSurface : EpiColors.surface;
    final borderColor = isDark ? EpiColors.darkBorder : EpiColors.border;
    final width       = collapsed ? _collapsed : _expanded;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeInOut,
      width: width,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(right: BorderSide(color: borderColor)),
      ),
      child: Column(
        children: [
          // Header / Logo area
          if (header != null)
            SizedBox(
              height: 60,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.md),
                child: collapsed
                    ? const Center(
                        child: Icon(Icons.security_rounded, color: EpiColors.brand, size: 24),
                      )
                    : header!,
              ),
            )
          else
            SizedBox(
              height: 60,
              child: Center(
                child: collapsed
                    ? const Icon(Icons.security_rounded, color: EpiColors.brand, size: 24)
                    : Padding(
                        padding: const EdgeInsets.symmetric(horizontal: EpiSpacing.lg),
                        child: Row(
                          children: [
                            const Icon(Icons.security_rounded, color: EpiColors.brand, size: 24),
                            const SizedBox(width: EpiSpacing.sm),
                            Text(
                              'EPI Controle',
                              style: EpiTypography.titleLarge.copyWith(
                                color: EpiColors.brand,
                              ),
                            ),
                          ],
                        ),
                      ),
              ),
            ),
          Divider(height: 1, thickness: 1, color: borderColor),
          // Nav items
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: EpiSpacing.sm),
              itemCount: items.length,
              itemBuilder: (_, i) => _NavItemTile(
                item: items[i],
                index: i,
                selected: selectedIndex == i,
                collapsed: collapsed,
                onTap: () => onItemSelected(i),
              ),
            ),
          ),
          // Collapse toggle
          if (onCollapse != null) ...[
            Divider(height: 1, thickness: 1, color: borderColor),
            _CollapseButton(collapsed: collapsed, onCollapse: onCollapse!),
          ],
        ],
      ),
    );
  }
}

class _NavItemTile extends StatelessWidget {
  const _NavItemTile({
    required this.item,
    required this.index,
    required this.selected,
    required this.collapsed,
    required this.onTap,
  });

  final EpiNavItem  item;
  final int         index;
  final bool        selected;
  final bool        collapsed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark     = Theme.of(context).brightness == Brightness.dark;
    final activeBg   = isDark
        ? EpiColors.brand.withOpacity(0.15)
        : EpiColors.brandSoft;
    final activeColor = EpiColors.brand;
    final inactiveColor = isDark ? const Color(0xFF8A9590) : EpiColors.textMuted;
    final fg = selected ? activeColor : inactiveColor;

    return Tooltip(
      message: collapsed ? item.label : '',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(EpiRadius.sm),
        child: Container(
          margin: const EdgeInsets.symmetric(
            horizontal: EpiSpacing.sm,
            vertical: 2,
          ),
          padding: EdgeInsets.symmetric(
            horizontal: collapsed ? 0 : EpiSpacing.md,
            vertical: EpiSpacing.sm + 2,
          ),
          decoration: selected
              ? BoxDecoration(
                  color: activeBg,
                  borderRadius: BorderRadius.circular(EpiRadius.sm),
                )
              : null,
          child: collapsed
              ? Stack(
                  alignment: Alignment.center,
                  children: [
                    Center(child: Icon(item.icon, size: 22, color: fg)),
                    if (item.badge != null && item.badge! > 0)
                      Positioned(
                        top: 0,
                        right: 0,
                        child: _Badge(count: item.badge!),
                      ),
                  ],
                )
              : Row(
                  children: [
                    Icon(item.icon, size: 20, color: fg),
                    const SizedBox(width: EpiSpacing.md),
                    Expanded(
                      child: Text(
                        item.label,
                        style: EpiTypography.labelLarge.copyWith(
                          color: fg,
                          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (item.badge != null && item.badge! > 0)
                      _Badge(count: item.badge!),
                  ],
                ),
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: EpiColors.danger,
        borderRadius: BorderRadius.circular(EpiRadius.full),
      ),
      child: Text(
        count > 99 ? '99+' : '$count',
        style: EpiTypography.labelSmall.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _CollapseButton extends StatelessWidget {
  const _CollapseButton({required this.collapsed, required this.onCollapse});
  final bool         collapsed;
  final VoidCallback onCollapse;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onCollapse,
      child: Padding(
        padding: const EdgeInsets.all(EpiSpacing.lg),
        child: Row(
          mainAxisAlignment: collapsed
              ? MainAxisAlignment.center
              : MainAxisAlignment.end,
          children: [
            Icon(
              collapsed
                  ? Icons.chevron_right_rounded
                  : Icons.chevron_left_rounded,
              size: 20,
              color: EpiColors.textMuted,
            ),
          ],
        ),
      ),
    );
  }
}
