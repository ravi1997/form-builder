import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/presentation/widgets/properties_panel.dart';

void main() {
  testWidgets('Form Notifications Tab and Fields State Sync Test', (WidgetTester tester) async {
    // Set surface size to avoid overflow and offscreen tapping errors
    await tester.binding.setSurfaceSize(const Size(1280, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => TestFormBuilderNotifier()),
      ],
    );

    // Render the PropertiesPanel (since selectedElementId is null, it shows Global Form Properties)
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 400,
              child: PropertiesPanel(),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify TabBar has 3 tabs and find the 'Notifications' tab
    expect(find.text('General'), findsOneWidget);
    expect(find.text('Style'), findsOneWidget);
    expect(find.text('Notifications'), findsOneWidget);

    // Switch to Notifications tab
    await tester.tap(find.text('Notifications'));
    await tester.pumpAndSettle();

    // 1. Email Alerts Tests
    expect(find.byKey(const ValueKey('notifications-email-switch')), findsOneWidget);
    
    // Webhook secret and trigger event dropdown should NOT be visible until switches are enabled
    expect(find.byKey(const ValueKey('notifications-email-trigger-dropdown')), findsNothing);
    expect(find.byKey(const ValueKey('notifications-webhook-url-input')), findsNothing);

    // Enable Email Alerts
    final emailSwitch = find.byKey(const ValueKey('notifications-email-switch'));
    await tester.ensureVisible(emailSwitch);
    await tester.tap(emailSwitch);
    await tester.pumpAndSettle();

    expect(container.read(formBuilderProvider).notifications.emailEnabled, isTrue);
    final emailTrigger = find.byKey(const ValueKey('notifications-email-trigger-dropdown'));
    expect(emailTrigger, findsOneWidget);
    final emailRecipients = find.byKey(const ValueKey('notifications-email-recipients-input'));
    expect(emailRecipients, findsOneWidget);

    // Enter recipients
    await tester.ensureVisible(emailRecipients);
    await tester.enterText(emailRecipients, 'test@example.com, alert@company.org');
    await tester.pumpAndSettle();
    expect(
      container.read(formBuilderProvider).notifications.emailRecipients,
      equals(['test@example.com', 'alert@company.org']),
    );

    // Toggle Include Attachments
    final attachmentsSwitch = find.byKey(const ValueKey('notifications-email-attachments-switch'));
    await tester.ensureVisible(attachmentsSwitch);
    await tester.tap(attachmentsSwitch);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).notifications.emailIncludeAttachments, isTrue);

    // 2. Webhook Delivery Tests
    final webhookSwitch = find.byKey(const ValueKey('notifications-webhook-switch'));
    await tester.ensureVisible(webhookSwitch);
    await tester.tap(webhookSwitch);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).notifications.webhookEnabled, isTrue);

    final webhookUrl = find.byKey(const ValueKey('notifications-webhook-url-input'));
    await tester.ensureVisible(webhookUrl);
    await tester.enterText(webhookUrl, 'https://api.test.com/hook');
    
    final webhookSecret = find.byKey(const ValueKey('notifications-webhook-secret-input'));
    await tester.ensureVisible(webhookSecret);
    await tester.enterText(webhookSecret, 'my-super-secret');
    await tester.pumpAndSettle();

    expect(container.read(formBuilderProvider).notifications.webhookUrl, equals('https://api.test.com/hook'));
    expect(container.read(formBuilderProvider).notifications.webhookSecret, equals('my-super-secret'));

    // 3. Internal Alerts Tests
    final internalSwitch = find.byKey(const ValueKey('notifications-internal-switch'));
    await tester.ensureVisible(internalSwitch);
    await tester.tap(internalSwitch);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).notifications.internalEnabled, isTrue);

    final internalUsers = find.byKey(const ValueKey('notifications-internal-users-input'));
    await tester.ensureVisible(internalUsers);
    await tester.enterText(internalUsers, '65c4f1011c9d2f0012bc5566, 65c4f1021c9d2f0012bc5567');
    
    final internalTeams = find.byKey(const ValueKey('notifications-internal-teams-input'));
    await tester.ensureVisible(internalTeams);
    await tester.enterText(internalTeams, 'team_dev, team_qa');
    await tester.pumpAndSettle();

    expect(
      container.read(formBuilderProvider).notifications.internalUserIds,
      equals(['65c4f1011c9d2f0012bc5566', '65c4f1021c9d2f0012bc5567']),
    );
    expect(
      container.read(formBuilderProvider).notifications.internalTeamIds,
      equals(['team_dev', 'team_qa']),
    );

    // 4. Failure Handling Tests
    expect(container.read(formBuilderProvider).notifications.alertOwnerOnFailure, isTrue);
    final failureSwitch = find.byKey(const ValueKey('notifications-failure-alert-switch'));
    await tester.ensureVisible(failureSwitch);
    await tester.tap(failureSwitch);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).notifications.alertOwnerOnFailure, isFalse);
  });
}

class TestFormBuilderNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'test_form',
      name: 'Test Form Name',
      style: FormStyle(),
      canvasMode: FormCanvasMode.edit,
      notifications: FormNotifications(),
      sections: [],
    );
  }
}
