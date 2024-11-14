import ctypes
import threading
import time
import logging
import os
from bot import Bot, register_handlers
from utils import calculate_hash, load_configs


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="bot.log",
    filemode="w",
)


def start_bot(config, filename, thread_map):
    token = config["PERSONAL"]["token"]
    bot = Bot(token)

    # Регистрация хендлеров
    register_handlers(bot, config)

    bot.listen()


if __name__ == "__main__":
    configs = load_configs()
    threads = {}

    for filename, config_info in configs.items():
        config, hash = config_info
        thread = threading.Thread(
            target=start_bot,
            args=(config, filename, threads),
            name=filename.removesuffix(".ini"),
        )
        thread.start()
        threads[filename] = {"thread": thread, "hash": hash}

    # Проверка на новые конфиги и запуск ботов для них
    while True:
        time.sleep(5)  # Проверка каждую минуту
        new_configs = load_configs()
        new_files = set(new_configs.keys()) - set(configs.keys())

        # Обработка новых config-файлов
        for new_file in new_files:
            logging.info(f"Config '{new_file}' added. Starting new bot...")
            new_config_info = new_configs[new_file]
            new_config, new_hash = new_config_info
            thread = threading.Thread(
                target=start_bot,
                args=(new_config, new_file, threads),
                name=new_file.removesuffix(".ini"),
            )
            thread.start()
            threads[new_file] = {"thread": thread, "hash": new_hash}

        same_config_files = set(configs.keys()) & set(new_configs.keys())
        for same_file in same_config_files:
            new_config_info = new_configs[same_file]
            new_config, new_hash = new_config_info
            if new_hash != threads[same_file]["hash"]:
                logging.info(f"Config '{same_file}' updated. Restarting bot...")
                threads[same_file]["hash"] = new_hash
                id = threads[same_file]["thread"].ident
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(id), ctypes.py_object(AssertionError)
                )
                new_thread = threading.Thread(
                    target=start_bot,
                    args=(new_config, same_file, threads),
                    name=same_file.removesuffix(".ini"),
                )
                threads[same_file]["thread"] = new_thread
                new_thread.start()

        configs = new_configs
