# Changelog

All notable changes to the City Map Poster Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
