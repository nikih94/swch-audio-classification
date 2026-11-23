from queue import Queue

from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from waitress import serve

from metrics import registry


def create_app(request_queue: Queue, debug_mode: bool = False) -> Flask:
    app = Flask(__name__)

    @app.get("/metrics")
    def metrics():
        payload = generate_latest(registry)
        if debug_mode:
            print("--------------------------------------------------------------------",flush=True)
            print("Prometheuse metrics request received",flush=True)
            print(
                f"{request.method} /metrics request received\n{payload.decode('utf-8')}",
                end="",
                flush=True,
            )
        return Response(payload, content_type=CONTENT_TYPE_LATEST)

    @app.route("/ready", methods=["GET"])
    def ready():
        return jsonify({"status": "ready"}), 200

    @app.route("/classification", methods=["POST"])
    def classification():
        if debug_mode:
            print("--------------------------------------------------------------------",flush=True)
            print("Classification request received",flush=True)

        # Extract form data.
        sensor_id = request.form.get("sensor_id")
        building = request.form.get("building")
        max_spl = request.form.get("max_spl")
        avg_spl = request.form.get("avg_spl")
        threshold = request.form.get("threshold")
        rec_seconds = request.form.get("rec_seconds")
        timestamp = request.form.get("timestamp")
        sample_rate = request.form.get("sample_rate")

        # Extract the file (audio recording).
        file_storage = request.files.get("file")
        audio_data = file_storage.read() if file_storage else None

        errors = {}
        if not sensor_id or not sensor_id.strip():
            errors["sensor_id"] = "sensor_id is required."
        try:
            sample_rate = int(sample_rate)
            if sample_rate <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["sample_rate"] = "sample_rate is required and must be a positive integer."
        if not audio_data:
            errors["file"] = "A non-empty audio file is required."
        if errors:
            return jsonify({"status": "error", "errors": errors}), 400

        # Build a dictionary from the received data.
        data = {
            "sensor_id": sensor_id,
            "building": building,
            "max_spl": max_spl,
            "avg_spl": avg_spl,
            "threshold": threshold,
            "rec_seconds": rec_seconds,
            "sample_rate": sample_rate,
            "timestamp": timestamp,
            "audio": audio_data,
        }
        # Place the data into the blocking queue.
        request_queue.put(data)
        # Respond with a JSON success message.
        return jsonify({"status": "success"}), 200

    return app


def start_server(request_queue: Queue, debug_mode: bool = False) -> None:
    """
    Starts the Flask web server using Waitress on 127.0.0.1:42002.
    """
    app = create_app(request_queue, debug_mode)
    serve(app, host="0.0.0.0", port=42002)
