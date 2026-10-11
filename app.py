"""REPAIR-C | AI-Powered Self-Healing Compiler Dashboard.

A modern developer-grade UI for analyzing syntax errors and applying
heuristic self-healing compiler repairs to C source code.
"""

import difflib
import time
from typing import Any, Dict, List, Optional

import streamlit as st

from parser_module import parse_code
from repair_engine import REPAIR_STRATEGIES, repair_code

# ---------------- Page Configuration ----------------

st.set_page_config(
    page_title="REPAIR-C | AI Code Repair Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Benchmark Presets ----------------

PRESETS: Dict[str, Dict[str, str]] = {
    "Missing Semicolon": {
        "description": "Variable initialization missing a terminal semicolon",
        "code": (
            "int main() {\n"
            "    int x = 10\n"
            "    x = x + 5;\n"
            "    return x;\n"
            "}\n"
        ),
    },
    "Unclosed Condition Parenthesis": {
        "description": "If-statement with missing closing parenthesis",
        "code": (
            "int main() {\n"
            "    int x = 10;\n"
            "    if (x > 5 {\n"
            "        return x;\n"
            "    }\n"
            "}\n"
        ),
    },
    "Misspelled Keyword": {
        "description": "Typo in loop keyword ('fro' instead of 'for')",
        "code": (
            "int main() {\n"
            "    int x = 0;\n"
            "    fro (int i = 0; i < 10; i++) {\n"
            "        x += i;\n"
            "    }\n"
            "    return x;\n"
            "}\n"
        ),
    },
    "Unclosed Block Braces": {
        "description": "Loop block missing trailing closing brace before EOF",
        "code": (
            "int main() {\n"
            "    int count = 0;\n"
            "    while (count < 5) {\n"
            "        count++;\n"
        ),
    },
    "Assignment vs Equality": {
        "description": "Single '=' assignment in conditional expression instead of '=='",
        "code": (
            "int main() {\n"
            "    int x = 1;\n"
            "    if (x = 1) {\n"
            "        x = 2;\n"
            "    }\n"
            "}\n"
        ),
    },
    "Unterminated String Literal": {
        "description": "Missing closing quotation mark in string argument",
        "code": (
            "int main() {\n"
            "    printf(\"Hello, Compiler!);\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    "Multiple Compound Errors": {
        "description": "Missing semicolon, keyword typo, and dangling scope",
        "code": (
            "int main() {\n"
            "    int a = 5\n"
            "    int b = 10;\n"
            "    retrun a + b;\n"
        ),
    },
    "Clean & Valid Program": {
        "description": "Fully compliant ANSI C program without errors",
        "code": (
            "int main() {\n"
            "    int sum = 0;\n"
            "    for (int i = 0; i < 10; i++) {\n"
            "        sum += i;\n"
            "    }\n"
            "    return sum;\n"
            "}\n"
        ),
    },
}

DEFAULT_PRESET_NAME = "Missing Semicolon"

# ---------------- Custom Dark CSS Injection ----------------

st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-obsidian: #0b0f19;
        --card-bg: rgba(19, 27, 46, 0.75);
        --card-border: rgba(139, 92, 246, 0.22);
        --accent-purple: #8b5cf6;
        --accent-purple-glow: rgba(139, 92, 246, 0.35);
        --accent-blue: #3b82f6;
        --accent-blue-glow: rgba(59, 130, 246, 0.3);
        --accent-cyan: #06b6d4;
        --accent-emerald: #10b981;
        --accent-rose: #f43f5e;
        --accent-amber: #f59e0b;
        --text-pure: #f8fafc;
        --text-muted: #94a3b8;
    }

    /* Global typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Main container tweaks */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 96%;
    }

    /* Header styling */
    .engine-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid var(--card-border);
        border-radius: 14px;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .engine-title-box h1 {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
        background: linear-gradient(135deg, #c084fc 0%, #818cf8 50%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    .engine-subtitle {
        color: var(--text-muted);
        font-size: 0.88rem;
        margin-top: 0.25rem;
        font-weight: 400;
    }

    .status-badge-group {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }

    .badge-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 9999px;
        padding: 0.28rem 0.75rem;
        font-size: 0.76rem;
        font-weight: 500;
        color: #cbd5e1;
        letter-spacing: 0.02em;
    }

    .badge-chip.online {
        border-color: rgba(16, 185, 129, 0.4);
        color: #34d399;
    }

    .badge-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
    }

    /* Panel Card Containers */
    .panel-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(8px);
    }

    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        padding-bottom: 0.65rem;
        margin-bottom: 0.85rem;
    }

    .panel-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-pure);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        letter-spacing: 0.01em;
    }

    /* Textarea / Code Editor styling */
    .stTextArea textarea {
        font-family: 'Fira Code', 'JetBrains Mono', Consolas, monospace !important;
        font-size: 0.90rem !important;
        line-height: 1.55 !important;
        background-color: #0d121f !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(139, 92, 246, 0.28) !important;
        border-radius: 8px !important;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.6) !important;
        tab-size: 4 !important;
    }

    .stTextArea textarea:focus {
        border-color: var(--accent-purple) !important;
        box-shadow: 0 0 0 2px var(--accent-purple-glow), inset 0 2px 8px rgba(0,0,0,0.6) !important;
    }

    /* Error cards */
    .error-card {
        background: rgba(30, 16, 26, 0.65);
        border-left: 4px solid #f43f5e;
        border-top: 1px solid rgba(244, 63, 94, 0.2);
        border-right: 1px solid rgba(244, 63, 94, 0.2);
        border-bottom: 1px solid rgba(244, 63, 94, 0.2);
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.65rem;
    }

    .error-card-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.88rem;
        font-weight: 600;
        color: #fda4af;
    }

    .error-card-meta {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-top: 0.2rem;
        font-family: 'Fira Code', monospace;
    }

    /* Fix pill */
    .fix-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 6px;
        padding: 0.35rem 0.75rem;
        font-size: 0.82rem;
        color: #6ee7b7;
        margin-bottom: 0.4rem;
        font-family: 'Fira Code', monospace;
    }

    /* Stat card */
    .stat-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        text-align: left;
    }

    .stat-val {
        font-size: 1.55rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }

    .stat-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* Diff styling block */
    .diff-stat-bar {
        display: flex;
        gap: 1.2rem;
        font-size: 0.82rem;
        color: #94a3b8;
        margin-bottom: 0.6rem;
    }

    .diff-add {
        color: #34d399;
        font-weight: 600;
    }

    .diff-del {
        color: #f87171;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Session State Initialization ----------------

if "source_code" not in st.session_state:
    st.session_state.source_code = PRESETS[DEFAULT_PRESET_NAME]["code"]

if "selected_preset_name" not in st.session_state:
    st.session_state.selected_preset_name = DEFAULT_PRESET_NAME

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "repair_data" not in st.session_state:
    st.session_state.repair_data = None

if "last_action" not in st.session_state:
    st.session_state.last_action = None

if "repair_toast_pending" not in st.session_state:
    st.session_state.repair_toast_pending = False


# ---------------- State Mutation Callbacks ----------------


def on_preset_change() -> None:
    """Callback when user selects a different benchmark preset."""
    chosen = st.session_state.preset_selector
    if chosen in PRESETS:
        st.session_state.source_code = PRESETS[chosen]["code"]
        st.session_state.selected_preset_name = chosen
        st.session_state.analysis_data = None
        st.session_state.repair_data = None
        st.session_state.last_action = None


def reset_to_default() -> None:
    """Callback to reset source code back to default."""
    st.session_state.source_code = PRESETS[DEFAULT_PRESET_NAME]["code"]
    st.session_state.selected_preset_name = DEFAULT_PRESET_NAME
    st.session_state.analysis_data = None
    st.session_state.repair_data = None
    st.session_state.last_action = None


def clear_code_editor() -> None:
    """Callback to clear editor content."""
    st.session_state.source_code = ""
    st.session_state.analysis_data = None
    st.session_state.repair_data = None
    st.session_state.last_action = None


def apply_repaired_code_to_editor() -> None:
    """Callback to overwrite editor with newly repaired C code."""
    if st.session_state.repair_data:
        res = st.session_state.repair_data.get("result", {})
        code_to_apply = res.get("repaired_code") or res.get("partial_code")
        if code_to_apply:
            st.session_state.source_code = code_to_apply
            st.session_state.repair_toast_pending = True
            # Re-run a fast parse on newly applied code so status updates
            _, fresh_errors = parse_code(code_to_apply)
            st.session_state.analysis_data = {
                "source": code_to_apply,
                "errors": fresh_errors,
                "elapsed_ms": 0.0,
            }
            # Clear old repair result since it has now become the active editor source
            st.session_state.repair_data = None
            st.session_state.last_action = "applied"


# ---------------- Helper Functions ----------------


def compute_unified_diff(original: str, repaired: str) -> str:
    """Accurately compute unified diff between original and repaired source."""
    orig_lines = original.replace("\r\n", "\n").splitlines(keepends=True)
    rep_lines = repaired.replace("\r\n", "\n").splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        rep_lines,
        fromfile="original.c",
        tofile="repaired.c",
        lineterm="",
    )
    return "".join(diff)


