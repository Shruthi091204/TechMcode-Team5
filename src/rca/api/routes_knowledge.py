from fastapi import APIRouter
from pydantic import BaseModel, Field

from rca.knowledge.retrieval import retrieve_runbooks, retrieve_similar_incidents

router = APIRouter()


class KnowledgeQuery(BaseModel):
    query: str = Field(min_length=1)
    k: int = 3


class KnowledgeMatch(BaseModel):
    id: str
    title: str
    snippet: str
    score: float


class KnowledgeResult(BaseModel):
    runbooks: list[KnowledgeMatch]
    similar_incidents: list[KnowledgeMatch]


@router.post("/knowledge/retrieve", response_model=KnowledgeResult)
def retrieve_knowledge(request: KnowledgeQuery) -> KnowledgeResult:
    runbooks = retrieve_runbooks(request.query, k=request.k)
    incidents = retrieve_similar_incidents(request.query, k=2)
    return KnowledgeResult(
        runbooks=[KnowledgeMatch(**match) for match in runbooks],
        similar_incidents=[KnowledgeMatch(**match) for match in incidents],
    )
