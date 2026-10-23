import re
from dataclasses import dataclass

# tl;dr Breaks rulebooks into chunks based on paragraphs and headings. Subheading should be grouped within larger headings and chunks will not trail into other sections to preserve accurate sourcing.

MAX_WORDS = 200
MAX_HEADING_CHARS = 80


@dataclass(frozen=True)
class Chunk:
    index: int
    section: str | None
    text: str


# Looks for and ignores decorations like underlines for page breaks.
DECORATION = re.compile(r"^\s*[-=_*]{3,}\s*$")


def is_heading(line: str) -> bool:
    """A heading is a short line with at least one letter and no lowercase letters."""
    line = line.strip()
    if not line or len(line) > MAX_HEADING_CHARS:
        return False
    return any(c.isalpha() for c in line) and line == line.upper()


def _split_sections(text: str) -> list[tuple[str | None, list[str]]]:
    """Group lines under the heading above them.

    Headings with no body (a title block, or "7. BUILDING RULES" directly above
    "ROADS") are combined with the next heading instead of becoming empty sections.
    """
    sections = []
    pending: list[str] = []
    section, body = None, []

    for line in text.splitlines():
        if DECORATION.match(line):
            continue
        if is_heading(line):
            if body:
                sections.append((section, body))
                pending, body = [], []
            pending.append(line.strip())
            section = " > ".join(pending[-2:])
        else:
            body.append(line)

    if body:
        sections.append((section, body))
    return sections


def _paragraphs(lines: list[str]) -> list[str]:
    paragraphs, current = [], []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _word_count(text: str) -> int:
    return len(text.split())


def _split_long(paragraph: str, max_words: int) -> list[str]:
    """Break an oversized paragraph at sentence boundaries."""
    pieces, current = [], []
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        if current and _word_count(" ".join(current + [sentence])) > max_words:
            pieces.append(" ".join(current))
            current = []
        current.append(sentence)
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_rulebook(text: str, max_words: int = MAX_WORDS) -> list[Chunk]:
    """Split a rulebook into chunks that never cross a section boundary."""
    chunks: list[Chunk] = []

    for section, lines in _split_sections(text):
        units = []
        for paragraph in _paragraphs(lines):
            if _word_count(paragraph) > max_words:
                units.extend(_split_long(paragraph, max_words))
            else:
                units.append(paragraph)

        current: list[str] = []
        for unit in units:
            if current and _word_count("\n\n".join(current + [unit])) > max_words:
                chunks.append(Chunk(len(chunks), section, "\n\n".join(current)))
                current = []
            current.append(unit)
        if current:
            chunks.append(Chunk(len(chunks), section, "\n\n".join(current)))

    return chunks
