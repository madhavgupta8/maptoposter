import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import geopandas as gpd
import copy
import time
import json
import os
from datetime import datetime
import argparse

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"

# ─── Font loading ──────────────────────────────────────────────────────────────

def load_fonts():
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    return fonts

FONTS = load_fonts()

# ─── Theme loading ─────────────────────────────────────────────────────────────

def get_available_themes():
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            themes.append(file[:-5])
    return themes

def load_theme(theme_name="feature_based"):
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF", "text": "#000000", "gradient_color": "#FFFFFF",
            "water": "#C0C0C0", "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A", "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A", "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A", "road_default": "#3A3A3A"
        }
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if 'description' in theme:
            print(f"  {theme['description']}")
        return theme

THEME = None  # Set in __main__

# ─── Output filename ───────────────────────────────────────────────────────────

def generate_output_filename(city, country, theme_name, distance):
    """
    Generate a unique output path using organized directory structure:
      posters/{country_slug}/{city_slug}/{theme}/{city}_{theme}_{distance}m_{timestamp}.png
    """
    country_slug = country.lower().replace(' ', '_')
    city_slug = city.lower().replace(' ', '_')

    out_dir = os.path.join(POSTERS_DIR, country_slug, city_slug, theme_name)
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{city_slug}_{theme_name}_{distance}m_{timestamp}.png"
    return os.path.join(out_dir, filename)

# ─── Map data caching ──────────────────────────────────────────────────────────

REQUIRED_META_KEYS = {
    "city", "country", "city_slug", "country_slug",
    "radius_m", "lat", "lon", "downloaded_at",
    "osmnx_version", "water_available", "parks_available"
}

def _slugify(s: str) -> str:
    """Normalize a city or country name to a filesystem-safe slug."""
    return s.lower().replace(' ', '_')

def _get_cache_dir(base_dir: str, city: str, country: str, dist: int) -> str:
    """Return the absolute path to the cache directory for a given key."""
    return os.path.join(
        base_dir, POSTERS_DIR,
        _slugify(country),
        _slugify(city),
        f"map_data_{dist}m"
    )

def _is_cache_valid(cache_dir: str) -> bool:
    """
    Return True if the cache directory holds a complete, internally consistent
    set of files. Returns False on any inconsistency — never raises.
    """
    meta_path = os.path.join(cache_dir, "metadata.json")
    graph_path = os.path.join(cache_dir, "graph.graphml")

    if not os.path.isdir(cache_dir):
        return False
    if not os.path.isfile(meta_path):
        return False
    if not os.path.isfile(graph_path):
        return False

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [cache] Warning: metadata.json unreadable ({exc}), treating as miss")
        return False

    missing = REQUIRED_META_KEYS - set(meta.keys())
    if missing:
        print(f"  [cache] Warning: metadata.json missing keys {missing}, treating as miss")
        return False

    if not isinstance(meta.get("water_available"), bool):
        print("  [cache] Warning: water_available is not bool, treating as miss")
        return False
    if not isinstance(meta.get("parks_available"), bool):
        print("  [cache] Warning: parks_available is not bool, treating as miss")
        return False

    if meta["water_available"] and not os.path.isfile(os.path.join(cache_dir, "water.gpkg")):
        print("  [cache] Warning: water.gpkg missing despite water_available=true, treating as miss")
        return False
    if meta["parks_available"] and not os.path.isfile(os.path.join(cache_dir, "parks.gpkg")):
        print("  [cache] Warning: parks.gpkg missing despite parks_available=true, treating as miss")
        return False

    return True

