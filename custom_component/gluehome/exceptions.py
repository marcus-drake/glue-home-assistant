
class GlueHomeException(Exception):
    """Base class for exceptions."""


class GlueHomeNetworkError(GlueHomeException):
    """Represents network error."""


class GlueHomeServerError(GlueHomeException):
    """Represents GlueHome server error."""


class GlueHomeInvalidAuth(GlueHomeException):
    """Represents invalid authentication."""

