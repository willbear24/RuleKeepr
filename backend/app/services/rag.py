from dataclasses import dataclass

from backend.app.schemas.chunk import SourceChunk
from backend.app.services.llm_client import chat
from backend.app.services.vector_store import retrieve
from backend.app.utils.exceptions import ServiceUnavailableException

# Chunks scoring below this were off-topic in retrieval spot checks.
MIN_SCORE = 0.3
N_RESULTS = 5

NOT_COVERED = "I couldn't find anything in the rulebook that answers that."

SYSTEM_PROMPT = (
    "You are a board game rules assistant. Answer the player's question using ONLY the rulebook excerpts provided. "
    "If the excerpts don't contain the answer, reply "
    f'exactly: "{NOT_COVERED}" Do not use outside knowledge or guess. '
    "Be concise and, when helpful, mention the section name you relied on."
)


@dataclass
class RagAnswer:
    answer: str
    sources: list[SourceChunk]


def _build_context(game_title: str, chunks: list[SourceChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        section = chunk.section or "General"
        parts.append(f"[{i}] {game_title} - {section}\n{chunk.text}")
    return "\n\n".join(parts)


def answer_question(question: str, game_id: int, game_title: str) -> RagAnswer:
    """Answer a rules question from one game's rulebook.

    Raises ServiceUnavailableException if the LLM is unreachable.
    """
    try:
        retrieved = retrieve(question, game_id, n_results=N_RESULTS)
    except Exception:
        raise ServiceUnavailableException("The rulebook search is unavailable")
    chunks = [c for c in retrieved if c.score is not None and c.score >= MIN_SCORE]
    if not chunks:
        return RagAnswer(answer=NOT_COVERED, sources=[])

    user_prompt = (
        f"Rulebook excerpts for {game_title}:\n\n"
        f"{_build_context(game_title, chunks)}\n\n"
        f"Question: {question}"
    )
    reply = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return RagAnswer(answer=reply, sources=chunks)
