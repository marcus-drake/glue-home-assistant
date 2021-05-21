
class GlueHomeException(Exception):
    """Base class for exceptions."""


class GlueHomeNetworkError(GlueHomeException):
    """Represents network error."""


class GlueHomeServerError(GlueHomeException):
    """Represents GlueHome server error."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:
        return f"Server returned error status {self.status_code} with body: {self.body}"


class GlueHomeInvalidAuth(GlueHomeException):
    """Represents invalid authentication."""


class GlueHomeNonSuccessfulResponse(GlueHomeException):
    """Represents GlueHome server error."""

class GlueHomeLockOperationFailed(GlueHomeException):
    """Represents GlueHome server error."""

    def __init__(self, lock_description: str, operation: str, reason):
        self.lock_description = lock_description
        self.operation = operation
        self.reason = reason

    def __str__(self) -> str:
        return f"Failed to perform operation '{self.operation}' on lock '{self.lock_description}', reason: {self.reason}"
