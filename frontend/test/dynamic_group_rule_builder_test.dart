import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/auth/presentation/widgets/dynamic_group_rule_builder.dart';

void main() {
  testWidgets('DynamicGroupRuleBuilder Widget Test - defaults, editing, focus retention, and didUpdateWidget', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    Map<String, dynamic>? latestRule;

    // A helper to pump the widget with changing rules/callbacks
    Widget buildWidget({Map<String, dynamic>? initialRule}) {
      return MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: DynamicGroupRuleBuilder(
              initialRule: initialRule,
              onChanged: (rule) {
                latestRule = rule;
              },
            ),
          ),
        ),
      );
    }

    // 1. Verify default values
    await tester.pumpWidget(buildWidget());
    await tester.pumpAndSettle();

    // The default rule should have 'org_viewer' as the value
    final valueFieldFinder = find.byType(TextFormField).first;
    expect(valueFieldFinder, findsOneWidget);
    
    final TextFormField textFormFieldWidget = tester.widget(valueFieldFinder);
    expect(textFormFieldWidget.controller?.text, equals('org_viewer'));
    expect(find.text('role'), findsOneWidget);
    expect(find.text('equals'), findsOneWidget);

    // 2. Verify input editing and onChanged notification
    // Enter a new value in the text field
    await tester.enterText(valueFieldFinder, 'custom_value');
    await tester.pumpAndSettle();

    expect(latestRule, isNotNull);
    expect(latestRule!['logical_operator'], equals('AND'));
    final conditions = latestRule!['conditions'] as List;
    expect(conditions.length, equals(1));
    expect(conditions[0]['field'], equals('role'));
    expect(conditions[0]['operator'], equals('equals'));
    expect(conditions[0]['value'], equals('custom_value'));

    // 3. Verify focus retention
    // Click the value field to focus on it
    await tester.tap(valueFieldFinder);
    await tester.pumpAndSettle();

    // Find internal Focus widget in descendants of valueFieldFinder to check focusNode.hasFocus
    final focusWidgetFinder = find.descendant(
      of: valueFieldFinder,
      matching: find.byType(Focus),
    ).first;
    expect(focusWidgetFinder, findsOneWidget);
    
    final Focus focusWidget = tester.widget(focusWidgetFinder);
    expect(focusWidget.focusNode?.hasFocus, isTrue);

    // Enter text and verify focus is not lost after rebuilding
    await tester.enterText(valueFieldFinder, 'another_value');
    await tester.pumpAndSettle();
    
    final Focus focusWidgetAfterEdit = tester.widget(focusWidgetFinder);
    expect(focusWidgetAfterEdit.focusNode?.hasFocus, isTrue);

    // 4. Verify didUpdateWidget updates state
    final newRule = {
      'logical_operator': 'OR',
      'conditions': [
        {'field': 'email', 'operator': 'contains', 'value': 'test@company.com'},
        {'field': 'status', 'operator': 'not_equals', 'value': 'active'},
      ]
    };

    // Pump the widget with the new rule
    await tester.pumpWidget(buildWidget(initialRule: newRule));
    await tester.pumpAndSettle();

    // Check that logical operator updated to OR
    expect(find.text('OR'), findsOneWidget);
    // Check that conditions updated
    expect(find.text('email'), findsOneWidget);
    expect(find.text('contains'), findsOneWidget);
    expect(find.text('test@company.com'), findsOneWidget);

    expect(find.text('status'), findsOneWidget);
    expect(find.text('not_equals'), findsOneWidget);
    expect(find.text('active'), findsOneWidget);
  });
}
