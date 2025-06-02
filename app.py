from flask import Flask, jsonify, send_from_directory, render_template
from flask_cors import CORS
from simulation import update_simulation, get_vehicle_states
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/state')
def state():
    update_simulation()
    return jsonify(get_vehicle_states())

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True)
