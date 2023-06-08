from flask import Flask, jsonify, request, send_from_directory
import os
import json

app = Flask(__name__)

# Home page that serves the index.html file from the 'webserver' directory
@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

# API to get the file structure of midi_lib recursively
@app.route('/api/midi_lib', methods=['GET'])
def midi_lib_structure():
    def fetch_structure(path):
        tree = {}
        for item in os.scandir(path):
            if item.is_dir():
                tree[item.name] = fetch_structure(item.path)
            else:
                tree[item.name] = item.path
        return tree

    structure = fetch_structure('midi_lib')
    return jsonify(structure)

# API to list files in songs_lib
@app.route('/api/songs_lib', methods=['GET'])
def songs_lib():
    if not os.path.isdir('songs_lib'):
        return jsonify({'error': 'The specified path does not exist or is not a directory'}), 404

    content = os.listdir('songs_lib')
    return jsonify(content)

# API to get a song's JSON data from songs_lib
@app.route('/api/songs_lib/<song_filename>', methods=['GET'])
def get_song_content(song_filename):
    filepath = os.path.join('songs_lib', song_filename)

    if not os.path.isfile(filepath):
        return jsonify({'error': 'The specified file does not exist'}), 404

    with open(filepath, 'r') as f:
        content = json.load(f)

    return jsonify(content)


# API to save JSON file to songs_lib
@app.route('/api/songs_lib', methods=['POST'])
def save_to_songs_lib():
    data = request.json
    filename = request.args.get('filename', default = '', type = str)

    if filename == '':
        return jsonify({'error': 'You must specify a filename'}), 400

    with open(os.path.join('songs_lib', filename), 'w') as f:
        json.dump(data, f)

    return jsonify({'message': 'File saved successfully'})



if __name__ == '__main__':
    app.run(port=5000, debug=True)
