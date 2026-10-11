"""REPAIR-C repair engine.

How it works
------------
1. Parse the code and look at the first syntax error.
2. Generate many small candidate edits around it (insert / remove / replace
   a token, fix a misspelled keyword, close brackets, fix quotes ...).
3. Re-parse every candidate. Keep only candidates that make real progress
   (no errors, or the first error moved further into the file).
4. Repeat with a small beam search until the code parses cleanly.

Every returned repair has been validated by the parser.
"""

import time
from collections import namedtuple

from lexer import reserved, tokenize
from parser_module import parse_code

REPAIR_STRATEGIES = [
    "Insert a missing token  ( ;  )  (  {  }  ,  = )",
    "Remove an unexpected token",
    "Replace a wrong token  ( e.g.  =  ->  == )",
    "Fix misspelled keywords",
    "Close unclosed brackets at the end of the code",
    "Fix unterminated strings and illegal characters",
]

MAX_ROUNDS = 25
BEAM_WIDTH = 3
TIME_LIMIT_SECONDS = 8.0

INF = float("inf")

# An edit is a set of non-overlapping (start, end, new_text) parts that are
# applied together. cost = how "invasive" it is (cheaper edits win ties).
Edit = namedtuple("Edit", ["parts", "cost", "label"])
State = namedtuple("State", ["code", "errors", "cost", "fixes"])

# (symbol, cost)
INSERTIONS = [
    (";", 1),
    (")", 1),
    ("}", 1),
    ("(", 2),
    ("{", 2),
    ("]", 1),
    ("[", 2),
    (",", 2),
    ("=", 3),
]

# These are inserted right before the next token; the others right after
# the previous token.
PREFIX_SYMBOLS = {"(", "["}

INSERT_TEXT = {
    ";": ";",
    ")": ")",
    ",": ",",
    "]": "]",
    "}": "\n}",
    "{": " {",
    "=": " =",
}

REPLACEMENTS = [";", ",", ")", "(", "]", "[", "{", "}", "=", "=="]

# Two operator tokens separated by whitespace that really are one operator.
MERGEABLE_OPERATORS = {
    "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=",
}

# Only characters that can never be valid C are removed automatically.
# (Valid-but-unsupported symbols such as . : ? | ^ ~ are reported instead,
# because deleting them would silently change the meaning of the code.)
DELETABLE_CHARS = set("@$`\\")

NON_PUNCTUATION = {"ID", "NUMBER", "STRING", "CHAR_LITERAL"} | set(
    reserved.values()
)

# Characters that often sneak in when code is pasted from documents/web.
LOOKALIKES = {
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2013": "-",
    "\u2014": "-",
    "\u00d7": "*",
    "\u00f7": "/",
    "\uff1b": ";",
    "\uff0c": ",",
    "\uff08": "(",
    "\uff09": ")",
    "\u00a0": " ",
    "\u200b": "",
    "\ufeff": "",
}


# ---------------- small helpers ----------------

def _no_errors_result(source_code):
    return {
        "success": True,
        "original_code": source_code,
        "repaired_code": source_code,
        "message": "No syntax errors found.",
        "fixes": [],
        "partial_code": None,
        "remaining_errors": [],
    }


def _first_pos(errors):
    position = errors[0]["position"]
    return INF if position is None else position


def _line_of(code, pos):
    return code.count("\n", 0, pos) + 1


def _apply(code, edit):
    out = []
    cursor = 0
    for start, end, text in edit.parts:
        out.append(code[cursor:start])
        out.append(text)
        cursor = end
    out.append(code[cursor:])
    return "".join(out)


def _map_position(pos, parts):
    """Where does old offset `pos` end up after the edit?"""
    shift = 0
    for start, end, text in parts:
        if start == end:  # pure insertion
            if pos >= start:
                shift += len(text)
            else:
                break
        elif pos >= end:
            shift += len(text) - (end - start)
        elif pos >= start:
            return start + shift  # inside the replaced text
        else:
            break
    return pos + shift


