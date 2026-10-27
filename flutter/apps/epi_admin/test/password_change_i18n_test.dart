import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/auth/change_password_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final locale in [
    const Locale('pt', 'BR'),
    const Locale('en', 'US'),
    const Locale('es', 'ES'),
    const Locale('fr', 'FR'),
    const Locale('no', 'NO'),
  ]) {
    testWidgets(
      'password labels and existing validation rules $locale without requests',
      (tester) async {
        final l = (await tester.runAsync(
          () => AppLocalizations.delegate.load(locale),
        ))!;
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          MaterialApp(
            locale: locale,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const ChangePasswordScreen(),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text(l.passwordChangeTitle), findsOneWidget);
        expect(find.text(l.passwordChangeIntro), findsOneWidget);
        final fields = find.byType(TextFormField);
        expect(fields, findsNWidgets(3));
        Future<void> submit() async {
          final button = find.text(l.passwordChangeSave);
          await tester.ensureVisible(button);
          await tester.tap(button);
          await tester.pumpAndSettle();
        }

        await submit();
        expect(find.text(l.passwordChangeCurrentRequired), findsOneWidget);
        expect(find.text(l.passwordChangeMinLength), findsOneWidget);
        await tester.enterText(fields.at(0), 'temporary1');
        await tester.enterText(fields.at(1), 'short');
        await submit();
        expect(find.text(l.passwordChangeMinLength), findsOneWidget);
        await tester.enterText(fields.at(1), 'temporary1');
        await tester.enterText(fields.at(2), 'different');
        await submit();
        expect(find.text(l.passwordChangeMustDiffer), findsOneWidget);
        expect(find.text(l.passwordChangeMismatch), findsOneWidget);
        // All submissions above fail the same preexisting local rules. No API
        // client is initialized, so an accidental network attempt fails the test.
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets(
    'validation messages follow locale changes and preserve entered passwords',
    (tester) async {
      final locale = ValueNotifier(const Locale('pt', 'BR'));
      addTearDown(locale.dispose);
      await tester.runAsync(() => AppLocalizations.delegate.load(locale.value));
      await tester.pumpWidget(
        ValueListenableBuilder<Locale>(
          valueListenable: locale,
          builder: (context, value, child) => MaterialApp(
            locale: value,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const ChangePasswordScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), 'Original temporary');
      await tester.enterText(fields.at(1), 'short');
      await tester.enterText(fields.at(2), 'different');
      var l = AppLocalizations.of(
        tester.element(find.byType(ChangePasswordScreen)),
      );
      await tester.ensureVisible(find.text(l.passwordChangeSave));
      await tester.tap(find.text(l.passwordChangeSave));
      await tester.pumpAndSettle();
      expect(find.text(l.passwordChangeMinLength), findsOneWidget);
      for (final target in [
        const Locale('fr', 'FR'),
        const Locale('en', 'US'),
      ]) {
        final oldMessage = l.passwordChangeMinLength;
        locale.value = target;
        await tester.pump();
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        l = AppLocalizations.of(
          tester.element(find.byType(ChangePasswordScreen)),
        );
        expect(find.text(oldMessage), findsNothing);
        expect(find.text(l.passwordChangeMinLength), findsOneWidget);
        expect(find.text(l.passwordChangeMismatch), findsOneWidget);
        expect(
          tester.widget<TextFormField>(fields.at(0)).controller!.text,
          'Original temporary',
        );
        expect(
          tester.widget<TextFormField>(fields.at(1)).controller!.text,
          'short',
        );
        expect(
          tester.widget<TextFormField>(fields.at(2)).controller!.text,
          'different',
        );
      }
      expect(tester.takeException(), isNull);
    },
  );
}
