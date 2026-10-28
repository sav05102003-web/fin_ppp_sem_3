"""Проверки поиска, пищевых ограничений, меню, покупок и таймеров."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from src.assistant import CookingAssistant, parse_duration
from src.catalogue import DIETS, MEALS, load_recipes, parse_ingredients, search
from src.storage import Storage


class AssistantTests(unittest.TestCase):
    """Проверять пользовательские сценарии в отдельных временных базах."""

    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "users.sqlite3"
        self.timestamp = datetime(
            2026, 10, 28, 12, tzinfo=timezone.utc).timestamp()
        self.assistant = CookingAssistant(
            Storage(self.path), lambda: self.timestamp)

    def command(self, text: str, user: int = 1) -> str:
        """Выполнить команду в собственном чате выбранного пользователя."""
        return self.assistant.execute(user, user, text)

    def test_catalogue_and_unique_ids(self) -> None:
        recipes = load_recipes()
        self.assertEqual(len(recipes), 14)
        self.assertEqual(len({r.id for r in recipes}), 14)
        for diet in DIETS:
            self.command("/diet " + diet)
            self.assertIn("Меню недели", self.command("/plan авто"))
            self.assertEqual(
                len(self.assistant.storage.menu(1, "2026-10-26")), 21)

    def test_aliases_and_deduplication(self) -> None:
        self.assertEqual(
            parse_ingredients(" Помидоры, томат; Яйца, курица "),
            ("помидор", "яйцо", "куриное филе"),
        )

    def test_search_ranks_complete_recipe_first(self) -> None:
        matches = search(
            load_recipes(),
            ("рис", "морковь", "перец", "растительное масло", "вода"),
            "обычное", (),
        )
        self.assertEqual(matches[0][0].id, 3)
        self.assertEqual(matches[0][1], ())

    def test_search_requires_overlap(self) -> None:
        self.assertIn("Совпадений", self.command("/find ананас"))

    def test_search_uses_saved_products(self) -> None:
        first = self.command("/find рис, морковь")
        self.assertEqual(first, self.command("/find"))
        self.assertIn("рис, морковь", self.command("/profile"))

    def test_diet_and_exclusions_filter_search(self) -> None:
        self.command("/diet веганское")
        self.command("/exclude помидоры")
        result = self.command("/find рис, морковь, помидор")
        self.assertIn("Рис с овощами", result)
        self.assertNotIn("Паста с помидорами", result)
        self.assertNotIn("Омлет", result)

    def test_recipe_warns_about_incompatible_diet(self) -> None:
        self.command("/diet веганское")
        self.assertIn("не соответствует", self.command("/recipe 4"))

    def test_week_is_moscow_calendar(self) -> None:
        self.timestamp = datetime(
            2026, 11, 1, 21, 30, tzinfo=timezone.utc).timestamp()
        self.assertEqual(self.assistant.week(), "2026-11-02")

    def test_manual_menu_replaces_slot(self) -> None:
        self.command("/plan пн ужин 3 3")
        self.command("/plan пн ужин 5 1")
        entries = self.assistant.storage.menu(1, self.assistant.week())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["recipe_id"], 5)
        self.assertEqual(entries[0]["portions"], 1)

    def test_automatic_menu_obeys_meal_and_preferences(self) -> None:
        self.command("/diet веганское")
        self.command("/exclude тофу")
        self.command("/plan авто 3")
        entries = self.assistant.storage.menu(1, self.assistant.week())
        self.assertEqual(len(entries), 21)
        for entry in entries:
            recipe = self.assistant.by_id[entry["recipe_id"]]
            self.assertIn(entry["meal"], recipe.meals)
            self.assertIn("веганское", recipe.diets)
            self.assertNotIn("тофу", [i.name for i in recipe.ingredients])
            self.assertEqual(entry["portions"], 3)
        for day in range(7):
            self.assertEqual({e["meal"]
                             for e in entries if e["day"] == day}, set(MEALS))

    def test_no_breakfast_does_not_replace_existing_menu(self) -> None:
        self.command("/exclude овсянка, яйцо, творог, гречка, рис")
        self.command("/plan пн ужин 5")
        before = self.command("/menu")
        self.assertIn("Не хватает", self.command("/plan авто"))
        self.assertEqual(self.command("/menu"), before)

    def test_invalid_plan_does_not_modify_menu(self) -> None:
        self.command("/plan пн ужин 3")
        before = self.command("/menu")
        for invalid in ("пн ужин 3 0", "пн обед 1", "вт ужин 100", "авто 13"):
            self.command("/plan " + invalid)
            self.assertEqual(self.command("/menu"), before)

    def test_shopping_scales_and_sums(self) -> None:
        self.command("/plan пн ужин 3 3")
        self.command("/plan вт обед 3 1")
        items = {name: (unit, amount) for name, unit, amount, _
                 in self.assistant.shopping(1)}
        self.assertEqual(items["рис"], ("г", 320))
        self.assertEqual(items["морковь"], ("г", 200))
        self.assertEqual(items["растительное масло"], ("мл", 30))
        self.assertNotIn("вода", items)

    def test_purchase_toggle_and_menu_change_resets_marks(self) -> None:
        self.command("/plan пн ужин 3")
        self.assertIn("☑", self.command("/buy 1"))
        self.assertNotIn("☑", self.command("/buy 1"))
        self.command("/buy 1")
        self.command("/plan вт ужин 3")
        self.assertNotIn("☑", self.command("/shopping"))

    def test_preference_changes_clear_menu(self) -> None:
        for command in ("/diet веганское", "/exclude тофу"):
            self.command("/plan авто")
            self.command("/buy 1")
            self.command(command)
            self.assertIn("пусто", self.command("/menu"))
            self.assertEqual(self.assistant.storage.purchased(
                1, self.assistant.week()), set())

    def test_users_are_isolated(self) -> None:
        self.command("/diet веганское")
        self.command("/plan авто")
        self.command("/buy 1")
        self.command("/timer 5 тест")
        self.assertIn("обычное", self.command("/profile", 2))
        self.assertIn("пусто", self.command("/menu", 2))
        self.assertIn("Список пуст", self.command("/shopping", 2))
        self.assertIn("нет", self.command("/timers", 2))
        self.assertIn("не найден", self.command("/cancel_timer 1", 2))
        self.assertIn("тест", self.command("/timers"))

    def test_profiles_menu_purchases_and_timers_survive_restart(self) -> None:
        self.command("/find рис, морковь")
        self.command("/diet веганское")
        self.command("/exclude тофу")
        self.command("/plan авто")
        self.command("/buy 1")
        self.command("/timer 5 суп")
        restarted = CookingAssistant(
            Storage(self.path), lambda: self.timestamp)
        for command in ("/profile", "/menu", "/shopping", "/timers"):
            self.assertEqual(self.command(command),
                             restarted.execute(1, 1, command))

    def test_durations_and_invalid_values(self) -> None:
        for text, expected in (("5", 300), ("10с", 10), ("1,5м", 90),
                               ("1ч", 3600), ("24h", 86400)):
            self.assertEqual(parse_duration(text), expected)
        invalid = ("-1", "0", "nan", "inf", "1e309", "25ч", "0.1с", "5 дней")
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_duration(text)

    def test_timer_limit_cancel_and_due(self) -> None:
        for _ in range(10):
            self.assertIn("Таймер #", self.command("/timer 10с суп"))
        self.assertIn("не более 10", self.command("/timer 1с лишний"))
        self.assertEqual(self.assistant.storage.due_timers(
            self.timestamp + 9), [])
        self.command("/cancel_timer 1")
        self.assertEqual(
            len(self.assistant.storage.due_timers(self.timestamp + 10)), 9)

    def test_retry_is_delayed_and_bounded(self) -> None:
        self.command("/timer 1с суп")
        self.timestamp += 2
        for _ in range(4):
            self.assistant.storage.retry_timer(1, self.timestamp)
            self.assertEqual(
                self.assistant.storage.due_timers(self.timestamp), [])
            self.timestamp += 30
            self.assertEqual(
                len(self.assistant.storage.due_timers(self.timestamp)), 1)
        self.assistant.storage.retry_timer(1, self.timestamp)
        self.assertEqual(self.assistant.storage.timers(1), [])

    def test_bad_inputs_have_readable_errors(self) -> None:
        for command in ("/unknown", "/recipe abc", "/plan", "/buy -1",
                        "/diet кето", "/exclude", "/timer", "/cancel_timer x"):
            with self.subTest(command=command):
                self.assertTrue(self.command(command))
        self.assertIn("слишком длинное", self.command("я" * 1501))
        self.assertIn("Список команд", self.command("/unknown"))


if __name__ == "__main__":
    unittest.main()