# ---------------- Sidebar Dashboard Controls ----------------

with st.sidebar:
    st.markdown("### ⚙️ Engine Control Panel")
    st.caption("Compiler Design Microproject | Heuristic Beam Search")

    st.markdown("---")
    st.markdown("#### 📂 Benchmark Test Suites")
    preset_keys = list(PRESETS.keys())
    current_idx = (
        preset_keys.index(st.session_state.selected_preset_name)
        if st.session_state.selected_preset_name in preset_keys
        else 0
    )

    st.selectbox(
        "Load test scenario:",
        options=preset_keys,
        index=current_idx,
        key="preset_selector",
        on_change=on_preset_change,
        help="Select a curated C syntax error benchmark to test the engine.",
    )

    chosen_meta = PRESETS.get(st.session_state.selected_preset_name, {})
    if "description" in chosen_meta:
        st.info(f"**Scenario:** {chosen_meta['description']}", icon="💡")

    st.markdown("---")
    st.markdown("#### 🛠️ Quick Actions")

    col_rst, col_clr = st.columns(2)
    with col_rst:
        st.button(
            "↺ Reset Code",
            on_click=reset_to_default,
            use_container_width=True,
            help="Reset editor to initial benchmark",
        )
    with col_clr:
        st.button(
            "🗑️ Clear",
            on_click=clear_code_editor,
            use_container_width=True,
            help="Clear all text in code editor",
        )

    st.markdown("---")
    st.markdown("#### 📋 Engine Capabilities")
    with st.expander(f"Active Strategies ({len(REPAIR_STRATEGIES)})", expanded=False):
        for idx, strat in enumerate(REPAIR_STRATEGIES, start=1):
            st.markdown(f"**{idx}.** {strat}")

    st.caption(
        "Powered by PLY (Python Lex-Yacc) and iterative beam search with "
        "Damerau-Levenshtein distance heuristic."
    )