def _progress(old_errors, new_errors, edit):
    """True if the edit fixed everything or pushed the first error later."""
    if not new_errors:
        return True

    old_pos = _first_pos(old_errors)
    if old_pos != INF:
        old_pos = _map_position(old_pos, edit.parts)

    return _first_pos(new_errors) > old_pos


def _edit_distance(a, b):
    """Damerau-Levenshtein distance (insert/delete/replace/transpose)."""
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]

    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j

    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if (
                i > 1
                and j > 1
                and a[i - 1] == b[j - 2]
                and a[i - 2] == b[j - 1]
            ):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)

    return d[la][lb]


def _expand_if_blank_line(code, start, end):
    """If removing [start, end) leaves an empty line, remove the line."""
    line_start = code.rfind("\n", 0, start) + 1
    line_end = code.find("\n", end)
    if line_end == -1:
        line_end = len(code)

    rest = code[line_start:start] + code[end:line_end]

    if rest.strip() == "":
        return line_start, min(line_end + 1, len(code))

    return start, end


# ---------------- edit generators ----------------

def _token_edits(code, tokens, e):
    """Insert / remove / replace tokens around the failing token e."""
    edits = []
    n = len(tokens)

    # Insert a missing token before token k (= after token k-1).
    for k in range(max(0, e - 4), min(n, e + 1) + 1):
        for symbol, cost in INSERTIONS:
            if symbol in PREFIX_SYMBOLS:
                if k >= n:
                    continue
                pos = tokens[k]["position"]
                text = symbol
            else:
                if k == 0:
                    continue
                pos = tokens[k - 1]["end"]
                text = INSERT_TEXT[symbol]

            # `int a = 5 b = 10;`  ->  a comma is far more likely than ';'
            if symbol == "," and _declaration_comma_likely(code, tokens, k):
                cost = 0

            edits.append(
                Edit([(pos, pos, text)], cost, f"Inserted a missing '{symbol}'")
            )

    # Merge split operators:  "= ="  ->  "=="
    for k in range(max(0, e - 2), min(n - 2, e) + 1):
        first, second = tokens[k], tokens[k + 1]
        combined = first["text"] + second["text"]

        if (
            combined in MERGEABLE_OPERATORS
            and first["type"] not in NON_PUNCTUATION
            and second["type"] not in NON_PUNCTUATION
            and first["end"] != second["position"]
        ):
            edits.append(
                Edit(
                    [(first["position"], second["end"], combined)],
                    1,
                    f"Merged '{first['text']} {second['text']}' "
                    f"into '{combined}'",
                )
            )

    # Remove or replace a token near the error.
    for k in range(max(0, e - 2), min(n - 1, e + 1) + 1):
        token = tokens[k]
        start, end = token["position"], token["end"]

        rm_start, rm_end = _expand_if_blank_line(code, start, end)
        edits.append(
            Edit(
                [(rm_start, rm_end, "")],
                2,
                f"Removed unexpected '{token['text']}'",
            )
        )

        if token["type"] not in NON_PUNCTUATION:
            for symbol in REPLACEMENTS:
                if symbol != token["text"]:
                    edits.append(
                        Edit(
                            [(start, end, symbol)],
                            3,
                            f"Replaced '{token['text']}' with '{symbol}'",
                        )
                    )

    return edits


def _declaration_comma_likely(code, tokens, k):
    """True if a ',' fits between token k-1 and token k: both are on the same
    line, token k is an identifier, and the statement started with a type
    (e.g. `int a = 5 b = 10;`)."""
    if k < 1 or k >= len(tokens):
        return False

    if tokens[k]["type"] != "ID":
        return False

    if "\n" in code[tokens[k - 1]["end"]:tokens[k]["position"]]:
        return False

    j = k - 1
    while j >= 0 and tokens[j]["type"] not in (
        "SEMICOLON", "LBRACE", "RBRACE"
    ):
        j -= 1

    return (
        j + 1 < len(tokens)
        and tokens[j + 1]["type"] in ("INT", "FLOAT", "CHAR")
    )


