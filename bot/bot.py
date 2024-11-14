import logging
import threading
from typing import Callable, Dict, List, Optional, Union

import vk_api
from vk_api.longpoll import Event, VkEventType, VkLongPoll


class Bot:
    def __init__(self, token: str):
        self.token = token
        self.vk_session = vk_api.VkApi(token=token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
        self.handlers: List[Dict[str, Union[Callable, Dict]]] = []

    def listen(self):
        logging.info(
            "Starting listening in thread of " + threading.current_thread().name
        )
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.text.lower():
                        self._handle_event(event)
            except AssertionError as e:
                logging.info(
                    "Shutting down thread of " + threading.current_thread().name
                )
                exit(0)
            except Exception as e:
                logging.error(
                    "Unexpected error in thread of "
                    + threading.current_thread().name
                    + ": "
                    + str(e)
                )
                pass

    def _handle_event(self, event: Event):
        for handler in self.handlers:
            func = handler["func"]
            filters = handler["filters"]
            if self._apply_filters(event, filters):
                func(event)

    def _apply_filters(self, event: Event, filters: Dict) -> bool:
        if "peer_id" in filters and int(filters["peer_id"]) != event.peer_id:
            return False
        if "text" in filters and filters["text"].lower() != event.text.lower():
            return False
        if (
            (event.from_user or event.from_chat)
            and "user_id" in filters
            and int(filters["user_id"]) != event.user_id
        ):
            return False
        if (
            event.from_group
            and "group_id" in filters
            and abs(int(filters["group_id"])) != event.group_id
        ):
            return False
        if "custom_filters" in filters:
            for custom_filter in filters["custom_filters"]:
                if not custom_filter(event):
                    return False
        return True

    def message_handler(self, **filters):
        """
        Декоратор для обработки сообщений с заданными фильтрами.

        Args:
            **filters: Фильтры для обработки сообщений (peer_id, from_id, text, custom_filters).

        Returns:
            Callable: Декоратор для обработки сообщений.
        """
        custom_filters = filters.pop("custom_filters", [])

        def decorator(func: Callable) -> Callable:
            self.handlers.append(
                {"func": func, "filters": {**filters, "custom_filters": custom_filters}}
            )
            return func

        return decorator

    def get_msg_by_id(self, id: int) -> Dict:
        """
        Получает сообщение по его ID.

        Args:
            id (int): ID сообщения.

        Returns:
            Dict: Сообщение.
        """
        return self.vk_session.method(
            "messages.getById", {"message_ids": id, "access_token": self.token}
        )["items"][0]

    def send(
        self,
        chat: int,
        text: str,
        reply_id: Optional[int] = None,
        forward_messages: Optional[List[int]] = None,
    ) -> int:
        """
        Отправляет сообщение.

        Args:
            chat (int): ID чата.
            text (str): Текст сообщения.
            reply_id (Optional[int]): ID сообщения для ответа.
            forward_messages (Optional[List[int]]): Список ID сообщений для пересылки.

        Returns:
            int: ID отправленного сообщения.
        """
        return self.vk_session.method(
            "messages.send",
            {
                "peer_id": chat,
                "message": text,
                "random_id": 0,
                "reply_to": reply_id,
                "forward_messages": forward_messages,
            },
        )
