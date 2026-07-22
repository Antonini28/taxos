"""Knowledge research endpoints (Phase 4, FR-402/403).

The corpus is global, so these reads are not tenant-scoped. Every answer cites its sources;
an unsupported question returns a structured INSUFFICIENT_SOURCES verdict with the coverage
diagnostics behind it, never a thin improvised reply.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.knowledge.service import KnowledgeService

from taxos_api.deps import Principal, current_principal, db_session

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class PassageOut(BaseModel):
    citation_ref: str
    title: str
    authority_rank: str
    heading: str
    body: str
    url: str | None
    score: float


class AnswerOut(BaseModel):
    question: str
    sufficient: bool
    passages: list[PassageOut]
    searched_chunks: int
    best_score: float
    note: str


@router.get("/answer", response_model=AnswerOut)
async def answer(
    principal: PrincipalDep,
    session: SessionDep,
    q: str = Query(min_length=3, description="A natural-language tax question"),
) -> AnswerOut:
    result = await KnowledgeService(session).answer(q)
    return AnswerOut(
        question=result.question,
        sufficient=result.sufficient,
        passages=[
            PassageOut(
                citation_ref=p.citation_ref,
                title=p.title,
                authority_rank=p.authority_rank,
                heading=p.heading,
                body=p.body,
                url=p.url,
                score=round(p.score, 4),
            )
            for p in result.passages
        ],
        searched_chunks=result.searched_chunks,
        best_score=round(result.best_score, 4),
        note=result.note,
    )
