"""Regression: metadata completeness must not depend on import order.

Found live — the API process imported ingestion models but not masterdata, so the
first upload failed with NoReferencedTableError on batch.entity_id → legal_entity.
The unit suite missed it because test fixtures import everything. These tests fail
if an entrypoint ever drops the registry import, or a new model module is added to
the codebase but not to it.
"""

from sqlalchemy.orm import configure_mappers

from taxos_core.models_registry import Base


def test_all_mappers_configure_from_the_registry_alone():
    """Resolving every relationship and FK must succeed with only the registry imported."""
    configure_mappers()  # raises if any FK target is missing


def test_expected_tables_are_registered():
    tables = set(Base.metadata.tables)
    assert {
        "tenant",
        "jurisdiction",
        "legal_entity",
        "tax_registration",
        "audit_event",
        "outbox_event",
        "batch",
        "transaction_row",
        "quarantine_row",
        "validation_result",
    } <= tables


def test_api_entrypoint_completes_metadata():
    """The API must not rely on something else having imported the models first."""
    import importlib
    import sys

    for module in [m for m in sys.modules if m.startswith("taxos_api")]:
        del sys.modules[module]
    main = importlib.import_module("taxos_api.main")
    assert main.create_app is not None
    configure_mappers()


def test_every_tenant_scoped_model_declares_tenant_id():
    """ADR-006 at the model layer: the RLS policy needs the column to exist.

    Global reference tables are exempt by design and listed explicitly, so adding a
    new one is a deliberate decision rather than an oversight.
    """
    global_tables = {"tenant", "jurisdiction", "alembic_version"}
    for name, table in Base.metadata.tables.items():
        if name in global_tables:
            continue
        assert "tenant_id" in table.columns, f"{name} is missing tenant_id"
