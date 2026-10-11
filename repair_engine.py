
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

def repair_missing_parenthesis(source_code):
    """
    Attempts to insert a missing closing parenthesis
    before an opening curly brace.
    """
    syntax_tree, errors = parse_code(source_code)

    if not errors:
        return {
            "success": True,
            "repaired_code": source_code,
            "message": "No syntax errors found.",
        }

    lines = source_code.splitlines()

    for line_index, line in enumerate(lines):
        # Target conditions such as: if (x > 5 {
        stripped = line.strip()

        if (
            stripped.startswith(("if (", "while (", "for ("))
            and "{" in stripped
            and stripped.count("(") > stripped.count(")")
        ):
            candidate_lines = lines.copy()
            brace_index = candidate_lines[line_index].find("{")

            candidate_lines[line_index] = (
                candidate_lines[line_index][:brace_index].rstrip()
                + ") "
                + candidate_lines[line_index][brace_index:]
            )

            candidate_code = "\n".join(candidate_lines)
            candidate_tree, candidate_errors = parse_code(candidate_code)

            if not candidate_errors and candidate_tree is not None:
                return {
                    "success": True,
                    "repaired_code": candidate_code,
                    "message": (
                        f"Inserted a missing closing parenthesis "
                        f"on line {line_index + 1}."
                    ),
                }

    return {
        "success": False,
        "repaired_code": None,
        "message": "Could not repair a missing closing parenthesis.",
    }


if __name__ == "__main__":
    broken_code = """int x = 10;
if (x > 5 {
    return x;
}
"""

    result = repair_missing_parenthesis(broken_code)

    print("Original code:")
    print(broken_code)

    print("\nRepair result:")
    print(result["message"])

    if result["success"]:
        print("\nRepaired code:")
        print(result["repaired_code"])
