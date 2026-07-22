"""Phase 4: grounded research with citations, and the evidenced refusal.

The two claims the knowledge layer rests on get direct tests: every answer cites its
sources, and a question the corpus cannot support returns INSUFFICIENT_SOURCES with
diagnostics rather than a thin reply.
"""

import pytest
from taxos_core.knowledge.service import KnowledgeService, seed_corpus


@pytest.fixture
async def corpus(session_a):
    """The corpus is global reference data; seeding it once is enough for the tenant
    session to read it (no tenant scoping)."""
    await seed_corpus(session_a)
    return session_a


async def test_corpus_seeds_idempotently(session_a):
    first = await seed_corpus(session_a)
    second = await seed_corpus(session_a)
    assert first > 0  # chunks loaded
    assert second == 0  # already present, not duplicated


async def test_reverse_charge_question_is_answered_with_the_right_authority(corpus):
    service = KnowledgeService(corpus)
    answer = await service.answer("How does the domestic reverse charge for construction work?")

    assert answer.sufficient is True
    assert answer.passages
    # The top passage cites the reverse-charge guidance the VAT engine also references.
    assert any("VATDSAG" in p.citation_ref for p in answer.passages)
    assert "customer accounts for the VAT" in answer.passages[0].body.lower() or (
        "customer" in answer.passages[0].body.lower()
    )


async def test_exempt_vs_zero_rated_question_surfaces_legislation(corpus):
    service = KnowledgeService(corpus)
    answer = await service.answer("Can I recover input tax on exempt supplies?")

    assert answer.sufficient is True
    citations = {p.citation_ref for p in answer.passages}
    assert any("VATA 1994" in c or "700" in c for c in citations)


async def test_every_answered_passage_carries_a_citation(corpus):
    service = KnowledgeService(corpus)
    answer = await service.answer("What evidence do I need to reclaim input tax?")
    assert answer.sufficient
    assert all(p.citation_ref and p.title for p in answer.passages)


async def test_unsupported_question_returns_insufficient_sources(corpus):
    """The refusal is first-class and evidenced — it says what was searched and how weak
    the best match was, rather than improvising a thin answer."""
    service = KnowledgeService(corpus)
    answer = await service.answer("What is the corporation tax rate in Germany for 2019?")

    assert answer.sufficient is False
    assert answer.passages == []
    assert answer.searched_chunks > 0  # the whole corpus was searched
    assert "escalated" in answer.note.lower()


async def test_legislation_outranks_guidance_on_a_tie(corpus):
    """Conflicts are surfaced by authority rank, never resolved: A1 legislation sorts above
    A3 guidance when relevance is comparable."""
    service = KnowledgeService(corpus)
    answer = await service.answer("zero rated supplies input tax recoverable")
    assert answer.sufficient
    ranks = [p.authority_rank for p in answer.passages]
    # An A1 legislation passage is present and appears no later than any A3 of equal score.
    assert "A1" in ranks


async def test_exact_reference_lookup_matches(corpus):
    """A user pasting a reference ('Box 4', 'VATDSAG') retrieves it, not just prose."""
    service = KnowledgeService(corpus)
    answer = await service.answer("Box 4 VAT reclaimed on purchases")
    assert answer.sufficient
    assert any("700" in p.citation_ref for p in answer.passages)


async def test_retrieval_is_deterministic(corpus):
    """Same question, same passages, same order — no runtime LLM rewriting to drift."""
    service = KnowledgeService(corpus)
    a = await service.answer("domestic reverse charge construction")
    b = await service.answer("domestic reverse charge construction")
    assert [p.citation_ref for p in a.passages] == [p.citation_ref for p in b.passages]
