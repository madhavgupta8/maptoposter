import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
from datetime import datetime
import argparse
import networkx as nx

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
THEMES_DIR = os.path.join(SCRIPT_DIR, "themes")
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
POSTERS_DIR = os.path.join(SCRIPT_DIR, "posters")

def load_fonts():
    """
    Load Roboto fonts from the fonts directory.
    Returns dict with font paths for different weights.
    """
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    
    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    
    return fonts

FONTS = load_fonts()

OUTER_FRAME = {'left': 0.03, 'bottom': 0.03, 'width': 0.94, 'height': 0.94}
MAP_FRAME = {'left': 0.11, 'bottom': 0.10, 'width': 0.78, 'height': 0.832}

def generate_output_filename(city, theme_name):
    """
    Generate unique output filename with city, theme, and datetime.
    Creates a city-specific subdirectory in posters/.
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    # Create city-specific folder
    city_slug = city.lower().replace(' ', '_')
    city_folder = os.path.join(POSTERS_DIR, city_slug)
    if not os.path.exists(city_folder):
        os.makedirs(city_folder)
        print(f"✓ Created folder: {city_folder}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{city_slug}_{theme_name}_no_small_roads_16x20_top_border_{timestamp}.png"
    return os.path.join(city_folder, filename)

def get_available_themes():
    """
    Scans the themes directory and returns a list of available theme names.
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes

def load_theme(theme_name="feature_based"):
    """
    Load theme from JSON file in themes directory.
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        # Fallback to embedded default theme
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A",
            "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A",
            "road_default": "#3A3A3A"
        }
    
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if 'description' in theme:
            print(f"  {theme['description']}")
        return theme

# Load theme (can be changed via command line or input)
THEME = None  # Will be loaded later

def create_gradient_fade(ax, color, location='bottom', zorder=10):
    """
    Creates a fade effect at the top or bottom of the map.
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 0.75
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top], 
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')

def set_top_weighted_map_window(ax, aspect_ratio=3/4, top_weight=0.08):
    """
    Enforce a 3:4 map viewport and shift content slightly upward in the frame.
    """
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    x_span = x_max - x_min
    y_span = y_max - y_min

    if x_span <= 0 or y_span <= 0:
        return

    current_ratio = x_span / y_span

    if current_ratio > aspect_ratio:
        new_y_span = x_span / aspect_ratio
        new_x_span = x_span
    else:
        new_x_span = y_span * aspect_ratio
        new_y_span = y_span

    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    # Shift the viewing window slightly downward so map features appear higher.
    y_shift = new_y_span * top_weight
    center_y -= y_shift

    ax.set_xlim(center_x - new_x_span / 2, center_x + new_x_span / 2)
    ax.set_ylim(center_y - new_y_span / 2, center_y + new_y_span / 2)

def draw_poster_frame(fig, color):
    """
    Draw outer poster frame and inner map frame in figure coordinates.
    """
    outer_rect = Rectangle(
        (OUTER_FRAME['left'], OUTER_FRAME['bottom']),
        OUTER_FRAME['width'],
        OUTER_FRAME['height'],
        transform=fig.transFigure,
        fill=False,
        linewidth=1.6,
        edgecolor=color,
        zorder=20,
    )

    inner_rect = Rectangle(
        (MAP_FRAME['left'], MAP_FRAME['bottom']),
        MAP_FRAME['width'],
        MAP_FRAME['height'],
        transform=fig.transFigure,
        fill=False,
        linewidth=1.6,
        edgecolor=color,
        zorder=20,
    )

    fig.add_artist(outer_rect)
    fig.add_artist(inner_rect)

