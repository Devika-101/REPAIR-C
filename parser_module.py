import ply.yacc as yacc
from lexer import tokens, lexer, lexical_errors, lexer_lock

# Store syntax errors detected by the parser
syntax_errors = []


# Operator precedence: lowest to highest
precedence = (
    ("nonassoc", "IFX"),      # "if" without else (resolves dangling else)
    ("nonassoc", "ELSE"),
    ("left", "OR"),
    ("left", "AND"),
    ("left", "EQ", "NE"),
    ("left", "LT", "GT", "LE", "GE"),
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE", "MOD"),
    ("right", "UMINUS", "NOT"),
)

# ---------------- GRAMMAR RULES ----------------


def p_program(p):
    """program : top_list"""
    p[0] = ("program", p[1])


def p_top_list_multiple(p):
    """top_list : top_list top_item"""
    p[0] = p[1] + [p[2]]


def p_top_list_empty(p):
    """top_list : empty"""
    p[0] = []


def p_top_item(p):
    """top_item : function_definition
                | statement"""
    p[0] = p[1]


def p_statement_list_multiple(p):
    """statement_list : statement_list statement"""
    p[0] = p[1] + [p[2]]


def p_statement_list_empty(p):
    """statement_list : empty"""
    p[0] = []


def p_statement(p):
    """statement : declaration
                 | assignment
                 | expression_statement
                 | if_statement
                 | while_statement
                 | for_statement
                 | return_statement
                 | break_statement
                 | continue_statement
                 | block"""
    p[0] = p[1]


def p_statement_empty(p):
    """statement : SEMICOLON"""
    p[0] = ("empty",)


def p_declaration(p):
    """declaration : type declarator_list SEMICOLON"""
    p[0] = ("declaration", p[1], p[2])


def p_declarator_list_multiple(p):
    """declarator_list : declarator_list COMMA declarator"""
    p[0] = p[1] + [p[3]]


def p_declarator_list_single(p):
    """declarator_list : declarator"""
    p[0] = [p[1]]


def p_declarator_plain(p):
    """declarator : ID"""
    p[0] = (p[1], None)


def p_declarator_init(p):
    """declarator : ID ASSIGN expression"""
    p[0] = (p[1], p[3])


def p_declarator_array(p):
    """declarator : ID LBRACKET expression RBRACKET
                  | ID LBRACKET RBRACKET"""
    p[0] = (p[1], None)


def p_declarator_array_init(p):
    """declarator : ID LBRACKET expression RBRACKET ASSIGN LBRACE argument_list RBRACE
                  | ID LBRACKET RBRACKET ASSIGN LBRACE argument_list RBRACE"""
    p[0] = (p[1], p[len(p) - 2])


def p_type(p):
    """type : INT
            | FLOAT
            | CHAR"""
    p[0] = p[1]


# Function definitions such as: int main() { ... }  (top level only)
def p_function_definition(p):
    """function_definition : type ID LPAREN parameters RPAREN block
                           | VOID ID LPAREN parameters RPAREN block"""
    p[0] = ("function", p[1], p[2], p[4], p[6])


def p_parameters_list(p):
    """parameters : parameter_list"""
    p[0] = p[1]


def p_parameters_void(p):
    """parameters : VOID"""
    p[0] = []


def p_parameters_empty(p):
    """parameters : empty"""
    p[0] = []


def p_parameter_list_multiple(p):
    """parameter_list : parameter_list COMMA parameter"""
    p[0] = p[1] + [p[3]]


def p_parameter_list_single(p):
    """parameter_list : parameter"""
    p[0] = [p[1]]


def p_parameter(p):
    """parameter : type ID"""
    p[0] = (p[1], p[2])


def p_assignment(p):
    """assignment : simple_assign SEMICOLON"""
    p[0] = p[1]


def p_simple_assign(p):
    """simple_assign : lvalue assign_op expression"""
    p[0] = ("assignment", p[1], p[2], p[3])


def p_lvalue_identifier(p):
    """lvalue : ID"""
    p[0] = p[1]


def p_lvalue_index(p):
    """lvalue : ID LBRACKET expression RBRACKET"""
    p[0] = ("index", p[1], p[3])


def p_assign_op(p):
    """assign_op : ASSIGN
                 | PLUSEQ
                 | MINUSEQ
                 | TIMESEQ
                 | DIVEQ"""
    p[0] = p[1]


def p_expression_statement(p):
    """expression_statement : expression SEMICOLON"""
    p[0] = ("expr", p[1])


def p_if_statement(p):
    """if_statement : IF LPAREN expression RPAREN statement %prec IFX
                    | IF LPAREN expression RPAREN statement ELSE statement"""
    if len(p) == 6:
        p[0] = ("if", p[3], p[5], None)
    else:
        p[0] = ("if", p[3], p[5], p[7])


def p_while_statement(p):
    """while_statement : WHILE LPAREN expression RPAREN statement"""
    p[0] = ("while", p[3], p[5])


def p_for_statement(p):
    """for_statement : FOR LPAREN for_init SEMICOLON for_cond SEMICOLON for_update RPAREN statement"""
    p[0] = ("for", p[3], p[5], p[7], p[9])


