"""Построение кривых на целочисленной квадратной сетке."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable


Point = tuple[int, int]


def _validate_order(order, maximum):
    if isinstance(order, bool) or not isinstance(order, int):
        raise ValueError("Порядок кривой должен быть целым числом.")
    if not 1 <= order <= maximum:
        raise ValueError(f"Порядок кривой должен лежать от 1 до {maximum}.")


@lru_cache(maxsize=8)
def _hilbert(order: int) -> tuple[Point, ...]:
    if order == 0:
        return ((0, 0),)
    smaller = _hilbert(order - 1)
    size = 2 ** (order - 1)
    # Четыре копии предыдущего порядка: первая повёрнута отражением
    # относительно диагонали, последняя — с разворотом и переносом.
    # Именно эти преобразования соединяют квадранты соседними точками.
    return (
        tuple((y, x) for x, y in smaller)
        + tuple((x, y + size) for x, y in smaller)
        + tuple((x + size, y + size) for x, y in smaller)
        + tuple((2 * size - 1 - y, size - 1 - x) for x, y in smaller)
    )


def hilbert_points(order: int) -> tuple[Point, ...]:
    """Вернуть 4**order точек рекурсивной кривой Гильберта, order=1..7."""
    _validate_order(order, 7)
    return _hilbert(order)


@dataclass(frozen=True)
class CurveSpec:
    """Алгоритм кривой, основание сетки и допустимая глубина рекурсии."""

    name: str
    base: int
    max_order: int
    builder: Callable[[int], tuple[Point, ...]]


CURVES = {
    "Кривая Гильберта": CurveSpec("Гильберт", 2, 7, hilbert_points),
}
