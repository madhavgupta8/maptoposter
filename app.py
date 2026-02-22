from flask import Flask, request, jsonify, send_from_directory, send_file
import subprocess
import sys
import os
import glob

app = Flask(__name__, static_folder='.', static_url_path='')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE_DIR, 'create_map_poster_hmi.py')
POSTERS_DIR = os.path.join(BASE_DIR, 'posters')


@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'hmi.html'))


@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    city = data.get('city', '').strip()
    country = data.get('country', '').strip()
    theme = data.get('theme', 'feature_based').strip()
    ratio = data.get('ratio', '3:4')
    no_small_roads = data.get('no_small_roads', True)

    try:
        radius = int(data.get('radius', 29000))
    except (ValueError, TypeError):
        radius = 29000

    if not city:
        return jsonify({'error': 'City is required'}), 400
    if not country:
        return jsonify({'error': 'Country is required'}), 400

    # Clamp radius to a sane range
    radius = max(1000, min(radius, 100000))

    ratio_map = {'3:4': (12, 16), '4:5': (12, 15)}
    W, H = ratio_map.get(ratio, (12, 16))

    cmd = [
        sys.executable,
        SCRIPT,
        '-c', city,
        '-C', country,
        '-t', theme,
        '-W', str(W),
        '-H', str(H),
        '-d', str(radius),
    ]
    if no_small_roads:
        cmd.append('--no-small-roads')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
        )
    except Exception as e:
        return jsonify({'error': f'Failed to run script: {str(e)}'}), 500

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or 'Script failed with no output'
        return jsonify({'error': error_msg}), 500

    # Find the most recently generated poster in nested dirs
    pattern = os.path.join(POSTERS_DIR, '**', '*.png')
    posters = sorted(
        glob.glob(pattern, recursive=True),
        key=os.path.getmtime,
        reverse=True
    )

    if not posters:
        return jsonify({'error': 'No output file found after generation'}), 500

    # Return path relative to POSTERS_DIR so the frontend can build the URL
    rel_path = os.path.relpath(posters[0], POSTERS_DIR)
    # Normalize to forward slashes for URLs
    rel_path = rel_path.replace(os.sep, '/')

    return jsonify({
        'success': True,
        'filepath': rel_path,
        'stdout': result.stdout,
    })


@app.route('/poster/<path:filepath>')
def serve_poster(filepath):
    return send_from_directory(POSTERS_DIR, filepath)


if __name__ == '__main__':
    print("=" * 50)
    print("Map Poster Generator — HMI Server")
    print("=" * 50)
    print(f"Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, port=5000)
