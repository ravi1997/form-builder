import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/auth/presentation/widgets/dynamic_group_rule_builder.dart';

void main() {
  group('DynamicGroupRuleBuilder Widget Tests (Tiers 1-3)', () {
    void setupScreen(WidgetTester tester) {
      tester.view.physicalSize = const Size(1200, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
    }

    testWidgets('T1: Render with default initial rule and verify UI fields', (WidgetTester tester) async {
      setupScreen(tester);
      Map<String, dynamic>? updatedRule;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DynamicGroupRuleBuilder(
              onChanged: (rule) {
                updatedRule = rule;
              },
            ),
          ),
        ),
      );

      // Verify that "Match" dropdown displays 'AND' by default
      expect(find.text('AND'), findsOneWidget);
      expect(find.text('Match'), findsOneWidget);

      // Verify default condition values: role, equals, org_member
      expect(find.widgetWithText(DropdownButtonFormField<String>, 'role'), findsOneWidget);
      expect(find.widgetWithText(DropdownButtonFormField<String>, 'equals'), findsOneWidget);
      
      final textFormField = tester.widget<TextFormField>(find.byType(TextFormField));
      expect(textFormField.controller?.text, equals('org_viewer'));
    });

    testWidgets('T1: Add a condition, change operator to OR, change values and verify JSON', (WidgetTester tester) async {
      setupScreen(tester);
      Map<String, dynamic>? updatedRule;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DynamicGroupRuleBuilder(
              initialRule: const {
                'logical_operator': 'AND',
                'conditions': [
                  {'field': 'email', 'operator': 'contains', 'value': '@company.com'}
                ],
              },
              onChanged: (rule) {
                updatedRule = rule;
              },
            ),
          ),
        ),
      );

      // Change logical operator from AND to OR
      await tester.tap(find.text('AND'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('OR').last);
      await tester.pumpAndSettle();

      // Add a condition
      await tester.tap(find.widgetWithText(ElevatedButton, 'Add Condition'));
      await tester.pumpAndSettle();

      final textFields = find.byType(TextFormField);
      expect(textFields, findsNWidgets(2));

      await tester.enterText(textFields.at(1), 'admin');
      await tester.pumpAndSettle();

      expect(updatedRule, isNotNull);
      expect(updatedRule!['logical_operator'], equals('OR'));
      expect(updatedRule!['conditions'].length, equals(2));
      expect(updatedRule!['conditions'][0]['field'], equals('email'));
      expect(updatedRule!['conditions'][0]['operator'], equals('contains'));
      expect(updatedRule!['conditions'][0]['value'], equals('@company.com'));
      
      expect(updatedRule!['conditions'][1]['field'], equals('role'));
      expect(updatedRule!['conditions'][1]['operator'], equals('equals'));
      expect(updatedRule!['conditions'][1]['value'], equals('admin'));
    });

    testWidgets('T2: Remove a condition and verify UI & callback updates', (WidgetTester tester) async {
      setupScreen(tester);
      Map<String, dynamic>? updatedRule;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DynamicGroupRuleBuilder(
              initialRule: const {
                'logical_operator': 'AND',
                'conditions': [
                  {'field': 'role', 'operator': 'equals', 'value': 'engineer'},
                  {'field': 'status', 'operator': 'equals', 'value': 'active'},
                ],
              },
              onChanged: (rule) {
                updatedRule = rule;
              },
            ),
          ),
        ),
      );

      final deleteButtons = find.byIcon(Icons.delete);
      expect(deleteButtons, findsNWidgets(2));

      // Remove the first condition
      await tester.tap(deleteButtons.first);
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      final textFormField = tester.widget<TextFormField>(find.byType(TextFormField));
      expect(textFormField.controller?.text, equals('active'));

      expect(updatedRule, isNotNull);
      expect(updatedRule!['conditions'].length, equals(1));
      expect(updatedRule!['conditions'][0]['field'], equals('status'));
      expect(updatedRule!['conditions'][0]['value'], equals('active'));
    });

    testWidgets('T2: Empty rule displays fallback text', (WidgetTester tester) async {
      setupScreen(tester);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DynamicGroupRuleBuilder(
              initialRule: const {
                'logical_operator': 'AND',
                'conditions': [],
              },
              onChanged: (rule) {},
            ),
          ),
        ),
      );

      expect(find.text('No conditions configured. All members in organization will be included.'), findsOneWidget);
    });

    testWidgets('T2: Comma-separated strings inside "in" operator', (WidgetTester tester) async {
      setupScreen(tester);
      Map<String, dynamic>? updatedRule;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DynamicGroupRuleBuilder(
              initialRule: const {
                'logical_operator': 'AND',
                'conditions': [
                  {'field': 'role', 'operator': 'in', 'value': 'admin,member,moderator'}
                ],
              },
              onChanged: (rule) {
                updatedRule = rule;
              },
            ),
          ),
        ),
      );

      final textFormField = tester.widget<TextFormField>(find.byType(TextFormField));
      expect(textFormField.controller?.text, equals('admin,member,moderator'));

      // Trigger change
      final textField = find.byType(TextFormField).first;
      await tester.enterText(textField, 'admin,member,moderator,guest');
      await tester.pumpAndSettle();

      expect(updatedRule, isNotNull);
      expect(updatedRule!['conditions'][0]['value'], equals('admin,member,moderator,guest'));
    });

    testWidgets('T3: Focus retention during typing and didUpdateWidget reload behavior', (WidgetTester tester) async {
      setupScreen(tester);
      Map<String, dynamic>? updatedRule;
      
      // We wrap it in a stateful widget that allows us to change the initialRule from the outside
      late void Function(Map<String, dynamic> newRule) updateRuleFn;
      
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: StatefulBuilder(
              builder: (context, setState) {
                updateRuleFn = (newRule) {
                  setState(() {
                    updatedRule = newRule;
                  });
                };
                return DynamicGroupRuleBuilder(
                  initialRule: updatedRule ?? const {
                    'logical_operator': 'AND',
                    'conditions': [
                      {'field': 'role', 'operator': 'equals', 'value': 'org_viewer'}
                    ],
                  },
                  onChanged: (rule) {
                    // callback
                  },
                );
              },
            ),
          ),
        ),
      );

      // 1. Verify focus retention during typing
      final textFields = find.byType(TextFormField);
      expect(textFields, findsOneWidget);
      
      // Tap/focus the text field
      await tester.tap(textFields);
      await tester.pump();
      
      // Verify it has focus
      final FocusNode focusNode = tester.widget<EditableText>(find.byType(EditableText).first).focusNode;
      expect(focusNode.hasFocus, isTrue);

      // Enter text step-by-step
      await tester.enterText(textFields, 'a');
      await tester.pump();
      expect(focusNode.hasFocus, isTrue);
      
      await tester.enterText(textFields, 'ab');
      await tester.pump();
      expect(focusNode.hasFocus, isTrue);

      await tester.enterText(textFields, 'abc');
      await tester.pump();
      expect(focusNode.hasFocus, isTrue);

      // 2. Verify didUpdateWidget updates the conditions list when initialRule changes from the outside
      updateRuleFn(const {
        'logical_operator': 'OR',
        'conditions': [
          {'field': 'email', 'operator': 'contains', 'value': 'test@test.com'},
          {'field': 'status', 'operator': 'equals', 'value': 'active'}
        ]
      });
      await tester.pumpAndSettle();

      // Verify logical operator is now OR
      expect(find.text('OR'), findsOneWidget);
      
      // Verify there are 2 TextFormFields
      expect(find.byType(TextFormField), findsNWidgets(2));
      
      final textFieldsAfterUpdate = tester.widgetList<TextFormField>(find.byType(TextFormField)).toList();
      expect(textFieldsAfterUpdate[0].controller?.text, equals('test@test.com'));
      expect(textFieldsAfterUpdate[1].controller?.text, equals('active'));
    });
  });
}

