"""Позиция анимации в долях полной длины ломаной."""

import math


class AnimationModel:
    """Учитывать время, скорость, паузу и завершение без зависимости от GUI."""

    def __init__(self, duration: float = 12.0):
        """Задать время полного прохода при скорости 1× в секундах."""
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Длительность должна быть положительной.")
        self.duration = duration
        self.progress = 0.0
        self.paused = False
        self._speed = 1.0

    @property
    def speed(self) -> float:
        """Получить множитель скорости анимации."""
        return self._speed

    @speed.setter
    def speed(self, value: float):
        """Установить множитель скорости в диапазоне 0.25..4."""
        if not math.isfinite(value) or not 0.25 <= value <= 4.0:
            raise ValueError("Скорость должна лежать от 0.25 до 4.")
        self._speed = value

    @property
    def completed(self) -> bool:
        """Сообщить, нарисована ли вся кривая."""
        return self.progress >= 1.0

    def advance(self, elapsed: float):
        """Продвинуть рисунок пропорционально прошедшему времени."""
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Прошедшее время должно быть неотрицательным.")
        if not self.paused:
            self.progress = min(
                1.0, self.progress + elapsed * self.speed / self.duration
            )

    def restart(self):
        """Начать проход сначала, сохранив скорость и состояние паузы."""
        self.progress = 0.0

    def show_all(self):
        """Показать готовую кривую без ожидания анимации."""
        self.progress = 1.0
