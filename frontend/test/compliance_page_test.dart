import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/compliance/presentation/pages/compliance_page.dart';

void main() {
  testWidgets('CompliancePage rendering and toggle hold test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: CompliancePage(),
      ),
    );

    // Verify Title
    expect(find.text('Admin Compliance & Settings'), findsOneWidget);

    // Verify Storage quota bar is rendered
    expect(find.textContaining('Storage Quota Usage'), findsOneWidget);
    expect(find.textContaining('Used'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);

    // Verify Warning message
    expect(find.textContaining('Warning: Near storage limit'), findsOneWidget);

    // Verify Legal holds list
    expect(find.text('GDPR Audit Retention'), findsOneWidget);
    expect(find.text('HIPAA Compliance Retainer'), findsOneWidget);

    // Toggle HIPAA hold (which is inactive) to active
    final switchFinder = find.byType(Switch);
    expect(switchFinder, findsNWidgets(2));

    // Tap the second switch (HIPAA compliance, currently inactive)
    await tester.tap(switchFinder.last);
    await tester.pumpAndSettle();
  });
}
