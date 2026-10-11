import threading

import ply.lex as lex

# C keywords supported by our project.
# (printf/scanf etc. are ordinary identifiers: calls are handled in the grammar)
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
    "break": "BREAK",
    "continue": "CONTINUE",
}

tokens = [
    "ID",
    "NUMBER",
    "STRING",
    "CHAR_LITERAL",
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "MOD",
    "ASSIGN",
    "PLUSEQ",
    "MINUSEQ",
    "TIMESEQ",
    "DIVEQ",
    "EQ",
    "NE",
    "LT",
    "GT",
    "LE",
    "GE",
    "AND",
    "OR",
    "NOT",
    "AMP",
    "INC",
    "DEC",
    "LPAREN",
    "RPAREN",
    "LBRACE",
    "RBRACE",
    "LBRACKET",
    "RBRACKET",
    "SEMICOLON",
    "COMMA",
] + list(reserved.values())

# Illegal characters are collected here (instead of only being printed)
# so the parser module can report them as errors.
lexical_errors = []

# The PLY lexer is a module-level singleton: every user of it must hold
# this lock (Streamlit can run several sessions in different threads).
lexer_lock = threading.Lock()

# Multi-character operators (PLY tries longer regexes first).
t_EQ = r"=="
t_NE = r"!="
t_LE = r"<="
t_GE = r">="
t_AND = r"&&"
t_OR = r"\|\|"
t_INC = r"\+\+"
t_DEC = r"--"
t_PLUSEQ = r"\+="
t_MINUSEQ = r"-="
t_TIMESEQ = r"\*="
t_DIVEQ = r"/="

# Single-character tokens
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_MOD = r"%"
t_ASSIGN = r"="
t_LT = r"<"
t_GT = r">"
t_NOT = r"!"
t_AMP = r"&"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LBRACE = r"\{"
t_RBRACE = r"\}"
t_LBRACKET = r"\["
t_RBRACKET = r"\]"
t_SEMICOLON = r";"
t_COMMA = r","

t_ignore = " \t\r"


def t_STRING(t):
    r'"([^\\\n]|(\\.))*?"'
    return t


def t_CHAR_LITERAL(t):
    r"'(?:[^\\\n']|\\.)'"
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


def t_block_comment(t):
    r"/\*[\s\S]*?\*/"
    t.lexer.lineno += t.value.count("\n")


def t_preprocessor(t):
    r"\#[^\n]*"
    pass


def t_error(t):
    lexical_errors.append({
        "message": f"Illegal character {t.value[0]!r}",
        "line": t.lineno,
        "position": t.lexpos,
        "token_type": "ILLEGAL",
    })
    t.lexer.skip(1)


lexer = lex.lex()


def tokenize(source_code):
    """Convert source code into a list of tokens.

    Each token has: type, value, text (raw source text), line,
    position (start offset) and end (end offset).
    """
    with lexer_lock:
        lexical_errors.clear()
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
                "text": source_code[token.lexpos:lexer.lexpos],
                "line": token.lineno,
                "position": token.lexpos,
                "end": lexer.lexpos,
            })

        return result


if __name__ == "__main__":
    sample = "int x = 10;"
    for token in tokenize(sample):
        print(token)