# ---------------- Header Banner ----------------

st.markdown(
    """
    <div class="engine-header">
        <div class="engine-title-box">
            <h1>⚡ REPAIR-C</h1>
            <div class="engine-subtitle">
                Self-Healing Compiler for C &bull; Syntax Diagnostics & Heuristic Repair
            </div>
        </div>
        <div class="status-badge-group">
            <div class="badge-chip online">
                <span class="badge-dot"></span>
                <span>LALR(1) Parser Online</span>
            </div>
            <div class="badge-chip">
                <span>Grammar: ANSI C Subset</span>
            </div>
            <div class="badge-chip">
                <span>Beam Search: 6 Strategies</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.repair_toast_pending:
    st.toast("Repaired code applied to editor!", icon="✅")
    st.session_state.repair_toast_pending = False


# ---------------- Main Action Controls ----------------

col_btn_analyze, col_btn_repair, col_spacer = st.columns([1.5, 1.5, 3.5])

with col_btn_analyze:
    analyze_clicked = st.button(
        "🔍 Analyze Code",
        type="secondary",
        use_container_width=True,
        help="Runs only lexical & syntax analysis without altering code",
    )

with col_btn_repair:
    repair_clicked = st.button(
        "⚡ Repair Code",
        type="primary",
        use_container_width=True,
        help="Executes self-healing beam search to repair syntax errors",
    )

# ---------------- Execution Logic ----------------

current_code = st.session_state.source_code

if analyze_clicked:
    if not current_code.strip():
        st.warning("Please enter or paste C source code to analyze.", icon="⚠️")
    else:
        with st.spinner("Analyzing lexical tokens and parsing syntax tree..."):
            t_start = time.perf_counter()
            try:
                tree, errors = parse_code(current_code)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                st.session_state.analysis_data = {
                    "source": current_code,
                    "tree": tree,
                    "errors": errors,
                    "elapsed_ms": elapsed_ms,
                }
                st.session_state.repair_data = None
                st.session_state.last_action = "analyze"
                if errors:
                    st.toast(
                        f"Analysis complete: {len(errors)} error(s) detected",
                        icon="⚠️",
                    )
                else:
                    st.toast(
                        "Analysis complete: Clean C syntax! No errors found.",
                        icon="✅",
                    )
            except Exception as exc:
                st.session_state.analysis_data = {
                    "source": current_code,
                    "exception": str(exc),
                    "errors": [],
                    "elapsed_ms": 0.0,
                }
                st.session_state.last_action = "analyze"

if repair_clicked:
    if not current_code.strip():
        st.warning("Please enter or paste C source code to repair.", icon="⚠️")
    else:
        with st.spinner("Running syntax parsing & heuristic beam search repair..."):
            t_start = time.perf_counter()
            try:
                _, errors = parse_code(current_code)
                result = repair_code(current_code)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0

                st.session_state.analysis_data = {
                    "source": current_code,
                    "errors": errors,
                    "elapsed_ms": elapsed_ms,
                }
                st.session_state.repair_data = {
                    "source": current_code,
                    "errors": errors,
                    "result": result,
                    "elapsed_ms": elapsed_ms,
                }
                st.session_state.last_action = "repair"

                if result.get("success"):
                    fix_cnt = len(result.get("fixes", []))
                    st.toast(
                        f"Repair complete: Code successfully fixed with {fix_cnt} edit(s)!",
                        icon="✨",
                    )
                elif result.get("partial_code"):
                    st.toast(
                        "Partial repair generated. Manual fixes needed for remaining errors.",
                        icon="⚠️",
                    )
                else:
                    st.toast(
                        "Could not automatically repair syntax errors.",
                        icon="❌",
                    )
            except Exception as exc:
                st.session_state.repair_data = {
                    "source": current_code,
                    "exception": str(exc),
                }
                st.session_state.last_action = "repair"


# ---------------- Two-Column Code Workspace ----------------

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
col_editor, col_repaired = st.columns(2)

# ----- Left Panel: Source Code Editor -----
with col_editor:
    st.markdown(
        """
        <div class="panel-header">
            <span class="panel-title">📝 C Source Code Editor</span>
            <span style="font-size: 0.78rem; color: #94a3b8; font-family: monospace;">Input Source</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.text_area(
        label="Write or edit your C code here",
        key="source_code",
        height=340,
        label_visibility="collapsed",
        help="Type or paste C code. Then click Analyze Code or Repair Code.",
    )

    line_count = len(st.session_state.source_code.splitlines())
    char_count = len(st.session_state.source_code)
    st.markdown(
        f"<div style='font-size: 0.76rem; color: #64748b; font-family: monospace; display: flex; justify-content: space-between;'>"
        f"<span>Lines: {line_count} | Characters: {char_count}</span>"
        f"<span>Encoding: UTF-8</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ----- Right Panel: Repaired Output -----
with col_repaired:
    repair_info = st.session_state.repair_data
    rep_result = repair_info.get("result") if repair_info else None

    # Compute repair state for display header
    if rep_result:
        was_repaired = (
            rep_result["success"]
            and rep_result["repaired_code"] != repair_info["source"]
        )
        if was_repaired:
            status_chip = "<span style='color: #34d399; font-weight: 600;'>● Repaired</span>"
        elif not repair_info["errors"]:
            status_chip = "<span style='color: #60a5fa; font-weight: 600;'>● Already Valid</span>"
        elif rep_result.get("partial_code"):
            status_chip = "<span style='color: #fbbf24; font-weight: 600;'>▲ Partially Repaired</span>"
        else:
            status_chip = "<span style='color: #f87171; font-weight: 600;'>✕ Not Repaired</span>"
    else:
        status_chip = "<span style='color: #64748b;'>Awaiting Repair</span>"

    st.markdown(
        f"""
        <div class="panel-header">
            <span class="panel-title">🛠️ Repaired Code Output</span>
            <span style="font-size: 0.78rem; font-family: monospace;">{status_chip}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if rep_result:
        final_code = (
            rep_result["repaired_code"]
            if rep_result.get("success")
            else rep_result.get("partial_code")
        )

        if final_code:
            st.code(final_code, language="c", line_numbers=True)

            col_apply, col_dl = st.columns(2)
            with col_apply:
                st.button(
                    "✅ Apply Repair to Editor",
                    on_click=apply_repaired_code_to_editor,
                    use_container_width=True,
                    help="Copies this repaired code directly into your active code editor",
                )
            with col_dl:
                st.download_button(
                    label="⬇️ Download .c File",
                    data=final_code,
                    file_name="repaired_code.c",
                    mime="text/x-c",
                    use_container_width=True,
                )
        else:
            st.error("No valid repair candidate was found for this code.")
            st.info(
                "The repair engine exhausted candidate edits. "
                "Review the syntax error diagnostics below.",
                icon="ℹ️",
            )
    else:
        # Placeholder view when no repair has been executed yet
        st.markdown(
            """
            <div style="height: 340px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(13, 18, 31, 0.4); border: 1px dashed rgba(139, 92, 246, 0.25); border-radius: 8px; color: #64748b; text-align: center; padding: 2rem;">
                <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">⚡</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #94a3b8; margin-bottom: 0.25rem;">Repaired code will appear here</div>
                <div style="font-size: 0.82rem;">Click <strong>Analyze Code</strong> to check for syntax issues, or <strong>Repair Code</strong> to run the engine.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------- Diagnostics & Comparison Section ----------------

analysis = st.session_state.analysis_data
repair = st.session_state.repair_data

if analysis or repair:
    st.markdown("<hr style='border-color: rgba(139, 92, 246, 0.2); margin: 1.75rem 0;'>", unsafe_allow_html=True)

    # Global Exception Trap
    exc_msg = (
        analysis.get("exception")
        if analysis and "exception" in analysis
        else (repair.get("exception") if repair and "exception" in repair else None)
    )

    if exc_msg:
        st.error("An unexpected error occurred during execution:")
        st.code(exc_msg)
    else:
        active_source = (
            repair["source"]
            if repair and "source" in repair
            else analysis.get("source", current_code)
        )
        errors = (
            repair["errors"]
            if repair and "errors" in repair
            else analysis.get("errors", [])
        )
        elapsed = (
            repair["elapsed_ms"]
            if repair and "elapsed_ms" in repair
            else analysis.get("elapsed_ms", 0.0)
        )

        # ---------------- Metrics Ribbon ----------------
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)

        with m_col1:
            err_cnt = len(errors)
            m_col1.metric("Syntax Errors", err_cnt)

        with m_col2:
            if repair and repair.get("result"):
                r_res = repair["result"]
                if r_res["success"] and r_res["repaired_code"] != active_source:
                    stat_label = "Repaired"
                elif not errors:
                    stat_label = "Valid Syntax"
                elif r_res.get("partial_code"):
                    stat_label = "Partial Repair"
                else:
                    stat_label = "Not Repaired"
            else:
                stat_label = "Analyzed (Clean)" if not errors else "Errors Found"
            m_col2.metric("Status", stat_label)

        with m_col3:
            fixes_cnt = (
                len(repair["result"].get("fixes", []))
                if repair and repair.get("result")
                else 0
            )
            m_col3.metric("Fixes Applied", fixes_cnt)

        with m_col4:
            m_col4.metric(
                "Execution Time",
                f"{elapsed:.1f} ms" if elapsed > 0 else "< 1 ms",
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ---------------- Tabs: Diagnostics & Comparison ----------------
        tab_errors, tab_diff, tab_fixes = st.tabs(
            [
                f"🚨 Error Diagnostics ({len(errors)})",
                "🔄 Before & After Code Diff",
                f"🧰 Applied Fixes & Strategies ({fixes_cnt})",
            ]
        )

        # ===== TAB 1: Error Diagnostics =====
        with tab_errors:
            if errors:
                st.markdown(
                    f"<div style='font-size: 0.9rem; font-weight: 600; color: #f87171; margin-bottom: 0.6rem;'>"
                    f"Found {len(errors)} syntax or lexical issue(s) in source code:</div>",
                    unsafe_allow_html=True,
                )

                for idx, err in enumerate(errors, start=1):
                    line = err.get("line")
                    pos = err.get("position")
                    tok_type = err.get("token_type") or "SYNTAX"
                    msg = err.get("message", "Syntax error")

                    loc_str = f"Line {line}" if line is not None else "End of Input"
                    pos_str = f" | Offset: {pos}" if pos is not None else ""

                    st.markdown(
                        f"""
                        <div class="error-card">
                            <div class="error-card-title">
                                <span>⚠️ Error #{idx}:</span>
                                <span>{msg}</span>
                            </div>
                            <div class="error-card-meta">
                                Location: <strong>{loc_str}</strong>{pos_str} &bull; Token Classification: <strong>{tok_type}</strong>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if not repair:
                    st.info(
                        "Click the **⚡ Repair Code** button above to run the beam search "
                        "and automatically resolve these issues.",
                        icon="💡",
                    )
            else:
                st.success("No syntax errors detected! The code conforms to supported C grammar rules.")

            # Remaining errors after partial repair
            if repair and repair.get("result"):
                remaining = repair["result"].get("remaining_errors") or []
                if remaining:
                    st.markdown("---")
                    st.markdown("#### 🚧 Errors Still Requiring Manual Attention")
                    for err in remaining:
                        r_line = err.get("line")
                        r_loc = f"Line {r_line}" if r_line is not None else "End of Input"
                        st.warning(f"**{r_loc}**: {err.get('message')}")

        # ===== TAB 2: Before & After Diff =====
        with tab_diff:
            if repair and repair.get("result"):
                r_res = repair["result"]
                repaired_final = (
                    r_res.get("repaired_code")
                    if r_res.get("success")
                    else r_res.get("partial_code")
                )

                if repaired_final:
                    diff_text = compute_unified_diff(active_source, repaired_final)

                    if diff_text.strip():
                        # Count additions and deletions
                        diff_lines = diff_text.splitlines()
                        additions = sum(
                            1
                            for line in diff_lines
                            if line.startswith("+") and not line.startswith("+++")
                        )
                        deletions = sum(
                            1
                            for line in diff_lines
                            if line.startswith("-") and not line.startswith("---")
                        )

                        st.markdown(
                            f"""
                            <div class="diff-stat-bar">
                                <span>Unified Diff:</span>
                                <span class="diff-add">+{additions} addition(s)</span>
                                <span class="diff-del">-{deletions} removal(s)</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.code(diff_text, language="diff", line_numbers=True)
                    else:
                        st.info("No modifications were required; source code is identical to output.")
                else:
                    st.warning("No repaired candidate available to compute difference.")
            else:
                st.info(
                    "Run **⚡ Repair Code** to view the automated diff between original and repaired source code."
                )

        # ===== TAB 3: Applied Fixes & Strategies =====
        with tab_fixes:
            if repair and repair.get("result"):
                r_res = repair["result"]
                st.markdown(f"**Engine Summary:** {r_res.get('message', 'Completed')}")

                fixes = r_res.get("fixes") or []
                if fixes:
                    st.markdown("##### Detailed Fix Sequence Applied:")
                    for fix_item in fixes:
                        st.markdown(
                            f"<div class='fix-pill'><span>✔</span> <span>{fix_item}</span></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No repair transformations were applied.")
            else:
                st.info("Execute **⚡ Repair Code** to see the list of applied repair rules.")