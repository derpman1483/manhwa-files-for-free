from flask import Flask, render_template, jsonify, request  # type: ignore
from flask_socketio import SocketIO, emit  # type: ignore
from dotenv import load_dotenv  # type: ignore
import os
import json
import random
import pyperclip
# Assuming fetch.py contains 'load_json_data'
from fetch import load_json_data,get_last_num

load_dotenv()
name_id_dict = {}
chapters_dict = {}
# --- Data Loading ---
def get_manhwa_data():
    """Loads manhwa data from the JSON file."""
    try:
        # This function should return the dictionary under the "manhwa" key
        data = load_json_data()
        # It's now expected that data.get("manhwa") returns a DICTIONARY
        return data.get("manhwa", {})
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading manhwa data: {e}")
        return {}

# The variable is renamed to reflect it's a dictionary
manhwa_dict = get_manhwa_data()
ln = get_last_num()
for i in range(ln):
    name_id_dict[i+1] = manhwa_dict[str(i+1)]["name"]
    chapters_dict[manhwa_dict[str(i+1)]["name"]] = manhwa_dict[str(i+1)]["chapters"]
pyperclip.copy(str(name_id_dict))
# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_default_secret_key')
socketio = SocketIO(app)

# --- Route Definitions ---

@app.route('/')
def index():
    """Serves the main index.html page."""
    # Convert integer keys to strings for template rendering
    string_key_dict = {str(k): v for k, v in name_id_dict.items()}
    return render_template('index.html', **string_key_dict)

@app.route('/api/random')
def random_manhwa():
    """Returns a single random manhwa from the loaded data."""
    if not manhwa_dict:
        return jsonify({"error": "No manhwa data available"}), 500

    # Convert the dictionary's values into a list first
    manhwa_values = list(manhwa_dict.values())

    if not manhwa_values:
         return jsonify({"error": "Manhwa data is empty"}), 500

    # Make a random choice from the new list of values
    selected_manhwa = random.choice(manhwa_values)
    return jsonify(selected_manhwa)

@app.route('/manga/<slug>')
def manhwa_reader(slug):
    """Serves the manhwa reading page for a given manhwa slug."""
    # Find the manhwa by slug
    manhwa = None
    for m in manhwa_dict.values():
        if m.get('link', '').split('/')[-1] == slug or m.get('slug', '') == slug:
            manhwa = m
            break
    if not manhwa:
        return render_template('404.html'), 404
    # Pass manhwa info and chapters to the template
    return render_template('reader.html', manhwa=manhwa)

@app.route('/api/manga/<slug>/chapter/<chapter_num>')
def get_chapter_images(slug, chapter_num):
    """Returns the image URLs for a specific chapter of a manhwa."""
    # Find the manhwa by slug
    manhwa = None
    for m in manhwa_dict.values():
        if m.get('link', '').split('/')[-1] == slug or m.get('slug', '') == slug:
            manhwa = m
            break
    if not manhwa:
        return jsonify({'error': 'Manhwa not found'}), 404
    chapters = manhwa.get('chapters', {})
    # Try direct key
    chapter = chapters.get(chapter_num)
    # Try 'Chapter X' key
    if not chapter:
        chapter = chapters.get(f'Chapter {chapter_num}')
    # Try integer key
    if not chapter:
        try:
            chapter = chapters.get(int(chapter_num))
        except Exception:
            pass
    if not chapter:
        return jsonify({'error': 'Chapter not found'}), 404
    # If chapter is a dict with 'images', use that
    if isinstance(chapter, dict) and 'images' in chapter:
        images = chapter['images']
    # If chapter is a list, use it directly
    elif isinstance(chapter, list):
        images = chapter
    else:
        images = []
    if not images:
        return jsonify({'error': 'No images found for this chapter'}), 404
    return jsonify({'images': images})

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    socketio.emit("dict",(name_id_dict, chapters_dict))
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    print('Client disconnected')

@socketio.on('my event')
def handle_my_event(data):
    """Handles 'my event' and emits a response."""
    print('received json: ' + str(data))
    emit('my response', data)

# --- Main Execution ---

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8090, debug=True)