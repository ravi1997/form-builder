import ast
import logging
import math
import operator
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId

logger = logging.getLogger(__name__)


class FormulaError(Exception):
    """Exception raised when formula evaluation fails."""
    pass


class FormulaVisitor(ast.NodeVisitor):
    """AST visitor for formula evaluation."""
    
    # Supported operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
        ast.Invert: operator.invert,
        ast.Not: operator.not_,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
    }
    
    # Supported functions
    FUNCTIONS = {
        # Math functions
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'len': len,
        'pow': pow,
        'sqrt': math.sqrt,
        'ceil': math.ceil,
        'floor': math.floor,
        'log': math.log,
        'log10': math.log10,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'degrees': math.degrees,
        'radians': math.radians,
        'pi': math.pi,
        'e': math.e,
        
        # String functions
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'upper': str.upper,
        'lower': str.lower,
        'strip': str.strip,
        'split': str.split,
        'join': str.join,
        'replace': str.replace,
        'startswith': str.startswith,
        'endswith': str.endswith,
        'contains': lambda s, substr: substr in s,
        
        # Date functions
        'now': datetime.utcnow,
        'date': datetime.date,
        'datetime': datetime.datetime,
        'timedelta': timedelta,
        'strftime': lambda dt, fmt: dt.strftime(fmt) if hasattr(dt, 'strftime') else str(dt),
        
        # List functions
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'sorted': sorted,
        'reversed': reversed,
        'enumerate': enumerate,
        'zip': zip,
        
        # Type checking
        'isinstance': isinstance,
        'type': type,
        'hasattr': hasattr,
        'getattr': getattr,
    }
    
    def __init__(self, context: Dict = None):
        self.context = context or {}
        self._current_question_id = None
    
    def set_current_question_id(self, question_id: str):
        """Set the current question ID for context."""
        self._current_question_id = question_id
    
    def visit_Name(self, node):
        """Visit a name node (variable or function)."""
        if node.id in self.FUNCTIONS:
            return self.FUNCTIONS[node.id]
        elif node.id in self.context:
            return self.context[node.id]
        else:
            # Try to get from form answers
            if hasattr(self, '_get_form_answer'):
                answer = self._get_form_answer(node.id)
                if answer is not None:
                    return answer
            raise FormulaError(f"Unknown variable: {node.id}")
    
    def visit_Constant(self, node):
        """Visit a constant node."""
        return node.value
    
    def visit_Num(self, node):
        """Visit a number node (for older Python versions)."""
        return node.n
    
    def visit_Str(self, node):
        """Visit a string node (for older Python versions)."""
        return node.s
    
    def visit_NameConstant(self, node):
        """Visit a name constant node (for older Python versions)."""
        return node.value
    
    def visit_List(self, node):
        """Visit a list node."""
        return [self.visit(elt) for elt in node.elts]
    
    def visit_Tuple(self, node):
        """Visit a tuple node."""
        return tuple(self.visit(elt) for elt in node.elts)
    
    def visit_Dict(self, node):
        """Visit a dict node."""
        keys = [self.visit(key) for key in node.keys]
        values = [self.visit(value) for value in node.values]
        return dict(zip(keys, values))
    
    def visit_BinOp(self, node):
        """Visit a binary operation node."""
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        
        if op_type in self.OPERATORS:
            try:
                return self.OPERATORS[op_type](left, right)
            except Exception as e:
                raise FormulaError(f"Error in binary operation: {str(e)}")
        else:
            raise FormulaError(f"Unsupported operator: {op_type}")
    
    def visit_UnaryOp(self, node):
        """Visit a unary operation node."""
        operand = self.visit(node.operand)
        op_type = type(node.op)
        
        if op_type in self.OPERATORS:
            try:
                return self.OPERATORS[op_type](operand)
            except Exception as e:
                raise FormulaError(f"Error in unary operation: {str(e)}")
        else:
            raise FormulaError(f"Unsupported unary operator: {op_type}")
    
    def visit_Compare(self, node):
        """Visit a comparison node."""
        left = self.visit(node.left)
        values = []
        ops = []
        
        for comparator, op in zip(node.comparators, node.ops):
            right = self.visit(comparator)
            op_type = type(op)
            
            if op_type in self.OPERATORS:
                try:
                    result = self.OPERATORS[op_type](left, right)
                except Exception as e:
                    raise FormulaError(f"Error in comparison: {str(e)}")
                
                values.append(result)
                ops.append(op_type)
                left = right  # For chained comparisons
            else:
                raise FormulaError(f"Unsupported comparison operator: {op_type}")
        
        # Handle chained comparisons (e.g., 1 < x < 5)
        if len(values) > 1:
            return all(values)
        elif values:
            return values[0]
        else:
            return True
    
    def visit_BoolOp(self, node):
        """Visit a boolean operation node."""
        values = [self.visit(value) for value in node.values]
        op_type = type(node.op)
        
        if op_type == ast.And:
            return all(values)
        elif op_type == ast.Or:
            return any(values)
        else:
            raise FormulaError(f"Unsupported boolean operator: {op_type}")
    
    def visit_Call(self, node):
        """Visit a function call node."""
        func = self.visit(node.func)
        args = [self.visit(arg) for arg in node.args]
        kwargs = {}
        
        for keyword in node.keywords:
            kwargs[keyword.arg] = self.visit(keyword.value)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise FormulaError(f"Error calling function: {str(e)}")
    
    def visit_IfExp(self, node):
        """Visit an if expression node."""
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)
        
        return body if test else orelse
    
    def visit_Attribute(self, node):
        """Visit an attribute access node."""
        obj = self.visit(node.value)
        attr = node.attr
        
        try:
            return getattr(obj, attr)
        except AttributeError:
            raise FormulaError(f"Object has no attribute '{attr}'")
    
    def visit_Subscript(self, node):
        """Visit a subscript node."""
        obj = self.visit(node.value)
        slice_val = self.visit(node.slice)
        
        try:
            return obj[slice_val]
        except (KeyError, IndexError, TypeError) as e:
            raise FormulaError(f"Error accessing subscript: {str(e)}")
    
    def visit_Index(self, node):
        """Visit an index node (for older Python versions)."""
        return self.visit(node.value)
    
    def visit_Slice(self, node):
        """Visit a slice node."""
        lower = self.visit(node.lower) if node.lower else None
        upper = self.visit(node.upper) if node.upper else None
        step = self.visit(node.step) if node.step else None
        
        return slice(lower, upper, step)
    
    def _get_form_answer(self, question_id: str) -> Any:
        """Get form answer by question ID."""
        # This would be implemented by the calling service
        # For now, return None
        return None


