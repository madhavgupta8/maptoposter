# Kanpur Map Project - Commands Used

This document contains all the commands used to set up the project and generate the Kanpur map.

## 1. Create Project Directory

```bash
# Create the main project directory
mkdir -p kanpur_map_project && cd kanpur_map_project
```

## 2. Create Virtual Environment

```bash
# Create a Python virtual environment
python3 -m venv venv
```

## 3. Clone the Repository

```bash
# Clone the maptoposter repository from GitHub
git clone https://github.com/originalankur/maptoposter.git
```

## 4. Install Dependencies

```bash
# Navigate to the cloned repository and install required packages
cd maptoposter

# Activate the virtual environment
source ../venv/bin/activate

# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

## 5. Generate the Map

```bash
# Generate a map poster of Kanpur, India
# -c: City name
# -C: Country name
# -t: Theme (contrast_zones for urban density visualization)
# -d: Distance/radius in meters (18000m = 18km for large city coverage)
python create_map_poster.py -c "Kanpur" -C "India" -t contrast_zones -d 18000
```

## Output

The generated map is saved in:
```
maptoposter/posters/kanpur_contrast_zones_20260118_223911.png
```

## Additional Theme Options

You can generate maps with different themes by changing the `-t` parameter:

```bash
# List all available themes
python create_map_poster.py --list-themes

# Examples with different themes:
python create_map_poster.py -c "Kanpur" -C "India" -t noir -d 18000
python create_map_poster.py -c "Kanpur" -C "India" -t sunset -d 18000
python create_map_poster.py -c "Kanpur" -C "India" -t japanese_ink -d 18000
```

## Project Structure

```
kanpur_map_project/
├── venv/                    # Virtual environment
├── maptoposter/            # Cloned repository
│   ├── create_map_poster.py   # Main script
│   ├── requirements.txt       # Dependencies
│   ├── themes/               # Theme JSON files
│   ├── fonts/                # Font files
│   └── posters/              # Generated map posters
└── COMMANDS.md             # This file
```
