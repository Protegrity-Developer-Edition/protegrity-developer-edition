"""CLI entry point for the Dev Edition Trial Center."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from trial_center.core.pipeline import (
    GuardianPromptForge,
    GuardrailConfig,
    SanitizationConfig,
    forge_from_file,
)

# Load environment variables
load_dotenv()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Dev Edition Trial Center pipeline.")
    parser.add_argument("prompt", help="Path to file containing the prompt text.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where sanitized prompt and report will be stored.",
    )
    parser.add_argument(
        "--method",
        choices=["protect", "redact"],
        default="protect",
        help="Preferred sanitization method. Fallback to redact if protect fails.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Guardrail rejection threshold (0..1).",
    )
    parser.add_argument(
        "--metadata",
        help="Optional JSON string with prompt metadata (e.g. business unit).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def build_forge(args: argparse.Namespace) -> GuardianPromptForge:
    guardrail_config = GuardrailConfig(rejection_threshold=args.threshold)
    sanitization_config = SanitizationConfig(method=args.method)
    return GuardianPromptForge(
        guardrail_config=guardrail_config,
        sanitization_config=sanitization_config,
    )


def parse_metadata(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Failed to parse metadata JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise SystemExit("Metadata must be a JSON object.")
    return parsed


def main() -> None:
    args = parse_args()
    _configure_logging(args.verbose)

    prompt_path = Path(args.prompt)
    output_dir = Path(args.output_dir)

    metadata = parse_metadata(args.metadata)
    forge = build_forge(args)

    report = forge_from_file(
        prompt_path=prompt_path,
        output_dir=output_dir,
    metadata=metadata,
    forge=forge,
    )

    logging.info("Sanitized prompt stored at: %s", (output_dir / f"{prompt_path.stem}_sanitized.txt"))
    logging.info("Report stored at: %s", (output_dir / f"{prompt_path.stem}_report.json"))
    logging.debug("Report payload:\n%s", report.to_json())


if __name__ == "__main__":
    main()
