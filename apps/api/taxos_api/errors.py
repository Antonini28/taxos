"""Typed error taxonomy (Phase 6 doc 02 §4).

Domain code raises these; only the boundary translates them to problem+json. Services
never import HTTP concepts, handlers never contain logic.
"""


class DomainError(Exception):
    status = 500
    type_suffix = "internal"
    title = "Internal error"


class NotFoundError(DomainError):
    status = 404
    type_suffix = "not-found"
    title = "Resource not found"


class ValidationFailed(DomainError):
    status = 422
    type_suffix = "validation"
    title = "Validation failed"


class ConflictError(DomainError):
    status = 409
    type_suffix = "conflict"
    title = "Conflict"


class DuplicateContentError(ConflictError):
    type_suffix = "duplicate-content"
    title = "Duplicate content"


class PermissionDeniedError(DomainError):
    status = 403
    type_suffix = "forbidden"
    title = "Permission denied"
