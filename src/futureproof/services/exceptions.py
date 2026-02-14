"""Service layer exceptions.

Centralized exception hierarchy for the service layer.
Extracted from career_service.py for SRP compliance.
"""


class ServiceError(Exception):
    """Base exception for service errors."""

    pass


class NoDataError(ServiceError):
    """Raised when no career data is available."""

    pass


class AnalysisError(ServiceError):
    """Raised when analysis fails."""

    pass