def filter_small_roads(G):
    """
    Removes edges representing small/residential roads from the graph.
    Keeps only major roads: motorway, trunk, primary, secondary, tertiary.
    Returns a new graph with filtered edges.
    """
    # Define which road types to KEEP (exclude lowest level roads)
    major_road_types = [
        'motorway', 'motorway_link',
        'trunk', 'trunk_link',
        'primary', 'primary_link',
        'secondary', 'secondary_link',
        'tertiary', 'tertiary_link'
    ]
    
    # Create a new graph with only major roads
    G_filtered = G.copy()
    edges_to_remove = []
    
    for u, v, key, data in G_filtered.edges(data=True, keys=True):
        highway = data.get('highway', 'unclassified')
        
        # Handle list of highway types
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Mark for removal if not a major road
        if highway not in major_road_types:
            edges_to_remove.append((u, v, key))
    
    # Remove the small roads
    G_filtered.remove_edges_from(edges_to_remove)
    
    print(f"✓ Filtered roads: {len(G.edges())} total → {len(G_filtered.edges())} major roads only")
    print(f"  (Removed {len(edges_to_remove)} small road segments)")
    
    return G_filtered

def get_edge_colors_by_type(G):
    """
    Assigns colors to edges based on road type hierarchy.
    Returns a list of colors corresponding to each edge in the graph.
    """
    edge_colors = []
    
    for u, v, data in G.edges(data=True):
        # Get the highway type (can be a list or string)
        highway = data.get('highway', 'unclassified')
        
        # Handle list of highway types (take the first one)
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign color based on road type
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
    """
    Assigns line widths to edges based on road type.
    Major roads get thicker lines.
    """
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign width based on road importance
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

def get_coordinates(city, country):
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster")
    
    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)
    
    location = geolocator.geocode(f"{city}, {country}")
    
    if location:
        print(f"✓ Found: {location.address}")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

def create_poster(city, country, point, dist, output_file, width=16, height=20):
    print(f"\nGenerating map for {city}, {country}...")
    print(f"Output dimensions: {width}\" x {height}\" at 300 DPI")
    print(f"⚠ Note: This version EXCLUDES small residential roads - only major roads shown")
    print("Layout: 16x20 poster, top-weighted 3:4 map, title in border")
    
    # Progress bar for data fetching
    with tqdm(total=3, desc="Fetching map data", unit="step", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        # 1. Fetch Street Network
        pbar.set_description("Downloading street network")
        G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all')
        pbar.update(1)
        time.sleep(0.5)  # Rate limit between requests
        
        # 2. Fetch Water Features
        pbar.set_description("Downloading water features")
        try:
            water = ox.features_from_point(point, tags={'natural': 'water', 'waterway': 'riverbank'}, dist=dist)
        except:
            water = None
        pbar.update(1)
        time.sleep(0.3)
        
        # 3. Fetch Parks
        pbar.set_description("Downloading parks/green spaces")
        try:
            parks = ox.features_from_point(point, tags={'leisure': 'park', 'landuse': 'grass'}, dist=dist)
        except:
            parks = None
        pbar.update(1)
    
    print("✓ All data downloaded successfully!")
    
    # Filter out small roads
    print("Filtering road network...")
    G = filter_small_roads(G)
    
    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([MAP_FRAME['left'], MAP_FRAME['bottom'], MAP_FRAME['width'], MAP_FRAME['height']])
    ax.set_axis_off()
    
    # 3. Plot Layers
    # Layer 1: Polygons (filter out Point geometries to avoid dots on the map)
    if water is not None and not water.empty:
        water_polys = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        if not water_polys.empty:
            water_polys.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=1)
    if parks is not None and not parks.empty:
        parks_polys = parks[parks.geometry.type.isin(['Polygon', 'MultiPolygon'])]
        if not parks_polys.empty:
            parks_polys.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=2)
    
    # Layer 2: Roads with hierarchy coloring (only major roads now)
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
    
    # Keep map viewport at 3:4 and skew content toward the top.
    set_top_weighted_map_window(ax, aspect_ratio=3/4, top_weight=0.08)

    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)

    draw_poster_frame(fig, THEME['text'])
    
    # 4. Typography using Roboto font
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=44)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family='monospace', weight='bold', size=44)
    
    spaced_city = "  ".join(list(city.upper()))

    # --- CITY TITLE IN BOTTOM BORDER (no country subtitle) ---
    fig.text(
        0.5,
        0.07,
        spaced_city,
        color=THEME['text'],
        ha='center',
        va='center',
        fontproperties=font_main,
        zorder=21,
    )

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_attr = FontProperties(family='monospace', size=8)
    
    fig.text(
        0.965,
        0.037,
        "© OpenStreetMap contributors",
        color=THEME['text'],
        alpha=0.5,
        ha='right',
        va='bottom',
        fontproperties=font_attr,
        zorder=21,
    )

    # 5. Save
    print(f"Saving to {output_file}...")
    plt.savefig(output_file, dpi=300, facecolor=THEME['bg'])
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")

