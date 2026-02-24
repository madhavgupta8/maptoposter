# Changelog

All notable changes to the City Map Poster Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added

#### New 16x20 Top-Border Poster Layout
- Added `maptoposter/create_map_poster_no_small_roads_16x20_top_border.py` as a copy of the no-small-roads generator with a custom print layout.
- Poster format is 16x20 inches with a 3:4 map frame that is visually weighted toward the top.
- City title is rendered in the bottom border area and the country subtitle is intentionally omitted.
- Added dual border rendering (outer poster frame + inner map frame) to match the framed poster style.

---

## [2.2.0] - 2026-02-01

### Changed

#### Improved Poster Organization
- **City-Specific Folders**: Posters are now automatically organized into city-specific subdirectories
- Structure: `posters/<city_name>/` (e.g., `posters/kansas_city/`, `posters/kanpur/`)
- Automatic folder creation when generating posters for a new city
- Makes it easier to manage and find posters when creating maps for multiple cities

#### Generated Posters
- Created Kansas City, United States poster set with Earth & Heritage theme
- Parameters: 31,500m radius, distance optimized for large metro area
- Generated both versions:
  - With all roads (including residential/small roads)
  - Major roads only (motorway, trunk, primary, secondary, tertiary)
- Saved to: `posters/kansas_city/`

### Technical Implementation
- Updated `generate_output_filename()` in both `create_map_poster.py` and `create_map_poster_no_small_roads.py`
- City folder creation with automatic slug generation (spaces → underscores, lowercase)
- Maintains backward compatibility with existing poster generation

---

## [2.1.0] - 2026-02-01

### Added

#### New Premium Themes Collection
- **6 New Themes** added to the theme library:
  1. **Warm Minimal** - Scandinavian-inspired warm minimal palette with soft neutrals and terracotta accents
  2. **Monochrome Luxe** - High-end monochrome theme with architectural gray tones
  3. **Midnight Blueprint** - Deep navy blueprint-style theme with cool contrasts
  4. **Earth & Heritage** - Heritage-inspired earthy palette reminiscent of old maps
  5. **Soft Pastel Modern** - Light, trendy pastel palette designed for modern interiors
  6. **Dark Mode Minimal** - Bold contemporary dark-mode theme with copper accents

#### Generated Posters
- Created complete set of Kanpur, India posters using all new themes
- Parameters: 11,000m radius, no small roads version
- Organized in dedicated collection folder: `posters/new_themes_2026_02_01/`
- Includes comprehensive README documenting each theme

### Changed
- Theme library expanded from 17 to 23 themes total
- Enhanced variety of color palettes for different interior design styles

---

## [2.0.0] - 2026-02-01

### Added

#### SVG Vector Format Support
- **New Script**: `maptoposter/create_map_poster_svg.py`
- Generates infinitely scalable vector posters in SVG format
- Perfect for web display, digital use, and vector editing
- Can be edited in Adobe Illustrator, Inkscape, and other vector graphics software
- Smaller file sizes compared to high-resolution PNG
- No quality loss when scaling to any size
- Zero additional dependencies required

#### DXF CAD Format Support
- **New Script**: `maptoposter/create_map_poster_dxf.py`
- Generates CAD-ready vector posters in DXF format
- Industry-standard format for professional plotting and printing
- Compatible with AutoCAD, LibreCAD, QCAD, and other CAD software
- Ideal for architectural presentations and large-format prints
- Infinitely scalable vector format
- Uses hybrid SVG-to-DXF conversion approach

#### New Dependencies
- `ezdxf >= 1.1.0` - For DXF file creation and manipulation
- `svgpathtools >= 1.5.0` - For SVG path parsing and conversion

### Changed
- Updated `requirements.txt` with new dependencies for DXF support
- Original PNG script (`create_map_poster.py`) remains unchanged and fully functional

### Technical Details

#### Implementation Approach
1. **SVG Implementation**: Direct matplotlib SVG export (simple modification)
2. **DXF Implementation**: Hybrid approach
   - Matplotlib renders to SVG first
   - Custom SVG-to-DXF converter parses SVG paths
   - Converts paths, lines, and rectangles to DXF entities
   - Handles coordinate system transformation (SVG Y-axis → DXF Y-axis)

#### File Structure
```
maptoposter/
├── create_map_poster.py      # Original PNG (300 DPI)
├── create_map_poster_svg.py  # New: SVG vector format
└── create_map_poster_dxf.py  # New: DXF CAD format
```

### Format Comparison

| Format | Type   | Scalability | Best For                    | File Size |
|--------|--------|-------------|----------------------------|-----------|
| PNG    | Raster | Fixed DPI   | Digital display, sharing   | Large     |
| SVG    | Vector | Infinite    | Web, editing, general use  | Small     |
| DXF    | Vector | Infinite    | CAD, plotting, pro prints  | Medium    |

### Usage Examples

```bash
# Generate PNG (original)
python maptoposter/create_map_poster.py -c "Paris" -C "France" -t noir

# Generate SVG (vector)
python maptoposter/create_map_poster_svg.py -c "Paris" -C "France" -t noir

# Generate DXF (CAD)
python maptoposter/create_map_poster_dxf.py -c "Paris" -C "France" -t noir
```

---

## [1.0.0] - 2026-01-01

### Initial Release
- PNG map poster generation at 300 DPI
- 17 beautiful themes (noir, blueprint, japanese_ink, etc.)
- Support for any city worldwide via OpenStreetMap
- Road hierarchy visualization with different colors
- Water features and parks rendering
- Customizable dimensions and map radius
- Typography with Roboto fonts
- Gradient fade effects
- OpenStreetMap attribution
