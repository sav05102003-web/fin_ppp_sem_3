"""Проверки реальных обработчиков PTB с подменой только сетевого транспорта."""

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram import Update
from telegram.error import Forbidden, NetworkError, RetryAfter
from telegram.request import BaseRequest

from src.assistant import CookingAssistant
from src.bot import build_application, deliver_timers, post_init, split_message
from src.storage import Storage


class FakeTelegramRequest(BaseRequest):
    """Эмулировать ответы Bot API без внешнего соединения."""

    def __init__(self) -> None:
        self.calls = []

    @property
    def read_timeout(self) -> float:
        """Вернуть формальный таймаут интерфейса BaseRequest."""
        return 5.0

    async def initialize(self) -> None:
        """Открытие тестового транспорта не требует ресурсов."""

    async def shutdown(self) -> None:
        """Закрытие тестового транспорта не требует ресурсов."""

    async def do_request(self, url, method, request_data=None, **kwargs):
        """Вернуть совместимые с Telegram ответы getMe и sendMessage."""
        endpoint = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.calls.append((endpoint, params))
        if endpoint == "getMe":
            result = {"id": 999, "is_bot": True, "first_name": "Кулинар",
                      "username": "cooking_test_bot"}
        elif endpoint == "sendMessage":
            result = {"message_id": len(self.calls), "date": 1,
                      "chat": {"id": params["chat_id"], "type": "private"},
                      "text": params["text"]}
        else:
            result = True
        return 200, json.dumps({"ok": True, "result": result}).encode()


class BotTests(unittest.IsolatedAsyncioTestCase):
    """Проверять маршрутизацию Telegram и результаты доставки уведомлений."""

    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.assistant = CookingAssistant(
            Storage(Path(self.temp.name) / "users.sqlite3"), lambda: 1000,
        )
        self.transport = FakeTelegramRequest()
        self.app = build_application(
            "123456:" + "a" * 35, self.assistant, self.transport,
        )

    async def send_update(
        self, text: str | None, chat_type: str = "private",
    ) -> str:
        """Передать настоящий Update в Application.process_update."""
        message = {
            "message_id": 1, "date": 1,
            "from": {"id": 1, "is_bot": False, "first_name": "Студент"},
            "chat": {"id": 1, "type": chat_type},
        }
        if text is not None:
            message["text"] = text
        else:
            message["photo"] = [{"file_id": "x", "file_unique_id": "x",
                                 "width": 10, "height": 10}]
        async with self.app:
            update = Update.de_json(
                {"update_id": 1, "message": message}, self.app.bot)
            await self.app.process_update(update)
        replies = [params["text"] for method, params in self.transport.calls
                   if method == "sendMessage"]
        return "\n".join(replies)

    async def test_command_goes_through_real_application(self) -> None:
        result = await self.send_update("/find рис, морковь, перец")
        self.assertIn("Рис с овощами", result)
        reply = next(p for m, p in self.transport.calls if m == "sendMessage")
        self.assertIn("reply_markup", reply)

    async def test_reply_keyboard_button(self) -> None:
        self.assertIn("Меню пусто", await self.send_update("📅 Меню"))

    async def test_group_does_not_access_personal_data(self) -> None:
        result = await self.send_update("/plan авто", "group")
        self.assertIn("личный чат", result)
        self.assertEqual(self.assistant.storage.menu(
            1, self.assistant.week()), [])

    async def test_media_has_helpful_response(self) -> None:
        self.assertIn("текстом", await self.send_update(None))

    async def test_register_commands_and_periodic_job(self) -> None:
        async with self.app:
            await post_init(self.app)
        self.assertTrue(any(m == "setMyCommands" for m,
                        _ in self.transport.calls))
        jobs = self.app.job_queue.get_jobs_by_name("saved-cooking-timers")
        self.assertEqual(len(jobs), 1)

    async def test_real_scheduler_delivers_overdue_timer(self) -> None:
        self.assistant.storage.add_timer(1, 1, "Суп", 999)
        async with self.app:
            await post_init(self.app)
            await self.app.start()
            try:
                for _ in range(40):
                    if not self.assistant.storage.timers(1):
                        break
                    await asyncio.sleep(0.05)
            finally:
                await self.app.stop()
        messages = [p["text"] for method, p in self.transport.calls
                    if method == "sendMessage"]
        self.assertEqual(len(messages), 1)
        self.assertIn("Суп. Время вышло!", messages[0])

    async def test_successful_timer_is_not_sent_twice(self) -> None:
        self.assistant.storage.add_timer(1, 1, "Суп", 999)
        bot = SimpleNamespace(send_message=AsyncMock())
        context = SimpleNamespace(
            bot_data={"assistant": self.assistant}, bot=bot)
        await deliver_timers(context)
        await deliver_timers(context)
        bot.send_message.assert_awaited_once()
        self.assertEqual(self.assistant.storage.timers(1), [])

    async def test_network_error_retries_without_losing_timer(self) -> None:
        self.assistant.storage.add_timer(1, 1, "Суп", 999)
        bot = SimpleNamespace(send_message=AsyncMock(
            side_effect=NetworkError("offline")))
        context = SimpleNamespace(
            bot_data={"assistant": self.assistant}, bot=bot)
        await deliver_timers(context)
        self.assertEqual(len(self.assistant.storage.timers(1)), 1)
        self.assertEqual(self.assistant.storage.due_timers(1000), [])
        self.assertEqual(len(self.assistant.storage.due_timers(1030)), 1)

    async def test_forbidden_stops_retries(self) -> None:
        self.assistant.storage.add_timer(1, 1, "Суп", 999)
        bot = SimpleNamespace(send_message=AsyncMock(
            side_effect=Forbidden("blocked")))
        context = SimpleNamespace(
            bot_data={"assistant": self.assistant}, bot=bot)
        await deliver_timers(context)
        self.assertEqual(self.assistant.storage.timers(1), [])

    async def test_retry_after_is_respected(self) -> None:
        self.assistant.storage.add_timer(1, 1, "Суп", 999)
        bot = SimpleNamespace(
            send_message=AsyncMock(side_effect=RetryAfter(90)))
        context = SimpleNamespace(
            bot_data={"assistant": self.assistant}, bot=bot)
        await deliver_timers(context)
        self.assertEqual(self.assistant.storage.due_timers(1089), [])
        self.assertEqual(len(self.assistant.storage.due_timers(1090)), 1)

    def test_message_splitting(self) -> None:
        original = ("Длинная строка\n" * 700).rstrip("\n")
        chunks = split_message(original)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(part) <= 3900 for part in chunks))
        self.assertEqual("\n".join(chunks), original)


if __name__ == "__main__":
    unittest.main()
