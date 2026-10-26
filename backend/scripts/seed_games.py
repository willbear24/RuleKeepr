"""Seed the games catalog from backend/data/rulebooks/games.json and ingest each rulebook into ChromaDB for retrieval.

Run from the repo root:  python -m backend.scripts.seed_games

Safe to re-run: games are matched by rules_filename and updated in place, and a game's chunks are replaced on each ingest. Entries whose .txt file is missing are skipped with a warning. The ChromaDB step needs the vector store running;
if it is unreachable the games are still saved and ingestion can be re-run later.
"""

import json
from pathlib import Path

from backend.app.database import Base, SessionLocal, engine
import backend.app.models  # noqa: F401  (registers tables on Base.metadata)
from backend.app.models.game import Game
from backend.app.services.vector_store import ingest_game

RULEBOOKS_DIR = Path(__file__).resolve().parents[1] / "data" / "rulebooks"
MANIFEST_PATH = RULEBOOKS_DIR / "games.json"
FIELDS = ("title", "min_player", "max_player", "play_time_minutes")


def seed_games() -> None:
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    Base.metadata.create_all(engine)

    added = updated = skipped = 0
    seeded = []
    with SessionLocal() as db:
        for entry in entries:
            filename = entry["rules_filename"]
            if not (RULEBOOKS_DIR / filename).is_file():
                print(f"SKIP  {entry['title']}: {filename} not found")
                skipped += 1
                continue

            game = db.query(Game).filter(Game.rules_filename == filename).first()
            if game is None:
                game = Game(
                    rules_filename=filename, **{f: entry.get(f) for f in FIELDS}
                )
                db.add(game)
                added += 1
            else:
                for field in FIELDS:
                    setattr(game, field, entry.get(field))
                updated += 1
            seeded.append(game)
        db.commit()
        print(f"Seeded games: {added} added, {updated} updated, {skipped} skipped")

        # Games are committed first, so a ChromaDB failure can't undo them.
        chunk_total = 0
        try:
            for game in seeded:
                text = (RULEBOOKS_DIR / game.rules_filename).read_text(encoding="utf-8")
                count = ingest_game(game.id, game.title, text)
                chunk_total += count
                print(f"INGEST {game.title}: {count} chunks")
        except Exception as exc:
            print(f"WARNING: ingestion stopped ({type(exc).__name__}: {exc})")
            print(
                "Games were saved. Start ChromaDB and re-run to ingest the rulebooks."
            )
            return

    print(f"Ingested {chunk_total} chunks for {len(seeded)} games")


if __name__ == "__main__":
    seed_games()
