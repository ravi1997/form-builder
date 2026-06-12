abstract class ExpressionNode {
  double evaluate(Map<String, dynamic> variables);
}

class NumberNode extends ExpressionNode {
  final double value;
  NumberNode(this.value);

  @override
  double evaluate(Map<String, dynamic> variables) => value;
}

class VariableNode extends ExpressionNode {
  final String name;
  VariableNode(this.name);

  @override
  double evaluate(Map<String, dynamic> variables) {
    final val = variables[name];
    if (val == null) return 0.0;
    if (val is num) return val.toDouble();
    if (val is String) {
      return double.tryParse(val) ?? 0.0;
    }
    return 0.0;
  }
}

class BinaryOpNode extends ExpressionNode {
  final String op;
  final ExpressionNode left;
  final ExpressionNode right;
  BinaryOpNode(this.op, this.left, this.right);

  @override
  double evaluate(Map<String, dynamic> variables) {
    final lVal = left.evaluate(variables);
    final rVal = right.evaluate(variables);
    switch (op) {
      case '+': return lVal + rVal;
      case '-': return lVal - rVal;
      case '*': return lVal * rVal;
      case '/': return rVal == 0 ? 0.0 : lVal / rVal;
      case '%': return rVal == 0 ? 0.0 : lVal % rVal;
      case '>': return lVal > rVal ? 1.0 : 0.0;
      case '<': return lVal < rVal ? 1.0 : 0.0;
      case '>=': return lVal >= rVal ? 1.0 : 0.0;
      case '<=': return lVal <= rVal ? 1.0 : 0.0;
      case '==': return lVal == rVal ? 1.0 : 0.0;
      case '!=': return lVal != rVal ? 1.0 : 0.0;
      case '&&': return (lVal != 0.0 && rVal != 0.0) ? 1.0 : 0.0;
      case '||': return (lVal != 0.0 || rVal != 0.0) ? 1.0 : 0.0;
      default: throw Exception('Unknown operator: $op');
    }
  }
}

class IfNode extends ExpressionNode {
  final ExpressionNode condition;
  final ExpressionNode thenBranch;
  final ExpressionNode elseBranch;
  IfNode(this.condition, this.thenBranch, this.elseBranch);

  @override
  double evaluate(Map<String, dynamic> variables) {
    final condVal = condition.evaluate(variables);
    return condVal != 0.0 ? thenBranch.evaluate(variables) : elseBranch.evaluate(variables);
  }
}

class UnaryNotNode extends ExpressionNode {
  final ExpressionNode expr;
  UnaryNotNode(this.expr);

  @override
  double evaluate(Map<String, dynamic> variables) {
    final val = expr.evaluate(variables);
    return val == 0.0 ? 1.0 : 0.0;
  }
}

class FormulaParser {
  final String input;
  int _pos = 0;

  FormulaParser(this.input);

  String get _currentChar => _pos < input.length ? input[_pos] : '';

  void _next() {
    _pos++;
  }

  void _skipWhitespace() {
    while (_pos < input.length && (input[_pos] == ' ' || input[_pos] == '\t')) {
      _next();
    }
  }

  ExpressionNode parse() {
    final node = _parseLogicalOr();
    _skipWhitespace();
    if (_pos < input.length) {
      throw Exception('Unexpected character at $_pos: ${input[_pos]}');
    }
    return node;
  }

