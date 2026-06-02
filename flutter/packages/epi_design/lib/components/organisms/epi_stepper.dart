// Stepper de progresso com indicador visual numerado e linha conectora.
import 'package:flutter/material.dart';
import '../../tokens/colors.dart';
import '../../tokens/spacing.dart';
import '../../tokens/typography.dart';

/// Define um passo no EpiStepper.
class EpiStep {
  const EpiStep({
    required this.title,
    this.subtitle,
    required this.content,
    this.isCompleted = false,
  });

  final String  title;
  final String? subtitle;
  final Widget  content;
  final bool    isCompleted;
}

class EpiStepper extends StatelessWidget {
  const EpiStepper({
    super.key,
    required this.steps,
    required this.currentStep,
    this.onStepTap,
  });

  final List<EpiStep>      steps;
  final int                currentStep;
  final ValueChanged<int>? onStepTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Step indicators
        Row(
          children: List.generate(steps.length * 2 - 1, (i) {
            if (i.isOdd) {
              // Connector line
              final stepIndex = i ~/ 2;
              final isPast = stepIndex < currentStep;
              return Expanded(
                child: Container(
                  height: 2,
                  color: isPast ? EpiColors.success : EpiColors.border,
                ),
              );
            }
            final stepIndex = i ~/ 2;
            return _StepIndicator(
              index: stepIndex,
              isActive: stepIndex == currentStep,
              isCompleted: steps[stepIndex].isCompleted || stepIndex < currentStep,
              onTap: onStepTap != null ? () => onStepTap!(stepIndex) : null,
            );
          }),
        ),
        const SizedBox(height: EpiSpacing.lg),
        // Step titles row
        Row(
          children: List.generate(steps.length * 2 - 1, (i) {
            if (i.isOdd) return const Expanded(child: SizedBox.shrink());
            final stepIndex = i ~/ 2;
            final step      = steps[stepIndex];
            final isActive  = stepIndex == currentStep;
            final isDark    = Theme.of(context).brightness == Brightness.dark;
            final labelColor = isActive
                ? EpiColors.brand
                : (isDark ? const Color(0xFF8A9590) : EpiColors.textMuted);
            return Expanded(
              child: Column(
                children: [
                  Text(
                    step.title,
                    textAlign: TextAlign.center,
                    style: EpiTypography.labelMedium.copyWith(
                      color: labelColor,
                      fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (step.subtitle != null)
                    Text(
                      step.subtitle!,
                      textAlign: TextAlign.center,
                      style: EpiTypography.labelSmall.copyWith(color: labelColor),
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            );
          }),
        ),
        const SizedBox(height: EpiSpacing.xl2),
        // Active step content
        if (currentStep >= 0 && currentStep < steps.length)
          steps[currentStep].content,
      ],
    );
  }
}

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({
    required this.index,
    required this.isActive,
    required this.isCompleted,
    this.onTap,
  });

  final int           index;
  final bool          isActive;
  final bool          isCompleted;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Color bg;
    final Color fg;
    final Color border;

    if (isCompleted) {
      bg     = EpiColors.success;
      fg     = Colors.white;
      border = EpiColors.success;
    } else if (isActive) {
      bg     = EpiColors.brand;
      fg     = Colors.white;
      border = EpiColors.brand;
    } else {
      bg     = Colors.transparent;
      fg     = EpiColors.textMuted;
      border = EpiColors.border;
    }

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: bg,
          shape: BoxShape.circle,
          border: Border.all(color: border, width: 2),
        ),
        alignment: Alignment.center,
        child: isCompleted
            ? const Icon(Icons.check_rounded, size: 16, color: Colors.white)
            : Text(
                '${index + 1}',
                style: EpiTypography.labelMedium.copyWith(
                  color: fg,
                  fontWeight: FontWeight.w700,
                ),
              ),
      ),
    );
  }
}
