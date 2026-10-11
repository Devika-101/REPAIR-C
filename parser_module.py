
import ply.yacc as yacc
from lexer import tokens, lexer

# Store syntax errors detected by the parser
syntax_errors = []


# Operator precedence: lowest to highest
precedence = (
    ("left", "EQ", "NE"),
    ("left", "LT", "GT", "LE", "GE"),
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE"),
)

# ---------------- GRAMMAR RULES ----------------

def p_program(p):
    """program : statement_list"""
    p[0] = ("program", p[1])



def p_statement_list_multiple(p):
    """statement_list : statement_list statement"""
    p[0] = p[1] + [p[2]]


def p_statement_list_empty(p):
    """statement_list : empty"""
    p[0] = []



def p_statement_declaration(p):
    """statement : declaration"""
    p[0] = p[1]


def p_statement_assignment(p):
    """statement : assignment"""
    p[0] = p[1]


def p_statement_if(p):
    """statement : if_statement"""
    p[0] = p[1]


def p_statement_while(p):
    """statement : while_statement"""
    p[0] = p[1]


def p_statement_return(p):
    """statement : return_statement"""
    p[0] = p[1]


def p_statement_block(p):
    """statement : block"""
    p[0] = p[1]


def p_declaration(p):
    """declaration : type ID ASSIGN expression SEMICOLON
                   | type ID SEMICOLON"""
    if len(p) == 6:
        p[0] = ("declaration", p[1], p[2], p[4])
    else:
        p[0] = ("declaration", p[1], p[2], None)


def p_type(p):
    """type : INT
            | FLOAT
            | CHAR"""
    p[0] = p[1]


def p_assignment(p):
    """assignment : ID ASSIGN expression SEMICOLON"""
    p[0] = ("assignment", p[1], p[3])


def p_if_statement(p):
    """if_statement : IF LPAREN expression RPAREN block"""
    p[0] = ("if", p[3], p[5])


def p_while_statement(p):
    """while_statement : WHILE LPAREN expression RPAREN block"""
    p[0] = ("while", p[3], p[5])


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


# Expressions and operator precedence
def p_expression_binary(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression EQ expression
                  | expression NE expression
                  | expression LT expression
                  | expression GT expression
                  | expression LE expression
                  | expression GE expression"""
    p[0] = ("binary", p[2], p[1], p[3])


def p_expression_group(p):
    """expression : LPAREN expression RPAREN"""
    p[0] = p[2]


def p_expression_number(p):
    """expression : NUMBER"""
    p[0] = ("number", p[1])


def p_expression_string(p):
    """expression : STRING"""
    p[0] = ("string", p[1])


def p_expression_identifier(p):
    """expression : ID"""
    p[0] = ("identifier", p[1])


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

parser = yacc.yacc()


def parse_code(source_code):
    """Parse source code and return its syntax tree and errors."""
    syntax_errors.clear()
    result = parser.parse(source_code, lexer=lexer)
    return result, syntax_errors.copy()


if __name__ == "__main__":
   sample = """
int x = 10;
x = x + 5;
if (x > 5) {
    return x;
}
"""

tree, errors = parse_code(sample)

print("Syntax tree:")
print(tree)

print("\nSyntax errors:")
print(errors if errors else "No syntax errors found.")