def _typo_edits(tokens):
    """Replace identifiers that look like misspelled keywords."""
    edits = []

    for token in tokens:
        if token["type"] != "ID":
            continue

        word = token["text"]
        if len(word) < 2:
            continue

        limit = 1 if len(word) <= 4 else 2
        best_keyword, best_distance = None, limit + 1

        for keyword in reserved:
            distance = _edit_distance(word.lower(), keyword)
            if distance < best_distance:
                best_keyword, best_distance = keyword, distance

        if best_keyword:
            edits.append(
                Edit(
                    [(token["position"], token["end"], best_keyword)],
                    1,
                    f"Replaced misspelled keyword '{word}' "
                    f"with '{best_keyword}'",
                )
            )

    return edits


def _closer_edit(code, tokens):
    """Append the brackets that are still open at the end of the code."""
    stack = []
    partner = {
        "RBRACE": "LBRACE",
        "RPAREN": "LPAREN",
        "RBRACKET": "LBRACKET",
    }

    for token in tokens:
        if token["type"] in ("LBRACE", "LPAREN", "LBRACKET"):
            stack.append(token["type"])
        elif token["type"] in partner:
            if not stack or stack[-1] != partner[token["type"]]:
                return None  # mismatched brackets: not a simple EOF fix
            stack.pop()

    if not stack:
        return None

    closing = {"LPAREN": ")", "LBRACKET": "]", "LBRACE": "\n}"}
    text = "".join(closing[t] for t in reversed(stack))
    pos = tokens[-1]["end"] if tokens else len(code)

    return Edit(
        [(pos, pos, text)],
        len(stack),
        f"Added {len(stack)} missing closing bracket(s) at the end",
    )


def _quote_edits(code, pos):
    """Close an unterminated string that starts at `pos`."""
    line_end = code.find("\n", pos)
    if line_end == -1:
        line_end = len(code)

    line = code[pos:line_end]
    comment_at = line.find("//")
    if comment_at != -1:
        line = line[:comment_at]
    body = line.rstrip()

    edits = []
    seen = set()

    for suffix in (");", ";", ")", ""):
        if suffix and not body.endswith(suffix):
            continue

        insert_at = pos + len(body) - len(suffix)

        if insert_at <= pos or insert_at in seen:
            continue

        seen.add(insert_at)
        edits.append(
            Edit(
                [(insert_at, insert_at, '"')],
                1,
                "Closed an unterminated string literal",
            )
        )

    return edits


def _illegal_edits(code, errors):
    """Fix illegal characters (pasted quotes, stray symbols, open strings)."""
    illegal = [e for e in errors if e["token_type"] == "ILLEGAL"]
    if not illegal:
        return []

    edits = []

    # 1. Typographic lookalikes -> plain ASCII (all at once, so “ ” pairs work)
    parts = []
    for error in illegal:
        pos = error["position"]
        char = code[pos]
        if char in LOOKALIKES:
            parts.append((pos, pos + 1, LOOKALIKES[char]))
    if parts:
        edits.append(
            Edit(parts, 1, "Replaced typographic characters with plain ASCII")
        )

    # 2. Remove stray characters such as @ $ ` (never a lone quote mark)
    parts = [
        (e["position"], e["position"] + 1, "")
        for e in illegal
        if code[e["position"]] in DELETABLE_CHARS
    ]
    if parts:
        edits.append(Edit(parts, 2, "Removed illegal character(s)"))

    # 3. Unterminated string literal
    for error in illegal:
        if code[error["position"]] == '"':
            edits.extend(_quote_edits(code, error["position"]))

    return edits


def _generate_edits(code, errors):
    first = errors[0]

    edits = _illegal_edits(code, errors)

    if first["token_type"] == "ILLEGAL":
        return edits

    tokens = tokenize(code)

    if first["position"] is None:
        e = len(tokens)  # error at end of input
        closer = _closer_edit(code, tokens)
        if closer:
            edits.append(closer)
    else:
        e = next(
            (
                i
                for i, token in enumerate(tokens)
                if token["position"] == first["position"]
            ),
            None,
        )

    if e is not None:
        edits.extend(_token_edits(code, tokens, e))

    edits.extend(_typo_edits(tokens))

    return edits


# ---------------- search ----------------

