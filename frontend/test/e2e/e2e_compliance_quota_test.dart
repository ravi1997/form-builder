import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/compliance/presentation/pages/compliance_page.dart';

void main() {
  group('Compliance & Storage Quota E2E Widget Tests (Tiers 1-2)', () {
    void setupScreen(WidgetTester tester) {
      tester.view.physicalSize = const Size(1200, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
    }

    testWidgets('T21, T22: Storage quota over 80% shows warning threshold banner', (WidgetTester tester) async {
      setupScreen(tester);

      // 850 MB used of 1024 MB = 83.0% (over 80% warning threshold)
      await tester.pumpWidget(
        const MaterialApp(
          home: CompliancePage(
            initialUsedBytes: 850 * 1024 * 1024,
          ),
        ),
      );

      expect(find.text('Admin Compliance & Settings'), findsOneWidget);
      expect(find.textContaining('83.0% Used'), findsOneWidget);
      expect(find.textContaining('Warning: Near storage limit'), findsOneWidget);
      expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);

      final progressIndicator = tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator));
      expect(progressIndicator.value, closeTo(0.830, 0.001));
    });

    testWidgets('T21: Storage quota under 80% does not show warning threshold banner', (WidgetTester tester) async {
      setupScreen(tester);

      // 500 MB used of 1024 MB = 48.8% (under 80% warning threshold)
      await tester.pumpWidget(
        const MaterialApp(
          home: CompliancePage(
            initialUsedBytes: 500 * 1024 * 1024,
          ),
        ),
      );

      expect(find.textContaining('48.8% Used'), findsOneWidget);
      expect(find.textContaining('Warning: Near storage limit'), findsNothing);
      expect(find.byIcon(Icons.warning_amber_rounded), findsNothing);

      final progressIndicator = tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator));
      expect(progressIndicator.value, closeTo(0.488, 0.001));
    });

    testWidgets('T24: Toggling legal hold switch changes state', (WidgetTester tester) async {
      setupScreen(tester);

      await tester.pumpWidget(
        const MaterialApp(
          home: CompliancePage(),
        ),
      );

      final switchFinders = find.byType(Switch);
      expect(switchFinders, findsNWidgets(2));

      // First switch (GDPR Audit Retention) is active (true)
      final firstSwitch = tester.widget<Switch>(switchFinders.at(0));
      expect(firstSwitch.value, isTrue);

      // Second switch (HIPAA Compliance Retainer) is inactive (false)
      final secondSwitch = tester.widget<Switch>(switchFinders.at(1));
      expect(secondSwitch.value, isFalse);

      // Tap the second switch to toggle it
      await tester.tap(switchFinders.at(1));
      await tester.pumpAndSettle();

      // Verify the value updated in the UI
      final secondSwitchUpdated = tester.widget<Switch>(switchFinders.at(1));
      expect(secondSwitchUpdated.value, isTrue);
    });

    testWidgets('T24: Add new legal hold via dialog and verify list rendering', (WidgetTester tester) async {
      setupScreen(tester);

      await tester.pumpWidget(
        const MaterialApp(
          home: CompliancePage(),
        ),
      );

      // Verify new hold does not exist yet
      expect(find.text('E2E Audit Hold'), findsNothing);

      // Tap "Add Legal Hold" button
      await tester.tap(find.widgetWithText(ElevatedButton, 'Add Legal Hold'));
      await tester.pumpAndSettle();

      // Dialog should be open
      expect(find.text('Create Compliance Legal Hold'), findsOneWidget);

      // Enter details
      await tester.enterText(find.widgetWithText(TextField, 'Hold Name'), 'E2E Audit Hold');
      await tester.enterText(find.widgetWithText(TextField, 'Description'), 'E2E validation of holds.');
      
      // Select Target Type
      await tester.tap(find.text('FORM'));
      await tester.pumpAndSettle();
      // Dropdown will show choices, select "PROJECT"
      await tester.tap(find.text('PROJECT').last);
      await tester.pumpAndSettle();

      await tester.enterText(find.widgetWithText(TextField, 'Target IDs (comma separated)'), 'proj_e2e_1, proj_e2e_2');
      await tester.pumpAndSettle();

      // Tap "Create"
      await tester.tap(find.widgetWithText(ElevatedButton, 'Create'));
      await tester.pumpAndSettle();

      // Dialog should close and new hold card should be displayed in the list
      expect(find.text('Create Compliance Legal Hold'), findsNothing);
      expect(find.text('E2E Audit Hold'), findsOneWidget);
      expect(find.text('E2E validation of holds.'), findsOneWidget);
      expect(find.textContaining('PROJECT: proj_e2e_1, proj_e2e_2'), findsOneWidget);
    });
  });
}
