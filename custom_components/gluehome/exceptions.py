
class GlueHomeException(Exception):
    """Base class for exceptions."""


class GlueHomeNetworkError(GlueHomeException):
    """Represents network error."""


class GlueHomeServerError(GlueHomeException):
    """Represents GlueHome server error."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class GlueHomeInvalidAuth(GlueHomeException):
    """Represents invalid authentication."""


class GlueHomeNonSuccessfulResponse(GlueHomeException):
    """Represents GlueHome server error."""
