"""Single import point for every mapped model.

SQLAlchemy resolves foreign keys against whatever is registered on `Base.metadata` at
mapper-configuration time. A process that imports only some model modules gets
`NoReferencedTableError` on the first query touching a cross-module FK — and unit tests
can easily miss it, because test fixtures tend to import everything anyway.

Every entrypoint (API, workers, migrations) imports this module, so metadata
completeness is a property of the codebase rather than of import order luck.
"""

from taxos_core.agents import models as agent_models
from taxos_core.audit import models as audit_models
from taxos_core.compliance import models as compliance_models
from taxos_core.ingestion import models as ingestion_models
from taxos_core.masterdata import models as masterdata_models
from taxos_core.shared.events import models as event_models
from taxos_core.shared.persistence.base import Base
from taxos_core.workflow import models as workflow_models

__all__ = [
    "Base",
    "agent_models",
    "audit_models",
    "compliance_models",
    "event_models",
    "ingestion_models",
    "masterdata_models",
    "workflow_models",
]