def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator (16x20 Top Border Layout)
===================================================

This version excludes residential and small roads, showing only major arteries:
- Motorways/Highways
- Trunk roads
- Primary roads
- Secondary roads
- Tertiary roads

Usage:
  python create_map_poster_no_small_roads_16x20_top_border.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster_no_small_roads_16x20_top_border.py -c "New York" -C "USA" -t noir -d 12000
  python create_map_poster_no_small_roads_16x20_top_border.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000
  
  # Waterfront & canals
  python create_map_poster_no_small_roads_16x20_top_border.py -c "Venice" -C "Italy" -t blueprint -d 4000
  python create_map_poster_no_small_roads_16x20_top_border.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000
  
  # Radial patterns
  python create_map_poster_no_small_roads_16x20_top_border.py -c "Paris" -C "France" -t pastel_dream -d 10000
  python create_map_poster_no_small_roads_16x20_top_border.py -c "Moscow" -C "Russia" -t noir -d 12000
  
  # List themes
  python create_map_poster_no_small_roads_16x20_top_border.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --theme, -t       Theme name (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --width, -W       Image width in inches (default: 16)
  --height, -H      Image height in inches (default: 20)
  --list-themes     List all available themes

Generated posters are saved to 'posters/' directory.
Output layout:
  - Poster size: 16x20 inches
  - Map frame: 3:4, skewed toward top
  - City title: in bottom border
  - Country line: omitted
""")

def list_themes():
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return
    
    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, 'r') as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except:
            display_name = theme_name
            description = ''
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate 16x20 border-layout map posters for any city (major roads only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster_no_small_roads_16x20_top_border.py --city "New York" --country "USA"
  python create_map_poster_no_small_roads_16x20_top_border.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster_no_small_roads_16x20_top_border.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster_no_small_roads_16x20_top_border.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, help='Map radius in meters (default: 29000)')
    parser.add_argument('--width', '-W', type=float, default=16, help='Image width in inches (default: 16)')
    parser.add_argument('--height', '-H', type=float, default=20, help='Image height in inches (default: 20)')
    parser.add_argument('--list-themes', action='store_true', help='List all available themes')
    
    args = parser.parse_args()
    
    # If no arguments provided, show examples
    if len(os.sys.argv) == 1:
        print_examples()
        os.sys.exit(0)
    
    # List themes if requested
    if args.list_themes:
        list_themes()
        os.sys.exit(0)
    
    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        os.sys.exit(1)
    
    # Validate theme exists
    available_themes = get_available_themes()
    if args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        os.sys.exit(1)
    
    print("=" * 50)
    print("City Map Poster Generator")
    print("(16x20 Top Border Layout - Major Roads Only)")
    print("=" * 50)
    
    # Load theme
    THEME = load_theme(args.theme)
    
    # Get coordinates and generate poster
    try:
        coords = get_coordinates(args.city, args.country)
        output_file = generate_output_filename(args.city, args.theme)
        create_poster(args.city, args.country, coords, args.distance, output_file, args.width, args.height)
        
        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
