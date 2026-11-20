"""Application-specific exceptions."""


class ValidationError(ValueError):
    """Raised when an API argument does not satisfy its contract."""

