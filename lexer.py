
import ply.lex as lex

# C keywords supported by our project
reserved = {
    "int": "INT",
    "float": "FLOAT",
    "char": "CHAR",
    "void": "VOID",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "for": "FOR",
    "return": "RETURN",
    "printf": "PRINTF",
}

tokens = [
    "ID",
    "NUMBER",
    "STRING",
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "ASSIGN",
    "EQ",
    "NE",
    "LT",
    "GT",
    "LE",
    "GE",
    "LPAREN",
    "RPAREN",
    "LBRACE",
    "RBRACE",
    "SEMICOLON",
    "COMMA",
] + list(reserved.values())

# Multi-character operators must be recognized correctly.
t_EQ = r"=="
t_NE = r"!="
t_LE = r"<="
t_GE = r">="

# Single-character tokens
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_ASSIGN = r"="
t_LT = r"<"
t_GT = r">"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LBRACE = r"\{"
t_RBRACE = r"\}"
t_SEMICOLON = r";"
t_COMMA = r","

t_ignore = " \t\r"

def t_STRING(t):
    r'"([^\\\n]|(\\.))*?"'
    return t

def t_NUMBER(t):
    r"\d+(\.\d+)?"
    t.value = float(t.value) if "." in t.value else int(t.value)
    return t

def t_ID(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"
    t.type = reserved.get(t.value, "ID")
    return t

def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)

def t_comment(t):
    r"//[^\n]*"
    pass

def t_error(t):
    print(
        f"Illegal character {t.value[0]!r} "
        f"at line {t.lineno}"
    )
    t.lexer.skip(1)

lexer = lex.lex()

def tokenize(source_code):
    """Convert source code into a list of tokens."""
    lexer.lineno = 1
    lexer.input(source_code)

    result = []

    while True:
        token = lexer.token()
        if token is None:
            break

        result.append({
            "type": token.type,
            "value": token.value,
            "line": token.lineno,
            "position": token.lexpos,
        })

    return result


if __name__ == "__main__":
    sample = "int x = 10;"
    for token in tokenize(sample):
        print(token)
