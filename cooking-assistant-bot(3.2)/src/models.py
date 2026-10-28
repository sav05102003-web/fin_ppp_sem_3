"""Неизменяемые модели каталога рецептов."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    """Продукт и его количество на базовое число порций."""

    name: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class Recipe:
    """Рецепт с ингредиентами, шагами и пищевыми метками."""

    id: int
    title: str
    portions: int
    minutes: int
    meals: tuple[str, ...]
    diets: frozenset[str]
    ingredients: tuple[Ingredient, ...]
    steps: tuple[str, ...]
