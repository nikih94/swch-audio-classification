from flask import Flask, request, jsonify
from queue import Queue
from waitress import serve

def create_app(request_queue: Queue) -> Flask:
    app = Flask(__name__)

    @app.route('/classification', methods=['POST'])
    def classification():
        # Extract form data.
        sensor_id = request.form.get('sensor_id')
        building = request.form.get('building')
        max_spl = request.form.get('max_spl')
        avg_spl = request.form.get('avg_spl')
        threshold = request.form.get('threshold')
        rec_seconds = request.form.get('rec_seconds')
        timestamp = request.form.get('timestamp')
        sample_rate = request.form.get('sample_rate')

        # Extract the file (audio recording).
        file_storage = request.files.get('file')
        audio_data = file_storage.read() if file_storage else None

        # Build a dictionary from the received data.
        data = {
            'sensor_id': sensor_id,
            'building': building,
            'max_spl': max_spl,
            'avg_spl': avg_spl,
            'threshold': threshold,
            'rec_seconds': rec_seconds,
            'sample_rate': int(sample_rate),
            'timestamp': timestamp,
            'audio': audio_data
        }
        # Place the data into the blocking queue.
        request_queue.put(data)
        # Respond with a JSON success message.
        return jsonify({"status": "success"}), 200

    return app

def start_server(request_queue: Queue) -> None:
    """
    Starts the Flask web server using Waitress on 127.0.0.1:42002.
    """
    app = create_app(request_queue)
    serve(app, host='0.0.0.0', port=42002)
