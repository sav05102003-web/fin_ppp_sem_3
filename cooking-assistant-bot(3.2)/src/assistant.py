"""Предметная логика команд, независимая от Telegram и сети."""

import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.catalogue import (
    DAYS, DIETS, MEALS, load_recipes, parse_ingredients, search, suitable,
)
from src.models import Recipe
from src.storage import Storage


MOSCOW = timezone(timedelta(hours=3))
HELP = """🍽 Кулинарный помощник — тема 4

/find рис, морковь — найти рецепты; текст без команды тоже ищет продукты
/recipe 3 — состав и шаги рецепта № 3
/diet — варианты питания; /diet веганское — выбрать
/exclude молоко, яйцо — исключить продукты; /exclude нет — очистить
/profile — продукты и предпочтения
/tips — рекомендации по выбранному типу питания

/plan авто 2 — создать 7 дней × 3 приёма пищи на 2 порции
/plan пн ужин 3 2 — поставить рецепт № 3 на ужин понедельника, 2 порции
/menu — показать меню текущей недели (понедельник–воскресенье, Москва)
/clear_menu — очистить меню текущей недели
/shopping — продукты на всю неделю, без воды
/buy 1 — отметить или снять отметку покупки № 1

/timer 5 паста — таймер на 5 минут
/timer 10с чай — таймер на 10 секунд; поддерживаются также м и ч
/timers — активные таймеры
/cancel_timer 1 — отменить собственный таймер № 1
/help — эта справка

При смене питания или исключений меню сбрасывается. Таймеры сохраняются
при перезапуске, но уведомления приходят только при работающем боте.
"""


def parse_duration(value: str) -> float:
    """Разобрать положительную длительность от секунды до суток."""
    match = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)(с|сек|s|м|мин|m|ч|h)?", value.lower())
    if not match:
        raise ValueError("Время: 5 (минут), 10с, 2м или 1ч.")
    amount = float(match[1].replace(",", "."))
    unit = match[2] or "м"
    multiplier = 1 if unit in {"с", "сек", "s"} else (
        3600 if unit in {"ч", "h"} else 60
    )
    seconds = amount * multiplier
    if not 1 <= seconds <= 86400:
        raise ValueError("Длительность должна быть от 1 секунды до 24 часов.")
    return seconds


def portions_value(value: str) -> int:
    """Проверить целое число порций от одного до двенадцати."""
    try:
        portions = int(value)
    except ValueError as error:
        raise ValueError(
            "Число порций должно быть целым, от 1 до 12.") from error
    if not 1 <= portions <= 12:
        raise ValueError("Число порций должно быть от 1 до 12.")
    return portions


