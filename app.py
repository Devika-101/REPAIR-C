import inspect

import streamlit as st

from parser_module import parse_code
from repair_engine import REPAIR_STRATEGIES, repair_code

st.set_page_config(
    page_title="REPAIR-C | Self-Healing Compiler",
    page_icon="🛠️",
    layout="wide",
)

EXAMPLE_CODE = (
    "int main() {\n"
    "    int x = 10\n"
    "    x = x + 5;\n"
    "    return x;\n"
    "}\n"
)

# Newer Streamlit versions use width="stretch"; older ones use
# use_container_width=True. Pick whichever this install supports.
if "width" in inspect.signature(st.button).parameters:
    STRETCH = {"width": "stretch"}
else:
    STRETCH = {"use_container_width": True}


# ---------------- callbacks ----------------
# Widget-bound values (like the text area's key) may only be changed inside
# callbacks, which run before the widget is created on the next rerun.

def reset_example():
    st.session_state.source_code = EXAMPLE_CODE
    st.session_state.analysis_result = None


def apply_repair():
    result = st.session_state.analysis_result["result"]
    st.session_state.source_code = (
        result["repaired_code"] or result["partial_code"]
    )
    st.session_state.analysis_result = None


# ---------------- state ----------------

if "source_code" not in st.session_state:
    st.session_state.source_code = EXAMPLE_CODE

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


# ---------------- UI ----------------

st.title("🛠️ REPAIR-C")
st.subheader("A Self-Healing Compiler for C")
st.write(
    "Enter C code, analyze syntax errors, and generate "
    "automatically repaired code."
)

st.markdown("### 📝 C Code Editor")

source_code = st.text_area(
    "Write or paste your C code here",
    key="source_code",
    height=300,
)

col1, col2 = st.columns(2)

with col1:
    analyze_clicked = st.button(
        "🔍 Analyze & Repair",
        type="primary",
        **STRETCH,
    )

with col2:
    st.button(
        "↺ Reset Example",
        on_click=reset_example,
        **STRETCH,
    )

if analyze_clicked:
    with st.spinner("Analyzing your C code..."):
        try:
            # parse_code returns a copy of the error list, so repair_code
            # cannot overwrite it.
            _, errors = parse_code(source_code)
            result = repair_code(source_code)

            st.session_state.analysis_result = {
                "source": source_code,  # the code that was analyzed
                "errors": errors,
                "result": result,
            }
        except Exception as error:
            st.session_state.analysis_result = {"exception": str(error)}

analysis = st.session_state.analysis_result

if analysis:
    st.divider()
    st.markdown("## 📊 Analysis Results")

    if "exception" in analysis:
        st.error("An unexpected error occurred.")
        st.code(analysis["exception"])
    else:
        analyzed_code = analysis["source"]
        errors = analysis["errors"]
        result = analysis["result"]

        was_repaired = (
            result["success"]
            and result["repaired_code"] != analyzed_code
        )

        if was_repaired:
            status = "Repaired"
        elif not errors:
            status = "Valid"
        elif result.get("partial_code"):
            status = "Partially Repaired"
        else:
            status = "Not Repaired"

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Syntax Errors", len(errors))
        metric2.metric("Repair Status", status)
        metric3.metric(
            "Repair Strategies", f"{len(REPAIR_STRATEGIES)} available"
        )

        if errors:
            st.markdown("### ⚠️ Detected Errors")

            for index, error in enumerate(errors, start=1):
                line = error.get("line")
                location = (
                    f"Line {line}"
                    if line is not None
                    else "End of input"
                )

                st.warning(
                    f"Error {index}: {error['message']} ({location})"
                )
        else:
            st.success("No syntax errors detected!")

        st.markdown("### 🧰 Repair Result")
        st.info(result["message"])

        fixes = result.get("fixes") or []
        if fixes:
            st.markdown("**Fixes applied:**")
            for fix in fixes:
                st.markdown(f"- {fix}")

        original_col, repaired_col = st.columns(2)

        with original_col:
            st.markdown("#### Original Code")
            st.code(analyzed_code, language="c")

        with repaired_col:
            partial_code = result.get("partial_code")

            if result["success"]:
                st.markdown("#### Repaired Code")
                st.code(result["repaired_code"], language="c")
            elif partial_code:
                st.markdown("#### Partially Repaired Code")
                st.code(partial_code, language="c")
            else:
                st.markdown("#### Repaired Code")
                st.warning("No valid repair candidate was found.")

        remaining = result.get("remaining_errors") or []
        if remaining:
            st.markdown("### 🚧 Errors still needing manual fixes")
            for error in remaining:
                line = error.get("line")
                location = f"Line {line}" if line is not None else "End of input"
                st.warning(f"{error['message']} ({location})")

        final_code = (
            result["repaired_code"] if was_repaired else result.get("partial_code")
        )

        if final_code:
            btn1, btn2 = st.columns(2)

            with btn1:
                st.download_button(
                    "⬇️ Download Repaired Code",
                    data=final_code,
                    file_name="repaired_code.c",
                    mime="text/plain",
                    **STRETCH,
                )

            with btn2:
                st.button(
                    "✅ Apply Repair to Editor",
                    on_click=apply_repair,
                    **STRETCH,
                )