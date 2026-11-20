"""Local metadata checks for user-selected authentication log files."""

from pathlib import Path


MAX_LOG_FILE_SIZE_BYTES = 20 * 1024 * 1024
SUPPORTED_LOG_EXTENSIONS = frozenset({".log", ".txt"})


class LogFileValidationError(ValueError):
    """A selected local file cannot be handed to the import workflow."""


def validate_log_file(path: str | Path) -> Path:
    """Check only local file type and size; do not open or parse its contents."""
    candidate = Path(path).expanduser()
    if candidate.suffix.lower() not in SUPPORTED_LOG_EXTENSIONS:
        raise LogFileValidationError("Choose a log file with a .log or .txt extension.")

    try:
        if not candidate.is_file():
            raise LogFileValidationError("The selected path is not a regular file.")
        file_size = candidate.stat().st_size
    except OSError as error:
        raise LogFileValidationError(f"Could not access the selected file: {error}") from error

    if file_size > MAX_LOG_FILE_SIZE_BYTES:
        raise LogFileValidationError("The selected file is larger than the 20 MB limit.")
    return candidate.resolve()
