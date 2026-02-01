# Kanpur Map Project - Architecture Documentation

## System Architecture Diagram

This diagram visualizes the complete architecture and data flow of the Kanpur Map Project, a Python application that generates minimalist map posters using OpenStreetMap data.

```mermaid
graph TB
    subgraph "Entry Points"
        A[main.py<br/>Root CLI Wrapper] --> B[create_map_poster.py<br/>Core Application]
        CLI[CLI Arguments<br/>city, country, theme,<br/>distance, dimensions] --> B
    end

    subgraph "Data Fetching Layer"
        B --> C[get_coordinates]
        C --> D[Nominatim API<br/>Geocoding Service]
        D --> E[Latitude, Longitude]
        
        E --> F[OSMnx Data Fetching]
        F --> G[Street Network<br/>ox.graph_from_point]
        F --> H[Water Features<br/>ox.features_from_point]
        F --> I[Park/Green Spaces<br/>ox.features_from_point]
    end

    subgraph "Theme System"
        J[themes/ Directory<br/>17 JSON Themes] --> K[load_theme]
        K --> L[Theme Dictionary<br/>bg, text, water,<br/>parks, road colors]
    end

    subgraph "Rendering Pipeline"
        M[create_poster<br/>Main Rendering Function]
        
        G --> N[get_edge_colors_by_type<br/>Road Hierarchy Coloring]
        G --> O[get_edge_widths_by_type<br/>Road Width Assignment]
        
        L --> M
        H --> M
        I --> M
        N --> M
        O --> M
        
        M --> P[Matplotlib Layers]
        
        P --> P1[Layer 0: Background]
        P --> P2[Layer 1: Water Polygons]
        P --> P3[Layer 2: Parks Polygons]
        P --> P4[Layer 3: Road Network]
        P --> P5[Layer 10: Gradient Fades<br/>create_gradient_fade]
        P --> P6[Layer 11: Typography<br/>City, Country, Coordinates]
    end

    subgraph "Road Hierarchy System"
        R[OSM Highway Tags]
        R --> R1[motorway<br/>Width: 1.2]
        R --> R2[primary/trunk<br/>Width: 1.0]
        R --> R3[secondary<br/>Width: 0.8]
        R --> R4[tertiary<br/>Width: 0.6]
        R --> R5[residential<br/>Width: 0.4]
        
        R1 --> N
        R2 --> N
        R3 --> N
        R4 --> N
        R5 --> N
    end

    subgraph "Font Assets"
        F1[fonts/Roboto-Bold.ttf]
        F2[fonts/Roboto-Regular.ttf]
        F3[fonts/Roboto-Light.ttf]
        F1 --> P6
        F2 --> P6
        F3 --> P6
    end

    subgraph "Output"
        P6 --> Q[plt.savefig<br/>300 DPI]
        Q --> S[posters/ Directory<br/>{city}_{theme}_{timestamp}.png]
    end

    subgraph "Dependencies"
        T1[osmnx 2.0.7<br/>OSM Data]
        T2[matplotlib 3.10.8<br/>Visualization]
        T3[geopandas 1.1.2<br/>Geospatial Data]
        T4[geopy 2.4.1<br/>Geocoding]
        
        T1 -.-> F
        T2 -.-> M
        T3 -.-> M
        T4 -.-> C
    end

    style A fill:#e1f5ff
    style B fill:#fff9c4
    style M fill:#fff9c4
    style S fill:#c8e6c9
    style J fill:#f8bbd0
    style D fill:#e1bee7
    style F fill:#e1bee7
    style P fill:#ffccbc
```

## Component Overview

### Entry Points
- **main.py**: Simple CLI wrapper that executes Kanpur-specific commands
- **CLI Arguments**: Accepts city, country, theme, distance, and dimension parameters

### Data Fetching Layer
- **Geocoding**: Uses Nominatim API to convert city names to coordinates
- **OSM Data**: Fetches street networks, water features, and parks via OSMnx

### Theme System
- 17 JSON-based themes define visual appearance
- Each theme controls colors for background, text, water, parks, and roads

### Rendering Pipeline
Six distinct layers rendered via matplotlib:
1. **Background**: Theme-based solid color
2. **Water Polygons**: Rivers, lakes, water bodies (z-order: 1)
3. **Park Polygons**: Green spaces, parks (z-order: 2)
4. **Road Network**: Hierarchical road rendering (z-order: 3)
5. **Gradient Fades**: Top/bottom fade effects (z-order: 10)
6. **Typography**: City name, country, coordinates (z-order: 11)

### Road Hierarchy
Five-tier classification based on OSM highway tags:
- **Motorway**: Width 1.2 (highways)
- **Primary/Trunk**: Width 1.0 (major roads)
- **Secondary**: Width 0.8 (secondary roads)
- **Tertiary**: Width 0.6 (local roads)
- **Residential**: Width 0.4 (neighborhood streets)

### Output
- Generated posters saved to `maptoposter/posters/`
- Format: `{city}_{theme}_{timestamp}.png`
- Resolution: 300 DPI
- Customizable dimensions

## Technology Stack
- **Python 3.12**
- **OSMnx**: OpenStreetMap data fetching
- **Matplotlib**: Map visualization
- **GeoPandas**: Geospatial operations
- **Geopy**: Geocoding services
- **NumPy, Pandas, Shapely, NetworkX**: Data processing
