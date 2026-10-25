"""User-safe errors raised by the domain layer."""

class UserOperationError(RuntimeError):
    """An operation was rejected without changing persisted data."""
