"""Проверка безопасной загрузки настроек и приоритетов переменных среды."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import config


class ConfigTests(unittest.TestCase):
    """Проверять настройки с временным .env без настоящего токена."""

    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.token = "123456:" + "a" * 35
        self.project_patch = patch.object(config, "PROJECT_DIR", self.folder)
        self.project_patch.start()
        self.addCleanup(self.project_patch.stop)
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def write_env(self, value: str) -> None:
        """Записать временный файл настроек с указанным содержимым."""
        (self.folder / ".env").write_text(value, encoding="utf-8")

    def test_missing_token_explains_setup(self) -> None:
        with self.assertRaisesRegex(ValueError, "BotFather"):
            config.load_settings()

    def test_quoted_token_and_relative_database(self) -> None:
        self.write_env(
            f'# Настройки\nBOT_TOKEN="{self.token}"\n'
            'BOT_DB_PATH=db/test.sqlite3'
        )
        token, path = config.load_settings()
        self.assertEqual(token, self.token)
        self.assertEqual(path, self.folder / "db/test.sqlite3")

    def test_environment_overrides_file(self) -> None:
        self.write_env("BOT_TOKEN=invalid\nBOT_DB_PATH=other.sqlite3")
        values = {"BOT_TOKEN": self.token, "BOT_DB_PATH": "own.sqlite3"}
        with patch.dict(os.environ, values):
            token, path = config.load_settings()
        self.assertEqual(token, self.token)
        self.assertEqual(path, self.folder / "own.sqlite3")

    def test_error_does_not_reveal_secret(self) -> None:
        secret = "this-is-an-invalid-private-token"
        self.write_env("BOT_TOKEN=" + secret)
        with self.assertRaises(ValueError) as result:
            config.load_settings()
        self.assertNotIn(secret, str(result.exception))

    def test_malformed_file_is_rejected(self) -> None:
        invalid = ('BOT_TOKEN="unclosed', "UNKNOWN=anything", "BOT_TOKEN")
        for content in invalid:
            self.write_env(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                config.load_settings()


if __name__ == "__main__":
    unittest.main()
