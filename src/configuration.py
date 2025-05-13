# configuration.py

import configparser
from dataclasses import dataclass

@dataclass
class ClassificationConfig:
    model_name: str
    window_size: int
    hop_size: int

@dataclass
class Influx2Config:
    url: str
    org: str
    token: str
    log_bucket: str
    data_bucket: str

@dataclass
class AppConfig:
    classification: ClassificationConfig
    influx2: Influx2Config

def load_config(filename: str) -> AppConfig:
    """Reads the INI file and returns an AppConfig object."""
    parser = configparser.ConfigParser()
    parser.read(filename)

    classification = ClassificationConfig(
        model_name=parser.get('classification', 'model_name'),
        window_size=parser.getint('classification', 'window_size'),
        hop_size=parser.getint('classification', 'hop_size'),
    )

    influx2 = Influx2Config(
        url=parser.get('influx2', 'url'),
        org=parser.get('influx2', 'org'),
        token=parser.get('influx2', 'token'),
        log_bucket=parser.get('influx2', 'log_bucket'),
        data_bucket=parser.get('influx2', 'data_bucket')
    )

    return AppConfig(classification=classification, influx2=influx2)