  ExpressionNode _parseLogicalOr() {
    var left = _parseLogicalAnd();
    while (true) {
      _skipWhitespace();
      if (_pos + 1 < input.length && input[_pos] == '|' && input[_pos + 1] == '|') {
        _pos += 2;
        final right = _parseLogicalAnd();
        left = BinaryOpNode('||', left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parseLogicalAnd() {
    var left = _parseEquality();
    while (true) {
      _skipWhitespace();
      if (_pos + 1 < input.length && input[_pos] == '&' && input[_pos + 1] == '&') {
        _pos += 2;
        final right = _parseEquality();
        left = BinaryOpNode('&&', left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parseEquality() {
    var left = _parseComparison();
    while (true) {
      _skipWhitespace();
      if (_pos + 1 < input.length && input[_pos] == '=' && input[_pos + 1] == '=') {
        _pos += 2;
        final right = _parseComparison();
        left = BinaryOpNode('==', left, right);
      } else if (_pos + 1 < input.length && input[_pos] == '!' && input[_pos + 1] == '=') {
        _pos += 2;
        final right = _parseComparison();
        left = BinaryOpNode('!=', left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parseComparison() {
    var left = _parseAdditive();
    while (true) {
      _skipWhitespace();
      if (_pos + 1 < input.length && input[_pos] == '>' && input[_pos + 1] == '=') {
        _pos += 2;
        final right = _parseAdditive();
        left = BinaryOpNode('>=', left, right);
      } else if (_pos + 1 < input.length && input[_pos] == '<' && input[_pos + 1] == '=') {
        _pos += 2;
        final right = _parseAdditive();
        left = BinaryOpNode('<=', left, right);
      } else if (_pos < input.length && input[_pos] == '>') {
        _next();
        final right = _parseAdditive();
        left = BinaryOpNode('>', left, right);
      } else if (_pos < input.length && input[_pos] == '<') {
        _next();
        final right = _parseAdditive();
        left = BinaryOpNode('<', left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parseAdditive() {
    var left = _parseMultiplicative();
    while (true) {
      _skipWhitespace();
      final op = _currentChar;
      if (op == '+' || op == '-') {
        _next();
        final right = _parseMultiplicative();
        left = BinaryOpNode(op, left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parseMultiplicative() {
    var left = _parsePrimary();
    while (true) {
      _skipWhitespace();
      final op = _currentChar;
      if (op == '*' || op == '/' || op == '%') {
        _next();
        final right = _parsePrimary();
        left = BinaryOpNode(op, left, right);
      } else {
        break;
      }
    }
    return left;
  }

  ExpressionNode _parsePrimary() {
    _skipWhitespace();
    final c = _currentChar;
    if (c == '(') {
      _next();
      final node = _parseLogicalOr();
      _skipWhitespace();
      if (_currentChar != ')') {
        throw Exception('Expected closing parenthesis');
      }
      _next();
      return node;
    }

    if (c == '-' || c == '+') {
      _next();
      final node = _parsePrimary();
      return BinaryOpNode(c, NumberNode(0.0), node);
    }

    if (c == '!') {
      _next();
      final node = _parsePrimary();
      return UnaryNotNode(node);
    }

    if (RegExp(r'[0-9]').hasMatch(c)) {
      final start = _pos;
      while (_pos < input.length && RegExp(r'[0-9.]').hasMatch(input[_pos])) {
        _next();
      }
      final numStr = input.substring(start, _pos);
      return NumberNode(double.parse(numStr));
    }

    if (RegExp(r'[a-zA-Z_]').hasMatch(c)) {
      final start = _pos;
      while (_pos < input.length && RegExp(r'[a-zA-Z0-9_]').hasMatch(input[_pos])) {
        _next();
      }
      final varName = input.substring(start, _pos);
      _skipWhitespace();
      if (_currentChar == '(') {
        _next(); // consume '('
        if (varName.toUpperCase() == 'IF') {
          final cond = _parseLogicalOr();
          _skipWhitespace();
          if (_currentChar != ',') {
            throw Exception('Expected comma after condition in IF');
          }
          _next(); // consume ','
          final thenBranch = _parseLogicalOr();
          _skipWhitespace();
          if (_currentChar != ',') {
            throw Exception('Expected comma after then branch in IF');
          }
          _next(); // consume ','
          final elseBranch = _parseLogicalOr();
          _skipWhitespace();
          if (_currentChar != ')') {
            throw Exception('Expected closing parenthesis in IF');
          }
          _next(); // consume ')'
          return IfNode(cond, thenBranch, elseBranch);
        } else {
          throw Exception('Unknown function: $varName');
        }
      }
      return VariableNode(varName);
    }

    throw Exception('Unexpected character: $c');
  }
}
