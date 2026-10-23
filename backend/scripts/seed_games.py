"""Seed the games catalog from backend/data/rulebooks/games.json.

Run from the repo root:  python -m backend.scripts.seed_games

Safe to re-run: games are matched by rules_filename and updated in place.
Entries whose .txt file is missing are skipped with a warning.
"""

import json
from pathlib import Path

from backend.app.database import Base, SessionLocal, engine
import backend.app.models  # noqa: F401  (registers tables on Base.metadata)
from backend.app.models.game import Game

RULEBOOKS_DIR = Path(__file__).resolve().parents[1] / "data" / "rulebooks"
MANIFEST_PATH = RULEBOOKS_DIR / "games.json"
FIELDS = ("title", "min_player", "max_player", "play_time_minutes")


def seed_games() -> None:
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    Base.metadata.create_all(engine)

    added = updated = skipped = 0
    with SessionLocal() as db:
        for entry in entries:
            filename = entry["rules_filename"]
            if not (RULEBOOKS_DIR / filename).is_file():
                print(f"SKIP  {entry['title']}: {filename} not found")
                skipped += 1
                continue

            game = db.query(Game).filter(Game.rules_filename == filename).first()
            if game is None:
                db.add(Game(rules_filename=filename, **{f: entry.get(f) for f in FIELDS}))
                added += 1
            else:
                for field in FIELDS:
                    setattr(game, field, entry.get(field))
                updated += 1
        db.commit()

    print(f"Seeded games: {added} added, {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    seed_games()
