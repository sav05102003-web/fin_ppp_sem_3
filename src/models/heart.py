"""Полярное уравнение сердца и перевод координат."""

from collections.abc import Callable
from math import cos, isfinite, sin, sqrt, tau

PolarCurve = Callable[[float], float]
Point = tuple[float, float]


def heart_radius(angle: float) -> float:
    """Вычислить радиус сердца для угла в радианах."""
    sine = sin(angle)
    # Поправка к кардиоиде формирует округлые доли и выемку сверху.
    # Знаменатель всегда положителен: sin(angle) + 1.4 >= 0.4.
    correction = sine * sqrt(abs(cos(angle))) / (sine + 1.4)
    return 2.0 - 2.0 * sine + correction


def polar_to_cartesian(radius: float, angle: float) -> Point:
    """Перевести полярные координаты в декартовы."""
    return radius * cos(angle), radius * sin(angle)


def sample_curve(curve: PolarCurve, samples: int = 1000) -> list[Point]:
    """Получить замкнутый контур полярной кривой за один оборот."""
    if samples < 16:
        raise ValueError("Для контура требуется не менее 16 отрезков.")
    points = []
    for index in range(samples):
        angle = -tau / 4 + tau * index / samples
        radius = curve(angle)
        if not isfinite(radius):
            raise ValueError("Радиус должен быть конечным.")
        points.append(polar_to_cartesian(radius, angle))
    points.append(points[0])
    return points
