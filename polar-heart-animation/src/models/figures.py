"""Каталог фигур: формула отделена от анимации и отрисовки."""

from dataclasses import dataclass
from math import cos

from src.models.heart import PolarCurve, heart_radius


def rose_radius(angle: float) -> float:
    """Вычислить радиус четырехлепестковой полярной розы."""
    # Отрицательный радиус означает точку на противоположном луче.
    return 2.4 * cos(2 * angle)


def limacon_radius(angle: float) -> float:
    """Вычислить радиус лимакона Паскаля с внутренней вмятиной."""
    return 2.0 + 1.2 * cos(angle)


@dataclass(frozen=True)
class Figure:
    """Описать имя, полярную функцию, подпись и цвет фигуры."""

    name: str
    radius: PolarCurve
    equation: str
    color: str


FIGURES = (
    Figure(
        "Сердце", heart_radius,
        "r = 2 − 2sin θ + sin θ · √|cos θ| / (sin θ + 1.4)",
        "#ff779a",
    ),
    Figure(
        "Полярная роза", rose_radius, "r = 2.4cos(2θ)", "#bc9cff",
    ),
    Figure(
        "Лимакон Паскаля", limacon_radius,
        "r = 2 + 1.2cos θ", "#6de0d0",
    ),
)
