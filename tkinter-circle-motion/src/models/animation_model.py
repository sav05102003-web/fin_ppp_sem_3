"""Вычисление движения по окружности независимо от интерфейса."""

import math
from dataclasses import dataclass, field


@dataclass
class AnimationModel:
    """Хранить параметры окружности и угол движущейся точки.

    Положительная скорость соответствует движению по часовой стрелке
    в системе координат Canvas, где ось Y направлена вниз.
    """

    center_x: float = 300.0
    center_y: float = 300.0
    radius: float = 200.0
    speed: float = 1.0
    angle: float = field(default=-math.pi / 2, init=False)

    def __post_init__(self) -> None:
        """Проверить допустимость начальных параметров."""
        if not all(math.isfinite(value) for value in (
            self.center_x, self.center_y, self.radius, self.speed
        )):
            raise ValueError("Параметры должны быть конечными числами.")
        if self.radius <= 0:
            raise ValueError("Радиус должен быть положительным.")

    @property
    def position(self) -> tuple[float, float]:
        """Вернуть текущие координаты центра точки."""
        return (
            self.center_x + self.radius * math.cos(self.angle),
            self.center_y + self.radius * math.sin(self.angle),
        )

    def advance(self, elapsed: float) -> None:
        """Продвинуть точку на elapsed секунд с текущей скоростью."""
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError(
                "Интервал должен быть конечным и неотрицательным."
            )
        # Угол зависит от времени, а не FPS. Остаток ограничивает его рост.
        self.angle = (self.angle + self.speed * elapsed) % math.tau

    def set_speed(self, speed: float) -> None:
        """Установить конечную угловую скорость в радианах в секунду."""
        if not math.isfinite(speed):
            raise ValueError("Скорость должна быть конечным числом.")
        self.speed = speed

    def reset(self) -> None:
        """Вернуть точку наверх, сохранив её скорость."""
        self.angle = -math.pi / 2
