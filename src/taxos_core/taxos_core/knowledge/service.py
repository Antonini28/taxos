"""Retrieval and grounded research (FR-402/403).

Retrieval is Postgres full-text with a relevance score. The research answer is composed of
retrieved passages, each carrying its citation — in deterministic mode there is no LLM
synthesis, so the "answer" is the grounded evidence itself, which is the honest and
reproducible form. When the best match is too weak, the verdict is INSUFFICIENT_SOURCES
with coverage diagnostics: what was searched and how weak the best hit was, so "no answer"
is itself evidenced (docs/knowledge/03 §3).
"""

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.knowledge.corpus import CORPUS, DEFAULT_VALID_FROM
from taxos_core.knowledge.models import KnowledgeChunk, KnowledgeDoc

# A hit below this rank is treated as no real support: better to refuse than to dress a
# weak match as an answer. With OR retrieval, an out-of-scope question that happens to share
# a common word ("tax", "rate") scores well below this floor, while a genuinely on-topic
# question clears it comfortably — measured against the demo corpus, in-scope questions score
# 0.36–0.55 and the out-of-scope German-corporation-tax question scores 0.19, so 0.30
# separates them with margin. A larger corpus re-tunes this against its own eval set.
MIN_RELEVANCE = 0.30

# Words too common or too short to carry meaning in a query. Kept small — the OR query plus
# the relevance floor do most of the work; this just trims obvious noise.
_STOPWORDS = frozenset(
    "the a an of to for in on and or is are do i my you what how can does need with".split()
)


def _or_tsquery(question: str) -> str:
    """Build an OR tsquery from a natural question.

    Question-answering retrieval is recall-first: a passage rarely contains every word of
    the question (the user asks to 'reclaim'; the guidance says 'recover'), so ANDing the
    terms — what websearch_to_tsquery does — misses real answers. ORing the content words
    and ranking by ts_rank surfaces the passage that matches the most, which is the one a
    reader wants.
    """
    words = [w for w in re.findall(r"[a-z0-9]+", question.lower()) if len(w) > 2]
    terms = [w for w in words if w not in _STOPWORDS]
    return " | ".join(terms) if terms else ""


@dataclass
class Passage:
    citation_ref: str
    title: str
    authority_rank: str
    heading: str
    body: str
    url: str | None
    score: float


@dataclass
class ResearchAnswer:
    question: str
    sufficient: bool
    passages: list[Passage] = field(default_factory=list)
    # Coverage diagnostics — the evidence behind an INSUFFICIENT_SOURCES verdict.
    searched_chunks: int = 0
    best_score: float = 0.0
    note: str = ""


class KnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def search(self, query: str, *, limit: int = 5) -> list[Passage]:
        """Full-text search over the corpus, ranked by relevance.

        The query is turned into an OR of its content words (see `_or_tsquery`) so a natural
        question matches on any term and ranks by how many. Exact references ("VATDSAG",
        "Box 4") match here as well as prose.
        """
        or_query = _or_tsquery(query)
        if not or_query:
            return []
        # search_vector is a generated column not mapped on the model; reference it as a
        # literal column on the real table so the ORM join stays a single query (no
        # aliasing, no accidental cartesian product).
        tsquery = func.to_tsquery("english", or_query)
        search_vector = literal_column("knowledge_chunk.search_vector")
        score = func.ts_rank(search_vector, tsquery).label("score")
        stmt = (
            select(
                KnowledgeChunk.heading,
                KnowledgeChunk.body,
                KnowledgeDoc.citation_ref,
                KnowledgeDoc.title,
                KnowledgeDoc.authority_rank,
                KnowledgeDoc.url,
                score,
            )
            .join(KnowledgeDoc, KnowledgeDoc.id == KnowledgeChunk.doc_id)
            .where(search_vector.op("@@")(tsquery))
            .order_by(score.desc())
            .limit(limit)
        )
        rows = (await self._s.execute(stmt)).all()
        return [
            Passage(
                citation_ref=r.citation_ref,
                title=r.title,
                authority_rank=r.authority_rank,
                heading=r.heading,
                body=r.body,
                url=r.url,
                score=float(r.score),
            )
            for r in rows
        ]

    async def answer(self, question: str) -> ResearchAnswer:
        """Grounded answer, or an evidenced refusal.

        Passages are ordered by relevance then authority (legislation above guidance) —
        conflicts are surfaced by rank, never resolved (docs/knowledge/03 §2)."""
        total = (
            await self._s.execute(select(func.count()).select_from(KnowledgeChunk))
        ).scalar_one()
        passages = await self.search(question, limit=5)
        best = passages[0].score if passages else 0.0

        if not passages or best < MIN_RELEVANCE:
            return ResearchAnswer(
                question=question,
                sufficient=False,
                searched_chunks=int(total),
                best_score=best,
                note=(
                    "No corpus passage supports an answer to this question. The knowledge "
                    "base was searched in full; the strongest match scored below the support "
                    "threshold. Rather than improvise, this is escalated for a human to "
                    "answer or to extend the corpus."
                ),
            )

        rank_order = {"A1": 0, "A2": 1, "A3": 2, "A4": 3}
        passages.sort(key=lambda p: (-p.score, rank_order.get(p.authority_rank, 9)))
        return ResearchAnswer(
            question=question,
            sufficient=True,
            passages=passages,
            searched_chunks=int(total),
            best_score=best,
        )


async def seed_corpus(session: AsyncSession) -> int:
    """Load the demo corpus idempotently. Global reference data, like jurisdictions —
    written once, read by every tenant, never tenant-scoped."""
    existing = (await session.execute(select(func.count()).select_from(KnowledgeDoc))).scalar_one()
    if existing:
        return 0

    chunk_count = 0
    for rank, source, ref, title, tax_domain, url, chunks in CORPUS:
        doc = KnowledgeDoc(
            authority_rank=rank,
            source=source,
            citation_ref=ref,
            title=title,
            jurisdiction="UK",
            tax_domain=tax_domain,
            url=url,
            valid_from=DEFAULT_VALID_FROM,
        )
        session.add(doc)
        await session.flush()
        for ordinal, (heading, body) in enumerate(chunks):
            session.add(
                KnowledgeChunk(
                    id=uuid.uuid4(),
                    doc_id=doc.id,
                    ordinal=ordinal,
                    heading=heading,
                    body=body,
                )
            )
            chunk_count += 1
    await session.commit()
    return chunk_count
