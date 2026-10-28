"""Загрузка и поиск рецептов в локальном проверяемом каталоге."""

import json
import math
import re
from pathlib import Path

from src.models import Ingredient, Recipe


CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "data/recipes.json"
DIETS = {
    "обычное": "Все рецепты каталога без дополнительного фильтра.",
    "вегетарианское": ("Блюда без мяса и рыбы; "
                       "возможны яйца и молочные продукты."),
    "веганское": "Блюда без мяса, рыбы, яиц и молочных продуктов.",
    "безглютеновое": "Рецепты без пшеницы, ржи и ячменя в составе каталога.",
    "безмолочное": "Рецепты без молочных ингредиентов в составе каталога.",
}
MEALS = ("завтрак", "обед", "ужин")
DAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
ALIASES = {
    "помидоры": "помидор", "томаты": "помидор", "томат": "помидор",
    "огурцы": "огурец", "яйца": "яйцо", "яиц": "яйцо",
    "курица": "куриное филе", "куриные грудки": "куриное филе",
    "картошка": "картофель", "морковка": "морковь",
    "масло растительное": "растительное масло", "бананы": "банан",
    "яблоки": "яблоко", "овсяные хлопья": "овсянка",
    "овсяные": "овсянка", "макароны": "паста", "перцы": "перец",
    "болгарский перец": "перец", "чечевица красная": "чечевица",
}


def normalize(value: str) -> str:
    """Привести название продукта к каноническому виду."""
    cleaned = " ".join(value.lower().replace("ё", "е").split())
    return ALIASES.get(cleaned, cleaned)


def parse_ingredients(text: str) -> tuple[str, ...]:
    """Разобрать список продуктов через запятую или точку с запятой."""
    items = tuple(dict.fromkeys(
        normalize(item) for item in re.split(r"[,;]", text)
        if item.strip()
    ))
    if not items or len(items) > 30 or any(len(x) > 60 for x in items):
        raise ValueError(
            "Укажите от 1 до 30 продуктов через запятую (до 60 букв).")
    return items


def load_recipes(path: Path = CATALOGUE_PATH) -> tuple[Recipe, ...]:
    """Загрузить каталог и отклонить неверные количества, метки или ID."""
    recipes = []
    seen = set()
    for row in json.loads(path.read_text(encoding="utf-8")):
        ingredients = tuple(Ingredient(**item) for item in row["ingredients"])
        recipe = Recipe(
            id=row["id"], title=row["title"], portions=row["portions"],
            minutes=row["minutes"], meals=tuple(row["meals"]),
            diets=frozenset(row["diets"]), ingredients=ingredients,
            steps=tuple(row["steps"]),
        )
        if (recipe.id in seen or recipe.id < 1 or recipe.portions < 1
                or recipe.minutes < 1 or not recipe.steps or not ingredients
                or not recipe.meals or not set(recipe.meals) <= set(MEALS)
                or not recipe.diets <= DIETS.keys() - {"обычное"}):
            raise ValueError(f"Ошибка в рецепте {recipe.id}.")
        names = set()
        for item in ingredients:
            if (item.name != normalize(item.name) or item.name in names
                    or not math.isfinite(item.quantity) or item.quantity <= 0
                    or item.unit not in {"г", "мл", "шт."}):
                raise ValueError(f"Ошибка ингредиентов рецепта {recipe.id}.")
            names.add(item.name)
        seen.add(recipe.id)
        recipes.append(recipe)
    if not recipes:
        raise ValueError("Каталог рецептов пуст.")
    return tuple(recipes)


def suitable(recipe: Recipe, diet: str, excluded: tuple[str, ...]) -> bool:
    """Проверить метки питания и точные названия исключённых продуктов."""
    names = {item.name for item in recipe.ingredients}
    return (diet == "обычное" or diet in recipe.diets) and not (
        names.intersection(excluded)
    )


def search(
    recipes: tuple[Recipe, ...], pantry: tuple[str, ...], diet: str,
    excluded: tuple[str, ...],
) -> list[tuple[Recipe, tuple[str, ...]]]:
    """Найти блюда хотя бы с одним совпадением и отсортировать по покрытию."""
    available = set(pantry)
    matches = []
    for recipe in recipes:
        if not suitable(recipe, diet, excluded):
            continue
        names = {
            item.name for item in recipe.ingredients if item.name != "вода"
        }
        found = names & available
        if found:
            missing = tuple(sorted(names - available))
            matches.append((recipe, missing))
    # Сначала максимальная доля имеющихся продуктов, затем меньше покупок.
    return sorted(matches, key=lambda row: (
        len(row[1]) / sum(i.name != "вода" for i in row[0].ingredients),
        len(row[1]), row[0].id,
    ))
