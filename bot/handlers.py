import configparser
import threading
from time import sleep
import re
from vk_api.longpoll import Event
import logging
from typing import Optional, List, Dict
from bot.bot import Bot
from bot.db import DatabaseHandler
import datetime
import pytz


class Settings:
    def __init__(
        self,
        global_config_path="bot/global_config.ini",
        pay=True,
        auction=True,
        autopost=False,
        track_fish=False,
        auto_store_items=False,
    ):
        self.global_config = configparser.ConfigParser()
        self.global_config.read(global_config_path)
        self.pay = pay
        self.auction = auction
        self.autopost = autopost
        self.track_fish = track_fish
        self.auto_store_items = auto_store_items


def autopost(bot, user_id, chat_id, parent_thread, settings, cooldown=10800):
    while parent_thread.is_alive():
        if settings.autopost:
            try:
                db = DatabaseHandler("data/database.db")
                autopost_text = db.get_autopost(user_id, chat_id)
                bot.send(chat_id, autopost_text)
            except Exception:
                pass
            sleep(cooldown)
        sleep(1)


def register_handlers(bot: Bot, config: configparser.ConfigParser):
    main_chat_id = int(config["PERSONAL"]["main_chat_id"])
    user_id = int(config["PERSONAL"]["user_id"])
    db = DatabaseHandler("data/database.db")

    db.add_user(user_id)
    db.add_autopost(user_id, main_chat_id)

    settings = Settings()
    autopost_thread = threading.Thread(
        target=autopost,
        args=(bot, user_id, main_chat_id, threading.current_thread(), settings),
    ).start()

    transfer_message = None

    # Проверка, что бот работает
    @bot.message_handler(text="пп", peer_id=user_id, user_id=user_id)
    def check(event: Event):
        bot.send(user_id, "Живой!")

    @bot.message_handler(text="инфо", peer_id=user_id, user_id=user_id)
    def get_settings(event: Event):
        bot.send(
            event.peer_id,
            (
                "ℹ Информация о состоянии бота\n\n"
                f"Id чата с автопостом: {main_chat_id}\n"
                f"Бот платит: {'✅' if settings.pay else '❌'}\n"
                f"Бот покупает с аукциона: {'✅' if settings.auction else '❌'}\n"
                f"Бот отправляет автопост: {'✅' if settings.autopost else '❌'}\n"
                f"Сбор игровой статистики: {'✅' if settings.track_fish else '❌'}\n"
                f"Автоматическое складирование: {'✅' if settings.auto_store_items else '❌'}\n\n"
                "Для помощи в настройке используйте команду Помощь"
            ),
        )

    @bot.message_handler(
        peer_id=user_id,
        custom_filters=[lambda event: event.text.lower().startswith("объявление\n")],
        user_id=user_id,
    )
    def update_autopost(event: Event):
        autopost_text = event.text.split("\n", 1)[1]
        db.update_autopost_text(user_id, main_chat_id, autopost_text)
        bot.send(user_id, "Объявление обновлено")

    @bot.message_handler(peer_id=user_id, text="спам", user_id=user_id)
    def send_autopost(event: Event):
        autopost_text = db.get_autopost(user_id, main_chat_id)
        if autopost_text:
            bot.send(event.peer_id, autopost_text)

    @bot.message_handler(text="стартспам", peer_id=user_id, user_id=user_id)
    def enable_autopost(event: Event):
        settings.autopost = True
        bot.send(user_id, "Автопост включён")

    @bot.message_handler(text="не спамим", peer_id=user_id, user_id=user_id)
    def disable_autopost(event: Event):
        settings.autopost = False
        bot.send(user_id, "Автопост отключен")

    @bot.message_handler(text="плати", peer_id=user_id, user_id=user_id)
    def enable_pay(event: Event):
        settings.pay = True
        bot.send(user_id, "Автооплата включена")

    @bot.message_handler(text="не плати", peer_id=user_id, user_id=user_id)
    def disable_pay(event: Event):
        settings.pay = False
        bot.send(user_id, "Автооплата отключена")

    @bot.message_handler(text="+аук", peer_id=user_id, user_id=user_id)
    def enable_auction(event: Event):
        settings.auction = True

    @bot.message_handler(text="-аук", peer_id=user_id, user_id=user_id)
    def disable_auction(event: Event):
        settings.auction = False

    @bot.message_handler(text="помощь", peer_id=user_id, user_id=user_id)
    def help(event: Event):
        help_text = (
            "Доступные команды:\n"
            "Пп - проверка, бот ответит, если работает\n"
            "Инфо - краткая информация о состоянии бота\n"
            "Стартспам - начать спамить объявление с кд в 3 часа\n"
            "Не спамим - прекратить спам объявления\n"
            "Не плати - отключает оплату в чате (на случай обменов и тп, НЕ ОТКЛЮЧАЕТ ЛОТЫ)\n"
            "Плати - включает обратно\n"
            "Скуп - выведет список скупа\n"
            "Объявление - с новой строки в том же сообщении текст автопоста\n"
            "Предмет <цена> <валюта> <полное название> - добавление предмета в скуп\n"
            "Удали <полное название> - удаляет предмет из скупа\n"
            "+аук или -аук - включает или отключает просмотр лотов\n"
            "+статистика или -статистика - включает или отключает сбор статистики\n"
            "Рыба за <количество> <период (дней/месяцев)> - вывести статистику по рыбалке. Использование команды требует включения статистики\n"
            "+склад или -склад - автоматическое складывание всех покупаемых предметов на склад (ТРЕБУЕТ НАЛИЧИЯ storage_chat_id В КОНФИГЕ)\n"
            "Выкл - выключить бота (не рекомендуется)"
        )
        bot.send(user_id, help_text)

    @bot.message_handler(text="выкл", peer_id=user_id, user_id=user_id)
    def shut_down(event: Event):
        bot.send(user_id, "Бот выключен")
        raise AssertionError("Bot shut down")

    # фильтр для регулярного выражения добавления предмета
    def add_item_command_filter(event: Event):
        pattern = r"предмет (\d+) (\w+) (.+)"
        match = re.match(pattern, event.text, re.IGNORECASE)
        if match:
            event.price = int(match.group(1))
            event.currency = match.group(2).lower()
            event.item_name = match.group(3).lower()
            return True
        return False

    @bot.message_handler(
        peer_id=user_id, custom_filters=[add_item_command_filter], user_id=user_id
    )
    def save_item(event: Event):
        db.add_item(user_id, event.item_name, event.price, event.currency)
        bot.send(
            user_id, f"{event.item_name} за {event.price} {event.currency} сохранен"
        )

    @bot.message_handler(
        peer_id=user_id,
        custom_filters=[lambda event: event.text.lower().startswith("удали")],
        user_id=user_id,
    )
    def delete_item(event: Event):
        item_name = event.text.split(" ", 1)[1]
        if db.delete_item(user_id, item_name) > 0:
            bot.send(user_id, f"{item_name} удален")
        else:
            bot.send(user_id, f"{item_name} не найден")

    @bot.message_handler(peer_id=user_id, text="скуп", user_id=user_id)
    def get_items(event: Event):
        items = db.get_items_by_user_id(user_id)
        if not items:
            bot.send(user_id, "Список пуст")
            return
        res = "Ваши предметы:\n\n"
        res += "\n".join(
            f"{key} - {price} {currency}" for key, (price, currency) in items.items()
        )
        bot.send(user_id, res)

    def get_mention(event: Event, bot: Bot = bot) -> Optional[dict]:
        msg = bot.get_msg_by_id(event.message_id)
        if msg.get("reply_message"):
            return msg["reply_message"]
        if len(msg["fwd_messages"]) > 0:
            return msg["fwd_messages"][0]
        return None

    def is_mention_of_the_user(
        event: Event, bot: Bot = bot, user_id: int = user_id
    ) -> bool:
        mention = get_mention(event, bot)
        return mention and mention["from_id"] == user_id

    @bot.message_handler(peer_id=main_chat_id, custom_filters=[is_mention_of_the_user])
    def remember_mention(event: Event):
        nonlocal transfer_message
        if event.text.lower().startswith("передать"):
            transfer_message = event

    def send_item(text: str) -> Optional[str]:
        items = {
            "факел": ["неп", "мб", "оше"],
            "молот": ["вс", "вл"],
            "меч": ["сл", "св"],
            "кинжал": ["лв", "лс"],
            "амулет": ["соб", "упо", "ини"],
            "пояс": ["вни", "вед", "фен"],
            "посох": ["рег", "рас", "уче"],
            "щит": ["уст", "неу", "про"],
        }

        text = text.lower().strip("/")
        parts = text.split()

        item_code = parts[0]
        quantity = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

        if item_code.startswith("д") and len(item_code) == 3:
            return f"передать доспех адмов ({item_code[1:].upper()})" + (
                f" - {quantity} штук" if quantity > 1 else ""
            )

        for key, values in items.items():
            if item_code in values:
                return f"передать {key} адмов ({item_code.upper()})" + (
                    f" - {quantity} штук" if quantity > 1 else ""
                )

        return None

    @bot.message_handler(
        user_id=user_id,
        custom_filters=[
            lambda event: get_mention(event) is not None and event.text.startswith("/")
        ],
    )
    def give_adm(event: Event):
        transfer_message = send_item(event.text)
        if transfer_message:
            bot.send(
                event.peer_id,
                transfer_message,
                forward_messages=get_mention(event)["id"],
            )

    # АВТООПЛАТА
    def parse_item_message(message):
        """
        Парсинг сообщения о передаче предмета.
        :param message: Текст сообщения.
        :return: Словарь с типом операции, количеством предметов, названием предмета,
                идентификатором отправителя и получателя.
        """
        # Регулярное выражение для парсинга сообщений
        item_regex = re.compile(
            r"(Получено|Отправлено):.{2}(\d*\*?)?(\S.+\S): \[id(\d+)\|[^]]+] =&gt; \[id(\d+)\|[^]]+]"
        )
        match = item_regex.match(message)
        if match:
            action, quantity, item_name, sender_id, receiver_id = match.groups()
            quantity = int(quantity[:-1]) if quantity and quantity.endswith("*") else 1
            return {
                "action": action,
                "quantity": quantity,
                "item_name": item_name.lower(),
                "sender_id": int(sender_id),
                "receiver_id": int(receiver_id),
            }
        return None

    def item_transfer_filter(event):
        """
        Фильтр для сообщений о передаче предметов.
        :param event: Ивент, содержащий сообщение.
        :return: True если сообщение соответствует шаблону, иначе False.
        """
        message_data = parse_item_message(event.text)
        if message_data:
            event.action = message_data["action"]
            event.quantity = message_data["quantity"]
            event.item_name = message_data["item_name"]
            event.sender_id = message_data["sender_id"]
            event.receiver_id = message_data["receiver_id"]
            return True
        return False

    @bot.message_handler(
        group_id=settings.global_config["CONSTANTS"]["game_group_id"],
        custom_filters=[item_transfer_filter],
    )
    def handle_item_transfer(event: Event):
        if event.action == "Получено":
            if (
                transfer_message
                and transfer_message.user_id == event.sender_id
                and settings.pay
            ):
                item = db.get_items_by_user_id(user_id).get(event.item_name)
                if item:
                    price, currency = item
                    bot.send(
                        transfer_message.peer_id,
                        f"Передать {event.quantity * price} {currency}",
                        transfer_message.message_id,
                    )
                    bot.send(
                        user_id,
                        f"Заплачено {event.quantity * price} {currency} за {event.quantity} {event.item_name}",
                    )
                    # АВТОСКЛАД
                    if settings.auto_store_items:

                        def delayed_send(delay=10):
                            sleep(delay)
                            bot.send(
                                int(config["PERSONAL"]["storage_chat_id"]),
                                f"положить {event.item_name} - {event.quantity} штук",
                            )

                        threading.Thread(target=delayed_send).start()

    @bot.message_handler(
        user_id=settings.global_config["CONSTANTS"]["transfer_bot_id"],
        custom_filters=[
            lambda event: "продает через аукцион" in event.text.lower()
            and settings.auction
        ],
    )
    def handle_auction(event: Event):
        pattern = re.compile(
            r"(\d+)\s*\*\s*([^\*-]+?)\s*-\s*(\d+)\s*золота\s*\((\d+)\)"
        )
        lines = event.text.lower().split("\n")
        for line in lines:
            match = pattern.search(line)
            if match:
                try:
                    mult = int(match.group(1))
                    item = match.group(2).strip()
                    total_price = int(match.group(3))
                    lot_id = match.group(4)
                    items = db.get_items_by_user_id(user_id)
                    if item not in items.keys():
                        continue

                    price, currency = items[item]
                    if price >= total_price / mult:
                        bot.send(
                            int(settings.global_config["CONSTANTS"]["game_group_id"]),
                            f"купить лот {lot_id}",
                        )
                except (ValueError, IndexError) as e:
                    continue

    @bot.message_handler(
        group_id=settings.global_config["CONSTANTS"]["game_group_id"],
        custom_filters=[
            lambda event: "вы готовитесь к рыбалке" in event.text.lower()
            and settings.track_fish
        ],
    )
    def log_fish_start(event: Event):
        db.add_stat(user_id, event.timestamp, "FISHING_START")

    @bot.message_handler(
        group_id=settings.global_config["CONSTANTS"]["game_group_id"],
        custom_filters=[
            lambda event: "карта озера активирована" in event.text.lower()
            and settings.track_fish
        ],
    )
    def log_fish_end(event: Event):
        db.add_stat(user_id, event.timestamp, "FISHING_MAP_ACTIVATED")

    @bot.message_handler(
        group_id=settings.global_config["CONSTANTS"]["game_group_id"],
        custom_filters=[
            lambda event: "вы успешно выловили рыбу!" in event.text.lower()
            and settings.track_fish
        ],
    )
    def get_fish_weight(event: Event):
        match = re.search(r"\(([\d.]+)\s*кг\).*в\s(\d+)\sзолота", event.text)
        if match:
            db.add_stat(user_id, event.timestamp, "FISH_WEIGHT", match.group(1))
            db.add_stat(user_id, event.timestamp, "FISH_PRICE", match.group(2))

    @bot.message_handler(
        peer_id=user_id,
        user_id=user_id,
        custom_filters=[
            lambda event: "рыба за" in event.text.lower() and settings.track_fish
        ],
    )
    def get_statistics(event: Event):
        stats = (
            db.get_all_stats()
        )  # -> List[Tuple[int, int, str, str, Optional[str]]] - (id, user_id, date, type, value(optional))

        # Парсинг периода
        period_match = re.search(
            r"рыба за (\d+)\s*(день|дня|дней|месяца|месяцев|месяц)", event.text.lower()
        )
        # if not period_match:
        #     bot.send(user_id, "Не удалось распознать период.")

        quantity = int(period_match.group(1))
        period_type = period_match.group(2)

        if "месяц" in period_type:
            period = datetime.timedelta(days=30 * quantity)
        else:
            period = datetime.timedelta(days=quantity)

        # Определение границ периода
        end_date = datetime.datetime.now(pytz.timezone("Europe/Moscow"))
        start_date = end_date - period

        # Переменные для накопления статистики
        fish_start_count = 0
        fish_map_count = 0
        total_weight = 0.0
        total_price = 0
        weight_count = 0
        price_count = 0

        # Проход по отфильтрованной статистике
        for stat in stats:
            _, stat_user_id, stat_date, stat_type, stat_value = stat

            if stat_user_id != user_id:
                continue

            stat_datetime = pytz.timezone("Europe/Moscow").localize(
                datetime.datetime.fromisoformat(stat_date)
            )
            if not (start_date <= stat_datetime <= end_date):
                continue

            if stat_type == "FISHING_START":
                fish_start_count += 1
            elif stat_type == "FISHING_MAP_ACTIVATED":
                fish_map_count += 1
            elif stat_type == "FISH_WEIGHT" and stat_value:
                total_weight += float(stat_value)
                weight_count += 1
            elif stat_type == "FISH_PRICE" and stat_value:
                total_price += int(stat_value)
                price_count += 1

        # Вычисление средних значений
        avg_weight = (total_weight / weight_count) if weight_count else 0
        avg_price = (total_price / price_count) if price_count else 0

        # Формирование ответа
        response = (
            f"Ваша статистика за {quantity} {period_type}:\n"
            f"Всего рыбалок: {fish_start_count}\n"
            f"Рыбалок по картам: {fish_map_count}\n"
            f"Общий вес рыбы за этот период: {total_weight:.2f} кг\n"
            f"Общая цена рыбы за этот период: {total_price} золота\n"
            f"Средний вес рыбы: {avg_weight:.2f} кг\n"
            f"Средняя цена рыбы: {avg_price:.2f} золота"
        )
        bot.send(user_id, response)

    @bot.message_handler(text="+статистика", peer_id=user_id, user_id=user_id)
    def stats_on(event: Event):
        settings.track_fish = True
        bot.send(
            user_id,
            "Сбор игровой статистики запущен. Команды работы со статистикой доступны.",
        )

    @bot.message_handler(text="-статистика", peer_id=user_id, user_id=user_id)
    def stats_off(event: Event):
        settings.track_fish = False
        bot.send(
            user_id,
            "Сбор игровой статистики остановлен. Команды работы со статистикой больше недоступны.",
        )

    @bot.message_handler(text="+склад", peer_id=user_id, user_id=user_id)
    def stats_on(event: Event):
        if config.has_option("PERSONAL", "storage_chat_id"):
            settings.auto_store_items = True
            bot.send(
                user_id,
                "Автоматическая разгрузка предметов в склад включена",
            )
        else:
            bot.send(
                user_id,
                "Внимание, работа с данной командой возможна только при наличии поля storage_chat_id в вашем конфиге.\n Добавьте поле в конфиг и повторите попытку",
            )

    @bot.message_handler(text="-склад", peer_id=user_id, user_id=user_id)
    def stats_off(event: Event):
        if config.has_option("PERSONAL", "storage_chat_id"):
            settings.auto_store_items = False
            bot.send(
                user_id,
                "Автоматическая разгрузка предметов в склад отключена",
            )
        else:
            bot.send(
                user_id,
                "Внимание, работа с данной командой возможна только при наличии поля storage_chat_id в вашем конфиге.\nДобавьте поле в конфиг и повторите попытку",
            )

    @bot.message_handler(
        group_id=settings.global_config["CONSTANTS"]["game_group_id"],
        custom_filters=[
            lambda event: "успешно приобрели с аукциона предмет" in event.text.lower()
            and settings.auto_store_items
        ],
    )
    def auction_item_bought(event: Event):
        pattern = r"\[id(\d+)\|.*?\], Вы успешно приобрели с аукциона предмет (\d+)\*(.+?)\s*-\s*\d+ золота потрачено"
        match = re.search(pattern, event.text)
        if match:
            buyer_id = int(match.group(1))
            quantity = int(match.group(2))
            item_name = match.group(3).lower()
            if buyer_id == user_id:
                bot.send(
                    int(config["PERSONAL"]["storage_chat_id"]),
                    f"положить {item_name} - {quantity} штук",
                )