def _load_from_cache(cache_dir: str):
    """
    Load all map data from a validated cache directory.
    Returns (G, water, parks, lat, lon).
    Caller must ensure _is_cache_valid() returned True.
    """
    with open(os.path.join(cache_dir, "metadata.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("  [cache] Loading street graph from graph.graphml...")
    G = ox.load_graphml(os.path.join(cache_dir, "graph.graphml"))

    if meta["water_available"]:
        print("  [cache] Loading water features from water.gpkg...")
        water = gpd.read_file(os.path.join(cache_dir, "water.gpkg"))
    else:
        water = None

    if meta["parks_available"]:
        print("  [cache] Loading parks from parks.gpkg...")
        parks = gpd.read_file(os.path.join(cache_dir, "parks.gpkg"))
    else:
        parks = None

    return G, water, parks, meta["lat"], meta["lon"]

def _save_to_cache(cache_dir: str, G, water, parks,
                   city: str, country: str, dist: int,
                   lat: float, lon: float):
    """
    Persist all fetched map data to cache_dir.
    metadata.json is written last via atomic os.replace() so a partial
    write (e.g. power cut) leaves no valid metadata — next run re-fetches.
    """
    os.makedirs(cache_dir, exist_ok=True)

    print("  [cache] Saving street graph to graph.graphml...")
    ox.save_graphml(G, filepath=os.path.join(cache_dir, "graph.graphml"))

    water_available = False
    if water is not None and not water.empty:
        print("  [cache] Saving water features to water.gpkg...")
        water.to_file(os.path.join(cache_dir, "water.gpkg"), driver="GPKG")
        water_available = True

    parks_available = False
    if parks is not None and not parks.empty:
        print("  [cache] Saving parks to parks.gpkg...")
        parks.to_file(os.path.join(cache_dir, "parks.gpkg"), driver="GPKG")
        parks_available = True

    meta = {
        "city": city,
        "country": country,
        "city_slug": _slugify(city),
        "country_slug": _slugify(country),
        "radius_m": dist,
        "lat": lat,
        "lon": lon,
        "downloaded_at": datetime.utcnow().isoformat(),
        "osmnx_version": ox.__version__,
        "water_available": water_available,
        "parks_available": parks_available,
    }

    # Atomic write: write to .tmp first, then os.replace (POSIX-atomic on macOS/Linux)
    meta_path = os.path.join(cache_dir, "metadata.json")
    meta_tmp = meta_path + ".tmp"
    with open(meta_tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    os.replace(meta_tmp, meta_path)

    print(f"  [cache] Cache written → {cache_dir}")

def get_or_fetch_map_data(city: str, country: str, dist: int, base_dir: str):
    """
    Return (G, water, parks, point) where point = (lat, lon).

    Cache key: (city_slug, country_slug, dist).
    Theme is NOT part of the key — OSM data is theme-independent.

    On a cache HIT:  loads from disk, no network calls at all.
    On a cache MISS: fetches from network, saves to cache, returns data.
    """
    cache_dir = _get_cache_dir(base_dir, city, country, dist)

    # ── Cache hit ──────────────────────────────────────────────────────────────
    if _is_cache_valid(cache_dir):
        print(f"\n[cache HIT] {city}, {country} @ {dist}m")
        print(f"  Loading from: {cache_dir}")
        G, water, parks, lat, lon = _load_from_cache(cache_dir)
        print(f"  Coordinates: {lat:.4f}, {lon:.4f}")
        return G, water, parks, (lat, lon)

    # ── Cache miss ─────────────────────────────────────────────────────────────
    print(f"\n[cache MISS] {city}, {country} @ {dist}m — fetching from network")

    # Geocode
    print("  Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster_hmi")
    time.sleep(1)
    location = geolocator.geocode(f"{city}, {country}")
    if not location:
        raise ValueError(f"Could not find coordinates for {city}, {country}")
    lat, lon = location.latitude, location.longitude
    point = (lat, lon)
    print(f"  Found: {location.address}")
    print(f"  Coordinates: {lat:.4f}, {lon:.4f}")

    # Fetch OSM data
    with tqdm(total=3, desc="Fetching map data", unit="step",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:

        pbar.set_description("Downloading street network")
        G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all')
        pbar.update(1)
        time.sleep(0.5)

        pbar.set_description("Downloading water features")
        try:
            water = ox.features_from_point(
                point, tags={'natural': 'water', 'waterway': 'riverbank'}, dist=dist)
        except Exception:
            water = None
        pbar.update(1)
        time.sleep(0.3)

        pbar.set_description("Downloading parks/green spaces")
        try:
            parks = ox.features_from_point(
                point, tags={'leisure': 'park', 'landuse': 'grass'}, dist=dist)
        except Exception:
            parks = None
        pbar.update(1)

    print("  ✓ All network data downloaded successfully.")

    # Persist to cache
    _save_to_cache(cache_dir, G, water, parks, city, country, dist, lat, lon)

    return G, water, parks, point

# ─── Road rendering helpers ───────────────────────────────────────────────────

def filter_small_roads(G):
    """Remove residential, living_street, and unclassified edges from the graph."""
    small_road_types = {'residential', 'living_street', 'unclassified'}
    edges_to_remove = []
    for u, v, k, d in G.edges(data=True, keys=True):
        hw = d.get('highway', '')
        if isinstance(hw, str) and hw in small_road_types:
            edges_to_remove.append((u, v, k))
        elif isinstance(hw, list) and all(t in small_road_types for t in hw):
            edges_to_remove.append((u, v, k))
    G.remove_edges_from(edges_to_remove)
    print(f"  Removed {len(edges_to_remove)} small road edges")
    return G

def get_edge_colors_by_type(G):
    edge_colors = []
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        if highway in ['motorway', 'motorway_link']:
            color = THEME['road_motorway']
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            color = THEME['road_primary']
        elif highway in ['secondary', 'secondary_link']:
            color = THEME['road_secondary']
        elif highway in ['tertiary', 'tertiary_link']:
            color = THEME['road_tertiary']
        elif highway in ['residential', 'living_street', 'unclassified']:
            color = THEME['road_residential']
        else:
            color = THEME['road_default']
        edge_colors.append(color)
    return edge_colors

def get_edge_widths_by_type(G):
    edge_widths = []
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        if highway in ['motorway', 'motorway_link']:
            width = 1.2
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            width = 1.0
        elif highway in ['secondary', 'secondary_link']:
            width = 0.8
        elif highway in ['tertiary', 'tertiary_link']:
            width = 0.6
        else:
            width = 0.4
        edge_widths.append(width)
    return edge_widths

# ─── Gradient helper ──────────────────────────────────────────────────────────

def create_gradient_fade(ax, color, location='bottom', zorder=10):
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start, extent_y_end = 0, 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start, extent_y_end = 0.75, 1.0
    custom_cmap = mcolors.ListedColormap(my_colors)
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top],
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')

# ─── Geocoding (kept as a standalone utility) ─────────────────────────────────

def get_coordinates(city, country):
    """
    Fetch coordinates from Nominatim. Kept for standalone/CLI use.
    The main flow uses get_or_fetch_map_data which also caches coordinates.
    """
    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster_hmi")
    time.sleep(1)
    location = geolocator.geocode(f"{city}, {country}")
    if location:
        print(f"✓ Found: {location.address}")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

# ─── Poster rendering ─────────────────────────────────────────────────────────

def create_poster(city, country, G, water, parks, point,
                  output_file, width=12, height=16, no_small_roads=False):
    """
    Render a map poster from pre-loaded OSM data.

    G, water, parks, and point are returned by get_or_fetch_map_data().
    The no_small_roads filter is applied here on a deep copy so the
    caller's (and the cache's) graph object is never mutated.
    """
    print(f"\nGenerating map for {city}, {country}...")
    print(f"Output dimensions: {width}\" x {height}\" at 300 DPI")

    # Apply per-render filtering on a copy so cache stays intact
    if no_small_roads:
        print("Filtering out small roads (working on a copy)...")
        G = copy.deepcopy(G)
        G = filter_small_roads(G)

    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])

    # Layer 1: Water and parks polygons
    if water is not None and not water.empty:
        water_polys = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        if not water_polys.empty:
            water_polys.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=1)
    if parks is not None and not parks.empty:
        parks_polys = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        if not parks_polys.empty:
            parks_polys.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=2)

    # Layer 2: Road network with hierarchy coloring
    print("Applying road hierarchy colors...")
    edge_colors = get_edge_colors_by_type(G)
    edge_widths = get_edge_widths_by_type(G)

    ox.plot_graph(
        G, ax=ax, bgcolor=THEME['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False, close=False
    )

    # Layer 3: Gradient fades
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)

    # Layer 4: Typography
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=60)
        font_sub = FontProperties(fname=FONTS['light'], size=22)
        font_coords = FontProperties(fname=FONTS['regular'], size=14)
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_main = FontProperties(family='monospace', weight='bold', size=60)
        font_sub = FontProperties(family='monospace', weight='normal', size=22)
        font_coords = FontProperties(family='monospace', size=14)
        font_attr = FontProperties(family='monospace', size=8)

    spaced_city = "  ".join(list(city.upper()))

    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)

    lat, lon = point
    coords_str = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
    if lon < 0:
        coords_str = coords_str.replace("E", "W")

    ax.text(0.5, 0.07, coords_str, transform=ax.transAxes,
            color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes,
            color=THEME['text'], linewidth=1, zorder=11)
    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=THEME['text'], alpha=0.5, ha='right', va='bottom',
            fontproperties=font_attr, zorder=11)

    # Save
    print(f"Saving to {output_file}...")
    plt.savefig(output_file, dpi=300, facecolor=THEME['bg'])
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city (HMI version with caching)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based',
                        help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000,
                        help='Map radius in metres (default: 29000)')
    parser.add_argument('--width', '-W', type=float, default=12,
                        help='Image width in inches (default: 12)')
    parser.add_argument('--height', '-H', type=float, default=16,
                        help='Image height in inches (default: 16)')
    parser.add_argument('--no-small-roads', action='store_true',
                        help='Exclude residential, living_street, and unclassified roads')
    parser.add_argument('--list-themes', action='store_true',
                        help='List all available themes')

    args = parser.parse_args()

    if args.list_themes:
        themes = get_available_themes()
        print("Available themes:", ', '.join(themes))
        os.sys.exit(0)

    if not args.city or not args.country:
        print("Error: --city and --country are required.")
        os.sys.exit(1)

    available_themes = get_available_themes()
    if args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        os.sys.exit(1)

    print("=" * 50)
    print("City Map Poster Generator (HMI)")
    print("=" * 50)

    THEME = load_theme(args.theme)

    # base_dir is the directory containing this script, so paths work
    # regardless of the shell's cwd when the script is invoked.
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # All I/O (geocoding + OSM downloads) goes through the cache layer.
        # On a HIT: no network calls at all.
        # On a MISS: fetches everything and saves for next time.
        G, water, parks, coords = get_or_fetch_map_data(
            args.city, args.country, args.distance, base_dir
        )

        output_file = generate_output_filename(
            args.city, args.country, args.theme, args.distance
        )

        create_poster(
            args.city, args.country,
            G, water, parks, coords,
            output_file,
            args.width, args.height,
            no_small_roads=args.no_small_roads
        )

        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print(f"✓ Saved to: {output_file}")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
