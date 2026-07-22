"""Knowledge corpus models — global reference data, not tenant-scoped.

A chunk is the unit of citation (Phase 4 doc 02): it maps 1:1 to a citable passage, so a
citation points at something that actually exists rather than an approximate location. The
full-text search vector is a Postgres generated column (see migration) — the index is a
property of the data, not something application code must remember to maintain.
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from taxos_core.shared.persistence.base import Base, new_id


class KnowledgeDoc(Base):
    """A source document: an HMRC notice, a manual page, a piece of legislation."""

    __tablename__ = "knowledge_doc"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    # Authority rank drives conflict presentation, never suppression (docs/knowledge/01 §1):
    # A1 legislation > A3 HMRC guidance. The Research layer shows conflicts ranked, and
    # never resolves them.
    authority_rank: Mapped[str] = mapped_column(String(4), nullable=False)  # A1, A2, A3…
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "hmrc_notice", "legislation"
    citation_ref: Mapped[str] = mapped_column(String(50), nullable=False)  # "VAT Notice 700 §10.3"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False, default="UK")
    tax_domain: Mapped[str] = mapped_column(String(20), nullable=False, default="VAT")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Temporal validity (docs/knowledge/01 §2): tax answers are always "as of when".
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class KnowledgeChunk(Base):
    """One citable passage. `search_vector` is a generated tsvector (migration) with a GIN
    index — retrieval is FTS over this column plus metadata filters."""

    __tablename__ = "knowledge_chunk"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=new_id)
    doc_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("knowledge_doc.id"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(nullable=False, default=0)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
