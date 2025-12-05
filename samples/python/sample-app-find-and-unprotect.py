import json
import logging
from pathlib import Path
import protegrity_developer_python as protegrity  # Ensure this module is installed


def configure_logger() -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger("sample_app_find_and_unprotect")
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
        named_entity_map=config.get("named_entity_map"),
        classification_score_threshold=config.get(
            "classification_score_threshold", 0.6
        ),
        enable_logging=config.get("enable_logging", True),
        log_level=config.get("log_level", "info"),
    )


def unprotect_file(input_path: Path, output_path: Path, logger: logging.Logger) -> None:
    """Read input file, unprotect sensitive data, and write to output file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Reading from file %s...", input_path)
        with (
            input_path.open("r", encoding="utf-8") as infile,
            output_path.open("w", encoding="utf-8") as outfile,
        ):
            for line in infile:
                stripped_line = line.rstrip()
                if stripped_line:  # Only process non-empty lines
                    unprotected_line = protegrity.find_and_unprotect(stripped_line) + "\n"
                    outfile.write(unprotected_line)
                else:
                    outfile.write(line)
        logger.info("Processed text written to: %s", output_path)
    except FileNotFoundError as error:
        logger.error("File not found: %s", error)
        raise RuntimeError(f"File not found: {error}") from error
    except Exception as error:
        logger.error("Unprotection failed: %s", error)
        raise RuntimeError(f"Unprotection failed: {error}") from error


def log_output_snippet(
    output_path: Path, logger: logging.Logger, snippet_length: int = 250
) -> None:
    """Log a snippet of the unprotected output file."""
    try:
        with output_path.open("r", encoding="utf-8") as file:
            text = file.read()
            logger.info(
                'Processed text snippet: "%s..."',
                text[:snippet_length],
            )
    except Exception as error:
        logger.error("Failed to read snippet from output file: %s", error)
        raise RuntimeError(
            f"Failed to read snippet from output file: {error}"
        ) from error


def main() -> None:
    """Main function to execute the protection process."""
    logger = configure_logger()

    base_dir = Path(__file__).resolve().parent.parent
    input_file = base_dir / "sample-data" / "output-protect.txt"
    output_file = base_dir / "sample-data" / "output-unprotect.txt"
    config_file = base_dir / "config.json"

    config = load_config(config_file)
    if config:
        configure_protegrity(config)

    unprotect_file(input_file, output_file, logger)
    log_output_snippet(output_file, logger)


if __name__ == "__main__":
    main()
