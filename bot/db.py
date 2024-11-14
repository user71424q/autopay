import sqlite3
import sqlite3
from sqlite3 import Connection, Cursor
from typing import Optional, List, Tuple, Dict, Any
import datetime


class DatabaseHandler:
    def __init__(self, db_name: str = "data/database.db"):
        """
        Инициализация DatabaseHandler с именем базы данных.

        :param db_name: Имя SQLite файла базы данных.
        """
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self) -> None:
        """
        Создание таблиц User, Autopost, Items и Stats в базе данных, если они еще не созданы.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS User (
                    user_id INTEGER PRIMARY KEY NOT NULL
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Autopost (
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    text TEXT,
                    PRIMARY KEY (user_id, chat_id),
                    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Items (
                    user_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    PRIMARY KEY (user_id, item_name),
                    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Stats (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    user_id INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    type TEXT NOT NULL,
                    text TEXT,
                    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
                )
            """
            )
            conn.commit()

    def _get_connection(self) -> Connection:
        """
        Получение соединения с базой данных с включенной поддержкой внешних ключей.

        :return: Объект соединения с базой данных.
        """
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def add_user(self, user_id: int) -> int:
        """
        Добавление пользователя в таблицу User.

        :param user_id: Идентификатор пользователя.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO User (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            return cursor.lastrowid

    def delete_user(self, user_id: int) -> int:
        """
        Удаление пользователя из таблицы User.

        :param user_id: Идентификатор пользователя.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM User WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount

    def add_autopost(
        self, user_id: int, chat_id: int, text: Optional[str] = None
    ) -> int:
        """
        Добавление записи в таблицу Autopost.

        :param user_id: Идентификатор пользователя.
        :param chat_id: Идентификатор чата.
        :param text: Текст автопоста.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO Autopost (user_id, chat_id, text) VALUES (?, ?, ?)",
                (user_id, chat_id, text),
            )
            conn.commit()
            return cursor.lastrowid

    def delete_autopost(self, user_id: int, chat_id: int) -> int:
        """
        Удаление записи из таблицы Autopost.

        :param user_id: Идентификатор пользователя.
        :param chat_id: Идентификатор чата.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Autopost WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            )
            conn.commit()
            return cursor.rowcount

    def add_item(self, user_id: int, item_name: str, price: int, currency: str) -> int:
        """
        Добавление записи в таблицу Items.

        :param user_id: Идентификатор пользователя.
        :param item_name: Название предмета.
        :param price: Цена предмета.
        :param currency: Валюта.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO Items (user_id, item_name, price, currency) VALUES (?, ?, ?, ?)",
                (user_id, item_name, price, currency),
            )
            conn.commit()
            return cursor.lastrowid

    def delete_item(self, user_id: int, item_name: str) -> int:
        """
        Удаление записи из таблицы Items.

        :param user_id: Идентификатор пользователя.
        :param item_name: Название предмета.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Items WHERE user_id = ? AND item_name = ?",
                (user_id, item_name),
            )
            conn.commit()
            return cursor.rowcount

    def add_stat(
        self, user_id: int, timestamp: int, type: str, text: Optional[str] = None
    ) -> int:
        """
        Добавление записи в таблицу Stats.

        :param user_id: Идентификатор пользователя.
        :param timestamp: Временная метка в виде int.
        :param text: Текст статистики.
        :param type: Тип статистики.
        """
        datetime_str = self.convert_timestamp(timestamp)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO Stats (user_id, timestamp, text, type) VALUES (?, ?, ?, ?)",
                (user_id, datetime_str, text, type),
            )
            conn.commit()
            return cursor.lastrowid

    def delete_stat(self, stat_id: int) -> int:
        """
        Удаление записи из таблицы Stats.

        :param stat_id: Идентификатор статистики.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Stats WHERE stat_id = ?", (stat_id,))
            conn.commit()
            return cursor.rowcount

    def update_stat(self, stat_id: int, text: str, type: Optional[str] = None) -> None:
        """
        Обновление текста и типа записи в таблице Stats.

        :param stat_id: Идентификатор статистики.
        :param text: Новый текст статистики.
        :param type: Новый тип статистики.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Stats SET text = ?, type = ? WHERE stat_id = ?",
                (text, type, stat_id),
            )
            conn.commit()

    def update_autopost_text(self, user_id: int, chat_id: int, new_text: str) -> None:
        """
        Обновление текста записи в таблице Autopost.

        :param user_id: Идентификатор пользователя.
        :param chat_id: Идентификатор чата.
        :param new_text: Новый текст автопоста.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Autopost SET text = ? WHERE user_id = ? AND chat_id = ?",
                (new_text, user_id, chat_id),
            )
            conn.commit()

    def update_item_price(self, user_id: int, item_name: str, new_price: int) -> None:
        """
        Обновление цены записи в таблице Items.

        :param user_id: Идентификатор пользователя.
        :param item_name: Название предмета.
        :param new_price: Новая цена.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Items SET price = ? WHERE user_id = ? AND item_name = ?",
                (new_price, user_id, item_name),
            )
            conn.commit()

    def clear_table(self, table_name: str) -> None:
        """
        Очистка таблицы без удаления.

        :param table_name: Название таблицы.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")
            conn.commit()

    def get_all_users(self) -> List[Tuple[int]]:
        """
        Получение всех пользователей.

        :return: Список кортежей с данными всех пользователей.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User")
            return cursor.fetchall()

    def get_all_autoposts(self) -> List[Tuple[int, int, Optional[str]]]:
        """
        Получение всех автопостов.

        :return: Список кортежей с данными всех автопостов.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Autopost")
            return cursor.fetchall()

    def get_all_items(self) -> List[Tuple[int, str, int, str]]:
        """
        Получение всех предметов.

        :return: Список кортежей с данными всех предметов.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Items")
            return cursor.fetchall()

    def get_all_stats(self) -> List[Tuple[int, int, str, str, Optional[str]]]:
        """
        Получение всех статистик.

        :return: Список кортежей с данными всех статистик.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Stats")
            return cursor.fetchall()

    def get_items_by_user_id(self, user_id: int) -> Dict[str, Tuple[int, str]]:
        """
        Получение всех предметов по идентификатору пользователя.

        :param user_id: Идентификатор пользователя.
        :return: Словарь предметов, где ключ - название предмета, значение - кортеж (цена, валюта).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT item_name, price, currency FROM Items WHERE user_id = ?",
                (user_id,),
            )
            items = cursor.fetchall()
            return {
                item_name: (price, currency) for item_name, price, currency in items
            }

    def get_autopost(self, user_id: int, chat_id: int) -> Optional[str]:
        """
        Получение текста автопоста по идентификатору пользователя и чата.

        :param user_id: Идентификатор пользователя.
        :param chat_id: Идентификатор чата.
        :return: Текст автопоста или None, если запись не найдена.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT text FROM Autopost WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def convert_timestamp(self, timestamp: int) -> str:
        """
        Конвертация timestamp в формат даты и времени.

        :param timestamp: Временная метка.
        :return: Дата и время в формате строки.
        """
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    db = DatabaseHandler("data/database.db")
    cursor = db._get_connection().cursor()
    cursor.execute("DROP TABLE STATS")
    db._get_connection().commit()
