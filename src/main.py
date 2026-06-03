import sys
import threading
import time
import warnings
from queue import Queue

from configuration import load_config
from inference import InferenceEngine
from result_manager import ResultManager
from server import start_server

warnings.filterwarnings(
    "ignore",
    message="Don't use ConvNormActivation directly.*",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    message="Failed to load image Python extension.*",
    category=UserWarning,
)


def main():

    config_filename = "configuration.ini"
    config = load_config(config_filename)

    # Create a blocking queue to hold incoming classification requests.
    request_queue = Queue()
    # Create a blockin queue for inference results
    result_queue = Queue()

    # Start the web server in a separate thread.
    server_thread = threading.Thread(
        target=start_server,
        args=(request_queue, config.classification.debug_mode),
        daemon=True,
    )
    server_thread.start()

    # Instantiate the InferenceEngine with your parallelism settings.
    inference_engine = InferenceEngine(
        model_name=config.classification.model_name,
        ensemble=config.classification.ensemble,
        window_size=config.classification.window_size,
        hop_size=config.classification.hop_size,
        result_queue=result_queue,
        debug_mode=config.classification.debug_mode,
    )

    # Start the inference loop in a separate daemon thread.
    inference_thread = threading.Thread(
        target=inference_engine.start_inference, args=(request_queue,), daemon=True
    )
    inference_thread.start()

    # Instantiate and start the result manager.
    result_manager = ResultManager(
        result_queue, config.influx2, config.classification.debug_mode
    )
    result_manager_thread = threading.Thread(
        target=result_manager.start_result_manager, daemon=True
    )
    result_manager_thread.start()

    print("Server and inference workers are running. Waiting for requests...")
    # Main loop that monitors thread status.
    while True:
        if not (
            server_thread.is_alive()
            and inference_thread.is_alive()
            and result_manager_thread.is_alive()
        ):
            print("A thread has terminated. Exiting the application.")
            sys.exit(1)
        time.sleep(1)


if __name__ == "__main__":
    main()
