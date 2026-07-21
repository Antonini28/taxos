"""Persistence: the single mutation path (Phase 6 doc 03).

`session.commit()` is called in exactly one place — `AuditedUnitOfWork.commit()`.
Anywhere else is a lint failure and a review reject.

Import from the submodules directly (`...persistence.uow`, `...persistence.session`):
this package deliberately re-exports nothing, so model modules can depend on `base`
without pulling the UoW — and the import graph stays acyclic.
"""
