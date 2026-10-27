"""Отрисовка объектов без изменения математической модели."""

import tkinter as tk

from src.models.animation_model import AnimationModel


class Renderer:
    """Создать окружность и обновлять положение одной точки."""

    POINT_RADIUS = 6

    def __init__(self, canvas: tk.Canvas, model: AnimationModel) -> None:
        """Создать два постоянных объекта на переданном Canvas."""
        self.canvas = canvas
        cx, cy, radius = model.center_x, model.center_y, model.radius
        self.orbit_id = canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline="#334155", width=2,
        )
        self.point_id = canvas.create_oval(
            0, 0, 0, 0, fill="#e11d48", outline="#e11d48",
        )
        self.draw(model)

    def draw(self, model: AnimationModel) -> None:
        """Переместить существующую точку в координаты модели."""
        x, y = model.position
        radius = self.POINT_RADIUS
        self.canvas.coords(
            self.point_id, x - radius, y - radius, x + radius, y + radius,
        )
