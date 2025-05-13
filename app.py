from flask import Flask, render_template, jsonify
from simulation import get_vehicle_states, update_simulation

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/state')
def state():
    update_simulation()
    return jsonify(get_vehicle_states())

if __name__ == '__main__':
    app.run(debug=True)
