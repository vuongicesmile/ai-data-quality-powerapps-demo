"""Safe error vocabulary shared by all platform entrypoints."""


class PlatformError(Exception):
    status_code = 500


class ConfigurationError(PlatformError):
    status_code = 422


class AuthenticationError(PlatformError):
    status_code = 401


class PermissionDeniedError(PlatformError):
    status_code = 403


class ResourceNotFoundError(PlatformError):
    status_code = 404


class ConflictError(PlatformError):
    status_code = 409


class BudgetExceededError(PlatformError):
    status_code = 413


class ThrottledError(PlatformError):
    status_code = 429


class UpstreamUnavailableError(PlatformError):
    status_code = 503
