import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/formula/formula_parser.dart';

void main() {
  test('FormulaParser basics', () {
    final parser = FormulaParser('3 + 5 * 2 - (6 / 2)');
    final ast = parser.parse();
    final result = ast.evaluate({});
    expect(result, equals(10.0));
  });

  test('FormulaParser variables', () {
    final parser = FormulaParser('q1 * (q2 + 10) / q3');
    final ast = parser.parse();
    final result = ast.evaluate({
      'q1': 5.0,
      'q2': 10.0,
      'q3': 2.5,
    });
    expect(result, equals(40.0));
  });

  test('FormulaParser IF and conditions', () {
    // IF(q1 > 10, q2 * 2, q2)
    final parser = FormulaParser('IF(q1 > 10, q2 * 2, q2)');
    final ast = parser.parse();

    // Condition true: 15 > 10 => q2 * 2 => 5 * 2 = 10
    expect(ast.evaluate({'q1': 15.0, 'q2': 5.0}), equals(10.0));

    // Condition false: 8 > 10 => q2 => 5
    expect(ast.evaluate({'q1': 8.0, 'q2': 5.0}), equals(5.0));
  });

  test('FormulaParser nested conditions', () {
    // IF(q1 > 10, IF(q2 > 5, 100, 200), 300)
    final parser = FormulaParser('IF(q1 > 10, IF(q2 > 5, 100, 200), 300)');
    final ast = parser.parse();

    expect(ast.evaluate({'q1': 15.0, 'q2': 10.0}), equals(100.0));
    expect(ast.evaluate({'q1': 15.0, 'q2': 2.0}), equals(200.0));
    expect(ast.evaluate({'q1': 5.0, 'q2': 10.0}), equals(300.0));
  });

  test('FormulaParser logical operators and comparisons', () {
    // q1 > 5 && q2 < 10
    final parser = FormulaParser('(q1 > 5) && (q2 < 10)');
    final ast = parser.parse();
    expect(ast.evaluate({'q1': 6.0, 'q2': 8.0}), equals(1.0));
    expect(ast.evaluate({'q1': 4.0, 'q2': 8.0}), equals(0.0));

    // q1 >= 10 || !q2
    final parser2 = FormulaParser('(q1 >= 10) || !(q2 == 0)');
    final ast2 = parser2.parse();
    expect(ast2.evaluate({'q1': 10.0, 'q2': 0.0}), equals(1.0));
    expect(ast2.evaluate({'q1': 5.0, 'q2': 0.0}), equals(0.0));
  });

  test('FormulaParser division and modulo by zero', () {
    final parser1 = FormulaParser('10 / 0');
    final ast1 = parser1.parse();
    expect(ast1.evaluate({}), equals(0.0));

    final parser2 = FormulaParser('10 % 0');
    final ast2 = parser2.parse();
    expect(ast2.evaluate({}), equals(0.0));
  });

  test('FormulaParser coercion of strings to doubles', () {
    final parser = FormulaParser('IF(q1 > 10, q2 * 2, q2)');
    final ast = parser.parse();
    // q1 is string "15", q2 is string "5"
    expect(ast.evaluate({'q1': '15', 'q2': '5'}), equals(10.0));
    // q1 is string "8", q2 is double 5.0
    expect(ast.evaluate({'q1': '8', 'q2': 5.0}), equals(5.0));
  });
}
