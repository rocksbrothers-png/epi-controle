import 'package:flutter/material.dart';
import '../../core/i18n/l10n_x.dart';

String libraryCategory(BuildContext context, String id) => switch (id) {
  'epi_matrix' => context.l10n.safetyCategoryEpi,
  'glove_matrix' => context.l10n.safetyCategoryGlove,
  'care_guides' => context.l10n.safetyCategoryCare,
  'use_instructions' => context.l10n.safetyCategoryUse,
  'technical_manuals' => context.l10n.safetyCategoryTechnical,
  _ => context.l10n.safetyCategoryOther,
};
String libraryState(BuildContext context, String id) => switch (id) {
  'draft' => context.l10n.safetyStateDraft,
  'published' => context.l10n.safetyStatePublished,
  'superseded' => context.l10n.safetyStateSuperseded,
  _ => context.l10n.safetyStateArchived,
};
