# Dev Edition Trial Center

An interactive Streamlit application demonstrating how to integrate Protegrity Developer Edition services for privacy-aware GenAI workflows. The Trial Center provides a hands-on environment to explore semantic guardrails, data discovery, protection, and redaction capabilities through an easy-to-use web interface.

## Features

- **Interactive UI** – Web-based interface with sample prompts and multiple execution modes
- **Semantic Guardrail** – Validates prompts for topic relevance and risk detection
- **Data Discovery** – Identifies and classifies sensitive data (PII, credentials, etc.)
- **Reversible Protection** – Tokenizes sensitive data with ability to restore original values
- **Irreversible Redaction** – Permanently masks sensitive information
- **Pipeline Flexibility** – Five execution modes to test different combinations of services
- **Comprehensive Logging** – Built-in run log to observe service interactions
- **Developer-Friendly** – Includes CLI, Python package, unit tests, and automated launcher

## Prerequisites

Before running the Trial Center, ensure you have:

- **Docker Desktop** – macOS, Linux, or Windows with Docker Desktop (or equivalent Docker engine) installed and running. At least 4 GB RAM available for containers.
- **Python 3.11+** – The repository includes a virtual environment at `.venv/` with all dependencies.
- **Protegrity credentials (optional)** – Set `DEV_EDITION_EMAIL`, `DEV_EDITION_PASSWORD`, and `DEV_EDITION_API_KEY` environment variables to enable reversible protection. Without credentials, protection operations will display error messages, but semantic guardrail, discovery, and redaction features remain fully functional.


## Quick Start

### Option 1: Using the Launch Script (Recommended)

The easiest way to run the Trial Center is using the automated launch script:

```bash
cd dev_edition_trial_center
./launch_trial_center.sh
```

The launch script automatically handles everything:
- ✅ Validates Docker installation and running status
- ✅ Checks Python virtual environment
- ✅ Starts Developer Edition services (`docker compose up -d`)
- ✅ Performs health checks on all services (Semantic Guardrail, Data Discovery)
- ✅ Detects and displays credential configuration status
- ✅ Sets up the output directory
- ✅ Launches the Streamlit UI at `http://localhost:8501`

**Note:** If credentials are missing, the script will warn you but still launch. Protection operations will show error messages; discovery and redaction will work normally.

### Option 2: Manual Setup

If you prefer to run each step manually or troubleshoot issues:

1. Ensure the Developer Edition services are running (from repository root):
   ```bash
   docker compose up -d
   ```
2. Activate the project virtual environment:
   ```bash
   source .venv/bin/activate
   ```
3. Install optional UI dependencies:
   ```bash
   pip install streamlit
   ```
4. Run the CLI with the provided test prompt:
   ```bash
   python -m dev_edition_trial_center.run_trial_center \
       dev_edition_trial_center/samples/input_test.txt \
       --output-dir dev_edition_trial_center/output
   ```
   - If protection credentials are unavailable, the pipeline will report clear errors.
   - Use `--method redact` to force redaction.
5. Launch the Streamlit UI:
   ```bash
   streamlit run dev_edition_trial_center/app.py
   ```
   Point your browser to the provided local URL (typically `http://localhost:8501`).

6. (Optional) Run the lightweight unit tests:
   ```bash
   python -m pytest dev_edition_trial_center/tests
   ```

## Using the Trial Center UI

### Sample Prompts

The UI includes four pre-loaded sample prompts demonstrating different guardrail scenarios:
- **Approved** – Customer support query that passes semantic guardrail validation
- **Data Leakage** – Prompt containing extensive PII that should be detected and protected
- **Malicious** – Prompt attempting harmful or inappropriate requests
- **Off-Topic** – Prompt outside the customer-support domain

Click any sample button to load the prompt into the text area.

### Execution Modes

Choose from five execution modes to explore different product combinations:

1. **Full Pipeline** – Complete workflow with all steps:
   - Step 1: Semantic Guardrail
   - Step 2: Discovery
   - Step 3: Protection
   - Step 4: Unprotection
   - Step 5: Redaction

2. **Semantic Guardrail** – Guardrail scoring only

3. **Discover Sensitive Data** – Entity discovery only (Step 1)

4. **Find, Protect & Unprotect** – Three-step workflow:
   - Step 1: Discovery
   - Step 2: Protection
   - Step 3: Unprotection

5. **Find & Redact** – Two-step workflow:
   - Step 1: Discovery
   - Step 2: Redaction

Each mode displays only the relevant steps with appropriate numbering.

### Run Log

Switch to the **Run log** tab to observe the guardrail and sanitization calls executed behind the scenes. INFO-level logs and SDK traces are captured automatically, showing:
- Service endpoints being called
- Entity detection details
- Protection/redaction operations
- Any warnings or errors

## Blueprint internals

1. **Semantic Guardrail** – Scores the prompt for topic relevance and risk. Trained on customer-support vertical using open-source datasets. Displays outcome with score and explanation.
2. **Data Discovery** – Enumerates detected entities (PII, sensitive data types) for audit trails.
3. **Protection** – Runs reversible tokenization with `find_and_protect`. **Requires credentials** to function. If protection fails (no credentials or authentication errors):
   - Displays clear error message
   - Shows credential setup instructions
   - Does NOT display sensitive data
4. **Unprotect** – Verifies reversibility with `find_and_unprotect`, confirming that authorized services can reconstruct the original prompt. Only runs if protection succeeded.
5. **Redaction** – Provides irreversible masking with `find_and_redact`. Always available, works without credentials.
6. **Error Handling** – Transparent approach:
   - No automatic fallbacks that mask failures
   - Clear error messages with actionable guidance
   - Security-first: never displays sensitive data when protection fails
   - Detects silent failures (when SDK completes but doesn't modify data)

## Generated artifacts

CLI generates:
- `dev_edition_trial_center/output/input_test_sanitized.txt`
- `dev_edition_trial_center/output/input_test_report.json`

UI provides download buttons for:
- Protected prompts (when protection succeeds)
- Redacted prompts

## Extending the prototype

- Add multi-turn conversations by supplying a JSON conversation to
   `metadata` or by extending `trial_center_pipeline.py`.
- Create additional sample prompts by adding files to `dev_edition_trial_center/samples/` and updating the `SAMPLE_PROMPTS` dictionary in `app.py`.
- Customize the UI theme by modifying the CSS in the Streamlit markdown section.
- Add new execution modes by extending the pipeline mode logic in `app.py`.
- Build policy templates per business unit by storing configuration presets in
   `dev_edition_trial_center/configs/`.

## Validation checklist

- ✅ Runs entirely on Developer Edition modules.
- ✅ Demonstrates creative integration with GenAI safety workflows.
- ✅ Ships in a reusable form factor (package + CLI + samples + launcher).
- ✅ Comprehensive launch script with prerequisite validation and health checks.
- ✅ Interactive UI with sample prompts and multiple execution modes.
- ✅ Transparent error handling with security-first approach.
- ✅ Dynamic step numbering adapts to selected execution mode.
- ✅ Ready for iterative prototyping with modular architecture.