class CookingAssistant:
    """Выполнять пользовательские команды над каталогом и личной базой."""

    def __init__(
        self, storage: Storage, now: Callable[[], float] = time.time,
    ) -> None:
        """Загрузить рецепты и сохранить источник времени для таймеров."""
        self.storage = storage
        self.recipes = load_recipes()
        self.by_id = {recipe.id: recipe for recipe in self.recipes}
        self.now = now

    def week(self) -> str:
        """Вернуть дату понедельника текущей недели по московскому времени."""
        today = datetime.fromtimestamp(self.now(), MOSCOW).date()
        return (today - timedelta(days=today.weekday())).isoformat()

    def recipe(self, value: str) -> Recipe:
        """Найти рецепт по числовому ID с понятной ошибкой ввода."""
        try:
            return self.by_id[int(value)]
        except (ValueError, KeyError) as error:
            raise ValueError(
                "Нет такого рецепта. Найдите ID через /find.") from error

    def recipe_text(self, recipe: Recipe) -> str:
        """Сформировать карточку с базовыми порциями и шагами."""
        ingredients = "\n".join(
            f"• {item.name}: {item.quantity:g} {item.unit}"
            for item in recipe.ingredients
        )
        steps = "\n".join(
            f"{index}. {step}" for index, step in enumerate(recipe.steps, 1)
        )
        return (
            f"#{recipe.id} {recipe.title}\n"
            f"{recipe.minutes} мин · порций: {recipe.portions}\n\n"
            f"Состав:\n{ingredients}\n\nПриготовление:\n{steps}"
        )

    def find(self, user_id: int, text: str) -> str:
        """Сохранить продукты и найти до семи подходящих рецептов."""
        profile = self.storage.profile(user_id)
        pantry = parse_ingredients(text) if text.strip() else profile["pantry"]
        if not pantry:
            raise ValueError("Например: /find рис, морковь, перец")
        self.storage.set_profile(user_id, "pantry", pantry)
        matches = search(
            self.recipes, pantry, profile["diet"], profile["excluded"],
        )
        if not matches:
            return (
                "Совпадений с учётом предпочтений нет. Укажите названия "
                "продуктов через запятую или проверьте /profile. "
                "Каталог локальный: в нём 14 рецептов."
            )
        lines = ["Подходящие рецепты:"]
        for recipe, missing in matches[:7]:
            needed = ", ".join(missing) if missing else "всё есть"
            lines.append(
                f"#{recipe.id} {recipe.title} · {recipe.minutes} мин\n"
                f"  Докупить: {needed}\n  /recipe {recipe.id}"
            )
        return "\n\n".join(lines)

    def plan(self, user_id: int, args: list[str]) -> str:
        """Составить недельное меню или изменить отдельный приём пищи."""
        profile = self.storage.profile(user_id)
        entries = []
        automatic = args and args[0].lower() == "авто"
        if automatic and len(args) <= 2:
            portions = portions_value(args[1]) if len(args) == 2 else 2
            allowed = [r for r in self.recipes if suitable(
                r, profile["diet"], profile["excluded"],
            )]
            pools = {meal: [r for r in allowed if meal in r.meals]
                     for meal in MEALS}
            if any(not pool for pool in pools.values()):
                raise ValueError(
                    "Не хватает подходящих рецептов для всех приёмов пищи. "
                    "Скорректируйте /diet и /exclude "
                    "или заполните меню вручную."
                )
            usage = defaultdict(int)
            for day in range(7):
                used_today = set()
                for meal in MEALS:
                    # Меньше повторений за неделю; при равенстве — другой
                    # рецепт в этот день, затем стабильный ID.
                    recipe = min(pools[meal], key=lambda r: (
                        r.id in used_today, usage[r.id], r.id,
                    ))
                    entries.append((day, meal, recipe.id, portions))
                    used_today.add(recipe.id)
                    usage[recipe.id] += 1
        elif not automatic and len(args) in {3, 4}:
            day, meal = args[0].lower(), args[1].lower()
            if day not in DAYS or meal not in MEALS:
                raise ValueError(
                    "День: пн–вс; приём пищи: завтрак, обед, ужин.")
            recipe = self.recipe(args[2])
            if meal not in recipe.meals:
                raise ValueError("Рецепт рассчитан на: " +
                                 ", ".join(recipe.meals))
            if not suitable(recipe, profile["diet"], profile["excluded"]):
                raise ValueError(
                    "Рецепт не соответствует вашим /diet или /exclude.")
            portions = portions_value(args[3]) if len(args) == 4 else 2
            entries.append((DAYS.index(day), meal, recipe.id, portions))
        else:
            raise ValueError("Примеры: /plan авто 2 или /plan пн ужин 3 2")
        self.storage.save_menu(user_id, self.week(), entries, bool(automatic))
        return self.menu_text(user_id) + "\n\nСписок покупок: /shopping"

    def menu_text(self, user_id: int) -> str:
        """Показать сохранённое меню с датой начала недели."""
        entries = self.storage.menu(user_id, self.week())
        if not entries:
            return "Меню пусто. Составить неделю: /plan авто 2"
        lines = [f"Меню недели с {self.week()} (Москва):"]
        for entry in entries:
            recipe = self.by_id[entry["recipe_id"]]
            lines.append(
                f"{DAYS[entry['day']].upper()} · {entry['meal']}: "
                f"{recipe.title} (#{recipe.id}, порций: {entry['portions']})"
            )
        return "\n".join(lines)

    def shopping(self, user_id: int) -> list[tuple[str, str, float, bool]]:
        """Сложить продукты недели с учётом порций и отметок покупки."""
        totals = defaultdict(float)
        for entry in self.storage.menu(user_id, self.week()):
            recipe = self.by_id[entry["recipe_id"]]
            scale = entry["portions"] / recipe.portions
            for item in recipe.ingredients:
                if item.name != "вода":
                    totals[(item.name, item.unit)] += item.quantity * scale
        purchased = self.storage.purchased(user_id, self.week())
        return [
            (name, unit, quantity, (name, unit) in purchased)
            for (name, unit), quantity in sorted(totals.items())
        ]

    def shopping_text(self, user_id: int) -> str:
        """Показать нумерованный список покупок на текущую неделю."""
        items = self.shopping(user_id)
        if not items:
            return "Список пуст. Сначала составьте меню: /plan авто 2"
        lines = [f"Покупки на неделю с {self.week()}:"]
        for index, (name, unit, quantity, bought) in enumerate(items, 1):
            mark = "☑" if bought else "☐"
            lines.append(f"{index}. {mark} {name}: {quantity:g} {unit}")
        return "\n".join(lines) + "\n\nПереключить отметку: /buy номер"

    def tips(self, user_id: int) -> str:
        """Предложить блюда каталога в соответствии с выбранным питанием."""
        profile = self.storage.profile(user_id)
        allowed = [r.title for r in self.recipes if suitable(
            r, profile["diet"], profile["excluded"],
        )]
        return (
            f"Питание: {profile['diet']}. {DIETS[profile['diet']]}\n"
            "Для разнообразия чередуйте доступные крупы, овощи и источники "
            "белка из подходящих рецептов.\n"
            "Примеры: " + ("; ".join(allowed[:4]) or "нет подходящих блюд")
            + ".\nМетки описывают состав рецепта. Для покупных продуктов "
            "проверяйте этикетку и возможные следы аллергенов. "
            "Исключения работают по названиям ингредиентов, без распознавания "
            "аллергенов внутри составных продуктов. "
            "Лечебные диеты бот не назначает."
        )

    def execute(self, user_id: int, chat_id: int, text: str) -> str:
        """Выполнить команду и превратить ошибки ввода в понятный ответ."""
        if len(text) > 1500:
            return "Сообщение слишком длинное. Допустимо до 1500 символов."
        try:
            return self._execute(user_id, chat_id, text.strip())
        except ValueError as error:
            return str(error)

    def _execute(self, user_id: int, chat_id: int, text: str) -> str:
        parts = text.split(maxsplit=1)
        if not parts:
            return HELP
        command = parts[0].split("@")[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if command in {"/start", "/help"}:
            return HELP
        if command == "/find":
            return self.find(user_id, arg)
        if command == "/recipe":
            recipe = self.recipe(arg)
            profile = self.storage.profile(user_id)
            warning = ""
            if not suitable(recipe, profile["diet"], profile["excluded"]):
                warning = "⚠ Рецепт не соответствует вашим предпочтениям.\n\n"
            return warning + self.recipe_text(recipe)
        if command == "/profile":
            profile = self.storage.profile(user_id)
            return (
                f"Питание: {profile['diet']}\n"
                f"Исключено: {', '.join(profile['excluded']) or 'ничего'}\n"
                f"Продукты: {', '.join(profile['pantry']) or 'не указаны'}"
            )
        if command == "/diet":
            if not arg:
                return "\n".join(
                    f"{key}: {value}" for key, value in DIETS.items()
                )
            if arg.lower() not in DIETS:
                raise ValueError("Неизвестный тип питания. Варианты: /diet")
            self.storage.set_profile(user_id, "diet", arg.lower())
            return "Питание сохранено. Меню сброшено.\n" + self.tips(user_id)
        if command == "/exclude":
            if not arg:
                raise ValueError(
                    "Пример: /exclude молоко, яйцо; очистить: /exclude нет")
            excluded = () if arg.lower() == "нет" else parse_ingredients(arg)
            self.storage.set_profile(user_id, "excluded", excluded)
            return ("Исключения сохранены. Меню сброшено. "
                    "Новое меню: /plan авто 2")
        if command == "/tips":
            return self.tips(user_id)
        if command == "/plan":
            return self.plan(user_id, arg.split())
        if command == "/menu":
            return self.menu_text(user_id)
        if command == "/clear_menu":
            self.storage.save_menu(user_id, self.week(), [], True)
            return "Меню недели и отметки покупок очищены."
        if command == "/shopping":
            return self.shopping_text(user_id)
        if command == "/buy":
            items = self.shopping(user_id)
            if not arg.isdecimal() or not 1 <= int(arg) <= len(items):
                raise ValueError(
                    "Укажите номер из актуального списка /shopping.")
            name, unit, _, _ = items[int(arg) - 1]
            self.storage.toggle_purchase(user_id, self.week(), name, unit)
            return self.shopping_text(user_id)
        if command == "/timer":
            timer_args = arg.split(maxsplit=1)
            if not timer_args:
                raise ValueError("Пример: /timer 5 паста или /timer 10с чай")
            seconds = parse_duration(timer_args[0])
            title = timer_args[1] if len(timer_args) == 2 else "Готовка"
            if len(title) > 80:
                raise ValueError(
                    "Название таймера должно быть не длиннее 80 символов.")
            timer_id = self.storage.add_timer(
                user_id, chat_id, title, self.now() + seconds,
            )
            return f"⏱ Таймер #{timer_id}: {title}, через {seconds:g} сек."
        if command == "/timers":
            timers = self.storage.timers(user_id)
            if not timers:
                return "Активных таймеров нет. Создать: /timer 5 паста"
            return "\n".join(
                f"#{row['id']} {row['title']} — осталось "
                f"{max(0, int(row['due'] - self.now()))} сек."
                for row in timers
            )
        if command == "/cancel_timer":
            if not arg.isdecimal():
                raise ValueError("Пример: /cancel_timer 1")
            cancelled = self.storage.cancel_timer(user_id, int(arg))
            return ("Таймер отменён." if cancelled
                    else "Активный таймер не найден.")
        if command.startswith("/"):
            return "Неизвестная команда. Список команд: /help"
        return self.find(user_id, text)