class FormulaEngine:
    """Engine for evaluating formulas in form calculations."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def parse_formula(self, formula_str: str) -> ast.AST:
        """Parse formula string into AST."""
        try:
            # Remove comments and clean up
            formula_str = re.sub(r'#.*$', '', formula_str, flags=re.MULTILINE)
            formula_str = formula_str.strip()
            
            if not formula_str:
                raise FormulaError("Formula is empty")
            
            # Parse AST
            tree = ast.parse(formula_str, mode='eval')
            return tree
            
        except SyntaxError as e:
            raise FormulaError(f"Syntax error in formula: {str(e)}")
        except Exception as e:
            raise FormulaError(f"Error parsing formula: {str(e)}")
    
    def validate_formula(self, formula_str: str, available_variables: List[str] = None) -> bool:
        """Validate formula syntax and variable references."""
        try:
            # Parse formula
            tree = self.parse_formula(formula_str)
            
            # Check for unsafe constructs
            validator = FormulaValidator(available_variables or [])
            validator.visit(tree)
            
            return True
            
        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"Error validating formula: {str(e)}")
    
    def evaluate_formula(self, formula_str: str, context: Dict = None, 
                        current_question_id: str = None) -> Any:
        """Evaluate a formula with given context."""
        try:
            # Check cache
            cache_key = f"{formula_str}:{hash(str(context))}:{current_question_id}"
            if cache_key in self.cache:
                cached_time, cached_result = self.cache[cache_key]
                # TODO: Check if cache is still valid
                return cached_result
            
            # Parse formula
            tree = self.parse_formula(formula_str)
            
            # Create visitor with context
            visitor = FormulaVisitor(context or {})
            if current_question_id:
                visitor.set_current_question_id(current_question_id)
            
            # Evaluate
            result = visitor.visit(tree)
            
            # Cache result
            self.cache[cache_key] = (time.time(), result)
            
            return result
            
        except FormulaError:
            raise
        except Exception as e:
            logger.error(f"Error evaluating formula '{formula_str}': {str(e)}")
            raise FormulaError(f"Error evaluating formula: {str(e)}")
    
    def evaluate_calculation(self, calculation_def: Dict, form_answers: Dict, 
                           current_question_id: str = None) -> Any:
        """Evaluate a form calculation definition."""
        try:
            formula_ast = calculation_def.get("formula_ast")
            if not formula_ast:
                raise FormulaError("Calculation missing formula AST")
            
            # Build context from form answers
            context = self._build_context(form_answers, current_question_id)
            
            # Convert AST back to string for evaluation
            # In a real implementation, you'd work directly with the AST
            formula_str = self._ast_to_string(formula_ast)
            
            # Evaluate formula
            result = self.evaluate_formula(formula_str, context, current_question_id)
            
            return result
            
        except FormulaError:
            raise
        except Exception as e:
            logger.error(f"Error evaluating calculation: {str(e)}")
            raise FormulaError(f"Error evaluating calculation: {str(e)}")
    
    def _build_context(self, form_answers: Dict, current_question_id: str = None) -> Dict:
        """Build evaluation context from form answers."""
        context = {}
        
        # Add common functions and constants
        context.update({
            'now': datetime.utcnow(),
            'pi': math.pi,
            'e': math.e,
        })
        
        # Add form answers
        for question_id, answer_data in form_answers.items():
            if question_id == current_question_id:
                continue  # Skip current question to avoid circular references
            
            answer_value = answer_data.get("value")
            if answer_value is not None:
                context[question_id] = answer_value
        
        return context
    
    def _ast_to_string(self, ast_node: ast.AST) -> str:
        """Convert AST node back to string (simplified)."""
        # This is a simplified implementation
        # In practice, you might want a more sophisticated AST-to-string converter
        if hasattr(ast_node, 'body'):
            return str(ast_node.body)
        return str(ast_node)
    
    def clear_cache(self):
        """Clear the formula cache."""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cache_ttl": self.cache_ttl
        }


class FormulaValidator(ast.NodeVisitor):
    """AST visitor for formula validation."""
    
    def __init__(self, allowed_variables: List[str] = None):
        self.allowed_variables = set(allowed_variables or [])
        self.errors = []
    
    def visit_Name(self, node):
        """Validate variable names."""
        if node.id not in FormulaVisitor.FUNCTIONS and node.id not in self.allowed_variables:
            self.errors.append(f"Unknown variable: {node.id}")
    
    def visit_Call(self, node):
        """Validate function calls."""
        func = self.visit(node.func)
        
        if isinstance(func, str) and func not in FormulaVisitor.FUNCTIONS:
            self.errors.append(f"Unknown function: {func}")
        
        # Visit arguments
        for arg in node.args:
            self.visit(arg)
        
        for keyword in node.keywords:
            self.visit(keyword.value)
    
    def visit_Attribute(self, node):
        """Validate attribute access."""
        # Only allow safe attributes
        obj = self.visit(node.value)
        attr = node.attr
        
        unsafe_attrs = ['__class__', '__dict__', '__module__', '__subclasses__', '__bases__']
        if attr in unsafe_attrs:
            self.errors.append(f"Unsafe attribute access: {attr}")
    
    def validate(self, formula_str: str) -> List[str]:
        """Validate formula and return list of errors."""
        try:
            tree = ast.parse(formula_str, mode='eval')
            self.visit(tree)
            return self.errors
        except SyntaxError as e:
            return [f"Syntax error: {str(e)}"]
        except Exception as e:
            return [f"Validation error: {str(e)}"]


# Create engine instance
formula_engine = FormulaEngine()