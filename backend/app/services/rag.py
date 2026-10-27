from dataclasses import dataclass

from backend.app.schemas.chunk import SourceChunk
from backend.app.services.llm_client import chat
from backend.app.services.vector_store import retrieve
from backend.app.utils.exceptions import ServiceUnavailableException

# Chunks scoring below this were weak matches in retrieval spot checks; the prompt
# still refuses when the excerpts don't answer the question.
MIN_SCORE = 0.25
N_RESULTS = 5

NOT_COVERED = "I couldn't find anything in the rulebook that answers that."

SYSTEM_PROMPT = (
    "You are a board game rules assistant. Answer the player's question using ONLY the rulebook excerpts provided. "
    "If the excerpts don't contain the answer, reply "
    f'exactly: "{NOT_COVERED}" Do not use outside knowledge or guess. '
    "Answer the whole question. If it involves several steps or options, list every one in order, "
    "and mention the section name you relied on."
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
        # Short questions often omit the game name, which weakens the match against rulebook text.
        retrieved = retrieve(f"{game_title}: {question}", game_id, n_results=N_RESULTS)
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
