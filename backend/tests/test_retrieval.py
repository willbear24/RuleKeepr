from backend.app.services import vector_store


class FakeCollection:
    def __init__(self, results):
        self.results = results
        self.query_args = None

    def query(self, **kwargs):
        self.query_args = kwargs
        return self.results


def test_retrieve_maps_matching_results_and_filters_by_distance(monkeypatch):
    collection = FakeCollection(
        {
            "documents": [[
                "Monopoly - PASSING GO\nCollect $200.",
                "Monopoly - JAIL\nStay in jail.",
            ]],
            "metadatas": [[
                {
                    "game_id": 7,
                    "game_title": "Monopoly",
                    "chunk_index": 2,
                    "section": "PASSING GO",
                    "text": "Collect $200.",
                },
                {
                    "game_id": 7,
                    "game_title": "Monopoly",
                    "chunk_index": 3,
                    "section": "JAIL",
                    "text": "Stay in jail.",
                },
            ]],
            "distances": [[0.2, 0.81]],
        }
    )
    monkeypatch.setattr(vector_store, "get_collection", lambda: collection)

    chunks = vector_store.retrieve("pass go", game_id=7, max_distance=0.8)

    assert len(chunks) == 1
    assert chunks[0].game_id == 7
    assert chunks[0].game_title == "Monopoly"
    assert chunks[0].chunk_index == 2
    assert chunks[0].section == "PASSING GO"
    assert chunks[0].text == "Collect $200."
    assert chunks[0].score == 0.8
    assert collection.query_args == {
        "query_texts": ["pass go"],
        "n_results": 5,
        "where": {"game_id": 7},
    }


def test_retrieve_returns_no_chunks_when_collection_has_no_matches(monkeypatch):
    collection = FakeCollection(
        {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
    )
    monkeypatch.setattr(vector_store, "get_collection", lambda: collection)

    assert vector_store.retrieve("unmatched question", game_id=7) == []