def p_for_init_assign(p):
    """for_init : simple_assign"""
    p[0] = p[1]


def p_for_init_declaration(p):
    """for_init : type ID ASSIGN expression"""
    p[0] = ("declaration", p[1], [(p[2], p[4])])


def p_for_init_empty(p):
    """for_init : empty"""
    p[0] = None


def p_for_cond_expression(p):
    """for_cond : expression"""
    p[0] = p[1]


def p_for_cond_empty(p):
    """for_cond : empty"""
    p[0] = None


def p_for_update_assign(p):
    """for_update : simple_assign"""
    p[0] = p[1]


def p_for_update_expression(p):
    """for_update : expression"""
    p[0] = p[1]


def p_for_update_empty(p):
    """for_update : empty"""
    p[0] = None


def p_block(p):
    """block : LBRACE statement_list RBRACE"""
    p[0] = ("block", p[2])


def p_return_statement(p):
    """return_statement : RETURN expression SEMICOLON
                        | RETURN SEMICOLON"""
    if len(p) == 4:
        p[0] = ("return", p[2])
    else:
        p[0] = ("return", None)


def p_break_statement(p):
    """break_statement : BREAK SEMICOLON"""
    p[0] = ("break",)


def p_continue_statement(p):
    """continue_statement : CONTINUE SEMICOLON"""
    p[0] = ("continue",)


# Expressions and operator precedence
def p_expression_binary(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression MOD expression
                  | expression EQ expression
                  | expression NE expression
                  | expression LT expression
                  | expression GT expression
                  | expression LE expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression"""
    p[0] = ("binary", p[2], p[1], p[3])


def p_expression_unary_minus(p):
    """expression : MINUS expression %prec UMINUS"""
    p[0] = ("unary", "-", p[2])


def p_expression_not(p):
    """expression : NOT expression"""
    p[0] = ("unary", "!", p[2])


def p_expression_address(p):
    """expression : AMP expression %prec UMINUS"""
    p[0] = ("unary", "&", p[2])


def p_expression_group(p):
    """expression : LPAREN expression RPAREN"""
    p[0] = p[2]


def p_expression_number(p):
    """expression : NUMBER"""
    p[0] = ("number", p[1])


def p_expression_string(p):
    """expression : STRING"""
    p[0] = ("string", p[1])


def p_expression_char(p):
    """expression : CHAR_LITERAL"""
    p[0] = ("char", p[1])


def p_expression_identifier(p):
    """expression : ID"""
    p[0] = ("identifier", p[1])


def p_expression_call(p):
    """expression : ID LPAREN arguments RPAREN"""
    p[0] = ("call", p[1], p[3])


def p_expression_index(p):
    """expression : ID LBRACKET expression RBRACKET"""
    p[0] = ("index", p[1], p[3])


def p_expression_postfix(p):
    """expression : ID INC
                  | ID DEC"""
    p[0] = ("postfix", p[2], p[1])


def p_arguments_list(p):
    """arguments : argument_list"""
    p[0] = p[1]


def p_arguments_empty(p):
    """arguments : empty"""
    p[0] = []


def p_argument_list_multiple(p):
    """argument_list : argument_list COMMA expression"""
    p[0] = p[1] + [p[3]]


def p_argument_list_single(p):
    """argument_list : expression"""
    p[0] = [p[1]]


def p_empty(p):
    """empty :"""
    p[0] = None


# ---------------- ERROR HANDLING ----------------

def p_error(token):
    if token:
        syntax_errors.append({
            "message": f"Unexpected token {token.value!r}",
            "line": token.lineno,
            "position": token.lexpos,
            "token_type": token.type,
        })
    else:
        syntax_errors.append({
            "message": "Unexpected end of input",
            "line": None,
            "position": None,
            "token_type": None,
        })


# ---------------- PARSER SETUP ----------------

# debug=False / write_tables=False: no parser.out or parsetab.py files, so a
# stale table can never be reused after the grammar changes.
# NullLogger hides PLY's harmless "token defined but not used" warnings
# (FOR, PRINTF, ...).
parser = yacc.yacc(
    debug=False,
    write_tables=False,
    errorlog=yacc.NullLogger(),
)


def parse_code(source_code):
    """Parse source code.

    Returns (tree, errors). `errors` is always a fresh list (a copy), so
    later calls to parse_code() can never change a result you already hold.
    The tree is None when any error was found.
    """
    with lexer_lock:
        syntax_errors.clear()
        lexical_errors.clear()
        lexer.lineno = 1

        tree = parser.parse(source_code, lexer=lexer)

        errors = list(lexical_errors) + list(syntax_errors)

    # Report errors in source order (end-of-input error, which has no
    # position, goes last).
    errors.sort(
        key=lambda e: (e["position"] is None, e["position"] or 0)
    )

    if errors:
        tree = None

    return tree, errors


if __name__ == "__main__":
    test_code = "int x = 10\nx = x + 5;"

    tree, errors = parse_code(test_code)

    print("Parse tree:", tree)
    print("Syntax errors:", errors)