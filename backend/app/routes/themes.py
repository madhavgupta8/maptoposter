import json
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify

from app.config import Config

bp = Blueprint("themes", __name__)


@lru_cache(maxsize=1)
def _load_themes() -> list[dict]:
    themes_dir = Path(Config.MAPTOPOSTER_DIR) / "themes"
    items = []
    for path in sorted(themes_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            theme = json.load(handle)
        items.append(
            {
                "key": path.stem,
                "name": theme.get("name", path.stem),
                "description": theme.get("description", ""),
                "bg": theme.get("bg"),
                "text": theme.get("text"),
                "water": theme.get("water"),
                "parks": theme.get("parks"),
                "road_default": theme.get("road_default"),
            }
        )
    return items


def get_theme_keys() -> set[str]:
    return {theme["key"] for theme in _load_themes()}


@bp.get("/themes")
def themes():
    return jsonify(_load_themes())
