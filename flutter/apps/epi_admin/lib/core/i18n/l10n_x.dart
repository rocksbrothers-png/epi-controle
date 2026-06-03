import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';

extension L10nX on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}
