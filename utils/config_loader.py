import configparser
import hashlib
import os
from typing import Dict, Tuple


def load_configs(
    config_dir="configs",
) -> Dict[str, Tuple[configparser.ConfigParser, str]]:
    configs = {}
    for file in os.listdir(config_dir):
        if file.endswith(".ini"):
            config = configparser.ConfigParser()
            config.read(os.path.join(config_dir, file))
            configs[file] = config, calculate_hash(config)
    return configs


def calculate_hash(config: configparser.ConfigParser) -> str:
    hash_object = hashlib.sha256()

    # Проходимся по секциям и параметрам и добавляем их значения в хэш
    for section_name in config.sections():
        hash_object.update(section_name.encode("utf-8"))
        for key, value in config.items(section_name):
            hash_object.update(key.encode("utf-8"))
            hash_object.update(value.encode("utf-8"))
    return hash_object.hexdigest()
