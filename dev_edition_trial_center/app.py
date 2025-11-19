"""Streamlit UI for the Dev Edition Trial Center."""

from __future__ import annotations
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import streamlit as st

try:
    from .trial_center_pipeline import (
        GuardrailConfig,
        GuardrailResult,
        PromptSanitizer,
        SanitizationConfig,
        SanitizationResult,
        SemanticGuardrailClient,
    )
except ImportError:  # Executed when run outside package context
    import sys

    PACKAGE_ROOT = Path(__file__).resolve().parent
    sys.path.append(str(PACKAGE_ROOT.parent))
    from dev_edition_trial_center.trial_center_pipeline import (  # type: ignore  # noqa: E402
        GuardrailConfig,
        GuardrailResult,
        PromptSanitizer,
        SanitizationConfig,
        SanitizationResult,
        SemanticGuardrailClient,
    )


st.set_page_config(page_title="Dev Edition Trial Center", layout="wide")

# Header with navigation links
col_left, col_center, col_right = st.columns([1, 3, 1])

with col_left:
    st.empty()

with col_center:
    st.title("Dev Edition Trial Center")
    st.caption("Trial center for combining Protegrity Developer Edition services to safeguard GenAI prompts.")

with col_right:
    st.markdown(
        """
        <div style="text-align: right; line-height: 1.8;">
            <a href="https://github.com/Protegrity-Developer-Edition/protegrity-developer-edition" 
               target="_blank" 
               title="Visit the official Protegrity Developer Edition GitHub repository"
               style="text-decoration: none; color: #58a6ff; font-size: 14px; display: block;">
                📂 GitHub Repository
            </a>
            <a href="https://www.protegrity.com/developers/api-playground" 
               target="_blank" 
               title="Get your API credentials to enable protect/unprotect operations"
               style="text-decoration: none; color: #58a6ff; font-size: 14px; display: block;">
                🔑 Protegrity API Playground
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Show shared environment disclaimer banner
import os
if os.getenv("SHARED_TRIAL_MODE", "false").lower() == "true":
    st.info(
        """
        **🔓 Shared Trial Environment**  
        This is a demonstration environment using shared credentials. All users have access to the same protection capabilities.  
        **⚠️ Do not enter real customer data or sensitive information.** This environment is for testing and evaluation purposes only.
        """,
        icon="ℹ️"
    )

st.markdown(
    """
    <style>
        div[data-testid="stToolbar"],
        #MainMenu,
        footer,
        section[data-testid="stSidebar"],
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        
        /* Style dropdown menu with gray background */
        [data-baseweb="popover"] {
            background-color: #262730 !important;
        }
        
        [data-baseweb="menu"] {
            background-color: #262730 !important;
        }
        
        [data-baseweb="menu"] li {
            background-color: #262730 !important;
        }
        
        [data-baseweb="menu"] li:hover {
            background-color: #31333f !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


DEFAULT_GUARDRAIL_URL = GuardrailConfig().url
class SessionLogHandler(logging.Handler):
    """In-memory log handler that feeds the Streamlit log view."""

    def __init__(self, buffer: List[str]) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            message = self.format(record)
        except Exception:  # noqa: BLE001
            message = record.getMessage()
        self._buffer.append(message)


@contextmanager
def capture_pipeline_logs(level: int, logger_names: Optional[List[str]] = None) -> Iterator[List[str]]:
    """Capture pipeline logs for the most recent run."""

    log_buffer = st.session_state.setdefault("run_logs", [])
    log_buffer.clear()
    handler = SessionLogHandler(log_buffer)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%H:%M:%S | %(levelname)s | %(name)s | %(message)s"))

    root_logger = logging.getLogger()
    targeted_loggers: List[logging.Logger] = []
    seen = set()
    for name in logger_names or []:
        logger = logging.getLogger(name)
        if logger.name not in seen:
            targeted_loggers.append(logger)
            seen.add(logger.name)

    previous_states: List[Tuple[logging.Logger, int, bool]] = []
    try:
        previous_states.append((root_logger, root_logger.level, root_logger.propagate))
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
        for logger in targeted_loggers:
            previous_states.append((logger, logger.level, getattr(logger, "propagate", True)))
            logger.setLevel(level)
            logger.propagate = True
        yield log_buffer
    finally:
        for logger, prev_level, prev_propagate in previous_states:
            if logger is root_logger:
                logger.removeHandler(handler)
            logger.setLevel(prev_level or logging.NOTSET)
            logger.propagate = prev_propagate


DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_SDK_LOG_LEVEL = "info"
SDK_LOGGING_ENABLED = True


@st.cache_resource(show_spinner=False)
def _build_services() -> Tuple[
    SemanticGuardrailClient,
    PromptSanitizer,
    PromptSanitizer,
]:
    """Instantiate reusable service clients for the trial experience."""

    guardrail_client = SemanticGuardrailClient(
        GuardrailConfig(url=DEFAULT_GUARDRAIL_URL)
    )
    protect_sanitizer = PromptSanitizer(
        SanitizationConfig(
            method="protect",
            fallback_method="redact",
            enable_logging=SDK_LOGGING_ENABLED,
            log_level=DEFAULT_SDK_LOG_LEVEL,
        )
    )
    redact_sanitizer = PromptSanitizer(
        SanitizationConfig(
            method="redact",
            fallback_method="redact",
            enable_logging=SDK_LOGGING_ENABLED,
            log_level=DEFAULT_SDK_LOG_LEVEL,
        )
    )
    return guardrail_client, protect_sanitizer, redact_sanitizer


def _render_guardrail(result: GuardrailResult, step_number: Optional[int] = None) -> None:
    if step_number:
        st.subheader(f"Step {step_number} · Semantic guardrail score")
    else:
        st.subheader("Semantic guardrail score")
    st.markdown(
        "The semantic guardrail scores the prompt and flags policy violations before it reaches your GenAI provider."
    )
    outcome_col, score_col = st.columns(2)
    outcome_col.metric("Outcome", result.outcome.title())
    score_col.metric("Risk score", f"{result.score:.2f}")
    if result.explanation:
        st.write("**Policy signals**")
        st.code(result.explanation)
    with st.expander("Full guardrail response"):
        st.json(result.raw_response)


def _render_discovery(result: SanitizationResult, step_number: Optional[int] = None) -> None:
    if step_number:
        st.subheader(f"Step {step_number} · Discovery insights")
    else:
        st.subheader("Discovery insights")
    st.markdown(
        "Entity discovery highlights the sensitive fields detected in the prompt. These drive the protection and redaction outputs that follow."
    )
    st.json(result.discovery_entities)


def _render_protection(result: SanitizationResult, step_number: Optional[int] = None) -> None:
    if step_number:
        st.subheader(f"Step {step_number} · Protect sensitive data")
    else:
        st.subheader("Protect sensitive data")
    
    # Check if protection failed
    if result.sanitize_error:
        st.markdown(
            "Protection tokenizes the identified values so downstream systems can reverse them later while the prompt remains shielded."
        )
        st.error(f"**Protection Failed:** {result.sanitize_error}")
        st.info(
            "💡 **Tip:** Ensure DEV_EDITION_EMAIL, DEV_EDITION_PASSWORD, and DEV_EDITION_API_KEY environment variables are set correctly. "
            "Protection requires valid credentials to tokenize sensitive data."
        )
    else:
        st.markdown(
            "Protection tokenizes the identified values so downstream systems can reverse them later while the prompt remains shielded."
        )
        preview_text = result.display_prompt or result.sanitized_prompt
        st.code(preview_text, language="text")
        
        st.download_button(
            "Download protected prompt",
            data=result.raw_sanitized_prompt or result.sanitized_prompt,
            file_name="trial_center_protected.txt",
            mime="text/plain",
            key="download_protected",
        )


def _render_unprotect(result: SanitizationResult, step_number: Optional[int] = None) -> None:
    if step_number:
        st.subheader(f"Step {step_number} · Restore protected data")
    else:
        st.subheader("Restore protected data")
    
    st.markdown(
        "When reversible protection succeeds, `find_and_unprotect` can reconstruct the original prompt for authorized reviewers."
    )
    
    # Check if protection failed (so unprotect can't run)
    if result.sanitize_error:
        st.error(
            "**Unprotect Not Available:** Cannot restore data because protection did not succeed in Step 3."
        )
        st.info(
            "💡 **Tip:** Fix the protection credentials and rerun to enable both protection and unprotection."
        )
    elif result.unprotected_prompt:
        st.code(result.unprotected_prompt, language="text")
        st.success("Protected tokens successfully reversed.")
    elif result.unprotect_error:
        st.error(f"**Unprotect Failed:** {result.unprotect_error}")
        if "Protection did not modify the text" in result.unprotect_error:
            st.info("💡 **Tip:** Ensure DEV_EDITION_EMAIL, DEV_EDITION_PASSWORD, and DEV_EDITION_API_KEY environment variables are set correctly.")
    else:
        st.info("Protected payload could not be reversed in this run.")


def _render_redaction(result: SanitizationResult, step_number: Optional[int] = None) -> None:
    if step_number:
        st.subheader(f"Step {step_number} · Redact sensitive data")
    else:
        st.subheader("Redact sensitive data")
    st.markdown(
        "Redaction masks the same entities, producing a shareable prompt that no longer exposes sensitive details."
    )
    st.code(result.display_prompt or result.sanitized_prompt, language="text")
    st.download_button(
        "Download redacted prompt",
        data=result.sanitized_prompt,
        file_name="trial_center_redacted.txt",
        mime="text/plain",
        key="download_redacted",
    )


st.markdown(
    "Submit a prompt and review how Protegrity services evaluate, protect, and redact it before you send it to an LLM."
)

selected_log_level = DEFAULT_LOG_LEVEL
sdk_log_level = DEFAULT_SDK_LOG_LEVEL


# Sample prompts configuration
SAMPLE_PROMPTS = {
    "Approved": "dev_edition_trial_center/samples/sample_approved.txt",
    "Data Leakage": "dev_edition_trial_center/samples/sample_data_leakage.txt",
    "Malicious": "dev_edition_trial_center/samples/sample_malicious.txt",
    "Off-Topic": "dev_edition_trial_center/samples/sample_offtopic.txt",
}

# Initialize prompt in session state if not exists
if "prompt_content" not in st.session_state:
    st.session_state.prompt_content = ""

tab_trial, tab_log = st.tabs(["Trial run", "Run log"])

with tab_trial:
    st.subheader("Try it with your prompt")
    
    # Single instruction with sample buttons below
    st.markdown("**You can either write your own test prompt or load from below sample prompts:**")
    
    # Sample prompt buttons in a compact row - use smaller column widths to keep them closer
    button_cols = st.columns([0.5, 0.5, 0.5, 0.5, 4])  # 4 buttons close together, empty space on right
    for idx, (label, file_path) in enumerate(SAMPLE_PROMPTS.items()):
        with button_cols[idx]:
            if st.button(label, key=f"sample_{label}", use_container_width=True):
                try:
                    sample_file = Path(file_path)
                    if sample_file.exists():
                        st.session_state.prompt_content = sample_file.read_text(encoding="utf-8")
                except Exception as error:  # noqa: BLE001
                    st.error(f"Failed to load sample: {error}")
    
    st.markdown("")  # Small spacing
    
    # Prompt text area - use session state value directly
    prompt_text = st.text_area(
        "Enter your prompt below", 
        value=st.session_state.prompt_content, 
        height=240
    )
    
    # Update session state with any manual changes
    st.session_state.prompt_content = prompt_text
    
    # Pipeline mode selection and run button - make dropdown more compact
    col1, col2, col3 = st.columns([0.75, 1, 3.25])
    with col1:
        pipeline_mode = st.selectbox(
            "Select products execution mode",
            options=[
                "Full Pipeline",
                "Semantic Guardrail",
                "Discover Sensitive Data",
                "Find, Protect & Unprotect",
                "Find & Redact"
            ],
            key="pipeline_mode"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Align button with selectbox
        run_button = st.button("Run trial", type="primary", key="run_trial_button")
    # col3 is intentionally left empty for spacing

    if run_button:
        if not prompt_text.strip():
            st.error("Please provide a prompt to analyze.")
        else:
            guardrail_result: GuardrailResult | None = None
            protect_result: SanitizationResult | None = None
            redact_result: SanitizationResult | None = None
            
            # Determine what to run based on pipeline mode
            run_guardrail = pipeline_mode in ["Full Pipeline", "Semantic Guardrail"]
            run_discovery = pipeline_mode in ["Full Pipeline", "Discover Sensitive Data", "Find, Protect & Unprotect", "Find & Redact"]
            run_protect = pipeline_mode in ["Full Pipeline", "Find, Protect & Unprotect"]
            run_redact = pipeline_mode in ["Full Pipeline", "Find & Redact"]
            
            spinner_msg = {
                "Full Pipeline": "Running semantic guardrail and sanitization...",
                "Semantic Guardrail": "Running semantic guardrail...",
                "Discover Sensitive Data": "Running data discovery...",
                "Find, Protect & Unprotect": "Running protection and unprotect...",
                "Find & Redact": "Running redaction..."
            }.get(pipeline_mode, "Processing...")
            
            with st.spinner(spinner_msg):
                with capture_pipeline_logs(
                    selected_log_level,
                    logger_names=[
                        "dev_edition_trial_center",
                        "protegrity_developer_python",
                    ],
                ):
                    guardrail_client, protect_sanitizer, redact_sanitizer = _build_services()
                    
                    # Run semantic guardrail if needed
                    if run_guardrail:
                        try:
                            guardrail_result = guardrail_client.score_prompt(prompt_text)
                        except RuntimeError as error:
                            st.error(f"Semantic guardrail request failed: {error}")
                    
                    # Run protection if needed
                    if run_protect:
                        try:
                            protect_result = protect_sanitizer.sanitize(prompt_text)
                        except Exception as error:  # noqa: BLE001
                            st.error(f"Protection failed: {error}")
                            protect_result = None
                    
                    # Run redaction if needed
                    if run_redact:
                        try:
                            redact_result = redact_sanitizer.sanitize(prompt_text)
                        except Exception as error:  # noqa: BLE001
                            st.error(f"Redaction failed: {error}")
                            redact_result = None
                    
                    # For discovery-only mode, run protect to get discovery results
                    if run_discovery and not run_protect and not run_redact:
                        try:
                            protect_result = protect_sanitizer.sanitize(prompt_text)
                        except Exception as error:  # noqa: BLE001
                            st.error(f"Discovery failed: {error}")
                            protect_result = None

            # Render results based on what was run
            # Determine step numbering based on pipeline mode
            step_counter = 1
            
            if guardrail_result:
                _render_guardrail(guardrail_result, step_counter if pipeline_mode == "Full Pipeline" else None)
                step_counter += 1
            
            # Show discovery results if available and requested
            if run_discovery or pipeline_mode == "Discover Sensitive Data":
                discovery_source = protect_result or redact_result
                if discovery_source:
                    step_num = step_counter if pipeline_mode in ["Full Pipeline", "Find, Protect & Unprotect", "Discover Sensitive Data"] else None
                    _render_discovery(discovery_source, step_num)
                    if step_num:
                        step_counter += 1
            
            # Show protection results if requested
            if run_protect and protect_result:
                step_num = step_counter if pipeline_mode in ["Full Pipeline", "Find, Protect & Unprotect"] else None
                _render_protection(protect_result, step_num)
                if step_num:
                    step_counter += 1
                # Always show unprotect when protection runs (for both Full Pipeline and Protect & Unprotect modes)
                step_num = step_counter if pipeline_mode in ["Full Pipeline", "Find, Protect & Unprotect"] else None
                _render_unprotect(protect_result, step_num)
                if step_num:
                    step_counter += 1
            
            # Show redaction results if requested
            if run_redact and redact_result:
                if protect_result and run_protect:
                    st.divider()
                step_num = step_counter if pipeline_mode in ["Full Pipeline", "Find & Redact"] else None
                _render_redaction(redact_result, step_num)

with tab_log:
    st.subheader("Pipeline diagnostics")
    logs = st.session_state.get("run_logs", [])
    if logs:
        st.code("\n".join(logs), language="text")
    else:
        st.info("Run the trial to collect background execution details.")
    st.caption("Logs reset on each run.")
