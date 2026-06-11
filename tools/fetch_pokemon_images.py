"""Download Pokemon images from PokeAPI into app/assets/pokemon.

Base Pokemon are named by National Dex number, such as 0001.png. If forms are
included, form images keep the same number plus a suffix, such as 0052-alola.png.

Example:
    python tools/fetch_pokemon_images.py
    python tools/fetch_pokemon_images.py --form-scope all
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Any

import requests

from build_pokedex_db import PokeApiClient, selected_varieties


def nested_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def sprite_url(pokemon: dict[str, Any], image_source: str) -> str | None:
    sources = {
        "official-artwork": (
            ("sprites", "other", "official-artwork", "front_default"),
            ("sprites", "other", "home", "front_default"),
            ("sprites", "front_default"),
        ),
        "home": (
            ("sprites", "other", "home", "front_default"),
            ("sprites", "other", "official-artwork", "front_default"),
            ("sprites", "front_default"),
        ),
        "front-default": (
            ("sprites", "front_default"),
            ("sprites", "other", "official-artwork", "front_default"),
            ("sprites", "other", "home", "front_default"),
        ),
    }

    for path in sources[image_source]:
        url = nested_get(pokemon, path)
        if url:
            return url

    return None


def extension_from_url(url: str) -> str:
    clean_url = url.split("?", 1)[0]
    extension = Path(clean_url).suffix.lower()
    if extension in {".gif", ".jpg", ".jpeg", ".png", ".webp"}:
        return extension
    return ".png"


def form_suffix(species_name: str, pokemon_name: str) -> str:
    prefix = species_name + "-"
    if pokemon_name.startswith(prefix):
        suffix = pokemon_name[len(prefix):]
    else:
        suffix = pokemon_name
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", suffix).strip("-")


def image_path(
    output_dir: Path,
    species_id: int,
    species_name: str,
    pokemon_name: str,
    is_default: bool,
    url: str,
) -> Path:
    if is_default:
        stem = f"{species_id:04d}"
    else:
        stem = f"{species_id:04d}-{form_suffix(species_name, pokemon_name)}"
    return output_dir / f"{stem}{extension_from_url(url)}"


def download_image(
    session: requests.Session,
    url: str,
    output_path: Path,
    overwrite: bool,
) -> bool:
    if output_path.exists() and not overwrite:
        return False

    response = session.get(url, timeout=30)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return True


def fetch_one(
    session: requests.Session,
    output_dir: Path,
    pokemon: dict[str, Any],
    species: dict[str, Any],
    is_default: bool,
    image_source: str,
    overwrite: bool,
) -> bool:
    url = sprite_url(pokemon, image_source)
    if url is None:
        print(f"No sprite URL for {pokemon['name']}")
        return False

    path = image_path(
        output_dir,
        species["id"],
        species["name"],
        pokemon["name"],
        is_default,
        url,
    )

    downloaded = download_image(session, url, path, overwrite)
    action = "Downloaded" if downloaded else "Skipped"
    print(f"{action} {path}")
    return downloaded


def fetch_images(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api = PokeApiClient(Path(args.cache_dir), sleep_seconds=args.sleep)
    session = requests.Session()
    downloaded = 0

    for pokemon_id in range(1, args.limit + 1):
        pokemon = api.get(f"pokemon/{pokemon_id}")
        species = api.get_url(pokemon["species"]["url"])

        if fetch_one(
            session,
            output_dir,
            pokemon,
            species,
            is_default=True,
            image_source=args.image_source,
            overwrite=args.overwrite,
        ):
            downloaded += 1

        for variety in selected_varieties(species, args.form_scope):
            form_pokemon = api.get_url(variety["pokemon"]["url"])
            if fetch_one(
                session,
                output_dir,
                form_pokemon,
                species,
                is_default=False,
                image_source=args.image_source,
                overwrite=args.overwrite,
            ):
                downloaded += 1

        if args.sleep:
            time.sleep(args.sleep)

    print(f"Done. Downloaded {downloaded} images to {output_dir}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Pokemon images from PokeAPI.",
    )
    parser.add_argument(
        "--output-dir",
        default="app/assets/pokemon",
        help="Directory to write Pokemon images into.",
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
        help="Number of National Dex Pokemon to fetch images for.",
    )
    parser.add_argument(
        "--form-scope",
        choices=("none", "regional", "all"),
        default="regional",
        help="Download no form images, only regional forms, or all varieties.",
    )
    parser.add_argument(
        "--image-source",
        choices=("official-artwork", "home", "front-default"),
        default="official-artwork",
        help="Preferred PokeAPI sprite source.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace images that already exist.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Seconds to sleep after requests.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    fetch_images(parse_args())
