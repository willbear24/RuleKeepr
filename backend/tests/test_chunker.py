from backend.app.services.chunker import chunk_rulebook


def test_empty_rulebook_returns_no_chunks():
    assert chunk_rulebook("") == []


def test_text_without_heading_has_no_section():
    chunks = chunk_rulebook("A short rulebook paragraph.")

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].section is None
    assert chunks[0].text == "A short rulebook paragraph."


def test_heading_is_attached_to_its_chunk():
    chunks = chunk_rulebook("SETUP\nPlace the board on the table.")

    assert len(chunks) == 1
    assert chunks[0].section == "SETUP"
    assert chunks[0].text == "Place the board on the table."


def test_paragraphs_are_packed_up_to_max_words():
    chunks = chunk_rulebook(
        "one two\n\nthree four\n\nfive six",
        max_words=5,
    )

    assert [chunk.text for chunk in chunks] == [
        "one two\n\nthree four",
        "five six",
    ]
    assert [chunk.index for chunk in chunks] == [0, 1]


def test_chunks_do_not_cross_heading_boundaries():
    chunks = chunk_rulebook("FIRST\nFirst section text.\nSECOND\nSecond section text.")

    assert [chunk.section for chunk in chunks] == ["FIRST", "SECOND"]
    assert [chunk.text for chunk in chunks] == [
        "First section text.",
        "Second section text.",
    ]


def test_heading_without_body_is_combined_with_following_heading():
    chunks = chunk_rulebook(
        "7. BUILDING RULES\nROADS\nBuild roads using road pieces."
    )

    assert len(chunks) == 1
    assert chunks[0].section == "7. BUILDING RULES > ROADS"
    assert chunks[0].text == "Build roads using road pieces."


def test_oversized_paragraph_splits_at_sentence_boundaries():
    chunks = chunk_rulebook(
        "One two three. Four five six. Seven eight nine.",
        max_words=5,
    )

    assert [chunk.text for chunk in chunks] == [
        "One two three.",
        "Four five six.",
        "Seven eight nine.",
    ]
