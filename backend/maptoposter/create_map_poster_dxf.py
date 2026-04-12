import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
from datetime import datetime
import argparse
import ezdxf
from xml.etree import ElementTree as ET
import re

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"

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

def generate_output_filename(city, theme_name):
    """
    Generate unique output filename with city, theme, and datetime.
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    filename = f"{city_slug}_{theme_name}_{timestamp}.dxf"
    return os.path.join(POSTERS_DIR, filename)

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

def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple (0-255 range).
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def parse_svg_path(path_data):
    """
    Parse SVG path data into coordinate lists.
    Simplified parser for basic path commands.
    """
    coords = []
    commands = re.findall(r'[MLHVCSQTAZmlhvcsqtaz][^MLHVCSQTAZmlhvcsqtaz]*', path_data)
    
    current_x, current_y = 0, 0
    
    for cmd in commands:
        cmd_type = cmd[0]
        params = re.findall(r'-?\d+\.?\d*', cmd[1:])
        params = [float(p) for p in params]
        
        if cmd_type in 'Mm':  # Move to
            if len(params) >= 2:
                if cmd_type == 'M':
                    current_x, current_y = params[0], params[1]
                else:  # relative
                    current_x += params[0]
                    current_y += params[1]
                coords.append((current_x, current_y))
        
        elif cmd_type in 'Ll':  # Line to
            if len(params) >= 2:
                if cmd_type == 'L':
                    current_x, current_y = params[0], params[1]
                else:  # relative
                    current_x += params[0]
                    current_y += params[1]
                coords.append((current_x, current_y))
        
        elif cmd_type in 'Hh':  # Horizontal line
            if len(params) >= 1:
                if cmd_type == 'H':
                    current_x = params[0]
                else:
                    current_x += params[0]
                coords.append((current_x, current_y))
        
        elif cmd_type in 'Vv':  # Vertical line
            if len(params) >= 1:
                if cmd_type == 'V':
                    current_y = params[0]
                else:
                    current_y += params[0]
                coords.append((current_x, current_y))
    
    return coords

def convert_svg_to_dxf(svg_path, dxf_path):
    """
    Convert SVG file to DXF format using ezdxf.
    This is a simplified conversion focusing on paths and lines.
    """
    print("Converting SVG to DXF format...")
    
    # Parse SVG
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Create DXF document
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # SVG namespace
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Extract viewBox or width/height for coordinate scaling
    viewbox = root.get('viewBox')
    if viewbox:
        viewbox_parts = viewbox.split()
        svg_width = float(viewbox_parts[2])
        svg_height = float(viewbox_parts[3])
    else:
        width_str = root.get('width', '1000')
        height_str = root.get('height', '1000')
        # Remove units like 'pt', 'px'
        svg_width = float(re.sub(r'[^0-9.]', '', width_str))
        svg_height = float(re.sub(r'[^0-9.]', '', height_str))
    
    print(f"  SVG dimensions: {svg_width} x {svg_height}")
    
    # Process all path elements
    paths_processed = 0
    for element in root.iter():
        tag = element.tag.split('}')[-1]  # Remove namespace
        
        if tag == 'path':
            path_data = element.get('d', '')
            stroke = element.get('stroke', '#000000')
            stroke_width = float(element.get('stroke-width', '1'))
            
            if path_data:
                coords = parse_svg_path(path_data)
                
                if len(coords) >= 2:
                    # Convert SVG coordinates to DXF (flip Y axis)
                    dxf_coords = [(x, svg_height - y) for x, y in coords]
                    
                    # Create polyline
                    try:
                        msp.add_lwpolyline(dxf_coords)
                        paths_processed += 1
                    except:
                        pass  # Skip problematic paths
        
        elif tag == 'line':
            x1 = float(element.get('x1', '0'))
            y1 = float(element.get('y1', '0'))
            x2 = float(element.get('x2', '0'))
            y2 = float(element.get('y2', '0'))
            
            # Convert Y coordinates (SVG to DXF)
            msp.add_line((x1, svg_height - y1), (x2, svg_height - y2))
            paths_processed += 1
        
        elif tag == 'rect':
            x = float(element.get('x', '0'))
            y = float(element.get('y', '0'))
            width = float(element.get('width', '0'))
            height = float(element.get('height', '0'))
            
            # Convert to rectangle (flip Y)
            y_dxf = svg_height - y - height
            msp.add_lwpolyline([
                (x, y_dxf),
                (x + width, y_dxf),
                (x + width, y_dxf + height),
                (x, y_dxf + height),
                (x, y_dxf)  # Close the rectangle
            ])
            paths_processed += 1
    
    print(f"  Processed {paths_processed} graphic elements")
    
    # Save DXF
    doc.saveas(dxf_path)
    print(f"✓ DXF conversion complete!")
    
    # Clean up temporary SVG
    try:
        os.remove(svg_path)
    except:
        pass

def create_poster(city, country, point, dist, output_file, width=12, height=16):
    print(f"\nGenerating DXF map for {city}, {country}...")
    print(f"Output dimensions: {width}\" x {height}\" (vector format)")
    
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
    
    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])
    
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
    
    # Layer 2: Roads with hierarchy coloring
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
    
    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)
    
    # 4. Typography using Roboto font
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=60)
        font_top = FontProperties(fname=FONTS['bold'], size=40)
        font_sub = FontProperties(fname=FONTS['light'], size=22)
        font_coords = FontProperties(fname=FONTS['regular'], size=14)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family='monospace', weight='bold', size=60)
        font_top = FontProperties(family='monospace', weight='bold', size=40)
        font_sub = FontProperties(family='monospace', weight='normal', size=22)
        font_coords = FontProperties(family='monospace', size=14)
    
    spaced_city = "  ".join(list(city.upper()))

    # --- BOTTOM TEXT ---
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)
    
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)
    
    lat, lon = point
    coords = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
    if lon < 0:
        coords = coords.replace("E", "W")
    
    ax.text(0.5, 0.07, coords, transform=ax.transAxes,
            color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)
    
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, 
            color=THEME['text'], linewidth=1, zorder=11)

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_attr = FontProperties(family='monospace', size=8)
    
    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=THEME['text'], alpha=0.5, ha='right', va='bottom', 
            fontproperties=font_attr, zorder=11)

    # 5. Save as SVG first (intermediate step)
    print(f"Saving intermediate SVG...")
    temp_svg = output_file.replace('.dxf', '_temp.svg')
    plt.savefig(temp_svg, format='svg', facecolor=THEME['bg'])
    plt.close()
    
    # 6. Convert SVG to DXF
    convert_svg_to_dxf(temp_svg, output_file)
    
    print(f"✓ Done! DXF poster saved as {output_file}")
    print(f"✓ DXF is a CAD vector format - perfect for professional plotting!")

def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator (DXF CAD Format)
==========================================

Usage:
  python create_map_poster_dxf.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster_dxf.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
  python create_map_poster_dxf.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district grid
  
  # Waterfront & canals
  python create_map_poster_dxf.py -c "Venice" -C "Italy" -t blueprint -d 4000       # Canal network
  python create_map_poster_dxf.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000  # Concentric canals
  python create_map_poster_dxf.py -c "Dubai" -C "UAE" -t midnight_blue -d 15000     # Palm & coastline
  
  # Radial patterns
  python create_map_poster_dxf.py -c "Paris" -C "France" -t pastel_dream -d 10000   # Haussmann boulevards
  python create_map_poster_dxf.py -c "Moscow" -C "Russia" -t noir -d 12000          # Ring roads
  
  # Organic old cities
  python create_map_poster_dxf.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000    # Dense organic streets
  python create_map_poster_dxf.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000 # Medina maze
  python create_map_poster_dxf.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient street layout
  
  # Coastal cities
  python create_map_poster_dxf.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
  python create_map_poster_dxf.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
  python create_map_poster_dxf.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula
  
  # River cities
  python create_map_poster_dxf.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
  python create_map_poster_dxf.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split
  
  # List themes
  python create_map_poster_dxf.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --theme, -t       Theme name (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --width, -W       Image width in inches (default: 12)
  --height, -H      Image height in inches (default: 16)
  --list-themes     List all available themes

Dimension presets (vector format - infinitely scalable):
  Standard Print:   -W 12   -H 16
  Large Print:      -W 24   -H 36
  Poster:           -W 36   -H 48
  A4:               -W 8.3  -H 11.7
  A3:               -W 11.7 -H 16.5
  A2:               -W 16.5 -H 23.4

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

DXF Format Benefits:
  - Industry-standard CAD format
  - Perfect for professional plotting and printing
  - Editable in AutoCAD, LibreCAD, QCAD, and other CAD software
  - Infinitely scalable vector format
  - Ideal for architectural presentations and large-format prints

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
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
        description="Generate beautiful DXF CAD vector map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster_dxf.py --city "New York" --country "USA"
  python create_map_poster_dxf.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster_dxf.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster_dxf.py --city Paris --country France -W 24 -H 36  # Large poster size
  python create_map_poster_dxf.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, help='Map radius in meters (default: 29000)')
    parser.add_argument('--width', '-W', type=float, default=12, help='Image width in inches (default: 12)')
    parser.add_argument('--height', '-H', type=float, default=16, help='Image height in inches (default: 16)')
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
    print("City Map Poster Generator (DXF)")
    print("=" * 50)
    
    # Load theme
    THEME = load_theme(args.theme)
    
    # Get coordinates and generate poster
    try:
        coords = get_coordinates(args.city, args.country)
        output_file = generate_output_filename(args.city, args.theme)
        create_poster(args.city, args.country, coords, args.distance, output_file, args.width, args.height)
        
        print("\n" + "=" * 50)
        print("✓ DXF Poster generation complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