def _normalized_pos(state, source_code):
    """First-error position expressed in the original code's coordinates
    (so candidates with different edit lengths can be ranked fairly)."""
    pos = _first_pos(state.errors)
    if pos == INF:
        return INF
    return pos - (len(state.code) - len(source_code))


def repair_code(source_code):
    """Repair as many kinds of syntax errors as possible.

    Returns a dict with:
      success          True only if the repaired code parses with no errors
      repaired_code    the fully repaired code (None on failure)
      message          short summary
      fixes            list of human-readable fixes that were applied
      partial_code     best partial repair when a full repair is impossible
      remaining_errors errors still present in partial_code
    """
    _, errors = parse_code(source_code)

    if not errors:
        return _no_errors_result(source_code)

    started = time.monotonic()

    def out_of_time():
        return time.monotonic() - started > TIME_LIMIT_SECONDS

    beam = [State(source_code, errors, 0, [])]
    seen = {source_code}
    best_partial = None

    for _ in range(MAX_ROUNDS):
        if out_of_time():
            break

        candidates = []

        for state in beam:
            for edit in _generate_edits(state.code, state.errors):
                if out_of_time():
                    break

                new_code = _apply(state.code, edit)

                if new_code in seen:
                    continue
                seen.add(new_code)

                _, new_errors = parse_code(new_code)

                if not _progress(state.errors, new_errors, edit):
                    continue

                line = _line_of(state.code, edit.parts[0][0])
                candidates.append(
                    State(
                        new_code,
                        new_errors,
                        state.cost + edit.cost,
                        state.fixes + [f"Line {line}: {edit.label}"],
                    )
                )

        if not candidates:
            break

        solved = [c for c in candidates if not c.errors]
        if solved:
            best = min(solved, key=lambda c: c.cost)
            count = len(best.fixes)
            return {
                "success": True,
                "original_code": source_code,
                "repaired_code": best.code,
                "message": (
                    f"Repaired the code with {count} fix"
                    f"{'es' if count != 1 else ''}."
                ),
                "fixes": best.fixes,
                "partial_code": None,
                "remaining_errors": [],
            }

        candidates.sort(
            key=lambda c: (
                -_normalized_pos(c, source_code),
                c.cost,
                len(c.errors),
            )
        )
        beam = candidates[:BEAM_WIDTH]

        top = beam[0]
        if best_partial is None or (
            _normalized_pos(top, source_code),
            -top.cost,
        ) > (
            _normalized_pos(best_partial, source_code),
            -best_partial.cost,
        ):
            best_partial = top

    result = {
        "success": False,
        "original_code": source_code,
        "repaired_code": None,
        "message": "Could not fully repair the code automatically.",
        "fixes": [],
        "partial_code": None,
        "remaining_errors": [],
    }

    if best_partial is not None:
        result["fixes"] = best_partial.fixes
        result["partial_code"] = best_partial.code
        result["remaining_errors"] = best_partial.errors
        result["message"] = (
            "Could not fully repair the code. A partial repair is shown; "
            "the remaining errors need manual fixing."
        )

    return result


if __name__ == "__main__":
    test_cases = [
        ("Missing semicolon", "int x = 10\nx = x + 5;\n"),
        ("Missing closing parenthesis", "int x = 10;\nif (x > 5 {\n    return x;\n}\n"),
        ("Several errors", "int main() {\nint a\na =10\nprintf(\"%d\",a);\n"),
        ("Keyword typo", "int main() {\n    retrun 0;\n}\n"),
        ("= instead of ==", "int main() {\n    int x = 1;\n    if (x = 1) {\n        x = 2;\n    }\n}\n"),
        ("Extra brace", "int main() {\n    int x = 1;\n}\n}\n"),
        ("Unterminated string", "int main() {\n    printf(\"hello);\n    return 0;\n}\n"),
        ("Valid code", "int x = 10;\nx = x + 5;\n"),
    ]

    for name, code in test_cases:
        print(f"\n--- {name} ---")

        result = repair_code(code)
        print(result["message"])

        for fix in result["fixes"]:
            print("  -", fix)

        if result["success"]:
            print(result["repaired_code"])
        else:
            print("No full repair.")