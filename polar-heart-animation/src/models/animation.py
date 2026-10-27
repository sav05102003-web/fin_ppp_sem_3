"""Независимая от интерфейса модель постепенной отрисовки."""

from dataclasses import dataclass
from math import cos, isfinite, tau


@dataclass
class AnimationModel:
    """Хранить угол, скорость, паузу и номер прохода контура."""

    speed: float = 1.0
    angle: float = 0.0
    paused: bool = False
    cycles: int = 0
    hold: float = 0.0
    last_step: float = 0.0

    @property
    def progress(self) -> float:
        """Вернуть долю нарисованного контура."""
        return self.angle / tau

    def advance(self, elapsed: float) -> None:
        """Продвинуть анимацию на число секунд с переменным шагом угла."""
        if not isfinite(elapsed) or elapsed < 0:
            raise ValueError("Время должно быть конечным и неотрицательным.")
        if self.paused:
            return
        self.last_step = 0.0
        # Мелкие временные шаги уменьшают зависимость движения от FPS.
        while elapsed > 1e-10:
            step_time = min(elapsed, 1 / 240)
            elapsed -= step_time
            if self.hold > 0:
                self.hold = max(0.0, self.hold - step_time)
                if self.hold == 0:
                    self.angle = 0.0
                    self.cycles += 1
                continue
            # Скорость меняется вдоль контура: угловое приращение не постоянно.
            angular_speed = 1.5 * self.speed * (
                0.6 + 0.4 * cos(2 * self.angle) ** 2
            )
            delta = min(angular_speed * step_time, tau - self.angle)
            self.angle += delta
            self.last_step += delta
            if self.angle >= tau:
                self.hold = 0.8

    def set_speed(self, speed: float) -> None:
        """Установить множитель скорости от 0.25 до 3."""
        if not isfinite(speed) or not 0.25 <= speed <= 3.0:
            raise ValueError("Скорость должна находиться в диапазоне 0.25–3.")
        self.speed = speed

    def toggle_pause(self) -> None:
        """Переключить паузу без изменения контура."""
        self.paused = not self.paused

    def reset(self) -> None:
        """Начать первый проход заново, сохранив скорость и паузу."""
        self.angle = 0.0
        self.cycles = 0
        self.hold = 0.0
        self.last_step = 0.0
