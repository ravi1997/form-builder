import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('Auth screens rendering and navigation smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();

    // Verify that the login page is shown initially.
    expect(find.text('Welcome to Form Builder'), findsOneWidget);
    expect(find.text('Login'), findsWidgets);
  });
}
