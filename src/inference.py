import concurrent.futures
import csv
import io
import os
import threading
import time
from contextlib import nullcontext

import librosa
import numpy as np
import torch
from torch import autocast

from helpers.utils import NAME_TO_WIDTH, labels
from models.dymn.model import get_model as get_dymn
from models.ensemble import get_ensemble_model
from models.mn.model import get_model as get_mobilenet
from models.preprocess import AugmentMelSTFT


class InferenceEngine:
    def __init__(
        self, model_name, ensemble, window_size, hop_size, result_queue, debug_mode=False
    ):
        self.model_name = model_name
        self.debug_mode = debug_mode
        self.model_reload_lock = threading.Lock()
        self.model = None
        self.class_names = None
        self.device = torch.device("cpu")
        self.mel = None

        # preprocessing parameters
        # hop size and windows size affect processing:
        # window size: chunk of the signal that will be processed at once
        # hop size: how much the window will move to perform the next processing step
        self.window_size = window_size
        self.hop_size = hop_size
        self.n_mels = 128
        self.strides = [2, 2, 2, 2]
        self.head_type = "mlp"
        self.ensemble = ensemble  # ["dymn20_as", "mn40_as_ext", "mn40_as"]

        self.result_queue = result_queue

        # Load the model initially.
        self.reload_model()

    def reload_model(self):
        with self.model_reload_lock:
            try:
                print("Reloading model...")
                if len(self.ensemble) > 0:
                    print("Loading ensemble:", self.ensemble)
                    new_model = get_ensemble_model(self.ensemble)
                else:
                    if self.model_name.startswith("dymn"):
                        print("Loading DyMN model:", self.model_name)
                        new_model = get_dymn(
                            width_mult=NAME_TO_WIDTH(self.model_name),
                            pretrained_name=self.model_name,
                            strides=self.strides,
                        )
                    else:
                        print("Loading MobileNet model:", self.model_name)
                        new_model = get_mobilenet(
                            width_mult=NAME_TO_WIDTH(self.model_name),
                            pretrained_name=self.model_name,
                            strides=self.strides,
                            head_type=self.head_type,
                        )
                new_model.to(self.device)
                new_model.eval()
                self.model = new_model
                print("Model reloaded successfully.")

                print("Model reloaded successfully.")
            except Exception as e:
                print("Error reloading model:", e)

    def inference_task(self, item):
        start_time = time.time()
        # model to preprocess waveform into mel spectrograms
        mel = AugmentMelSTFT(
            n_mels=self.n_mels,
            sr=item["sample_rate"],
            win_length=self.window_size,
            hopsize=self.hop_size,
            fmax=item["sample_rate"] / 2,
        )
        mel.to(self.device)
        mel.eval()

        pcm = np.frombuffer(item["audio"], dtype=np.int16)
        waveform = pcm.astype(np.float32) / 32768.0
        waveform = torch.from_numpy(waveform[None, :]).to(self.device)
        # inference
        with torch.no_grad():
            spec = mel(waveform)

        with self.model_reload_lock:
            with torch.no_grad():
                preds, features = self.model(spec.unsqueeze(0))

        # get the top class
        preds = torch.sigmoid(preds.float()).squeeze().cpu().numpy()
        sorted_indexes = np.argsort(preds)[::-1]

        top_idx = np.argmax(preds)
        top_label = labels[top_idx]
        top_prob = preds[top_idx]

        # measure the inference time
        end_time = time.time()

        item["result"] = top_label
        item["result_p"] = round(top_prob, 3)
        item["inference_time_ms"] = int((end_time - start_time) * 1000)
        del item["audio"]
        del item["sample_rate"]

        if self.debug_mode:
            print("audio processed",flush=True)
            print(item,flush=True)

        return item

    def handle_future(self, fut):
        """
        Callback to handle the result of an inference task.
        If an exception occurs, it reloads the model.
        """
        try:
            result = fut.result()
            self.result_queue.put(result)
        except Exception as e:
            print("Exception in inference task:", e)
            self.reload_model()

    def start_inference(self, request_queue):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                # Block until an item is available.
                item = request_queue.get()
                # Submit the inference task.
                future = executor.submit(self.inference_task, item)
                # Attach the callback for handling result or exception.
                future.add_done_callback(self.handle_future)
                # Indicate that the queued task is complete.
                request_queue.task_done()
