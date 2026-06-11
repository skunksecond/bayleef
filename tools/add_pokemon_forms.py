"""Append PokeAPI Pokemon forms to an existing Pokedex SQLite database.

By default this adds regional forms only: Alola, Galar, Hisui, and Paldea.

Example:
    python tools/add_pokemon_forms.py
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from build_pokedex_db import (
    PokeApiClient,
    build_version_maps,
    ensure_form_columns,
    insert_complete_pokemon,
    resource_id,
    selected_varieties,
)


DEFAULT_SKIP_SPECIES = (50, 51, 72, 73, 854, 855)


def parse_species_ids(value: str) -> set[int]:
    if not value.strip():
        return set()
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def chain_exists(conn: sqlite3.Connection, chain_id: int | None) -> bool:
    if chain_id is None:
        return True
    row = conn.execute(
        "SELECT 1 FROM evolution_chains WHERE chain_id = ?",
        (chain_id,),
    ).fetchone()
    return row is not None


def pokemon_exists(conn: sqlite3.Connection, pokemon_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pokemon WHERE id = ?",
        (pokemon_id,),
    ).fetchone()
    return row is not None


def add_forms(args: argparse.Namespace) -> None:
    db_path = Path(args.database)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    api = PokeApiClient(Path(args.cache_dir), sleep_seconds=args.sleep)
    conn = sqlite3.connect(db_path)

    try:
        ensure_form_columns(conn)
        generation_by_version_group, generation_by_version = build_version_maps(
            conn,
            api,
        )

        added = 0
        skipped = 0
        skipped_species = parse_species_ids(args.skip_species)

        for species_id in range(1, args.limit + 1):
            if species_id in skipped_species:
                skipped += 1
                continue

            species = api.get(f"pokemon-species/{species_id}")
            varieties = selected_varieties(species, args.form_scope)
            if not varieties:
                continue

            for variety in varieties:
                pokemon = api.get_url(variety["pokemon"]["url"])

                if pokemon_exists(conn, pokemon["id"]) and not args.refresh:
                    skipped += 1
                    continue

                print(f"Adding {pokemon['name']} ({species_id})")
                insert_complete_pokemon(
                    conn,
                    pokemon,
                    species,
                    generation_by_version_group,
                    generation_by_version,
                    args.language,
                    is_default=False,
                )
                added += 1

            evolution_chain_id = resource_id(species["evolution_chain"])
            if not chain_exists(conn, evolution_chain_id):
                from build_pokedex_db import insert_evolution_chain

                chain = api.get_url(species["evolution_chain"]["url"])
                insert_evolution_chain(conn, chain)

            if species_id % args.commit_every == 0:
                conn.commit()

        conn.commit()
        print(f"Done. Added {added} forms; skipped {skipped} existing forms.")
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append regional or other PokeAPI forms to a Pokedex DB.",
    )
    parser.add_argument(
        "--database",
        default="app/data/pokedex.sqlite",
        help="Existing SQLite database to update.",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/pokeapi",
        help="Directory used to cache PokeAPI JSON responses.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1025,
        help="Number of National Dex species to scan for forms.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Flavor text language code.",
    )
    parser.add_argument(
        "--form-scope",
        choices=("regional", "all"),
        default="regional",
        help="Add only regional forms or all non-default PokeAPI varieties.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh form rows that already exist in the database.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds to sleep after uncached API requests.",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=25,
        help="Commit progress after this many species.",
    )
    parser.add_argument(
        "--skip-species",
        default=",".join(str(species_id) for species_id in DEFAULT_SKIP_SPECIES),
        help=(
            "Comma-separated National Dex species IDs to skip while scanning "
            "for forms."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    add_forms(parse_args())
