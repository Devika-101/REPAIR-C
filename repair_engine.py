
from parser_module import parse_code


def repair_missing_semicolon(source_code):
    """
    Attempts to repair a missing semicolon by inserting one
    before a line that the parser reports as unexpected.
    """

    syntax_tree, errors = parse_code(source_code)

    # If the program is already valid, no repair is needed.
    if not errors:
        return {
            "success": True,
            "original_code": source_code,
            "repaired_code": source_code,
            "message": "No syntax errors found.",
        }

    repaired_code = source_code

    # Try inserting a semicolon at the end of the
    # line immediately before the reported error.
    for error in errors:
        if error["message"].startswith("Unexpected token"):
            error_line = error["line"]
            lines = repaired_code.splitlines()

            previous_line = error_line - 2

            if 0 <= previous_line < len(lines):
                candidate_lines = lines.copy()

                if not candidate_lines[previous_line].rstrip().endswith(
                    (";", "{", "}", ":")
                ):
                    candidate_lines[previous_line] = (
                        candidate_lines[previous_line].rstrip() + ";"
                    )

                    candidate_code = "\n".join(candidate_lines)

                    # Accept the candidate only if parsing succeeds.
                    candidate_tree, candidate_errors = parse_code(
                        candidate_code
                    )

                    if not candidate_errors and candidate_tree is not None:
                        return {
                            "success": True,
                            "original_code": source_code,
                            "repaired_code": candidate_code,
                            "message": (
                                f"Inserted a missing semicolon "
                                f"on line {error_line - 1}."
                            ),
                        }

    return {
        "success": False,
        "original_code": source_code,
        "repaired_code": None,
        "message": "Could not automatically repair this syntax error.",
    }

if __name__ == "__main__":
    test_cases = [
        ("Missing semicolon", """int x = 10
x = x + 5;
"""),
        ("Valid code", """int x = 10;
x = x + 5;
"""),
    ]

    for name, code in test_cases:
        print(f"\n--- {name} ---")
        result = repair_missing_semicolon(code)
        print(result["message"])
        print(result["repaired_code"] or "No repair generated.")