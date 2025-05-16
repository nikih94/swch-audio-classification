import concurrent.futures
import time
from queue import Empty
from influxdb_client import InfluxDBClient, Point
from influxdb_client .client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
import datetime

class ResultManager:
    def __init__(self, result_queue, influx2_config):
        self.result_queue = result_queue
        self.influx2_config = influx2_config
        self.url=self.influx2_config.url
        self.token=self.influx2_config.token
        self.org=self.influx2_config.org
        self.bucket=self.influx2_config.data_bucket

        self.influx_client = None
        self.write_api = None

        self.retries = 0
        #intialize influxd client
        self.initialize_influx_client()

    def initialize_influx_client(self):
        self.influx_client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)


    def process_result(self, result):
        try:
            p = Point("classification").tag("building",result['building']) \
            .tag("sensor_id",result['sensor_id']) \
            .field("max_spl",float(result['max_spl'])) \
            .field("avg_spl",float(result['avg_spl'])) \
            .field("threshold",float(result['threshold'])) \
            .field("result",result['result']) \
            .field("result_p",float(result['result_p'])) \
            .field('inference_time_ms',int(result['inference_time_ms'])) \
            .time(datetime.datetime.utcfromtimestamp(int(result['timestamp'])))

            self.write_api.write(bucket=self.bucket, record=p)
            self.retries = 0

            #print("result: ", result)
            #print("sent to influx: ",result['result'])
        except Exception as e:
            self.retries+=1
            print(e)
            if self.retries > 5:
                self.initialize_influx_client()
                self.retries = 0


    def start_result_manager(self, max_workers=1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                # This call blocks indefinitely until a result item is available.
                result_item = self.result_queue.get()
                # Submit the result processing task.
                future = executor.submit(self.process_result, result_item)
                # When the task is complete, mark the result as done.
                future.add_done_callback(lambda fut: self.result_queue.task_done())
