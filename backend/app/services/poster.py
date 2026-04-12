import importlib
import os
import sys
from pathlib import Path

from app.config import Config

if Config.MAPTOPOSTER_DIR not in sys.path:
    sys.path.insert(0, Config.MAPTOPOSTER_DIR)

_module = None


def _get_module():
    global _module
    if _module is None:
        original_cwd = os.getcwd()
        try:
            os.chdir(Config.MAPTOPOSTER_DIR)
            _module = importlib.import_module("create_map_poster_hmi")
            _module.FONTS = _module.load_fonts()
        finally:
            os.chdir(original_cwd)
    return _module


def render_poster(city, country, theme, ratio, radius, no_small_roads, output_path):
    module = _get_module()
    ratio_map = {"3:4": (12, 16), "4:5": (12, 15)}
    width, height = ratio_map.get(ratio, (12, 16))
    original_cwd = os.getcwd()
    try:
        os.chdir(Config.MAPTOPOSTER_DIR)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        module.THEME = module.load_theme(theme)
        graph, water, parks, coords = module.get_or_fetch_map_data(
            city, country, int(radius), Config.MAPTOPOSTER_DIR
        )
        module.create_poster(
            city,
            country,
            graph,
            water,
            parks,
            coords,
            output_path,
            width=width,
            height=height,
            no_small_roads=no_small_roads,
        )
        return output_path
    finally:
        os.chdir(original_cwd)
