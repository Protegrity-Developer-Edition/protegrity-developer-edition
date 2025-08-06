import json
import logging
from pathlib import Path
import protegrity_developer_python as protegrity  # Ensure this module is available


def configure_logger() -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger("sample_app_find")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def load_config(config_path: Path) -> dict:
    """Load configuration from a JSON file if it exists."""
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def configure_protegrity(config: dict) -> None:
    """Configure the protegrity module using the provided configuration."""
    protegrity.configure(
        endpoint_url=config.get("endpoint_url"),
        classification_score_threshold=config.get(
            "classification_score_threshold", 0.6
        ),
    )


def read_input_file(input_path: Path, logger: logging.Logger) -> str:
    """Read and return the content of the input file."""
    try:
        logger.info("Reading from file %s...", input_path)
        with input_path.open("r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError as error:
        logger.error("Input file not found: %s", input_path)
        raise RuntimeError(f"Input file not found: {input_path}") from error


def discover_pii(text: str) -> str:
    """Discover PII in the input text and return formatted JSON output."""
    try:
        output = protegrity.discover(text)
        return json.dumps(output, indent=4)
    except Exception as error:
        raise RuntimeError(f"PII discovery failed: {error}") from error


def main() -> None:
    """Main function to execute the PII discovery process."""
    logger = configure_logger()

    base_dir = Path(__file__).resolve().parent
    input_file = base_dir / "sample-data" / "sample-find-redact.txt"
    config_file = base_dir / "config.json"

    config = load_config(config_file)
    if config:
        configure_protegrity(config)

    input_text = read_input_file(input_file, logger)
    pii_output = discover_pii(input_text)

    logger.info("Found the below PII data...\n%s", pii_output)


if __name__ == "__main__":
    main()
